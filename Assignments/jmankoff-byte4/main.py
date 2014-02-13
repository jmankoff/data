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
import logging
# make sure to add this to app.yaml too
from webapp2_extras import jinja2

# new imports for database access
import MySQLdb
from google.appengine.ext import db

# new import for checking whether we are running on localhost or remotely
import os

# new import for doing math operations
import math


# Define your production Cloud SQL instance information. 
_INSTANCE_NAME = 'jmankoff-byte4:aware'
# database name
_DB = 'byte4'
# the table where messages show up
_MQTT = 'mqtt_messages'
# the table where activities are logged
_ACTIVITY = 'plugin_google_activity_recognition'
# the table where locations are logged
_LOCATIONS = 'locations'
# the distance that determins new locations
_EPSILON = .001

# This is the id for Jen's phone. Replace it with your own id if you have a phone up and
# running. 
_ID = '785434b8-ce03-46a2-b003-b7be938d5ff4'


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

class MainHandler(BaseHandler):

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

                
    def get(self):
        """default landing page"""

        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            db = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db=_DB, user='root')
            cursor = db.cursor()

            logging.info("making queries")
            
            # some sample queries that will write examples of the sort of
            # data we have collected to the log so you can get a sense of things
            self.make_and_print_query(cursor, 'SHOW TABLES', 'Show the names of all tables')
            self.make_and_print_query(cursor, 'SELECT DISTINCT device_id FROM locations', 'List all device ids')
            self.make_and_print_query(cursor, "SELECT * FROM mqtt_messages  WHERE device_id = '{0}' LIMIT 10".format(_ID), 'Example contents of mqtt_messages')
            self.make_and_print_query(cursor, "SELECT * FROM plugin_google_activity_recognition WHERE device_id = '{0}' LIMIT 10 ".format(_ID), 'Example contents of plugin_google_activity_recognition')
            self.make_and_print_query(cursor, "SELECT * FROM locations  WHERE device_id = '{0}' LIMIT 10".format(_ID), 'Example contents of locations')
            

            # this query collects information about the number
            # of log enteries for each day. 
            day = "FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d')"
            query = "SELECT {0} as day_with_data, count(*) as records FROM {1} WHERE device_id = '{2}' GROUP by day_with_data".format(day, _LOCATIONS, _ID)

            rows = self.make_query(cursor, query)
            queries = [{"query": query, "results": rows}]

            # this query lets us collect information about 
            # locations that are visited so we can bin them. 
            query = "SELECT double_latitude, double_longitude FROM {0} WHERE device_id = '{1}'".format(_LOCATIONS, _ID)
            locations = self.make_query(cursor, query)
            #locations = self.make_and_print_query(cursor, query, "locatons")
            bins = self.bin_locations(locations, _EPSILON)
            for location in bins:
                logging.info('%s\n' % str(location))
                
            queries = queries + [{"query": query, "results": bins}]

            # now get locations organized by day and hour 
            time_of_day = "FROM_UNIXTIME(timestamp/1000,'%H')"
            day = "FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d')"
            query = "SELECT {0} as day, {1} as time_of_day, double_latitude, double_longitude FROM {2} WHERE device_id = '{3}' GROUP BY day, time_of_day".format(day, time_of_day, _LOCATIONS, _ID)
            locations = self.make_query(cursor, query)
            
            # and get physical activity per day and hour
            # activity name and duration in seconds
            day_and_time_of_day = "FROM_UNIXTIME(timestamp/100, '%Y-%m-%d %H')"
            elapsed_seconds = "(max(timestamp)-min(timestamp))/1000"
            query = "SELECT {0} as day, {1} as time_of_day, activity_name, {2} as time_elapsed_seconds FROM  {3} WHERE device_id = '{4}' GROUP BY day, activity_name, {5}".format(day, time_of_day, elapsed_seconds, _ACTIVITY, _ID, day_and_time_of_day)

            activities = self.make_query(cursor, query)

            # now we want to associate activities with locations. This will update the
            # bins list with activities.
            self.group_activities_by_location(bins, locations, activities, _EPSILON)

            db.close()

        else:
            queries = [{"query": 'Need to connect from Google Appspot', "results": []}]
            
        context = {"queries": queries}

        logging.info("context")
        logging.info(context)

        # and render the response
        self.render_response('index.html', context)


app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
