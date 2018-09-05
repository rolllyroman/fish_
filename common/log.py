# -*- coding: utf-8 -*-
import time
import sys
from twisted.python.log import msg
from twisted.python.logfile import DailyLogFile
import traceback
import os
#from twisted.python.lockfile import FilesystemLock, isLocked

LOG_LEVEL_DEBUG = 1
LOG_LEVEL_TEST = 2
LOG_LEVEL_RELEASE = 3
LOG_LEVEL_WARNING = 4
LOG_LEVEL_ERROR = 5

LOG_LEVEL_PREFIX = { \
    LOG_LEVEL_DEBUG : '[Debug]', \
    LOG_LEVEL_TEST : '[Test]', \
    LOG_LEVEL_RELEASE : '[Info]', \
    LOG_LEVEL_WARNING : '[Warning]', \
    LOG_LEVEL_ERROR : '[Error]' \
}
g_log_level = LOG_LEVEL_RELEASE
def setLogLevel(log_level):
    global g_log_level
    g_log_level = log_level

def log(txt, log_level = LOG_LEVEL_TEST):
    global g_log_level
    if log_level >= g_log_level:
        global LOG_LEVEL_PREFIX
        if log_level <= LOG_LEVEL_DEBUG:
            code = sys._getframe(1).f_code
            func_tag = '[%d:%s]'%(code.co_firstlineno, code.co_name)
        else:
            func_tag = ''
        try:
            msg(LOG_LEVEL_PREFIX[log_level] + func_tag + txt)
        except Exception as e:
            print 'log File error'
            print traceback.format_exc()
'''

def log(txt,log_level = LOG_LEVEL_TEST):
    LOG_PATH = os.path.join(os.path.dirname(__file__), "logs")
    log_name = datetime.strftime(datetime.now(),'%Y_%m_%d') + ".log"
    filename = os.path.join(LOG_PATH,log_name)
    time_str = str(datetime.now())
    head = log_level+"["+str(time_str)+"]"
    with open(filename,'a') as f:
        f.write(head)
        f.write(txt)
        f.write('\n')
'''

class HourLogFile(DailyLogFile):
    def __init__(self, name, directory, exist_postfix = ''):
#        if isLocked(name):
#            import os
#            base, ext = os.path.splitext(name)
#            name = base + exist_postfix + ext
#        self._lock = FilesystemLock(name)
#        self._lock.lock()
        try:
            DailyLogFile.__init__(self, name, directory)
        except Exception as e:
            print 'HourLogFile __init__ File error'
            print traceback.format_exc()
            print directory

    def close(self):
        #self._lock.unlock()
        try:
            DailyLogFile.close(self)
        except Exception as e:
            print 'HourLogFile close File error'
            print traceback.format_exc()

    def shouldRotate(self):
        """Rotate when the date has changed since last write"""
        cur_date = self.toDate()
        return cur_date > self.lastDate

    def toDate(self, *args):
        """Convert a unixtime to (year, month, day) localtime tuple,
        or return the current (year, month, day) localtime tuple.

        This function primarily exists so you may overload it with
        gmtime, or some cruft to make unit testing possible.
        """
        # primarily so this can be unit tested easily
        return time.localtime(*args)[:4]