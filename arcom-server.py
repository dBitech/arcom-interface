#!/usr/bin/python2
"""Arcom RC210 control - XMLRPC Server

   KD7DK/Doug, KG7AUL/CK 12/16

   Copyright 2016 Costa Katsaniotis, KG7AUL
   Released under Apache License V2.0
   http://www.apache.org/licenses/LICENSE-2.0.txt

   Reference: RCP Protocol and Serial Port Operations
   http://www.arcomcontrollers.com/images/documents/rc210/rcpprotocol.pdf

"""
import datetime
import fcntl
import optparse
import logging
import logging.handlers
import os
import pickle
import signal
import sys
import threading
import time
from time import sleep
from configparser import ConfigParser
import serial
import weblog_Google as weblog
import web_server

configDefaults = {
    'serialDevice': '/dev/ttyUSB0'
}

LOG_HISTORY_SIZE = 100
debugFile = 'arcom.commands'
historyFile = 'arcom.history'
logFile = 'arcom.log'
logFormat = '%(levelname)-7s %(asctime)s %(threadName)s %(message)s'
"""
logging.basicConfig(
    format=logFormat,
    level=logging.INFO,
)
"""
log = logging.getLogger('arcom')
log.addHandler(logging.handlers.RotatingFileHandler(
    logFile, maxBytes=512*1024, backupCount=5))


class Arcom(object):
  """Arcom 210 controller with serial access
     We maintain current state and interact with the serial port
     It's OK to hard code the serial setup as the Arcom serial
     settings are fixed.
     """
  def __init__(self, opt, cfg):
    """open and configure serial port"""
    self.cfg = cfg
    self.testing = opt.testing
    self.weblog = weblog.LogGoogle(cfg, opt.testing)
    self.arcomLock = threading.Lock()
    self.port1Lock = threading.Lock()
    self.port1Enabled = True
    self.enableTimer = None
    self.port3Bridged = True
    self.identity = cfg.get('arcom server', 'identity')
    self.autoEnableTime = None
    self.load_history(LOG_HISTORY_SIZE)
    if not opt.testing:
      self.serialport = serial.Serial(
          port=opt.device,
          baudrate=9600,
          parity=serial.PARITY_NONE,
          stopbits=serial.STOPBITS_ONE,
          bytesize=serial.EIGHTBITS,
          timeout=.1
          )
    else:
      self.serialport = open(debugFile, 'w')

  def register_functions(self, server):
    """Register externally callable methods with XMLRPC server."""
    server.register_function(self.port1Disable)
    server.register_function(self.port1Enable)
    server.register_function(self.port3Unbridge)
    server.register_function(self.port3Bridge)
    server.register_function(self.restart)
    server.register_function(self.setDateTime)
    server.register_function(self.status)
    server.register_function(self.getLog)
    server.register_function(self.logInterference)
    server.register_function(self.setViolator)

  def authlog(self, auth, string, history=True, level=logging.INFO):
    """We log to a file and the in memory queue."""
    log.log(level, '[%s] %s', auth, string)
    if history:
      self.history.append((time.time(), auth, string))
      while len(self.history) > LOG_HISTORY_SIZE:
        del self.history[0]
      try:
        with open(historyFile, "w") as f:
          pickle.dump(self.history, f)
      except IOError as e:
        log.error('dumping to %s: %s', historyFile, e)

  def load_history(self, num_entries):
    """Read pickled entries from history file and initialize
       self.history with tuples of (time, call, string).
       Truncate to the max size.
       """
    log.debug('Loading max of %d log entries.', num_entries)
    try:
      with open(historyFile) as f:
        self.history = pickle.load(f)
    except IOError as e:
      log.error('error loading %s: %s', historyFile, e)
      self.history = []
    while len(self.history) > LOG_HISTORY_SIZE:
      del self.history[0]
    log.info('Loaded %d entries to history', len(self.history))


  def cmdSend(self, command):
    """Sends one command to the controller after clearing stream.
       This interaction with the Arcom controller is protected
       by a lock since we have some asynchronous activites in
       separate threads (like re-enabling after a timeout).
       """
    status = False

    def clrBuff():
      """Swallow any pending output from the controller."""
      if self.testing:
        return
      indata = ''
      count = 0
      while count < 5:
        indata = self.serialport.readline()
        log.debug('clrBuff received: %s', indata)
        count += 1
      self.serialport.write('\r')

    self.arcomLock.acquire()
    clrBuff()
    sleep(0.1)
    command = '1*' + command + '\r\n'
    log.debug(' Sending: %s', command)
    self.serialport.write(str(command))
    if self.testing:
      self.serialport.flush()
      self.arcomLock.release()
      return True, 'TESTING MODE'

    sleep(0.1)
    indata = self.serialport.readline()
    log.debug('received from arcom: ' + indata)
    if indata.startswith("+"):
      msg = 'succeeded'
      status = True
    elif indata.startswith("-"):
      msg = 'failed: %s' % command
    else:
      msg = "unexpected response: %s" % indata
    log.debug(msg)
    clrBuff()
    self.arcomLock.release()
    return status, msg

  def port1Disable(self, auth, interval=0):
    """Disable Port 1 (the main repeater) and optionally set enable timer
       We always disable in case our state is out of sync, then
       if there is not already a enableTimer running, we create and
       start one.  This will re-enable the repeater after interval seconds.
       Manipulation of port 1 is protected with a lock.
       """
    self.port1Lock.acquire()
    msg = 'Port 1 OFF'
    if interval:
      msg += ' (with %d second timer)' % interval
    if self.enableTimer:
      secs_left = int(self.autoEnableTime - time.time())
      log.info('[%s] Timed disable already active (%d secs left)', auth, secs_left)
      self.port1Lock.release()
      return False, "Timed disable already active (%d secs left)" % secs_left
    self.authlog(auth, msg)
    status, msg = self.cmdSend(self.cfg.get('arcom commands', 'port1Disable'))
    if status:
      self.port1Enabled = False
      if interval > 0:
        if not self.enableTimer:
          log.info('[%s] Setting enable timer for %d seconds', auth, interval)
          self.enableTimer = threading.Timer(interval, self.port1Enable, [auth, True])
          self.enableTimer.start()
          self.autoEnableTime = time.time() + float(interval)
    self.port1Lock.release()
    return status, msg

  def port1Enable(self, auth, fromTimer=False):
    """Enable Port 1.  Like port1Disable, its protected by the same lock."""
    self.port1Lock.acquire()
    if fromTimer:
      log.info('[%s] Timer expired, re-enabling repeater', auth)
    self.authlog(auth, 'Port 1 ON')
    status, msg = self.cmdSend(self.cfg.get('arcom commands', 'port1Enable'))
    if status:
      self.port1Enabled = True
    if self.enableTimer:
      log.info('[%s] Timer cancelled', auth)
      self.enableTimer.cancel()
      self.enableTimer = None
      self.autoEnableTime = None
    self.port1Lock.release()
    return status, msg

  def port3Unbridge(self, auth):
    self.authlog(auth, 'Unbridge Port 1-3')
    status, msg = self.cmdSend(self.cfg.get('arcom commands', 'port3Unbridge'))
    if status:
      self.port3Bridged = False
    return status, msg

  def port3Bridge(self, auth):
    self.authlog(auth, 'Bridge Port 1-3')
    status, msg = self.cmdSend(self.cfg.get('arcom commands', 'port3Bridge'))
    if status:
      self.port3Bridged = True
    return status, msg

  def restart(self, auth):
    self.authlog(auth, 'Restart')
    _, _ = self.cmdSend(self.cfg.get('arcom commands', 'restart'))
    return True, 'Restarting...'

  def setDateTime(self, auth):
    self.authlog(auth, 'Set Date/Time')
    now = datetime.datetime.now()
    datestring = now.strftime('%m%d%y')
    timestring = now.strftime('%H%M%S')
    datestring = self.cfg.get('arcom commands', 'setDate') + datestring
    timestring = self.cfg.get('arcom commands', 'setTime') + timestring
    status, msg = self.cmdSend(datestring)
    if not status:
      return status, msg
    sleep(.5)
    self.cmdSend(timestring)
    if status:
      return True, "Date/Time set to (%s, %s)" % (datestring[-6:], timestring[-6:])
    else:
      return status, msg

  def logInterference(self, auth, location, seconds):
    self.authlog(auth, 'Log Interference %s, %d seconds' % (location, seconds))
    return self.weblog.log(auth, location, seconds/60)

  def status(self, auth):
    """Non-Standard: returns dict"""
    self.authlog(auth, "Status Request", history=False, level=logging.DEBUG)
    status = {
        'identity': self.identity,
        'port1Enabled': self.port1Enabled,
        'port3Bridged': self.port3Bridged,
        }
    if self.testing:
      status['testing'] = True
    if self.autoEnableTime:
      status['auto-enable'] = self.autoEnableTime
    return status

  def getLog(self, auth, num_entries):
    """Non-Standard: returns an array of strings, possibly empty"""
    self.authlog(auth, "Log Request - %d entries, returning %d" % (
        num_entries, len(self.history[-num_entries:])))
    return self.history[-num_entries:]

  def setViolator(self, auth, violator):
    #TODO(dpk): implement violator setting
    self.authlog(auth, 'setViolator to "%s"', violator)
    return False, 'Not implemented yet.'


