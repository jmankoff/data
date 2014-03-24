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

credentials = AppAssertionCredentials(scope='https://www.googleapis.com/auth/bigquery.readonly')
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
        

        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            
            query     = {'query':'SELECT state, count(*) FROM [{0}] GROUP by state;'.format(_DATABASE_NAME), 'timeoutMs':10000}
            # service is the oauth2 setup that we created above
            jobRunner = service.jobs()
            # project number is the project number you should have 
            # defined in your app
            reply     = jobRunner.query(projectId=_PROJECT_NUMBER,body=query).execute()
            logging.info(reply)
        else:
            # open the data stored in a file called "data.json"
            try:
                fp = open("data/states.json")
                reply = simplejson.load(fp)
                # but if that file does not exist, download the data from fusiontables
            except IOError:
                logging.info("failed to load states.json file")

        # similar to the google SQL work we did in byte4, the stuff we 
        # care about is in rows
        rows = reply[u'rows']
        states = []
        for row in rows:
            name = row[u'f'][0][u'v']
            num = row[u'f'][1][u'v']
            if name == None: name = u'None'
            state = {'state':unicode.encode(name), 'total':int(num)}
            states = states + [state]

        logging.info(states)
        context = {"states": states}

        # and render the response
        self.render_response('index.html', context)


app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
