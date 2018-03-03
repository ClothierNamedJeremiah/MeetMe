# Meet Me

Displays free and busy appointment times from a selected date range of a user's Google calendar

## Description
This is essentially “a better Doodle”, providing a better user experience in meeting scheduling by leveraging information about their schedules. The scheduler will be useable on mobile phones as well as tablets, desktops, and laptop computers. It allows participants to use their Google calendar information in meeting scheduling without exposing more information than they choose, and it will be usable for participants who do not have a Google calendar or choose not to use it. Establishing an account with the service is required for the proposer of a meeting, but not for other participants.

## Notes to Grader:
### It's the Alpha, what's Missing?
* On the final webpage *status.html* the available times are not displayed.
  * All the busy time blocks for each responded user are stored in the MongoDB, but the final calculation at the end has not yet been implemented
  
* The Application cannot run outside of *localhost:5000/*
  * My efforts fell short on both attempts 1. http://clothiernamedjeremiah.pythonanywhere.com/ 2. https://agile-chamber-64682.herokuapp.com/
  * I thought deploying my app to the web would be a simple process which I could save till the end. Apparently it wasn't so simple and after two hours of trying I gave up
  * I don't blame anyone but myself for this. A suggestion for future classes, it may be a good idea to have students deploy their application at the very beginning. For example, during proj7 when they are calculating busy times

### How do I run the application?
1. Clone it!
2. Copy credentials.ini to ```/meetings/``` and fill out the GOOGLE_KEY_FILE field with a [client_secret.json](https://developers.google.com/google-apps/calendar/quickstart/python) file
3. Additionally, you will need a client_secret.json file in the ```/meetings/``` repository
4. Run the following commands to get the application running
    * In the MeetMe repository run the ```make install``` command in bash
    * ```source env/bin/active```
    * ```cd meetings/```
    * ```python3 flask_main.py``` following these commands the application will be ruuning on http://0.0.0.0:5000/

#### Interacting with the Application once it's running
1. On the very first webpage you will be asked to select and confirm a date and time range for which your meeting will lie within. Upon clicking the "Choose Date & Time Range" you will be asked to log in to your Google Account
    * Note: it is reccommend that you run the application in a new incognito browser window to simulate a "new user" or "invitee"
 2. After logging into your Google Account you will be shown a list of your account's calendars. Select one or more of the given calendars by clicking the checkbox beside its name and then clicking the *Select Calendar(s)* button.
    * Note: The Calendar selected MUST contain at least one 'busy' event within the selected time range otherwise you will get a NoneType Error when the program tries to calculate your busy times (I did not encounter this bug until it was too late to fix).
 3. Upon selecting a Calendar you will shown your available times blocks. If you want to change calendars and experiment with the time blocks that is allowed, but once you have found a good calendar then you need to click *Creat a Guest List*
 4. The next webpage will allow you to set a meeting duration and enter in the email address (your personal email address) you would like to recieve updates on.
 5. on the ```/guest_list``` webpage you can add email addresses, delete email addresses and send a *template* email to everyone on the email list
    * Note: the *invite link* will be is part of the email, to gain access of the invitees perspective you must copy and paste that link into you approriate browser (a new icognito tab works best to "simulate" a new user)
    * Once you have saved the *invite link* and emailed the recipeint's you may click the Done Button
      * Aside: the MongoDB is not created until the *Done* button has been selected, therefore it is best to not proceed with any steps on the ```invite/``` link until you have clicked the aforementioned button
#### The Application now "splits" into two paths, the Host's Page and the Invitee's Page 
1. On the Host's webpage *(link displayed on the webpage ```emailed/```)* you will be able to see who has not yet responded and a list of timeslots for potential meetings 
2. On the Invitee's webpage *(link copied from the mailto: email template in step 5)* a user will enter in their email address and then select from a list of personal 
3. *NOT YET IMPLEMENTED* The Host can select a timeslot and an email will be sent out to everyone notifying them of the selected date/time


## Author

* Jeremiah Clothier jclothie@uoregon.edu
