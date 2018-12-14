# -*- coding: utf-8 -*-
"""Accuracy_Error_Analysis_AC_multilabel_CNN

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1fKt0M9PzFtrntgP4XSPIZoULRIK3hVt3
"""

from google.colab import drive
drive.mount('/content/drive')

import os, random, operator, sys
import collections
import math
import pandas as pd
import numpy as np
import csv
import re

############################################################
##  Related to data preparation
############################################################

MAX_MONEY = 1.5*10**9    # financial info, for reference
MIN_MONEY = 10**4
NUM_MONEY_BUCKETS = 10

def prepare_raw_WB_project_data():
	wb_small = pd.read_csv('WBsubset.csv')
	wb_small = wb_small[['sector1','sector2', 'sector3', 'sector4', 'sector5', 'sector', 'mjsector1','mjsector2', 'mjsector3', 'mjsector4', 'mjsector5', 'mjsector','Country','project_name', 'totalamt', 'grantamt']]
	return wb_small.fillna('')


def clean_sector_string(sector_string):
	sector_string = str(sector_string)
	if sector_string == 'nan':
		return []
	to_return = []
	sec = sector_string.split(';')
	for y in sec:
		to_add = re.sub(r'!\$!\d*!\$!\D\D', "", y)
		to_add = re.sub(r'\(.*\)', "", to_add)
	if to_add:
		if to_add[0] == " ":
			to_add = to_add[1:]
		to_return.append(to_add)
	return to_return


def prepare_clean_WB_project_data(df):
	"""
		Returns a list of tuples, where the tuples are
		(project_name, [countries], [sectors], finance) for every datapoint
	"""
	clean_data = []
	for index, x in df.iterrows():
		clean_sectors = clean_sector_string(x['sector1'])+clean_sector_string(x['sector2'])+clean_sector_string(x['sector3'])+clean_sector_string(x['sector4'])+clean_sector_string(x['sector5'])+clean_sector_string(x['sector'])+clean_sector_string(x['mjsector1'])+clean_sector_string(x['mjsector2'])+clean_sector_string(x['mjsector3'])+clean_sector_string(x['mjsector4'])+clean_sector_string(x['mjsector5'])+clean_sector_string(x['mjsector'])
		clean_countries = list(set(x['Country'].split(';')))
		clean_money = int(x['totalamt']) + int(x['grantamt'])
		clean_tuple = (x['project_name'], clean_countries, clean_sectors, clean_money)
		clean_data.append(clean_tuple)
	return clean_data


def prepare_2016_17_data(): 
	""" 
		Returns a list of tuples, where the tuples are 
		([countries], [sectors], [issues], finance) for every datapoint
	"""
	df = pd.read_csv('2016_17_complaints.csv')
	df = df.fillna('')
	df = pd.DataFrame({'Country': df['Country'], 'Finance': df['Money'], 'Issues': df['Issues'], 'Sector': df['Sector']})
	clean_data = [] 
	# clean data
	for index, x in df.iterrows():
		country = (x['Country'].split('/'))
		finance = (x['Finance'])
		issue = ([y.lstrip().rstrip() for y in str(x['Issues']).replace('Unknown', 'Other').replace('Extractives (oil, gas, mining)', 'Extractives (oil/gas/mining)').replace(', ', ',').replace(',', ';').split(';')])
		sector = (x['Sector'].split(';'))
		if country or finance or issue or sector:
			clean_tuple = (country, sector, issue,finance)
			clean_data.append(clean_tuple)
	return clean_data

def prepare_raw_complaint_data(): 
		""" 
				Slice relevant columns for country, sector, and issue
				and returns master complaint csv for project purposes.
		"""
		df = pd.read_csv('complaints.csv')
		df = df[['Country', 'Sector/Industry (1)','Sector/Industry (2)',
				 'Issue Raised (1)','Issue Raised (2)', 'Issue Raised (3)', 
				 'Issue Raised (4)','Issue Raised (5)', 'Issue Raised (6)', 
				 'Issue Raised (7)', 'Issue Raised (8)', 'Issue Raised (9)', 
				 'Issue Raised (10)']]
		return df.fillna('')