def die(_signum, _frame):
  """Exit gracefully.  Generally from SIGINTR while testing."""
  sys.exit(0)

def main():
  """Main module - parse args and start server"""
  cfg = ConfigParser(configDefaults)
  cfg.read('arcom-server.conf')

  p = optparse.OptionParser()

  p.add_option('--device', action='store', type='string', dest='device')
  p.add_option('--logtostderr', action='store_true', dest='logtostderr')
  p.add_option('--pidfile', action='store', type='string', dest='pidfile')
  p.add_option('--port', action='store', type='int', dest='port')
  p.add_option('--testing', action='store_true', dest='testing')
  p.add_option('--verbose', action='store', type='int', dest='verbose')
  p.add_option('-v', action='count', dest='verbose')

  p.set_defaults(device=cfg.get('arcom server', 'serialDevice'),
                 logtostderr=False,
                 pidfile='',
                 port=3333,
                 testing=False)

  opt, _ = p.parse_args()

  if opt.verbose > 1:
    log.setLevel(logging.DEBUG)

  # Create a second handler to log to the console.
  formatter = logging.Formatter(logFormat)
  if opt.logtostderr:
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    log.addHandler(handler)

  # More than a pidfile, we use locking to ensure exclusive access.
  if opt.pidfile:
    log.debug('pid %d, pidfile %s', os.getpid(), opt.pidfile)
    f = open(opt.pidfile, 'w')
    try:
      fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError, e:
      log.fatal('Unable to acquire lock on %s: %s', opt.pidfile, e)
      sys.exit(99)
    f.write("%d\n" % os.getpid())
    f.flush()

  signal.signal(signal.SIGINT, die)
  arcom = Arcom(opt, cfg)
  web_server.run_server(arcom, opt)


if __name__ == '__main__':
  main()
