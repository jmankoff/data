#!/usr/bin/env python
#
# Byte 4 Version 1
# 
# Copyright 2/2014 Jennifer Mankoff
#
# Licensed under GPL v3 (http://www.gnu.org/licenses/gpl.html)
#

# standard imports
import webapp2
from google.appengine.api import files
from google.appengine.api import memcache
from apiclient.discovery import build
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from oauth2client.appengine import AppAssertionCredentials 
from apiclient.discovery import build
from webapp2_extras import json
from django.utils import simplejson
import httplib2
import urllib
import numpy

import logging

# import for checking whether we are running on localhost or remotely
import os

# make sure to add this to app.yaml too
from webapp2_extras import jinja2

# BigQuery API Settings
_PROJECT_NUMBER        = '756504729929' 

# Define your production Cloud SQL instance information. 
_DATABASE_NAME = 'publicdata:samples.natality'

credentials = AppAssertionCredentials(scope='https://www.googleapis.com/auth/bigquery')
http        = credentials.authorize(httplib2.Http(memcache))
service     = build("bigquery", "v2", http=http)

# we are adding a new class that will 
# help us to use jinja. MainHandler will sublclass this new
# class (BaseHandler), and BaseHandler is in charge of subclassing
# webapp2.RequestHandler  
class BaseHandler(webapp2.RequestHandler):
    @webapp2.cached_property
    def jinja2(self):
        # Returns a Jinja2 renderer cached in the app registry.
        return jinja2.get_jinja2(app=self.app)
    
    # lets jinja render our response
    def render_response(self, _template, context):
        values = {'url_for': self.uri_for}
        logging.info(context)
        values.update(context)
        self.response.headers['Content-Type'] = 'text/html'

        # Renders a template and writes the result to the response.
        rv = self.jinja2.render_template(_template, **values)
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.write(rv)