def prepare_clean_complaint_data(df):
	""" 
		Returns a list of tuples, where the tuples are 
		([countries], [sectors], [issues]) for every datapoint
	"""
	clean_data = [] 
	for index, x in df.iterrows():
		clean_sectors = filter(None,x['Sector/Industry (1)'].split('|')+x['Sector/Industry (2)'].split('|'))
		clean_issues = filter(None,x['Issue Raised (1)'].split('|')+x['Issue Raised (2)'].split('|')+x['Issue Raised (3)'].split('|')+x['Issue Raised (4)'].split('|')+x['Issue Raised (5)'].split('|')+x['Issue Raised (6)'].split('|')+x['Issue Raised (7)'].split('|')+x['Issue Raised (8)'].split('|')+x['Issue Raised (9)'].split('|')+x['Issue Raised (10)'].split('|'))
		clean_tuple = (x['Country'].split('|'), clean_sectors, clean_issues)
		clean_data.append(clean_tuple)
	return clean_data 

def get_unique(column): 
	""" 
		Given a column from the master complaints df,
		return a list of its unique values
	"""
	u_column = []
	for x in column: 
		if x == x:
			for y in x.replace('Unknown', 'Other').replace('Extractives (oil, gas, mining)', 'Extractives (oil/gas/mining)').replace(', ', ',').split(','): 
				u_column.append(y)
	return list(set(u_column))

def get_project_names(): 
	ac = pd.read_csv('2016_17_complaints.csv')
	return list(set(filter(None, list(ac['Project Name'].fillna('')))))

def remove_duplicate_projects(proj_names, wb_data):
	"""
		proj_names is list of project names from COMPLAINTS
		wb_data is list of tuples where each element is tuple of (project name, [countries], [sectors])
		updates wb_data to remove instances of matching project names
	"""
	unmatched_data = []

	for tup in wb_data:
		match = False
		for name in proj_names:
			if tup[0] in name:
			#if tup[0] == name:
				match = True
				break
		if match == False: unmatched_data.append(tup)

	return unmatched_data

def combine_datasets(complaint_data, WB_data, numIssues):
	"""
		Returns a shuffled combo of complaint_data and unique WB_data
		Complaint Data: list of ([countries], [sectors], [issues]) tuples
		WB Data:        list of (proj name, [countries], [sectors]) tuples
		Ignores project name.
	""" 
	#print('orig 0:', complaint_data[0], 'orig 20:', complaint_data[20], 'orig 600:', complaint_data[600])
	for a, b, c, d in WB_data:
		complaint_data.append( (b, c, ['NONE'], d) )
	random.shuffle(complaint_data)
	#print('new 0:', complaint_data[0], 'new 20:', complaint_data[20], 'new 600:', complaint_data[600])

	return complaint_data

############################################################
##  Related to featurization
############################################################

def build_dict(filename):
	""" 
		Returns a tuple consisting of
		(1) the list of regions
		(2) a dictionary mapping countries to regions
	"""
	your_list = []
	with open(filename) as inputfile:
		for row in csv.reader(inputfile):
			your_list.append(row[0])

	your_list = your_list[1:]

	dictionary = {}     # maps country to region
	categories = []     # list of regions
	category = ''

	for item in your_list:
		if item[0] == '*':
			category = item[1:]
			dictionary[category] = category
			categories.append(category)

		else:
			dictionary[item] = category

	return categories, dictionary


def featurize_complex(inputList, featureVec, dictionary):
	"""
	Converts a list of string inputs (countries or sectors) into an
	extracted feature vector (based on regions or standard sectors).
	Outputs a sparse feature vector (of regions or standard sectors).
	"""
	#print "SUCCESSFUL COMPLEX FEATURIZER"
	#print("\nInput List: ", inputList)
	newVec = np.zeros(len(featureVec))

	for s in inputList:
		if s in dictionary:
			for i in range(len(featureVec)):
				if dictionary[s] == featureVec[i]: 
					newVec[i] = 1

	return newVec.tolist()

