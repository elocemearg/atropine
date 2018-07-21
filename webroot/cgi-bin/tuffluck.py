#!/usr/bin/python3

import sys
import cgicommon
import urllib.request, urllib.parse, urllib.error
import cgi
import cgitb

cgitb.enable()

cgicommon.writeln("Content-Type: text/html; charset=utf-8")
cgicommon.writeln("")

form = cgi.FieldStorage()
tourney_name = form.getfirst("tourney")

tourney = None

cgicommon.set_module_path()

import countdowntourney

cgicommon.print_html_head("Tuff luck: " + str(tourney_name))

cgicommon.writeln("<body>")

cgicommon.assert_client_from_localhost()

if tourney_name is None:
    cgicommon.writeln("<h1>No tourney specified</h1>")
    cgicommon.writeln("<p><a href=\"/cgi-bin/home.py\">Home</a></p>")
    cgicommon.writeln("</body></html>")
    sys.exit(0)

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
    cgicommon.show_sidebar(tourney)
    num_losing_games = cgicommon.int_or_none(form.getfirst("numlosinggames", 3))
    if num_losing_games is None or num_losing_games <= 0:
        num_losing_games = 3

    cgicommon.writeln("<div class=\"mainpane\">")

    cgicommon.writeln("<h1>Tuff Luck</h1>")

    cgicommon.writeln("<form action=\"/cgi-bin/tuffluck.py\" method=\"GET\">")
    cgicommon.writeln("<p>")
    cgicommon.writeln("A player's Tuff Luck is their aggregate losing margin over their")
    cgicommon.writeln("<input type=\"number\" name=\"numlosinggames\" value=\"%d\" min=\"1\" max=\"999\" size=\"3\" />" % (num_losing_games))
    cgicommon.writeln("closest losing games, for players who have lost at least that many games.")
    cgicommon.writeln("</p>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourney_name, True)))
    cgicommon.writeln("<input type=\"submit\" name=\"submit\" value=\"Refresh\" />")
    cgicommon.writeln("</p>")
    cgicommon.writeln("</form>")

    players_tuff_luck = tourney.get_players_tuff_luck(num_losing_games)

    pos = 0
    joint = 1
    prev_tuffness = None
    if not players_tuff_luck:
        cgicommon.writeln("<p>No players have lost %d or more games.</p>" % (num_losing_games))
    else:
        cgicommon.writeln("<table class=\"miscranktable\">")
        cgicommon.writeln("<tr>")
        cgicommon.writeln("<th></th><th>Player</th><th>Margins</th><th>Tuff Luck</th>")
        cgicommon.writeln("</tr>")
        for row in players_tuff_luck:
            player = row[0]
            tuffness = row[1]
            margins = row[2]
            if prev_tuffness is None or prev_tuffness != tuffness:
                pos += joint
                joint = 1
            else:
                joint += 1
            cgicommon.writeln("<tr class=\"tuffluckrow\">")
            cgicommon.writeln("<td class=\"tuffluckpos\">%d</td>" % (pos))
            cgicommon.writeln("<td class=\"tuffluckname\">%s</td>" % (cgicommon.player_to_link(player, tourney_name)))
            cgicommon.writeln("<td class=\"tuffluckmargins\">%s</td>" % (", ".join(map(str, margins))))
            cgicommon.writeln("<td class=\"tufflucktuffness\">%d</td>" % (tuffness))
            cgicommon.writeln("</tr>")
            prev_tuffness = tuffness
        cgicommon.writeln("</table>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("For the purpose of Tuff Luck, games which go to a tiebreak have a margin of zero. Games adjudicated as a loss for both players do not count. Only games which count towards the standings are considered.")
    cgicommon.writeln("</p>")
    cgicommon.writeln("</div>") #mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e)

cgicommon.writeln("</body>")
cgicommon.writeln("</html>")

sys.exit(0)

