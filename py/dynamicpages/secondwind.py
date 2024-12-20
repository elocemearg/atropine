#!/usr/bin/python3

import htmlcommon
import countdowntourney

def add_sign(num):
    if num == 0:
        return "0"
    else:
        return "%+d" % (num)

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourney_name = tourney.get_name()

    # How many rows of each table do we show? If not specified, show 10.
    table_row_limit = htmlcommon.int_or_none(form.getfirst("limit", "10"))
    if table_row_limit is None:
        table_row_limit = 10
    if table_row_limit == 0:
        table_row_limit = None

    htmlcommon.print_html_head(response, "Second Wind: " + str(tourney_name))
    response.writeln("<body>")

    try:
        htmlcommon.show_sidebar(response, tourney, expand_spot_prize_links=True)

        response.writeln("<div class=\"mainpane\">")
        response.writeln("<h1>Second Wind</h1>")

        response.writeln("<p>The players with the biggest score improvement in the second round compared to the first.</p>")

        latest_round = tourney.get_latest_round_no()

        if latest_round is None or latest_round < 2:
            response.writeln("<p>This is only meaningful after round 2.</p>")
        else:
            response.writeln("<form method=\"GET\" style=\"margin-bottom: 20px;\">")
            response.writeln("<div class=\"simpleformline\">")
            response.writeln("<label for=\"limit\">Show the top <input type=\"number\" min=\"0\" name=\"limit\" id=\"limit\" value=\"%d\"> rows, plus ties.</label>" % (0 if not table_row_limit else table_row_limit))
            response.writeln("</div>")
            response.writeln("<div class=\"simpleformline\">")
            response.writeln("<input type=\"submit\" value=\"Refresh\">")
            response.writeln("</div>")
            response.writeln("</form>")

            num_divisions = tourney.get_num_divisions()
            for div_index in range(num_divisions):
                div_name = tourney.get_division_name(div_index)
                if num_divisions > 1:
                    response.writeln("<h2>%s</h2>" % (htmlcommon.escape(div_name)))
                rows = tourney.get_score_diff_between_rounds(div_index, 1, 2, limit=table_row_limit)
                htmlcommon.write_ranked_table(
                        response,
                        [ "Player", "Round 1 score", "Round 2 score", "Difference" ],
                        [ "rankname", "ranknumber", "ranknumber", "ranknumber rankhighlight" ],
                        [
                            (htmlcommon.player_to_link(row[0], tourney_name),
                                row[1], row[2], row[3]) for row in rows
                        ],
                        key_fn=lambda x : -x[3],
                        no_escape_html=[0],
                        formatters={
                            3 : add_sign
                        }
                )
        response.writeln("""
<p>
Only games which count towards the standings are considered.
Points scored on tiebreaks do not count.
</p>
""")
        response.writeln("</div>") #mainpane
    except countdowntourney.TourneyException as e:
        htmlcommon.show_tourney_exception(response, e)

    response.writeln("</body>")
    response.writeln("</html>")
