#!/usr/bin/python3

import sys;
import cgicommon;
import urllib.request, urllib.parse, urllib.error;
import cgi;
import cgitb;
import os;
import re;

def show_player_selection(players, control_name, value):
    print("<select name=\"%s\">" % cgi.escape(control_name, True));
    for p in players:
        player_name = p.get_name();
        if player_name == value:
            sel = " selected";
        else:
            sel = "";
        print("<option value=\"%s\"%s>%s</option>" % (cgi.escape(player_name, True), sel, cgi.escape(player_name)));
    print("</select>");

def lookup_player(players, name):
    for p in players:
        if p.get_name() == name:
            return p;
    raise countdowntourney.PlayerDoesNotExistException("Player \"%s\": I've never heard of them." % name);

cgitb.enable();

print("Content-Type: text/html; charset=utf-8");
print("");

baseurl = "/cgi-bin/fixtureedit.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");
round_no = form.getfirst("round");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

import countdowntourney;

cgicommon.print_html_head("Edit fixtures: " + str(tourney_name));

print("<body>");

cgicommon.assert_client_from_localhost()

if not tourney_name:
    print("<h1>No tourney specified</h1>");
    print("<p><a href=\"/cgi-bin/home.py\">Home</a></p>");
    print("</body></html>");
    sys.exit(0);

if not round_no:
    print("<h1>No round number specified</h1>");
    print("<p><a href=\"/cgi-bin/home.py\">Home</a></p>");
    print("</body></html>");
    sys.exit(0);

try:
    round_no = int(round_no);
