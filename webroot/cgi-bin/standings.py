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

    standings = tourney.get_standings();

    print "<h1>Standings</h1>";

    #if round_nos:
    #    print "<p>Rounds: %s</p>" % (", ".join(map(str, round_nos)));
    #if round_types:
    #    print "<p>Round types: %s</p>" % (", ".join(round_types));

    print "<p>"
    rank_method = tourney.get_rank_method();
    if rank_method == countdowntourney.RANK_WINS_POINTS:
        print "Players are ranked by wins, then points.";
    elif rank_method == countdowntourney.RANK_POINTS:
        print "Players are ranked by points.";
    else:
        print "Players are ranked somehow. Your guess is as good as mine.";
        print "</p>"

    if tourney.are_players_assigned_teams():
        cgicommon.show_team_score_table(tourney.get_team_scores())
        print '<br />'

    show_draws_column = tourney.get_show_draws_column()

    print "<table class=\"standingstable\">";
    print "<tr><th></th><th></th><th>P</th><th>W</th>%s<th>Pts</th></tr>" % ("<th>D</th>" if show_draws_column else "");
    last_wins_inc_draws = None;
    tr_bgcolours = ["#ffdd66", "#ffff88" ];
    bgcolour_index = 0;
    for s in standings:
        (pos, name, played, wins, points, draws) = s;
        wins_inc_draws = wins + draws * 0.5
        if rank_method == countdowntourney.RANK_WINS_POINTS:
            if last_wins_inc_draws is None:
                bgcolour_index = 0;
            elif last_wins_inc_draws != wins_inc_draws:
                bgcolour_index = (bgcolour_index + 1) % 2;
            last_wins_inc_draws = wins_inc_draws;

            print "<tr class=\"standingsrow\" style=\"background-color: %s\">" % tr_bgcolours[bgcolour_index];
        print "<td class=\"standingspos\">%d</td>" % pos;
        p = tourney.get_player_from_name(name)
        team = p.get_team()
        print "<td class=\"standingsname\">%s %s</td>" % (cgicommon.make_team_dot_html(team), cgi.escape(name));
        print "<td class=\"standingsplayed\">%d</td>" % played;
        print "<td class=\"standingswins\">%d</td>" % wins;
        if show_draws_column:
            print "<td class=\"standingsdraws\">%d</td>" % draws;
        print "<td class=\"standingspoints\">%d</td>" % points;
        print "</tr>";
    print "</table>";

    print "</div>"; #mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);

print "</body>"
print "</html>"

sys.exit(0);

