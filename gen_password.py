#!/usr/bin/env python2
"""
Generate entries for arcom.password file.
"""
import hashlib
import sys

def main():
  sys.stdout.write('user: ')
  call = sys.stdin.readline().strip()
  sys.stdout.write('password: ')
  password = sys.stdin.readline().strip()
  print '%s:%s' % (call, hashlib.sha224('arcom%s%s' % (call, password)).hexdigest())

if __name__ == '__main__':
  main()
