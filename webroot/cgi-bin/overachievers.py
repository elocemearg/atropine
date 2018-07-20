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

cgicommon.print_html_head("Overachievers: " + str(tourney_name))
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

    cgicommon.writeln("<div class=\"mainpane\">")

    cgicommon.writeln("<h1>Overachievers</h1>")
    cgicommon.writeln("<p>Each player is assigned a seed according to their rating, with the top-rated player in a division being the #1 seed, and so on down. Players are listed here in order of the difference between their position in the standings table and their seed position.</p>")

    num_divisions = tourney.get_num_divisions()
    for div_index in range(num_divisions):
        div_name = tourney.get_division_name(div_index)
        overachievements = tourney.get_players_overachievements(div_index)
        if num_divisions > 1:
            cgicommon.writeln("<h2>%s</h2>" % (cgicommon.escape(div_name)))
        if not overachievements:
            cgicommon.writeln("<p>There are no players to show.</p>")
            continue
        if tourney.are_player_ratings_uniform(div_index):
            cgicommon.show_warning_box("<p>Here all the players have the same rating, so this table isn't likely to be of much use to you.</p>")
        cgicommon.writeln("<table class=\"miscranktable\">")
        cgicommon.writeln("<tr>")
        cgicommon.writeln("<th></th><th>Player</th><th>Seed</th><th>Pos</th><th>+/-</th>")
        cgicommon.writeln("</tr>")
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
            cgicommon.writeln("<tr>")
            cgicommon.writeln("<td class=\"overachieverspos\">%d</td>" % (pos))
            cgicommon.writeln("<td class=\"overachieversname\">%s</td>" % (cgicommon.player_to_link(player, tourney_name)))
            cgicommon.writeln("<td class=\"overachieversseed\">%d</td>" % (seed))
            cgicommon.writeln("<td class=\"overachieversstandingspos\">%d</td>" % (standings_pos))
            cgicommon.writeln("<td class=\"overachieversoverachievement\">")
            if overachievement == 0:
                cgicommon.writeln("0")
            else:
                cgicommon.writeln("%+d" % (overachievement))
            cgicommon.writeln("</td>")

            cgicommon.writeln("</tr>")
            prev_overachievement = overachievement
        cgicommon.writeln("</table>")

    cgicommon.writeln("</div>") #mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e)

cgicommon.writeln("</body>")
cgicommon.writeln("</html>")

sys.exit(0)


