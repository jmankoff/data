import httplib2
from StringIO import StringIO
from apiclient.discovery import build
import urllib
import json
import csv
import matplotlib.pyplot as plt 
import numpy as np
import scipy.stats
from sklearn.naive_bayes import GaussianNB
from sklearn import tree
from sklearn import cross_validation
from sklearn import preprocessing
from sklearn import metrics
from sklearn.dummy import DummyClassifier

# This API key is provided by google as described in the tutorial
API_KEY = '... add your own ...'

# This is the table id for the fusion table
TABLE_ID = '... add your own ...'

# open the data stored in a file called "data.json"
try:
    fp = open("data/dogs.json")
    dogs = json.load(fp)
    fp = open("data/cats.json")
    cats = json.load(fp)

# but if that file does not exist, download the data from fusiontables
except IOError:
    service = build('fusiontables', 'v1', developerKey=API_KEY)
    query = "SELECT * FROM " + TABLE_ID + " WHERE  AnimalType = 'DOG'"
    dogs = service.query().sql(sql=query).execute()
    fp = open("data/dogs.json", "w+")
    json.dump(dogs, fp)
    query = "SELECT * FROM " + TABLE_ID + " WHERE  AnimalType = 'CAT'"
    cats = service.query().sql(sql=query).execute()
    fp = open("data/cats.json", "w+")
    json.dump(cats, fp)

#================================================================
# Statistics
#================================================================

# Checking whether a difference is significant
# Are cats returned to owners at the same rate as dogs (H0) 
# or is the difference significant (H1)

# first let's grab the data
n_groups = 2 # cats and dogs
outcome_types = ['Returned to Owner', 'Transferred to Rescue Group', 'Adopted', 'Foster', 'Euthanized']
outcome_labels = ['Owner', 'Rescue Group', 'Adopted', 'Foster', 'Euthanized', 'Other']
cat_outcomes = np.array([0.0,0,0,0,0,0])
dog_outcomes = np.array([0.0,0,0,0,0,0])

# loop through all of the rows of data
rows = dogs['rows'] # the actual data 

for dog in rows:
    # get the outcome for this dog
    outcome = dog[0]
    try:
        i = outcome_types.index(outcome)
        # one of outcome_types
        dog_outcomes[i] = dog_outcomes[i] + 1
    except ValueError:
        # everything else
        dog_outcomes[5] = dog_outcomes[5] + 1
rows = cats['rows'] # the actual data 
for cat in rows:
    # get the outcome for this cat
    outcome = cat[0]
    try:
        i = outcome_types.index(outcome)
        # one of outcome_types
        cat_outcomes[i] = cat_outcomes[i] + 1
    except ValueError:
        # everything else
        cat_outcomes[5] = cat_outcomes[5] + 1

print "cat_outcomes", cat_outcomes
print "dog_outcomes",  dog_outcomes

# plot the data to see what it looks like
fig, ax = plt.subplots()
index = np.arange(6)
bar_width = 0.35
opacity = 0.4
rects1 = plt.bar(index, dog_outcomes, bar_width, alpha=opacity, color='b', label='Dogs')
rects2 = plt.bar(index+bar_width, cat_outcomes, bar_width, alpha=opacity, color='r', label='Cats')
plt.ylabel('Number')
plt.title('Number of animals by animal type and outcome type')
plt.xticks(index + bar_width, outcome_labels)
plt.legend()
plt.tight_layout()
plt.show() 

# from this I'd say it looks like there's a real difference. 
# Let's do a significance test

# Step 1: alpha = .05
alpha = .05

# Step 2: define hypotheses: 
# Hypothesis 1: cat_outcomes = dog_outcomes
# Hypothesis 2: cat_outcomes != dog_outcomes

# Step 3: calculate the statistic (in this case
# we will have to use a ChiSquare test beacuse the
# data is nominal (non-parametric). Note that this returns
# a p value, so we don't need to determine the critical value
# here is a good explanation of ChiSquare tests: 
# http://stattrek.com/chi-square-test/independence.aspx
# this one too
# http://udel.edu/~mcdonald/statchiind.html

Observed = np.array([cat_outcomes, dog_outcomes])
X_2, p, dof, expected= scipy.stats.chi2_contingency(Observed)
print "X_2", X_2, ", p", p

# Step 4: State decision rule 
# Hypothesis 1 is rejected if p < alpha
# Hypothesis 2 is rejected if p > alpha

# Step 5: State conclusion:
if (p < alpha):
    print "The difference is significant. H0 (cats and dogs have the same outcomes) is rejected." 