def featurize_finance(investment, average_money):
	"""
	Converts a single monetary investment into an extracted feature vector,
	where the amount is bucketed based on magnitude. 
	"""

	#newVec = [0, 0, 0, 0, 0, 0, 0, 0]
	newVec = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

	if investment == 0: money = average_money
	else: money = investment

	if   money < 1*10**5: newVec[0]=1
	elif money < 5*10**5: newVec[1]=1
	elif money < 1*10**6: newVec[2]=1
	elif money < 5*10**6: newVec[3]=1
	elif money < 1*10**7: newVec[4]=1
	elif money < 5*10**7: newVec[5]=1
	elif money < 1*10**8: newVec[6]=1
	elif money < 5*10**8: newVec[7]=1
	elif money < 1*10**9: newVec[8]=1
	else: newVec[9]=1

	return newVec

# def featurize_issue(inputList, featureVec):
#     """
#     Converts a list of string inputs (issues) into an extracted 
#     feature vector, based on the related feature vector.
#     If no issues, then the 'NONE' element is marked true.
#     Outputs a sparse feature vector.
#     """
#     newVec = np.zeros(len(featureVec))
#     numIssues = 0

#     for s in inputList:
#         for i in range(len(featureVec) - 1):
#             if s == featureVec[i]: 
#                 newVec[i] = 1
#                 numIssues += 1
#                 break

#     if numIssues == 0: featureVec[-1] = 1
#     return newVec.tolist()

def featurize_issue(inputList, issueBuckets):
	"""
	Converts a list of string inputs (issues) into an extracted 
	feature vector, based on the related feature vector.
	If no issues, then the 'NONE' element is marked true.
	Outputs a sparse feature vector.
	"""
	issueMap = { 
		'Other retaliation (actual or feared)': 'Violence',
		'Livelihoods': 'Community',
		'Labor': 'Malpractice',
		'Consultation and disclosure': 'Community',
		'Property damage': 'Damages',
		'Indigenous peoples': 'Community',
		'Cultural heritage': 'Community',
		'Personnel issues': 'Malpractice',
		'Water': 'Environment',
		'Other gender-related issues': 'Violence',
		'Biodiversity': 'Environment',
		'Procurement': 'Malpractice',
		'Gender-based violence': 'Violence',
		'Other community health and safety issues': 'Community',
		'Pollution': 'Environment',
		'Human rights': 'Violence',
		"Violence against the community (by gov't and/or company)": 'Violence',
		'Due diligence': 'Malpractice',
		'Displacement (physical and/or economic)': 'Displacement',
		'Other environmental': 'Environment',
		'Corruption/fraud': 'Malpractice',
		'Other': 'Other',
		'NONE': 'NONE'
	}

	newVec = np.zeros(len(issueBuckets))
	numIssues = 0

	for s in inputList:
		if s in issueMap:
			for i in range(len(issueBuckets)):
				if issueMap[s] == issueBuckets[i]: 
					newVec[i] = 1
					numIssues += 1
					break

	if numIssues == 0: newVec[-1] = 1
	return newVec.tolist()

def organize_issues(complaint_data): 
	unique_issues = set()
	for country, issue, sector, finance in complaint_data:
		for i in issue:
			unique_issues.add(i)
	print ('# unique issues: ', len(unique_issues))
	print unique_issues

############################################################

