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
import socket
import sys
import time
import xmlrpclib
from time import sleep
from configparser import ConfigParser

config_file = '.arcom.conf'
testing = True
verbose = 1


def countdown(t):
  """Count down t seconds printing the time in minutes:seconds.
     Allows users to interrupt out of the countdown.
     Returns number of seconds remaining in from t if terminated early.
  """
  while t:
    try:
      mins, secs = divmod(t, 60)
      timeformat = '{:02d}:{:02d}'.format(mins, secs)
      sys.stdout.write("\rCountdown: " + timeformat + "  [CTRL+C to re-enable]")
      sys.stdout.flush()
      sleep(1)
      t -= 1
    except KeyboardInterrupt:
      print ""
      break
  return t

def interact(port, cfg):
  """Main user interaction loop.
     We pass in a configuration object which must at a minimum have callsign (call).
  """
  arcom = xmlrpclib.ServerProxy("http://localhost:%s" % port)
  call = cfg.get('arcom', 'call')
  if not re.match(r'[A-Za-z]+\d[A-Za-z]+', call):
    raise RuntimeError('Format error for call in .arcom.conf.')
  location = cfg.get('arcom', 'location')
  identity = ''
  while identity == '':
    try:
      identity = arcom.getIdentity(call)
    except socket.error, e:
      print "Server error: %s, sleeping 5" % e
      sleep(5)

  def ask_confirm(question, default):
    """Prompt for user yes/no response with a possible default"""
    valid = {'yes': True, 'y': True, 'ye': True,
             'no': False, 'n': False}
    if default is None:
      prompt = ''
    elif default == 'yes':
      prompt = ' [Y/n] '
    elif default == 'no':
      prompt = ' [y/N] '
    else:
      raise ValueError("invalid default answer: '%s'" % default)

    while True:
      sys.stdout.write(question + prompt)
      try:
        choice = raw_input().lower()
      except (EOFError, KeyboardInterrupt):
        print ""
        sys.exit(0)

      if default is None:
        return choice
      elif choice == '':
        return valid[default]
      elif choice in valid:
        return valid[choice]
      else:
        sys.stdout.write(
            "Please respond with 'y' or 'n'.\n")

  def print_failure(command, result):
    status, msg = result
    if not status:
      print "%s failed: %s" % (command, msg)

  def disable_for_minutes(minutes):
    """Disable for specified number of seconds.
       If the users interrupts the countdown, re-enable immediately.
    """
    if ask_confirm('Are you SURE? [Action will be logged.]\n', 'no'):
      print "DISABLING Port 1 XMIT - %02d:00 Minutes" % minutes
      print_failure('port1Disable', arcom.port1Disable(call, minutes*60))
      print_failure('logInterference', arcom.logInterference(call, location, minutes))
      if countdown(minutes*60+1) > 0:
        print_failure('port1Enable', arcom.port1Enable(call))
      print ""
      return True

  def printStatus(status):
    for key, value in sorted(status.items()):
      if key == 'testing' and value:
        print " |             TESTING MODE!                    |"
      else:
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

  def successString(status):
    """Take boolean success status and return string."""
    if status:
      return "succeeded"
    else:
      return "failed"

  def dispatch(line):
    """Decide what do to.  Eventually table driven?"""
    status = False
    msg = ''

    if line == "":
      return False
    try:
      choice = int(line)
    except ValueError:
      choice = 99

    if choice is 1:
      return disable_for_minutes(5)
    elif choice is 2:
      return disable_for_minutes(10)
    elif choice is 3:
      return disable_for_minutes(15)
    elif choice is 4:
      print "DISABLING Port 1 XMIT"
      if ask_confirm("Are you SURE?\n", "no"):
        status, msg = arcom.port1Disable(call)
    elif choice is 5:
      print "ENABLING Port 1 XMIT"
      status, msg = arcom.port1Enable(call)
    elif choice is 6:
      print "UN-BRIDGING IRLP NODE Port 3</>1"
      if ask_confirm("Are you SURE?\n", "no"):
        status, msg = arcom.port3Unbridge(call)
    elif choice is 7:
      print "BRIDGING IRLP NODE Port 3<->1"
      status, msg = arcom.port3Bridge(call)
    elif choice is 8:
      if ask_confirm("Are you SURE?\n", "no"):
        print "RESTARTING CONTROLLER"
        status, msg = arcom.restart(call)
    elif choice is 9:
      status, msg = arcom.setDateTime(call)
    elif choice is 10:
      entries = arcom.getLog(call, 10)
      listLog(entries)
      return True
    elif choice is 0:
      print "Quitting"
      sys.exit(0)
    else:
      # Any other integer inputs print an error message
      ask_confirm("Invalid option selected. Choose a valid number option.\nContinue? ", None)
      return False
    print "Command %s: %s" % (successString(status), msg)
    return status

  while True:
    status = arcom.status(call)
    print_menu(status)    ## Displays menu
    choice = ask_confirm("Enter your choice [0-10]: ", None)
    try:
      if dispatch(choice):
        # This is just to keep the screen from repainting the menu.
        ask_confirm("Continue?", None)
    except SyntaxError:
      continue
    except socket.error, e:
      print "Server error: %s" % e
      ask_confirm("Continue?", None)


Valid_Options = ['port=', 'testing=', 'verbose=']

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
  port = 45000

  try:
    opts, args = getopt.getopt(sys.argv[1:], 'v', Valid_Options)
    print 'opts = %s, args = %s' % (opts, args)
  except getopt.GetoptError, error:
    usage(error)
  for flag, value in opts:
    if flag == '--port':
      port = int(value)
    if flag == '--testing':
      testing = value in ('True', '1', 'y')
    if flag == '--verbose':
      verbose = int(value)
    if flag == '-v':
      verbose += 1

  home_config_file = os.path.expandvars('$HOME/'+config_file)
  cfg = ConfigParser()
  cfg.read((config_file, home_config_file))

  interact(port, cfg)


if __name__ == '__main__':
  main()
