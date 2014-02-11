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
import logging

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

            try:
                cursor.execute('set profiling = 1')

                self.response.write('SHOW TABLES')
                cursor.execute('SHOW TABLES')
                for r in cursor.fetchall():
                    self.response.write('%s\n' % str(r))
                self.response.write('\n')

                self.response.write('SELECT * FROM mqtt_messages LIMIT 20')
                cursor.execute('SELECT * FROM mqtt_messages LIMIT 20')
                for r in cursor.fetchall():
                    self.response.write('%s\n' % str(r))
                self.response.write('\n')

                self.response.write('SELECT * FROM plugin_google_activity_recognition LIMIT 20')
                cursor.execute('SELECT * FROM plugin_google_activity_recognition LIMIT 20')
                for r in cursor.fetchall():
                    self.response.write('%s\n' % str(r))
                self.response.write('\n')

                self.response.write('SELECT * FROM plugin_mode_of_transportation LIMIT 20')
                cursor.execute('SELECT * FROM plugin_mode_of_transportation LIMIT 20')
                for r in cursor.fetchall():
                    self.response.write('%s\n' % str(r))
                self.response.write('\n')

                self.response.write('SELECT * FROM locations LIMIT 20')
                cursor.execute('SELECT * FROM locations LIMIT 20')
                for r in cursor.fetchall():
                    self.response.write('%s\n' % str(r))
                self.response.write('\n')

                cursor.execute("SELECT from_unixtime(locations.timestamp/1000,'%Y-%m-%d') as day_with_data, count(*) as records FROM locations GROUP by day_with_data;")
                self.response.write("#Days with data from location data")
                for r in cursor.fetchall():
                    self.response.write('%s\n' % str(r))
                self.response.write('\n')

                day = "FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d')"
                time_of_day = "FROM_UNIXTIME(timestamp/1000,'%H:%i')"
                table = "locations"
                query = "SELECT {0} as day, {1} as time_of_day, double_latitude, double_longitude FROM {2} GROUP BY day, time_of_day".format(day, time_of_day, table)
                self.response.write(query)
                cursor.execute(query)
                for r in cursor.fetchall():
                    self.response.write('%s=n' % str(r))
                self.response.write('\n')
                
                # physical activity per day, time of day (granularity of minutes), 
                # activity name and time in seconds
                day_and_time_of_day = "FROM_UNIXTIME(timestamp/100, '%Y-%m-%d %H:%i'"
                elapsed_seconds = "(max(timestamp)-min(timestamp))/1000"
                table = plugin_google_activity_recognition
                query = "SELECT {0} as day, {1} as time_of_day, activity_name, {2} as time_elapsed_seconds FROM  {3} GROUP BY day, activity_name, {4}".format(day, time_of_day, time_elapsed_seconds, table, day_and_time_of_day)
                self.response.write(query)
                #cursor.execute(query)
                #for r in cursor.fetchall():
                #self.response.write('%s=n' % str(r))
                self.response.write('\n')
            
                # physical activity per day, time of day (granularity of hour),
                # activity name and time in seconds
                # - maybe this one is more useful :)
                query = "SELECT {0} as day, {1} as time_of_day, activity_name, {2}  as time_elapsed_seconds FROM {3}  GROUP BY day, activity_name, {4}".format(day, time_of_day, time_elapsed_seconds, table, day_and_time_of_day)
                self.response.write(query)
                #cursor.execute(query)
                #for r in cursor.fetchall():
                #self.response.write('%s=n' % str(r))
                self.response.write('\n')

            except Exception:
                cursor.execute('show profiles')
                for row in cursor:
                    logging.info(row)        
                    cursor.execute('set profiling = 0')

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
