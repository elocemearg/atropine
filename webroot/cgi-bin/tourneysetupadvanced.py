#!/usr/bin/python3

import cgi;
import cgitb;
import cgicommon;
import sys;
import csv;
import os;
import urllib.request, urllib.parse, urllib.error;

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

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

baseurl = "/cgi-bin/tourneysetupadvanced.py";
form = cgi.FieldStorage();
tourneyname = form.getfirst("tourney");
show_tournament_rating = bool(int_or_none(form.getfirst("showtournamentratingcolumn")))
tr_bonus = float_or_none(form.getfirst("tournamentratingbonus"))
tr_diff_cap = float_or_none(form.getfirst("tournamentratingdiffcap"))

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Advanced setup: " + str(tourneyname));

cgicommon.writeln("<body>");

cgicommon.assert_client_from_localhost()

if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);
        cgicommon.writeln("<p><a href=\"/cgi-bin/home.py\">Home</a></p>")
        cgicommon.writeln("</body></html>")
        sys.exit(1)

cgicommon.show_sidebar(tourney);

cgicommon.writeln("<div class=\"mainpane\">");
cgicommon.writeln("<h1>Advanced Setup</h1>");

if tourneyname is None:
    cgicommon.writeln("<h1>Sloblock</h1>");
    cgicommon.writeln("<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>");
elif not tourney:
    cgicommon.writeln("<p>No valid tourney name specified</p>");
else:
    #print '<p><a href="%s?tourney=%s">%s</a></p>' % (baseurl, urllib.quote_plus(tourneyname), cgicommon.escape(tourneyname));
    if request_method == "POST" and "submit" in form:
        try:
            tourney.set_show_tournament_rating_column(show_tournament_rating)
            tourney.set_tournament_rating_config(tr_bonus, tr_diff_cap)
            #tourney.set_table_size(players_per_table);
            cgicommon.writeln("<p><strong>Options updated successfully.</strong></p>");
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);

    cgicommon.writeln("<hr />")
    cgicommon.writeln(('<form action="%s?tourney=%s" method="post" />' % (baseurl, urllib.parse.quote_plus(tourneyname))));
    cgicommon.writeln(('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname, True)));
    cgicommon.writeln("<h2>Tournament Ratings</h2>")
    cgicommon.writeln("<p>If you don't know what tournament ratings are, you can safely leave these as the defaults and they won't affect anything.</p>")
    cgicommon.writeln("<p>")
    cgicommon.writeln(("<input type=\"checkbox\" name=\"showtournamentratingcolumn\" value=\"1\" %s />" % ("checked" if tourney.get_show_tournament_rating_column() else "")))
    cgicommon.writeln("Show tournament ratings in exported results standings table")
    cgicommon.writeln("</p>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("For each game you play, your tournament rating is calculated as follows.")
    cgicommon.writeln("</p>")
    cgicommon.writeln("<ul>")
    cgicommon.writeln("<li>If you win, your opponent's <em>effective rating</em> plus the <em>win value</em>.</li>")
    cgicommon.writeln("<li>If you draw, your opponent's <em>effective rating</em>.</li>")
    cgicommon.writeln("<li>If you lose, your opponent's <em>effective rating</em> minus the <em>win value</em>.</li>")
    cgicommon.writeln("</ul>")
    cgicommon.writeln("<p>")
    cgicommon.writeln(("The <em>win value</em> is <input type=\"number\" name=\"tournamentratingbonus\" value=\"%g\" maxlength=\"5\" />" % (tourney.get_tournament_rating_bonus_value())))
    cgicommon.writeln("</p><p>")
    cgicommon.writeln("Your opponent's <em>effective rating</em> for a game is their rating at the start of the tournament, capped to within")
    cgicommon.writeln(("<input type=\"number\" name=\"tournamentratingdiffcap\" value=\"%g\" maxlength=\"5\" />" % (tourney.get_tournament_rating_diff_cap())))
    cgicommon.writeln("of your own.")
    cgicommon.writeln("</p>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("Your overall tournament rating is the mean average from all your games.")
    cgicommon.writeln("</p>")
    cgicommon.writeln('<p><input type="submit" name="submit" value="Save Advanced Setup" /></p>')
    cgicommon.writeln("</form>");

cgicommon.writeln("</div>");

cgicommon.writeln("</body>");
cgicommon.writeln("</html>");
