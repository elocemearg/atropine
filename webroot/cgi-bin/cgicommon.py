#!/usr/bin/python

import sys;
import os;
import cgi;
import urllib;
import sqlite3;

dbdir = os.path.join("..", "tourneys");
globaldbfile = os.path.join("..", "prefs.db");

def int_or_none(s):
    try:
        i = int(s)
        return i
    except:
        return None

def print_html_head(title, cssfile="style.css"):
    #print """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
#<html xmlns="http://www.w3.org/1999/xhtml" lang="en-GB" xml:lang="en-GB">
#""";
    print "<!DOCTYPE html>"
    print "<html>"
    print "<head>";
    print "<title>%s</title>" % (cgi.escape(title));
    print "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />";
    print "<link rel=\"stylesheet\" type=\"text/css\" href=\"/%s\" />" % (cgi.escape(cssfile, True));
    print "<link rel=\"shortcut icon\" href=\"/favicon.ico\" type=\"image/x-icon\" />"
    print "<link rel=\"shortcut icon\" href=\"/favicon.png\" type=\"image/png\" />"
    print "</head>";

def print_html_head_local(title):
    print "<!DOCTYPE html>"
    print "<head>"
    print "<title>%s</title>" % (cgi.escape(title))
    print "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />"
    print "<style>"

    # Current directory should already be webroot
    try:
        f = open("style.css")
        for line in f:
            sys.stdout.write(line)
        f.close()
    except IOError:
        print "<!-- Failed to load style.css -->"
        pass

    print "</style>"
    print "</head>"

def show_tourney_exception(exc):
    print "<div class=\"tourneyexception\">"
    print "<div class=\"tourneyexceptionimage\">"
    print "<img src=\"/images/facepalm.png\" alt=\"Facepalm\" />"
    print "</div>"
    print "<div class=\"tourneyexceptionmessagecontainer\">"
    print "<div class=\"tourneyexceptionmessage\">"
    print cgi.escape(exc.description)
    print "</div>"
    print "</div>"
    print "</div>"

def show_warning_box(html):
    print "<div class=\"warningbox\">"
    print "<div class=\"warningboximage\">"
    print "<img src=\"/images/warning.png\" alt=\"Warning\" />"
    print "</div>"
    print "<div class=\"warningboxmessagecontainer\">"
    print "<div class=\"warningboxmessage\">"
    print html
    print "</div>"
    print "</div>"
    print "</div>"

def show_info_box(html):
    print("<div class=\"infoboxcontainer\">")
    print("<div class=\"infoboximage\">")
    print("<img src=\"/images/info.png\" alt=\"Info\" />")
    print("</div>")
    print("<div class=\"infoboxmessagecontainer\">")
    print("<div class=\"infoboxmessage\">")
    print(html)
    print("</div>")
    print("</div>")
    print("</div>")

def set_module_path():
    generator_dir = os.environ.get("GENERATORPATH", ".");
    code_dir = os.environ.get("CODEPATH", os.path.join("..", "..", "py"));
    sys.path.append(generator_dir);
    sys.path.append(code_dir);


