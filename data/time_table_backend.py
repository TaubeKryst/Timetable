from datetime import datetime, timedelta, date
from apiclient import discovery
from oauth2client.file import Storage
from oauth2client import tools, client
import httplib2
import inspect
import os
import pickle
import sys
import time

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()

except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'

class GoogleCalendarBackend():
    """ Calendar backend for Google Calendar. Uses OAuth2.0. """
    def __init__(self, date):
        self.get_credentials()
        self.script_dir = self.get_script_dir()
        self.calendar_service = None
        self.calendar_id = None
        self.authentication_tried = False
        self.i = 0
        self.events_length = 0
        self.events = ()
        self.date = date

    def get_script_dir(self, follow_symlinks=True):
        if getattr(sys, 'frozen', False):
            path = os.path.abspath(sys.executable)
        else:
            path = inspect.getabsfile(self.get_script_dir)
        if follow_symlinks:
            path = os.path.realpath(path)
        path = os.path.dirname(path)
        if os.path.isfile(path):
            return path
        else:
            return ""

    def authenticate(self):
        self.authentication_tried = True
        try:
            self.calendar_service = self.get_calendar_service_object()
            self.calendar_id = "primary"
        except Exception as e:
            print(e)
            self.calendar_service = None
            self.calendar_id = None

    def get_credentials(self):
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'calendar-python-quickstart.json')
        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else:  # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            print('Storing credentials to ' + credential_path)

        return credentials

    def get_calendar_service_object(self):
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)
        return service

    def get_events_from_day(self, day):
        if not self.authentication_tried:
            self.authenticate()
        if not self.calendar_service or not self.calendar_id:
            return []
        timeMin = (datetime(year=day.year, month=day.month, day=day.day)).isoformat() + "Z"
        timeMax = (datetime(year=day.year, month=day.month, day=day.day) + timedelta(days=1)).isoformat() + "Z"
        response = self.calendar_service.events().list(
            fields="items/summary,items/start,items/end,items/id,items/description,items/location",
            calendarId=self.calendar_id, orderBy="startTime", singleEvents=True, timeMin=timeMin,
            timeMax=timeMax, maxResults=100).execute()
        if "items" not in response:
            self.update_cache([])
            return []
        self.update_cache(response["items"])
        return response["items"]

    def update_cache(self, events):
        path = os.path.join(self.script_dir, "event_cache")
        content = (date.today(), events)
        try:
            file_object = open(path, 'wb')
            pickle.dump(content, file_object)
            file_object.close()
        except IOError:
            print("Could not write to file %s." % path)
            return False
        print("Successfully updated event cache.")

    def get_current_situation(self):
        self.events = self.get_simple_events(self.get_events_from_day(self.date))
        self.events_length = len(self.events)
        return self.assign_events()

    def assign_events(self):
        if self.events_length < 1:
            return Situation(None, None, None)

        self.events = self.sort_events(self.events)
        if self.events_length == 1:
            return Situation(None, self.events[self.i], None)
        elif self.events_length == 2:
            if self.i == 0:
                return Situation(None, self.events[self.i], self.events[self.i+1])
            elif self.i == 1:
                return Situation(self.events[self.i-1], self.events[self.i], None)
        elif self.events_length > 2:
            if self.i == 0:
                return Situation(None, self.events[self.i], self.events[self.i + 1])
            elif self.i == self.events_length - 1:
                return Situation(self.events[self.i-1], self.events[self.i], None)
            else:
                return Situation(self.events[self.i-1], self.events[self.i], self.events[self.i+1])

    def get_simple_events(self, events):
        events_list = []
        filter_events = True
        #if filter_events is true, enter the key word
        key_word = 'konsultacje'

        for event in events:
            event = SimpleEvent().from_google_event(event)

            if not filter_events:
                events_list.append(event)
            elif event.title == key_word:
                events_list.append(event)

        return events_list

    def roll_down(self):
        if self.i > 0:
            self.i -= 1

    def roll_up(self):
        if self.i + 1 < self.events_length:
            self.i += 1

    def previous_day(self):
        current_date = datetime.now()
        if current_date.month == self.date.month and current_date.day < self.date.day:
            self.i = 0
            self.date -= timedelta(days=1)
            self.get_current_situation()
            return True
        else:
            return False

    def next_day(self):
        self.i = 0
        self.date += timedelta(days=1)
        self.get_current_situation()

    def sort_events(self, events):
        changed = True
        while changed:
            changed = False
            for i in range(len(events) -1):
                if events[i].start > events[i+1].start:
                    changed = True
                    temp = events[i+1]
                    events[i+1] = events[i]
                    events[i] = temp
        return events

    def save_date(self, event):
        # User data needed to sign up for the event
        first_name = "Tom"
        last_name = "Wood"
        index_number = "160999"

        changes = {
            'summary': event.title + " SAVED",
            'description': first_name +' '+ last_name +' '+index_number
        }
        self.calendar_service.events().patch(calendarId="primary", eventId=event.google_id, body=changes).execute()
        self.i = 0

class Situation():
    """ Represents the current situation with last, current and next event. """
    def __init__(self, last=None, current=None, next_=None):
        self.last = last
        self.current = current
        self.next = next_

    def is_freetime(self):
        return not self.current and not self.next

    def relative_position_available(self):
        return self.current or (self.last and self.next)

    def get_current_length(self):
        if self.current:
            return self.current.end - self.current.start
        if self.last and self.next:
            return self.next.start - self.last.end
        return 0

    def has_last_break(self):
        return self.last and self.current

    def has_next_break(self):
        return self.current and self.next

    def get_last_break_length(self):
        return self.current.start - self.last.end

    def get_next_break_length(self):
        return self.next.start - self.current.end

class SimpleEvent():
    """ Parses data received from the Google Calendar. """
    def __init__(self, title="", start=0, end=0, description="", location="", google_id=""):
        self.title = title
        self.description = description
        self.start = start
        self.end = end
        self.location = location
        self.google_id = google_id

    def from_google_event(self, event):
        self.title = event["summary"]
        self.start = self.convert_isodate_to_seconds(event["start"]["dateTime"], ignore_tz=True)
        self.end = self.convert_isodate_to_seconds(event["end"]["dateTime"], ignore_tz=True)
        self.description = event.get("description", "")
        self.location = event.get("location", "")
        self.google_id = event["id"]
        return self

    def convert_isodate_to_seconds(self, ts, ignore_tz=False):
        """Takes ISO 8601 format(string) and converts into epoch time."""
        if ignore_tz:
            dt = datetime.strptime(ts[:-7],'%Y-%m-%dT%H:%M:%S')
        else:
            dt = datetime.strptime(ts[:-7],'%Y-%m-%dT%H:%M:%S')+\
                        timedelta(hours=int(ts[-5:-3]),
                        minutes=int(ts[-2:]))*int(ts[-6:-5]+'1')
        seconds = time.mktime(dt.timetuple())
        return seconds