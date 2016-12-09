#!/usr/bin/python
#SuperHacky Arcom RC210 control KG7AUL/CK 11/16
#
# Copyright 2016 Costa Katsaniotis, KG7AUL
# Released under Apache License V2.0
# http://www.apache.org/licenses/LICENSE-2.0.txt
#
import requests, serial, time, datetime, select, sys, os, fileinput
from time import sleep
 
#open and configure serial port
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout = .1
)

def clrBuff():
  indata =""
  count = 0
  while (count < 5):
    indata = ser.readline()
    count +=1
  ser.write("\r") 

def cmdSend(command):
  clrBuff()
  sleep(0.1)
  command = "1*" + command + "\r"
  print " Sending: " + command
  ser.write(command)
  sleep(0.1)
  indata = ser.readline()
  print "Received: " + indata
  clrBuff()
  
def print_menu():       ## Your menu design here
    os.system('clear')
    print " ", 8 * "-" , "WW7PSR - Arcom RC210 Control" , 8  * "-"
    print " |", 44 * " " , "|"
    print " | 1. DISABLE RC210 Port 1 XMIT - 05:00 Minutes |"
    print " | 2. DISABLE RC210 Port 1 XMIT - 10:00 Minutes |"
    print " | 3. DISABLE RC210 Port 1 XMIT - 15:00 Minutes |"
    print " | 4. DISABLE RC210 Port 1 XMIT                 |"
    print " | 5.  ENABLE RC210 Port 1 XMIT                 |"
    print " | 6. UN-BRIDGE IRLP NODE Port 3</>1            |"
    print " | 7.    BRIDGE IRLP NODE Port 3< >1            |"
    print " | 8. RESTART RC210                             |"
    print " | 9. SET DATE/TIME                             |"
    print " | 0. Exit                                      |"
    print " |", 44 * " " , "|"
    print " ", 36 * "-" , "KG7AUL" , "--"

def countdown(t):
    while t:
      try:
        mins, secs = divmod(t, 60)
        timeformat = '{:02d}:{:02d}'.format(mins, secs)
        sys.stdout.write("\rCountdown: " + timeformat + "< [CTRL+C to re-enable]")
        sys.stdout.flush()
        time.sleep(1)
        t -= 1
      except KeyboardInterrupt:
        break
        print "\r\r"
def enable210():
  cmdSend('1234')

def disable210():
  cmdSend('4321')

def askConfirm(question, default):
  #print "Are you sure? (This action will be logged.)"
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
                               
def logGoogle(t):
  url = 'https://www.example.com/a/b'
  
  form_data = {'entry.1':'Now',
            'entry.2':'Didn\'t Check',
            'entry.3':'AA11',
            'entry.4':'N0CAL',
            'entry.5':'Alpha'
            'entry.6':'W1ABC/R',
            'entry.7':'Yes - ' + str(t) + ' min',
            'entry.8':'Note',
            'draftResponse':[],
            'pageHistory':0}
  user_agent = {'Referer':'https://www.example.com/a/c','User-Agent': "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36"}
  r = requests.post(url, data=form_data, headers=user_agent)
  print "Action logged."

def main():
  loop = True
  while loop:
    print_menu()    ## Displays menu
    choice = int(input("Enter your choice [1-0]: "))
    if choice==1:     
      print "DISABLING RC210 Port 1 XMIT - 05:00 Minutes"
      if askConfirm("Are you SURE? [Action will be logged.]\n", "no"):
        logGoogle(5)
        #print "She's OFF"
        disable210()
        countdown(300)
        #print "She's ON"
        enable210()
        print "\rRC210 Port 1 XMIT RE-ENABLED"
        askConfirm("Continue?", "yes")
    elif choice==2:
      print "DISABLING RC210 Port 1 XMIT - 10:00 Minutes"
      if askConfirm("Are you SURE? [Action will be logged.]\n", "no"):
        logGoogle(10)
        disable210()
        countdown(600)
        enable210()
        print "\rRC210 Port 1 XMIT RE-ENABLED"
        askConfirm("Continue?", "yes")
    elif choice==3:
      print "DISABLING RC210 Port 1 XMIT - 15:00 Minutes"
      if askConfirm("Are you SURE? [Action will be logged.]\n", "no"):
        logGoogle(15)
        disable210()
        countdown(900)
        enable210()
        print "\rRC210 Port 1 XMIT ENABLED"
        askConfirm("Continue?", "yes")
    elif choice==4:
            print "DISABLING RC210 Port 1 XMIT"
      if askConfirm("Are you SURE?\n", "no"):
        disable210()
        askConfirm("Continue?", "yes")
    elif choice==5:
      print "ENABLING Port 1 XMIT"
      enable210()
      askConfirm("Continue?", "yes")
    elif choice==6:
      print "UN-BRIDGING IRLP NODE Port 3</>1"
      if askConfirm("Are you SURE?\n", "no"):
        cmdSend('2222')
        askConfirm("Continue?", "yes")    
    elif choice==7:
      print "BRIDGING IRLP NODE Port 3</>1"
      cmdSend('3333')
      askConfirm("Continue?", "yes")
    elif choice==8:
      if askConfirm("Are you SURE?\n", "no"):
        print "RESTARTING RC210"
        cmdSend('44444')
        askConfirm("Continue?", "yes")
    elif choice==9:
      print "SETTING DATE/TIME"
      now = datetime.datetime.now()
      datestring = now.strftime("%m%d%y")  
      timestring = now.strftime("%H%M%S")
      datestring = "5555" + datestring
      timestring = "6666" + timestring
      cmdSend(datestring)
      sleep(.5)
      cmdSend(timestring)
      askConfirm("Continue?", "yes")
    elif choice==0:
      print "Exiting"
      loop=False # This will make the while loop to end as not value of loop is set to False
    else:
      # Any integer inputs other than values 1-5 we print an error message
      raw_input("Invalid option selected. Choose an option, 1-0.")  

if __name__ == '__main__':
    main()
