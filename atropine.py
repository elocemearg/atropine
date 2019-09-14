#!/usr/bin/python3

import sys;
import os;
import http.server;
import http.server;
import socketserver
import socket;
import errno;

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

http_listen_port = 3960
uploader_listen_port = 3961

os.chdir(os.path.dirname(os.path.abspath(__file__)));

sys.path.append(os.getcwd());
sys.path.append(os.path.join(os.getcwd(), "generators"));
sys.path.append(os.path.join(os.getcwd(), "py"));

os.environ["GENERATORPATH"] = os.path.join(os.getcwd(), "generators");
os.environ["CODEPATH"] = os.path.join(os.getcwd(), "py");

import uploader

uploader_service = None

try:
    uploader_service = uploader.TourneyUploaderService(uploader_listen_port)
except Exception as e:
    print("Failed to start uploader thread...")
    print(str(e))
    print("Press ENTER to exit...")
    input()
    sys.exit(1)

os.chdir("webroot");
try:
    server_address = ('', http_listen_port);
    httpd = ThreadedHTTPServer(server_address, http.server.CGIHTTPRequestHandler);
    print("Tourney web server");
    print()
    print("Browser link: http://localhost:" + str(http_listen_port) + "/cgi-bin/home.py")
    print()
    httpd.serve_forever();
except socket.error as e:
    err = e.args[0];
    if err == errno.EADDRINUSE:
        print("Address localhost:%d is already in use." % http_listen_port);
        print();
        print("Perhaps there is another instance of Atropine running?")
        print("If so, close it before attempting to start a new one.")
        print();
    else:
        print(str(e))
    print("Press ENTER to exit...");
    input();

sys.exit(0);
