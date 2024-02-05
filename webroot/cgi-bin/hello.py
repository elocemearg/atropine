#!/usr/bin/python3

import sys;
import cgicommon;

form = cgicommon.FieldStorage();

tourney = form.getfirst("tourney", "NONE");

cgicommon.writeln("Content-Type: text/plain; charset=utf-8");
cgicommon.writeln("");
cgicommon.writeln("Hello, world!");
cgicommon.writeln("Tourney is %s" % tourney);

sys.exit(0);