else:
    print "The difference is not significant. H1 (cats and dogs have different outcomes) is rejected."

# =====================================================================
# Now do something similar for animals under one year of age
# =====================================================================

# first let's grab the data

# organize the data into outcome arrays for each age type

# plot the data to see what it looks like

# Step 1: alpha = .05
alpha = .05

# Step 2: define hypotheses (something like this):
# Hypothesis 1: young_outcomes = old_outcomes = unkwnown_outcomes
# Hypothesis 2: something is different

# Step 3: calculate the statistic (in this case
# we will have to use a ChiSquare test beacuse the
# data is nominal (non-parametric). Note that this returns
# a p value, so we don't need to determin the critical value

# Step 5: State decision rule 
# Hypothesis 1 is rejected if p < alpha
# Hypothesis 2 is rejected if p > alpha

# Step 6: State conclusion:

#================================================================
# Machine Learning
#================================================================
# We want to store the complete data set to disk 
# beacuse we need to randomize the order and we don't
# want to have the random order change every time we 
# run this program. This is especially important because
# if we re randomize every time the optimization set will
# be different every time which will add bias to our results
try:
    fp = open("data/random_dogs_and_cats.json")
    all_data = np.array(json.load(fp))

# but if that file does not exist, download the data from fusiontables
except IOError:
# make an array of all data about cats and dogs
    all_data = cats['rows'] + dogs['rows']
    # randomize it so the cats aren't all first
    np.random.shuffle(all_data)
    fp = open("data/random_dogs_and-cats.json", "w+")
    json.dump(all_data, fp)
    all_data = np.array(all_data)

# We'd like to use both dogs and cats, and we'll want to use several different
# features (not just the two we were playing with)

# For a first pass, these are likely to be useful features
# I'm avoiding actual dates because they are hard to parse
# and I'm avoiding anything to do with the outcome  (such as outcome date)
# as that might bias the results
# It may be important to calculate features based on these though
# such as something that deals better with mixed breeds to improve the results

# IMPORTANT NOTE: make sure these appear in this array in the same order as they
# do in the columns array (this will help with labeling later in the machine
# learning work)
features = ['AnimalType', 'IntakeMonth', 'Breed', 'Age', 'Sex', 'SpayNeuter',
            'Size', 'Color', 'IntakeType']
# this will be the class we are predicting.
# We will need to narrow it down to fewer classes probably
out = 'Outcome'

# the column names are the same for cats and dogs. Pick one
# to work with
cols = cats['columns']

# make a new, empty array that will store
# for each column we should use
use_data = []

# and loop through the columns
ncols = len(cols)
for i in np.arange(ncols):
    try: 
        # we want to use a column 
        # if its name is in the list of features we want to keep
        features.index(cols[i])
        use_data.append(i)
    except ValueError:
        # and if it matches the name of the column we are predicting
        # ('Outcome') we capture the column index for later
        if cols[i] == out:
            out_index = i

# Now we create a new array that only has the columns we care about in it
X = all_data[:, use_data]
# This is just the column with the outcome values
y = all_data[:, out_index]

# Make all the outcomes that are very rare be "Other"
y[y=="No Show"] = "Other"
y[y=="Missing Report Expired"] = "Other"
y[y=="Found Report Expired"] = "Other"
y[y=="Lost Report Expired"] = "Other"
y[y=="Released in Field"] = "Other"
y[y==''] = "Other"
y[y=="Died"] = "Other"
y[y=="Disposal"] = "Other"
y[y=="Missing"] = "Other"
y[y=="Trap Neuter/Spay Released"] = "Other"
y[y=="Transferred to Rescue Group"] = "Other"
y[y==u'Foster']="Other"

# Leave the following outcomes as separate (may want to 
# combine some of these to reduce the number of classes 
# and improve the results) 
# Returned to Owner; Adopted; Euthanized
y[y=="Returned to Owner"] = "Home"
y[y==u'Adopted']="Home"
y[y==u'Euthanized']="Euthanized"
# So for now we have 5 classes total: Other, Foster, Owner, Adopted, Euthanized
Outcomes = ["Euth.", "Home", "Other"]

# We'll use the first 20%. This is fine
# to do because we know the data is randomized.
nrows = len(all_data)
percent = len(X)/5
X_opt = X[:percent, :]
y_opt = y[:percent]

# and a train/test set
X_rest = X[percent:, :]
y_rest = y[percent:]

# ======================================================
# print out files for orange if you want to use that
# ======================================================

