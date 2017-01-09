#!/usr/bin/python

import sys
import cgicommon
import urllib
import cgi
import cgitb

cgitb.enable()

print "Content-Type: text/html; charset=utf-8"
print ""

form = cgi.FieldStorage()
tourney_name = form.getfirst("tourney")

tourney = None

cgicommon.set_module_path()

import countdowntourney

cgicommon.print_html_head("Tuff luck: " + str(tourney_name))

print "<body>"

if tourney_name is None:
    print "<h1>No tourney specified</h1>"
    print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>"
    print "</body></html>"
    sys.exit(0)

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
    cgicommon.show_sidebar(tourney)
    num_losing_games = cgicommon.int_or_none(form.getfirst("numlosinggames", 3))
    if num_losing_games is None or num_losing_games <= 0:
        num_losing_games = 3

    print "<div class=\"mainpane\">"

    print "<h1>Tuff Luck</h1>"

    print "<form action=\"/cgi-bin/tuffluck.py\" method=\"GET\">"
    print "<p>"
    print "A player's Tuff Luck is their aggregate losing margin over their"
    print "<input type=\"number\" name=\"numlosinggames\" value=\"%d\" min=\"1\" max=\"999\" size=\"3\" maxlength=\"3\" />" % (num_losing_games)
    print "closest losing games, for players who have lost at least that many games."
    print "</p>"
    print "<p>"
    print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgi.escape(tourney_name, True))
    print "<input type=\"submit\" name=\"submit\" value=\"Refresh\" />"
    print "</p>"
    print "</form>"

    players_tuff_luck = tourney.get_players_tuff_luck(num_losing_games)

    pos = 0
    joint = 1
    prev_tuffness = None
    if not players_tuff_luck:
        print "<p>No players have lost %d or more games.</p>" % (num_losing_games)
    else:
        print "<table class=\"miscranktable\">"
        print "<tr>"
        print "<th></th><th>Player</th><th>Margins</th><th>Tuff Luck</th>"
        print "</tr>"
        for row in players_tuff_luck:
            player = row[0]
            tuffness = row[1]
            margins = row[2]
            if prev_tuffness is None or prev_tuffness != tuffness:
                pos += joint
                joint = 1
            else:
                joint += 1
            print "<tr class=\"tuffluckrow\">"
            print "<td class=\"tuffluckpos\">%d</td>" % (pos)
            print "<td class=\"tuffluckname\">%s</td>" % (cgicommon.player_to_link(player, tourney_name))
            print "<td class=\"tuffluckmargins\">%s</td>" % (", ".join(map(str, margins)))
            print "<td class=\"tufflucktuffness\">%d</td>" % (tuffness)
            print "</tr>"
            prev_tuffness = tuffness
        print "</table>"
    print "<p>"
    print "For the purpose of Tuff Luck, games which go to a tiebreak have a margin of zero. Only games which count towards the standings are considered."
    print "</p>"
    print "</div>" #mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e)

print "</body>"
print "</html>"

sys.exit(0)

