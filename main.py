from datetime import datetime, timedelta
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
import kivy.base
import time
from data.time_table_backend import GoogleCalendarBackend
import data.animations

class timetable(App):

    def build(self):
        self.time_table_backend = GoogleCalendarBackend(datetime.today())
        self.situation = (None, None, None)
        self.current_card = None
        self.lock = False
        self.counter = 0
        self.gui = GUI()
        self.gui.scroll_view.bind(scroll_y=self.on_scroll)
        self.gui.left_button.bind(on_press = self.previous_day)
        self.gui.right_button.bind(on_press=self.next_day)
        self.get_situation()
        Clock.schedule_interval(self.update_timer, 1)
        return self.gui

    def get_situation(self, trigger=None, value=None):
        self.situation = self.time_table_backend.get_current_situation()
        self.build_gui_situation()

    def build_gui_situation(self):
        self.clear_gui()
        gui = self.gui
        situation = self.situation

        if situation.last:
            card = NoneCurrentEventCard(situation.last)
            gui.layout_last_event.add_widget(card)
        if situation.current:
            card = CurrentEventCard(situation.current, self.time_table_backend, self)
            gui.layout_current_event.add_widget(card)
            self.current_card = card
        else:
            card = BreakCard()
            gui.layout_current_event.add_widget(card)
            self.current_card = card

        if situation.next:
            card = NoneCurrentEventCard(situation.next)
            gui.layout_next_event.add_widget(card)
        if situation.has_last_break():
            gui.last_break_label.text = self.format_time_as_break(situation.get_last_break_length())
        if situation.has_next_break():
            gui.next_break_label.text = self.format_time_as_break(situation.get_next_break_length())

    def clear_gui(self):
        gui = self.gui
        gui.layout_last_event.clear_widgets()
        gui.layout_current_event.clear_widgets()
        gui.layout_next_event.clear_widgets()
        gui.last_break_label.text = ""
        gui.next_break_label.text = ""

    def update_timer(self, trigger=None, value=None):
        situation = self.situation
        time_left = self.get_time_left(situation)

        if self.current_card:
            if situation.is_freetime():
                date = self.time_table_backend.date
                time_left_string = "\n\n{:d}-{:d}-{:d}".format(date.day, date.month, date.year)
            else:
                time_left_string = self.format_time_in_seconds(self.get_time_left(situation))
            self.current_card.time_left_string = time_left_string
            if situation.relative_position_available():
                current_length = situation.get_current_length()
                self.current_card.marker_pos = float(current_length - time_left) / current_length

        if self.lock == True:
            self.counter += 1
            if self.counter > 1:
                self.lock = False
                self.counter = 0

    def get_time_left(self, situation):
        if situation.current:
            # time till end of current event
            return situation.current.end - time.time()
        elif situation.next:
            # time till end of break
            return situation.next.start - time.time()
        else:
            # time till end of day
            day = datetime.now() + timedelta(days=1)
            dt = datetime(year=day.year, month=day.month, day=day.day)
            end_of_day = time.mktime(dt.timetuple())
            return end_of_day - time.time()

    def format_time_in_seconds(self, time):
        hours = int(time / 3600)
        minutes = int((time - hours * 3600) / 60)
        sec = int(time - hours * 3600 - minutes * 60)
        if hours:
            return "{}h {:2}m {:2}s left".format(hours, minutes, sec)
        if minutes:
            return "{}m {:2}s left".format(minutes, sec)
        return "{}s left".format(sec)

    def format_time_as_break(self, time):
        hours = int(time / 3600)
        minutes = int((time - hours * 3600) / 60)
        if hours:
            if minutes:
                return "{}h {:2}min".format(hours, minutes)
            return "{} h".format(hours)
        return "{} min".format(minutes)

    def on_scroll(self, trigger=None, value=None):
        touches = len(kivy.base.EventLoop.touches)

        if self.lock == False:
            if value < -10 and not touches:
                self.time_table_backend.roll_up()
                self.situation = self.time_table_backend.assign_events()
                self.build_gui_situation()
                self.lock = True
            elif value > 10 and not touches:
                self.time_table_backend.roll_down()
                self.situation = self.time_table_backend.assign_events()
                self.build_gui_situation()
                self.lock = True

    def previous_day(self, instance):
        if self.time_table_backend.previous_day():
            self.situation = self.time_table_backend.assign_events()
            self.build_gui_situation()

    def next_day(self, instance):
        self.time_table_backend.next_day()
        self.situation = self.time_table_backend.assign_events()
        self.build_gui_situation()

class GUI(FloatLayout):
    last_event_string = StringProperty("")
    current_event_string = StringProperty("")
    next_event_string = StringProperty("")

class NoneCurrentEventCard(BoxLayout):
    """ Layout of a card that displays title,
    start time, end time, date and location"""
    start_time = StringProperty("")
    end_time = StringProperty("")
    title = StringProperty("")
    description = StringProperty("")
    location = StringProperty("")

    def __init__(self, event, **kwargs):
        super(NoneCurrentEventCard, self).__init__(**kwargs)
        self.title = event.title
        time_to_format = datetime.fromtimestamp(event.start)
        self.description = "{:d}-{:d}-{:d}".format(time_to_format.day, time_to_format.month, time_to_format.year)
        self.location = event.location
        time_to_format = datetime.fromtimestamp(event.start)
        self.start_time = "{:d}:{:02d}".format(time_to_format.hour, time_to_format.minute)
        time_to_format = datetime.fromtimestamp(event.end)
        self.end_time = "{:d}:{:02d}".format(time_to_format.hour, time_to_format.minute)

class CurrentEventCard(BoxLayout):
    """ Layout of a card that displays title,
    start time, end time, date, location and
    button to sign up for the event"""
    start_time = StringProperty("")
    end_time = StringProperty("")
    title = StringProperty("")
    description = StringProperty("")
    location = StringProperty("")
    time_left_string = StringProperty("")
    marker_pos = NumericProperty(0)
    def __init__(self, event, time_table_backend, calendar, **kwargs):
        super(CurrentEventCard, self).__init__(**kwargs)
        self.event = event
        self.calendar = calendar
        self.title = event.title
        self.location = event.location
        time_to_format = datetime.fromtimestamp(event.start)
        self.description = "{:d}-{:d}-{:d}".format(time_to_format.day, time_to_format.month, time_to_format.year)
        self.start_time = "{:d}:{:02d}".format(time_to_format.hour, time_to_format.minute)
        time_to_format = datetime.fromtimestamp(event.end)
        self.end_time = "{:d}:{:02d}".format(time_to_format.hour, time_to_format.minute)
        self.time_table_backend = time_table_backend

    def choose_date(self):
        self.time_table_backend.save_date(self.event)
        self.calendar.situation = self.time_table_backend.get_current_situation()
        self.calendar.build_gui_situation()

class BreakCard(AnchorLayout):
    """ Layout that informs that there are no
    events on that day"""
    time_left_string = StringProperty("")
    marker_pos = NumericProperty(0)

if __name__ in ('__android__', '__main__'):
    timetable().run()