def show_sidebar(tourney):
    new_window_html = "<img src=\"/images/opensinnewwindow.png\" alt=\"Opens in new window\" title=\"Opens in new window\" />"
    print "<div class=\"sidebar\">";

    print "<a href=\"/cgi-bin/home.py\"><img src=\"/images/robin128.png\" alt=\"Robin\" /></a><br />";
    if tourney:
        print "<p><strong>%s</strong></p>" % cgi.escape(tourney.name);
        print("<a href=\"/cgi-bin/tourneysetup.py?tourney=%s\"><strong>General Setup</strong></a>" % urllib.quote_plus(tourney.name));
        print "<div class=\"sidebarlinklist\">"
        print("<div>")
        print("<a href=\"/cgi-bin/player.py?tourney=%s\">Players...</a>" % (urllib.quote_plus(tourney.name)))
        print("</div>")
        print("<div>")
        print("<a href=\"/cgi-bin/divsetup.py?tourney=%s\">Divisions...</a>" % (urllib.quote_plus(tourney.name)))
        print("</div>")
        print("<div>")
        print("<a href=\"/cgi-bin/teamsetup.py?tourney=%s\">Teams...</a>" % (urllib.quote_plus(tourney.name)))
        print("</div>")
        print "</div>"

        print("<br />")

        rounds = tourney.get_rounds();
        current_round = tourney.get_current_round()
        if rounds:
            if current_round:
                print("<div><a href=\"/cgi-bin/games.py?tourney=%s&amp;round=%s\"><strong>Results entry</strong></a></div>" % (urllib.quote_plus(tourney.name), urllib.quote_plus(str(current_round["num"]))))
            else:
                print("<div><strong>Games</strong></div>")
        print("<div class=\"roundlinks\">")
        for r in rounds:
            round_no = r["num"];
            round_name = r.get("name", None);
            if not round_name:
                round_name = "Round " + str(round_no);

            print "<div class=\"roundlink\">";
            print "<a href=\"/cgi-bin/games.py?tourney=%s&amp;round=%s\">%s</a>" % (urllib.quote_plus(tourney.name), urllib.quote_plus(str(round_no)), cgi.escape(round_name));
            print "</div>";
        print("</div>")
        print "<br />";
        print "<div class=\"genroundlink\">";
        print "<a href=\"/cgi-bin/fixturegen.py?tourney=%s\">Generate fixtures...</a>" % (urllib.quote_plus(tourney.name));
        print "</div>";

        print "<br />"

        print "<div>"
        print("<a href=\"/cgi-bin/displayoptions.py?tourney=%s\">Display options...</a>" % urllib.quote_plus(tourney.name));
        print "</div>"
        print("<div style=\"padding: 5px 5px 5px 0px;\">")
        print("<a href=\"/cgi-bin/display.py?tourney=%s\" style=\"background-color: #88ccff; padding: 5px; border-radius: 5px;\" target=\"_blank\"><strong>Open Display %s</strong></a>" % (urllib.quote_plus(tourney.name), new_window_html));
        print "</div>"

        banner_text = tourney.get_banner_text()
        if banner_text:
            print("<a href=\"/cgi-bin/displayoptions.py?tourney=%s\">" % (urllib.quote_plus(tourney.name)))
            #print("<div class=\"sidebarbannerheading\">")
            #print("BANNER ENABLED");
            #print("</div>")
            print("<div class=\"sidebarbanner\" title=\"Banner is active\">")
            print(cgi.escape(banner_text))
            print("</div>")
            print("</a>")

        print "<br />"
        print("<div class=\"misclinks\">")
        print("<a href=\"/cgi-bin/tableindex.py?tourney=%s\">Name-to-table index</a>" % (urllib.quote_plus(tourney.name)))
        print("<br />")

        print "<a href=\"/cgi-bin/standings.py?tourney=%s\">Standings</a>" % (urllib.quote_plus(tourney.name));
        print "<br />"
        print "<a href=\"/cgi-bin/tuffluck.py?tourney=%s\">Tuff Luck</a>" % (urllib.quote_plus(tourney.name))
        print "<br />"
        print "<a href=\"/cgi-bin/overachievers.py?tourney=%s\">Overachievers</a>" % (urllib.quote_plus(tourney.name))
        print "</div>"

        print "<br />"

        print "Tournament report"
        print "<div class=\"sidebarlinklist\">"
        print "<div class=\"exportlink\">"
        print "<a href=\"/cgi-bin/export.py?tourney=%s&format=html\" target=\"_blank\">HTML %s</a>" % (urllib.quote_plus(tourney.name), new_window_html)
        print "</div>"
        print "<div class=\"exportlink\">"
        print "<a href=\"/cgi-bin/export.py?tourney=%s&format=text\" target=\"_blank\">Text %s</a>" % (urllib.quote_plus(tourney.name), new_window_html)
        print "</div>"
        print "<div class=\"exportlink\">"
        print "<a href=\"/cgi-bin/export.py?tourney=%s&format=wikitext\" target=\"_blank\">Wikitext %s</a>" % (urllib.quote_plus(tourney.name), new_window_html)
        print "</div>"
        print "</div>"
    print "<br />"
    print "<div class=\"globalprefslink\">"
    print "<a href=\"/cgi-bin/preferences.py\" target=\"_blank\" "
    print "onclick=\"window.open('/cgi-bin/preferences.py', 'newwindow', 'width=450,height=500'); return false;\" >Preferences... " + new_window_html + "</a>"
    print "</div>"
    print "</div>";

