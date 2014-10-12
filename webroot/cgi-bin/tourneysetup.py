#!/usr/bin/python

# vim: ts=4 noexpandtab

import cgi;
import cgitb;
import cgicommon;
import sys;
import csv;
import os;
import urllib;

def int_or_none(s):
	if s is None:
		return None;
	try:
		return int(s);
	except ValueError:
		return None;

cgitb.enable();

cgicommon.set_module_path();
import countdowntourney;

print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/tourneysetup.py";
form = cgi.FieldStorage();
tourneyname = form.getfirst("tourney");
playerlist = form.getfirst("playerlist");
player_list_submit = form.getfirst("playerlistsubmit");
players_per_table = form.getfirst("playerspertable");
players_per_table = int_or_none(players_per_table);
modify_player_submit = form.getfirst("modifyplayersubmit");
rank = form.getfirst("rank");
rank = int_or_none(rank);
rules_submit = form.getfirst("rulessubmit");


tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Tourney Setup: " + str(tourneyname));

print "<body>";



if tourneyname is not None:
	try:
		tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
	except countdowntourney.TourneyException as e:
		cgicommon.show_tourney_exception(e);

cgicommon.show_sidebar(tourney);

print "<div class=\"mainpane\">";
print "<h1>Tourney Setup</h1>";

if tourneyname is None:
	print "<h1>Sloblock</h1>";
	print "<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>";
elif not tourney:
	print "<p>No valid tourney name specified</p>";
else:
	print '<p><a href="%s?tourney=%s">%s</a></p>' % (baseurl, urllib.quote_plus(tourneyname), cgi.escape(tourneyname));
	if request_method == "POST" and playerlist and player_list_submit:
		lines = playerlist.split("\n");
		lines = filter(lambda x : len(x) > 0, map(lambda x : x.rstrip(), lines));
		reader = csv.reader(lines);
		player_rating_list = [];
		for row in reader:
			if len(row) == 1:
				player_rating_list.append((row[0].lstrip().rstrip(), None));
			else:
				player_rating_list.append((row[0].lstrip().rstrip(), row[1]));
		try:
			tourney.set_players(player_rating_list);
			print "<p><strong>Player list updated successfully.</strong></p>";
		except countdowntourney.TourneyException as e:
			cgicommon.show_tourney_exception(e);
	if request_method == "POST" and rules_submit:
		try:
			tourney.set_rank_method(rank);
			tourney.set_table_size(players_per_table);
			print "<p><strong>Rules updated successfully.</strong></p>";
		except countdowntourney.TourneyException as e:
			cgicommon.show_tourney_exception(e);
	if request_method == "POST" and modify_player_submit:
		try:
			cur_name = form.getfirst("playername")
			if cur_name:
				new_name = form.getfirst("newplayername")
				new_rating = form.getfirst("newplayerrating")
				if new_name:
					tourney.rename_player(cur_name, new_name);
					cur_name = new_name;
				if new_rating:
					try:
						new_rating = int(new_rating);
						tourney.rerate_player(cur_name, new_rating);
					except ValueError:
						print "<p><strong>Failed to rerate player: \"%s\" is not a valid rating.</strong></p>" % cgi.escape(new_rating);
		except countdowntourney.TourneyException as e:
			cgicommon.show_tourney_exception(e);

	if tourney.get_num_games() > 0:
		print "<p>Tournament has started.</p>";

		print "<h2>Modify player</h2>"
		print "<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.quote_plus(tourneyname))
		print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % cgi.escape(tourneyname, True)

		print "<select name=\"playername\">"
		players = tourney.get_players();
		players = sorted(players, key=lambda x : x.name);
		print "<option value=\"\">-- select player --</option>"
		for p in players:
			print "<option value=\"%s\">%s (%d)</option>" % (cgi.escape(p.name, True), cgi.escape(p.name), p.rating);
		print "</select>"
		print "<br />"
		print "New name <input type=\"text\" name=\"newplayername\" /> (blank to leave unchanged)<br />"
		print "New rating <input type=\"text\" name=\"newplayerrating\" /> (blank to leave unchanged)<br />"
		print "<input type=\"submit\" name=\"modifyplayersubmit\" value=\"Modify Player\" />"
		print "</form>"
	else:
		print "<h2>Player list</h2>";
		print "<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.quote_plus(tourneyname))
		print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname);
		print '<textarea rows="30" cols="40" name="playerlist">';
		players = tourney.get_players();
		auto_ratings = tourney.are_ratings_automatic();
		writer = csv.writer(sys.stdout);
		# Write player names, or player names and ratings if the user specified
		# the players' ratings.
		for p in players:
			(name, rating) = p;
			if auto_ratings and rating != 0:
				writer.writerow((cgi.escape(name),));
			else:
				writer.writerow((cgi.escape(name), str(rating)));
		print "</textarea><br />";

		table_size = tourney.get_table_size();
		if players_per_table:
			table_size = players_per_table;
		if len(players) % table_size != 0:
			print "<blockquote>";
			print "<strong>Warning!</strong> Number of players must be a multiple of %d to generate fixtures!</strong>" % table_size;
			print "</blockquote>";
		print '<input type="submit" name="playerlistsubmit" value="Save Player List" />'
		print '</form>'

	players_per_table = tourney.get_table_size();
	rank = tourney.get_rank_method();
	print "<h2>Tourney rules</h2>";
	print '<form action="%s" method="post" />' % baseurl;
	print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname);
	print "<h3>Rank players by</h3>";
	print "<blockquote>";
	print '<input type="radio" name="rank" value="%d" %s /> Wins, then points<br />' % (countdowntourney.RANK_WINS_POINTS, "checked" if rank == countdowntourney.RANK_WINS_POINTS else "");
	print '<input type="radio" name="rank" value="%d" %s /> Points only' % (countdowntourney.RANK_POINTS, "checked" if rank == countdowntourney.RANK_POINTS else "");
	print '</blockquote>';
	print "<h3>Players per table</h3>";
	print "<blockquote>";
	print '<input type="radio" name="playerspertable" value="2" %s /> 2<br />' % ("checked" if players_per_table == 2 else "");
	print '<input type="radio" name="playerspertable" value="3" %s /> 3' % ("checked" if players_per_table == 3 else "");
	print "</blockquote>";
	print '<input type="submit" name="rulessubmit" value="Save Rules" />';
	print "</form>";

	if tourney.get_num_games() > 0:
		print '<h2>Delete rounds</h2>'
		print '<p>Press this button to delete the most recent round. You\'ll be asked to confirm on the next screen.</p>'
		print '<form action="/cgi-bin/delround.py" method="get" />'
		print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname)
		print '<input type="submit" name="delroundsetupsubmit" value="Delete most recent round" />'
		print '</form>'

print "</div>";

print "</body>";
print "</html>";
