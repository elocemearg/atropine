#!/usr/bin/python3

import cgitb
import cgicommon
import sys
import csv
import os
import urllib.request, urllib.parse, urllib.error

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

cgicommon.writeln("Content-Type: text/html; charset=utf-8")
cgicommon.writeln("")

baseurl = "/cgi-bin/divsetup.py"
form = cgicommon.FieldStorage()
tourneyname = form.getfirst("tourney")
num_divisions_required = int_or_none(form.getfirst("numdivisions"))
division_size_multiple = int_or_none(form.getfirst("divsizemultiple"))
div_sort = form.getfirst("divsort")
if not div_sort or div_sort not in ["standings", "ratings"]:
    div_sort = "ratings"
else:
    div_sort = "standings"

if num_divisions_required is None:
    num_divisions_required = 1
if division_size_multiple is None:
    division_size_multiple = 2

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Division Setup: " + str(tourneyname));

cgicommon.writeln("<body onload=\"hide_div_renames();\">");

cgicommon.writeln("""
<script>
function show_div_rename(div) {
    buttondiv = document.getElementById("divrenamebutton" + div.toString());
    renamediv = document.getElementById("divrenamecontrols" + div.toString());
    textbox = document.getElementById("newdivnameinput" + div.toString())
    buttondiv.style.display = "none";
    renamediv.style.display = "inline";
    textbox.focus();
    textbox.select();
}

function hide_div_rename(div) {
    buttondiv = document.getElementById("divrenamebutton" + div.toString());
    renamediv = document.getElementById("divrenamecontrols" + div.toString());
    buttondiv.style.display = "inline";
    renamediv.style.display = "none";
}

function hide_div_renames() {
    buttons = document.getElementsByClassName("divrenamebutton");
    renames = document.getElementsByClassName("divrenamecontrols");
    if (buttons != null) {
        for (var i = 0; i < buttons.length; ++i) {
            buttons[i].style.display = "inline";
        }
    }

    if (renames != null) {
        for (var i = 0; i < renames.length; ++i) {
            renames[i].style.display = "none";
        }
    }
}
</script>
""")

cgicommon.assert_client_from_localhost()

if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);

cgicommon.show_sidebar(tourney)

cgicommon.writeln("<div class=\"mainpane\">");
cgicommon.writeln("<h1>Division Setup</h1>");

if tourneyname is None:
    cgicommon.writeln("<h1>Sloblock</h1>");
    cgicommon.writeln("<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>");
elif not tourney:
    cgicommon.writeln("<p>No valid tourney name specified</p>");