def make_team_dot_html(team):
    if team:
        team_string = '<font color="#%s">&bull;</font>' % team.get_hex_colour()
    else:
        team_string = ""
    return team_string

def make_player_dot_html(player):
    return make_team_dot_html(player.get_team())

def show_team_score_table(team_scores):
    print "<table class=\"teamscorestable\">"
    print '<th colspan="2">Team score</th>'
    for (team, score) in team_scores:
        print '<tr>'
        print '<td class="teamscorestablename">%s %s</td>' % (make_team_dot_html(team), cgi.escape(team.get_name()))
        print '<td class="teamscorestablescore">%d</td>' % score
        print '</tr>'
    print '</table>'

def show_games_as_html_table(games, editable=True, remarks=None, include_round_column=False, round_namer=None, player_to_link=None, remarks_heading=""):
    if remarks is None:
        remarks = dict()
     
    if round_namer is None:
        round_namer = lambda x : ("Round %d" % (x))

    if player_to_link is None:
        player_to_link = lambda x : cgi.escape(x.get_name())

    print "<table class=\"scorestable\">";
    print "<tr>";
    if include_round_column:
        print "<th>Round</th>"
    print "<th>Table</th><th>Type</th>";
    print "<th>Player 1</th><th>Score</th><th>Player 2</th><th>%s</th>" % (cgi.escape(remarks_heading));
    print "</tr>"
    last_table_no = None;
    last_round_no = None
    game_seq = 0
    for g in games:
        player_html_strings = (player_to_link(g.p1), player_to_link(g.p2));
        tr_classes = ["gamerow"];

        if last_round_no is None or last_round_no != g.round_no or last_table_no is None or last_table_no != g.table_no:
            tr_classes.append("firstgameintable");
            # Count how many consecutive games appear with this table
            # number, so we can group them together in the table.
            num_games_on_table = 0;
            while game_seq + num_games_on_table < len(games) and games[game_seq + num_games_on_table].table_no == g.table_no and games[game_seq + num_games_on_table].round_no == g.round_no:
                num_games_on_table += 1;
            first_game_in_table = True;
        else:
            first_game_in_table = False;

        if last_round_no is None or last_round_no != g.round_no:
            tr_classes.append("firstgameinround")
            num_games_in_round = 0
            while game_seq + num_games_in_round < len(games) and games[game_seq + num_games_in_round].round_no == g.round_no:
                num_games_in_round += 1
            first_game_in_round = True
        else:
            first_game_in_round = False
        
        if g.is_complete():
            tr_classes.append("completedgame");
        else:
            tr_classes.append("unplayedgame");

        print "<tr class=\"%s\">" % " ".join(tr_classes);
        if first_game_in_round and include_round_column:
            print "<td class=\"roundno\" rowspan=\"%d\">%s</td>" % (num_games_in_round, round_namer(g.round_no))
        if first_game_in_table:
            print "<td class=\"tableno\" rowspan=\"%d\">%d</td>" % (num_games_on_table, g.table_no);
        print "<td class=\"gametype\">%s</td>" % cgi.escape(g.game_type);

        p1_classes = ["gameplayer1"];
        p2_classes = ["gameplayer2"];
        if g.is_complete():
            if g.is_double_loss():
                p1_classes.append("losingplayer")
                p2_classes.append("losingplayer")
            elif g.s1 == g.s2:
                p1_classes.append("drawingplayer");
                p2_classes.append("drawingplayer");
            elif g.s1 > g.s2:
                p1_classes.append("winningplayer");
                p2_classes.append("losingplayer");
            elif g.s2 > g.s1:
                p1_classes.append("losingplayer");
                p2_classes.append("winningplayer");
        
        team_string = make_player_dot_html(g.p1)

        print "<td class=\"%s\" align=\"right\">%s %s</td>" % (" ".join(p1_classes), player_html_strings[0], team_string);
        if g.is_double_loss():
            edit_box_score = "0 - 0*"
            html_score = "&#10006; - &#10006;"
        else:
            edit_box_score = g.format_score()
            html_score = cgi.escape(g.format_score())

        print "<td class=\"gamescore\" align=\"center\">";

        if g.are_players_known():
            if editable:
                print """
<input class="gamescore" id="gamescore_%d_%d" type="text" size="10"
name="gamescore_%d_%d" value="%s"
onchange="score_modified('gamescore_%d_%d');" />""" % (g.round_no, g.seq, g.round_no, g.seq, cgi.escape(edit_box_score, True), g.round_no, g.seq);
            else:
                print html_score;

        print "</td>";
        team_string = make_player_dot_html(g.p2)
        print "<td class=\"%s\" align=\"left\">%s %s</td>" % (" ".join(p2_classes), team_string, player_html_strings[1]);
        print "<td class=\"gameremarks\">%s</td>" % cgi.escape(remarks.get((g.round_no, g.seq), ""));
        print "</tr>";
        last_round_no = g.round_no
        last_table_no = g.table_no;
        game_seq += 1
    
    print "</table>";

