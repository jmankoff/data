"""`main` is the top level module for your Flask application."""

# Imports
import os
import jinja2
import webapp2
import logging
import json
import urllib

# this is used for constructing URLs to google's APIS
from googleapiclient.discovery import build

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

API_KEY = 'XXxxXxXXXXxxNXXxXXXxxxNNXXxxxxxxxXXXxXX'

# This uses discovery to create an object that can talk to the 
# fusion tables API using the developer key
service = build('fusiontables', 'v1', developerKey=API_KEY)

TABLE_ID = 'NxxxNXxXxxNxXXXXNXxXXXxXxxxNxXxNxXxxXxxX'

# Import the Flask Framework
from flask import Flask, request
app = Flask(__name__)

def get_all_data():
    query = "SELECT * FROM " + TABLE_ID + " WHERE  AnimalType = 'DOG' LIMIT 2"
    response = service.query().sql(sql=query).execute()
    logging.info(response['columns'])
    logging.info(response['rows'])
        
    return response

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

@app.route('/')
def index():
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')
    request = service.column().list(tableId=TABLE_ID)
    logging.info(request)
    logging.info(get_all_data())
    return template.render()

    
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
