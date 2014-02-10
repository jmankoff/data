#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
from google.appengine.api import files
from google.appengine.ext import db
import MySQLdb
import os


# Define your production Cloud SQL instance information.
_INSTANCE_NAME = 'jmankoff-byte4:aware'
_DB = 'byte4'
_MQTT = 'mqtt_messages'
_ACTIVITY = 'plugin_google_activity_recognition'
_TRANSPORTATION = 'plugin_mode_of_transportation'

class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'

        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            db = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db=_DB, user='root')
            cursor = db.cursor()
            cursor.execute('SHOW TABLES')
            for r in cursor.fetchall():
                self.response.write('%s\n' % str(r))
            cursor.execute('SELECT * FROM mqtt_messages LIMIT 200')
            for r in cursor.fetchall():
                self.response.write('%s\n' % str(r))

            cursor.execute('SELECT * FROM plugin_google_activity_recognition LIMIT 200')
            for r in cursor.fetchall():
                self.response.write('%s\n' % str(r))

            cursor.execute('SELECT * FROM plugin_mode_of_transportation LIMIT 200')
            for r in cursor.fetchall():
                self.response.write('%s\n' % str(r))


            cursor.execute('SELECT * FROM locations LIMIT 200')
            for r in cursor.fetchall():
                self.response.write('%s\n' % str(r))

            cursor.execute("SELECT from_unixtime(locations.timestamp/1000,'%Y-%m-%d') as day_with_data, count(*) as records FROM locations GROUP by day_with_data;")
            self.response.write("#Days with data from location data")
            for r in cursor.fetchall():
                self.response.write('%s\n' % str(r))

            self.response.write("#activity per day")
            cursor.execute("SELECT FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d') as day, activity_name, (max(timestamp)-min(timestamp))/1000 FROM_UNIXTIME(timestamp/1000, '%Y-%m-%d %H:%i') as time_elapsed_seconds FROM plugin_google_activity_recognition ORDER BY FROM_UNIXTIME(timestamp/1000, '%Y-%m-%d %H:%i');")
            for r in cursor.fetchall():
                self.response.write('%s\n' % str(r))

            db.close()
        else:
            self.response.write('Need to connect from Google Appspot')
            #db = MySQLdb.connect(host='127.0.0.1', port=3306, user='root')
            # Alternately, connect to a Google Cloud SQL instance using:
            #db = MySQLdb.connect(host='ip-address-of-google-cloud-sql-instance', port=3306, user='root')

        

#        db = MySQLdb.connect(host='epiwork.hcii.cs.cmu.edu', user='byte4', passwd='DaTaB4', db='byte4' )





app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
