#!/usr/bin/python

import sys
import cgicommon
import urllib
import cgi
import cgitb
import re

cgitb.enable()

print "Content-Type: text/html; charset=utf-8"
print ""

form = cgi.FieldStorage()
tourney_name = form.getfirst("tourney")

cgicommon.set_module_path()

import countdowntourney

cgicommon.print_html_head("Display: " + str(tourney_name), cssfile="teleoststyle.css")

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
except countdowntourney.TourneyException as e:
    print "<body>"
    print "<p>"
    print cgi.escape(e.description)
    print "</p>"
    print "</body></html>"
    sys.exit(0)

teleost_modes = tourney.get_teleost_modes()

print "<script type=\"text/javascript\">"
print "var tourneyName = \"%s\";" % (tourney_name);

for mode in teleost_modes:
    print "var %s = %d;" % (mode["id"], mode["num"])

print "</script>"

print '<script type="text/javascript" src="/teleost.js"></script>';

print "<body class=\"display\" onload=\"displaySetup();\">"

if tourney_name is None:
    cgicommon.show_tourney_exception(countdowntourney.TourneyException("No tourney name specified."))
    print "</body>"
    print "</html>"
    sys.exit(0)

print "<div id=\"displaymainpane\">"
print "</div>"

print "</body>"
print "</html>"
