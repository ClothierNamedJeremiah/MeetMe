import flask
from flask import render_template
from flask import request
from flask import url_for
import uuid


import json
import logging
import copy

# Date handling
import arrow # Replacement for datetime, based on moment.js
# import datetime # But we still need time
from dateutil import tz  # For interpreting local times


# OAuth2  - Google library implementation for convenience
from oauth2client import client
import httplib2   # used in oauth2 flow

# Google API for services
from apiclient import discovery

# Our own modules
import calc_busy_time
import calc_free_times
import timeblocks
import manage_db

###
# Globals
###
import config
if __name__ == "__main__":
    CONFIG = config.configuration()
else:
    CONFIG = config.configuration(proxied=True)

app = flask.Flask(__name__)
app.debug=CONFIG.DEBUG
app.logger.setLevel(logging.DEBUG)
app.secret_key=CONFIG.SECRET_KEY

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = CONFIG.GOOGLE_KEY_FILE  ## You'll need this
APPLICATION_NAME = 'MeetMe class project'

#############################
#
#  Pages (routed from URLs)
#
#############################

@app.route("/")
@app.route("/index")
def index():
  app.logger.debug("Entering index")
  flask.session["meeting_id"] = manage_db.generate_key()
  if 'begin_date' not in flask.session:
    init_session_values()
  return render_template('index.html')

@app.route("/choose")
def choose():
    ## We'll need authorization to list calendars 
    ## I wanted to put what follows into a function, but had
    ## to pull it back here because the redirect has to be a
    ## 'return' 
    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))
    
    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.g.calendars = list_calendars(gcal_service)
    return render_template  ('index.html')

####
#
#  Google calendar authorization:
#      Returns us to the main /choose screen after inserting
#      the calendar_service object in the session state.  May
#      redirect to OAuth server first, and may take multiple
#      trips through the oauth2 callback function.
#
#  Protocol for use ON EACH REQUEST: 
#     First, check for valid credentials
#     If we don't have valid credentials
#         Get credentials (jump to the oauth2 protocol)
#         (redirects back to /choose, this time with credentials)
#     If we do have valid credentials
#         Get the service object
#
#  The final result of successful authorization is a 'service'
#  object.  We use a 'service' object to actually retrieve data
#  from the Google services. Service objects are NOT serializable ---
#  we can't stash one in a cookie.  Instead, on each request we
#  get a fresh serivce object from our credentials, which are
#  serializable. 
#
#  Note that after authorization we always redirect to /choose;
#  If this is unsatisfactory, we'll need a session variable to use
#  as a 'continuation' or 'return address' to use instead. 
#
####

def valid_credentials():
    """
    Returns OAuth2 credentials if we have valid
    credentials in the session.  This is a 'truthy' value.
    Return None if we don't have credentials, or if they
    have expired or are otherwise invalid.  This is a 'falsy' value. 
    """
    if 'credentials' not in flask.session:
      return None

    credentials = client.OAuth2Credentials.from_json(
        flask.session['credentials'])

    if (credentials.invalid or
        credentials.access_token_expired):
      return None
    return credentials


def get_gcal_service(credentials):
  """
  We need a Google calendar 'service' object to obtain
  list of calendars, busy times, etc.  This requires
  authorization. If authorization is already in effect,
  we'll just return with the authorization. Otherwise,
  control flow will be interrupted by authorization, and we'll
  end up redirected back to /choose *without a service object*.
  Then the second call will succeed without additional authorization.
  """
  app.logger.debug("Entering get_gcal_service")
  http_auth = credentials.authorize(httplib2.Http())
  service = discovery.build('calendar', 'v3', http=http_auth)
  app.logger.debug("Returning service")
  return service

