#!/usr/bin/python
"""Arcom RC210 control - XMLRPC Client

   KD7DK/Doug, KG7AUL/CK 12/16

   Copyright 2016 Costa Katsaniotis, KG7AUL
   Released under Apache License V2.0
   http://www.apache.org/licenses/LICENSE-2.0.txt

   Reference: RCP Protocol and Serial Port Operations
   (available from the Arcom website)
"""
import getopt
import os
import re
import sys
import time
import xmlrpclib
from time import sleep
from configparser import ConfigParser
import requests

config_file = '.arcom.conf'
testing = True
verbose = 1
Valid_Options = ['testing=', 'verbose=']


class LogPSRG(object):
  """Post the event(s) to Google interference log.
     Currently, way too much stuff is hardcoded.  We need a solution
     to this that still keeps it simple for the control operator.
  """
  url_base = ''
  form_data = {}
  user_agent = {
      'User-Agent':'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36'
      }

  def __init__(self, cfg):
    self.url_base = cfg.get('google form', 'url_base')
    self.form_data['entry.773252163'] = cfg.get('arcom', 'location')
    self.form_data['entry.1984381604'] = cfg.get('arcom', 'call'),
    self.form_data['draftResponse'] = []
    self.form_data['pageHistory'] = 0
    for entry in cfg.items('google form'):
      key, value = entry
      self.form_data[key] = value
    self.user_agent['Referer'] = self.url_base + '/viewform'

  def log(self, mins):
    if not testing:
      self.form_data['entry.530211156'] = 'Yes - ' + str(mins) + ' min'
      resp = requests.post(self.url_base+'/formResponse',
                           data=self.form_data,
                           headers=self.user_agent)
      if resp.status_code == 200:
        print "Action logged to Google."
      else:
        print "Logging to Google failed: %s" % resp.status_code
    else:
      print "Action NOT logged.  (Testing mode)"


def countdown(t):
  """Count down t seconds printing the time in minutes:seconds.
     Allows users to interrupt out of the countdown.
  """
  while t:
    try:
      mins, secs = divmod(t, 60)
      timeformat = '{:02d}:{:02d}'.format(mins, secs)
      sys.stdout.write("\rCountdown: " + timeformat + "< [CTRL+C to re-enable]")
      sys.stdout.flush()
      sleep(1)
      t -= 1
    except KeyboardInterrupt:
      print ""
      break

