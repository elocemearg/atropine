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
    print("<table class=\"tourneylist\">");
    print("<tr>")
    print("<th><a href=\"/cgi-bin/home.py?orderby=%s\">Name</a></th>" % ("name_d" if order_by == "name_a" else "name_a"))

    if show_last_modified:
        print("<th><a href=\"/cgi-bin/home.py?orderby=%s\">Last modified</a></th>" % ("mtime_a" if order_by == "mtime_d" else "mtime_d"))

    if show_display_link or show_export_html_link:
        print("<th colspan=\"%d\">Useful links</th>" % ( 2 if show_display_link and show_export_html_link else 1 ))

    print("</tr>")
    for tourney_basename in tourney_list:
        name = tourney_basename[:-3];
        filename = os.path.join(cgicommon.dbdir, tourney_basename)
        st = os.stat(filename)
        modified_time = time.localtime(st.st_mtime)
        print("<tr>")
        print('<td class=\"tourneylistname\">')
        if destination_page:
            print('<a href="%s?tourney=%s">%s</a>' % (cgi.escape(destination_page, True), urllib.parse.quote_plus(name), cgi.escape(name)));
        else:
            print(cgi.escape(name))
        print('</td>')
        
        if show_last_modified:
            print("<td class=\"tourneylistmtime\">%s</td>" % (time.strftime("%d %b %Y %H:%M", modified_time)))

        if show_export_html_link:
            print("<td class=\"tourneylistlink\">")
            print("<a href=\"/cgi-bin/export.py?tourney=%s&format=html\">Tourney report</a>" % (urllib.parse.quote_plus(name)))
            print("</td>")
        if show_display_link:
            print("<td class=\"tourneylistlink\">")
            print("<a href=\"/cgi-bin/display.py?tourney=%s\">Full screen display</a>" % (urllib.parse.quote_plus(name)))
            print("</td>")

        print("</tr>")
    print("</table>");

baseurl = "/cgi-bin/home.py";

print("Content-Type: text/html; charset=utf-8");
print("");

cgicommon.print_html_head("Create Tourney" if cgicommon.is_client_from_localhost() else "Atropine");

form = cgi.FieldStorage();

tourneyname = form.getfirst("name", "");
order_by = form.getfirst("orderby", "mtime_d")
request_method = os.environ.get("REQUEST_METHOD", "GET");

print("<body>");
print("<h1>Welcome to Atropine</h1>");

tourney_list = os.listdir(cgicommon.dbdir);
tourney_list = [x for x in tourney_list if (len(x) > 3 and x[-3:] == ".db")];
if order_by in ("mtime_a", "mtime_d"):
    tourney_list = sorted(tourney_list, key=get_tourney_modified_time, reverse=(order_by == "mtime_d"));
else:
    tourney_list = sorted(tourney_list, key=lambda x : x.lower(), reverse=(order_by == "name_d"));


if cgicommon.is_client_from_localhost():
    # Client is from localhost, so serve the administrator's front page, which
    # produces a menu of tournaments and the ability to create a new one.
    tourney_created = False;

    if request_method == "POST" and tourneyname:
        try:
            tourney = countdowntourney.tourney_create(tourneyname, cgicommon.dbdir);
            tourney.close();
            print("<p>Tourney \"%s\" was created successfully.</p>" % tourneyname);
            print("<p>");
            print('<a href="/cgi-bin/tourneysetup.py?tourney=%s">Click here to continue</a>' % urllib.parse.quote_plus(tourneyname));
            print("</p>");
            tourney_created = True;
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);

    if not tourney_created:
        # If name has been filled in, attempt to create tourney

        print("<h2>Create new tourney</h2>");
        print('<form action="%s" method="POST">' % cgi.escape(baseurl, True));
        print("<p>");
        print('Tourney name: <input type="text" name="name" value="%s" /> <br />' % cgi.escape(tourneyname, True));
        print("</p>");
        print("<p>");
        print('<input type="submit" name="submit" value="Create Tourney" />');
        print("</p>");
        print("</form>");

    print("<hr />")

    if tourney_list:
        print("<h2>Open existing tourney</h2>");
        print_tourney_table(tourney_list, "/cgi-bin/tourneysetup.py", True, False, False)
    else:
        print("<p>")
        print("No tourneys exist yet.");
        print("</p>")

    print("<hr>")

    try:
        print("<p>")
        print("Tournament database directory: <tt>%s</tt>" % (cgi.escape(os.path.realpath(cgicommon.dbdir))))
        print("</p>")
    except:
        print("<p>Failed to expand tournament database directory name</p>")
else:
    # Client is not from localhost, so display a menu of tournaments. Each
    # link goes to the Teleost display for that tournament, which is the only
    # thing non-localhost clients are allowed to access.
    print("<h2>Select tourney</h2>")
    print_tourney_table(tourney_list, None, False, True, True)

print("<p>atropine version %s</p>" % (countdowntourney.SW_VERSION))

print("</body>");
print("</html>");

sys.exit(0);
