#!/usr/bin/python

import sys;
import cgicommon;
import urllib;
import cgi;
import cgitb;

cgitb.enable();

print "Content-Type: text/html; charset=utf-8";
print "";

form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;

cgicommon.set_module_path();

import countdowntourney;

cgicommon.print_html_head("Standings: " + str(tourney_name));

print "<body>";

if tourney_name is None:
    print "<h1>No tourney specified</h1>";
    print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>";
    print "</body></html>";
    sys.exit(0);

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

    cgicommon.show_sidebar(tourney);

    print "<div class=\"mainpane\">";

    print "<h1>Standings</h1>";

    #if round_nos:
    #    print "<p>Rounds: %s</p>" % (", ".join(map(str, round_nos)));
    #if round_types:
    #    print "<p>Round types: %s</p>" % (", ".join(round_types));

    print "<p>"
    rank_method = tourney.get_rank_method();
    if rank_method == countdowntourney.RANK_WINS_POINTS:
        print "Players are ranked by wins, then points.";
    elif rank_method == countdowntourney.RANK_WINS_SPREAD:
        print "Players are ranked by wins, then cumulative winning margin.";
    elif rank_method == countdowntourney.RANK_POINTS:
        print "Players are ranked by points.";
    else:
        print "Players are ranked somehow. Your guess is as good as mine.";
        print "</p>"

    if tourney.are_players_assigned_teams():
        cgicommon.show_team_score_table(tourney.get_team_scores())
        print '<br />'

    rank_method = tourney.get_rank_method()
    cgicommon.show_standings_table(tourney, rank_method in (countdowntourney.RANK_WINS_POINTS, countdowntourney.RANK_WINS_SPREAD), True, True, True, True, True)

    print "</div>"; #mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);

print "</body>"
print "</html>"

sys.exit(0);