def organize_data():
	"""
	Returns a list of inputs (x) and outputs (y) for the entire combined dataset.
	You must partition train vs. test & convert lists to arrays within neuralnet function. 
	"""

	regions, regionDict = build_dict('countrylist.csv')
	sectors, sectorDict = build_dict('sectorlist.csv')
	#issues = ['Biodiversity', 'Consultation and disclosure', 'Corruption/fraud', 'Cultural heritage', 'Displacement (physical and/or economic)', 'Due diligence', 'Gender-based violence', 'Human rights', 'Indigenous peoples', 'Labor', 'Livelihoods', 'Other', 'Other community health and safety issues', 'Other environmental', 'Other gender-related issues', 'Other retaliation (actual or feared)', 'Personnel issues', 'Pollution', 'Procurement', 'Property damage', 'Unknown', "Violence against the community (by gov't and/or company)", 'Water', 'NONE']
	issueBuckets = ['Community', 'Damages', 'Displacement', 'Environment', 'Malpractice', 'Other', 'Violence', 'NONE']
	
	numRegions = len(regions)
	numSectors = len(sectors)
	#numIssues = len(issues)
	numIssues = len(issueBuckets)		# 10 ISSUES BUCKETS
	numMoney = NUM_MONEY_BUCKETS


	print('#regions: ', numRegions)
	print('#sectors: ', numSectors)
	print sectors
	print('#money: ', numMoney)
	print('#issues: ', numIssues)

	complaint_data = prepare_2016_17_data()
	print('Length of raw complaint: ', len(complaint_data) )
	organize_issues(complaint_data)

	print('Example Complaint Data: ', complaint_data[0])
	print('Example Complaint Data: ', complaint_data[1])
	print('Example Complaint Data: ', complaint_data[2])
	print('Example Complaint Data: ', complaint_data[3])

	WB_df = prepare_raw_WB_project_data()
	WB_clean_df = prepare_clean_WB_project_data(WB_df)
	unique_WB_data = remove_duplicate_projects(get_project_names(), WB_clean_df)
	total_dataset = combine_datasets(complaint_data, unique_WB_data, numIssues)

	print('Len Complaint: ', len(complaint_data))
	print('Len WB Data: ', len(WB_clean_df))
	print('Len Unique Data: ', len(unique_WB_data))
	print('Len Total Data: ', len(total_dataset))

	print('Example WB Data: ', unique_WB_data[2])
	print('Example Total Data: ', total_dataset[2])

	sum_money = 0
	for i in range(len(unique_WB_data)):
		sum_money += unique_WB_data[i][3]
	average_money = sum_money / len(unique_WB_data)


	print('Length of raw WB data: ', len(WB_df) )
	print('Length of unique WB data: ', len(unique_WB_data) )
	print('Length of total dataset: ', len(total_dataset) )

	regionCounter = np.zeros(numRegions+numSectors+numMoney)
	bucketCounter = np.zeros(len(issueBuckets))

	## Convert data
	xlist = []
	ylist = []
	total_dataset = total_dataset
	for i in range(len(total_dataset)):
		x = featurize_complex(total_dataset[i][0], regions, regionDict)+featurize_complex(total_dataset[i][1], sectors, sectorDict)+featurize_finance(total_dataset[i][3], average_money)
		y = featurize_issue(total_dataset[i][2], issueBuckets)  # Sorted into 8 issues
		xlist.append(x)
		ylist.append(y)
		regionCounter += x
		bucketCounter += y
		
	print('Region COUNTER: ', regionCounter, '\n Region Buckets:', regions)
	print('BUCKET COUNTER: ', bucketCounter, '\n Issue Buckets:', issueBuckets)
	return xlist, ylist, numRegions, numSectors, numIssues, numMoney

import collections
import math
import pandas as pd
import numpy as np
from keras.models import Sequential
from keras.layers import Dense, Activation, Dropout
from keras.optimizers import SGD
import keras.backend as K

from keras.metrics import top_k_categorical_accuracy, categorical_accuracy
def top_3_accuracy(y_true, y_pred):
    return top_k_categorical_accuracy(y_true, y_pred, k=3)

from matplotlib import pyplot

from sklearn.model_selection import StratifiedKFold

from keras.utils.vis_utils import plot_model
# first, add threshold to calculate 0/1 values
def change_by_threshold(threshold, values_vector):
  new_values_vector = [] 
  for x in values_vector:
    actual = [] 
    for y in x: 
      y = 1 if y > threshold else 0 
      actual.append(y)
    new_values_vector.append(actual)
  return new_values_vector


############################################################

# Parameters
numTrainers = 6000	# DECIDE SPLIT BETWEEN TRAINING AND TEST
xlist, ylist, numRegions, numSectors, numIssues, numMoney = organize_data()
featureVec_size = numRegions + numSectors + numMoney
final_dim = numIssues
batch_sz = 256

xtrain = np.array( xlist[:numTrainers] )
ytrain = np.array( ylist[:numTrainers] )
xtest = np.array( xlist[numTrainers:] )
ytest = np.array( ylist[numTrainers:] )

# Create the model
model = Sequential()
model.add(Dense(64, activation='relu', input_shape=(featureVec_size,) ))	#small dataset - less hidden layers needed
model.add(Dense(50, activation='relu'))
model.add(Dense(final_dim, activation='sigmoid'))
model.summary()

# Stochastic Gradient Descent
sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)

