#!/usr/bin/python3

import htmlcommon
import countdowntourney

def write_round_drop_down(response, control_name, rounds, which_selected, last_round_option=False):
    response.writeln("<select name=\"%s\">" % (control_name))
    for (idx, r) in enumerate(rounds):
        if last_round_option and idx == len(rounds) - 1:
            name = "Latest round"
            num = -1
        else:
            name = r["name"]
            num = r["num"]
        response.writeln("<option value=\"%d\"%s>%s</option>" % (
            num, " selected" if num == which_selected else "",
            htmlcommon.escape(name)
        ))
    response.writeln("</select>")

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourney_name = tourney.get_name()

    starting_from_round = htmlcommon.int_or_none(form.getfirst("fromround"))
    if starting_from_round is None or starting_from_round < 1:
        starting_from_round = 1
    last_round = htmlcommon.int_or_none(form.getfirst("toround"))
    if last_round is not None and last_round < 0:
        # If last_round == -1, take it as None (no maximum round number).
        last_round = None

    # If the starting round is later than the ending round, swap them over.
    if last_round is not None and starting_from_round > last_round:
        (starting_from_round, last_round) = (last_round, starting_from_round)

    htmlcommon.print_html_head(response, "Standings: " + str(tourney_name));

    response.writeln("<body>");

    try:
        htmlcommon.show_sidebar(response, tourney);

        response.writeln("<div class=\"mainpane\">");

        response.writeln("<h1>Standings</h1>");

        response.writeln("<p>")
        rank_method = tourney.get_rank_method();
        response.writeln(htmlcommon.escape(rank_method.get_short_description()))
        response.writeln("</p>")

        rounds = tourney.get_rounds()

        if tourney.has_per_round_standings() and len(rounds) > 1:
            max_round_no = 1
            for r in rounds:
                if r["num"] > max_round_no:
                    max_round_no = r["num"]

            response.writeln("<form method=\"GET\" class=\"spaced\">")
            response.writeln("Count games from ")
            write_round_drop_down(response, "fromround", rounds, starting_from_round)
            response.writeln(" to ")
            write_round_drop_down(response, "toround", rounds, last_round if last_round is not None else -1, last_round_option=True)
            response.writeln(" inclusive.")

            response.writeln("<br><input type=\"submit\" value=\"Refresh\">")
            response.writeln("</form>")
        else:
            # Either we have no more than one round at the moment, or this is
            # an older tourney DB without the round_standings view. Either way,
            # don't offer the user per-round selection form.
            starting_from_round = 1

        if tourney.are_players_assigned_teams():
            htmlcommon.show_team_score_table(response, tourney.get_team_scores())
            response.writeln('<br />')

        show_finals_placings = tourney.is_rankable_by_finals() and starting_from_round == 1 and (last_round is None or last_round == max_round_no)

        if show_finals_placings:
            response.writeln("<h2>Before finals</h2>")

        if starting_from_round > 1 or last_round is not None:
            if starting_from_round == max_round_no or (last_round is not None and starting_from_round == last_round):
                response.writeln("<p>Showing standings based on games in <b>round %d only</b>.</p>" % (starting_from_round))
            else:
                response.writeln("<p>Showing standings based on games in <b>rounds %d-%d only</b>.</p>" % (starting_from_round, last_round if last_round is not None else max_round_no))

        htmlcommon.show_standings_table(response, tourney, True, True, True,
                show_first_second_column=True,
                linkify_players=True,
                show_tournament_rating_column=None,
                show_qualified=False,
                which_division=None,
                show_finals_column=False,
                rank_finals=False,
                starting_from_round=starting_from_round,
                last_round=last_round)

        if show_finals_placings:
            response.writeln("<h2>After finals</h2>")
            htmlcommon.show_standings_table(response, tourney, True, True, True,
                    show_first_second_column=True,
                    linkify_players=True,
                    show_tournament_rating_column=None,
                    show_qualified=False,
                    which_division=None,
                    show_finals_column=True,
                    rank_finals=True,
                    starting_from_round=starting_from_round,
                    last_round=last_round)

        response.writeln("</div>"); #mainpane
    except countdowntourney.TourneyException as e:
        htmlcommon.show_tourney_exception(response, e);

    response.writeln("</body>")
    response.writeln("</html>")
