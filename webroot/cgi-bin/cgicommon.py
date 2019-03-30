#!/usr/bin/python3

import sys;
import os;
import cgi;
import urllib.request, urllib.parse, urllib.error;
import sqlite3;
import html

dbdir = os.path.join("..", "tourneys");
globaldbfile = os.path.join("..", "prefs.db");

def int_or_none(s):
    try:
        i = int(s)
        return i
    except:
        return None

def writeln(string=""):
    sys.stdout.buffer.write(string.encode("utf-8"))
    sys.stdout.buffer.write(b'\n')

def write(string):
    sys.stdout.buffer.write(string.encode("utf-8"))

def escape(string, quote=True):
    return html.escape(string, quote)

def print_html_head(title, cssfile="style.css", othercssfiles=[]):
    writeln("<!DOCTYPE html>")
    writeln("<html lang=\"en\">")
    writeln("<head>");
    writeln("<title>%s</title>" % (escape(title)));
    writeln("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />");
    writeln("<link rel=\"stylesheet\" type=\"text/css\" href=\"/%s\" />" % (escape(cssfile, True)));
    for f in othercssfiles:
        writeln("<link rel=\"stylesheet\" type=\"text/css\" href=\"/%s\" />" % (escape(f, True)));
    writeln("<link rel=\"shortcut icon\" href=\"/favicon.ico\" type=\"image/x-icon\" />")
    writeln("<link rel=\"shortcut icon\" href=\"/favicon.png\" type=\"image/png\" />")
    writeln("</head>");

def print_html_head_local(title):
    writeln("<!DOCTYPE html>")
    writeln("<html lang=\"en\">")
    writeln("<head>")
    writeln("<title>%s</title>" % (escape(title)))
    writeln("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />")
    writeln("<style>")

    # Current directory should already be webroot
    try:
        f = open("style.css")
        for line in f:
            write(line)
        f.close()
    except IOError:
        writeln("<!-- Failed to load style.css -->")
        pass

    writeln("</style>")
    writeln("</head>")

def show_tourney_exception(exc):
    writeln("<div class=\"tourneyexception\">")
    writeln("<div class=\"tourneyexceptionimage\">")
    writeln("<img src=\"/images/facepalm.png\" alt=\"Facepalm\" />")
    writeln("</div>")
    writeln("<div class=\"tourneyexceptionmessagecontainer\">")
    writeln("<div class=\"tourneyexceptionmessage\">")
    writeln(escape(exc.description))
    writeln("</div>")
    writeln("</div>")
    writeln("</div>")

def show_warning_box(html, wide=False):
    writeln("<div class=\"warningbox%s\">" % (" warningboxwidthlimited" if not wide else ""))
    writeln("<div class=\"warningboximage\">")
    writeln("<img src=\"/images/warning.png\" alt=\"Warning\" />")
    writeln("</div>")
    writeln("<div class=\"warningboxmessagecontainer%s\">" % (" warningboxmessagecontainerwidthlimited" if not wide else ""))
    writeln("<div class=\"warningboxmessage\">")
    writeln(html)
    writeln("</div>")
    writeln("</div>")
    writeln("</div>")

def show_info_box(html):
    writeln("<div class=\"infoboxcontainer\">")
    writeln("<div class=\"infoboximage\">")
    writeln("<img src=\"/images/info.png\" alt=\"Info\" />")
    writeln("</div>")
    writeln("<div class=\"infoboxmessagecontainer\">")
    writeln("<div class=\"infoboxmessage\">")
    writeln(html)
    writeln("</div>")
    writeln("</div>")
    writeln("</div>")

def set_module_path():
    generator_dir = os.environ.get("GENERATORPATH", ".");
    code_dir = os.environ.get("CODEPATH", os.path.join("..", "..", "py"));
    sys.path.append(generator_dir);
    sys.path.append(code_dir);


