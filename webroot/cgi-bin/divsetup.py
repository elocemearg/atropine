#!/usr/bin/python3

import cgi
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

print("Content-Type: text/html; charset=utf-8")
print("")

baseurl = "/cgi-bin/divsetup.py"
form = cgi.FieldStorage()
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

print("""
<script type="text/javascript">
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

print("<body onload=\"hide_div_renames();\">");

cgicommon.assert_client_from_localhost()

if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);

cgicommon.show_sidebar(tourney)

print("<div class=\"mainpane\">");
print("<h1>Division Setup</h1>");

if tourneyname is None:
    print("<h1>Sloblock</h1>");
    print("<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>");
elif not tourney:
    print("<p>No valid tourney name specified</p>");
else:
    #print '<p><a href="%s?tourney=%s">%s</a></p>' % (baseurl, urllib.quote_plus(tourneyname), cgi.escape(tourneyname));
    name_to_position = dict()
    name_to_div_position = dict()
    num_divisions = tourney.get_num_divisions()
    for s in tourney.get_standings():
        name_to_position[s.name] = s.position
    if request_method == "POST":
        if form.getfirst("setdivs"):
            if num_divisions_required is None or num_divisions_required < 1:
                print("<p>Number of divisions must be a positive integer.</p>")
            elif division_size_multiple is None or division_size_multiple < 1:
                print("<p>Division size multiple must be a positive integer.</p>")
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
            print("<p>")
            print("The tourney doesn't have any players yet, so you can't set up divisions.")
            if num_games == 0:
                print("You can define the list of players on the <a href=\"tourneysetup.py?tourney=%s\">Tourney Setup</a> page." % (urllib.parse.quote_plus(tourney.get_name())))

            print("</p>")
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
            
            print("<h2>Summary</h2>")
            print("<table class=\"divsummarytable\">")
            print("<tr><th></th><th colspan=\"2\">Players</th><th></th></tr>")
            print("<tr><th>Division</th><th>Active</th><th>Withdrawn</th><th></th></tr>")

            div_active_player_count = [ len([p for p in div_players[div_index] if not p.is_withdrawn()]) for div_index in range(num_divisions) ]
            div_withdrawn_player_count = [ len([p for p in div_players[div_index] if p.is_withdrawn()]) for div_index in range(num_divisions) ]

            for div_index in range(num_divisions):
                div_name = tourney.get_division_name(div_index)
                print("<tr>")
                print("<td class=\"divsummaryname\">%s</td>" % (cgi.escape(div_name)))
                print("<td class=\"divsummaryactiveplayers\">%d</td>" % (div_active_player_count[div_index]))
                print("<td class=\"divsummarywithdrawnplayers\">%d</td>" % (div_withdrawn_player_count[div_index]))
                print("<td class=\"divsummaryrename\">")
                print("<div class=\"divrenamecontrols\" id=\"divrenamecontrols%d\">" % (div_index))
                print("<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.parse.quote_plus(tourneyname)))
                print("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgi.escape(tourneyname, True)))
                print("<input type=\"text\" id=\"newdivnameinput%d\" name=\"newdivname%d\" value=\"%s\" />" % (div_index, div_index, cgi.escape(div_name, True)))
                print("<input type=\"submit\" name=\"setdivname%d\" value=\"Save\" />" % (div_index))
                print("<input type=\"button\" name=\"canceldivrename%d\" value=\"Cancel\" onclick=\"hide_div_rename(%d);\" />" % (div_index, div_index))
                print("</form>")
                print("</div>")
                print("<div class=\"divrenamebutton\" id=\"divrenamebutton%d\">" % (div_index))
                print("<input type=\"button\" name=\"showdivrename%d\" value=\"Rename\" onclick=\"show_div_rename(%d);\" />" % (div_index, div_index))
                print("</div>")
                print("</td></tr>")
            print("</table>")

            print("<hr />")

            print("<p><strong>N.B.</strong> To change the division assignment of an individual player, use the <a href=\"/cgi-bin/player.py?tourney=%s\">Player Setup</a> page. The form below will overwrite, and lose, any previous assignments of players to divisions, whether made from this page or in Player Setup.</p>" % (urllib.parse.quote_plus(tourneyname)))
            if num_games > 0:
                cgicommon.show_warning_box("The tourney has already started. Reassigning player divisions will only take effect for rounds whose fixtures have yet to be generated. Existing games will not be changed.")
            print("<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.parse.quote_plus(tourneyname)))
            print("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgi.escape(tourneyname)))

            # Show a table for each division, containing its players
            print("<p>Players may be manually assigned to the top division by ticking the boxes below before distributing. Any players manually promoted in this way will <em>replace</em> that many non-ticked players in the top division. If you want the top-rated players to remain in the top division along with the manually-promoted players, and have a larger top division, tick the promote box on all the players in the top division before distributing.</p>")
            player_seq = 0
            for div_index in range(0, num_divisions):
                div_name = tourney.get_division_name(div_index)
                print("<h2>%s</h2>" % (cgi.escape(div_name)))
                print("<table class=\"divtable\">")
                print("<tr>")
                print("<th rowspan=\"2\">Name</th>")
                print("<th rowspan=\"2\">Rating</th>")
                print("<th colspan=\"2\">Position</th>")
                print("<th rowspan=\"2\">Promote to top division</th>")
                print("</tr>")
                print("<tr>")
                print("<th>Division</th><th>Overall</th>")
                print("</tr>")
                for p in div_players[div_index]:
                    print("<tr>")
                    print("<td class=\"divtablename divtable\">%s%s</td>" % (cgicommon.player_to_link(p, tourney.get_name()), " (withdrawn)" if p.is_withdrawn() else ""))
                    print("<td class=\"divtablerating divtable\">%g</td>" % (p.get_rating()))
                    print("<td class=\"divtabledivpos divtable\">%d</td>" % (name_to_div_position[p.get_name()]))
                    print("<td class=\"divtablepos divtable\">%d</td>" % (name_to_position[p.get_name()]))
                    print("<td class=\"divtablepromote divtable\"><input type=\"checkbox\" name=\"promote%d\" value=\"1\" %s />" % (
                            player_seq, "checked" if p.is_division_fixed() else ""))
                    print("<input type=\"hidden\" name=\"promotename%d\" value=\"%s\" />" % (player_seq, cgi.escape(p.get_name(), True)))
                    print("</tr>")
                    player_seq += 1
                print("</table>")

            print("<hr />")

            print("<h2>Divide players into divisions</h2>")
            print("<p>")
            print("Number of divisions: <input type=\"number\" min=\"1\" size=\"4\" maxlength=\"4\" name=\"numdivisions\" value=\"%d\" />" % (num_divisions))
            print("</p><p>")
            print("When assigning divisions, ensure the number of active players in a division is a multiple of ")
            print("<input type=\"number\" name=\"divsizemultiple\" min=\"1\" size=\"4\" maxlength=\"4\" value=\"%d\" />" % (division_size_multiple))
            print("</p>")

            print("<p>")
            print("<input type=\"radio\" name=\"divsort\" value=\"ratings\" %s /> Assign divisions by rating" % ("checked" if div_sort == "ratings" else ""))
            print("<br />")
            print("<input type=\"radio\" name=\"divsort\" value=\"standings\" %s /> Assign divisions by standings position" % ("checked" if div_sort == "standings" else ""))
            print("</p>")

            print("<p>Players will be distributed into divisions. The divisions will be sized as equally as possible subject to the constraints above. If the divisions cannot be equally-sized, higher divisions will be given more players.</p>")
            print("<p>")
            print("<input type=\"submit\" name=\"setdivs\" value=\"Distribute players into divisions\" />")
            print("</p>")

            #print "<p>"
            #print "<input type=\"submit\" name=\"setdivs\" value=\"Distribute players into divisions\" />"
            #print "</p>"
            print("</form>")

print("</div>")
print("</body>")

print("</html>")

sys.exit(0)
