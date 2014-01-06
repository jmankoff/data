#!/usr/bin/env python
#
# Byte 1 Version 1
# 
# Copyright 11/2013 Jennifer Mankoff
#
# Licensed under GPL v3 (http://www.gnu.org/licenses/gpl.html)
#

# this import is part of all google webapps
import webapp2

# this import is for logging
import logging

# this one is to help us parse an RSS feed
import feedparser  

# this is for displaying HTML
from webapp2_extras import jinja2

# this is for encoding the search terms
import urllib

# BaseHandler subclasses RequestHandler so that we can use jinja
class BaseHandler(webapp2.RequestHandler):
    
    @webapp2.cached_property
    def jinja2(self):
        # Returns a Jinja2 renderer cached in the app registry.
        return jinja2.get_jinja2(app=self.app)
        
    # This will call self.response.write using the specified template and context.
    # The first argument should be a string naming the template file to be used. 
    # The second argument should be a pointer to an array of context variables
    #  that can be used for substitutions within the template
    def render_response(self, _template, **context):
        # Renders a template and writes the result to the response.
        rv = self.jinja2.render_template(_template, **context)
        self.response.write(rv)

# Class MainHandler now subclasses BaseHandler instead of webapp2
class MainHandler(BaseHandler):

    # This method should return the html to be displayed
    def get(self):
        """default landing page"""
        
        # This is the url for the yahoo pipe created in our tutorial. It searches 
        # (by default) for dogs.
        feed = feedparser.parse("http://pipes.yahoo.com/pipes/pipe.run?_id=1nWYbWm82xGjQylL00qv4w&_render=rss&textinput1=dogs" )
        
        # this sets up feed as a list of dictionaries containing information 
        # about the RSS feed using a for loop
        feed = [{"link": item.link, "title":item.title, "description" : item.description} for item in feed["items"]]

        # now we place the feed in context and provide the default search term
        context = {"feed" : feed, "search" : "dog"}
        
        # here we call render_response instead of self.response.write
        # this sends the context and the file to render to jinja2 
        self.render_response('index.html', **context)

    # here we handle the results of the form
    def post(self):

        # this retrieves the contents of the search term 
        terms = self.request.get('search_term')

        # and converts it to a safe format for use in a url 
        terms = urllib.quote(terms)

        # NOTE: we are now repeating (almost verbatim) things from 
        # the get method. It would be better to create and call a helper method
        # that retrieves and constructs the feed given search terms.
        # This is left as an exercise to the reader. 

        # now we construct the url for the yahoo pipe created in our tutorial
        # (you will want to replace this with your own url), using the search 
        # terms provided by the user in the form
        feed = feedparser.parse("http://pipes.yahoo.com/pipes/pipe.run?_id=1nWYbWm82xGjQylL00qv4w&_render=rss&textinput1=" + terms )
        
        # this sets up feed as a list of dictionaries containing information 
        feed = [{"link": item.link, "title":item.title, "description" : item.description} for item in feed["items"]]

        # this sets up the context with the user's search terms and the search
        # results in feed
        context = {"feed": feed, "search": terms}

        # this sends the context and the file to render to jinja2
        self.render_response('index.html', **context)

# this sets up the correct callback for [yourname]-byte1.appspot.com
# This is where you would add additional handlers if you 
# wanted to have more subpages on that website.
app = webapp2.WSGIApplication([('/.*', MainHandler)], debug=True)