model.compile(loss='binary_crossentropy',
              optimizer=sgd,
              metrics=['accuracy'])

history = model.fit(xtrain, ytrain, epochs=200, batch_size=batch_sz)

# Time to test!
score = model.evaluate(xtest, ytest, batch_size=batch_sz)
print('Test loss:', score[0])
print('Test accuracy:', score[1])

#y_pred as by model
y_pred = model.predict_proba(xtest)
y_pred

def f1(y_true, y_pred):
    def recall(y_true, y_pred):
        """Recall metric.

        Only computes a batch-wise average of recall.

        Computes the recall, a metric for multi-label classification of
        how many relevant items are selected.
        """
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
        recall = true_positives / (possible_positives + K.epsilon())
        return recall

    def precision(y_true, y_pred):
        """Precision metric.

        Only computes a batch-wise average of precision.

        Computes the precision, a metric for multi-label classification of
        how many selected items are relevant.
        """
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
        precision = true_positives / (predicted_positives + K.epsilon())
        return precision
    precision = precision(y_true, y_pred)
    recall = recall(y_true, y_pred)
    return 2*((precision*recall)/(precision+recall+K.epsilon()))

sklearn.metrics.precision_score(ytest, predictions.round(), labels=None, pos_label=1, average='micro', sample_weight=None)

from sklearn.metrics import hamming_loss
hamming_loss(np.array([[0, 1], [1, 1]]), np.zeros((2, 2)))

df2 = pd.DataFrame(np.random.rand(10, 9), columns=['Threshold', 'Micro Recall', 'Micro Precision', 'Micro F1-Score', 'Macro Recall', 'Macro Precision', 'Macro F1-Score', 'Hamming Loss', 'Top 3 Categorical Accuracy'])


df2 = df2.set_index('Threshold')

df2

import matplotlib.pyplot as plot
df2.plot.bar(figsize=(20,10), use_index=True)
plt.savefig('output.png')

from google.colab import files
files.download( "model_plot.png" )

files.download( "df4.png" )

# micro recall 

# first, add threshold to calculate 0/1 values
def change_by_threshold(threshold, values_vector):
  new_values_vector = [] 
  for x in values_vector:
    actual = [] 
    for y in x: 
      y = 1 if y > threshold else 0 
      actual.append(y)
    new_values_vector.append(actual)
  return np.array(new_values_vector)

ypred = y_pred
newypred = change_by_threshold(0.02, ypred)
ypred

np.array(newypred)

#X = np.array(new_ypred)
#X = dataset[:,0:4].astype(float)

from sklearn.metrics import precision_recall_curve
from sklearn.metrics import average_precision_score
import matplotlib.pyplot as plt

# For each class
precision = dict()
recall = dict()
average_precision = dict()
for i in range(23):
    precision[i], recall[i], _ = precision_recall_curve(ytest[:, i],
                                                        newypred[:, i])
    average_precision[i] = average_precision_score(ytest[:, i], newypred[:, i])

# A "micro-average": quantifying score on all classes jointly
precision["micro"], recall["micro"], _ = precision_recall_curve(ytest.ravel(),
    newypred.ravel())
average_precision["micro"] = average_precision_score(ytest, newypred,
                                                     average="micro")
print('Average precision score, micro-averaged over all classes: {0:0.2f}'
      .format(average_precision["micro"]))

ypred

newypred

def get_micro_precision():
  recision = dict()
  recall = dict()
  average_precision = dict()
  for i in range(23):
      precision[i], recall[i], _ = precision_recall_curve(ytest[:, i],
                                                          ypred[:, i])
      average_precision[i] = average_precision_score(ytest[:, i], ypred[:, i])

  # A "micro-average": quantifying score on all classes jointly
  precision["micro"], recall["micro"], _ = precision_recall_curve(ytest.ravel(),
      ypred.ravel())
  average_precision["micro"] = average_precision_score(ytest, ypred,
                                                       average="micro")
  
  return average_precision["micro"]

from sklearn.metrics import recall_score
for x in new_ypred:
  print(x)
  break

# get average recall (mirco)

recall.values()
all_recall = []
# convert list of array into list of lists
for x in recall.values(): 
  all_recall.append(list(x))

recall

newypred

def get_micro_recall(newypred):
  return recall_score(ytest, newypred, average='micro')

