#!/usr/bin/python3

import random

import htmlcommon
import htmldialog
import countdowntourney
import time

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;

# Very important functions.
# Unlike the C structure, tm_wday == 0 means Monday and 6 means Sunday, and
# tm_mon counts from 1 and not 0.
def is_today_last_sunday_in_january(tm):
    return tm.tm_mon == 1 and tm.tm_mday >= 25 and tm.tm_wday == 6

def is_tomorrow_last_sunday_in_january(tm):
    return tm.tm_mon == 1 and tm.tm_mday >= 24 and tm.tm_mday <= 30 and tm.tm_wday == 5

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
            player_teams.append((player.get_id(), team_id))
            team_counts[team_id] += 1

        pos += group_size

    # Assign each prune to no team
    for p in prunes:
        player_teams.append((p.get_id(), -1))

    # Return the map of player IDs to team IDs
    return player_teams


def write_radio_button(response, player_id, team_id, checked, hex_colour):
    response.writeln("""
<td class="control" style="padding: 0; %(style)s">
<label for="player%(playerid)d_team%(teamid)d" style="min-width: 70px;" class="fillcontainer">
<input type="radio" id="player%(playerid)d_team%(teamid)d" style="margin: 5px;" name="player%(playerid)d" value="%(teamid)d" %(checked)s>
</label>
</td>""" % {
        "style" : ("background-color: #" + hex_colour + ";") if hex_colour is not None else "",
        "playerid" : player_id,
        "teamid" : team_id,
        "checked" : "checked" if checked else ""
    })

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourneyname = tourney.get_name()
    player_team_submit = form.getfirst("playerteamsubmit")
    random_assignment_submit = form.getfirst("randomassignmentsubmit")
    clear_teams_submit = form.getfirst("clearteams")
    random_group_size = int_or_none(form.getfirst("randomgroupsize"))
    if random_group_size is None:
        random_group_size = 6

    tourney_exception = None
    player_teams_set = False

    htmlcommon.print_html_head(response, "Hangover Team Setup: " + str(tourneyname))

    response.writeln("<body>")

    response.writeln("<script>")
    response.writeln(htmldialog.DIALOG_JAVASCRIPT)
    response.writeln("""
function showRandomAssignmentDialogBox() {
    let randomGroupSizeBox = document.getElementById("randomgroupsize");
    let randomGroupSize = 6;
    if (randomGroupSizeBox) {
        randomGroupSize = parseInt(randomGroupSizeBox.value);
        if (isNaN(randomGroupSize)) {
            randomGroupSize = 6;
        }
    }
    let p1 = document.createElement("P");
    let p2 = document.createElement("P");
    p1.innerHTML = "Players have already been assigned teams for this tourney. If you proceed, the players will be re-randomised into teams, losing the existing team assignments.";
    p2.innerHTML = "Are you sure you want to reassign players to random teams?";
    dialogBoxShow("randomassignmentdialog",
        "Discard existing team assignments?", "Randomise teams", "Cancel",
        "POST", null, "randomassignmentsubmit", [p1, p2],
        { "randomgroupsize" : randomGroupSize.toString() });
}

function showClearTeamsDialogBox() {
    let p1 = document.createElement("P");
    let p2 = document.createElement("P");
    p1.innerHTML = "This will lose all existing team assignments. No players will be in any team.";
    p2.innerHTML = "Are you sure you want to clear all existing team assignments?";
    dialogBoxShow("clearteamsdialog", "Discard existing team assignments?",
        "Clear team assignments", "Cancel", "POST", null, "clearteams",
        [p1, p2]);
}
""")
    response.writeln("</script>")

    htmlcommon.show_sidebar(response, tourney);

    if request_method == "POST":
        player_teams = None
        if player_team_submit:
            # User set their own player-to-team assignments
            player_teams = []
            for name in form:
                # Find all the form parameters that look like player<number>
                if name.startswith("player"):
                    try:
                        player_id = int(name[6:])
                        team_id = int_or_none(form.getfirst(name))
                        player_teams.append((player_id, team_id))
                    except ValueError:
                        pass
        elif random_assignment_submit:
            # User asked for random team assignment
            if random_group_size is None:
                random_group_size = 0
            player_teams = random_team_assignment(tourney, random_group_size)
        elif clear_teams_submit:
            # User asked to clear team assignments
            players = tourney.get_players()
            player_teams = [ (p.get_id(), None) for p in players ]

        if player_teams:
            try:
                tourney.set_player_teams(player_teams)
                player_teams_set = True
            except countdowntourney.TourneyException as e:
                tourney_exception = e

    response.writeln("<div class=\"mainpane\">");
    response.writeln("<h1>Hangover Team Setup</h1>");

    num_players = len(tourney.get_players())

    if player_teams_set:
        htmlcommon.show_success_box(response, "Teams set successfully.")
    elif tourney_exception:
        htmlcommon.show_tourney_exception(response, tourney_exception)
    elif num_players > 0:
        # Give the user an appropriate context-sensitive greeting
        tm = time.localtime(time.time())
        if is_today_last_sunday_in_january(tm):
            response.writeln("<p>Hi Ben!</p>")
        elif is_tomorrow_last_sunday_in_january(tm):
            response.writeln("<p>Isn't this supposed to be tomorrow?</p>")
        else:
            response.writeln("<p>It's not the usual time of year for this, but what do I care?</p>")

    # Fetch the current list of teams and players from tourney
    teams = tourney.get_teams()
    players = sorted(tourney.get_players(), key=lambda x : x.get_rating(), reverse=True)

    team_assignments_exist = False
    for player in players:
        if player.get_team() is not None:
            team_assignments_exist = True
            break

    if num_players == 0:
        response.writeln("<p>This tourney doesn't have any players, so you can't specify teams yet.</p>")
        response.writeln('<p><a href="/atropine/%s/tourneysetup">Back to Tourney Setup</a></p>' % (htmlcommon.escape(tourneyname)));
    else:
        # For each team, list its players
        response.writeln('<h2>Teams</h2>')
        for team in teams:
            response.writeln('<p>')
            response.writeln(htmlcommon.make_team_dot_html(team) + " " + htmlcommon.escape(team.get_name()))
            player_name_list = [ htmlcommon.escape(p.get_name()) for p in players if p.get_team_id() is not None and p.get_team_id() == team.get_id() ]

            if player_name_list:
                response.writeln(" (%d): %s" % (len(player_name_list), ", ".join(player_name_list)));
            else:
                response.writeln(" (no players)")
            response.writeln('</p>')

        # Show a table of players, with radio buttons to indicate/change which
        # team those players are on.
        response.writeln('<h2>Players</h2>')
        response.writeln('<form method="POST">')
        response.writeln('<table class="misctable">')
        response.writeln('<tr><th>Player</th>')
        response.writeln('<th>No team</th>')
        for team in teams:
            response.writeln('<th>%s</th>' % (htmlcommon.escape(team.get_name())))
        response.writeln('</tr>')

        for player in players:
            response.writeln('<tr>')
            response.writeln('<td class="text">%s</td>' % (htmlcommon.escape(player.get_name())))

            # Radio button for "no team"
            write_radio_button(response, player.get_id(), -1, player.get_team() is None, "dddddd")
            for t in teams:
                # Radio button for team t
                write_radio_button(response, player.get_id(), t.get_id(),
                        player.get_team() is not None and t.get_id() == player.get_team_id(), t.get_hex_colour())
            response.writeln('</tr>')

        response.writeln('</table>')

        response.writeln('<p>')
        response.writeln('<input type="submit" name="playerteamsubmit" value="Set Teams" />')
        response.writeln('</p>')
        response.writeln('</form>')

        response.writeln('<h2>Automatic random team assignment</h2>')

        # If there are teams already assigned, the random team assignment
        # button brings up an "are you sure" dialog box. Otherwise, it simply
        # submits the form and randomises the teams.
        if not team_assignments_exist:
            response.writeln('<form method="POST">')
        response.writeln('<p>')
        response.writeln('Divide players by rating into groups of <input type="number" name="randomgroupsize" id="randomgroupsize" value="%d" min="0" /> and randomly distribute each group as evenly as possible among the teams. Set to 0 to divide the whole player list randomly into teams, ignoring rating.' % random_group_size)
        response.writeln('</p>')
        response.writeln('<p>')
        if team_assignments_exist:
            response.writeln('<button name="randomassignmentsubmit" onclick="showRandomAssignmentDialogBox();">Randomly assign players to teams</button>')
        else:
            response.writeln('<input type="submit" name="randomassignmentsubmit" value="Randomly assign players to teams" />')
        response.writeln('</p>')

        if not team_assignments_exist:
            response.writeln('</form>')

        if team_assignments_exist:
            response.writeln('<h2>Clear teams</h2>')
            response.writeln('<p>')
            response.writeln('Remove all players from their teams.')
            response.writeln('</p>')
            response.writeln('<p>')
            response.writeln('<button name="clearteams" onclick="showClearTeamsDialogBox();">Clear team assignments</button>')
            response.writeln('</p>')

    response.writeln('</div>')

    # Hidden dialog boxes for random team assignment and clear team confirmation
    response.writeln(htmldialog.get_html("randomassignmentdialog"))
    response.writeln(htmldialog.get_html("clearteamsdialog"))

    response.writeln('</body>')
    response.writeln('</html>')