def show_standings_table(tourney, show_draws_column, show_points_column, show_spread_column, show_first_second_column=False, linkify_players=False, show_tournament_rating_column=False):
    num_divisions = tourney.get_num_divisions()
    ranking_by_wins = tourney.is_ranking_by_wins()

    if linkify_players:
        linkfn = lambda x : player_to_link(x, tourney.get_name())
    else:
        linkfn = lambda x : cgi.escape(x.get_name())

    print "<table class=\"standingstable\">";
    for div_index in range(num_divisions):
        standings = tourney.get_standings(div_index)
        if num_divisions > 1:
            div_string = tourney.get_division_name(div_index)
        else:
            div_string = ""
        if div_index > 0:
            print "<tr class=\"standingstabledivspacer\"><td></td></tr>"
        print "<tr><th colspan=\"2\">%s</th><th>Played</th><th>Wins</th>%s%s%s%s%s</tr>" % (
                cgi.escape(div_string),
                "<th>Draws</th>" if show_draws_column else "",
                "<th>Points</th>" if show_points_column else "",
                "<th>Spread</th>" if show_spread_column else "",
                "<th>1st/2nd</th>" if show_first_second_column else "",
                "<th>Tournament Rating</th>" if show_tournament_rating_column else "");
        last_wins_inc_draws = None;
        tr_bgcolours = ["#ffdd66", "#ffff88" ];
        bgcolour_index = 0;
        for s in standings:
            (pos, name, played, wins, points, draws, spread, num_first) = s[0:8];
            tournament_rating = s.tournament_rating
            player = tourney.get_player_from_name(name)
            if ranking_by_wins:
                if last_wins_inc_draws is None:
                    bgcolour_index = 0;
                elif last_wins_inc_draws != wins + 0.5 * draws:
                    bgcolour_index = (bgcolour_index + 1) % 2;
                last_wins_inc_draws = wins + 0.5 * draws;

                if player.is_withdrawn():
                    bgcolour = "#cccccc"
                else:
                    bgcolour = tr_bgcolours[bgcolour_index]
            else:
                if player.is_withdrawn():
                    bgcolour = "#cccccc"
                else:
                    bgcolour = "#ffdd66"

            print "<tr class=\"standingsrow\" style=\"background-color: %s\">" % (bgcolour);

            bold_style = "style=\"font-weight: bold;\""
            if ranking_by_wins:
                wins_style = bold_style
                draws_style = bold_style
            else:
                wins_style = ""
                draws_style = ""
            if tourney.is_ranking_by_points():
                points_style = bold_style
            else:
                points_style = ""
            if tourney.is_ranking_by_spread():
                spread_style = bold_style
            else:
                spread_style = ""
            print "<td class=\"standingspos\">%d</td>" % pos;
            print "<td class=\"standingsname\">%s</td>" % (linkfn(player));
            print "<td class=\"standingsplayed\">%d</td>" % played;
            print "<td class=\"standingswins\" %s >%d</td>" % (wins_style, wins);
            if show_draws_column:
                print "<td class=\"standingsdraws\" %s >%d</td>" % (draws_style, draws);
            if show_points_column:
                print "<td class=\"standingspoints\" %s >%d</td>" % (points_style, points);
            if show_spread_column:
                print "<td class=\"standingsspread\" %s >%+d</td>" % (spread_style, spread);
            if show_first_second_column:
                print "<td class=\"standingsfirstsecond\">%d/%d</td>" % (num_first, played - num_first)
            if show_tournament_rating_column:
                print "<td class=\"standingstournamentrating\">"
                if tournament_rating is not None:
                    print "%.2f" % (tournament_rating)
                print "</td>"
            print "</tr>";
    print "</table>";

