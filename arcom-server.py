#!/usr/bin/python
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
import getopt
import logging
import os
import sys
import time
from time import sleep
from configparser import ConfigParser
import serial
import weblog_Google as weblog

try:
  from xmlrpc.server import SimpleXMLRPCServer       # Python 3
except ImportError:
  from SimpleXMLRPCServer import SimpleXMLRPCServer  # Python 2

defaults = {
    'serialDevice': '/dev/ttyUSB0'
}

LOG_HISTORY_SIZE = 100
testing = False
verbose = 1
arcomDebugFile = 'arcom.commands'
logging.basicConfig(
    filename='arcom.log',
    format='%(levelname)-1s %(asctime)s %(message)s',
    level=logging.DEBUG
)
log = logging.getLogger('arcom')
cfg = ConfigParser(defaults)

class ArcomXMLRPCServer(SimpleXMLRPCServer):
  """Basic XMLRPC server class with localhost only access."""
  def verify_request(self, request, client_address):
    host, _ = client_address
    if host != '127.0.0.1':
      return False
    return SimpleXMLRPCServer.verify_request(self, request, client_address)


def load_log_entries(num_entries):
  """Read the last LOG_HISTORY_SIZE entries from log file
     and return tuples of (time, call, string) to prime
     the in memory log history.
     """
  #TODO(dpk): return log entries from log file
  return []

class Arcom(object):
  """Arcom 210 controller with serial access
     We maintain current state and interact with the serial port
     It's OK to hard code the serial setup as the Arcom serial
     settings are fixed.
     """
  def __init__(self, device):
    """open and configure serial port"""
    self.weblog = weblog.LogGoogle(cfg, testing)
    self.log_entries = load_log_entries(LOG_HISTORY_SIZE)
    self.port1Enabled = True
    self.port3Bridged = True
    self.identity = cfg.get('arcom server', 'identity')
    if not testing:
      self.serialport = serial.Serial(
          port=device,
          baudrate=9600,
          parity=serial.PARITY_NONE,
          stopbits=serial.STOPBITS_ONE,
          bytesize=serial.EIGHTBITS,
          timeout=.1
          )
    else:
      self.serialport = open(arcomDebugFile, 'w')

  def register_methods(self, server):
    """Register externally callable methods with XMLRPC server."""
    server.register_function(self.port1Disable)
    server.register_function(self.port1Enable)
    server.register_function(self.port3Unbridge)
    server.register_function(self.port3Bridge)
    server.register_function(self.restart)
    server.register_function(self.setDateTime)
    server.register_function(self.status)
    server.register_function(self.getLog)
    server.register_function(self.getIdentity)
    server.register_function(self.logInterference)

  def authlog(self, auth, string, history=True):
    """We log to a file and the in memory queue."""
    log.info('[%s] %s]', auth, string)
    if history:
      self.log_entries.append((time.time(), auth, string))
      while len(self.log_entries) > LOG_HISTORY_SIZE:
        del self.log_entries[0]

  def cmdSend(self, command):
    """Sends one command to the controller after clearing stream."""
    status = False

    def clrBuff():
      """Swallow any pending output from the controller."""
      if testing:
        return
      indata = ''
      count = 0
      while count < 5:
        indata = self.serialport.readline()
        if verbose:
          log.debug('clrBuff received: %s', indata)
        count += 1
      self.serialport.write('\r')

    clrBuff()
    sleep(0.1)
    command = '1*' + command + '\r\n'
    log.debug(' Sending: %s', command)
    self.serialport.write(command)
    if testing:
      self.serialport.flush()
      return True, 'TESTING MODE'

    sleep(0.1)
    indata = self.serialport.readline()
    print 'Received: ' + indata
    if indata.startswith("+" + command[0:5]):
      msg = 'succeeded'
      status = True
    elif indata.startswith("-" + command[0:5]):
      msg = 'failed: %s' % command
    else:
      msg = "unexpected response: %s" % command
    log.debug(msg)
    clrBuff()
    return status, msg

  def port1Disable(self, auth, interval=0):
    self.authlog(auth, 'Port 1 OFF')
    status, msg = self.cmdSend(cfg.get('arcom commands', 'port1Disable'))
    if status:
      self.port1Enabled = False
    if interval > 0:
      #TODO(dpk): implement
      pass
    return status, msg

  def port1Enable(self, auth):
    self.authlog(auth, 'Port 1 ON')
    status, msg = self.cmdSend(cfg.get('arcom commands', 'port1Enable'))
    if status:
      self.port1Enabled = True
    return status, msg

  def port3Unbridge(self, auth):
    self.authlog(auth, 'Unbridge Port 1-3')
    status, msg = self.cmdSend(cfg.get('arcom commands', 'port3Unbridge'))
    if status:
      self.port3Bridged = False
    return status, msg

  def port3Bridge(self, auth):
    self.authlog(auth, 'Bridge Port 1-3')
    status, msg = self.cmdSend(cfg.get('arcom commands', 'port3Bridge'))
    if status:
      self.port3Bridged = True
    return status, msg

  def restart(self, auth):
    self.authlog(auth, 'Restart')
    return self.cmdSend(cfg.get('arcom commands', 'restart'))

  def setDateTime(self, auth):
    self.authlog(auth, 'Set Date/Time')
    now = datetime.datetime.now()
    datestring = now.strftime('%m%d%y')
    timestring = now.strftime('%H%M%S')
    datestring = cfg.get('arcom commands', 'setDate') + datestring
    timestring = cfg.get('arcom commands', 'setTime') + timestring
    status, msg = self.cmdSend(datestring)
    if not status:
      return status, msg
    sleep(.5)
    self.cmdSend(timestring)
    if status:
      return True, "Date/Time set to (%s, %s)" % (datestring[-6:], timestring[-6:])
    else:
      return status, msg

  def logInterference(self, call, location, minutes):
    return self.weblog.log(call, location, minutes)

  def status(self, auth):
    """Non-Standard: returns status and dict"""
    self.authlog(auth, "Status Request", history=False)
    return {
        'port1Enabled': self.port1Enabled,
        'port3Bridged': self.port3Bridged,
        'testing': testing
        }

  def getLog(self, auth, num_entries):
    """Non-Standard: returns status and array"""
    self.authlog(auth, "Log Request - %d entries" % num_entries)
    return self.log_entries[-num_entries:]

  def getIdentity(self, auth):
    self.authlog(auth, 'Identity', history=False)
    return self.identity


