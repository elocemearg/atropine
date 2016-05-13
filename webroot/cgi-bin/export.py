#!/usr/bin/python

import sys
import cgicommon
import urllib
import cgi
import cgitb
import datetime
import calendar

def int_or_none(s):
    try:
        i = int(s)
        return i
    except:
        return None

def valid_date(d, m, y):
    try:
        datetime.datetime.strptime("%04d-%02d-%02d" % (y, m, d), "%Y-%m-%d")
        return True
    except ValueError:
        return False

def show_error(err_str):
    print "Content-Type: text/html; charset=utf-8";
    print "";
    cgicommon.print_html_head("Tourney: %s" % tourney_name);

    print "<body>";

    cgicommon.show_sidebar(tourney);

    print "<div class=\"mainpane\">"
    print "<p><strong>%s</strong></p>" % err_str
    print "</div>"
    print "</body>"
    print "</html>"

cgitb.enable();

started_html = False;
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");
export_format = form.getfirst("format");
wikitext_date_d = form.getfirst("wikitextday");
wikitext_date_m = form.getfirst("wikitextmonth");
wikitext_date_y = form.getfirst("wikitextyear");
wikitext_game_prefix = form.getfirst("wikitextgameprefix")
wikitext_submit = form.getfirst("wikitextsubmit")

if export_format is None:
    export_format = "text"

tourney = None;

cgicommon.set_module_path();

import countdowntourney;

if tourney_name is None:
    show_error("No tourney specified");
    sys.exit(0);

# If the user has asked for wikitext, prompt the user for the date of the
# tournament and the prefix for any individual game articles.
if export_format == "wikitext":
    errors = []
    if wikitext_submit:
        # Check that what the user has put in the form makes sense, and if it
        # doesn't, ask them to try again
        wikitext_date_d = int_or_none(wikitext_date_d)
        wikitext_date_m = int_or_none(wikitext_date_m)
        wikitext_date_y = int_or_none(wikitext_date_y)
        if wikitext_date_d is None or wikitext_date_m is None or wikitext_date_y is None or not valid_date(wikitext_date_d, wikitext_date_m, wikitext_date_y):
            errors.append("That date is not valid.")

    if errors or wikitext_submit is None:
        print "Content-Type: text/html; charset=utf-8"
        print ""
        started_html = True

        cgicommon.print_html_head("Tournament report - Wikitext")

        tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
        cgicommon.show_sidebar(tourney)

        # Default value for date is today, default value for game prefix is the
        # tourney name, upcased, with all non-letter and non-digit characters
        # removed, and with a dot on the end if it ends with a digit.
        if wikitext_submit is None:
            today = datetime.date.today()
            wikitext_date_d = today.day
            wikitext_date_m = today.month
            wikitext_date_y = today.year

            wikitext_game_prefix = ""
            for c in tourney_name.upper():
                if c.isupper() or c.isdigit():
                    wikitext_game_prefix += c
            if wikitext_game_prefix[-1].isdigit():
                wikitext_game_prefix += "."

        print "<body>"
        print "<div class=\"mainpane\">"
        print "<h1>Tournament report - Wikitext</h1>"
        if errors:
            print "<h2>Failed to generate wikitext...</h2>"
            print "<blockquote>"
            for txt in errors:
                print "<li>%s</li>" % (cgi.escape(txt))
            print "</blockquote>"

        print "<p>"
        print "Select the date the tournament was played, and a string to prefix each game ID. Then generate the wikitext for copy-pasting into a new wiki page."
        print "</p>"
        print "<form method=\"GET\" action=\"/cgi-bin/export.py\">"
        print "<table>"
        print "<tr><td>Day</td><td>Month</td><td>Year</td></tr>"
        print "<tr>"
        print "<td><input type=\"number\" name=\"wikitextday\" value=\"%d\" min=\"1\" max=\"31\" size=\"2\" maxlength=\"2\" /></td>" % (wikitext_date_d)
        print "<td>"
        print "<select name=\"wikitextmonth\">"
        for m in range(1, 13):
            print "<option value=\"%d\" %s>%s</option>" % (m, "selected " if m == wikitext_date_m else "", cgi.escape(calendar.month_name[m]))
        print "</select>"
        print "</td>"
        print "<td><input type=\"number\" name=\"wikitextyear\" value=\"%d\" min=\"0\" max=\"9999\" size=\"4\" maxlength=\"4\" /></td>" % (wikitext_date_y)
        print "</tr></table>"
        print "<p>"
        print "Game ID prefix: <input type=\"text\" name=\"wikitextgameprefix\" value=\"%s\" />" % (cgi.escape(wikitext_game_prefix, True))
        print "</p>"
        print "<p>"
        print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgi.escape(tourney_name, True))
        print "<input type=\"hidden\" name=\"format\" value=\"wikitext\" />"
        print "<input type=\"submit\" name=\"wikitextsubmit\" value=\"Generate Wikitext\" />"
        print "</p>"
        print "</form>"
        print "</div>"
        print "</body>"
        print "</html>"
        sys.exit(0)