def get_macro_precision(newypred):
    # For each class
    precision = dict()
    recall = dict()
    average_precision = dict()
    for i in range(23):
        precision[i], recall[i], _ = precision_recall_curve(ytest[:, i],
                                                            newypred[:, i])
        average_precision[i] = average_precision_score(ytest[:, i], newypred[:, i])

    # A "micro-average": quantifying score on all classes jointly
    precision["macro"], recall["macro"], _ = precision_recall_curve(ytest.ravel(),
        newypred.ravel())
    average_precision["macro"] = average_precision_score(ytest, newypred,
                                                         average="macro")
    return average_precision["macro"]

newypred

y_pred.shape

all_y_pred[11].shape

ytest

average_precision_score(ytest,newypred, average='macro')
np.isnan(newypred).any()

def average_precision_score(newypred): 
  
  y_val_true, val_pred = ytest.reshape((-1)), newypred.reshape((-1))
  val_ap = average_precision_score(y_val_true, val_pred)
  return val_ap

recall_score(ytest, newypred, average='macro')

micro_precision.append(get_micro_precision(ypred))

get_micro_precision(newypred)

# micro recall 
import numpy as np
from sklearn.metrics import precision_recall_curve
from sklearn.metrics import average_precision_score
from sklearn.metrics import f1_score
import matplotlib.pyplot as plt
from sklearn.metrics import hamming_loss
# first, add threshold to calculate 0/1 values
def change_by_threshold(threshold, values_vector):
  new_values_vector = [] 
  for x in values_vector:
    actual = [] 
    for y in x: 
      y = 1 if y > threshold else 0 
      actual.append(y)
    new_values_vector.append(actual)
  return np.array(new_values_vector)

def get_micro_precision(ytest, newypred):
    # For each class
    precision = dict()
    recall = dict()
    average_precision = dict()
    for i in range(8):
        precision[i], recall[i], _ = precision_recall_curve(ytest[:, i],
                                                            newypred[:, i])
        average_precision[i] = average_precision_score(ytest[:, i], newypred[:, i])

    # A "micro-average": quantifying score on all classes jointly
    precision["micro"], recall["micro"], _ = precision_recall_curve(ytest.ravel(),
        newypred.ravel())
    average_precision["micro"] = average_precision_score(ytest, newypred,
                                                         average="micro")
    return average_precision["micro"]

def get_micro_recall(ytest, newypred):
  return recall_score(ytest, newypred, average='micro') 

def get_macro_precision(ytest,newypred): 
  y_val_true, val_pred = ytest.reshape((-1)), newypred.reshape((-1))
  val_ap = average_precision_score(y_val_true, val_pred)
  return val_ap

def get_macro_recall(ytest,newypred):
    return recall_score(ytest, newypred, average='macro') 

def get_hamming_loss(ytest,newypred):
    return hamming_loss(ytest, newypred)

def top_3_accuracy(y_true, y_pred):
    return top_k_categorical_accuracy(y_true, y_pred, k=3)

def get_micro_f1_score(ytest,newypred):
    return f1_score(ytest, newypred, average='micro')  

def get_macro_f1_score(ytest,newypred):
    return f1_score(ytest, newypred, average='macro')  


thresholds = [0.01, .02, .04, .08, .16, .25, .35, .5, .8]
micro_precision = [] 
micro_recall = [] 
macro_recall = [] 
macro_precision = [] 
micro_f1 = []
macro_f1 = [] 
hamming_loss_stat = []
micro_precision_a = [] 
micro_recall_a = []
macro_recall_a = [] 
macro_precision_a = []
micro_f1_a = []
macro_f1_a = []
hamming_loss_stat_a = [] 

