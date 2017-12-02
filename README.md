# Free Times

Displays free and busy appointment times from a selected date range of a user's Google calendar

## Installation

1. Clone it!
2. Copy credentials-skel.ini to ```/meetings/``` and fill out the GOOGLE_KEY_FILE field with a [client_secret.json](https://developers.google.com/google-apps/calendar/quickstart/python) file
3. run ```make install```
4. navigate to ```/meetings/``` and run the following command: ```python3 flask_main.py```
5. open a browser and type [http://localhost:5000/](http://localhost:5000/) into the address bar

## Author

* Jeremiah Clothier jclothie@uoregon.edu# proj8-FreeTime
# proj8-FreeTime


## Notes to Grader:
- A new "meeting_id" session variable is generated each time you visit "/" or "/index" try not to revist that webpage until you've "submitted" a meeting

- The Calendar selected MUST at least one 'busy' event within the selected time range otherwise you will get a 'NoneType' Error (I did not catch this error until
the end and didn't think it was that important considering what else needed to be done at the time)

- On the last page following your meeting submission "/emailed" make sure you save the given URL it is your key/access which will let you view: times available and who has not yet responded

- Click the mailto: tag, copy and paste the link into your browser, this will act as a new user and will work so long as the email you oauth2 was entered
by the host