@app.route('/oauth2callback')
def oauth2callback():
  """
  The 'flow' has this one place to call back to.  We'll enter here
  more than once as steps in the flow are completed, and need to keep
  track of how far we've gotten. The first time we'll do the first
  step, the second time we'll skip the first step and do the second,
  and so on.
  """
  app.logger.debug("Entering oauth2callback")
  flow =  client.flow_from_clientsecrets(
      CLIENT_SECRET_FILE,
      scope= SCOPES,
      redirect_uri=flask.url_for('oauth2callback', _external=True))
  ## Note we are *not* redirecting above.  We are noting *where*
  ## we will redirect to, which is this function. 
  
  ## The *second* time we enter here, it's a callback 
  ## with 'code' set in the URL parameter.  If we don't
  ## see that, it must be the first time through, so we
  ## need to do step 1. 
  app.logger.debug("Got flow")
  if 'code' not in flask.request.args:
    app.logger.debug("Code not in flask.request.args")
    auth_uri = flow.step1_get_authorize_url()
    return flask.redirect(auth_uri)
    ## This will redirect back here, but the second time through
    ## we'll have the 'code' parameter set
  else:
    ## It's the second time through ... we can tell because
    ## we got the 'code' argument in the URL.
    app.logger.debug("Code was in flask.request.args")
    auth_code = flask.request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    flask.session['credentials'] = credentials.to_json()
    ## Now I can build the service and execute the query,
    ## but for the moment I'll just log it and go back to
    ## the main screen
    app.logger.debug("Got credentials")
    if "guest" in flask.session:
      return flask.redirect(flask.url_for('invite_submission',meeting_id=flask.session["meeting_id"]))
    else:
      return flask.redirect(flask.url_for('choose'))

#####
#
#  Option setting:  Buttons or forms that add some
#     information into session state.  Don't do the
#     computation here; use of the information might
#     depend on what other information we have.
#   Setting an option sends us back to the main display
#      page, where we may put the new information to use.
#
#####

@app.route('/setrange', methods=['POST'])
def setrange():
    """
    User chose a date range with the bootstrap daterange
    widget.
    """
    app.logger.debug("Entering setrange")
    flask.flash("Setrange gave us '{}'".format(
      request.form.get('daterange')))
    daterange = request.form.get('daterange')
    flask.session['daterange'] = daterange
    daterange_parts = daterange.split()
    flask.session['begin_date'] = interpret_date(daterange_parts[0])
    flask.session['end_date'] = interpret_date(daterange_parts[2])
    app.logger.debug("Setrange parsed {} - {}  dates as {} - {}".format(
      daterange_parts[0], daterange_parts[1],
      flask.session['begin_date'], flask.session['end_date']))
    # Get Begin/End Times
    open_time = request.form['opentime']
    close_time = request.form['closetime']
    flask.session['begin_time'] = open_time
    flask.session['end_time'] = close_time

    return flask.redirect(flask.url_for("choose"))

@app.route('/setcalendars', methods=['GET','POST'])
def setcalendars():
  """
  User has selected their calendars from the checkboxes
  """
  if request.method == 'GET':
    return render_template("index.html")
  app.logger.debug("Checking credentials for Google calendar access")
  credentials = valid_credentials()
  if not credentials:
    app.logger.debug("Redirecting to authorization")
    return flask.redirect(flask.url_for('oauth2callback'))

  gcal_service = get_gcal_service(credentials)
  app.logger.debug("Returned from get_gcal_service")
  flask.g.calendars = list_calendars(gcal_service)
  checked_calendars = calc_busy_time.list_checked(flask.g.calendars,request)
  print("===================LOOOK FOR THIS=========================")
  print(checked_calendars)
  print(flask.session["begin_date"])
  print(flask.session["end_date"])
  print(flask.session["begin_time"])
  print(flask.session["end_time"])
  print("===================END=========================")
  busy_blocks = calc_busy_time.get_all_busy(gcal_service,checked_calendars,flask.session["begin_date"],flask.session["end_date"],flask.session["begin_time"],flask.session["end_time"])
  c = copy.deepcopy(busy_blocks)
  # Get the List of Busy Times and format them to be stored in the session/database
  begin_hr, begin_min = list(map(int,flask.session["begin_time"].split(":")))
  end_hr, end_min = list(map(int,flask.session["end_time"].split(":")))
  open_time = arrow.get(flask.session["begin_date"]).replace(hour=begin_hr,minute=begin_min)
  open_year, open_month, open_day = list(map(int,open_time.format("YYYY:MM:DD").split(":")))
  end_time = arrow.get(flask.session["end_date"]).replace(hour=end_hr,minute=end_min)
  
  # consolidate and trim the list of busy_blocks
  consolidated_busy = calc_free_times.consolidate(c)
  trimmed = calc_free_times.trim_blocks(consolidated_busy,open_time,end_time)
  trimmed_json = []
  for tb in trimmed:
    trimmed_json.append(json.dumps(tb,cls=timeblocks.MyEnconder))
  flask.session["busy_times"] = trimmed_json
  ### End of Formatting
  
  time_blocks = calc_free_times.get_time_blocks(busy_blocks,flask.session["begin_date"],flask.session["end_date"],flask.session["begin_time"],flask.session["end_time"])
  flask.g.timeblocks = list_blocks(time_blocks)
  return render_template('index.html')

