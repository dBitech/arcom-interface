#!/usr/bin/python
"""Arcom RC210 control - Test harness for weblog

   KD7DK/Doug, KG7AUL/CK 12/16

   Copyright 2016 Costa Katsaniotis, KG7AUL
   Released under Apache License V2.0
   http://www.apache.org/licenses/LICENSE-2.0.txt  
"""
from configparser import ConfigParser
import weblog_Google as weblog

defaults = {
    'serialDevice': '/dev/ttyUSB0'
}

cfg = ConfigParser(defaults)


def main():
  """Main module - parse args and start server"""
  global testing, verbose

  cfg.read('arcom-server.conf')

  w = weblog.LogGoogle(cfg, False)
  print 'status %s: %s' % w.log('KD7DK/TEST', 'CN87tq', 5)


if __name__ == '__main__':
  main()