try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

    games = tourney.get_games();

    show_draws_column = tourney.get_show_draws_column()

    rank_method = tourney.get_rank_method()
    show_points_column = (rank_method in [countdowntourney.RANK_WINS_POINTS, countdowntourney.RANK_POINTS])
    show_spread_column = (rank_method == countdowntourney.RANK_WINS_SPREAD)
    show_tournament_rating_column = tourney.get_show_tournament_rating_column()

    if export_format == "html":
        print "Content-Type: text/html; charset=utf-8";
        print "";
        started_html = True;

        cgicommon.print_html_head("Tourney: %s" % tourney_name);

        print "<body>";

        print "<h1>%s - Standings</h1>" % tourney_name

        num_divisions = tourney.get_num_divisions()

        print "<p>"
        rank_method = tourney.get_rank_method();
        if rank_method == countdowntourney.RANK_WINS_POINTS:
            print "Players are ranked by wins, then points."
        elif rank_method == countdowntourney.RANK_WINS_SPREAD:
            print "Players are ranked by wins, then cumulative winning margin."
        elif rank_method == countdowntourney.RANK_POINTS:
            print "Players are ranked by points.";
        else:
            print "Players are ranked somehow. Your guess is as good as mine.";
        if show_draws_column:
            print "Draws count as half a win."
        print "</p>"

        rank_method = tourney.get_rank_method()
        cgicommon.show_standings_table(tourney, tourney.get_show_draws_column(), rank_method in (countdowntourney.RANK_WINS_POINTS, countdowntourney.RANK_POINTS), rank_method == countdowntourney.RANK_WINS_SPREAD, False, False, show_tournament_rating_column)

        print "<h1>Results</h1>"
        prev_round_no = None
        prev_table_no = None
        prev_division = None
        show_table_numbers = None
        game_seq = 0
        for g in games:
            if prev_round_no is None or prev_round_no != g.round_no:
                if prev_round_no is not None:
                    print "</table>"
                    print "<h2>%s</h2>" % tourney.get_round_name(g.round_no)
                    print "<table class=\"resultstable\">"
                else:
                    print "<h2>%s</h2>" % tourney.get_round_name(g.round_no)
                    print "<table class=\"resultstable\">"
                prev_table_no = None
                prev_division = None
            if prev_division is None or prev_division != g.division:
                if num_divisions > 1:
                    print "<tr class=\"exportdivisionnumber\"><th class=\"exportdivisionnumber\" colspan=\"3\">%s</th></tr>" % (cgi.escape(tourney.get_division_name(g.division)))

                # If this division has a table with more than one game on it
                # then show the table numbers, otherwise don't bother.
                prev_table_no = g.table_no
                show_table_numbers = False
                i = 1
                while game_seq + i < len(games) and games[game_seq + i].round_no == g.round_no and games[game_seq + i].division == g.division:
                    if games[game_seq + i].table_no == prev_table_no:
                        show_table_numbers = True
                        break
                    prev_table_no = games[game_seq + i].table_no
                    i += 1
                prev_table_no = None
            if prev_table_no is None or prev_table_no != g.table_no:
                if show_table_numbers:
                    print "<tr class=\"exporttablenumber\"><th class=\"exporttablenumber\" colspan=\"3\">Table %d</th></tr>" % g.table_no
            print "<tr class=\"exportgamerow\">"
            names = g.get_player_names();
            print "<td class=\"exportleftplayer\">%s</td>" % names[0];
            if g.s1 is None or g.s2 is None:
                print "<td class=\"exportscore\"> v </td>"
            else:
                print "<td class=\"exportscore\">%s</td>" % cgi.escape(g.format_score());
            print "<td class=\"exportrightplayer\">%s</td>" % names[1];
            print "</tr>"
            prev_table_no = g.table_no
            prev_round_no = g.round_no
            prev_division = g.division
            game_seq += 1
        if prev_round_no is not None:
            print "</table>"

        print "</body></html>";
    elif export_format == "text":
        print "Content-Type: text/plain; charset=utf-8"
        print tourney_name
        print ""
        print "STANDINGS"
        print ""
        rank_method = tourney.get_rank_method();
        if rank_method == countdowntourney.RANK_WINS_POINTS:
            print "Players are ranked by wins, then points.";
        elif rank_method == countdowntourney.RANK_WINS_SPREAD:
            print "Players are ranked by wins, then cumulative winning margin."
        elif rank_method == countdowntourney.RANK_POINTS:
            print "Players are ranked by points.";
        else:
            print "Players are ranked somehow. Your guess is as good as mine.";
        if show_draws_column:
            print "Draws count as half a win."
        print ""
        print ""

        num_divisions = tourney.get_num_divisions()

        # First, work out how much room we need for the longest name
        max_name_len = 0
        for div_index in range(num_divisions):
            standings = tourney.get_standings(div_index)
            if len(standings) > 0:
                m = max(map(lambda x : len(x[1]), standings));
                if m > max_name_len:
                    max_name_len = m

        for div_index in range(num_divisions):
            standings = tourney.get_standings(div_index)
            if num_divisions > 1:
                print tourney.get_division_name(div_index)
            header_format_string = "%%-%ds  P   W%s%s%s%s" % (
                    max_name_len + 6,
                    "   D" if show_draws_column else "",
                    "  Pts" if show_points_column else "",
                    "   Spr" if show_spread_column else "",
                    "      TR" if show_tournament_rating_column else "")
            print header_format_string % ""
            for s in standings:
                sys.stdout.write("%3d %-*s  %3d %3d " % (s[0], max_name_len, s[1], s[2], s[3]))
                if show_draws_column:
                    sys.stdout.write("%3d " % s[5])
                if show_points_column:
                    sys.stdout.write("%4d " % s[4])
                if show_spread_column:
                    sys.stdout.write("%+5d " % s[6])
                if show_tournament_rating_column:
                    if s.tournament_rating is not None:
                        sys.stdout.write("%7.2f " % s.tournament_rating)
                    else:
                        sys.stdout.write("        ")
                print ""
            print ""
            print ""

        print "RESULTS"

        prev_round_no = None
        prev_table_no = None
        prev_division = None
        show_table_numbers = False
        game_seq = 0
        for g in games:
            if prev_round_no is None or prev_round_no != g.round_no:
                print ""
                print tourney.get_round_name(g.round_no)
                prev_table_no = None
                prev_division = None
            if prev_division is None or prev_division != g.division:
                if num_divisions > 1:
                    print ""
                    print tourney.get_division_name(g.division)
                i = 1
                prev_table_no = g.table_no
                show_table_numbers = False
                # If this division in this round has a table with more than
                # one game on it, show the table numbers, else don't.
                while game_seq + i < len(games) and games[game_seq + i].round_no == g.round_no and games[game_seq + i].division == g.division:
                    if games[game_seq + i].table_no == prev_table_no:
                        show_table_numbers = True
                        break
                    prev_table_no = games[game_seq + i].table_no
                    i += 1
                prev_table_no = None
            if prev_table_no is None or prev_table_no != g.table_no:
                if show_table_numbers:
                    print ""
                    print "Table %d" % g.table_no
            if g.s1 is None or g.s2 is None:
                score_str = "    -    "
            else:
                score_str = "%3d%s-%s%d" % (g.s1, "*" if g.tb and g.s1 > g.s2 else " ", "*" if g.tb and g.s2 > g.s1 else " ", g.s2)
            names = g.get_player_names()
            print "%*s %-9s %s" % (max_name_len, names[0], score_str, names[1])
            prev_round_no = g.round_no
            prev_table_no = g.table_no
            prev_division = g.division
            game_seq += 1
    elif export_format == "wikitext":
        num_divisions = tourney.get_num_divisions()
        print "Content-Type: text/plain; charset=utf-8"
        print ""
        print "==Standings=="
        print
        for div_index in range(num_divisions):
            if num_divisions > 1:
                print "===%s===" % (tourney.get_division_name(div_index))
            standings = tourney.get_standings(div_index)
            print "{|"
            sys.stdout.write("! Rank !! Name !! Games !! Wins")
            if show_draws_column:
                sys.stdout.write(" !! Draws")
            if show_points_column:
                sys.stdout.write(" !! Points")
            if show_spread_column:
                sys.stdout.write(" !! Spread")
            if show_tournament_rating_column:
                sys.stdout.write(" !! Tournament rating")
            print ""
            for s in standings:
                print "|-"
                sys.stdout.write("| %3d || %s || %d || %d" % (s.position, s.name, s.played, s.wins))
                if show_draws_column:
                    sys.stdout.write(" || %d" % (s.draws))
                if show_points_column:
                    sys.stdout.write(" || %d" % (s.points))
                if show_spread_column:
                    sys.stdout.write(" || %+d" % (s.spread))
                if show_tournament_rating_column:
                    sys.stdout.write(" || %d" % (s.tournament_rating))
                print ""
            print "|-"
            print "|}"
            print

        print "==Results=="
        num_tiebreaks = 0
        game_serial_no = 1
        wikitext_date = "%02d/%02d/%04d" % (wikitext_date_d, wikitext_date_m, wikitext_date_y)
        for div_index in range(num_divisions):
            if num_divisions > 1:
                print "===%s===" % (tourney.get_division_name(div_index))
            print "{{game table}}"
            div_games = filter(lambda x : x.get_division() == div_index, games)
            prev_round_no = None
            for g in div_games:
                if g.round_no != prev_round_no:
                    print "{{game table block|%s}}" % (tourney.get_round_name(g.round_no))
                print "{{game | %s%03d | %s | Table %d | %s | %s | %s | }}" % (
                        wikitext_game_prefix, game_serial_no, wikitext_date,
                        g.table_no, g.get_player_names()[0], g.format_score(),
                        g.get_player_names()[1])
                if g.tb:
                    num_tiebreaks += 1
                prev_round_no = g.round_no
                game_serial_no += 1
            print "{{game table end}}"
            print ""

        if num_tiebreaks > 0:
            print "<center>* includes 10 points from a tie-break conundrum</center>"

    else:
        show_error("Unknown export format: %s" % export_format);
except countdowntourney.TourneyException as e:
    if started_html:
        cgicommon.show_tourney_exception(e);
    else:
        show_error(e.get_description());

sys.exit(0)
