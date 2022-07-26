#!/usr/bin/python3

import sys;
import cgicommon;
import urllib.request, urllib.parse, urllib.error;
import cgi;
import cgitb;

cgitb.enable();

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;

cgicommon.set_module_path();

import countdowntourney;

cgicommon.print_html_head("Standings: " + str(tourney_name));

cgicommon.writeln("<body>");

cgicommon.assert_client_from_localhost()

if tourney_name is None:
    cgicommon.writeln("<h1>No tourney specified</h1>");
    cgicommon.writeln("<p><a href=\"/cgi-bin/home.py\">Home</a></p>");
    cgicommon.writeln("</body></html>");
    sys.exit(0);

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

    cgicommon.show_sidebar(tourney);

    cgicommon.writeln("<div class=\"mainpane\">");

    cgicommon.writeln("<h1>Standings</h1>");

    cgicommon.writeln("<p>")
    rank_method = tourney.get_rank_method();
    if rank_method == countdowntourney.RANK_WINS_POINTS:
        cgicommon.writeln("Players are ranked by wins, then points.");
    elif rank_method == countdowntourney.RANK_WINS_SPREAD:
        cgicommon.writeln("Players are ranked by wins, then cumulative winning margin.");
    elif rank_method == countdowntourney.RANK_POINTS:
        cgicommon.writeln("Players are ranked by points.");
    else:
        cgicommon.writeln("Players are ranked somehow. Your guess is as good as mine.");
        cgicommon.writeln("</p>")

    if tourney.are_players_assigned_teams():
        cgicommon.show_team_score_table(tourney.get_team_scores())
        cgicommon.writeln('<br />')

    rank_method = tourney.get_rank_method()
    cgicommon.show_standings_table(tourney, True, True, True, True, True, tourney.get_show_tournament_rating_column(), True)

    cgicommon.writeln("</div>"); #mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);

cgicommon.writeln("</body>")
cgicommon.writeln("</html>")

sys.exit(0);

