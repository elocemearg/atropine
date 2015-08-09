#!/usr/bin/python

import cgi;
import sys;
import os;
import cgitb;
import urllib;

import cgicommon;

cgitb.enable();
cgicommon.set_module_path();

import countdowntourney;

def int_or_none(s):
    try:
        return int(s);
    except ValueError:
        return None;

baseurl = "/cgi-bin/home.py";

print "Content-Type: text/html; charset=utf-8";
print "";

cgicommon.print_html_head("Create Tourney");

form = cgi.FieldStorage();

tourneyname = form.getfirst("name", "");
request_method = os.environ.get("REQUEST_METHOD", "GET");

print "<body>";
print "<h1>Welcome to Atropine</h1>";

tourney_list = os.listdir(cgicommon.dbdir);
tourney_list = filter(lambda x : (len(x) > 3 and x[-3:] == ".db"), tourney_list);
tourney_list = sorted(tourney_list);

if tourney_list:
    print "<h2>Existing tourneys</h2>";
    print "<p>";
    print "<table>";
    for tourney in tourney_list:
        name = tourney[:-3];
        print '<tr><td><a href="/cgi-bin/tourneysetup.py?tourney=%s">%s</a></td></tr>' % (urllib.quote_plus(name), cgi.escape(name));
    print "</table>";
    print "</p>";
else:
    print "<p>"
    print "No tourneys exist yet.";
    print "</p>"

tourney_created = False;

if request_method == "POST" and tourneyname:
    try:
        tourney = countdowntourney.tourney_create(tourneyname, cgicommon.dbdir);
        tourney.close();
        print "<p>Tourney \"%s\" was created successfully.</p>" % tourneyname;
        print "<p>";
        print '<a href="/cgi-bin/tourneysetup.py?tourney=%s">Click here to continue</a>' % urllib.quote_plus(tourneyname);
        print "</p>";
        tourney_created = True;
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);

if not tourney_created:
    # If name has been filled in, attempt to create tourney

    print "<h2>Create new tourney</h2>";
    print '<form action="%s" method="POST">' % cgi.escape(baseurl, True);
    print "<p>";
    print 'Tourney name: <input type="text" name="name" value="%s" /> <br />' % cgi.escape(tourneyname, True);
    print "</p>";
    print "<p>";
    print '<input type="submit" name="submit" value="Create Tourney" />';
    print "</p>";
    print "</form>";

print "<hr>"
print "<p>atropine version %s</p>" % (countdowntourney.SW_VERSION)

print "</body>";
print "</html>";

sys.exit(0);
