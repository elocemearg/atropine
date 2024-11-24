#!/usr/bin/python3

import htmlcommon
import countdowntourney

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourney_name = tourney.get_name()

    htmlcommon.print_html_head(response, "Tuff luck: " + str(tourney_name))

    response.writeln("<body>")

    try:
        htmlcommon.show_sidebar(response, tourney, show_misc_table_links=True)
        num_losing_games = htmlcommon.int_or_none(form.getfirst("numlosinggames", 3))
        if num_losing_games is None or num_losing_games <= 0:
            num_losing_games = 3

        response.writeln("<div class=\"mainpane\">")

        response.writeln("<h1>Tuff Luck</h1>")

        response.writeln("<form method=\"GET\" class=\"spaced\">")
        response.writeln("A player's Tuff Luck is their aggregate losing margin over their")
        response.writeln("<input type=\"number\" name=\"numlosinggames\" value=\"%d\" min=\"1\" max=\"999\" size=\"3\" />" % (num_losing_games))
        response.writeln("closest losing games, for players who have lost at least that many games.")
        response.writeln("It is the opposite of <a href=\"/atropine/%s/luckystiff\">Lucky Stiff</a>." % (htmlcommon.escape(tourney_name)))
        response.writeln("<br>")
        response.writeln("<input type=\"submit\" name=\"submit\" value=\"Refresh\" />")
        response.writeln("</form>")

        players_tuff_luck = tourney.get_players_tuff_luck(num_losing_games)

        pos = 0
        joint = 1
        prev_tuffness = None
        if not players_tuff_luck:
            response.writeln("<p>No players have lost %d or more games.</p>" % (num_losing_games))
        else:
            htmlcommon.write_ranked_table(response,
                    [ "Player", "Defeats", "Closest margins", "Total" ],
                    [ "rankname", "ranknumber", "ranktext", "ranknumber rankhighlight" ],
                    [
                        (htmlcommon.player_to_link(player, tourney_name),
                            num_losses,
                            ", ".join(map(str, margins)),
                            tuffness) for (player, num_losses, tuffness, margins) in players_tuff_luck
                    ],
                    lambda x : x[3],
                    no_escape_html=[0]
            )
        response.writeln("<p>")
        response.writeln("For the purpose of Tuff Luck, games lost on a tiebreak have a margin of zero. Games adjudicated as a loss for both players do not count. Only games which count towards the standings are considered.")
        response.writeln("</p>")
        response.writeln("</div>") #mainpane
    except countdowntourney.TourneyException as e:
        htmlcommon.show_tourney_exception(response, e)

    response.writeln("</body>")
    response.writeln("</html>")