X_opt_for_orange = np.insert(X_opt, len(features), y_opt, axis=1)
with open("data/orange_opt.csv", "w+") as csvfile:
    datawriter = csv.writer(csvfile, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
    datawriter.writerow(features + ["Class"])
    for row in X_opt_for_orange:
        datawriter.writerow(row)


import csv
with open("data/orange_rest.csv", "w+") as csvfile:
    datawriter = csv.writer(csvfile, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
    datawriter.writerow(features + ["Class"])
    for row in X_rest:
        datawriter.writerow(row)


# ======================================================
# use scikit-learn
# ======================================================

# and we need to convert all the data from strings to numeric values
le = preprocessing.LabelEncoder()
labels = []
le
# collect all the labels. The csv files we are loading 
# were generated back in byte 2 and are provided as part
# of this source code. They just contain all possible
# values for each column. We're putting those values all
# in a list now
for name in features:
    csvfile = open('data/{0}.csv'.format(name), 'rb')
    datareader = csv.reader(csvfile, delimiter=',')
    for row in datareader:
        labels.append(row[0])
# make a label for empty values too
labels.append(u'')
le.fit(labels)

# now transform the array to have only numeric values instead
# of strings
X = le.transform(X)

# Lastly we need to split these into a optimization set
# using about 20% of the data
nrows = len(all_data)
percent = len(X)/5

# We'll use the first 20%. This is fine
# to do because we know the data is randomized.
X_opt = X[:percent, :]
y_opt = y[:percent]

# and a train/test set
X_rest = X[percent:, :]
y_rest = y[percent:]

dc = DummyClassifier(strategy='most_frequent',random_state=0)
gnb = GaussianNB()
# you could try other classifiers here

# make a set of folds
skf = cross_validation.StratifiedKFold(y_opt, 10)
gnb_acc_scores = []
dc_acc_scores = []

# loop through the folds
for train, test in skf:
    # extract the train and test sets
    X_train, X_test = X_opt[train], X_opt[test]
    y_train, y_test = y_opt[train], y_opt[test]
    
    # train the classifiers
    dc = dc.fit(X_train, y_train)
    gnb = gnb.fit(X_train, y_train)

    # test the classifiers
    dc_pred = dc.predict(X_test)
    gnb_pred = gnb.predict(X_test)

    # calculate metrics relating how well they did
    dc_accuracy = metrics.accuracy_score(y_test, dc_pred)
    dc_precision, dc_recall, dc_f, dc_support = metrics.precision_recall_fscore_support(y_test, dc_pred)
    gnb_accuracy = metrics.accuracy_score(y_test, gnb_pred)
    gnb_precision, gnb_recall, gnb_f, gnb_support = metrics.precision_recall_fscore_support(y_test, gnb_pred)

    # print the results for this fold
    print "Accuracy "
    print "Dummy Cl: %.2f" %  dc_accuracy
    print "Naive Ba: %.2f" %  gnb_accuracy
    print "F Score"
    print "Dummy Cl: %s" % dc_f
    print "Naive Ba: %s" % gnb_f
    print "Precision", "\t".join(list(Outcomes))
    print "Dummy Cl:", "\t".join("%.2f" % score for score in  dc_precision)
    print "Naive Ba:", "\t".join("%.2f" % score for score in  gnb_precision)
    print "Recall   ", "\t".join(list(Outcomes))
    print "Dummy Cl:", "\t".join("%.2f" % score for score in  dc_recall)
    print "Naive Ba:", "\t".join("%.2f" % score for score in  gnb_recall)

    dc_acc_scores = dc_acc_scores + [dc_accuracy]
    gnb_acc_scores = gnb_acc_scores + [gnb_accuracy]

diff = np.mean(dc_acc_scores) - np.mean(gnb_acc_scores)
t, prob = scipy.stats.ttest_rel(dc_acc_scores, gnb_acc_scores)

print "============================================="
print " Results of optimization "
print "============================================="
print "Dummy Mean accuracy: ", np.mean(dc_acc_scores)
print "Naive Bayes Mean accuracy: ", np.mean(gnb_acc_scores)
print "Accuracy for Dummy Classifier and Naive Bayes differ by {0}; p<{1}".format(diff, prob)

print "These are good summary scores, but you may also want to" 
print "Look at the details of what is going on inside this"
print "Possibly even without 10 fold cross validation"
print "And look at the confusion matrix and other details"
print "Of where mistakes are being made for developing insight"

print "============================================="
print " Final Results "
print "============================================="
print "When you have finished this assignment you should"
print "train a final classifier using the X_rest and y_rest"
print "using 10-fold cross validation"
print "And you should print out some sort of statistics on how it did"
