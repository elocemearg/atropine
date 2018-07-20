#!/usr/bin/python3

import sys
import cgi
import cgitb
import cgicommon
import os
import urllib.request, urllib.parse, urllib.error
import random

cgitb.enable();

cgicommon.set_module_path();
import countdowntourney;

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;

def random_team_assignment(tourney, group_size):
    # Get a list of all players, excluding prunes (players with a rating of 0)
    players = tourney.get_players()
    prunes = [ p for p in players if p.get_rating() <= 0 ]

    players = [ p for p in players if p.get_rating() > 0]

    # Sort them by rating descending
    players = sorted(players, key=lambda x : x.get_rating(), reverse=True)

    if group_size < 1:
        group_size = len(players)

    teams = tourney.get_teams()
    if len(teams) == 0:
        # wat
        return []
    
    team_counts = dict()
    for t in teams:
        team_counts[t.get_id()] = 0

    # For each group of group_size players, distribute the players in that
    # group randomly, and as evenly as possible, between the teams. If we have
    # to assign one team more players than other, prefer to assign excess to
    # the team or teams with fewer players at the moment.
    pos = 0
    player_teams = []
    while pos < len(players):
        # our player group
        group = players[pos:(pos + group_size)]

        # sort "teams" so the teams with fewest players assigned to them so far
        # are at the front of the list
        teams = sorted(teams, key=lambda x : (team_counts[x.get_id()], x.get_id()))

        team_ids = []
        for i in range(len(group)):
            team_ids.append(teams[i % len(teams)].get_id())

        # These are the team IDs we want to give out to this group of players.
        # Put the team IDs in a random order...
        random.shuffle(team_ids)

        # Then assign them to players
        for i in range(len(group)):
            player = group[i]
            team_id = team_ids[i]
            player_teams.append((player.get_name(), team_id))
            team_counts[team_id] += 1

        pos += group_size

    # Assign each prune to no team
    for p in prunes:
        player_teams.append((p.get_name(), -1))
    
    # Return the map of players to team IDs
    return player_teams


cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

baseurl = "/cgi-bin/teamsetup.py";
form = cgi.FieldStorage();

tourneyname = form.getfirst("tourney")
player_team_submit = form.getfirst("playerteamsubmit")
random_assignment_submit = form.getfirst("randomassignmentsubmit")
clear_teams_submit = form.getfirst("clearteams")
random_group_size = int_or_none(form.getfirst("randomgroupsize"))
if random_group_size is None:
    random_group_size = 6

tourney = None
tourney_exception = None
player_teams_set = False
request_method = os.environ.get("REQUEST_METHOD", "")

cgicommon.print_html_head("Hangover Team Setup: " + str(tourneyname))

cgicommon.writeln("<body>")

cgicommon.assert_client_from_localhost()

if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);

cgicommon.show_sidebar(tourney);


if tourneyname and tourney:
    if request_method == "POST":
        if player_team_submit:
            index = 0
            player_teams = []
            while form.getfirst("player%d" % (index)):
                player_name = form.getfirst("player%d" % (index))
                team_no = int_or_none(form.getfirst("team%d" % (index)))
                player_teams.append((player_name, team_no))
                index += 1
            try:
                tourney.set_player_teams(player_teams)
                player_teams_set = True
            except countdowntourney.TourneyException as e:
                tourney_exception = e
        elif random_assignment_submit:
            if random_group_size is None:
                random_group_size = 0
            player_teams = random_team_assignment(tourney, random_group_size)
            try:
                tourney.set_player_teams(player_teams)
                player_teams_set = True
            except countdowntourney.TourneyException as e:
                tourney_exception = e
        elif clear_teams_submit:
            players = tourney.get_players()
            player_teams = [ (p.get_name(), None) for p in players ]
            try:
                tourney.set_player_teams(player_teams)
                player_teams_set = True
            except countdowntourney.TourneyException as e:
                tourney_exception = e

cgicommon.writeln("<div class=\"mainpane\">");
cgicommon.writeln("<h1>Hangover Team Setup</h1>");

if tourneyname is None:
    cgicommon.writeln("<h1>Sloblock</h1>");
    cgicommon.writeln("<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>");
elif not tourney:
    cgicommon.writeln("<p>No valid tourney name specified</p>");