else:
    #print '<p><a href="%s?tourney=%s">%s</a></p>' % (baseurl, urllib.quote_plus(tourneyname), cgicommon.escape(tourneyname));
    name_to_position = dict()
    name_to_div_position = dict()
    num_divisions = tourney.get_num_divisions()
    for s in tourney.get_standings():
        name_to_position[s.name] = s.position
    if request_method == "POST":
        if form.getfirst("setdivs"):
            if num_divisions_required is None or num_divisions_required < 1:
                cgicommon.writeln("<p>Number of divisions must be a positive integer.</p>")
            elif division_size_multiple is None or division_size_multiple < 1:
                cgicommon.writeln("<p>Division size multiple must be a positive integer.</p>")
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
                    tourney.set_player_divisions(num_divisions_required, division_size_multiple, div_sort == "rating", promotees)
                    num_divisions = tourney.get_num_divisions()
                except countdowntourney.TourneyException as e:
                    cgicommon.show_tourney_exception(e)

        # If we've been asked to rename any division, rename it now
        for div_index in range(num_divisions):
            if form.getfirst("setdivname%d" % (div_index)):
                new_name = form.getfirst("newdivname%d" % (div_index)).strip()
                if new_name:
                    tourney.set_division_name(div_index, new_name)

    if request_method in ["GET", "POST"]:
        players = tourney.get_players()
        num_divisions = tourney.get_num_divisions()
        num_games = tourney.get_num_games()
        if len(players) == 0:
            cgicommon.writeln("<p>")
            cgicommon.writeln("The tourney doesn't have any players yet, so you can't set up divisions.")
            if num_games == 0:
                cgicommon.writeln("You can define the list of players on the <a href=\"tourneysetup.py?tourney=%s\">Tourney Setup</a> page." % (urllib.parse.quote_plus(tourney.get_name())))

            cgicommon.writeln("</p>")
        else:
            for div_index in range(num_divisions):
                for s in tourney.get_standings(div_index):
                    name_to_div_position[s.name] = s.position

            div_players = [ [] for i in range(num_divisions) ]
            for p in players:
                div_players[p.get_division()].append(p)
            if div_sort == "standings":
                for div_index in range(0, num_divisions):
                    div_players[div_index] = sorted(div_players[div_index], key=lambda x : name_to_position[x.get_name()])
            else:
                for div_index in range(0, num_divisions):
                    div_players[div_index] = sorted(div_players[div_index], key=lambda x : (x.get_rating()), reverse=True)

            cgicommon.writeln("<h2>Summary</h2>")
            cgicommon.writeln("<table class=\"misctable\">")
            cgicommon.writeln("<tr><th rowspan=\"2\">Division</th><th colspan=\"2\">Players</th><th rowspan=\"2\"></th></tr>")
            cgicommon.writeln("<tr><th>Active</th><th>Withdrawn</th></tr>")

            div_active_player_count = [ len([p for p in div_players[div_index] if not p.is_withdrawn()]) for div_index in range(num_divisions) ]
            div_withdrawn_player_count = [ len([p for p in div_players[div_index] if p.is_withdrawn()]) for div_index in range(num_divisions) ]

            for div_index in range(num_divisions):
                div_name = tourney.get_division_name(div_index)
                cgicommon.writeln("<tr>")
                cgicommon.writeln("<td class=\"text\">%s</td>" % (cgicommon.escape(div_name)))
                cgicommon.writeln("<td class=\"number\">%d</td>" % (div_active_player_count[div_index]))
                cgicommon.writeln("<td class=\"number\">%d</td>" % (div_withdrawn_player_count[div_index]))
                cgicommon.writeln("<td class=\"control\" style=\"text-align: left\">")
                cgicommon.writeln("<div class=\"divrenamecontrols\" id=\"divrenamecontrols%d\">" % (div_index))
                cgicommon.writeln("<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.parse.quote_plus(tourneyname)))
                cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourneyname, True)))
                cgicommon.writeln("<input type=\"text\" id=\"newdivnameinput%d\" name=\"newdivname%d\" value=\"%s\" />" % (div_index, div_index, cgicommon.escape(div_name, True)))
                cgicommon.writeln("<input type=\"submit\" name=\"setdivname%d\" value=\"Save\" />" % (div_index))
                cgicommon.writeln("<input type=\"button\" name=\"canceldivrename%d\" value=\"Cancel\" onclick=\"hide_div_rename(%d);\" />" % (div_index, div_index))
                cgicommon.writeln("</form>")
                cgicommon.writeln("</div>")
                cgicommon.writeln("<div class=\"divrenamebutton\" id=\"divrenamebutton%d\">" % (div_index))
                cgicommon.writeln("<input type=\"button\" name=\"showdivrename%d\" value=\"Rename\" onclick=\"show_div_rename(%d);\" />" % (div_index, div_index))
                cgicommon.writeln("</div>")
                cgicommon.writeln("</td></tr>")
            cgicommon.writeln("</table>")

            cgicommon.writeln("<hr />")

            cgicommon.writeln("<h2>Division assignment by rating or standings position</h2>")
            cgicommon.writeln("<p><strong>N.B.</strong> To change the division assignment of an individual player, use the <a href=\"/cgi-bin/player.py?tourney=%s\">Player Setup</a> page. The form below will overwrite, and lose, any previous assignments of players to divisions, whether made from this page or in Player Setup.</p>" % (urllib.parse.quote_plus(tourneyname)))
            if num_games > 0:
                cgicommon.show_warning_box("The tourney has already started. Reassigning player divisions will only take effect for rounds whose fixtures have yet to be generated. Existing games will not be changed.")
            cgicommon.writeln("<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.parse.quote_plus(tourneyname)))
            cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourneyname)))

            # Show a table for each division, containing its players
            cgicommon.writeln("<p>Players may be manually assigned to the top division by ticking the boxes below before distributing. Any players manually promoted in this way will <em>replace</em> that many non-ticked players in the top division. If you want the top-rated players to remain in the top division along with the manually-promoted players, and have a larger top division, tick the promote box on all the players in the top division before distributing.</p>")
            player_seq = 0
            for div_index in range(0, num_divisions):
                div_name = tourney.get_division_name(div_index)
                cgicommon.writeln("<h3>%s</h3>" % (cgicommon.escape(div_name)))
                cgicommon.writeln("<table class=\"misctable\">")
                cgicommon.writeln("<tr>")
                cgicommon.writeln("<th rowspan=\"2\">Name</th>")
                cgicommon.writeln("<th rowspan=\"2\">Rating</th>")
                cgicommon.writeln("<th colspan=\"2\">Position</th>")
                cgicommon.writeln("<th rowspan=\"2\">Promote to top division</th>")
                cgicommon.writeln("</tr>")
                cgicommon.writeln("<tr>")
                cgicommon.writeln("<th>Division</th><th>Overall</th>")
                cgicommon.writeln("</tr>")
                for p in div_players[div_index]:
                    cgicommon.writeln("<tr>")
                    cgicommon.writeln("<td class=\"text\">%s%s</td>" % (cgicommon.player_to_link(p, tourney.get_name()), " (withdrawn)" if p.is_withdrawn() else ""))
                    cgicommon.writeln("<td class=\"number\">%g</td>" % (p.get_rating()))
                    cgicommon.writeln("<td class=\"number\">%d</td>" % (name_to_div_position[p.get_name()]))
                    cgicommon.writeln("<td class=\"number\">%d</td>" % (name_to_position[p.get_name()]))
                    cgicommon.writeln("<td class=\"control\"><input type=\"checkbox\" name=\"promote%d\" value=\"1\" %s />" % (
                            player_seq, "checked" if p.is_division_fixed() else ""))
                    cgicommon.writeln("<input type=\"hidden\" name=\"promotename%d\" value=\"%s\" />" % (player_seq, cgicommon.escape(p.get_name(), True)))
                    cgicommon.writeln("</tr>")
                    player_seq += 1
                cgicommon.writeln("</table>")

            cgicommon.writeln("<h3>Assign divisions</h3>")
            cgicommon.writeln("<p>")
            cgicommon.writeln("Number of divisions: <input type=\"number\" min=\"1\" name=\"numdivisions\" value=\"%d\" />" % (num_divisions))
            cgicommon.writeln("</p><p>")
            cgicommon.writeln("When assigning divisions, ensure the number of active players in a division is a multiple of ")
            cgicommon.writeln("<input type=\"number\" name=\"divsizemultiple\" min=\"1\" value=\"%d\" />" % (division_size_multiple))
            cgicommon.writeln("</p>")

            cgicommon.writeln("<p>")
            cgicommon.writeln("<label for=\"divsortrating\"><input type=\"radio\" name=\"divsort\" value=\"ratings\" id=\"divsortrating\" %s /> Assign divisions by rating</label>" % ("checked" if div_sort == "ratings" else ""))
            cgicommon.writeln("<br />")
            cgicommon.writeln("<label for=\"divsortpos\"><input type=\"radio\" name=\"divsort\" value=\"standings\" id=\"divsortpos\" %s /> Assign divisions by standings position</label>" % ("checked" if div_sort == "standings" else ""))
            cgicommon.writeln("</p>")

            cgicommon.writeln("<p>Players will be distributed into divisions. The divisions will be sized as equally as possible subject to the constraints above. If the divisions cannot be equally-sized, higher divisions will be given more players.</p>")
            cgicommon.writeln("<p>")
            cgicommon.writeln("<input type=\"submit\" name=\"setdivs\" value=\"Distribute players into divisions\" />")
            cgicommon.writeln("</p>")

            cgicommon.writeln("</form>")

cgicommon.writeln("</div>")
cgicommon.writeln("</body>")

cgicommon.writeln("</html>")

sys.exit(0)
