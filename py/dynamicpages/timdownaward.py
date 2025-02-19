#!/usr/bin/python3

import htmlcommon
import countdowntourney

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourney_name = tourney.get_name()

    htmlcommon.print_html_head(response, "Tim Down Award: %s" % (tourney_name))

    response.writeln("<body>")

    try:
        htmlcommon.show_sidebar(response, tourney, expand_spot_prize_links=True)

        num_losing_games = htmlcommon.int_or_none(form.getfirst("numlosinggames", 3))
        if num_losing_games is None or num_losing_games < 0:
            num_losing_games = 3

        response.writeln("<div class=\"mainpane\">")

        response.writeln("<h1>Tim Down Award</h1>")

        response.writeln("<form method=\"GET\" class=\"spaced\">")
        response.writeln("The Tim Down Award goes to the player whose opponents have the highest average standings position, and who lost ")
        response.writeln("<input type=\"number\" name=\"numlosinggames\" value=\"%d\" min=\"0\" max=\"999\" size=\"3\" />" % (num_losing_games))
        response.writeln("or more games.")
        response.writeln("<br>")
        response.writeln("<input type=\"submit\" value=\"Refresh\" />")
        response.writeln("</form>")

        num_divisions = tourney.get_num_divisions()
        for division in range(num_divisions):
            if num_divisions > 1:
                div_name = tourney.get_division_name(division)
                response.writeln("<h2>%s</h2>" % (htmlcommon.escape(div_name)))

            td_standings = tourney.get_tim_down_award_standings(division, num_losing_games)

            pos = 0
            joint = 1
            prev_avg_opp_rank = None

            if not td_standings:
                response.writeln("<p>No players have lost %d or more games.</p>" % (num_losing_games))
            else:
                htmlcommon.write_ranked_table(response,
                        [ "Player", "Opp. ranks", "Avg. opp. rank" ],
                        [ "rankname", "ranktext", "ranknumber rankhighlight" ],
                        [
                            ( htmlcommon.player_to_link(row[0], tourney_name),
                                ", ".join(map(str, row[1])),
                                row[2] ) for row in td_standings
                        ],
                        key_fn=lambda x : x[2],
                        no_escape_html=[0],
                        formatters={2 : (lambda x : "%.2f" % (x)) }
                )

        response.writeln("""
<p>
Only games which count towards the standings are considered.
</p>
<p>
This page was added to Atropine in 2019 and named after Tim Down, who often
found himself subject to a tough draw. As of December 2024, the Tim Down Award
has never been won by Tim Down.
</p>
""")
        response.writeln("</div>") # mainpane
    except countdowntourney.TourneyException as e:
        htmlcommon.show_tourney_exception(response, e)

    response.writeln("</body></html>")
