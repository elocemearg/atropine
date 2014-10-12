#!/usr/bin/python

import sys;
import cgi;

form = cgi.FieldStorage();

tourney = form.getfirst("tourney", "NONE");

print "Content-Type: text/plain; charset=utf-8";
print "";
print "Hello, world!";
print "Tourney is %s" % tourney;

sys.exit(0);