@app.route('/setduration',methods=['GET','POST'])
def setduration():
  """
  Lets the user select a duration for their meeting
  """
  if request.method == 'GET':
    flask.session["guest_list"] = []
    return render_template('set-duration.html')

  flask.session["meeting_duration"] = int(request.form["ts"])
  flask.session["host_email"] = request.form["host_email"]
  return flask.redirect(flask.url_for("guest_list"))

#TODO:
@app.route('/guest_list', methods=['GET','POST'])
def guest_list():
  """
  Responsible for keeping guest-list.html updated with
  a list of email addresses
  """
  if request.method == 'POST':
    if len(request.form["usremail"]) > 1:
      # A new email address was added, we need store it in the session guest_list
      flask.session["guest_list"] += [str(request.form["usremail"])]
      flask.session["guest_list"].sort()

  flask.g.guest_list = flask.session["guest_list"]

  ### Content stored in "mailto:" tag in guest-list.html
  flask.g.invite_link = "localhost:5000/invite/{}".format(str(flask.session["meeting_id"])) # link of invite sent in email
  flask.g.recipients = string_of_emails(flask.session["guest_list"])
  ### End of "mailto:" content
  return render_template('guest-list.html')

@app.route('/delete',methods=['POST'])
def delete():
  """
  Deletes selected email addresses on the webpage guest-list.html
  """
  for i in range(1,len(flask.session["guest_list"])+1):
    try:
      email = request.form["chk{}".format(i)]
      flask.session["guest_list"].remove(email)
    except:
      pass
  flask.session["guest_list"] = flask.session["guest_list"] # This line may seem meaningless, but without it the list stored in the session will not update
  return flask.redirect(flask.url_for("guest_list"))

@app.route('/emailed', methods=['POST'])
def emailed():
  """
  1. Creates a database and populates it with session variables/users

  2. Loads a "receipt" webpage, thanking the user for creating a meeting using
  the MeetMe Application and giving them a link so that they can check back
  on the list of available times
  """

  manage_db.init_db(flask.session["meeting_id"], flask.session["meeting_duration"], flask.session["begin_date"],flask.session["end_date"],
    flask.session["begin_time"],flask.session["end_time"],flask.session["host_email"], flask.session["busy_times"], flask.session["guest_list"])

  flask.g.status = "localhost:5000/status/{}".format(flask.session["meeting_id"])
  return render_template('emailed.html')

@app.route("/invite/<string:meeting_id>",methods=["GET","POST"])
def invite(meeting_id):
  """
  Web page that loads when an invidual
  """
  flask.session["guest"] = True
  flask.session["meeting_id"] = meeting_id
  flask.g.meeting_id = meeting_id
  if request.method == "GET":
    if "credentials" in flask.session.keys():
     flask.session.pop("credentials") # flask.session.pop("credentials")# While testing on LocalHost we want to clear the session
    return flask.render_template("invited.html")

  # Case request.method == "POST", they have entered their email address and clicked 'submit' button
  email = request.form["usremail"]
  flask.session["user_email"] = email

  app.logger.debug("Checking credentials for Google calendar access")
  credentials = valid_credentials()
  if not credentials:
    app.logger.debug("Redirecting to authorization")
    return flask.redirect(flask.url_for('oauth2callback'))


