#!/usr/bin/python3

import cgicommon
import urllib.request, urllib.parse, urllib.error
import random
import countdowntourney

baseurl = "/cgi-bin/teamsetup.py"

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


def handle(httpreq, response, tourney, request_method, form, query_string):
    tourneyname = tourney.get_name()
    player_team_submit = form.getfirst("playerteamsubmit")
    random_assignment_submit = form.getfirst("randomassignmentsubmit")
    clear_teams_submit = form.getfirst("clearteams")
    random_group_size = int_or_none(form.getfirst("randomgroupsize"))
    if random_group_size is None:
        random_group_size = 6

    tourney_exception = None
    player_teams_set = False

    cgicommon.print_html_head(response, "Hangover Team Setup: " + str(tourneyname))

    response.writeln("<body>")

    cgicommon.show_sidebar(response, tourney);

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

    response.writeln("<div class=\"mainpane\">");
    response.writeln("<h1>Hangover Team Setup</h1>");

    num_players = len(tourney.get_players())

    if player_teams_set:
        cgicommon.show_success_box(response, "Teams set successfully.")
    elif tourney_exception:
        cgicommon.show_tourney_exception(response, tourney_exception)

    teams = tourney.get_teams()
    player_teams = sorted(tourney.get_player_teams(), key=lambda x : x[0].get_rating(), reverse=True)

    if num_players == 0:
        response.writeln("<p>This tourney doesn't have any players, so you can't specify teams yet.</p>")
        response.writeln('<p><a href="/cgi-bin/tourneysetup.py?tourney=%s">Back to Tourney Setup</a></p>' % (urllib.parse.quote_plus(tourneyname)));
    else:
        response.writeln('<h2>Teams</h2>')
        for team in teams:
            response.writeln('<p>')
            response.writeln(cgicommon.make_team_dot_html(team) + " " + cgicommon.escape(team.get_name()))
            player_name_list = [ cgicommon.escape(p.get_name()) for (p, pt) in player_teams if pt is not None and pt.get_id() == team.get_id() ]

            if player_name_list:
                response.writeln(" (%d): %s" % (len(player_name_list), ", ".join(player_name_list)));
            else:
                response.writeln(" (no players)")
            response.writeln('</p>')

        response.writeln('<h2>Players</h2>')
        response.writeln('<form action="%s?tourney=%s" method="POST">' % (cgicommon.escape(baseurl, True), urllib.parse.quote_plus(tourneyname)))
        response.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname, True))
        response.writeln('<table class="misctable">')
        response.writeln('<tr><th>Player</th>')
        response.writeln('<th>No team</th>')
        for team in teams:
            response.writeln('<th>%s</th>' % (cgicommon.escape(team.get_name())))
        response.writeln('</tr>')

        index = 0
        for player_team in player_teams:
            player = player_team[0]
            team = player_team[1]

            response.writeln('<tr>')
            response.writeln('<td class="text">%s<input type="hidden" name="player%d" value="%s" /></td>' % (cgicommon.escape(player.get_name()), index, cgicommon.escape(player.get_name())))

            # Radio button for "no team"
            response.writeln('<td class="control"><input type="radio" name="team%d" value="%d" %s /></td>' % (index, -1, "checked" if team is None else ""))
            for t in teams:
                response.writeln('<td class="control" style="background-color: #%s;"><input type="radio" name="team%d" value="%d" %s /></td>' % (t.get_hex_colour(), index, t.get_id(), "checked" if team is not None and team.get_id() == t.get_id() else ""))
            response.writeln('</tr>')
            index += 1
        response.writeln('</table>')

        response.writeln('<p>')
        response.writeln('<input type="submit" name="playerteamsubmit" value="Set Teams" />')
        response.writeln('</p>')
        response.writeln('</form>')

        response.writeln('<h2>Automatic random team assignment</h2>')
        response.writeln('<form action="%s?tourney=%s" method="POST">' % (cgicommon.escape(baseurl, True), urllib.parse.quote_plus(tourneyname)))
        response.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname, True))
        response.writeln('<p>')
        response.writeln('Divide players by rating into groups of <input type="number" name="randomgroupsize" value="%d" min="0" /> and randomly distribute each group as evenly as possible among the teams. Set to 0 to divide the whole player list randomly into teams, ignoring rating.' % random_group_size)
        response.writeln('</p>')
        response.writeln('<p>')
        response.writeln('<input type="submit" name="randomassignmentsubmit" value="Randomly assign players to teams" />')
        response.writeln('</p>')
        response.writeln('</form>')

        response.writeln('<h2>Clear teams</h2>')
        response.writeln('<form action="%s?tourney=%s" method="POST">' % (cgicommon.escape(baseurl, True), urllib.parse.quote_plus(tourneyname)))
        response.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname, True))
        response.writeln('<p>')
        response.writeln('Remove all players from their teams.')
        response.writeln('</p>')
        response.writeln('<p>')
        response.writeln('<input type="submit" name="clearteams" value="Clear team assignments"/>')
        response.writeln('</p>')
        response.writeln('</form>')

    response.writeln('</div>')
    response.writeln('</body>')
    response.writeln('</html>')