class MainHandler(BaseHandler):
    def get(self):
        """default landing page"""
        
        #====================================================================
        # Sample query for getting #births by state 
        #====================================================================

        query_string = 'SELECT state, count(*) FROM [{0}] GROUP by state;'.format(_DATABASE_NAME)
        births = self.run_query(query_string, filename='data/states.json')

        # similar to the google SQL work we did in byte4, the stuff we 
        # care about is in rows
        rows = births[u'rows']
        states = []
        for row in rows:
            name = row[u'f'][0][u'v']
            num = row[u'f'][1][u'v']
            if name == None: name = u'None'
            state = {'state':unicode.encode(name), 'total':int(num)}
            states = states + [state]

        #====================================================================
        # Sample query for getting data for machine learning
        #====================================================================
        # we will be trying to predict the birth weight of the baby. 

        # This query will select a different num_records records (randomly) each time it is run
        num_records = 100
        query_string = "SELECT born_alive_alive, born_alive_dead, born_dead, child_race, alcohol_use, ever_born, father_age, father_race, mother_age, mother_birth_state, mother_married, plurality, year, weight_pounds, apgar_1min, apgar_5min, HASH(NOW()-source_year-gestation_weeks*10000+year-child_race*10-mother_age*100-record_weight*10) as hash_val FROM [{0}] WHERE born_alive_alive IS NOT NULL AND born_alive_dead IS NOT NULL AND born_dead IS NOT NULL AND child_race IS NOT NULL AND  alcohol_use IS NOT NULL AND ever_born IS NOT NULL AND father_age IS NOT NULL AND father_race IS NOT NULL AND mother_age IS NOT NULL AND mother_birth_state IS NOT NULL AND mother_married IS NOT NULL AND plurality IS NOT NULL AND year IS NOT NULL AND weight_pounds IS NOT NULL AND apgar_1min IS NOT NULL AND apgar_5min IS NOT NULL  ORDER BY hash_val LIMIT {1}".format(_DATABASE_NAME, num_records)
        
        # save a history of the weight vectors into an array
        weights_history = []
        max_iterations = 10
        stop_condition_met = False

        data = self.run_long_query(query_string)

        # loop again if the query failed (timeouts happen fairly frequently and
        # this gets around that problem)
        while data == None:
            data = self.run_long_query(query_string)

        X, y = self.prepare_for_machine_learning(data)
        
        weights = numpy.array([0.0 for i in range(X.shape[1])])
        logging.info("weights: {0}".format(weights))

        # train the logistic regression
        # using gradient descent
        for i in range(max_iterations):
            # run the next iteration of gradient descent
            weights, stop_condition_met = self.gradient_descent(X, y, weights, eta=10.0)

            # store the new weights
            weights_history.append(numpy.copy(weights))
            # decide whether to keep iterating or not
            if stop_condition_met: break

        logging.info("number of iterations: %s", i)
        logging.info("hypothesis weights: {:}".format(weights))
        
        # let's see how accurate we are
        data = self.run_long_query(query_string, 'data/data.json', 10000)

        # loop again if the query failed (timeouts happen fairly frequently and
        # this gets around that problem)
        while data == None:
            data = self.run_long_query(query_string, 'data/data.json', 10000)

        test_X, test_y = self.prepare_for_machine_learning(data)

        # logistic calculates theta, or the probability of our class
        logistic = lambda s: 1.0 / (1.0 + numpy.exp(-s))
        pred_y = weights.dot(test_X.T)
        logging.info(pred_y)
        pred_y = logistic(weights.dot(test_X.T))
        logging.info(pred_y)
        
        context = {"states": states}

        # and render the response
        self.render_response('index.html', context)

    # prepend a column of 1's to dataset X to enable theta_0 calculations
    def add_ones(self, X):
        return numpy.hstack((numpy.zeros(shape=(X.shape[0],1), dtype='float') + 1, X))

    # prepares data for use in machine learning. Returns X and y arrays
    def prepare_for_machine_learning(self, data):
        # sample row: {u'f': [{u'v': None}, {u'v': u'0'}, {u'v': u'0'}, {u'v': u'0'}, {u'v': u'7'}, {u'v': None}, {u'v': None}, {u'v': None}, {u'v': u'1'}, {u'v': u'21'}, {u'v': u'7'}, {u'v': u'18'}, {u'v': u'Foreign'}, {u'v': None}, {u'v': u'CA'}, {u'v': u'1'}, {u'v': u'1973'}, {u'v': u'4.18657835538'}, {u'v': u'-9222828571341066309'}]}

        rows = []
        for row in data:
            row_contents = row[u'f']
            new_row = []

            # check if the mother was born abroad or not
            # columns are: (born_alive_alive, born_alive_dead, born_dead, child_race, alcohol_use, ever_born, father_age, father_race, mother_age, mother_birth_state, mother_married, plurality, year, weight_pounds, apgar_1min, apgar_5min)  
            mother_birth_state = row_contents[9][u'v']
            if (mother_birth_state == u'Foreign'):
                mother_birth_state = 0
            elif mother_birth_state is None:
                continue
            else:
                mother_birth_state = 1
            row_contents[9][u'v'] = mother_birth_state

            # now convert everything to integers or floats
            for item in row_contents:
                if item[u'v'] is None:
                    continue
                elif (item[u'v'] == u'false'):
                    new_row.append(0)
                elif (item[u'v'] == u'true'):
                    new_row.append(1)
                else:
                    new_row.append(float(item[u'v']))

            if len(new_row) == 16:
                rows.append(new_row)

        rows = numpy.array(rows)

        # normalize the data, ignoring missing values (leave them as -1 and don't count them in when normalizing)

        col_sums = rows.argmax(axis=0) 
        col_sums = col_sums + 1
        rows = rows/col_sums

        # need to extract X and y here 
        # X holds the first 17 columns (born_alive_alive, born_alive_dead, born_dead, child_race, cigarette_use, ever_born, father_age, father_race, mother_age, mother_birth_state, mother_married, plurality, year, weight_pounds)
        X = rows[:, :5]

        # add ones for theta_0 calculations
        #X = self.add_ones(X)

        # y holds the apgar_1min
        y = rows[:, 14]

        # y should be 1 if the apgar is 8 or 9 and 0 otherwise 
        # because an apgar of 7-10 indicates a healthy baby
        # http://www.nlm.nih.gov/medlineplus/ency/article/003402.htm
        y = y.astype(int)
        y = y // 9 | y //8 | y // 7 | y // 10 

        return X, y

    def run_long_query(self, query_string, filename=None, timeout=10000):
        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            # set up the query 
            query = {'configuration': {'query': {'query':query_string} } }
            # service is the oauth2 setup that we created above
            jobCollection = service.jobs()
            insertResponse = jobCollection.insert(projectId=_PROJECT_NUMBER,body=query).execute()
            query_jobId = insertResponse[u'jobReference'][u'jobId']
            currentRow = 0

            logging.info("Job ID")
            logging.info(query_jobId)

            try:
                queryReply = jobCollection.getQueryResults(projectId=_PROJECT_NUMBER, jobId=query_jobId,
                                                           startIndex=currentRow).execute()

                rows = []
                while(('rows' in queryReply) and currentRow < queryReply[u'totalRows']):
                    currentRow += len(queryReply[u'rows'])
                    rows = queryReply[u'rows']
                    queryReply = jobCollection.getQueryResults(
                        projectId=_PROJECT_NUMBER, jobId=query_jobId,
                        startIndex=currentRow).execute()
                return rows

            except Exception as err:
                logging.info("error")
                logging.info(err)
                print err

        else: 
            return self.run_query(query_string, filename=filename, timeout=timeout)
        

    # run the query specified in query_string, but if local open filename instead
    def run_query(self, query_string, filename=None, timeout=10000):
        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            # set up the query 
            query = {'query':query_string, 'timeoutMs':timeout}
            # service is the oauth2 setup that we created above
            jobCollection = service.jobs()
            # project number is the project number you should have 
            # defined in your app
            return jobCollection.query(projectId=_PROJECT_NUMBER,body=query).execute()
        else:
            # open the data stored in a file called filename
            try:
                fp = open(filename)
                return simplejson.load(fp)
            except IOError:
                logging.info("failed to load file %s", filename)
                return None

    # X are the features, y is the class, weights is the weight vector. 
    # this is based on http://nbviewer.ipython.org/gist/vietjtnguyen/6655020
    def gradient_descent(self, X, y, weights, eta=1.0, epsilon=0.001): 
        #logging.info("in gradient descent")
        #logging.info("X {0}:".format(X))
        #logging.info(type(X))
        #logging.info("y {0}:".format(y))
        #logging.info(type(y))
        logging.info("weights {0}:".format(weights))
        #logging.info(type(weights))
        # calculate the predicting y values for these weights
        #y_pred = weights.dot(X.T)
        #logging.info("y_pred:".format(y_pred))

        #logging.info("weights {0}:".format(weights))
        error_E = numpy.mean(numpy.tile(- y / (1.0 + numpy.exp(y * weights.dot(X.T))),
                                                (X.shape[1], 1)).T * X, axis=0)
        weights = weights - (eta * error_E)
        logging.info("error_E {0}:".format(error_E))
        stop_condition = numpy.linalg.norm(error_E) <= numpy.linalg.norm(weights) * epsilon
        return weights, stop_condition
            

app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)

