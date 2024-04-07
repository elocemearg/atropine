#!/usr/bin/python3

import sys;
import cgicommon;
import urllib.request, urllib.parse, urllib.error;
import htmltraceback;
import html

htmltraceback.enable();

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

form = cgicommon.FieldStorage();
tourney_name = form.getfirst("tourney");
starting_from_round = form.getfirst("fromround")
try:
    starting_from_round = int(starting_from_round)
    if starting_from_round < 1:
        starting_from_round = 1
except:
    starting_from_round = 1

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
    cgicommon.writeln(cgicommon.escape(rank_method.get_short_description()))
    cgicommon.writeln("</p>")

    if tourney.has_per_round_standings():
        cgicommon.writeln("<form action=\"standings.py\" method=\"GET\" style=\"margin-bottom: 20px;\">")
        cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\">" % (html.escape(tourney_name)))
        cgicommon.writeln("Count games from ")
        rounds = tourney.get_rounds()

        cgicommon.writeln("<select name=\"fromround\">")
        max_round_no = 1
        for r in rounds:
            cgicommon.writeln("<option value=\"%d\"%s>%s</option>" % (r["num"],
                " selected" if r["num"] == starting_from_round else "",
                html.escape(r["name"])
            ))
            if r["num"] > max_round_no:
                max_round_no = r["num"]
        cgicommon.writeln("</select>")
        cgicommon.writeln(" onwards")
        cgicommon.writeln("<br><input type=\"submit\" value=\"Refresh\" style=\"margin-top: 10px;\">")
        cgicommon.writeln("</form>")
    else:
        # This is an older tourney DB without the round_standings view, so we
        # can only show standings for the whole tourney, not per-round.
        starting_from_round = 1

    if tourney.are_players_assigned_teams():
        cgicommon.show_team_score_table(tourney.get_team_scores())
        cgicommon.writeln('<br />')

    show_finals_placings = tourney.is_rankable_by_finals() and starting_from_round == 1

    if show_finals_placings:
        cgicommon.writeln("<h2>Before finals</h2>")

    if starting_from_round > 1:
        if starting_from_round == max_round_no:
            cgicommon.writeln("<p>Showing standings based on games in <b>round %d only</b>.</p>" % (starting_from_round))
        else:
            cgicommon.writeln("<p>Showing standings based on games in <b>rounds %d-%d only</b>.</p>" % (starting_from_round, max_round_no))

    cgicommon.show_standings_table(tourney, True, True, True,
            show_first_second_column=True,
            linkify_players=True,
            show_tournament_rating_column=None,
            show_qualified=False,
            which_division=None,
            show_finals_column=False,
            rank_finals=False,
            starting_from_round=starting_from_round)

    if show_finals_placings:
        cgicommon.writeln("<h2>After finals</h2>")
        cgicommon.show_standings_table(tourney, True, True, True,
                show_first_second_column=True,
                linkify_players=True,
                show_tournament_rating_column=None,
                show_qualified=False,
                which_division=None,
                show_finals_column=True,
                rank_finals=True,
                starting_from_round=starting_from_round)

    cgicommon.writeln("</div>"); #mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);

cgicommon.writeln("</body>")
cgicommon.writeln("</html>")

sys.exit(0);

