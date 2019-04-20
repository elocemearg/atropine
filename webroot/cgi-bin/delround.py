#!/usr/bin/python3

import cgi
import cgitb
import cgicommon
import sys
import urllib.request, urllib.parse, urllib.error
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

cgicommon.writeln("Content-Type: text/html; charset=utf-8")
cgicommon.writeln("")

baseurl = "/cgi-bin/delround.py"
form = cgi.FieldStorage()

round_no = int_or_none(form.getfirst("round"))
confirm = int_or_none(form.getfirst("confirm"))
tourneyname = form.getfirst("tourney")

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Delete round: " + str(tourneyname));

cgicommon.writeln("<body>");

cgicommon.assert_client_from_localhost()

if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);

if tourneyname is None:
    cgicommon.show_sidebar(None);
    cgicommon.writeln("<div class=\"mainpane\">");
    cgicommon.writeln("<h1>Delete round</h1>");
    cgicommon.writeln("<h1>Sloblock</h1>");
    cgicommon.writeln("<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>");
elif not tourney:
    cgicommon.show_sidebar(None);
    cgicommon.writeln("<div class=\"mainpane\">");
    cgicommon.writeln("<h1>Delete round</h1>");
    cgicommon.writeln("<p>No valid tourney name specified</p>");
else:
    #print '<p><a href="%s?tourney=%s">%s</a></p>' % (baseurl, urllib.quote_plus(tourneyname), cgicommon.escape(tourneyname));
    if confirm:
        try:
            tourney.delete_round(round_no)
            cgicommon.show_sidebar(tourney);
            cgicommon.writeln("<div class=\"mainpane\">");
            cgicommon.writeln("<h1>Delete round</h1>");
            cgicommon.show_success_box("Round %d deleted successfully." % (round_no))
            cgicommon.writeln('<p><a href="/cgi-bin/tourneysetup.py?tourney=%s">Back to tourney setup</a></p>' % urllib.parse.quote_plus(tourneyname))
        except countdowntourney.TourneyException as e:
            cgicommon.show_sidebar(tourney);
            cgicommon.writeln("<div class=\"mainpane\">");
            cgicommon.writeln("<h1>Delete round</h1>");
            cgicommon.show_tourney_exception(e)
    else:
        cgicommon.show_sidebar(tourney);
        cgicommon.writeln("<div class=\"mainpane\">");
        cgicommon.writeln("<h1>Delete round</h1>");
        latest_round_no = tourney.get_latest_round_no()
        if latest_round_no is None:
            cgicommon.writeln('<p>There are no rounds to delete!</p>')
            cgicommon.writeln('<p><a href="/cgi-bin/tourneysetup.py?tourney=%s">Back to tourney setup</a></p>' % urllib.parse.quote_plus(tourneyname))
        else:
            round_name = tourney.get_round_name(latest_round_no)
            cgicommon.writeln('<p>The most recent round is shown below.</p>')
            cgicommon.show_warning_box("You are about to delete this round and all the fixtures in it. <strong>This cannot be undone.</strong> Are you sure you want to delete it?")
            cgicommon.writeln('<form action="%s" method="post">' % (baseurl))
            cgicommon.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname))
            cgicommon.writeln('<input type="hidden" name="round" value="%d" />' % latest_round_no)
            cgicommon.writeln('<input type="hidden" name="confirm" value="1" />')
            cgicommon.writeln('<p>')
            cgicommon.writeln('<input type="submit" class="bigbutton destroybutton" name="delroundsubmit" value="Yes, I\'m sure. Delete the round and all its games." />')
            cgicommon.writeln('</p>')
            cgicommon.writeln('</form>')
            cgicommon.writeln('<form action="/cgi-bin/tourneysetup.py" method="post">')
            cgicommon.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname))
            cgicommon.writeln('<input type="submit" class="bigbutton chickenoutbutton" name="arrghgetmeoutofhere" value="No. Cancel this and take me back to the tourney setup page." />')
            cgicommon.writeln('</form>')

            num_divisions = tourney.get_num_divisions()
            cgicommon.writeln("<h2>%s</h2>" % (round_name))
            for div_index in range(num_divisions):
                cgicommon.writeln("<h3>%s</h3>" % cgicommon.escape(tourney.get_division_name(div_index)))
                games = tourney.get_games(round_no=latest_round_no, division=div_index)
                cgicommon.show_games_as_html_table(games, False, None, False, None, lambda x : cgicommon.player_to_link(x, tourneyname))


cgicommon.writeln("</div>")

cgicommon.writeln("</body>")
cgicommon.writeln("</html>")


