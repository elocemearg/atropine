#!/usr/bin/python

import sys;
import os;
import BaseHTTPServer;
import CGIHTTPServer;
import socket;
import errno;

listen_port = 3960;

os.chdir(os.path.dirname(os.path.abspath(__file__)));

sys.path.append(os.getcwd());
sys.path.append(os.path.join(os.getcwd(), "generators"));
sys.path.append(os.path.join(os.getcwd(), "py"));

os.environ["GENERATORPATH"] = os.path.join(os.getcwd(), "generators");
os.environ["CODEPATH"] = os.path.join(os.getcwd(), "py");

os.chdir("webroot");

try:
	server_address = ('', listen_port);
	httpd = BaseHTTPServer.HTTPServer(server_address, CGIHTTPServer.CGIHTTPRequestHandler);
	print "Tourney web server";
	print
	print "Browser link: http://localhost:" + str(listen_port) + "/cgi-bin/home.py"
	httpd.serve_forever();
except socket.error as e:
	err = e.args[0];
	if err == errno.EADDRINUSE:
		print "Address localhost:%d is already in use." % listen_port;
		print;
		print "Perhaps there is another instance of Atropine running?"
		print "If so, close it before attempting to start a new one."
		print;
	print "Press ENTER to exit...";
	raw_input();

sys.exit(0);
