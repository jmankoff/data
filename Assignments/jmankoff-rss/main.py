"""`main` is the top level module for your Flask application."""

# Imports
import os
import jinja2
import webapp2
import feedparser
import logging

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# Import the Flask Framework
from flask import Flask, request
app = Flask(__name__)

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

@app.route('/')
def index():
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')
    feed = feedparser.parse("http://www.bing.com/search?q=dog&format=rss")

    # loop through the items in the feed to log them
    for item in feed[ "items" ]:
        logging.info(item)
    # loop through the items in the feed again to collect them in a data
    # object to pass to the index.html template
    data = [{"link":item.link, "title":item.title, "description":item.summary_detail} for item in feed["items"]]

    # log the data for debugging purposes
    logging.info(data)

    # render the web page with the data 
    return template.render(feed=data)

    
@app.route('/about')
def about():
    template = JINJA_ENVIRONMENT.get_template('templates/about.html')
    return template.render()

@app.route('/search', methods=['POST'])
def search():
    term = request.form["search_term"]
    logging.info(term)

    template = JINJA_ENVIRONMENT.get_template('templates/index.html')

    # creating the bing search url and collecting the data from it
    url = "http://www.bing.com/search?q=" + term + "&format=rss"
    feed = feedparser.parse(url)
    logging.info(url)

    # same as in '/'
    for item in feed[ "items" ]:
        logging.info(item)
    data = [{"link":item.link, "title":item.title, "description":item.summary_detail} for item in feed["items"]]
    logging.info(data)
    return template.render(feed=data)

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500
