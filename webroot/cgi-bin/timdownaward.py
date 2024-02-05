#!/usr/bin/python3

import sys
import cgicommon
import urllib.request, urllib.parse, urllib.error
import cgitb

baseurl = "/cgi-bin/timdownaward.py"

cgitb.enable()

cgicommon.writeln("Content-Type: text/html; charset=utf-8")
cgicommon.writeln("")

form = cgicommon.FieldStorage()
tourney_name = form.getfirst("tourney")

tourney = None

cgicommon.set_module_path()

import countdowntourney

cgicommon.print_html_head("Tim Down Award: %s" % (tourney_name))

cgicommon.writeln("<body>")

cgicommon.assert_client_from_localhost()

if tourney_name is None:
    cgicommon.writeln("<h1>No tourney specified</h1>")
    cgicommon.writeln("<p><a href=\"/cgi-bin/home.py\">Home</a></p>")
    cgicommon.writeln("</body></html>")
    sys.exit(0)

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
    cgicommon.show_sidebar(tourney, show_misc_table_links=True)

    num_losing_games = cgicommon.int_or_none(form.getfirst("numlosinggames", 3))
    if num_losing_games is None or num_losing_games < 0:
        num_losing_games = 3

    cgicommon.writeln("<div class=\"mainpane\">")

    cgicommon.writeln("<h1>Tim Down Award</h1>")

    cgicommon.writeln("<form action=\"%s\" method=\"GET\">" % (baseurl))
    cgicommon.writeln("<p>")
    cgicommon.writeln("The Tim Down Award goes to the player whose opponents have the highest average standings position, and who lost ")
    cgicommon.writeln("<input type=\"number\" name=\"numlosinggames\" value=\"%d\" min=\"0\" max=\"999\" size=\"3\" />" % (num_losing_games))
    cgicommon.writeln("or more games.")
    cgicommon.writeln("</p>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourney_name, True)))
    cgicommon.writeln("<input type=\"submit\" name=\"submit\" value=\"Refresh\" />")
    cgicommon.writeln("</p>")
    cgicommon.writeln("</form>")

    num_divisions = tourney.get_num_divisions()
    for division in range(num_divisions):
        if num_divisions > 1:
            div_name = tourney.get_division_name(division)
            cgicommon.writeln("<h2>%s</h2>" % (cgicommon.escape(div_name)))

        td_standings = tourney.get_tim_down_award_standings(division, num_losing_games)

        pos = 0
        joint = 1
        prev_avg_opp_rank = None

        if not td_standings:
            cgicommon.writeln("<p>No players have lost %d or more games.</p>" % (num_losing_games))
        else:
            cgicommon.write_ranked_table(
                    [ "Player", "Opp. ranks", "Avg. opp. rank" ],
                    [ "rankname", "ranktext", "ranknumber rankhighlight" ],
                    [
                        ( cgicommon.player_to_link(row[0], tourney_name),
                            ", ".join(map(str, row[1])),
                            row[2] ) for row in td_standings
                    ],
                    key_fn=lambda x : x[2],
                    no_escape_html=[0],
                    formatters={2 : (lambda x : "%.2f" % (x)) }
            )

    cgicommon.writeln("<p>Only games which count towards the standings are considered.</p>")
    cgicommon.writeln("</div>") # mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e)

cgicommon.writeln("</body></html>")

sys.exit(0)
