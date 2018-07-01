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

tourney = None

cgicommon.set_module_path()

import countdowntourney

cgicommon.print_html_head("Display: " + str(tourney_name), cssfile="teleoststyle.css")

print "<script type=\"text/javascript\">"
print "var tourneyName = \"%s\";" % (tourney_name);

print "var TELEOST_MODE_AUTO = %d;" % (countdowntourney.TELEOST_MODE_AUTO);
print "var TELEOST_MODE_STANDINGS = %d;" % (countdowntourney.TELEOST_MODE_STANDINGS);
print "var TELEOST_MODE_STANDINGS_VIDEPRINTER = %d;" % (countdowntourney.TELEOST_MODE_STANDINGS_VIDEPRINTER);
print "var TELEOST_MODE_STANDINGS_RESULTS = %d;" % (countdowntourney.TELEOST_MODE_STANDINGS_RESULTS);
print "var TELEOST_MODE_TECHNICAL_DIFFICULTIES = %d;" % (countdowntourney.TELEOST_MODE_TECHNICAL_DIFFICULTIES);
print "var TELEOST_MODE_FIXTURES = %d;" % (countdowntourney.TELEOST_MODE_FIXTURES);
print "var TELEOST_MODE_TABLE_NUMBER_INDEX = %d;" % (countdowntourney.TELEOST_MODE_TABLE_NUMBER_INDEX);
print "var TELEOST_MODE_OVERACHIEVERS = %d;" % (countdowntourney.TELEOST_MODE_OVERACHIEVERS);
print "var TELEOST_MODE_TUFF_LUCK = %d;" % (countdowntourney.TELEOST_MODE_TUFF_LUCK);
print "var TELEOST_MODE_RECORDS = %d;" % (countdowntourney.TELEOST_MODE_RECORDS);
print "var TELEOST_MODE_FASTEST_FINISHERS = %d;" % (countdowntourney.TELEOST_MODE_FASTEST_FINISHERS);

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