def player_to_link(player, tourney_name, emboldenise=False, disable_tab_order=False, open_in_new_window=False, custom_text=None):
    return "<a class=\"playerlink%s\" href=\"player.py?tourney=%s&id=%d\" %s%s>%s</a>" % (
            " thisplayerlink" if emboldenise else "",
            urllib.quote_plus(tourney_name), player.get_id(),
            "tabindex=\"-1\" " if disable_tab_order else "",
            "target=\"_blank\"" if open_in_new_window else "",
            cgi.escape(custom_text) if custom_text is not None else cgi.escape(player.get_name())
    )

def ordinal_number(n):
    if (n / 10) % 10 == 1:
        return "%dth" % (n)
    elif n % 10 == 1:
        return "%dst" % (n)
    elif n % 10 == 2:
        return "%dnd" % (n)
    elif n % 10 == 3:
        return "%drd" % (n)
    else:
        return "%dth" % (n)

class GlobalPreferences(object):
    def __init__(self, names_values):
        self.mapping = names_values.copy()

    def get_result_entry_tab_order(self):
        return self.mapping.get("resultsentrytaborder", "nnss")

    def set_result_entry_tab_order(self, value):
        self.mapping["resultsentrytaborder"] = value

    def get_map(self):
        return self.mapping.copy()

def get_global_preferences():
    db = sqlite3.connect(globaldbfile)
    
    cur = db.cursor()
    cur.execute("create table if not exists prefs(name text, value text)")
    cur.execute("select name, value from prefs")
    prefs = dict()
    for row in cur:
        prefs[row[0]] = row[1]
    cur.close()

    db.close()

    return GlobalPreferences(prefs)

def set_global_preferences(prefs):
    db = sqlite3.connect(globaldbfile)
    db.execute("delete from prefs")
    
    rows_to_insert = []
    
    mapping = prefs.get_map()
    for name in mapping:
        rows_to_insert.append((name, mapping[name]))

    db.executemany("insert into prefs values (?, ?)", rows_to_insert)

    db.commit()

    db.close()
