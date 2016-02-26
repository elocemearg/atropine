#!/usr/bin/python

import sys;
import cgicommon;
import urllib;
import cgi;
import cgitb;

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

if export_format is None:
    export_format = "text"

tourney = None;

cgicommon.set_module_path();

import countdowntourney;

if tourney_name is None:
    show_error("No tourney specified");
    sys.exit(0);

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
    else:
        show_error("Unknown export format: %s" % export_format);
except countdowntourney.TourneyException as e:
    if started_html:
        cgicommon.show_tourney_exception(e);
    else:
        show_error(e.get_description());

sys.exit(0)
