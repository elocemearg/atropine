#!/usr/bin/python

import cgi;
import cgitb;
import cgicommon;
import sys;
import csv;
import os;
import urllib;

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;

def float_or_none(s):
    if s is None:
        return None;
    try:
        return float(s);
    except ValueError:
        return None;

cgitb.enable();

cgicommon.set_module_path();
import countdowntourney;

print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/tourneysetupadvanced.py";
form = cgi.FieldStorage();
tourneyname = form.getfirst("tourney");
show_tournament_rating = bool(int_or_none(form.getfirst("showtournamentratingcolumn")))
tr_bonus = float_or_none(form.getfirst("tournamentratingbonus"))
tr_diff_cap = float_or_none(form.getfirst("tournamentratingdiffcap"))

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Advanced setup: " + str(tourneyname));

print "<body>";

if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);
        print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>"
        print "</body></html>"
        sys.exit(1)

cgicommon.show_sidebar(tourney);

print "<div class=\"mainpane\">";
print "<h1>Advanced Setup</h1>";

if tourneyname is None:
    print "<h1>Sloblock</h1>";
    print "<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>";
elif not tourney:
    print "<p>No valid tourney name specified</p>";
else:
    #print '<p><a href="%s?tourney=%s">%s</a></p>' % (baseurl, urllib.quote_plus(tourneyname), cgi.escape(tourneyname));
    if request_method == "POST" and "submit" in form:
        try:
            tourney.set_show_tournament_rating_column(show_tournament_rating)
            tourney.set_tournament_rating_config(tr_bonus, tr_diff_cap)
            #tourney.set_table_size(players_per_table);
            print "<p><strong>Options updated successfully.</strong></p>";
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);

    print "<hr />"
    print('<form action="%s?tourney=%s" method="post" />' % (baseurl, urllib.quote_plus(tourneyname)));
    print('<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname, True));
    print("<h2>Tournament Ratings</h2>")
    print("<p>If you don't know what tournament ratings are, you can safely leave these as the defaults and they won't affect anything.</p>")
    print("<p>")
    print("<input type=\"checkbox\" name=\"showtournamentratingcolumn\" value=\"1\" %s />" % ("checked" if tourney.get_show_tournament_rating_column() else ""))
    print("Show tournament ratings in exported results standings table")
    print("</p>")
    print("<p>")
    print("For each game you play, your tournament rating is calculated as follows.")
    print("</p>")
    print("<ul>")
    print("<li>If you win, your opponent's <em>effective rating</em> plus the <em>win value</em>.</li>")
    print("<li>If you draw, your opponent's <em>effective rating</em>.</li>")
    print("<li>If you lose, your opponent's <em>effective rating</em> minus the <em>win value</em>.</li>")
    print("</ul>")
    print("<p>")
    print("The <em>win value</em> is <input type=\"number\" name=\"tournamentratingbonus\" value=\"%g\" maxlength=\"5\" />" % (tourney.get_tournament_rating_bonus_value()))
    print("</p><p>")
    print("Your opponent's <em>effective rating</em> for a game is their rating at the start of the tournament, capped to within")
    print("<input type=\"number\" name=\"tournamentratingdiffcap\" value=\"%g\" maxlength=\"5\" />" % (tourney.get_tournament_rating_diff_cap()))
    print("of your own.")
    print("</p>")
    print("<p>")
    print("Your overall tournament rating is the mean average from all your games.")
    print("</p>")
    print('<p><input type="submit" name="submit" value="Save Advanced Setup" /></p>')
    print("</form>");

print "</div>";

print "</body>";
print "</html>";
