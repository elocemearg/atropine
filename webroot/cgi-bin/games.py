#!/usr/bin/python

import sys;
import cgicommon;
import urllib;
import cgi;
import cgitb;
import os;
import re;
import random;

def set_random_score(game):
	r1 = game.p1.rating;
	r2 = game.p2.rating;

	# multiply stronger player's rating by 1.8 to magnify differences
	if r1 > r2:
		r1 *= 1.8;
	elif r2 > r1:
		r2 *= 1.8;

	p1_threshold = float(r1) / float(r1 + r2);
	p2_threshold = p1_threshold;
	p1_threshold *= 0.8
	p2_threshold = 1 - ((1 - p2_threshold) * 0.8)

	#print "%d %d %.3f %.3f" % (game.p1.rating, game.p2.rating, p1_threshold, p2_threshold);

	p1_score = 0;
	p2_score = 0;

	for i in range(9):
		x = random.random();
		round_score = random.randint(4, 10);
		if round_score == 9:
			if random.randint(1, 4) == 1:
				round_score = 18;
			else:
				round_score = 7;
		if x < p1_threshold:
			p1_score += round_score;
		elif x > p2_threshold:
			p2_score += round_score;
		else:
			p1_score += round_score;
			p2_score += round_score;

	if p1_score == p2_score:
		if random.randint(0, 1) == 0:
			p1_score += 10;
		else:
			p2_score += 10;
		tb = True;
	else:
		tb = False;

	game.set_score(p1_score, p2_score, tb);


cgitb.enable();

print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/games.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

import countdowntourney;

cgicommon.print_html_head("Games: " + str(tourney_name));

print "<body>";

if tourney_name is None:
	print "<h1>No tourney specified</h1>";
	print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>";
	print "</body></html>";
	sys.exit(0);

