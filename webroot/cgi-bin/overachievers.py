#!/usr/bin/python3

import sys
import os
import cgicommon
import urllib.request, urllib.parse, urllib.error
import cgi
import cgitb

cgitb.enable()

cgicommon.writeln("Content-Type: text/html; charset=utf-8")
cgicommon.writeln("")

form = cgi.FieldStorage()
tourney_name = form.getfirst("tourney")
baseurl = "/cgi-bin/overachievers.py"

tourney = None

cgicommon.set_module_path()

import countdowntourney

def show_rerate_button(tourney):
    tourney_name = tourney.get_name()
    cgicommon.writeln("<h2>Rerate players by player ID</h2>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("""
    Set the ratings of players in order, by player ID, which corresponds
    to the order in which they appeared in the list you put into the text
    box at the start of the tournament. The player at the top of the list
    (the lowest player ID) gets the highest rating, and the player at the
    bottom of the list (the highest player ID) gets the lowest rating. Any
    player with a rating of zero remains unchanged.""")
    cgicommon.writeln("</p>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("""
    This is useful if when you pasted in the player list you forgot to
    select the option which tells Atropine that they're in rating order,
    and now the Overachievers page thinks they're all seeded the same.
    """)
    cgicommon.writeln("</p>")

    cgicommon.writeln("<p>")
    cgicommon.writeln("""
    If you press this button, it will overwrite all other non-zero ratings
    you may have given the players. That's why you need to tick the box as
    well.
    """)
    cgicommon.writeln("</p>")

    cgicommon.writeln("<p>")
    cgicommon.writeln("<form method=\"POST\" action=\"%s?tourney=%s\">" % (cgicommon.escape(baseurl), urllib.parse.quote_plus(tourney_name)))
    cgicommon.writeln("<input type=\"submit\" name=\"reratebyplayerid\" value=\"Rerate players by player ID\" />")
    cgicommon.writeln("<input type=\"checkbox\" name=\"reratebyplayeridconfirm\" id=\"reratebyplayeridconfirm\" style=\"margin-left: 20px\" />")
    cgicommon.writeln("<label for=\"reratebyplayeridconfirm\">Yes, I'm sure</label>")

    cgicommon.writeln("</form>")
    cgicommon.writeln("</p>")


cgicommon.print_html_head("Overachievers: " + str(tourney_name))
cgicommon.writeln("<body>")

cgicommon.assert_client_from_localhost()

request_method = os.environ.get("REQUEST_METHOD", "")

if tourney_name is None:
    cgicommon.writeln("<h1>No tourney specified</h1>")
    cgicommon.writeln("<p><a href=\"/cgi-bin/home.py\">Home</a></p>")
    cgicommon.writeln("</body></html>")
    sys.exit(0)

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
    cgicommon.show_sidebar(tourney, show_misc_table_links=True)


    cgicommon.writeln("<div class=\"mainpane\">")

    cgicommon.writeln("<h1>Overachievers</h1>")

    if request_method == "POST" and "reratebyplayerid" in form and "reratebyplayeridconfirm" in form:
        try:
            tourney.rerate_players_by_id()
            cgicommon.show_success_box("Players successfully rerated by player ID.")
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e)

    if tourney.get_num_games() == 0:
        cgicommon.writeln("<p>No games have been played yet.</p>")
    else:
        cgicommon.writeln("<p>Each player is assigned a seed according to their rating, with the top-rated player in a division being the #1 seed, and so on down. Players are listed here in order of the difference between their position in the standings table and their seed position.</p>")

        num_divisions = tourney.get_num_divisions()
        do_show_rerate_button = False
        for div_index in range(num_divisions):
            div_name = tourney.get_division_name(div_index)
            overachievements = tourney.get_players_overachievements(div_index)
            if num_divisions > 1:
                cgicommon.writeln("<h2>%s</h2>" % (cgicommon.escape(div_name)))
            if not overachievements:
                cgicommon.writeln("<p>There are no players to show.</p>")
                continue
            if tourney.are_player_ratings_uniform(div_index):
                cgicommon.show_warning_box("<p>All the players have the same rating. This means the Overachievers table won't be meaningful. If when you set up the tournament you pasted the players into the player list in order of rating but forgot to tell Atropine you'd done that, try the \"Rerate players by player ID\" button below.</p>")
                do_show_rerate_button = True
            else:
                cgicommon.write_ranked_table(
                        [ "Player", "Seed", "Pos", "+/-" ],
                        [ "rankname", "ranknumber", "ranknumber", "ranknumber rankhighlight" ],
                        [
                            (cgicommon.player_to_link(row[0], tourney_name),
                                row[1], row[2], row[3]) for row in overachievements
                        ],
                        key_fn=lambda x : -x[3],
                        no_escape_html=[0],
                        formatters={3 : (lambda x : "0" if x == 0 else ("%+d" % (x)))}
                )
        if do_show_rerate_button:
            show_rerate_button(tourney)

    cgicommon.writeln("</div>") #mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e)

cgicommon.writeln("</body>")
cgicommon.writeln("</html>")

sys.exit(0)