else:
    num_players = len(tourney.get_players())

    if player_teams_set:
        cgicommon.writeln("<p><strong>Teams set successfully.</strong></p>")
    elif tourney_exception:
        cgicommon.show_tourney_exception(e)

    #print '<p>'

    teams = tourney.get_teams()
    player_teams = sorted(tourney.get_player_teams(), key=lambda x : x[0].get_rating(), reverse=True)

    if num_players == 0:
        cgicommon.writeln("<p>This tourney doesn't have any players, so you can't specify teams yet.</p>")
        cgicommon.writeln('<p><a href="/cgi-bin/tourneysetup.py?tourney=%s">Back to Tourney Setup</a></p>' % (urllib.parse.quote_plus(tourneyname)));
    else:
        #print '<p><a href="/cgi-bin/tourneysetup.py?tourney=%s">Back to tourney setup</a></p>' % (urllib.quote_plus(tourneyname));
        cgicommon.writeln('<h2>Teams</h2>')
        for team in teams:
            cgicommon.writeln('<p>')
            cgicommon.writeln('<font color="#%s">&bull;</font> %s' % (team.get_hex_colour(), team.get_name()))
            player_name_list = [ cgicommon.escape(p.get_name()) for (p, pt) in player_teams if pt is not None and pt.get_id() == team.get_id() ]

            if player_name_list:
                cgicommon.writeln(" (%d): %s" % (len(player_name_list), ", ".join(player_name_list)));
            else:
                cgicommon.writeln(" (no players)")
            cgicommon.writeln('</p>')

        cgicommon.writeln('<h2>Players</h2>')
        cgicommon.writeln('<form action="%s?tourney=%s" method="POST">' % (cgicommon.escape(baseurl, True), urllib.parse.quote_plus(tourneyname)))
        cgicommon.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname, True))
        cgicommon.writeln('<table border="1">')
        cgicommon.writeln('<tr><th>Player</th>')
        cgicommon.writeln('<th>No team</th>')
        for team in teams:
            cgicommon.writeln('<th>%s</th>' % (cgicommon.escape(team.get_name())))
        cgicommon.writeln('</tr>')

        index = 0
        for player_team in player_teams:
            player = player_team[0]
            team = player_team[1]

            cgicommon.writeln('<tr>')
            cgicommon.writeln('<td align="left">%s<input type="hidden" name="player%d" value="%s" /></td>' % (cgicommon.escape(player.get_name()), index, cgicommon.escape(player.get_name())))

            # Radio button for "no team"
            cgicommon.writeln('<td align="center"><input type="radio" name="team%d" value="%d" %s /></td>' % (index, -1, "checked" if team is None else ""))
            for t in teams:
                cgicommon.writeln('<td align="center" bgcolor="#%s"><input type="radio" name="team%d" value="%d" %s /></td>' % (t.get_hex_colour(), index, t.get_id(), "checked" if team is not None and team.get_id() == t.get_id() else ""))
            cgicommon.writeln('</tr>')
            index += 1
        cgicommon.writeln('</table>')

        cgicommon.writeln('<p>')
        cgicommon.writeln('<input type="submit" name="playerteamsubmit" value="Set Teams" />')
        cgicommon.writeln('</p>')
        cgicommon.writeln('</form>')

        cgicommon.writeln('<h2>Automatic random team assignment</h2>')
        cgicommon.writeln('<form action="%s?tourney=%s" method="POST">' % (cgicommon.escape(baseurl, True), urllib.parse.quote_plus(tourneyname)))
        cgicommon.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname, True))
        cgicommon.writeln('<p>')
        cgicommon.writeln('Divide players by rating into groups of <input type="text" name="randomgroupsize" value="%d" size="5"> and randomly distribute each group as evenly as possible among the teams. Set to 0 to divide the whole player list randomly into teams, ignoring rating.' % random_group_size)
        cgicommon.writeln('</p>')
        cgicommon.writeln('<p>')
        cgicommon.writeln('<input type="submit" name="randomassignmentsubmit" value="Randomly assign players to teams" />')
        cgicommon.writeln('</p>')
        cgicommon.writeln('</form>')

        cgicommon.writeln('<h2>Clear teams</h2>')
        cgicommon.writeln('<form action="%s?tourney=%s" method="POST">' % (cgicommon.escape(baseurl, True), urllib.parse.quote_plus(tourneyname)))
        cgicommon.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname, True))
        cgicommon.writeln('<p>')
        cgicommon.writeln('Remove all players from their teams.')
        cgicommon.writeln('</p>')
        cgicommon.writeln('<p>')
        cgicommon.writeln('<input type="submit" name="clearteams" value="Clear team assignments"/>')
        cgicommon.writeln('</p>')
        cgicommon.writeln('</form>')
    #print '</p>'

cgicommon.writeln('</div>')
cgicommon.writeln('</body>')
cgicommon.writeln('</html>')
