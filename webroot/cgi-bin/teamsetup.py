#!/usr/bin/python

import sys
import cgi
import cgitb
import cgicommon
import os
import urllib
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
    # Get a list of all players, excluding patzers (players with a rating of 0)
    players = tourney.get_players()
    patzers = [ p for p in players if p.get_rating() <= 0 ]

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

    # Assign each patzer to no team
    for p in patzers:
        player_teams.append((p.get_name(), -1))
    
    # Return the map of players to team IDs
    return player_teams


print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/teamsetup.py";
form = cgi.FieldStorage();

tourneyname = form.getfirst("tourney")
player_team_submit = form.getfirst("playerteamsubmit")
random_assignment_submit = form.getfirst("randomassignmentsubmit")
random_group_size = int_or_none(form.getfirst("randomgroupsize"))
if random_group_size is None:
    random_group_size = 6

tourney = None
tourney_exception = None
player_teams_set = False
request_method = os.environ.get("REQUEST_METHOD", "")

cgicommon.print_html_head("Hangover Team Setup: " + str(tourneyname))

print "<body>"

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

print "<div class=\"mainpane\">";
print "<h1>Hangover Team Setup</h1>";

if tourneyname is None:
    print "<h1>Sloblock</h1>";
    print "<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>";
elif not tourney:
    print "<p>No valid tourney name specified</p>";
else:
    print '<p><a href="/cgi-bin/tourneysetup.py?tourney=%s">Back to tourney setup</a></p>' % (urllib.quote_plus(tourneyname));

    if player_teams_set:
        print "<p><strong>Teams set successfully.</strong></p>"
    elif tourney_exception:
        cgicommon.show_tourney_exception(e)

    #print '<p>'

    teams = tourney.get_teams()
    player_teams = sorted(tourney.get_player_teams(), key=lambda x : x[0].get_rating(), reverse=True)

    print '<h2>Teams</h2>'
    for team in teams:
        print '<p>'
        print '<font color="#%s">&bull;</font> %s' % (team.get_hex_colour(), team.get_name())
        player_name_list = [ cgi.escape(p.get_name()) for (p, pt) in player_teams if pt is not None and pt.get_id() == team.get_id() ]

        if player_name_list:
            print " (%d): %s" % (len(player_name_list), ", ".join(player_name_list));
        else:
            print " (no players)"
        print '</p>'

    print '<h2>Players</h2>'
    print '<form action="%s?tourney=%s" method="POST">' % (cgi.escape(baseurl, True), urllib.quote_plus(tourneyname))
    print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname, True)
    print '<table border="1">'
    print '<tr><th>Player</th>'
    print '<th>No team</th>'
    for team in teams:
        print '<th>%s</th>' % (cgi.escape(team.get_name()))
    print '</tr>'

    index = 0
    for player_team in player_teams:
        player = player_team[0]
        team = player_team[1]

        print '<tr>'
        print '<td align="left">%s<input type="hidden" name="player%d" value="%s" /></td>' % (cgi.escape(player.get_name()), index, cgi.escape(player.get_name()))

        # Radio button for "no team"
        print '<td align="center"><input type="radio" name="team%d" value="%d" %s /></td>' % (index, -1, "checked" if team is None else "")
        for t in teams:
            print '<td align="center" bgcolor="#%s"><input type="radio" name="team%d" value="%d" %s /></td>' % (t.get_hex_colour(), index, t.get_id(), "checked" if team is not None and team.get_id() == t.get_id() else "")
        print '</tr>'
        index += 1
    print '</table>'

    print '<p>'
    print '<input type="submit" name="playerteamsubmit" value="Set Teams" />'
    print '</p>'
    print '</form>'

    print '<h2>Automatic random team assignment</h2>'
    print '<form action="%s?tourney=%s" method="POST">' % (cgi.escape(baseurl, True), urllib.quote_plus(tourneyname))
    print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname, True)
    print '<p>'
    print 'Divide players by rating into groups of <input type="text" name="randomgroupsize" value="%d" size="5"> and randomly distribute each group as evenly as possible among the teams. Set to 0 to divide the whole player list randomly into teams, ignoring rating.' % random_group_size
    print '</p>'
    print '<p>'
    print '<input type="submit" name="randomassignmentsubmit" value="Yes please, do that" />'
    print '</p>'
    print '</form>'
    #print '</p>'

print '</div>'
print '</body>'
print '</html>'
