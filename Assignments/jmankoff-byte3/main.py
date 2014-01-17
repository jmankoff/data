#!/usr/bin/env python
#
# Byte 3 Version 2
# 
# Copyright 1/2014 Jennifer Mankoff
#
# Licensed under GPL v3 (http://www.gnu.org/licenses/gpl.html)
#

# standard imports (same as byte2)
import webapp2
from webapp2_extras import jinja2
from webapp2_extras import json
import logging
import httplib2
from apiclient.discovery import build
import urllib
import numpy

# This API key is provided by google as described in the tutorial
API_KEY = 'AIzaSyAz7ASJbZew8v09mdFjwG3z0_n8HhTB02I'

# This is the table id for the fusion table
TABLE_ID = '1ymz3EtGdi4qKGMl5AxEFXtTlgk3tKi8iCpjTzvM'

# This uses discovery to create an object that can talk to the 
# fusion tables API using the developer key
service = build('fusiontables', 'v1', developerKey=API_KEY)

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
        try: 
            rv = self.jinja2.render_template(_template, **values)
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            self.response.write(rv)
        except TemplateNotFound:
            self.abort(404)

# This is changed from Byte1 to subclass basehandler 
class MainHandler(BaseHandler):

    # Once again, get is responsible for returning the appropriate
    # information for display to the user (specifically for the default
    # landing page
    def get(self):
        """default landing page"""
        
        #data = self.get_all_data()

        data = [[{'x':0, 'y':35},
                 {'x':1, 'y':40}],
                [{'x':0, 'y':30}, 
                 {'x':1, 'y':20}]]
        context = {'data':json.encode(data),
                   'x_labels':['adopted', 'euthanized'],
                   'y_labels':['0-6m', '6m-1y']}
        
        #table = {'<6mo':0, '6mo-1yr':0, '1-7':0, '>7':0}
        # specify the ages we will search for
        ages = ['Infant - Younger than 6 months', 'Youth - Younger than 1 year', 'Older than 1 year', 'Older than 7 years']
        
        # specify the outcomes we will search for
        outcomes = ['Adopted', 'Euthanized', 'Foster', 'Returned to Owner', 'Transferred to Rescue Group']
    
        # set up the rest of the data table by counting up the number
        # of rows in each combination of age and outcome for each age
        # note that this is a lot of queries and takes about 30 seconds
        # to run. 
        for age in ages:
            # create a row to store the number of rows for each outcome
            row = []
            
            # and create a variable to store the total number of rows
            # for that age across all outcomes
            total = 0

            # for each outcome
            #for outcome in outcomes:

            # divide everything in the row by the total 
            # number of responses in that age across all outcomes
            # to get a percentage
            #row = [x/total for x in row]

            # add the row. We include [age] because the first
            # column of the data needs to have the label for each row 
            #data = data + [[age] + row]

        # log the result to make sure it looks correct
        #logging.info("data")
        #logging.info(data)

        # add it to the context being passed to jinja
        variables = {'data':json.encode(data)}

        # and render the response
        self.render_response('index.html', variables)
        
    # collect the data from google fusion tables
    # pass in the name of the file the data should be stored in
    def get_all_data(self):
        """ collect data from the server. """
        # limited to 10 rows
        query = "SELECT * FROM " + TABLE_ID + " WHERE  AnimalType = 'DOG' LIMIT 10"
        response = service.query().sql(sql=query).execute()
        logging.info(response)
        return response
            
      
        
# This specifies that MainHandler should handle a request to 
# jmankoff-byte2.appspot.com/
# This is where you would add additional handlers if you 
# wanted to have more subpages on that website.
app = webapp2.WSGIApplication([('/', MainHandler)], debug=True)
