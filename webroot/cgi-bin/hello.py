#!/usr/bin/python3

import sys;
import cgi;
import cgicommon;

form = cgi.FieldStorage();

tourney = form.getfirst("tourney", "NONE");

cgicommon.writeln("Content-Type: text/plain; charset=utf-8");
cgicommon.writeln("");
cgicommon.writeln("Hello, world!");
cgicommon.writeln("Tourney is %s" % tourney);

sys.exit(0);
