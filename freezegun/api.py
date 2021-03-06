import datetime
import sys
from calendar import timegm
import functools

from dateutil import parser

real_date = datetime.date
real_datetime = datetime.datetime


class FakeTime(object):
    def __init__(self):
        import time
        self._time_mod = time
        self.active = False
        self._time = 0  # frozen time to be filled in here

    def time(self):
        ''' faked time '''
        if not self.active:
            return self._time_mod.time()
        return self._time

    def set_time_from_datetime(self, time_to_freeze):
        ''' set time to return '''
        self._time = timegm(time_to_freeze.utctimetuple())

    def __getattr__(self, name):
        ''' pass through unknowns '''
        return getattr(self._time_mod, name)


sys.modules['time'] = FakeTime()        
import time


class FakeDate(real_date):
    active = False
    date_to_freeze = None

    def __init__(self, *args, **kwargs):
        return super(FakeDate, self).__init__(*args, **kwargs)

    @classmethod
    def today(cls):
        if cls.active:
            result = cls.date_to_freeze
        else:
            result = real_date.today()
        return date_to_fakedate(result)


class FakeDatetime(real_datetime, FakeDate):
    active = False
    time_to_freeze = None
    tz_offset = None

    def __init__(self, *args, **kwargs):
        return super(FakeDatetime, self).__init__(*args, **kwargs)

    @classmethod
    def now(cls):
        if cls.active:
            result = cls.time_to_freeze + datetime.timedelta(hours=cls.tz_offset)
        else:
            result = real_datetime.now()
        return datetime_to_fakedatetime(result)

    @classmethod
    def utcnow(cls):
        if cls.active:
            result = cls.time_to_freeze
        else:
            result = real_datetime.utcnow()
        return datetime_to_fakedatetime(result)

datetime.datetime = FakeDatetime
datetime.date = FakeDate


def datetime_to_fakedatetime(datetime):
    return FakeDatetime(datetime.year,
                        datetime.month,
                        datetime.day,
                        datetime.hour,
                        datetime.minute,
                        datetime.second,
                        datetime.microsecond,
                        datetime.tzinfo)


def date_to_fakedate(date):
    return FakeDate(date.year,
                    date.month,
                    date.day)


class _freeze_time():

    def __init__(self, time_to_freeze_str, tz_offset):
        time_to_freeze = parser.parse(time_to_freeze_str)
        time.set_time_from_datetime(time_to_freeze)

        self.time_to_freeze = time_to_freeze
        self.tz_offset = tz_offset

    def __call__(self, func):
        return self.decorate_callable(func)

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()

    def start(self):
        datetime.datetime.time_to_freeze = self.time_to_freeze
        datetime.datetime.tz_offset = self.tz_offset
        datetime.datetime.active = True

        # Since datetime.datetime has already been mocked, just use that for
        # calculating the date
        datetime.date.date_to_freeze = datetime.datetime.now().date()
        datetime.date.active = True
        time.active = True

    def stop(self):
        datetime.datetime.active = False
        datetime.date.active = False
        time.active = False

    def decorate_callable(self, func):
        def wrapper(*args, **kwargs):
            with self:
                result = func(*args, **kwargs)
            return result
        functools.update_wrapper(wrapper, func)
        return wrapper


def freeze_time(time_to_freeze, tz_offset=0):
    return _freeze_time(time_to_freeze, tz_offset)
