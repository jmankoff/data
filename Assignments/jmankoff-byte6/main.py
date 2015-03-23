#!/usr/bin/env python
#
# Byte 6 Version 2
# 
# Copyright 2/2014 Jennifer Mankoff
#
# Licensed under GPL v3 (http://www.gnu.org/licenses/gpl.html)
#

# standard imports
import webapp2
import math
from google.appengine.api import files
from google.appengine.api import memcache
from apiclient.discovery import build
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from oauth2client.appengine import AppAssertionCredentials 
from django.utils import simplejson
import httplib2
import urllib
import numpy as np
import logging

# import for checking whether we are running on localhost or remotely
import os

# make sure to add this to app.yaml too
from webapp2_extras import jinja2

# BigQuery API Settings
_PROJECT_NUMBER        = '' 

# Define your production Cloud SQL instance information. 
_DATABASE_NAME = 'publicdata:samples.natality'

# number of rows to request at a time (make this smaller when you are testing)
_MAX_ROWS = 80
_TIMEOUT = 2000000

# cutoff for apgar_1min
_APGAR_CUTOFF = 7

logging.info("setting up credentials")
credentials = AppAssertionCredentials(scope='https://www.googleapis.com/auth/bigquery.readonly')
http        = credentials.authorize(httplib2.Http(memcache))
service     = build("bigquery", "v2", http=http)
logging.info("done setting up credentials")

