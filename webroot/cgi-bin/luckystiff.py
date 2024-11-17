#!/usr/bin/python3

import urllib.request, urllib.parse, urllib.error
import cgicommon
import countdowntourney

def handle(httpreq, response, tourney, request_method, form, query_string):
    tourney_name = tourney.get_name()

    cgicommon.print_html_head(response, "Lucky Stiff: " + str(tourney_name))

    response.writeln("<body>")

    httpreq.assert_client_from_localhost()

    try:
        cgicommon.show_sidebar(response, tourney, show_misc_table_links=True)
        num_wins = cgicommon.int_or_none(form.getfirst("numwins", 3))
        if num_wins is None or num_wins <= 0:
            num_wins = 3

        response.writeln("<div class=\"mainpane\">")

        response.writeln("<h1>Lucky Stiff</h1>")

        response.writeln("<form action=\"/cgi-bin/luckystiff.py\" method=\"GET\" class=\"spaced\">")
        response.writeln("The Lucky Stiff is the player whose")
        response.writeln("<input type=\"number\" name=\"numwins\" value=\"%d\" min=\"1\" max=\"999\" size=\"3\" />" % (num_wins))
        response.writeln("closest winning games had the lowest aggregate winning margin. It is the opposite of <a href=\"/cgi-bin/tuffluck.py?tourney=%s\">Tuff Luck</a>." % (cgicommon.escape(tourney_name, True)))
        response.writeln("<br>")
        response.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourney_name, True)))
        response.writeln("<input type=\"submit\" name=\"submit\" value=\"Refresh\" />")
        response.writeln("</form>")

        players_lucky_stiff = tourney.get_players_lucky_stiff(num_wins)

        pos = 0
        joint = 1
        prev_stiffness = None
        if not players_lucky_stiff:
            response.writeln("<p>No players have won %d or more games.</p>" % (num_wins))
        else:
            cgicommon.write_ranked_table(
                    response,
                    [ "Player", "Wins", "Closest margins", "Total" ],
                    [ "rankname", "ranknumber", "ranktext", "ranknumber rankhighlight" ],
                    [
                        ( cgicommon.player_to_link(player, tourney_name),
                            num_wins, ", ".join(map(str, margins)), stiffness) for (player, num_wins, stiffness, margins) in players_lucky_stiff
                    ],
                    lambda x : x[3],
                    [ 0 ]
            )
        response.writeln("<p>")
        response.writeln("For the purpose of Lucky Stiff, games won a tiebreak have a margin of zero. Only games which count towards the standings are considered.")
        response.writeln("</p>")
        response.writeln("</div>") #mainpane
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(response, e)

    response.writeln("</body>")
    response.writeln("</html>")