@app.route("/invite_submission/<string:meeting_id>",methods=["GET","POST"])
def invite_submission(meeting_id):
  if request.method == "GET":
    flask.g.meeting_id = meeting_id
    credentials = valid_credentials()
    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.g.calendars = list_calendars(gcal_service)
    return flask.render_template("invited.html")
  else:
    #TODO: Proccess the users data and add it to the database
    # The session variables we have are meeting_id, user_email
    # Idea: use database to get timerange start/stop, daterange start/stop
    
    ## GET THE CHECKMARKED CALENDARS
    credentials = valid_credentials()
    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.g.calendars = list_calendars(gcal_service)
    checked_calendars = calc_busy_time.list_checked(flask.g.calendars,request)
    ## END OF GET THE CHECKMARKED CALENDARS

    ## GET THE DATE/TIME RANGES USING OUR DATABASE
    a,b,c,d = manage_db.get_meetings_datetimerange(meeting_id) # for description of variables see get_meetings_datetimerange in the file manage_db.py
    
    ## BUILD A LIST OF BUSY BLOCKS, CONSOLIDATE AND TRIM THEM
    busy_blocks = calc_busy_time.get_all_busy(gcal_service,checked_calendars,a,b,c,d)
    begin_hr, begin_min = list(map(int,c.split(":")))
    end_hr, end_min = list(map(int,d.split(":")))
    open_time = arrow.get(a).replace(hour=begin_hr,minute=begin_min)
    open_year, open_month, open_day = list(map(int,open_time.format("YYYY:MM:DD").split(":")))
    end_time = arrow.get(b).replace(hour=end_hr,minute=end_min)
    
    consolidated_busy = calc_free_times.consolidate(busy_blocks)
    trimmed = calc_free_times.trim_blocks(consolidated_busy,open_time,end_time)
    trimmed_json = []
    for tb in trimmed:
      trimmed_json.append(json.dumps(tb,cls=timeblocks.MyEnconder))

    manage_db.update_user(meeting_id,flask.session["user_email"],True,trimmed_json)

    return flask.render_template("thanks.html")

@app.route("/status/<string:meeting_id>",methods=["GET","POST"])
def status(meeting_id):
  flask.g.guest_list = manage_db.get_not_responded(meeting_id)
  return flask.render_template("status.html")
def string_of_emails(email_list):
  """
  converts a list of email addresses (str) to a single string separated
  by commas. This will be passed to guest-list.html and added to the
  'mailto' tag
  """
  return ",".join(email_list)


def list_blocks(blocks):
  """
    Creates a list of lists (time block attributes) to be used for Jinja Template
  """
  block_list = []
  for block in blocks:
    start = block.get_start_time()
    end = block.get_end_time()
    if block.get_description():
      description = block.get_description()
    else:
      description = "Free Time"
    block_list.append([description, start, end])
  return block_list

@app.template_filter( 'humanize_date' )
def humanize_month(date):
  """
    Creates a human readable date
  """
  a = arrow.get(date)
  return a.format("dddd, MM/DD/YYYY ") + "@"

@app.template_filter( 'humanize_time' )
def humanize_time(time):
  """
    Creates a human readable time
  """
  a = arrow.get(time)
  return "  " + a.format("h:mm A")

####
#
#   Initialize session variables
#
####

def init_session_values():
    """
    Start with some reasonable defaults for date and time ranges.
    Note this must be run in app context ... can't call from main. 
    """
    # Default date span = tomorrow to 1 week from now
    now = arrow.now('local')     # We really should be using tz from browser
    tomorrow = now.replace(days=+1)
    nextweek = now.replace(days=+7)
    flask.session["begin_date"] = tomorrow.floor('day').isoformat()
    flask.session["end_date"] = nextweek.ceil('day').isoformat()
    flask.session["daterange"] = "{} - {}".format(
        tomorrow.format("MM/DD/YYYY"),
        nextweek.format("MM/DD/YYYY"))
    # Default time span each day, 8 to 5
    flask.session["begin_time"] = interpret_time("8am")
    flask.session["end_time"] = interpret_time("5pm")
    flask.session["meeting_id"] = manage_db.generate_key()