for x in thresholds: 
  micro_precision_a= [] 
  macro_recall_a=[]
  micro_recall_a=[]
  macro_precision_a=[]
  micro_f1_a=[]
  macro_f1_a=[]
  hamming_loss_stat_a=[]
  for i in xrange(len(all_y_pred)):
    
    newypred = change_by_threshold(x, all_y_pred[i])
    ytest = all_y_test[i]
    # get micro precision 
    micro_precision_a.append(precision_score(ytest,newypred, average='micro'))
    # get micro F1 score 
    micro_recall_a.append(get_micro_recall(ytest,newypred))
    # get macro recall 
    macro_recall_a.append(get_macro_recall(ytest,newypred))
    # get macro precision 
    macro_precision_a.append(precision_score(ytest,newypred, average='macro'))
    # get macro F1 score 
    macro_f1_a.append(get_macro_f1_score(ytest,newypred))
    # get micro F1 score 
    micro_f1_a.append(get_micro_f1_score(ytest,newypred))
    # get top 3 categorial accuracy -- later
    # get hamming loss
    hamming_loss_stat_a.append(get_hamming_loss(ytest,newypred))
  micro_precision.append(np.mean(micro_precision_a))
  micro_recall.append(np.mean(micro_recall_a))
  macro_recall.append(np.mean(macro_recall_a))
  macro_precision.append(np.mean(macro_precision_a))
  micro_f1.append(np.mean(micro_f1_a))
  macro_f1.append(np.mean(macro_f1_a))
  hamming_loss_stat.append(np.mean(hamming_loss_stat_a))

import numpy as np
from sklearn.metrics import precision_score
thresholds = [0.01, .02, .04, .08, .16, .25, .35, .5, .8]
ham_average = [] 
ham_min = [] 
ham_max = [] 
for x in thresholds: 
  individual_hamming_loss_stat= [] 
  for i in xrange(len(all_y_pred)):
    newypred = change_by_threshold(x, all_y_pred[i])
    ytest = all_y_test[i]
    individual_hamming_loss_stat.append(get_micro_f1_score(ytest,newypred))
  #sum of hamming loss for this threshold 
  ham_average.append(np.mean(individual_hamming_loss_stat))
  ham_min.append(min(individual_hamming_loss_stat))
  ham_max.append(max(individual_hamming_loss_stat))

average = [] 
for x in thresholds: 
  individual_hamming_loss_stat= [] 
  for i in xrange(len(all_y_pred)):
    newypred = change_by_threshold(x, all_y_pred[i])
    ytest = all_y_test[i]
    individual_hamming_loss_stat.append(get_micro_f1_score(ytest,newypred))
  #sum of hamming loss for this threshold 
  average.append(np.mean(individual_hamming_loss_stat))

new_thresholds = [] 
for x in thresholds: 
    for i in xrange(len(all_y_pred)):
      new_thresholds.append(x)
len(new_thresholds)

len(new_thresholds)

df = pd.DataFrame({'Threshold': thresholds,'Micro Recall': micro_recall, 
                  'Macro Recall': macro_recall, 
                  'Micro Precision': micro_precision,
                   'Macro Precision': macro_precision, 
                  'Micro F1-Score': micro_f1, 
                  'Macro F1-Score': macro_f1, 
                  'Hamming Loss': hamming_loss_stat})
index = ['Threshold', 'Micro Recall', 'Macro Recall', 'Micro Precision','Macro Precision','Micro F1-Score','Macro F1-Score','Hamming Loss']
df.index

df

index = ['Micro Recall', 'Macro Recall', 'Micro Precision','Macro Precision','Micro F1-Score','Macro F1-Score','Hamming Loss']

df3 = pd.DataFrame({'Micro Recall': micro_recall, 
                  'Macro Recall': macro_recall, 
                  'Micro Precision': micro_precision,
                   'Macro Precision': macro_precision, 
                  'Micro F1-Score': micro_f1, 
                  'Macro F1-Score': macro_f1, 
                  'Hamming Loss': hamming_loss_stat}, index = thresholds)

df3 = df3.reindex(columns=['Micro Recall', 'Macro Recall', 'Micro Precision','Macro Precision','Micro F1-Score','Macro F1-Score','Hamming Loss'])
df3.plot.bar(rot=0,figsize=(20,10), use_index=True)
plt.savefig('df4.png')