try:
	tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

	cgicommon.show_sidebar(tourney);

	print "<div class=\"mainpane\">";

	# If a round is selected, show the scores for that round, in editable
	# boxes so they can be changed.
	round_no = None;
	if "round" in form:
		try:
			round_no = int(form.getfirst("round"));
		except ValueError:
			print "<h1>Invalid round number</h1>";
			print "<p>\"%s\" is not a valid round number.</p>";
	
	if round_no is not None:
		games = tourney.get_games(round_no=round_no);
		rounds = tourney.get_rounds();
		round_name = None;
		last_modified_element = None;
		for r in rounds:
			if r["num"] == round_no:
				round_name = r.get("name", None);
				break;
		if not round_name:
			round_name = "Round " + str(round_no);

		remarks = dict();

		print "<h1>Score editor: %s</h1>" % cgi.escape(round_name);

		print "<p>";
		print "<a href=\"/cgi-bin/fixtureedit.py?tourney=%s&amp;round=%d\">Edit fixtures</a>" % (urllib.quote_plus(tourney_name), round_no);
		print "</p>";

		print "<script>"
		print """function set_unsaved_data_warning() {
	if (window.onbeforeunload == null) {
		window.onbeforeunload = function() {
			return 'You have modified scores on this page and not saved them.';
		};
	}
}

function unset_unsaved_data_warning() {
	window.onbeforeunload = null;
}

function score_modified(control_name) {
	document.getElementById('lastmodified').value = control_name;
	document.getElementById(control_name).style = 'background-color: #ffffcc;';
	set_unsaved_data_warning();
}
""";

		print "</script>"
		
		if "save" in form or "randomresults" in form:
			# If the user clicked Save, then save the new scores to the
			# database.
			gamenum = 0;

			last_modified_element = form.getfirst("lastmodified");
			if last_modified_element:
				if not re.match("^game[0-9]+score$", last_modified_element):
					last_modified_element = None;

			for g in games:
				if "randomresults" in form:
					set_random_score(g);
				else:
					score = form.getfirst("game%dscore" % gamenum);
					# We're pretty liberal about what constitutes a score.
					# A number, followed by an optional asterisk, followed by
					# any sequence of non-numbers, followed by a number,
					# followed by an optional asterisk.
					
					# If the score consists only of whitespace, then the game
					# hasn't been played.
					if not score or re.match("^\s*$", score):
						g.set_score(None, None, False);
					else:
						m = re.match("^\s*(\d+)\s*(\*?)\D+\s*(\d+)\s*(\*?)\s*$", score);
						if not m:
							remarks[gamenum] = "Invalid score: %s" % score;
						else:
							s1 = int(m.group(1));
							s2 = int(m.group(3));
							if m.group(2) == "*" or m.group(4) == "*":
								tb = True;
							else:
								tb = False;
							g.set_score(s1, s2, tb);

				gamenum += 1;
			tourney.merge_games(games);

		print "<div class=\"scorestable\">";
		print "<form method=\"POST\" action=\"%s?tourney=%s&amp;round=%d\">" % (baseurl, urllib.quote_plus(tourney_name), round_no);
		print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % cgi.escape(tourney_name, True);
		print "<input type=\"hidden\" name=\"round\" value=\"%d\" />" % round_no;
		print "<input type=\"hidden\" id=\"lastmodified\" name=\"lastmodified\" value=\"\" />";

		print "<table class=\"scorestable\">";
		print "<tr>";
		print "<th>Table</th><th>Type</th>";
		print "<th>Player 1</th><th>Score</th><th>Player 2</th><th>Remarks</th>";
		print "</tr>"

		gamenum = 0;
		last_table_no = None;
		games = tourney.get_games(round_no=round_no, only_players_known=False);
		for g in games:
			player_names = g.get_player_names();
			player_strings = (str(g.p1), str(g.p2));
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
			
			if g.is_complete():
				tr_classes.append("completedgame");
			else:
				tr_classes.append("unplayedgame");

			print "<tr class=\"%s\">" % " ".join(tr_classes);
			#print "<td class=\"roundno\">%d</td>" % round_no;
			if first_game_in_table:
				print "<td class=\"tableno\" rowspan=\"%d\">%d</td>" % (num_games_on_table, g.table_no);
			print "<td class=\"gametype\">%s</td>" % cgi.escape(g.game_type);

			p1_classes = ["gameplayer1"];
			p2_classes = ["gameplayer2"];
			if g.is_complete():
				if g.s1 == g.s2:
					p1_classes.append("losingplayer");
					p2_classes.append("losingplayer");
				elif g.s1 > g.s2:
					p1_classes.append("winningplayer");
					p2_classes.append("losingplayer");
				elif g.s2 > g.s1:
					p1_classes.append("losingplayer");
					p2_classes.append("winningplayer");
			
			print "<td class=\"%s\" align=\"right\">%s</td>" % (" ".join(p1_classes), cgi.escape(player_strings[0]));
			score = g.format_score();
			print "<td class=\"gamescore\" align=\"center\">";

			if g.are_players_known():
				print """
<input class="gamescore" id="game%dscore" type="text" size="10"
	name="game%dscore" value="%s"
	onchange="score_modified('game%dscore');" />""" % (gamenum, gamenum, cgi.escape(score, True), gamenum);

			print "</td>";
			print "<td class=\"%s\" align=\"left\">%s</td>" % (" ".join(p2_classes), cgi.escape(player_strings[1]));
			print "<td class=\"gameremarks\">%s</td>" % cgi.escape(remarks.get(gamenum, ""));
			print "</tr>";
			gamenum += 1;
			last_table_no = g.table_no;
		
		print "</table>";

		print "<input type=\"submit\" name=\"save\" value=\"Save\" onclick=\"unset_unsaved_data_warning();\" />";
		#print "<input type=\"submit\" name=\"randomresults\" value=\"Random Results\" />";

		print "</form>"

		focus_index = None;
		if last_modified_element:
			m = re.match("^game([0-9]+)score$", last_modified_element)
			if m:
				lastmod_index = int(m.group(1));
				# The box with focus should be the next unfilled box equal to
				# or after the one that was last modified. If they're all
				# filled, put the focus on the first box.
				if lastmod_index >= 0 and lastmod_index < len(games):
					for i in range(0, len(games)):
						g = games[(lastmod_index + i) % len(games)];
						if not g.is_complete():
							focus_index = (lastmod_index + i) % len(games);
							break;
		if focus_index is None:
			focus_index = 0;

		if focus_index >= 0 and focus_index < len(games):
			control_with_focus = "game%dscore" % focus_index;
			print "<script>"
			print "document.getElementById('" + control_with_focus + "').focus();"
			print "</script>"


		print "</div>"; #scorestable

	print "</div>"; #mainpane

except countdowntourney.TourneyException as e:
	cgicommon.show_tourney_exception(e);

print "</body>";
print "</html>";

sys.exit(0);