def show_sidebar(tourney):
    new_window_html = "<img src=\"/images/opensinnewwindow.png\" alt=\"Opens in new window\" title=\"Opens in new window\" />"
    writeln("<div class=\"sidebar\">");

    writeln("<a href=\"/cgi-bin/home.py\"><img src=\"/images/eyebergine128.png\" alt=\"Eyebergine\" /></a><br />");
    if tourney:
        writeln("<p><strong>%s</strong></p>" % escape(tourney.name));
        writeln(("<a href=\"/cgi-bin/tourneysetup.py?tourney=%s\"><strong>General Setup</strong></a>" % urllib.parse.quote_plus(tourney.name)));
        writeln("<div class=\"sidebarlinklist\">")
        writeln("<div>")
        writeln(("<a href=\"/cgi-bin/player.py?tourney=%s\">Players...</a>" % (urllib.parse.quote_plus(tourney.name))))
        writeln("</div>")
        writeln("<div>")
        writeln(("<a href=\"/cgi-bin/divsetup.py?tourney=%s\">Divisions...</a>" % (urllib.parse.quote_plus(tourney.name))))
        writeln("</div>")
        writeln("<div>")
        writeln(("<a href=\"/cgi-bin/teamsetup.py?tourney=%s\">Teams...</a>" % (urllib.parse.quote_plus(tourney.name))))
        writeln("</div>")
        writeln("<div>")
        writeln(("<a href=\"/cgi-bin/tourneysetupadvanced.py?tourney=%s\">Advanced...</a>" % (urllib.parse.quote_plus(tourney.name))))
        writeln("</div>")
        writeln("</div>")

        writeln("<br />")

        writeln("<div>")
        writeln(("<a href=\"/cgi-bin/displayoptions.py?tourney=%s\"><strong>Display Setup</strong></a>" % urllib.parse.quote_plus(tourney.name)));
        writeln("</div>")

        banner_text = tourney.get_banner_text()
        if banner_text:
            writeln(("<a href=\"/cgi-bin/displayoptions.py?tourney=%s\">" % (urllib.parse.quote_plus(tourney.name))))
            writeln("<div class=\"sidebarbanner\" title=\"Banner is active\">")
            writeln((escape(banner_text)))
            writeln("</div>")
            writeln("</a>")

        writeln("<br />")

        rounds = tourney.get_rounds();
        current_round = tourney.get_current_round()
        if rounds:
            if current_round:
                writeln(("<div><a href=\"/cgi-bin/games.py?tourney=%s&amp;round=%s\"><strong>Results entry</strong></a></div>" % (urllib.parse.quote_plus(tourney.name), urllib.parse.quote_plus(str(current_round["num"])))))
            else:
                writeln("<div><strong>Games</strong></div>")
        writeln("<div class=\"roundlinks\">")
        for r in rounds:
            round_no = r["num"];
            round_name = r.get("name", None);
            if not round_name:
                round_name = "Round " + str(round_no);

            writeln("<div class=\"roundlink\">");
            writeln("<a href=\"/cgi-bin/games.py?tourney=%s&amp;round=%s\">%s</a>" % (urllib.parse.quote_plus(tourney.name), urllib.parse.quote_plus(str(round_no)), escape(round_name)));
            writeln("</div>");
        writeln("</div>")
        writeln("<br />");
        writeln("<div class=\"genroundlink\">");
        writeln("<a href=\"/cgi-bin/fixturegen.py?tourney=%s\">Generate fixtures...</a>" % (urllib.parse.quote_plus(tourney.name)));
        writeln("</div>");

        writeln("<br />")
        writeln("<div class=\"misclinks\">")
        writeln(("<a href=\"/cgi-bin/tableindex.py?tourney=%s\">Name-to-table index</a>" % (urllib.parse.quote_plus(tourney.name))))
        writeln("<br />")

        writeln("<a href=\"/cgi-bin/standings.py?tourney=%s\">Standings</a>" % (urllib.parse.quote_plus(tourney.name)));
        writeln("<br />")
        writeln("<a href=\"/cgi-bin/tuffluck.py?tourney=%s\">Tuff Luck</a>" % (urllib.parse.quote_plus(tourney.name)))
        writeln("<br />")
        writeln("<a href=\"/cgi-bin/overachievers.py?tourney=%s\">Overachievers</a>" % (urllib.parse.quote_plus(tourney.name)))
        writeln("<br />")
        writeln("<a href=\"/cgi-bin/timdownaward.py?tourney=%s\">Tim Down Award</a>" % (urllib.parse.quote_plus(tourney.name)))
        writeln("</div>")

        writeln("<br />")

        writeln("Tournament report")
        writeln("<div class=\"sidebarlinklist\">")
        
        writeln("<div class=\"exportlink\">")
        writeln("<a href=\"/cgi-bin/export.py?tourney=%s&format=html\" target=\"_blank\">HTML %s</a>" % (urllib.parse.quote_plus(tourney.name), new_window_html))
        writeln("</div>")
        
        writeln("<div class=\"exportlink\">")
        writeln("<a href=\"/cgi-bin/export.py?tourney=%s&format=text\" target=\"_blank\">Text %s</a>" % (urllib.parse.quote_plus(tourney.name), new_window_html))
        writeln("</div>")

        writeln("<div class=\"exportlink\">")
        writeln("<a href=\"/cgi-bin/export.py?tourney=%s&format=csv\" target=\"_blank\">CSV %s</a>" % (urllib.parse.quote_plus(tourney.name), new_window_html))
        writeln("</div>")

        writeln("<div class=\"exportlink\">")
        writeln("<a href=\"/cgi-bin/export.py?tourney=%s&format=wikitext\" target=\"_blank\">Wikitext %s</a>" % (urllib.parse.quote_plus(tourney.name), new_window_html))
        writeln("</div>")

        writeln("</div>")
    writeln("<br />")
    writeln("<div class=\"globalprefslink\">")
    writeln("<a href=\"/cgi-bin/preferences.py\" target=\"_blank\" ")
    writeln("onclick=\"window.open('/cgi-bin/preferences.py', 'newwindow', 'width=450,height=500'); return false;\" >Preferences... " + new_window_html + "</a>")
    writeln("</div>")

    writeln("<br />")

    writeln("<div class=\"sidebarversioninfo\" title=\"This is the version number of the Atropine installation you're using, and the version which created the database for this tourney.\">");
    writeln("<div class=\"sidebarversionline\">")
    writeln("Atropine version: %s" % (tourney.get_software_version()))
    writeln("</div>")
    writeln("<div class=\"sidebarversionline\">")
    writeln("This tourney version: %s" % (tourney.get_db_version()))
    writeln("</div>")
    writeln("</div>")

    writeln("</div>");

