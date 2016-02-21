#!/usr/bin/python

import sys;
import cgicommon;
import urllib;
import cgi;
import cgitb;
import os;
import re;

def show_player_selection(players, control_name, value):
    print "<select name=\"%s\">" % cgi.escape(control_name, True);
    for p in players:
        player_name = p.get_name();
        if player_name == value:
            sel = " selected";
        else:
            sel = "";
        print "<option value=\"%s\"%s>%s</option>" % (cgi.escape(player_name, True), sel, cgi.escape(player_name));
    print "</select>";

def lookup_player(players, name):
    for p in players:
        if p.get_name() == name:
            return p;
    raise countdowntourney.PlayerDoesNotExistException("Player \"%s\": I've never heard of them." % name);

cgitb.enable();

print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/fixtureedit.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");
round_no = form.getfirst("round");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

import countdowntourney;

cgicommon.print_html_head("Edit fixtures: " + str(tourney_name));

print "<body>";

if not tourney_name:
    print "<h1>No tourney specified</h1>";
    print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>";
    print "</body></html>";
    sys.exit(0);

if not round_no:
    print "<h1>No round number specified</h1>";
    print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>";
    print "</body></html>";
    sys.exit(0);

try:
    round_no = int(round_no);
except ValueError:
    print "<h1>Round number is not a number</h1>";
    print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>";
    print "</body></html>";
    sys.exit(0);

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

    cgicommon.show_sidebar(tourney);

    print "<div class=\"mainpane\">";

    round_name = tourney.get_round_name(round_no);
    print "<h1>Fixture editor: %s</h1>" % round_name;

    players = sorted(tourney.get_players(), key=lambda x : x.get_name());

    remarks = dict();

    num_games_updated = None;
    if "save" in form:
        games = tourney.get_games(round_no=round_no);
        alterations = [];
        for g in games:
            seq = g.seq;
            set1 = form.getfirst("gamep1_%d_%d" % (g.round_no, g.seq));
            set2 = form.getfirst("gamep2_%d_%d" % (g.round_no, g.seq));
            new_p1 = lookup_player(players, set1);
            new_p2 = lookup_player(players, set2);

            if new_p1 == new_p2:
                remarks[(g.round_no, g.seq)] = "Not updated (%s v %s): players can't play themselves" % (new_p1.get_name(), new_p2.get_name());
            elif g.p1 != new_p1 or g.p2 != new_p2:
                alterations.append((round_no, seq, new_p1, new_p2));

        if alterations:
            num_games_updated = tourney.set_game_players(alterations);

        for (round_no, seq, new_p1, new_p2) in alterations:
            remarks[seq] = "Updated";

    print "<p>"
    print "<a href=\"/cgi-bin/games.py?tourney=%s&amp;round=%d\">Back to the score editor</a>" % (urllib.quote_plus(tourney_name), round_no);
    print "</p>"

    if num_games_updated:
        print "<p>%d games updated.</p>" % num_games_updated;

    num_divisions = tourney.get_num_divisions()

    print "<div class=\"scorestable\">";
    print "<form method=\"POST\" action=\"%s?tourney=%s&amp;round=%d\">" % (baseurl, urllib.quote_plus(tourney_name), round_no);
    print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % cgi.escape(tourney_name, True);
    print "<input type=\"hidden\" name=\"round\" value=\"%d\" />" % round_no;
    for div_index in range(num_divisions):
        games = tourney.get_games(round_no=round_no, division=div_index);

        if num_divisions > 1:
            print "<h2>%s</h2>" % (tourney.get_division_name(div_index))

        print "<table class=\"scorestable\">";
        print "<tr>";
        print "<th>Table</th><th></th><th></th>";
        print "<th>Player 1</th><th>Score</th><th>Player 2</th><th></th></tr>";

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

            print "<tr class=\"%s\">" % " ".join(tr_classes);
            if first_game_in_table:
                print "<td class=\"tableno\" rowspan=\"%d\">%d</td>" % (num_games_on_table, g.table_no);
            print "<td class=\"gameseq\">%d</td>" % g.seq;
            print "<td class=\"gametype\">%s</td>" % cgi.escape(g.game_type);

            print "<td class=\"gameplayer1\" align=\"right\">"
            show_player_selection(players, "gamep1_%d_%d" % (g.round_no, g.seq), game_player_names[0]);
            print "</td>";

            if g.is_complete():
                score_str = g.format_score();
            else:
                score_str = "-";
            print "<td class=\"gamescore\" align=\"center\">%s</td>" % cgi.escape(score_str);

            print "<td class=\"gameplayer2\" align=\"right\">"
            show_player_selection(players, "gamep2_%d_%d" % (g.round_no, g.seq), game_player_names[1]);
            print "</td>";
            
            print "<td class=\"remarks\">";
            print cgi.escape(remarks.get((g.round_no, g.seq), ""));
            print "</td>";
            print "</tr>";
            gamenum += 1;
            last_table_no = g.table_no;
        print "</table>";

    print "<p>"
    print "<input type=\"submit\" name=\"save\" value=\"Save\" />";
    print "</p>"
    print "</form>";

    print "</div>"; # scorestable

    print "</div>"; # mainpane
except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);

print "</body>";
print "</html>";

sys.exit(0);
