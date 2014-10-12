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

	standings = tourney.get_standings();

	games = tourney.get_games();

	if export_format == "html":
		print "Content-Type: text/html; charset=utf-8";
		print "";
		started_html = True;

		cgicommon.print_html_head("Tourney: %s" % tourney_name);

		print "<body>";

		print "<h1>%s - Standings</h1>" % tourney_name

		print "<p>"
		rank_method = tourney.get_rank_method();
		if rank_method == countdowntourney.RANK_WINS_POINTS:
			print "Players are ranked by wins, then points.";
		elif rank_method == countdowntourney.RANK_POINTS:
			print "Players are ranked by points.";
		else:
			print "Players are ranked somehow. Your guess is as good as mine.";
		print "</p>"

		print "<table class=\"standingstable\">";
		print "<tr><th></th><th></th><th>P</th><th>W</th><th>Pts</th></tr>";
		last_wins = None;
		tr_bgcolours = ["#ffdd66", "#ffff88" ];
		bgcolour_index = 0;
		for s in standings:
			(pos, name, played, wins, points) = s;
			if rank_method == countdowntourney.RANK_WINS_POINTS:
				if last_wins is None:
					bgcolour_index = 0;
				elif last_wins != wins:
					bgcolour_index = (bgcolour_index + 1) % 2;
				last_wins = wins;

				print "<tr class=\"standingsrow\" style=\"background-color: %s\">" % tr_bgcolours[bgcolour_index];
			print "<td class=\"standingspos\">%d</td>" % pos;
			print "<td class=\"standingsname\">%s</td>" % name;
			print "<td class=\"standingsplayed\">%d</td>" % played;
			print "<td class=\"standingswins\">%d</td>" % wins;
			print "<td class=\"standingspoints\">%d</td>" % points;
			print "</tr>";
		print "</table>";

		print "<h1>Results</h1>"
		prev_round_no = None
		prev_table_no = None
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
			if prev_table_no is None or prev_table_no != g.table_no:
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
		elif rank_method == countdowntourney.RANK_POINTS:
			print "Players are ranked by points.";
		else:
			print "Players are ranked somehow. Your guess is as good as mine.";
		print ""
		max_name_len = max(map(lambda x : len(x[1]), standings));
		header_format_string = "%%-%ds  P   W  Pts" % (max_name_len + 6);
		print header_format_string % ""
		for s in standings:
			print "%3d %-*s  %3d %3d %4d" % (s[0], max_name_len, s[1], s[2], s[3], s[4])
		print ""

		print "RESULTS"

		prev_round_no = None
		prev_table_no = None
		for g in games:
			if prev_round_no is None or prev_round_no != g.round_no:
				print ""
				print tourney.get_round_name(g.round_no)
				prev_table_no = None
			if prev_table_no is None or prev_table_no != g.table_no:
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
	else:
		show_error("Unknown export format: %s" % export_format);
except countdowntourney.TourneyException as e:
	if started_html:
		cgicommon.show_tourney_exception(e);
	else:
		show_error(e.get_description());

sys.exit(0)
