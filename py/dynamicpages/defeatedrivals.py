#!/usr/bin/python3

import htmlcommon
import countdowntourney

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourney_name = tourney.get_name()

    htmlcommon.print_html_head(response, "Defeated Rivals: " + str(tourney_name))
    response.writeln("<body>")

    try:
        htmlcommon.show_sidebar(response, tourney, expand_spot_prize_links=True)

        response.writeln("<div class=\"mainpane\">")
        response.writeln("<h1>Defeated Rivals</h1>")

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
            response.writeln("<p>The following players have beaten one or more of their Rivals.</p>")
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
            response.writeln("<p>These are the games in which a player beat one of their Rivals.</p>")
            htmlcommon.show_games_as_html_table(response,
                    games, editable=False, include_round_column=True,
                    include_table_number_column=False, colour_win_loss=True,
                    round_namer=lambda x : tourney.get_short_round_name(x))

        # Get complete list of players, so we can show all rivalries
        players = tourney.get_players(include_prune=True)
        name_to_player = {}
        num_rivalries = 0
        for p in players:
            num_rivalries += len(p.get_rival_names())
            name_to_player[p.get_name()] = p

        response.writeln("<h2>Rivalries</h2>")
        if num_rivalries == 0:
            if tourney.has_rivals():
                response.writeln("<p>No players have any Rivals set. You can set players' rivals using <a href=\"/atropine/%s/player\">Player Setup</a>.</p>" % (htmlcommon.escape(tourney_name)))
            else:
                response.writeln("<p>This tourney was created with a version of Atropine prior to 1.3.2. Rivals are not supported, so this page isn't of any use to you.</p>")
        else:
            # Show table of all rivalries
            response.writeln("<p>All rivalries in effect for this tourney are listed here. A player in the left-hand column will appear above if they beat one of their rivals in the right-hand column.</p>")
            response.writeln("<p>A player's rivalries can be edited on their <a href=\"/atropine/%s/player\">Player Setup</a> page.</p>" % (htmlcommon.escape(tourney_name)))
            response.writeln("<table class=\"misctable\">")
            response.writeln("<th>Player</th><th>Player's rivals</th>")
            for p in sorted(players, key=lambda x : x.get_name()):
                rival_names = p.get_rival_names()
                if rival_names:
                    response.writeln("<tr>")
                    response.writeln("<td>%s</td>" % (htmlcommon.player_to_link(p, tourney_name, open_in_new_window=True)))
                    response.writeln("<td>")
                    first = True
                    for rival_name in sorted(rival_names):
                        rival = name_to_player.get(rival_name)
                        if rival:
                            response.write("%s%s" % ("" if first else ", ", htmlcommon.player_to_link(rival, tourney_name, open_in_new_window=True)))
                            first = False
                    response.writeln("</td></tr>")
            response.writeln("</table>")

        response.writeln("</div>") #mainpane
    except countdowntourney.TourneyException as e:
        htmlcommon.show_tourney_exception(response, e)

    response.writeln("</body>")
    response.writeln("</html>")
