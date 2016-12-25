#!/usr/bin/python
"""
Test framework for web server function of arcom-server
"""
import logging
import sys
import web_server

logging.basicConfig(
    filename='arcom.log',
    format='%(levelname)-7s %(asctime)s %(threadName)s %(message)s',
    level=logging.DEBUG
)
log = logging.getLogger('')
logtostderr = True


class ArcomDummy(object):
  """Dummy Arcom 210 controller with serial access
     We maintain current state and interact with the serial port
     It's OK to hard code the serial setup as the Arcom serial
     settings are fixed.
     """
  def __init__(self):
    """open and configure serial port"""
    self.port1Enabled = True
    self.enableTimer = None
    self.port3Bridged = True
    self.identity = 'DummyArcom'

  def register_functions(self, server):
    """Register externally callable methods with XMLRPC server."""
    log.info('registering methods')
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

  def authlog(self, auth, string, history=True, level=logging.INFO):
    """We log to a file and the in memory queue."""
    log.log(level, '[%s] %s', auth, string)

  def port1Disable(self, auth, interval=0):
    msg = 'Port 1 OFF'
    if interval:
      msg += ' (with %d second timer)' % interval
    self.authlog(auth, msg)

    status, msg = True, 'success'
    self.port1Enabled = False
    return status, msg

  def port1Enable(self, auth, fromTimer=False):
    """Enable Port 1.  Like port1Disable, its protected by the same lock."""
    self.authlog(auth, 'Port 1 ON')
    status, msg = True, 'success'
    self.port1Enabled = True
    return status, msg

  def port3Unbridge(self, auth):
    self.authlog(auth, 'Unbridge Port 1-3')
    status, msg = True, 'success'
    if status:
      self.port3Bridged = False
    return status, msg

  def port3Bridge(self, auth):
    self.authlog(auth, 'Bridge Port 1-3')
    status, msg = True, 'success'
    if status:
      self.port3Bridged = True
    return status, msg

  def restart(self, auth):
    self.authlog(auth, 'Restart')
    return True, 'restart complete'

  def setDateTime(self, auth):
    self.authlog(auth, 'Set Date/Time')
    return True, 'time set'

  def logInterference(self, auth, location, minutes):
    self.authlog(auth, 'Log Interference (%s, %s, %s)' % (auth, location, minutes))
    return True

  def status(self, auth):
    """Non-Standard: returns dict"""
    self.authlog(auth, "Status Request", history=False, level=logging.INFO)
    status = {
        'port1Enabled': self.port1Enabled,
        'port3Bridged': self.port3Bridged,
        'testing': True
        'violator': 'Violator Alfa (High pitched, falsetto, singing, swearing)'
        }
    return status

  def getLog(self, auth, num_entries):
    """Non-Standard: returns an array of strings, possibly empty"""
    self.authlog(auth, "Log Request - %d entries" % num_entries)
    return []

  def getIdentity(self, auth):
    """We always log this to record invocations of the client."""
    self.authlog(auth, 'Identity')
    return self.identity

  def setViolator(self, auth, violator):
    self.authlog(auth, 'setViolator')
    return False, 'Not implemented yet.'


def main():
  if logtostderr:
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)-1s %(asctime)s %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)

  arcom = ArcomDummy()
  web_server.run_server(arcom)


if __name__ == '__main__':
  main()
