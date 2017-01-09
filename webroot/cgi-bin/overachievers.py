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

cgicommon.print_html_head("Overachievers: " + str(tourney_name))
print "<body>"

if tourney_name is None:
    print "<h1>No tourney specified</h1>"
    print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>"
    print "</body></html>"
    sys.exit(0)

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
    cgicommon.show_sidebar(tourney)

    print "<div class=\"mainpane\">"

    print "<h1>Overachievers</h1>"
    print "<p>Each player is assigned a seed according to their rating, with the top-rated player in a division being the #1 seed, and so on down. Players are listed here in order of the difference between their position in the standings table and their seed position.</p>"

    num_divisions = tourney.get_num_divisions()
    for div_index in range(num_divisions):
        div_name = tourney.get_division_name(div_index)
        overachievements = tourney.get_players_overachievements(div_index)
        if num_divisions > 1:
            print "<h2>%s</h2>" % (cgi.escape(div_name))
        if tourney.are_player_ratings_uniform(div_index):
            cgicommon.show_warning_box("<p>Here all the players have the same rating, so this table isn't likely to be of much use to you.</p>")
        print "<table class=\"miscranktable\">"
        print "<tr>"
        print "<th></th><th>Player</th><th>Seed</th><th>Pos</th><th>+/-</th>"
        print "</tr>"
        pos = 0
        joint = 1
        prev_overachievement = None
        for row in overachievements:
            player = row[0]
            seed = row[1]
            standings_pos = row[2]
            overachievement = row[3]
            if prev_overachievement is None or prev_overachievement != overachievement:
                pos += joint
                joint = 1
            else:
                joint += 1
            print "<tr>"
            print "<td class=\"overachieverspos\">%d</td>" % (pos)
            print "<td class=\"overachieversname\">%s</td>" % (cgicommon.player_to_link(player, tourney_name))
            print "<td class=\"overachieversseed\">%d</td>" % (seed)
            print "<td class=\"overachieversstandingspos\">%d</td>" % (standings_pos)
            print "<td class=\"overachieversoverachievement\">"
            if overachievement == 0:
                print "0"
            else:
                print "%+d" % (overachievement)
            print "</td>"

            print "</tr>"
            prev_overachievement = overachievement
        print "</table>"

    print "</div>" #mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e)

print "</body>"
print "</html>"

sys.exit(0)