def interact(cfg):
  """Main user interaction loop.
     We pass in a configuration object which must at a minimum have callsign (call).
  """
  arcom = xmlrpclib.ServerProxy("http://localhost:45000")
  log = LogPSRG(cfg)
  call = cfg.get('arcom', 'call')
  if not re.match(r'[A-Za-z]+\d[A-Za-z]+', call):
    print "No call specified in .arcom.conf (e.g. call = N7AAA)."
    return
  identity = arcom.getIdentity(call)

  def ask_confirm(question, default):
    """Prompt for user yes/no response with a possible default"""
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
      prompt = " [y/n] "
    elif default == "yes":
      prompt = " [Y/n] "
    elif default == "no":
      prompt = " [y/N] "
    else:
      raise ValueError("invalid default answer: '%s'" % default)

    while True:
      sys.stdout.write(question + prompt)
      choice = raw_input().lower()
      if default is not None and choice == '':
        return valid[default]
      elif choice in valid:
        return valid[choice]
      else:
        sys.stdout.write("Please respond with 'yes' or 'no' "
                         "(or 'y' or 'n').\n")

  def disable_for_minutes(minutes):
    """Disable for specified number of seconds.
       If the users interrupts the countdown, re-enable immediately.
    """
    if ask_confirm("Are you SURE? [Action will be logged.]\n", "no"):
      print "DISABLING Port 1 XMIT - %02d:00 Minutes" % minutes
      log.log(minutes)
      arcom.port1Disable(call)
      countdown(minutes*60)
      arcom.port1Enable(call)
      print "\rPort 1 XMIT RE-ENABLED"

  def printStatus(status):
    for key, value in sorted(status.items()):
      print " | %-16.16s %-27.27s |" % (key, value)

  def print_menu(status):       ## Your menu design here
    """Render the menu."""
    #TODO(dpk): we should use curses library here?
    os.system('clear') # this is expensive.
    print " ", 8 * "-", "%6.6s - Arcom RC210 Control" % identity, 8 * "-"
    printStatus(status)
    print " |", 44 * " ", "|"
    print " | 0.  Quit                                     |"
    print " | 1.  DISABLE Port 1 XMIT - 05:00 Minutes      |"
    print " | 2.  DISABLE Port 1 XMIT - 10:00 Minutes      |"
    print " | 3.  DISABLE Port 1 XMIT - 15:00 Minutes      |"
    print " | 4.  DISABLE Port 1 XMIT                      |"
    print " | 5.  ENABLE  Port 1 XMIT                      |"
    print " | 6.  UN-BRIDGE IRLP NODE Port 3</>1           |"
    print " | 7.  BRIDGE    IRLP NODE Port 3<->1           |"
    print " | 8.  RESTART CONTROLLER                       |"
    print " | 9.  SET DATE/TIME                            |"
    print " | 10. GET LAST 10 LOG ENTRIES                  |"
    print " |", 44 * " ", "|"
    print " ", 30 * "-", "KG7AUL/KD7DK", "--"

  def listLog(entries):
    """Display the log entry tuples (time, call, string)."""
    for entry in entries:
      seconds, call, string = entry
      tm = time.localtime(seconds)
      print "%s [%s] %s" % (time.strftime('%x %X', tm), call, string)

  def dispatch(line):
    """Decide what do to.  Eventually table driven?"""
    try:
      choice = int(line)
    except ValueError:
      choice = 99

    if choice is 1:
      disable_for_minutes(5)
    elif choice is 2:
      disable_for_minutes(10)
    elif choice is 3:
      disable_for_minutes(15)
    elif choice is 4:
      print "DISABLING Port 1 XMIT"
      if ask_confirm("Are you SURE?\n", "no"):
        arcom.port1Disable(call)
    elif choice is 5:
      print "ENABLING Port 1 XMIT"
      arcom.port1Enable(call)
    elif choice is 6:
      print "UN-BRIDGING IRLP NODE Port 3</>1"
      if ask_confirm("Are you SURE?\n", "no"):
        arcom.port3Unbridge(call)
    elif choice is 7:
      print "BRIDGING IRLP NODE Port 3<->1"
      arcom.port3Bridge(call)
    elif choice is 8:
      if ask_confirm("Are you SURE?\n", "no"):
        print "RESTARTING CONTROLLER"
        arcom.restart(call)
    elif choice is 9:
      arcom.setDateTime(call)
    elif choice is 10:
      entries = arcom.getLog(call, 10)
      listLog(entries)
    elif choice is 0:
      print "Exiting"
      sys.exit(0)
    else:
      # Any integer inputs other than values 1-5 we print an error message
      raw_input("Invalid option selected. Choose an option, 0-10.\nContinue? ")
      return False
    return True

  while True:
    status = arcom.status(call)
    print_menu(status)    ## Displays menu
    try:
      if dispatch(raw_input("Enter your choice [0-10]: ")):
        # This is just to keep the screen from repainting the menu.
        ask_confirm("Continue?", "yes")
    except SyntaxError:
      continue

def usage(error_msg=None):
  """Print the error and a usage message, then exit."""
  if error_msg:
    print '%s' % error_msg
  print 'Usage: %s [options] input output_prefix' % sys.argv[0]
  for option in Valid_Options:
    print '  --%s' % option
  sys.exit(1)

def main():
  """Main module - parse args and start server"""
  global testing, verbose
  defaults = {
      'location': 'Home'
  }

  try:
    opts, args = getopt.getopt(sys.argv[1:], 'v', Valid_Options)
    print 'opts = %s, args = %s' % (opts, args)
  except getopt.GetoptError, error:
    usage(error)
  for flag, value in opts:
    if flag == '--testing':
      testing = bool(value)
    if flag == '--verbose':
      verbose = int(value)
    if flag == '-v':
      verbose += 1

  home_config_file = os.path.expandvars('$HOME/'+config_file)
  cfg = ConfigParser(defaults)
  cfg.read((config_file, home_config_file))

  interact(cfg)


if __name__ == '__main__':
  main()