Valid_Options = ['device=', 'pidfile=', 'port=', 'testing=', 'verbose=']

def usage(error_msg=None):
  """Print the error and a usage message, then exit."""
  if error_msg:
    print '%s' % error_msg
  print 'Usage: %s [options]' % sys.argv[0]
  for option in Valid_Options:
    print '  --%s' % option
  sys.exit(1)

def main():
  """Main module - parse args and start server"""
  global testing, verbose
  pidfile = ''
  port = 45000

  cfg.read('arcom-server.conf')
  serialDevice = cfg.get('arcom server', 'serialDevice')

  try:
    opts, args = getopt.getopt(sys.argv[1:], 'v', Valid_Options)
    log.debug('opts = %s, args = %s', opts, args)
  except getopt.GetoptError, error:
    usage(error)
  for flag, value in opts:
    if flag == '--device':
      serialDevice = value
    if flag == '--pidfile':
      pidfile = value
    if flag == '--port':
      port = int(value)
    if flag == '--testing':
      testing = value in ('True', '1', 'y')
    if flag == '--verbose':
      verbose = int(value)
    if flag == '-v':
      verbose += 1

  if pidfile:
    log.debug('pid %d, pidfile %s', os.getpid(), pidfile)
    f = open(pidfile, 'w')
    try:
      fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError, e:
      log.fatal('Unable to acquire lock on %s: %s', pidfile, e)
      sys.exit(99)
    f.write("%d\n" % os.getpid())
    f.flush()

  arcom = Arcom(serialDevice)
  server = ArcomXMLRPCServer(('', port))
  arcom.register_methods(server)
  server.serve_forever()


if __name__ == '__main__':
  main()