def make_team_dot_html(team):
    if team:
        team_string = '<font color="#%s">&bull;</font>' % team.get_hex_colour()
    else:
        team_string = ""
    return team_string

def make_player_dot_html(player):
    return make_team_dot_html(player.get_team())

def show_team_score_table(team_scores):
    writeln("<table class=\"teamscorestable\">")
    writeln('<th colspan="2">Team score</th>')
    for (team, score) in team_scores:
        writeln('<tr>')
        writeln('<td class="teamscorestablename">%s %s</td>' % (make_team_dot_html(team), escape(team.get_name())))
        writeln('<td class="teamscorestablescore">%d</td>' % score)
        writeln('</tr>')
    writeln('</table>')

def show_games_as_html_table(games, editable=True, remarks=None,
        include_round_column=False, round_namer=None, player_to_link=None,
        remarks_heading="", show_game_type=True, game_onclick_fn=None,
        colour_win_loss=True, score_id_prefix=None, show_heading_row=True):
    if round_namer is None:
        round_namer = lambda x : ("Round %d" % (x))

    if player_to_link is None:
        player_to_link = lambda x : escape(x.get_name())

    writeln("<table class=\"scorestable\">");

    if show_heading_row:
        writeln("<tr>");
        if include_round_column:
            writeln("<th>Round</th>")

        writeln("<th>Table</th>");

        if show_game_type:
            writeln("<th>Type</th>");

        writeln("<th>Player 1</th><th>Score</th><th>Player 2</th>");
        if remarks is not None:
            writeln("<th>%s</th>" % (escape(remarks_heading)));
        writeln("</tr>")

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

        if game_onclick_fn:
            onclick_attr = "onclick=\"" + escape(game_onclick_fn(g.round_no, g.seq)) + "\""
            tr_classes.append("handcursor")
        else:
            onclick_attr = "";
        writeln("<tr class=\"%s\" %s>" % (" ".join(tr_classes), onclick_attr));
        if first_game_in_round and include_round_column:
            writeln("<td class=\"roundno\" rowspan=\"%d\">%s</td>" % (num_games_in_round, round_namer(g.round_no)))
        if first_game_in_table:
            writeln("<td class=\"tableno\" rowspan=\"%d\">%d</td>" % (num_games_on_table, g.table_no));

        if show_game_type:
            writeln("<td class=\"gametype\">%s</td>" % escape(g.game_type));

        p1_classes = ["gameplayer1"];
        p2_classes = ["gameplayer2"];
        if g.is_complete() and colour_win_loss:
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

        writeln("<td class=\"%s\">%s %s</td>" % (" ".join(p1_classes), player_html_strings[0], team_string));
        if g.is_double_loss():
            edit_box_score = "0 - 0*"
            html_score = "&#10006; - &#10006;"
        else:
            edit_box_score = g.format_score()
            html_score = escape(g.format_score())

        if score_id_prefix:
            writeln("<td class=\"gamescore\" id=\"%s_%d_%d\">" % (escape(score_id_prefix), g.round_no, g.seq));
        else:
            writeln("<td class=\"gamescore\">");

        if g.are_players_known():
            if editable:
                writeln("""
<input class="gamescore" id="gamescore_%d_%d" type="text" size="10"
name="gamescore_%d_%d" value="%s"
onchange="score_modified('gamescore_%d_%d');" />""" % (g.round_no, g.seq, g.round_no, g.seq, escape(edit_box_score, True), g.round_no, g.seq));
            else:
                writeln(html_score);

        writeln("</td>");
        team_string = make_player_dot_html(g.p2)
        writeln("<td class=\"%s\">%s %s</td>" % (" ".join(p2_classes), team_string, player_html_strings[1]));
        if remarks is not None:
            writeln("<td class=\"gameremarks\">%s</td>" % escape(remarks.get((g.round_no, g.seq), "")));
        writeln("</tr>");
        last_round_no = g.round_no
        last_table_no = g.table_no;
        game_seq += 1
    
    writeln("</table>");

