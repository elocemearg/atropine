#!/usr/bin/python3

import htmlcommon
import countdowntourney

def show_rerate_button(response, tourney):
    tourney_name = tourney.get_name()
    response.writeln("<h2>Rerate players by player ID</h2>")
    response.writeln("<p>")
    response.writeln("""
    Set the ratings of players in order, by player ID, which corresponds
    to the order in which they appeared in the list you put into the text
    box at the start of the tournament. The player at the top of the list
    (the lowest player ID) gets the highest rating, and the player at the
    bottom of the list (the highest player ID) gets the lowest rating. Any
    player with a rating of zero remains unchanged.""")
    response.writeln("</p>")
    response.writeln("<p>")
    response.writeln("""
    This is useful if when you pasted in the player list you forgot to
    select the option which tells Atropine that they're in rating order,
    and now the Overachievers page thinks they're all seeded the same.
    """)
    response.writeln("</p>")

    response.writeln("<p>")
    response.writeln("""
    If you press this button, it will overwrite all other non-zero ratings
    you may have given the players. That's why you need to tick the box as
    well.
    """)
    response.writeln("</p>")

    response.writeln("<p>")
    response.writeln("<form method=\"POST\">")
    response.writeln("<input type=\"submit\" name=\"reratebyplayerid\" value=\"Rerate players by player ID\" />")
    response.writeln("<input type=\"checkbox\" name=\"reratebyplayeridconfirm\" id=\"reratebyplayeridconfirm\" style=\"margin-left: 20px\" />")
    response.writeln("<label for=\"reratebyplayeridconfirm\">Yes, I'm sure</label>")

    response.writeln("</form>")
    response.writeln("</p>")

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourney_name = tourney.get_name()

    # How many rows of each table do we show? If not specified, show 10.
    table_row_limit = htmlcommon.int_or_none(form.getfirst("limit", "10"))
    if table_row_limit is None:
        table_row_limit = 10
    if table_row_limit == 0:
        table_row_limit = None

    slingshot_by_rating = "rating" in form

    htmlcommon.print_html_head(response, "Overachievers: " + str(tourney_name))
    response.writeln("<body>")

    try:
        htmlcommon.show_sidebar(response, tourney, show_misc_table_links=True)

        response.writeln("<div class=\"mainpane\">")
        response.writeln("<h1>Overachievers</h1>")

        if request_method == "POST" and "reratebyplayerid" in form and "reratebyplayeridconfirm" in form:
            try:
                tourney.rerate_players_by_id()
                htmlcommon.show_success_box(response, "Players successfully rerated by player ID.")
            except countdowntourney.TourneyException as e:
                htmlcommon.show_tourney_exception(response, e)

        if tourney.get_num_games() == 0:
            response.writeln("<p>No games have been played yet.</p>")
        else:
            response.writeln("<form method=\"GET\">")
            response.writeln("<div class=\"simpleformline\">")
            response.writeln("<label for=\"limit\">Show the top <input type=\"number\" min=\"0\" name=\"limit\" id=\"limit\" value=\"%d\"> rows in each table, plus ties.</label>" % (0 if not table_row_limit else table_row_limit))
            response.writeln("</div>")
            response.writeln("<div class=\"simpleformline\">")
            response.writeln("<input type=\"checkbox\" name=\"rating\" id=\"rating\" %s><label for=\"rating\"> Calculate Slingshot gaps by rating difference, not seeding difference</label>" % ("checked" if slingshot_by_rating else ""))
            response.writeln("</div>")
            response.writeln("<div class=\"simpleformline\">")
            response.writeln("<input type=\"submit\" value=\"Refresh\">")
            response.writeln("</div>")
            response.writeln("</form>")
            response.writeln("<p>Each player is assigned a seed according to their rating, with the top-rated player in a division being the #1 seed, and so on down. Players are listed here in order of the difference between their position in the standings table and their seed position.</p>")

            num_divisions = tourney.get_num_divisions()
            do_show_rerate_button = False
            for div_index in range(num_divisions):
                div_name = tourney.get_division_name(div_index)
                overachievements = tourney.get_players_overachievements(div_index, limit=table_row_limit)
                if num_divisions > 1:
                    response.writeln("<h2>%s</h2>" % (htmlcommon.escape(div_name)))
                if not overachievements:
                    response.writeln("<p>There are no players to show.</p>")
                    continue
                if tourney.are_player_ratings_uniform(div_index):
                    htmlcommon.show_warning_box(response, "<p>All the players have the same rating. This means the Overachievers table won't be meaningful. If when you set up the tournament you pasted the players into the player list in order of rating but forgot to tell Atropine you'd done that, try the \"Rerate players by player ID\" button below.</p>")
                    do_show_rerate_button = True
                else:
                    htmlcommon.write_ranked_table(
                            response,
                            [ "Player", "Seed", "Pos", "+/-" ],
                            [ "rankname", "ranknumber", "ranknumber", "ranknumber rankhighlight" ],
                            [
                                (htmlcommon.player_to_link(row[0], tourney_name),
                                    row[1], row[2], row[3]) for row in overachievements
                            ],
                            key_fn=lambda x : -x[3],
                            no_escape_html=[0],
                            formatters={
                                1 : lambda x : htmlcommon.ordinal_number(x),
                                2 : lambda x : htmlcommon.ordinal_number(x),
                                3 : (lambda x : "0" if x == 0 else ("%+d" % (x)))
                            }
                    )

                    response.writeln("<%(tag)s>Slingshot</%(tag)s>" % {
                        "tag" : "h3" if num_divisions > 1 else "h2"
                    })
                    response.writeln("<p>This table shows the biggest %s deficits overcome by the winner of a game.</p>" % ("rating" if slingshot_by_rating else "seeding"))
                    rating_gap_wins = tourney.get_big_seed_gap_wins(div_index, limit=table_row_limit, use_rating=slingshot_by_rating)
                    rows = []
                    round_names = {}
                    for (g, winner_rating, loser_rating, winner_seed, loser_seed) in rating_gap_wins:
                        winner = g.get_winner()
                        loser = g.get_loser()
                        if not winner or not loser:
                            continue
                        round_no = g.get_round_no()
                        if round_no not in round_names:
                            round_names[round_no] = tourney.get_round_name(round_no)
                        round_name = round_names[round_no]
                        score_str = g.format_score(force_winner_first=True)
                        rows.append((round_name,
                                htmlcommon.player_to_link(winner, tourney_name),
                                score_str,
                                htmlcommon.player_to_link(loser, tourney_name),
                                winner_rating if slingshot_by_rating else winner_seed,
                                loser_rating if slingshot_by_rating else loser_seed,
                                loser_rating - winner_rating if slingshot_by_rating else winner_seed - loser_seed
                        ))

                    ranking_by = "rating" if slingshot_by_rating else "seeding"
                    if slingshot_by_rating:
                        rank_formatter = lambda x : ("%.2f" % (x))
                    else:
                        rank_formatter = lambda x : htmlcommon.ordinal_number(x)
                    htmlcommon.write_ranked_table(
                            response,
                            [ "Round", "David", "Score", "Goliath", "Winner's " + ranking_by, "Loser's " + ranking_by, ranking_by.capitalize() + " gap" ],
                            [ "rankname", "rankname rankhighlight", "rankscore", "rankname", "ranknumber", "ranknumber", "ranknumber rankhighlight", "ranknumber" ],
                            rows,
                            key_fn=lambda x : x[6],
                            no_escape_html=[1, 3],
                            formatters={
                                4 : rank_formatter,
                                5 : rank_formatter,
                                6 : rank_formatter if slingshot_by_rating else str
                            }
                    )

            if do_show_rerate_button:
                show_rerate_button(response, tourney)

        response.writeln("</div>") #mainpane
    except countdowntourney.TourneyException as e:
        htmlcommon.show_tourney_exception(response, e)

    response.writeln("</body>")
    response.writeln("</html>")
