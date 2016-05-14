#!/usr/bin/python

import cgi
import cgitb
import cgicommon
import sys
import csv
import os
import urllib

cgitb.enable()

cgicommon.set_module_path()
import countdowntourney

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;

print "Content-Type: text/html; charset=utf-8"
print ""

baseurl = "/cgi-bin/divsetup.py"
form = cgi.FieldStorage()
tourneyname = form.getfirst("tourney")
num_divisions = int_or_none(form.getfirst("numdivisions"))
division_size_multiple = int_or_none(form.getfirst("divsizemultiple"))

if num_divisions is None:
    num_divisions = 1
if division_size_multiple is None:
    division_size_multiple = 2

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Division Setup: " + str(tourneyname));

print "<body>";

if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);

cgicommon.show_sidebar(tourney)

print "<div class=\"mainpane\">";
print "<h1>Division Setup</h1>";

if tourneyname is None:
    print "<h1>Sloblock</h1>";
    print "<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>";
elif not tourney:
    print "<p>No valid tourney name specified</p>";
else:
    #print '<p><a href="%s?tourney=%s">%s</a></p>' % (baseurl, urllib.quote_plus(tourneyname), cgi.escape(tourneyname));
    if request_method == "POST":
        if num_divisions is None or num_divisions < 1:
            print "<p>Number of divisions must be a positive integer.</p>"
        elif division_size_multiple is None or division_size_multiple < 1:
            print "<p>Division size multiple must be a positive integer.</p>"
        else:
            # Find which players' names have had the "put in top division"
            # box ticked
            promotees = []
            index = 0
            while form.getfirst("promotename%d" % (index)):
                name = form.getfirst("promotename%d" % (index))
                promote = int_or_none(form.getfirst("promote%d" % (index)))
                if promote:
                    promotees.append(name)
                index += 1
            try:
                tourney.set_player_divisions(num_divisions, division_size_multiple, promotees)
            except countdowntourney.TourneyException as e:
                cgicommon.show_tourney_exception(e)
    if request_method in ["GET", "POST"]:
        players = tourney.get_players()
        num_divisions = tourney.get_num_divisions()
        num_games = tourney.get_num_games()
        if len(players) == 0:
            print "<p>"
            print "The tourney doesn't have any players yet, so you can't set up divisions."
            if num_games == 0:
                print "You can define the list of players on the <a href=\"tourneysetup.py?tourney=%s\">Tourney Setup</a> page." % (urllib.quote_plus(tourney.get_name()))

            print "</p>"
        else:
            print "<p><strong>N.B.</strong> To change the division assignment of an individual player, use the <a href=\"/cgi-bin/player.py?tourney=%s\">Player Setup</a> page. The form below will overwrite, and lose, any previous assignments of players to divisions, whether made from this page or in Player Setup.</p>" % (urllib.quote_plus(tourneyname))
            if num_games > 0:
                cgicommon.show_warning_box("The tourney has already started. Reassigning player divisions will only take effect for rounds whose fixtures have yet to be generated. Existing games will not be changed.")
            print "<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.quote_plus(tourneyname))
            print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgi.escape(tourneyname))
            print "<p>"
            print "Number of divisions: <input type=\"number\" min=\"1\" size=\"4\" maxlength=\"4\" name=\"numdivisions\" value=\"%d\" />" % (num_divisions)
            print "</p><p>"
            print "When assigning divisions by rating, ensure the number of active players in a division is a multiple of "
            print "<input type=\"number\" name=\"divsizemultiple\" min=\"1\" size=\"4\" maxlength=\"4\" value=\"%d\" />" % (division_size_multiple)
            print "</p>"

            div_players = [ [] for i in range(num_divisions) ]
            for p in players:
                div_players[p.get_division()].append(p)
            for div_index in range(0, num_divisions):
                div_players[div_index] = sorted(div_players[div_index], key=lambda x : (x.get_rating()), reverse=True)

            print "<p>Players will be distributed, by rating, into divisions. The divisions will be sized as equally as possible subject to the constraints above. If the divisions cannot be equally-sized, higher divisions will be given more players.</p>"
            print "<p>"
            print "<input type=\"submit\" name=\"setdivs\" value=\"Distribute players into divisions\" />"
            print "</p>"

            print "<hr />"

            print "<p>Players may be manually assigned to the top division by ticking the boxes below before distributing. Any players manually promoted in this way will <em>replace</em> that many non-ticked players in the top division. If you want the top-rated players to remain in the top division along with the manually-promoted players, and have a larger top division, tick the promote box on all the players in the top division before distributing.</p>"
            player_seq = 0
            for div_index in range(0, num_divisions):
                print "<h2>%s</h2>" % (cgi.escape(tourney.get_division_name(div_index)))
                num_withdrawn = len([p for p in div_players[div_index] if p.is_withdrawn()])
                if num_withdrawn > 0:
                    print "<p>%d active players, and %d withdrawn.</p>" % (len(div_players[div_index]) - num_withdrawn, num_withdrawn)
                else:
                    print "<p>%d active players.</p>" % (len(div_players[div_index]))
                print "<table>"
                print "<th>Name</th><th>Rating</th><th>Promote to top division</th>"
                for p in div_players[div_index]:
                    print "<tr>"
                    print "<td>%s%s</td><td align=\"right\">%g</td><td align=\"center\"><input type=\"checkbox\" name=\"promote%d\" value=\"1\" %s />" % (
                            cgicommon.player_to_link(p, tourney.get_name()),
                            " (withdrawn)" if p.is_withdrawn() else "",
                            p.get_rating(), player_seq,
                            "checked" if p.is_division_fixed() else "")
                    print "<input type=\"hidden\" name=\"promotename%d\" value=\"%s\" />" % (player_seq, cgi.escape(p.get_name(), True))
                    print "</tr>"
                    player_seq += 1
                print "</table>"

            print "<p>"
            print "<input type=\"submit\" name=\"setdivs\" value=\"Distribute players into divisions\" />"
            print "</p>"
            print "</form>"

print "</div>"
print "</body>"

print "</html>"

sys.exit(0)
