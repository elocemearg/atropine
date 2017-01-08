#!/usr/bin/python

import cgi;
import sys;
import os;
import cgitb;
import urllib;
import time;

import cgicommon;

cgitb.enable();
cgicommon.set_module_path();

import countdowntourney;

def int_or_none(s):
    try:
        return int(s);
    except ValueError:
        return None;

def get_tourney_modified_time(name):
    path_name = os.path.join(cgicommon.dbdir, name)
    st = os.stat(path_name)
    return st.st_mtime

baseurl = "/cgi-bin/home.py";

print "Content-Type: text/html; charset=utf-8";
print "";

cgicommon.print_html_head("Create Tourney");

form = cgi.FieldStorage();

tourneyname = form.getfirst("name", "");
order_by = form.getfirst("orderby", "mtime_d")
request_method = os.environ.get("REQUEST_METHOD", "GET");

print "<body>";
print "<h1>Welcome to Atropine</h1>";

tourney_list = os.listdir(cgicommon.dbdir);
tourney_list = filter(lambda x : (len(x) > 3 and x[-3:] == ".db"), tourney_list);
if order_by in ("mtime_a", "mtime_d"):
    tourney_list = sorted(tourney_list, key=get_tourney_modified_time, reverse=(order_by == "mtime_d"));
else:
    tourney_list = sorted(tourney_list, key=lambda x : x.lower(), reverse=(order_by == "name_d"));

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

print "<hr />"

if tourney_list:
    print "<h2>Open existing tourney</h2>";
    print "<p>";
    print "<table class=\"tourneylist\">";
    print "<tr>"
    print "<th><a href=\"/cgi-bin/home.py?orderby=%s\">Name</a></th>" % ("name_d" if order_by == "name_a" else "name_a")
    print "<th><a href=\"/cgi-bin/home.py?orderby=%s\">Last modified</a></th>" % ("mtime_a" if order_by == "mtime_d" else "mtime_d")
    print "</tr>"
    for tourney_basename in tourney_list:
        name = tourney_basename[:-3];
        filename = os.path.join(cgicommon.dbdir, tourney_basename)
        st = os.stat(filename)
        modified_time = time.localtime(st.st_mtime)
        print "<tr>"
        print '<td class=\"tourneylistname\"><a href="/cgi-bin/tourneysetup.py?tourney=%s">%s</a></td>' % (urllib.quote_plus(name), cgi.escape(name));
        print "<td class=\"tourneylistmtime\">%s</td>" % (time.strftime("%d %b %Y %H:%M", modified_time))
        print "</tr>"
    print "</table>";
    print "</p>";
else:
    print "<p>"
    print "No tourneys exist yet.";
    print "</p>"

print "<hr>"

try:
    print "<p>"
    print "Tournament database directory: <tt>%s</tt>" % (cgi.escape(os.path.realpath(cgicommon.dbdir)))
    print "</p>"
except:
    print "<p>Failed to expand tournament database directory name</p>"

print "<p>atropine version %s</p>" % (countdowntourney.SW_VERSION)

print "</body>";
print "</html>";

sys.exit(0);
