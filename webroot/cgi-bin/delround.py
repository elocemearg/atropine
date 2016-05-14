#!/usr/bin/python

import cgi
import cgitb
import cgicommon
import sys
import urllib
import os

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;


cgitb.enable()

cgicommon.set_module_path()
import countdowntourney

print "Content-Type: text/html; charset=utf-8"
print ""

baseurl = "/cgi-bin/delround.py"
form = cgi.FieldStorage()

round_no = int_or_none(form.getfirst("round"))
confirm = int_or_none(form.getfirst("confirm"))
tourneyname = form.getfirst("tourney")

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Delete round: " + str(tourneyname));

print "<body>";

if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);

if tourneyname is None:
    cgicommon.show_sidebar(None);
    print "<div class=\"mainpane\">";
    print "<h1>Delete round</h1>";
    print "<h1>Sloblock</h1>";
    print "<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>";
elif not tourney:
    cgicommon.show_sidebar(None);
    print "<div class=\"mainpane\">";
    print "<h1>Delete round</h1>";
    print "<p>No valid tourney name specified</p>";
else:
    #print '<p><a href="%s?tourney=%s">%s</a></p>' % (baseurl, urllib.quote_plus(tourneyname), cgi.escape(tourneyname));
    if confirm:
        try:
            tourney.delete_round(round_no)
            cgicommon.show_sidebar(tourney);
            print "<div class=\"mainpane\">";
            print "<h1>Delete round</h1>";
            print "<p>Round %d deleted successfully.</p>" % round_no
            print '<p><a href="/cgi-bin/tourneysetup.py?tourney=%s">Back to tourney setup</a></p>' % urllib.quote_plus(tourneyname)
        except countdowntourney.TourneyException as e:
            cgicommon.show_sidebar(tourney);
            print "<div class=\"mainpane\">";
            print "<h1>Delete round</h1>";
            cgicommon.show_tourney_exception(e)
    else:
        cgicommon.show_sidebar(tourney);
        print "<div class=\"mainpane\">";
        print "<h1>Delete round</h1>";
        latest_round_no = tourney.get_latest_round_no()
        if latest_round_no is None:
            print '<p>There are no rounds to delete!</p>'
            print '<p><a href="/cgi-bin/tourneysetup.py?tourney=%s">Back to tourney setup</a></p>' % urllib.quote_plus(tourneyname)
        else:
            round_name = tourney.get_round_name(latest_round_no)
            print '<p>The most recent round is this one:</p>'

            num_divisions = tourney.get_num_divisions()
            print "<h2>%s</h2>" % (round_name)
            for div_index in range(num_divisions):
                print "<h3>%s</h3>" % cgi.escape(tourney.get_division_name(div_index))
                games = tourney.get_games(round_no=latest_round_no, division=div_index)
                cgicommon.show_games_as_html_table(games, False, None, False, None, lambda x : cgicommon.player_to_link(x, tourneyname))

            print "<br />"
            cgicommon.show_warning_box("You are about to delete this round and all the fixtures in it. <strong>This cannot be undone.</strong> Are you sure you want to delete it?")
            print '<form action="%s" method="post">' % (baseurl)
            print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname)
            print '<input type="hidden" name="round" value="%d" />' % latest_round_no
            print '<input type="hidden" name="confirm" value="1" />'
            print '<p>'
            print '<input type="submit" name="delroundsubmit" value="Yes, I\'m sure. Delete the round and all its games." />'
            print '</p><p>'
            print '</form>'
            print '<form action="/cgi-bin/tourneysetup.py" method="post">'
            print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname)
            print '<input type="submit" name="arrghgetmeoutofhere" value="Um, wait, actually no. Take me back to the tourney setup page." />'
            print '</form>'
            print '</p>'

print "</div>"

print "</body>"
print "</html>"


