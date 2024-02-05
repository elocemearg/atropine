#!/usr/bin/python3

import sys
import cgicommon
import urllib.request, urllib.parse, urllib.error
import cgitb

cgitb.enable()

cgicommon.writeln("Content-Type: text/html; charset=utf-8")
cgicommon.writeln("")

form = cgicommon.FieldStorage()
tourney_name = form.getfirst("tourney")

tourney = None

cgicommon.set_module_path()

import countdowntourney

cgicommon.print_html_head("Lucky Stiff: " + str(tourney_name))

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
    num_wins = cgicommon.int_or_none(form.getfirst("numwins", 3))
    if num_wins is None or num_wins <= 0:
        num_wins = 3

    cgicommon.writeln("<div class=\"mainpane\">")

    cgicommon.writeln("<h1>Lucky Stiff</h1>")

    cgicommon.writeln("<form action=\"/cgi-bin/luckystiff.py\" method=\"GET\">")
    cgicommon.writeln("<p>")
    cgicommon.writeln("The Lucky Stiff is the player whose")
    cgicommon.writeln("<input type=\"number\" name=\"numwins\" value=\"%d\" min=\"1\" max=\"999\" size=\"3\" />" % (num_wins))
    cgicommon.writeln("closest winning games had the lowest aggregate winning margin. It is the opposite of <a href=\"/cgi-bin/tuffluck.py?tourney=%s\">Tuff Luck</a>." % (cgicommon.escape(tourney_name, True)))
    cgicommon.writeln("</p>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourney_name, True)))
    cgicommon.writeln("<input type=\"submit\" name=\"submit\" value=\"Refresh\" />")
    cgicommon.writeln("</p>")
    cgicommon.writeln("</form>")

    players_lucky_stiff = tourney.get_players_lucky_stiff(num_wins)

    pos = 0
    joint = 1
    prev_stiffness = None
    if not players_lucky_stiff:
        cgicommon.writeln("<p>No players have won %d or more games.</p>" % (num_wins))
    else:
        cgicommon.write_ranked_table(
                [ "Player", "Wins", "Closest margins", "Total" ],
                [ "rankname", "ranknumber", "ranktext", "ranknumber rankhighlight" ],
                [
                    ( cgicommon.player_to_link(player, tourney_name),
                        num_wins, ", ".join(map(str, margins)), stiffness) for (player, num_wins, stiffness, margins) in players_lucky_stiff
                ],
                lambda x : x[3],
                [ 0 ]
        )
    cgicommon.writeln("<p>")
    cgicommon.writeln("For the purpose of Lucky Stiff, games won a tiebreak have a margin of zero. Only games which count towards the standings are considered.")
    cgicommon.writeln("</p>")
    cgicommon.writeln("</div>") #mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e)

cgicommon.writeln("</body>")
cgicommon.writeln("</html>")

sys.exit(0)

