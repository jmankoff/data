import httplib2
from apiclient.discovery import build
import urllib
import json
import csv
import matplotlib.pyplot as plt 


# This API key is provided by google as described in the tutorial
API_KEY = '... add your own ...'

# This is the table id for the fusion table
TABLE_ID = '... add your own ...'

# open the data stored in a file called "data.json"
try:
    fp = open("data.json")
    response = json.load(fp)

# but if that file does not exist, download the data from fusiontables
except IOError:
    service = build('fusiontables', 'v1', developerKey=API_KEY)
    query = "SELECT * FROM " + TABLE_ID + " WHERE  AnimalType = 'DOG'"
    response = service.query().sql(sql=query).execute()
    fp = open("data.json", "w+")
    json.dump(response, fp)
    

# this will be our summary of the data. For each column name, it will store
# a dictionary containing the number of occurences of each possible
# value for that column in the data. For example, for gender, 
# the possible values are "MALE" and "FEMALE" and "UNKNOWN"
# summary will contain {"MALE": 5199, "FEMALE": 4354, "UNKNOWN":82} 
# indicating that in the data, 5199 rows are marked as MALE, 
# 4354 rows are marked as FEMALE and 82 rows are marked as UNKNOWN
summary = {} 
columns = response['columns'] # the names of all columns
rows = response['rows'] # the actual data 

# how many rows are in the data we downloaded?
# this should be the same as in the fusion table
print len(rows)

# we'll ignore some columns because they are
# not useful for our analysis (such as AnimalID and Name which
# are unique for every animal
ignore = [u'AnimalID', u'AnimalType', u'Name', u'IconName', u'icon type']

# now we want to summarize the data to facilitate exploration. To do 
# so we will collect information about each *column* in the spreadsheet
for i in range(0, len(columns)):  # loops through each column

    # skip the rest of this loop if it's an ignore column
    if columns[i] in ignore: continue 

    # will store unique values for this column
    column_values = {} 
    # the name for this column
    column_name = columns[i]

    # loop through all of the rows of data
    for row in rows:
        # get the value stored for this column in this row
        value = row[i]
        
        # convert any string values to ascii, and any empty strings 
        # to a string called 'EMPTY' we can use as a value
        if type(value) is unicode: value = row[i].encode('ascii','ignore') 
        if value == '': value = 'EMPTY'
        if value == 'NaN' : value = 'EMPTY'
        
        # increase the count the value already exists
        try:               
            column_values[value] = column_values[value] + 1

        # or set it to 1 if it does not exist
        except KeyError:  
            column_values[value] = 1

    # to facilitate exploration we want to also write our summary
    # information for each column to disk in a csv file
    fc = open("{0}.csv".format(column_name), "w+")
    cwriter = csv.writer(fc)
    cwriter.writerow(["name", "amount"])

    # store the result in summary
    summary[column_name] = column_values   


# we also want to write summary information for the whole data set
# containing the name of each column, the max rows in any value for that column
# the min rows, the number of rows without a value, and the number of 
# values only present in a single row ('unique')
fp = open("summary.csv", "w+")
headers = ["name", "max", "min", "empty", "unique"] 
writer = csv.writer(fp)
dict_writer = csv.DictWriter(fp, headers)
writer.writerow(headers)

# to collect that data, we need to loop through the summary
# data we just created for each column. column_name is the column name,
# details is the dictionary containing {column_value: numrows,  ...}
for column_name, details in summary.iteritems():
    # rowcounts is a list containing the numrows numbers, but 
    # no column value names
    rowcounts = details.values()
    max_count = max(rowcounts)
    min_count = min(rowcounts)

    # we also want to know specifically how many rows had no
    # entry for this column
    try: 
        emptyrowcounts = details["EMPTY"]
    # and that throws an error, we know that no rows were empty
    except KeyError:
        emptyrowcounts = 0

    # for a sanity check we print this out to the screen
    print("column {0} has {1} different keys of which the 'EMPTY' key holds {2} values".format(column_name, len(details), emptyrowcounts))

    # we can also calculate fun things like the number of 
    # column values associated with only a single row
    unique = 0
    for numrows in details.itervalues():
        if numrows == 1:
            unique = unique + 1


    # as a second sanity check, let's write this out to a csv summary file
    row = {"name": column_name, "max": max_count, "min": min_count, "empty": emptyrowcounts, 
           "unique":unique}
    dict_writer.writerow(row)

    # now we will write this all to a csv file:
    # we loop through the different possible
    # column values, and write out how many rows
    # had that value. 
    for column_value, numrows in details.iteritems():
        # and write just the values for this out as a csv file
        fc = open("{0}.csv".format(column_name), "a+")
        kdict_writer = csv.DictWriter(fc, ["name", "amount"])
        kdict_writer.writerow({"name":column_value, "amount":numrows})


# some of the data is numeric -- especially the latituted, longitude,
# zipfound, and zipplaced. You might also explore the data
# about, for example, month found/placed numerically (are some months
# likely to have more strays or placements than others?). You could
# even parse the date data and look at for example the impact of 
# day of week. The code below shows some ways of visualizing 
# latitude and longitude only. 
    
latitude = summary['Latitude']

# need to replace the "EMPTY" key with a numeric value for plotting
latitude[0] = latitude['EMPTY']
del latitude['EMPTY']

latitude = dict((float(k), v) for k, v in latitude.iteritems())

# make a bar plot of all the latitudes we found
plt.bar(latitude.keys(), latitude.values())
plt.show()

# you may want to explore other visualizations
# such as a histogram or other aspects of the data 
# including other columns

