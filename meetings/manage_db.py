import pymongo
from pymongo import MongoClient
import arrow
import sys
import string
import random
from flask import Flask

import config
CONFIG = config.configuration()

MONGO_CLIENT_URL = "mongodb://{}:{}@{}:{}/{}".format(
    CONFIG.DB_USER,
    CONFIG.DB_USER_PW,
    CONFIG.DB_HOST, 
    CONFIG.DB_PORT, 
    CONFIG.DB)

def init_db(unique_meeting_id,meeting_duration,daterange_start,daterange_stop,timerange_start,timerange_stop,host_email,host_busy_times,guest_list):
	"""
	@breif 		intializes our data base for a specific meeting

	@param 		unique_meeting_id
	@param 		meeting_duration
	@param 		daterange_start
	@param 		daterange_stop
	@param 		timerange_start
	@param 		timerange_stop
	@param      host_email
	@param 		host_busy_times
	@param 		guest_list

	@return  	None, creates a database that will be later updated with users busy times

	"""
	# print("=============================")
	# print("Arguments Recieved in init_db")
	# print("Unique meeting id: ", unique_meeting_id)
	# print("Meeting Duration: ", meeting_duration)
	# print("Daterange Start: ", daterange_start)
	# print("Daterange Stop: ", daterange_stop)
	# print("Timerange Start: ", timerange_start)
	# print("Timerange Stop: ", timerange_stop)
	# print("Host Email: ", host_email)
	# print("Host Busy Times: ", host_busy_times)
	# print("Guest List: ", guest_list)
	# print("=============================")

	try: 
		dbclient = MongoClient(MONGO_CLIENT_URL)
		db = getattr(dbclient, CONFIG.DB)
		collection = db.dated
	except Exception as err:
		print(err)
		sys.exit(1)

	meeting = {"meeting_id": unique_meeting_id,
				"meeting_duration": meeting_duration,
				"daterange_start": daterange_start,
				"daterange_stop": daterange_stop,
				"timerange_start": timerange_start,
				"timerange_stop": timerange_stop,
				}
	collection.insert(meeting)

	# Add the host because we alread have their information
	add_user(collection,unique_meeting_id,host_email, True,host_busy_times)

	# Add the guests to the database
	for email in guest_list:
		add_user(collection,unique_meeting_id,email)

	return None


def update_user(meeting_id, user_email, responded, busy_times):
	try: 
		dbclient = MongoClient(MONGO_CLIENT_URL)
		db = getattr(dbclient, CONFIG.DB)
		collection = db.dated
	except Exception as err:
		print(err)
		sys.exit(1)
	user = collection.find({"user_email":user_email})
	if user:
		collection.update({"user_email":user_email},
				{
				"$set": {
					"user_responded": responded,
					"user_busy_times": busy_times
				}
				}
		)

def add_user(db, meeting_id, user_email, responded=False,busy_times=[]):
	"""
	@brief      addds a user to a specific collection in our mongo database
	
	@param      mongo the "meetme" database
	@param      meeting_id   a unique meeting_id, randomly generated and shared across multiple users
	            attending the same meeting
	@param      user_email (str) the users email address
	@param      responsded (boolean) "True" if the user has responed and we have their busy times, "False" otherwise
	@param      busy_times(list of TimeBlocks) busy times from the individuals calendar, busy_times will be empty if the user has not yet responded
	
	@return     None, the result is that a new user has been added to a collection in our database
	"""
	user = {"user_meeting_id" : meeting_id,
			"user_email": user_email,
			"user_responded": responded,
			"user_busy_times": busy_times
			}
	db.insert(user)
	return None


def generate_key(chars=string.ascii_lowercase + string.digits):
	return ''.join(random.choice(chars) for _ in range(10))


def get_not_responded(meeting_id):
	"""
	@brief      Gets the list of users all from the same meeting whose "responded" key is False
	
	@param      db          The database
	@param      meeting_id  A Unique meeting identifier
	
	@return     A list of email addresses of those who have not yet
	"""
	try: 
		dbclient = MongoClient(MONGO_CLIENT_URL)
		db = getattr(dbclient, CONFIG.DB)
		collection = db.dated
	except Exception as err:
		print(err)
		sys.exit(1)

	emails = []

	for record in collection.find({"user_meeting_id":meeting_id}).sort("user_email",pymongo.ASCENDING):
		# removed the useless id
		del record["_id"]
		# if they haven't responsded add them to our list
		if record["user_responded"] == False:
			emails.append(record["user_email"])

	return emails


def get_meetings_datetimerange(meeting_id):
	"""
	@brief      Gets the meetings datetimerange.
	
	@param      meeting_id  The unique meeting identifier
	
	@return     returns a tuple of datestart,datestop,timestart,timestop
	"""
	try: 
		dbclient = MongoClient(MONGO_CLIENT_URL)
		db = getattr(dbclient, CONFIG.DB)
		collection = db.dated
	except Exception as err:
		print(err)
		sys.exit(1)
	
	meeting = collection.find({"meeting_id": meeting_id})[0]
	del meeting["_id"]
	dr_s1 = meeting["daterange_start"]
	dr_s2 = meeting["daterange_stop"]

	tr_s1 = meeting["timerange_start"]
	tr_s2 = meeting["timerange_stop"]

	return (dr_s1,dr_s2,tr_s1,tr_s2)