# You can change these features, but make sure they are all numerical
features = ['drinks_per_week', 'born_alive_alive', 'born_alive_dead', 'father_age', 'mother_age', 'plurality', 'weight_gain_pounds']
# this is global so each time someone presses 'learn' it remembers what was already learned
        
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
        
        logging.info("running birth related queries")
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

        # This is what you are predicting
        predict = 'apgar_1min'

        # this gets data only from the TRAIN set (odd numbered rows) and for which 
        # apgar_1min is small (one class we are predicting)
        zeros_string = "row_number % 2 = 1 AND apgar_1min < {0}".format(_APGAR_CUTOFF)
        # thes gits data only from the TRAIN set (odd numbered rows) and for which
        # apgar_1min is large (the other class we are predicting)
        ones_string = "row_number % 2 = 1 AND apgar_1min >= {0}".format(_APGAR_CUTOFF) 

        weights, regression_model = self.stochastic_gradient_descent(features, predict, self.apgar_1min_test, zeros_string, ones_string)

        # TODO
        # this is something you should implement yourself. It is VERY simple -- you just need to count
        # how many rows are 'true' for self.apgar_1min_test and how many are false
        # you should return a function that takes in anything and outputs the majority class
        # zeror_model = self.zeror_train(features, predict, self.apgar_1min_test)
        # pay attention to how the model is constructed just above to do this
        # -- it is a function.

        # testing_X is the data we will use to make predictions, labels are the ground truth
        # (correct) y values. The test makes sure we rae getting data for which the row numbers are
        # even (this is the half of our data we will use for testing, odd numbers are reserved for training)
        testing_X, labels = self.get_data(features, predict, self.apgar_1min_test, filter="row_number % 2 = 0", limit=100)

        # apply_model can apply any model (a model is just a function that can predict a value)
        # it returns an accuracy
        regression_accuracy = self.apply_model(regression_model, testing_X, labels)
        # TODO
        # you should uncomment the line below and remove the line that sets zeror_accuracy to 0
        # zeror_accuracy = self.apply_model(zeror_model, testing_X, labels) 
        zeror_accuracy = 0

        # this is just preparing for display on the web page
        features_weights = []
        for i in xrange(len(features)):
            features_weights.append({'feature' : features[i], 'weight' : weights[i]})
        context = {"weights": features_weights, "accuracy": [regression_accuracy, zeror_accuracy]}
        self.render_response('index.html', context)

    # a helper function for retrieving data from the database and putting it into
    # the right format for machine learning. The parameters for this function are
    # features -- an array of features to retrieve from the database (column names)
    # predict -- the column name of the item to be predicted
    # prediction_test -- returns a class based on the value of the predict variable
    # filter -- used to decide which rows should be included in this data retrieval
    # limit -- the maximum number of rows to retrieve
    def get_data(self, features, predict, prediction_test, filter=None, limit=_MAX_ROWS):
        # need to retrieve data from bigquery 
        query_string = self.make_query_string(features, predict, filter)

        # run the query and capture the results
        data = self.run_query(query_string)

        # similar to the google SQL work we did in byte4, the stuff we 
        # care about is in rows
        rows = data[u'rows']
        data = []
        labels = []
        featureNum = len(features)

        # construct the dataset
        for row in rows:
            instance = []
            prediction=row[u'f'][0][u'v']
            labels.append(prediction_test(prediction))
            for i in xrange(1,featureNum+1):
                instance.append(float(row[u'f'][i][u'v']))
            data.append(instance)
        for i in data:
            i.append(1.0)

        # y are the labels -- the values we are predicting
        # np.array helps to make it possible to do very fast matrix arithmetic
        y = np.array(labels)

        # X are the features -- the values we use to make the prediction
        X = np.array(data)

        return X, y

    # make_query_string makes a valid query string for Google BigQuery based
    # on a given set of column names for features and prediction
    # features -- an array of features to retrieve from the database (column names)
    # predict -- the column name of the item to be predicted
    # prediction_test -- returns a class based on the value of the predict variable
    # filter -- used to decide which rows should be included in this data retrieval
    # limit -- the maximum number of rows to retrieve
    def make_query_string(self, features, predict, filter=None, limit=_MAX_ROWS):
        columns_string = predict  
        checks = ""
        
        for feature in features:
            columns_string = columns_string + ", " + feature
            checks = checks + feature + " IS NOT NULL AND " + feature + "!=99 AND "
        checks = checks + predict + " IS NOT NULL AND " + predict + "!=99 " 

        columns_string = columns_string 
        
        query_string = "SELECT *, rand() as ind FROM ( SELECT " + columns_string
        query_string = query_string + ", ROW_NUMBER() OVER (ORDER BY year) AS row_number FROM "
        query_string = query_string + _DATABASE_NAME + " WHERE " + checks  + ") "

        if filter!=None:
            query_string = query_string + " WHERE " + filter
            
        query_string = query_string + " LIMIT {0}".format(_MAX_ROWS)

        logging.info(query_string)
        
        return query_string

    # run the query specified in query_string, or load a local file
    # (you'll use that option potentially when debugging the first half
    # of the assignment)
    def run_query(self, query_string, filename=None):
        # set up the query 
        query = {'query':query_string, 'timeoutMs':_TIMEOUT}
        # service is the oauth2 setup that we created above
        jobCollection = service.jobs()

        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):

            # project number is the project number you should have 
            # defined in your app
            return jobCollection.query(projectId=_PROJECT_NUMBER,body=query).execute()
        else:
            # open the data stored in a file called filename
            try:
                fp = open(filename)
                return simplejson.load(fp)
            except IOError:
                logging.info('cannot run locally')
                return None
            
    # This function has knowledge specific to the thing that is being predicted
    # on this data set. In this case, we are assuming that value is an apgar score
    # and that it should be converted to an int, and that less than 4 is different
    # than more than 4 (more than 4 is a positive outcome, less than 4 is a negative)
    # It takes in a value and returns a class (in this case, either 0 or 1 since we
    # are only doing a two class prediction problem)
    def apgar_1min_test(self, value):
        if (int(value)>=_APGAR_CUTOFF):
            return 1.0
        else:
            return 0.0

    # loss function for logistic regression
    # you shouldn't need to modify this. 
    def loss_func(self, x, weights):
        return 1.0/(1.+math.e**(-1.0*np.dot(x,weights)))

    
    # basic logistic regression (used by stochastic_gradient_descent)
    # weights -- the list weight scurrently assigned to the features  (an empty array that will
    #   be filled in by this function.
    # X -- the array containing cases to predict from,
    # labels -- the ground truth y values.
    # step -- the rate controller for changing the weights.
    # lam --  the regularization parameter. Something you could play with on a large data set is
    #      what value to use for this. you would want to do that by picking an optimization set 
    #      and trying lots of lam values (from 0 to 1) on that optimization set.
    # iterations -- defaults to 1 for stochastic gradient descent, but can be higher in standard gradient descent. 
    def gradient_descent(self, weights, X, y_labels, step=0.1, lam=0.1, iterations=1):
        # this is the logistic regression implementation from slide 61
        m, n=X.shape
        # initiate the attribute vector
        # iterate over the rows to train the model on the same data
        old_weights = weights

        for i in xrange(iterations):
            for r in xrange(_MAX_ROWS):
                old_weights = weights
                weights = old_weights + step*(self.loss_func(X[r], old_weights - y_labels[r]))*X[r] 
                #add in regularization term
                weights = weights - lam*2.*step*old_weights

        return weights


    # stochastic gradient descent needs to run repeatedly, pulling new data each time
    # for this reason, it incorporates calls to get_data inside its loop and it needs
    # all of the parameters for those calls, including the feature set (features)
    # predictor (predict), labeling function (prediction_test), and a way to get examples
    # of both classes (zeros_string and ones_string).
    # batch is the number of times to run this (make it small when debugging)
    def stochastic_gradient_descent(self, features, predict, prediction_test, zeros_string, ones_string, batch=10):
        weights = np.random.random(len(features)+1)
        # train the regression model stochastically. Technically, we would do only one x
        # at each round, but we can load subsets of the data and do multiple Xs at
        # each round. _MAX_ROWS determines how much data is loaded at earch iteration.
        for i in xrange(batch):
            # get _MAX_ROWS of examples of bad births and good births (equal amounts of each)
            # this is so we have lots of examples of both types
            bad_births, bad_births_labels = self.get_data(features, predict, prediction_test, zeros_string)
            good_births, good_births_labels = self.get_data(features, predict, prediction_test, ones_string)
            
            # combine them into one data set
            y_labels = np.concatenate([bad_births_labels, good_births_labels])
            X = np.concatenate([bad_births, good_births])

            # the resulting weights
            weights = self.gradient_descent(weights, X, y_labels)
            
        # this is a function that returns a class given a vector of features
        # the class that is returned is determined by the array weights that was
        # just trained
        model = lambda x: 1-self.loss_func(x, weights)<.5
        return weights, model

    # apply_model takes a model (a function that can make a prediction from a set of features)
    # and X (data to test the model against) and labels
    def apply_model(self, model, testing_X, labels):
        # This will hold the predicted class values over the test set
        y=[]

        # apply the model on the testing dataset testing_X

        # apply the model on the testing dataset
        for i in testing_X:
            y.append(model(i))

        # evaluate the model 
        # how many cases were equal to the labels?
        correct_results =np.sum(np.equal(y, labels))
        accuracy = 1.0* correct_results /len(y)

        # TODO
        # you should also calcualte precision and recall
        # using the equations provided in class and return them here as well
        return accuracy
        
        
app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)

