#!/usr/bin/python

# vim: ts=4 sw=4 noexpandtab

import sys;
import os;
import cgi;
import urllib;

dbdir = os.path.join("..", "tourneys");

def print_html_head(title):
	print """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en-GB" xml:lang="en-GB">
""";
	print "<head>";
	print "<title>%s</title>" % (cgi.escape(title));
	print "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />";
	print "<link rel=\"stylesheet\" type=\"text/css\" href=\"/style.css\" />";
	print "</head>";

def show_tourney_exception(exc):
	print "<blockquote>";
	print "<strong>%s</strong>" % cgi.escape(exc.description);
	print "</blockquote>";

def set_module_path():
	generator_dir = os.environ.get("GENERATORPATH", ".");
	code_dir = os.environ.get("CODEPATH", os.path.join("..", "..", "py"));
	sys.path.append(generator_dir);
	sys.path.append(code_dir);


def show_sidebar(tourney):
	print "<div class=\"sidebar\">";

	print "<a href=\"/cgi-bin/home.py\">Home</a><br />";
	if tourney:
		print "<p><strong>%s</strong></p>" % cgi.escape(tourney.name);
		print "<a href=\"/cgi-bin/tourneysetup.py?tourney=%s\">Setup</a><br />" % urllib.quote_plus(tourney.name);
		print "<br />";

		print "<a href=\"/cgi-bin/teleost.py?tourney=%s\">Display Control</a><br />" % urllib.quote_plus(tourney.name);
		print "<br />";

		rounds = tourney.get_rounds();
		for r in rounds:
			round_no = r["num"];
			round_type = r["type"];
			round_name = r.get("name", None);
			if not round_name:
				round_name = "Round " + str(round_no);

			print "<div class=\"roundlink\">";
			print "<a href=\"/cgi-bin/games.py?tourney=%s&amp;round=%s\">%s</a>" % (urllib.quote_plus(tourney.name), urllib.quote_plus(str(round_no)), cgi.escape(round_name));
			print "</div>";
		print "<br />";
		print "<div class=\"genroundlink\">";
		print "<a href=\"/cgi-bin/fixturegen.py?tourney=%s\">Generate new round...</a>" % (urllib.quote_plus(tourney.name));
		print "</div>";

		print "<div class=\"standingslink\">";
		print "<a href=\"/cgi-bin/standings.py?tourney=%s\">Standings</a>" % (urllib.quote_plus(tourney.name));
		print "</div>";
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

def show_games_as_html_table(games, editable=True, remarks=None):
	if remarks is None:
		remarks = dict()

	print "<table class=\"scorestable\">";
	print "<tr>";
	print "<th>Table</th><th>Type</th>";
	print "<th>Player 1</th><th>Score</th><th>Player 2</th><th></th>";       
	print "</tr>"
	last_table_no = None;
	gamenum = 0;
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
		
		team_string = make_player_dot_html(g.p1)

		print "<td class=\"%s\" align=\"right\">%s %s</td>" % (" ".join(p1_classes), cgi.escape(player_strings[0]), team_string);
		score = g.format_score();
		print "<td class=\"gamescore\" align=\"center\">";

		if g.are_players_known():
			if editable:
				print """
<input class="gamescore" id="game%dscore" type="text" size="10"
name="game%dscore" value="%s"
onchange="score_modified('game%dscore');" />""" % (gamenum, gamenum, cgi.escape(score, True), gamenum);
			else:
				print cgi.escape(score)

		print "</td>";
		team_string = make_player_dot_html(g.p2)
		print "<td class=\"%s\" align=\"left\">%s %s</td>" % (" ".join(p2_classes), team_string, cgi.escape(player_strings[1]));
		print "<td class=\"gameremarks\">%s</td>" % cgi.escape(remarks.get(gamenum, ""));
		print "</tr>";
		gamenum += 1;
		last_table_no = g.table_no;
	
	print "</table>";