except ValueError:
    print("<h1>Round number is not a number</h1>");
    print("<p><a href=\"/cgi-bin/home.py\">Home</a></p>");
    print("</body></html>");
    sys.exit(0);

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

    cgicommon.show_sidebar(tourney);

    print("<div class=\"mainpane\">");

    round_name = tourney.get_round_name(round_no);
    print("<h1>Fixture editor: %s</h1>" % round_name);

    # Javascript function to tick/untick all heat game boxes for a division
    print("""
<script type="text/javascript">
//<![CDATA[
// Set all drop-down boxes in this division to have the value of the first one
function div_type_select(div) {
    var idStub = "div" + div.toString() + "_gametype_";

    var dropDown = document.getElementById(idStub + "0");

    if (dropDown) {
        var selectedValue = null;
        for (var i = 0; i < dropDown.options.length; ++i) {
            if (dropDown.options[i].selected) {
                selectedValue = dropDown.options[i].text;
                break;
            }
        }
        if (selectedValue) {
            var otherDropDown;
            var num = 0;
            do {
                ++num;
                otherDropDown = document.getElementById(idStub + num.toString());
                if (otherDropDown) {
                    for (var i = 0; i < otherDropDown.options.length; ++i) {
                        if (otherDropDown.options[i].text == selectedValue) {
                            otherDropDown.options[i].selected = true;
                        }
                        else {
                            otherDropDown.options[i].selected = false;
                        }
                    }
                }
            } while (otherDropDown);
        }
    }
}
//]]>
</script>
""")
    players = sorted(tourney.get_players(), key=lambda x : x.get_name());

    remarks = dict();

    num_divisions = tourney.get_num_divisions()

    num_games_updated = None;
    num_games_deleted = 0
    if "save" in form:
        games = tourney.get_games(round_no=round_no);
        alterations = [];
        for g in games:
            seq = g.seq;
            set1 = form.getfirst("gamep1_%d_%d" % (g.round_no, g.seq));
            set2 = form.getfirst("gamep2_%d_%d" % (g.round_no, g.seq));
            set_type = form.getfirst("gametype_%d_%d" % (g.round_no, g.seq))
            #set_heat = form.getfirst("gameheat_%d_%d" % (g.round_no, g.seq))

            new_p1 = lookup_player(players, set1);
            new_p2 = lookup_player(players, set2);
            if not set_type:
                new_game_type = "P"
            else:
                new_game_type = set_type

            if new_p1 == new_p2:
                remarks[(g.round_no, g.seq)] = "Not updated (%s v %s): players can't play themselves" % (new_p1.get_name(), new_p2.get_name());
            elif g.p1 != new_p1 or g.p2 != new_p2 or g.game_type != new_game_type:
                alterations.append((round_no, seq, new_p1, new_p2, new_game_type));

        if alterations:
            num_games_updated = tourney.alter_games(alterations);

        for (round_no, seq, new_p1, new_p2, new_game_type) in alterations:
            remarks[seq] = "Updated";

        for div in range(num_divisions):
            if form.getfirst("deldiv%d" % (div)) == "1":
                num_games_deleted += tourney.delete_round_div(round_no, div)

    print("<p>")
    print("<a href=\"/cgi-bin/games.py?tourney=%s&amp;round=%d\">Back to the score editor</a>" % (urllib.parse.quote_plus(tourney_name), round_no));
    print("</p>")

    if num_games_updated:
        print("<p>%d games updated.</p>" % (num_games_updated));
    if num_games_deleted:
        print("<p>%d games deleted.</p>" % (num_games_deleted))

    game_types = countdowntourney.get_game_types()

    print("<div class=\"scorestable\">");
    print("<form method=\"POST\" action=\"%s?tourney=%s&amp;round=%d\">" % (baseurl, urllib.parse.quote_plus(tourney_name), round_no));
    print("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % cgi.escape(tourney_name, True));
    print("<input type=\"hidden\" name=\"round\" value=\"%d\" />" % round_no);
    for div_index in range(num_divisions):
        games = tourney.get_games(round_no=round_no, division=div_index);

        if num_divisions > 1:
            print("<h2>%s</h2>" % (tourney.get_division_name(div_index)))
        print("<p><input type=\"checkbox\" name=\"deldiv%d\" value=\"1\" /> Delete all games in %s, %s</p>" % (div_index, cgi.escape(tourney.get_division_name(div_index)), tourney.get_round_name(round_no)))
        print("<table class=\"scorestable\">");
        print("<tr>");
        print("<th colspan=\"5\"></th>")
        print("<th>Game type</th>")
        print("</tr>")
        print("<th>Table</th><th></th>");
        print("<th>Player 1</th><th>Score</th><th>Player 2</th>")
        print("<th>")
        print("<input type=\"button\" name=\"div%d_set_all\" value=\"Set all to match first game\" onclick=\"div_type_select(%d);\" />" % (div_index, div_index))
        print("</th>")
        print("<th></th></tr>");

        gamenum = 0;
        last_table_no = None;
        for g in games:
            game_player_names = g.get_player_names();
            tr_classes = ["gamerow"];

            if last_table_no is None or last_table_no != g.table_no:
                tr_classes.append("firstgameintable");
                # Count how many consecutive games appear with this table
                # number, so we can group them together in the table.
                num_games_on_table = 0;
                while gamenum + num_games_on_table < len(games) and games[gamenum + num_games_on_table].table_no == g.table_no:
                    num_games_on_table += 1;
                first_game_in_table = True;
            else:
                first_game_in_table = False;

            print("<tr class=\"%s\">" % " ".join(tr_classes));
            if first_game_in_table:
                print("<td class=\"tableno\" rowspan=\"%d\">%d</td>" % (num_games_on_table, g.table_no));
            print("<td class=\"gameseq\">%d</td>" % g.seq);
            #print "<td class=\"gametype\">%s</td>" % cgi.escape(g.game_type);

            print("<td class=\"gameplayer1\" align=\"right\">")
            show_player_selection(players, "gamep1_%d_%d" % (g.round_no, g.seq), game_player_names[0]);
            print("</td>");

            if g.is_complete():
                score_str = g.format_score();
            else:
                score_str = "-";
            print("<td class=\"gamescore\" align=\"center\">%s</td>" % cgi.escape(score_str));

            print("<td class=\"gameplayer2\" align=\"right\">")
            show_player_selection(players, "gamep2_%d_%d" % (g.round_no, g.seq), game_player_names[1]);
            print("</td>");

            print("<td class=\"gameheat\">")
            print("<select name=\"%s\" id=\"%s\">" % (
                    "gametype_%d_%d" % (g.round_no, g.seq),
                    "div%d_gametype_%d" % (div_index, gamenum)
            ))
            for game_type in game_types:
                print("<option value=\"%s\" %s >%s (%s)</option>" % (
                        cgi.escape(game_type["code"], True),
                        "selected" if g.game_type == game_type["code"] else "",
                        cgi.escape(game_type["name"]),
                        cgi.escape(game_type["code"])
                ))
            print("</select>")
            #print "<input type=\"checkbox\" class=\"heatcheckbox_div%d\" name=\"gameheat_%d_%d\" value=\"1\" %s />" % (div_index, g.round_no, g.seq, "checked" if g.game_type == "P" else "")
            print("</td>")
            
            print("<td class=\"remarks\">");
            print(cgi.escape(remarks.get((g.round_no, g.seq), "")));
            print("</td>");
            print("</tr>");
            gamenum += 1;
            last_table_no = g.table_no;
        print("</table>");

    print("<p>")
    print("<input type=\"submit\" name=\"save\" value=\"Save\" />");
    print("</p>")
    print("</form>");

    print("</div>"); # scorestable

    print("</div>"); # mainpane

except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);

print("</body>");
print("</html>");

sys.exit(0);
