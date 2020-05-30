# arcom-interface
Python based UI and Server for controlling Arcom 210 Repeater Controller via Serial

* Installation

apt-get install python3 pip3
pip3 install -r requirements.txt

cp arcom-server.conf.sample arcom-server.conf
Edit arcom-server.conf as needed
Use gen_password.py to create password entries to poplulate arcom.passwd, one user per line.

Copy the following files to your server attached to the Arcom:
arcom-server.conf arcom-server.py arcom.css arcom.passwd arcom.rc bootbox.min.js gen_password.py index.html jquery.xmlrpc*.js web_server.py weblog_Google.py
touch arcom.commands arcom.history arcom.log

Create a SSL key and put the key in pem.key

Move or copy arcom.rc to /etc/init.d or integrate with your system startup processes.

Reference: RCP Protocol and Serial Port Operations
http://www.arcomcontrollers.com/images/documents/rc210/rcpprotocol.pdf
