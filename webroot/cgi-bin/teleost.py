#!/usr/bin/python

import sys;
import cgi;
import cgitb;
import os;
import cgicommon;
import urllib;

cgitb.enable();

print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/teleost.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

import countdowntourney;

cgicommon.print_html_head("Display control: " + str(tourney_name));

print "<body>";

if tourney_name is None:
    print "<h1>No tourney specified</h1>";
    print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>";
else:
    try:
        tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

        cgicommon.show_sidebar(tourney);

        print "<div class=\"mainpane\">"

        if request_method == "POST":
            mode = form.getfirst("mode");
            auto_use_vertical = form.getfirst("autousevertical")
            if mode is not None:
                try:
                    mode = int(mode);
                    tourney.set_teleost_mode(mode);
                except ValueError:
                    pass;
            if auto_use_vertical is not None:
                try:
                    auto_use_vertical = int(auto_use_vertical)
                    tourney.set_auto_use_vertical(auto_use_vertical != 0)
                except ValueError:
                    pass
            else:
                tourney.set_auto_use_vertical(False)

        views = tourney.get_teleost_modes();
        print "<h1>Display control</h1>";

        print "<form action=\"/cgi-bin/teleost.py?tourney=%s\" method=\"POST\">" % urllib.quote_plus(tourney_name);
        print "<p>";
        for v in views:
            view_num = v.get("num", -1);
            view_name = v.get("name", "View %d" % view_num);
            view_desc = v.get("desc", "");
            view_selected = v.get("selected", False);
            print "<input type=\"radio\" name=\"mode\" value=\"%d\" %s />" % (view_num, "checked" if view_selected else "");
            print "<strong>%s</strong>: %s" % (cgi.escape(view_name), cgi.escape(view_desc));
            print "<br />";
            if view_num == 0:
                use_vertical = tourney.get_auto_use_vertical()
                print "<span style=\"padding-left: 2em\">"
                print "<input type=\"checkbox\" name=\"autousevertical\" value=\"1\" %s /> Use vertical standings/results format between rounds" % ("checked" if use_vertical else "")
                print "</span>"
                print "<br />"
        print "</p>";

        print "<input type=\"submit\" name=\"submit\" value=\"Apply Settings\" />";
        print "</form>";

        print "</div>";

    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);

print "</body></html>";

sys.exit(0);