def interpret_time( text ):
    """
    Read time in a human-compatible format and
    interpret as ISO format with local timezone.
    May throw exception if time can't be interpreted. In that
    case it will also flash a message explaining accepted formats.
    """
    app.logger.debug("Decoding time '{}'".format(text))
    time_formats = ["ha", "h:mma",  "h:mm a", "H:mm"]
    try: 
        as_arrow = arrow.get(text, time_formats).replace(tzinfo=tz.tzlocal())
        as_arrow = as_arrow.replace(year=2016) #HACK see below
        app.logger.debug("Succeeded interpreting time")
    except:
        app.logger.debug("Failed to interpret time")
        flask.flash("Time '{}' didn't match accepted formats 13:30 or 1:30pm"
              .format(text))
        raise
    return as_arrow.isoformat()
    
    #HACK #Workaround
    # isoformat() on raspberry Pi does not work for some dates
    # far from now.  It will fail with an overflow from time stamp out
    # of range while checking for daylight savings time.  Workaround is
    # to force the date-time combination into the year 2016, which seems to
    # get the timestamp into a reasonable range. This workaround should be
    # removed when Arrow or Dateutil.tz is fixed.
    # FIXME: Remove the workaround when arrow is fixed (but only after testing
    # on raspberry Pi --- failure is likely due to 32-bit integers on that platform)

def interpret_date( text ):
    """
    Convert text of date to ISO format used internally,
    with the local time zone.
    """
    try:
      as_arrow = arrow.get(text, "MM/DD/YYYY").replace(
          tzinfo=tz.tzlocal())
    except:
        flask.flash("Date '{}' didn't fit expected format 12/31/2001")
        raise
    return as_arrow.isoformat()

def next_day(isotext):
    """
    ISO date + 1 day (used in query to Google calendar)
    """
    as_arrow = arrow.get(isotext)
    return as_arrow.replace(days=+1).isoformat()

####
#
#  Functions (NOT pages) that return some information
#
####
  
def list_calendars(service):
    """
    Given a google 'service' object, return a list of
    calendars.  Each calendar is represented by a dict.
    The returned list is sorted to have
    the primary calendar first, and selected (that is, displayed in
    Google Calendars web app) calendars before unselected calendars.
    """
    app.logger.debug("Entering list_calendars")  
    calendar_list = service.calendarList().list().execute()["items"]
    result = [ ]
    for cal in calendar_list:
        kind = cal["kind"]
        id = cal["id"]
        if "description" in cal: 
            desc = cal["description"]
        else:
            desc = "(no description)"
        summary = cal["summary"]
        # Optional binary attributes with False as default
        selected = ("selected" in cal) and cal["selected"]
        primary = ("primary" in cal) and cal["primary"]

        result.append(
          { "kind": kind,
            "id": id,
            "summary": summary,
            "selected": selected,
            "primary": primary
            })
    return sorted(result, key=cal_sort_key)


def cal_sort_key( cal ):
    """
    Sort key for the list of calendars:  primary calendar first,
    then other selected calendars, then unselected calendars.
    (" " sorts before "X", and tuples are compared piecewise)
    """
    if cal["selected"]:
       selected_key = " "
    else:
       selected_key = "X"
    if cal["primary"]:
       primary_key = " "
    else:
       primary_key = "X"
    return (primary_key, selected_key, cal["summary"])


#################
#
# Functions used within the templates
#
#################

@app.template_filter( 'fmtdate' )
def format_arrow_date( date ):
    try: 
        normal = arrow.get( date )
        return normal.format("ddd MM/DD/YYYY")
    except:
        return "(bad date)"

@app.template_filter( 'fmttime' )
def format_arrow_time( time ):
    try:
        normal = arrow.get( time )
        return normal.format("HH:mm")
    except:
        return "(bad time)"
    
#############


if __name__ == "__main__":
  # App is created above so that it will
  # exist whether this is 'main' or not
  # (e.g., if we are running under green unicorn)
  app.run(port=CONFIG.PORT,host="0.0.0.0")
  # app.run()
    
