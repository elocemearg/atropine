#!/usr/bin/python3

import cgi;
import sys;
import os;
import cgitb;
import urllib.request, urllib.parse, urllib.error;
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

def print_tourney_table(tourney_list, destination_page, show_last_modified, show_export_html_link=False, show_display_link=False):
    cgicommon.writeln("<table class=\"tourneylist\">");
    cgicommon.writeln("<tr>")
    cgicommon.writeln("<th><a href=\"/cgi-bin/home.py?orderby=%s\">Name</a></th>" % ("name_d" if order_by == "name_a" else "name_a"))

    if show_last_modified:
        cgicommon.writeln("<th><a href=\"/cgi-bin/home.py?orderby=%s\">Last modified</a></th>" % ("mtime_a" if order_by == "mtime_d" else "mtime_d"))

    if show_display_link or show_export_html_link:
        cgicommon.writeln("<th colspan=\"%d\">Useful links</th>" % ( 2 if show_display_link and show_export_html_link else 1 ))

    cgicommon.writeln("</tr>")
    for tourney_basename in tourney_list:
        name = tourney_basename[:-3];
        filename = os.path.join(cgicommon.dbdir, tourney_basename)
        st = os.stat(filename)
        modified_time = time.localtime(st.st_mtime)
        cgicommon.writeln("<tr>")
        cgicommon.writeln('<td class=\"tourneylistname\">')
        if destination_page:
            cgicommon.writeln('<a href="%s?tourney=%s">%s</a>' % (cgicommon.escape(destination_page, True), urllib.parse.quote_plus(name), cgicommon.escape(name)));
        else:
            cgicommon.writeln(cgicommon.escape(name))
        cgicommon.writeln('</td>')

        if show_last_modified:
            cgicommon.writeln("<td class=\"tourneylistmtime\">%s</td>" % (time.strftime("%d %b %Y %H:%M", modified_time)))

        if show_export_html_link:
            cgicommon.writeln("<td class=\"tourneylistlink\">")
            cgicommon.writeln("<a href=\"/cgi-bin/export.py?tourney=%s&format=html\">Tourney report</a>" % (urllib.parse.quote_plus(name)))
            cgicommon.writeln("</td>")
        if show_display_link:
            cgicommon.writeln("<td class=\"tourneylistlink\">")
            cgicommon.writeln("<a href=\"/cgi-bin/display.py?tourney=%s\">Full screen display</a>" % (urllib.parse.quote_plus(name)))
            cgicommon.writeln("</td>")

        cgicommon.writeln("</tr>")
    cgicommon.writeln("</table>");

baseurl = "/cgi-bin/home.py";

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

cgicommon.print_html_head("Create Tourney" if cgicommon.is_client_from_localhost() else "Atropine");

form = cgi.FieldStorage();

tourneyname = form.getfirst("name", "");
order_by = form.getfirst("orderby", "mtime_d")
request_method = os.environ.get("REQUEST_METHOD", "GET");

cgicommon.writeln("<body>");
cgicommon.writeln("<h1>Welcome to Atropine</h1>");

if cgicommon.is_client_from_localhost():
    # Client is from localhost, so serve the administrator's front page, which
    # produces a menu of tournaments and the ability to create a new one.
    tourney_created = False;

    if request_method == "POST" and tourneyname:
        try:
            tourney = countdowntourney.tourney_create(tourneyname, cgicommon.dbdir);
            tourney.close();
            cgicommon.show_success_box("Tourney \"%s\" was created successfully." % cgicommon.escape(tourneyname));
            cgicommon.writeln("<p>");
            cgicommon.writeln('<a href="/cgi-bin/tourneysetup.py?tourney=%s">Click here to continue</a>' % urllib.parse.quote_plus(tourneyname));
            cgicommon.writeln("</p>");
            tourney_created = True;
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);

    if not tourney_created:
        # If name has been filled in, attempt to create tourney

        cgicommon.writeln("<h2>Create new tourney</h2>");
        cgicommon.writeln('<form action="%s" method="POST">' % cgicommon.escape(baseurl, True));
        cgicommon.writeln("<div>Enter the name for your new tourney.</div>")
        cgicommon.writeln("<div class=\"createtourneynamebox\">")
        cgicommon.writeln('<input style=\"font-size: 12pt;\" type="text" name="name" value="%s" /> <br />' % cgicommon.escape(tourneyname, True));
        cgicommon.writeln("</div>");
        cgicommon.writeln("<div class=\"createtourneybuttonbox\">");
        cgicommon.writeln('<input type="submit" name="submit" value="Create Tourney" class=\"bigbutton\" />');
        cgicommon.writeln("</div>");
        cgicommon.writeln("</form>");

    cgicommon.writeln("<hr />")

tourney_list = os.listdir(cgicommon.dbdir);
tourney_list = [x for x in tourney_list if (len(x) > 3 and x[-3:] == ".db")];
if order_by in ("mtime_a", "mtime_d"):
    tourney_list = sorted(tourney_list, key=get_tourney_modified_time, reverse=(order_by == "mtime_d"));
else:
    tourney_list = sorted(tourney_list, key=lambda x : x.lower(), reverse=(order_by == "name_d"));

if cgicommon.is_client_from_localhost():
    if tourney_list:
        cgicommon.writeln("<h2>Open existing tourney</h2>");
        print_tourney_table(tourney_list, "/cgi-bin/tourneysetup.py", True, False, False)
    else:
        cgicommon.writeln("<p>")
        cgicommon.writeln("No tourneys exist yet.");
        cgicommon.writeln("</p>")

    cgicommon.writeln("<hr>")

    try:
        cgicommon.writeln("<p>")
        cgicommon.writeln("Tournament database directory: <span class=\"fixedwidth\">%s</span>" % (cgicommon.escape(os.path.realpath(cgicommon.dbdir))))
        cgicommon.writeln("</p>")
    except:
        cgicommon.writeln("<p>Failed to expand tournament database directory name</p>")
else:
    # Client is not from localhost, so display a menu of tournaments. Each
    # link goes to the Teleost display for that tournament, which is the only
    # thing non-localhost clients are allowed to access.
    cgicommon.writeln("<h2>Select tourney</h2>")
    print_tourney_table(tourney_list, None, False, True, True)

cgicommon.writeln("<p>Atropine version %s</p>" % (countdowntourney.SW_VERSION))
cgicommon.writeln("<p>Python version %d.%d.%d</p>" % tuple(sys.version_info[0:3]))

cgicommon.writeln("</body>");
cgicommon.writeln("</html>");

sys.exit(0);