all_y_test = [] 
all_y_pred = [] 
def perform_validation(model, feat_vecs, labels, all_labels, n_folds):
        
	skf = StratifiedKFold(n_splits=n_folds, random_state=None, shuffle=False)
	min_loss, max_loss = float('inf'), -float('inf')
	min_accuracy, max_accuracy = float('inf'), -float('inf')
	loss_sum = 0
	accuracy_sum = 0
	# iterate through n_folds number of train/test partitions
	for train_indices, test_indices in skf.split(feat_vecs, labels):
		sz = len(train_indices)
		xtrain, ytrain, xtest, ytest = [], [], [], []
		for i, train_index in enumerate(train_indices):
			xtrain.append(feat_vecs[train_index])
			ytrain.append(all_labels[train_index])
		for i, test_index in enumerate(test_indices):
			xtest.append(feat_vecs[test_index])
			ytest.append(all_labels[test_index])
		# train on xtrain, ytrain (copied from neuralnet.py)
		xtrain = np.asarray(xtrain)
		ytrain = np.asarray(ytrain)
		xtest = np.asarray(xtest)
		ytest = np.asarray(ytest)
		history = model.fit(xtrain, ytrain, epochs=200, batch_size=batch_sz, verbose=0)
		# test on xtest, ytest (copied from neuralnet.py)
		score = model.evaluate(xtest, ytest, batch_size=batch_sz)
		all_y_test.append(ytest)
                all_y_pred.append(model.predict_proba(xtest))
                # update metrics
		loss_sum += score[0]
		accuracy_sum += score[1]
		if score[0] < min_loss: min_loss = score[0]
		if score[0] > max_loss: max_loss = score[0]
		if score[1] < min_accuracy: min_accuracy = score[1]
		if score[1] > max_accuracy: max_accuracy = score[1]

	avg_loss = float(loss_sum)/n_folds
	avg_accuracy = float(accuracy_sum)/n_folds
	final_tuple = (avg_loss, min_loss, max_loss, avg_accuracy, min_accuracy, max_accuracy)
	print ("average loss: %f\nmin: %f\tmax: %f\n\naverage accuracy: %f\nmin: %f\tmax: %f\t\n" % final_tuple)
	return final_tuple

def cross_validate(model, feat_vecs, labels, n_folds):
	summaries = []
	for col in range(len(labels[0])):
		print col
		issue_label = []
		for label in labels:
			issue_label.append(label[col])
		summaries.append(perform_validation(model, feat_vecs, issue_label, labels, n_folds))
	return summaries

def evaluate_summaries(summaries):
	max_tuple = []
	avg_tuple = []
	for i, summary in enumerate(summaries):
		if len(max_tuple) == 0 or max_tuple[5] < summary[5]:
			max_tuple = [summary, i]
		if len(avg_tuple) == 0 or avg_tuple[3] < summary[3]:
			avg_tuple = [summary, i]
	print "Out of the 24 iterations, issue #%d had the highest max accuracy at %f, \n\
	and issue #%d had the highest average accuracy at %f." % (max_tuple[1], max_tuple[0], avg_tuple[1], avg_tuple[0])

############################################################

# Parameters
numTrainers = 6000
xlist, ylist, numRegions, numSectors, numIssues, numMoney = organize_data()
featureVec_size = numRegions + numSectors + numMoney
final_dim = numIssues
batch_sz = 256

xtrain = np.array( xlist[:numTrainers] )
ytrain = np.array( ylist[:numTrainers] )
xtest = np.array( xlist[numTrainers:] )
ytest = np.array( ylist[numTrainers:] )

# Create the model
model = Sequential()
model.add(Dense(64, activation='relu', input_shape=(featureVec_size,) ))	#small dataset - less hidden layers needed
model.add(Dense(40, activation='relu'))
model.add(Dense(final_dim, activation='sigmoid'))

model.summary()

# Stochastic Gradient Descent
sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)

model.compile(loss='binary_crossentropy',
			  optimizer=sgd,
			  metrics=['accuracy'])

history = model.fit(xtrain, ytrain, epochs=200, batch_size=batch_sz)

# Time to test!
score = model.evaluate(xtest, ytest, batch_size=batch_sz)

print "\nCompiled! Here are your results..."
print('Test loss:', score[0])
print('Test accuracy:', score[1])

all_featurevecs = xlist
all_labels = ylist
summaries = cross_validate(model, all_featurevecs, all_labels, 3)
############################################################
"""
	NOTES: 
	- Consider shrinking the number of issues (from 15 to 4) - leads to acc of 100%... too high

"""

all_y_pred

i=0
for x in all_y_pred:
  print(i)
  i+=1
