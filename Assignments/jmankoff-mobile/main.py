"""`main` is the top level module for your Flask application."""

# Imports
import os
import jinja2
import webapp2
import logging
import json
import urllib
import MySQLdb

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# Define your production Cloud SQL instance information.
_INSTANCE_NAME = 'your-project-id:your-instance-name'
_DB_NAME = 'your-db-name'
_USER = 'root' # or whatever other user account you created

if (os.getenv('SERVER_SOFTWARE') and
    os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
    _DB = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db=_DB_NAME, user=_USER, charset='utf8')
else:
    _DB = MySQLdb.connect(host='127.0.0.1', port=3306, db=_DB_NAME, user=_USER, charset='utf8')

    # Alternatively, connect to a Google Cloud SQL instance using:
    # _DB = MySQLdb.connect(host='ip-address-of-google-cloud-sql-instance', port=3306, user=_USER, charset='utf8')

# Import the Flask Framework
from flask import Flask, request
app = Flask(__name__)

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

@app.route('/')
def index():
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')

    cursor = _DB.cursor()
    cursor.execute('SHOW TABLES')
    
    logging.info(cursor.fetchall())
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

    # Takes the database link and the query as input
    def make_query(self, cursor, query):
        # this is for debugging -- comment it out for speed
        # once everything is working
        cursor.execute('set profiling = 1')
        try:
            # try to run the query
            cursor.execute(query)
            # and return the results
            return cursor.fetchall()

        except Exception:
            # if the query failed, log that fact
            logging.info("query making failed")
            # and get additional debugging information from mysql
            cursor.execute('show profiles')
            # and print them all to the log
            for row in cursor:
                logging.info(row)        
            cursor.execute('set profiling = 0')
            # finally, return an empty list of rows 
            return []

    # helper function to make a query and print lots of 
    # information about it. 
    def make_and_print_query(self, cursor, query, description):
        logging.info(description)
        logging.info(query)

        rows = self.make_query(cursor, query)
        for r in rows:
            logging.info('%s\n' % str(r))
        
    def bin_locations(self, locations, epsilon):
        # always add the first location to the bin
        bins = {1: [locations[0][0], locations[0][1]]}
        # this gives us the current maximum key used in our dictionary
        num_places = 1

        # now loop through all the locations 
        for location in locations:
            lat = location[0]
            lon = location[1]
            # assume that our current location is new for now (hasn't been found yet)
            place_found = False
            # loop through the bins 
            for place in bins.values():
                # check whether the distance is smaller than epsilon
                if self.distance_on_unit_sphere(lat, lon, place[0], place[1]) < epsilon:
                    #(lat, lon) is near  (place[0], place[1]), so we can stop looping
                    place_found = True
                    
            # we weren't near any of the places already in bins
            if place_found is False:
                logging.info("new place: {0}, {1}".format(lat, lon))
                # increment the number of places found and create a new entry in the 
                # dictionary for this place. Store the lat lon for comparison in the 
                # next round of the loop
                num_places = num_places + 1
                bins[num_places] = [lat, lon]

        return bins.values()
            
    def find_bin(self, bins, lat, lon, epsilon):
        for i in range(len(bins)):
            blat = bins[i][0]
            blon = bins[i][1]
            if self.distance_on_unit_sphere(lat, lon, blat, blon) < epsilon:
                return i
        bins.append([lat, lon])
        return len(bins)-1

    def group_activities_by_location(self, bins, locations, activities, epsilon):
        searchable_locations = {}
        for location in locations:
            # day, hour
            key = (location[0], location[1])
            if key in searchable_locations:
                                                    # lat,   lon 
                searchable_locations[key] = locations[key] + [(location[2], location[3])]
            else:
                searchable_locations[key] = [(location[2], location[3])]
        logging.info(searchable_locations)
                
        # a place to store activities for which we couldn't find a location
        # (indicates an error in either our data or algorithm)
        no_loc = []
        for activity in activities:
            # collect the information we will need 
            aday = activity[0] # day
            ahour = activity[1] # hour
            aname = activity[2] # name
            aduration = activity[3] # duration
            try: 
                possible_locations = searchable_locations[(aday, ahour)]
                # loop through the locations
                for location in possible_locations:
                    logging.info(" about to find bin")
                    logging.info(location[0])
                    logging.info(location[1])
                    bin = self.find_bin(bins, location[0], location[1], epsilon)
                    # and add the information to it
                    bins[bin] = bins[bin] + [aname, aduration]
            except KeyError:
                no_loc.append([aname, aduration])

        # add no_loc to the bins
        bins.append(no_loc)
    # this function is taken verbatim from http://www.johndcook.com/python_longitude_latitude.html

    def distance_on_unit_sphere(self, lat1, long1, lat2, long2):

        # Convert latitude and longitude to 
        # spherical coordinates in radians.
        degrees_to_radians = math.pi/180.0
        
        # phi = 90 - latitude
        phi1 = (90.0 - lat1)*degrees_to_radians
        phi2 = (90.0 - lat2)*degrees_to_radians
        
        # theta = longitude
        theta1 = long1*degrees_to_radians
        theta2 = long2*degrees_to_radians
        
        # Compute spherical distance from spherical coordinates.
        
        # For two locations in spherical coordinates 
        # (1, theta, phi) and (1, theta, phi)
        # cosine( arc length ) = 
        #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
        # distance = rho * arc length
        
        cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
               math.cos(phi1)*math.cos(phi2))
        # sometimes small errors add up, and acos will fail if cos > 1
        if cos>1: cos = 1
        arc = math.acos( cos )
        
        # Remember to multiply arc by the radius of the earth 
        # in your favorite set of units to get length.
        return arc
