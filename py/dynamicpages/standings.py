#!/usr/bin/python3

import cgicommon
import urllib.request, urllib.parse, urllib.error
import html
import countdowntourney

def handle(httpreq, response, tourney, request_method, form, query_string):
    tourney_name = tourney.get_name()
    starting_from_round = form.getfirst("fromround")
    try:
        starting_from_round = int(starting_from_round)
        if starting_from_round < 1:
            starting_from_round = 1
    except:
        starting_from_round = 1

    cgicommon.print_html_head(response, "Standings: " + str(tourney_name));

    response.writeln("<body>");

    try:
        cgicommon.show_sidebar(response, tourney);

        response.writeln("<div class=\"mainpane\">");

        response.writeln("<h1>Standings</h1>");

        response.writeln("<p>")
        rank_method = tourney.get_rank_method();
        response.writeln(cgicommon.escape(rank_method.get_short_description()))
        response.writeln("</p>")

        rounds = tourney.get_rounds()

        if tourney.has_per_round_standings() and len(rounds) > 1:
            response.writeln("<form action=\"standings.py\" method=\"GET\" class=\"spaced\">")
            response.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\">" % (html.escape(tourney_name)))
            response.writeln("Count games from ")
            response.writeln("<select name=\"fromround\">")
            max_round_no = 1
            for r in rounds:
                response.writeln("<option value=\"%d\"%s>%s</option>" % (r["num"],
                    " selected" if r["num"] == starting_from_round else "",
                    html.escape(r["name"])
                ))
                if r["num"] > max_round_no:
                    max_round_no = r["num"]
            response.writeln("</select>")
            response.writeln(" onwards")
            response.writeln("<br><input type=\"submit\" value=\"Refresh\">")
            response.writeln("</form>")
        else:
            # Either we have no more than one round at the moment, or this is
            # an older tourney DB without the round_standings view. Either way,
            # don't offer the user per-round selection form.
            starting_from_round = 1

        if tourney.are_players_assigned_teams():
            cgicommon.show_team_score_table(response, tourney.get_team_scores())
            response.writeln('<br />')

        show_finals_placings = tourney.is_rankable_by_finals() and starting_from_round == 1

        if show_finals_placings:
            response.writeln("<h2>Before finals</h2>")

        if starting_from_round > 1:
            if starting_from_round == max_round_no:
                response.writeln("<p>Showing standings based on games in <b>round %d only</b>.</p>" % (starting_from_round))
            else:
                response.writeln("<p>Showing standings based on games in <b>rounds %d-%d only</b>.</p>" % (starting_from_round, max_round_no))

        cgicommon.show_standings_table(response, tourney, True, True, True,
                show_first_second_column=True,
                linkify_players=True,
                show_tournament_rating_column=None,
                show_qualified=False,
                which_division=None,
                show_finals_column=False,
                rank_finals=False,
                starting_from_round=starting_from_round)

        if show_finals_placings:
            response.writeln("<h2>After finals</h2>")
            cgicommon.show_standings_table(response, tourney, True, True, True,
                    show_first_second_column=True,
                    linkify_players=True,
                    show_tournament_rating_column=None,
                    show_qualified=False,
                    which_division=None,
                    show_finals_column=True,
                    rank_finals=True,
                    starting_from_round=starting_from_round)

        response.writeln("</div>"); #mainpane
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(response, e);

    response.writeln("</body>")
    response.writeln("</html>")
