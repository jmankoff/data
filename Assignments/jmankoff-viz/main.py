"""`main` is the top level module for your Flask application."""

# Visualization Byte Version 1
# 
# Copyright 1/2016 Jennifer Mankoff
#
# Licensed under GPL v3 (http://www.gnu.org/licenses/gpl.html)
#

# standard imports (same as other bytes)
# Imports -- similar to explore byte
import os
import jinja2
import webapp2
import logging
import json
import urllib
#from googleapiclient.discovery import build

#import MySQLdb
#import math
#import httplib2
from apiclient.discovery import build
#import numpy
#from django.utils import simplejson

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# This API key is provided by google as described in the tutorial
API_KEY = 'XXxxXxXXXXxxNXXxXXXxxxNNXXxxxxxxxXXXxXX'

# This is the table id for the fusion table
TABLE_ID = 'NxxxNXxXxxNxXXXXNXxXXXxXxxxNxXxNxXxxXxxX'

# This API key is provided by google as described in the tutorial
API_KEY = 'AIzaSyCpZ1iLD_Id7epHtnkEgAYTXsk2uBUtGkk'

# This is the table id for the fusion table
TABLE_ID = '1ymz3EtGdi4qKGMl5AxEFXtTlgk3tKi8iCpjTzvM'


# This uses discovery to create an object that can talk to the 
# fusion tables API using the developer key
service = build('fusiontables', 'v1', developerKey=API_KEY)

# This is the default columns for the query
query_cols = []
query_animals = ['DOG']

# Import the Flask Framework
from flask import Flask, request
app = Flask(__name__)

@app.route('/')
def index():
    data = get_all_data()
    columns = data['columns']
    rows = data['rows']
    
    # specify the ages we will search for
    age_mapping = {u'Infant - Younger than 6 months':'<6mo',
                   u'Youth - Younger than 1 year':'6mo-1yr',
                   u'Older than 1 year':'1yr-6yr',
                   u'Older than 7 years':'>7yr',
                   u'':'Unspecified'}
    # create an 'empty' array storing the number of dogs in each outcome
    
    # specify the outcomes we will search for
    outcomes = ['Adopted', 'Euthanized', 'Foster', 'Returned to Owner', 'Transferred to Rescue Group', 'Other']
    ages = ['<6mo', '6mo-1yr', '1yr-6yr', '>7yr', 'Unspecified']
    
    age_by_outcome = []
    for age in ages:
        res = {'Age': age}
        for outcome in outcomes:
            res[outcome] = 0
        age_by_outcome = age_by_outcome + [res]

    # find the column id for ages
    ageid = columns.index(u'Age')
    
    # find the column id for outcomes
    outcomeid = columns.index(u'Outcome')

    # loop through each row
    for row in rows: 
        # get the age of the dog in that row
        age = age_mapping[row[ageid]]
        # get the outcome for the dog in that row
        outcome = row[outcomeid]
        # if the age is a known value (good data) find
        # out which of the items in our list it corresponds to
        if age in ages: age_position = ages.index(age)
        # otherwise we will store the data in the 'Other' age column
        else: age_position = ages.index('Other')
        
        # if the outcome is a bad value, we call it 'Other' as well
        if outcome not in outcomes: outcome = 'Other'
        
        # now get the current number of dogs with that outcome and age
        outcomes_for_age = age_by_outcome[age_position]
        # and increase it by one
        outcomes_for_age[outcome] = outcomes_for_age[outcome] + 1

    logging.info(age_by_outcome)
    
    # add it to the context being passed to jinja
    variables = {'data':age_by_outcome,
                 'y_labels':outcomes,
                 'x_labels':ages}
    
    # and render the response
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')
    return template.render(variables)

@app.route('/about')
def about():
    template = JINJA_ENVIRONMENT.get_template('templates/about.html')
    return template.render()


@app.route('/quality')
def quality():
    template = JINJA_ENVIRONMENT.get_template('templates/quality.html')
    return template.render()

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404

@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500

# collect the data from google fusion tables
# pass in the name of the file the data should be stored in
def get_all_data():
    """ collect data from the server. """
    
    # open the data stored in a file called "data.json"
    try:
        fp = open("data/data.json")
        response = simplejson.load(fp)
        # but if that file does not exist, download the data from fusiontables
    except IOError:
        logging.info("failed to load file")
        service = build('fusiontables', 'v1', developerKey=API_KEY)
        query = "SELECT * FROM " + TABLE_ID + " WHERE  AnimalType = 'DOG'"
        response = service.query().sql(sql=query).execute()
        
    return response

