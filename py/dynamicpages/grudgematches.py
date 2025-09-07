#!/usr/bin/python3

import htmlcommon
import countdowntourney

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourney_name = tourney.get_name()

    htmlcommon.print_html_head(response, "Grudge matches: " + str(tourney_name))
    response.writeln("<body>")

    try:
        htmlcommon.show_sidebar(response, tourney, expand_spot_prize_links=True)

        response.writeln("<div class=\"mainpane\">")
        response.writeln("<h1>Grudge Matches</h1>")

        response.writeln("<p>The following players have beaten one or more of their Rivals.</p>")

        games = tourney.get_games_where_player_beat_rival()
        if games:
            # Group these games by the name of the winner
            winner_games = {}
            name_to_player = {}
            for g in games:
                winner = g.get_winner()
                loser = g.get_loser()
                if winner and loser:
                    winner_name = winner.get_name()
                    loser_name = loser.get_name()
                    if winner_name not in name_to_player:
                        name_to_player[winner_name] = winner
                    if loser_name not in name_to_player:
                        name_to_player[loser_name] = loser
                if winner_name not in winner_games:
                    winner_games[winner_name] = []
                winner_games[winner_name].append(g)

            # Show the list of people who have beaten a rival, along with the
            # names of the rivals they beat.
            response.writeln("<ul>")
            for winner_name in sorted(winner_games):
                # Build a frequency map of the number of times this winner beat each of their rivals.
                winner = name_to_player[winner_name]
                losers_freq = {}
                for g in winner_games[winner_name]:
                    loser = g.get_loser()
                    if loser:
                        loser_name = loser.get_name()
                        losers_freq[loser_name] = losers_freq.get(loser_name, 0) + 1

                # Show the winner's name and a link to their player page
                response.writeln("<li>")
                response.writeln(htmlcommon.player_to_link(winner, tourney_name, emboldenise=True, open_in_new_window=True) + " beat ")

                # List defeated rivals, with the number of times in brackets
                # if they defeated the same rival more than once.
                loser_name_list = []
                for loser_name in sorted(losers_freq):
                    loser = name_to_player[loser_name]
                    s = htmlcommon.player_to_link(loser, tourney_name, emboldenise=False, open_in_new_window=True)
                    if losers_freq[loser_name] > 1:
                        s += " (x" + str(losers_freq[loser_name]) + ")"
                    loser_name_list.append(s)
                response.writeln(", ".join(loser_name_list))
                response.writeln("</li>")
            response.writeln("</ul>")

            # Show the full list of games in order
            response.writeln("<h2>Games</h2>")
            htmlcommon.show_games_as_html_table(response,
                    games, editable=False, include_round_column=True,
                    include_table_number_column=False, colour_win_loss=True,
                    round_namer=lambda x : tourney.get_short_round_name(x))

        response.writeln("</div>") #mainpane
    except countdowntourney.TourneyException as e:
        htmlcommon.show_tourney_exception(response, e)

    response.writeln("</body>")
    response.writeln("</html>")