def show_standings_table(tourney, show_draws_column, show_points_column,
        show_spread_column, show_first_second_column=False,
        linkify_players=False, show_tournament_rating_column=False,
        show_qualified=False):
    num_divisions = tourney.get_num_divisions()
    ranking_by_wins = tourney.is_ranking_by_wins()

    if linkify_players:
        linkfn = lambda x : player_to_link(x, tourney.get_name())
    else:
        linkfn = lambda x : escape(x.get_name())

    writeln("<table class=\"standingstable\">");
    for div_index in range(num_divisions):
        standings = tourney.get_standings(div_index)
        if num_divisions > 1:
            div_string = tourney.get_division_name(div_index)
        else:
            div_string = ""
        if div_index > 0:
            writeln("<tr class=\"standingstabledivspacer\"><td></td></tr>")
        writeln("<tr><th colspan=\"2\">%s</th><th>Played</th><th>Wins</th>%s%s%s%s%s</tr>" % (
                escape(div_string),
                "<th>Draws</th>" if show_draws_column else "",
                "<th>Points</th>" if show_points_column else "",
                "<th>Spread</th>" if show_spread_column else "",
                "<th>1st/2nd</th>" if show_first_second_column else "",
                "<th>Tournament Rating</th>" if show_tournament_rating_column else ""));
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
                elif s.qualified and show_qualified:
                    bgcolour = "#66ff66"
                else:
                    bgcolour = tr_bgcolours[bgcolour_index]
            else:
                if player.is_withdrawn():
                    bgcolour = "#cccccc"
                elif s.qualified and show_qualified:
                    bgcolour = "#66ff66"
                else:
                    bgcolour = "#ffdd66"

            writeln("<tr class=\"standingsrow\" style=\"background-color: %s\">" % (bgcolour));

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
            writeln("<td class=\"standingspos\">%d</td>" % pos);
            writeln("<td class=\"standingsname\">%s</td>" % (linkfn(player)));
            writeln("<td class=\"standingsplayed\">%d</td>" % played);
            writeln("<td class=\"standingswins\" %s >%d</td>" % (wins_style, wins));
            if show_draws_column:
                writeln("<td class=\"standingsdraws\" %s >%d</td>" % (draws_style, draws));
            if show_points_column:
                writeln("<td class=\"standingspoints\" %s >%d</td>" % (points_style, points));
            if show_spread_column:
                writeln("<td class=\"standingsspread\" %s >%+d</td>" % (spread_style, spread));
            if show_first_second_column:
                writeln("<td class=\"standingsfirstsecond\">%d/%d</td>" % (num_first, played - num_first))
            if show_tournament_rating_column:
                writeln("<td class=\"standingstournamentrating\">")
                if tournament_rating is not None:
                    writeln("%.2f" % (tournament_rating))
                writeln("</td>")
            writeln("</tr>");
    writeln("</table>");

def player_to_link(player, tourney_name, emboldenise=False, disable_tab_order=False, open_in_new_window=False, custom_text=None, withdrawn=False):
    return "<a class=\"playerlink%s%s\" href=\"player.py?tourney=%s&id=%d\" %s%s>%s</a>" % (
            "withdrawn" if withdrawn else " ",
            " thisplayerlink" if emboldenise else "",
            urllib.parse.quote_plus(tourney_name), player.get_id(),
            "tabindex=\"-1\" " if disable_tab_order else "",
            "target=\"_blank\"" if open_in_new_window else "",
            escape(custom_text) if custom_text is not None else escape(player.get_name())
    )

def ordinal_number(n):
    if (n // 10) % 10 == 1:
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

def is_client_from_localhost():
    # If the web server is listening only on the loopback interface, then
    # disable this check - instead we'll rely on the fact that we're only
    # listening on that interface.
    if os.environ.get("ATROPINE_LISTEN_ON_LOCALHOST_ONLY", "0") == "1":
        return True

    valid_answers = ["127.0.0.1", "localhost"]

    remote_addr = os.environ.get("REMOTE_ADDR", None)
    if remote_addr:
        if remote_addr in valid_answers:
            return True
    else:
        remote_host = os.environ.get("REMOTE_HOST", None)
        if remote_host in valid_answers:
            return True
    return False

class FakeException(object):
    def __init__(self, description):
        self.description = description

def assert_client_from_localhost():
    if not is_client_from_localhost():
        show_tourney_exception(FakeException(
            "You're only allowed to access this page from the same computer " +
            "as the one on which atropine is running. Your address is " + 
            os.environ.get("REMOTE_ADDR", "(unknown)") + " and I'll only " +
            "serve you this page if you're from localhost."))
        writeln("</body></html>")
        sys.exit(1)

