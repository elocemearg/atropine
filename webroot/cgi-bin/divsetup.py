#!/usr/bin/python3

import cgicommon
import urllib.request, urllib.parse, urllib.error
import countdowntourney

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;

baseurl = "/cgi-bin/divsetup.py"

def handle(httpreq, response, tourney, request_method, form, query_string):
    tourneyname = tourney.name

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

    cgicommon.print_html_head(response, "Division Setup: " + str(tourneyname));

    response.writeln("<body onload=\"hide_div_renames();\">");

    response.writeln("""
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

    cgicommon.show_sidebar(response, tourney)

    response.writeln("<div class=\"mainpane\">");
    response.writeln("<h1>Division Setup</h1>");

    name_to_position = dict()
    name_to_div_position = dict()
    num_divisions = tourney.get_num_divisions()
    for s in tourney.get_standings():
        name_to_position[s.name] = s.position
    if request_method == "POST":
        if form.getfirst("setdivs"):
            if num_divisions_required is None or num_divisions_required < 1:
                response.writeln("<p>Number of divisions must be a positive integer.</p>")
            elif division_size_multiple is None or division_size_multiple < 1:
                response.writeln("<p>Division size multiple must be a positive integer.</p>")
            else:
                # Find which players' names have had the "put in top
                # division" box ticked
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
                    cgicommon.show_tourney_exception(response, e)

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
            response.writeln("<p>")
            response.writeln("The tourney doesn't have any players yet, so you can't set up divisions.")
            if num_games == 0:
                response.writeln("You can define the list of players on the <a href=\"tourneysetup.py?tourney=%s\">Tourney Setup</a> page." % (urllib.parse.quote_plus(tourney.get_name())))

            response.writeln("</p>")
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

            response.writeln("<h2>Summary</h2>")
            response.writeln("<table class=\"misctable\">")
            response.writeln("<tr><th rowspan=\"2\">Division</th><th colspan=\"2\">Players</th><th rowspan=\"2\"></th></tr>")
            response.writeln("<tr><th>Active</th><th>Withdrawn</th></tr>")

            div_active_player_count = [ len([p for p in div_players[div_index] if not p.is_withdrawn()]) for div_index in range(num_divisions) ]
            div_withdrawn_player_count = [ len([p for p in div_players[div_index] if p.is_withdrawn()]) for div_index in range(num_divisions) ]

            for div_index in range(num_divisions):
                div_name = tourney.get_division_name(div_index)
                response.writeln("<tr>")
                response.writeln("<td class=\"text\">%s</td>" % (cgicommon.escape(div_name)))
                response.writeln("<td class=\"number\">%d</td>" % (div_active_player_count[div_index]))
                response.writeln("<td class=\"number\">%d</td>" % (div_withdrawn_player_count[div_index]))
                response.writeln("<td class=\"control\" style=\"text-align: left\">")
                response.writeln("<div class=\"divrenamecontrols\" id=\"divrenamecontrols%d\">" % (div_index))
                response.writeln("<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.parse.quote_plus(tourneyname)))
                response.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourneyname, True)))
                response.writeln("<input type=\"text\" id=\"newdivnameinput%d\" name=\"newdivname%d\" value=\"%s\" />" % (div_index, div_index, cgicommon.escape(div_name, True)))
                response.writeln("<input type=\"submit\" name=\"setdivname%d\" value=\"Save\" />" % (div_index))
                response.writeln("<input type=\"button\" name=\"canceldivrename%d\" value=\"Cancel\" onclick=\"hide_div_rename(%d);\" />" % (div_index, div_index))
                response.writeln("</form>")
                response.writeln("</div>")
                response.writeln("<div class=\"divrenamebutton\" id=\"divrenamebutton%d\">" % (div_index))
                response.writeln("<input type=\"button\" name=\"showdivrename%d\" value=\"Rename\" onclick=\"show_div_rename(%d);\" />" % (div_index, div_index))
                response.writeln("</div>")
                response.writeln("</td></tr>")
            response.writeln("</table>")

            response.writeln("<hr />")

            response.writeln("<h2>Division assignment by rating or standings position</h2>")
            response.writeln("<p><strong>N.B.</strong> To change the division assignment of an individual player, use the <a href=\"/cgi-bin/player.py?tourney=%s\">Player Setup</a> page. The form below will overwrite, and lose, any previous assignments of players to divisions, whether made from this page or in Player Setup.</p>" % (urllib.parse.quote_plus(tourneyname)))
            if num_games > 0:
                cgicommon.show_warning_box(response, "The tourney has already started. Reassigning player divisions will only take effect for rounds whose fixtures have yet to be generated. Existing games will not be changed.")
            response.writeln("<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.parse.quote_plus(tourneyname)))
            response.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourneyname)))

            # Show a table for each division, containing its players
            response.writeln("<p>Players may be manually assigned to the top division by ticking the boxes below before distributing. Any players manually promoted in this way will <em>replace</em> that many non-ticked players in the top division. If you want the top-rated players to remain in the top division along with the manually-promoted players, and have a larger top division, tick the promote box on all the players in the top division before distributing.</p>")
            player_seq = 0
            for div_index in range(0, num_divisions):
                div_name = tourney.get_division_name(div_index)
                response.writeln("<h3>%s</h3>" % (cgicommon.escape(div_name)))
                response.writeln("<table class=\"misctable\">")
                response.writeln("<tr>")
                response.writeln("<th rowspan=\"2\">Name</th>")
                response.writeln("<th rowspan=\"2\">Rating</th>")
                response.writeln("<th colspan=\"2\">Position</th>")
                response.writeln("<th rowspan=\"2\">Promote to top division</th>")
                response.writeln("</tr>")
                response.writeln("<tr>")
                response.writeln("<th>Division</th><th>Overall</th>")
                response.writeln("</tr>")
                for p in div_players[div_index]:
                    response.writeln("<tr>")
                    response.writeln("<td class=\"text\">%s%s</td>" % (cgicommon.player_to_link(p, tourney.get_name()), " (withdrawn)" if p.is_withdrawn() else ""))
                    response.writeln("<td class=\"number\">%g</td>" % (p.get_rating()))
                    response.writeln("<td class=\"number\">%d</td>" % (name_to_div_position[p.get_name()]))
                    response.writeln("<td class=\"number\">%d</td>" % (name_to_position[p.get_name()]))
                    response.writeln("<td class=\"control\"><input type=\"checkbox\" name=\"promote%d\" value=\"1\" %s />" % (
                            player_seq, "checked" if p.is_division_fixed() else ""))
                    response.writeln("<input type=\"hidden\" name=\"promotename%d\" value=\"%s\" />" % (player_seq, cgicommon.escape(p.get_name(), True)))
                    response.writeln("</tr>")
                    player_seq += 1
                response.writeln("</table>")

            response.writeln("<h3>Assign divisions</h3>")
            response.writeln("<p>")
            response.writeln("Number of divisions: <input type=\"number\" min=\"1\" name=\"numdivisions\" value=\"%d\" />" % (num_divisions))
            response.writeln("</p><p>")
            response.writeln("When assigning divisions, ensure the number of active players in a division is a multiple of ")
            response.writeln("<input type=\"number\" name=\"divsizemultiple\" min=\"1\" value=\"%d\" />" % (division_size_multiple))
            response.writeln("</p>")

            response.writeln("<p>")
            response.writeln("<label for=\"divsortrating\"><input type=\"radio\" name=\"divsort\" value=\"ratings\" id=\"divsortrating\" %s /> Assign divisions by rating</label>" % ("checked" if div_sort == "ratings" else ""))
            response.writeln("<br />")
            response.writeln("<label for=\"divsortpos\"><input type=\"radio\" name=\"divsort\" value=\"standings\" id=\"divsortpos\" %s /> Assign divisions by standings position</label>" % ("checked" if div_sort == "standings" else ""))
            response.writeln("</p>")

            response.writeln("<p>Players will be distributed into divisions. The divisions will be sized as equally as possible subject to the constraints above. If the divisions cannot be equally-sized, higher divisions will be given more players.</p>")
            response.writeln("<p>")
            response.writeln("<input type=\"submit\" name=\"setdivs\" value=\"Distribute players into divisions\" />")
            response.writeln("</p>")

            response.writeln("</form>")

    response.writeln("</div>")
    response.writeln("</body>")

    response.writeln("</html>")
