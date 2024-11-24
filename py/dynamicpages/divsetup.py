#!/usr/bin/python3

import htmlcommon
import countdowntourney

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;

def write_division_selector(response, player, div_names):
    response.writeln("<select name=\"player%(id)d_div\" id=\"player%(id)d_div\">" % { "id" : player.get_id() })
    for div_index in range(len(div_names)):
        response.writeln("<option value=\"%d\" %s>%s</option>" % (
            div_index,
            "selected" if (player.get_division() == div_index) else "",
            div_names[div_index]
        ))
    response.writeln("</select>")

def write_auto_assignment_controls(response, players, div_names):
    # Show some buttons which rewrite the table of players to set their
    # division assignments according to some simple rules.
    num_divisions = len(div_names)
    response.writeln("<p>All your players are in the top division. If you want to split the players into multiple divisions, the controls below will automatically set the drop-down boxes and re-order the table rows.</p>")
    response.writeln("<div>")
    num_players = len(players)
    num_players_per_div = (num_players + num_divisions - 1) // num_divisions
    num_players_remaining = num_players
    response.writeln("<table class=\"misctable\">")
    response.writeln("<tr><th>Division</th><th>Players</th></tr>")
    for div_index in range(num_divisions):
        response.writeln("<tr>")
        if div_index == num_divisions - 1:
            response.writeln("""
<td>%(divname)s</td>
<td>
<span id="autoassigndivplayercount%(divindex)d">%(lastdivcount)d</span>
</td>""" % {
                "divindex" : div_index,
                "lastdivcount" : num_players_remaining,
                "divname" : div_names[div_index]
            })
            num_players_remaining = 0
        else:
            response.writeln("""
<td>%(divname)s</td>
<td>
<input type="number" id="autoassigndivplayercount%(divindex)d"
name="autoassigndivplayercount%(divindex)d"
class="autoassigndivplayercounts"
style="font-size: 12pt;"
oninput="autoAssignDivPlayerCountChanged();"
min="0" max="%(numplayers)d" value="%(playersperdiv)d">
</td>""" % {
                "divindex" : div_index,
                "divname" : div_names[div_index],
                "numplayers" : num_players,
                "playersperdiv" : min(num_players_remaining, num_players_per_div)
            })
            num_players_remaining -= min(num_players_remaining, num_players_per_div)
        response.writeln("</tr>")
    response.writeln("</table>")
    response.writeln("<div>")
    response.writeln("""<p>Automatically assign players to divisions based on:</p>
<button type="button" onclick="autoAssignByRating();"
    title="Sort players by rating and put higher-rated players in higher divisions.">Rating</button>
<button type="button" onclick="autoAssignByStandingsPosition();"
    title="Sort players by standings position and put higher-ranked players in higher divisions.">Standings position</button>
<button type="button" onclick="autoAssignByPlayerID();"
    title="Sort players by Player ID, which is the order the players were initially entered in the player list, followed by any players added afterwards. Put lower player IDs in higher divisions.">Player ID</button>
""")
    response.writeln("</div>")

    response.writeln("<p>This will not save the new assignments. Review them below and accept them with the \"Save new division details\" button.</p>")


def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourneyname = tourney.name

    htmlcommon.print_html_head(response, "Division Setup: " + str(tourneyname));

    response.writeln("""
<body onload="hide_div_renames();">
<script>
function show_div_rename(div) {
    buttondiv = document.getElementById("divrenamebutton" + div.toString());
    renamediv = document.getElementById("divrenamecontrols" + div.toString());
    textbox = document.getElementById("newdivnameinput" + div.toString())
    textbox.disabled = false;
    buttondiv.style.display = "none";
    renamediv.style.display = "inline";
    textbox.focus();
    textbox.select();
}

function hide_div_rename(div) {
    buttondiv = document.getElementById("divrenamebutton" + div.toString());
    renamediv = document.getElementById("divrenamecontrols" + div.toString());
    textbox = document.getElementById("newdivnameinput" + div.toString())
    textbox.disabled = true;
    buttondiv.style.display = "inline";
    renamediv.style.display = "none";
}

function hide_div_renames() {
    buttons = document.getElementsByClassName("divrenamebutton");
    renames = document.getElementsByClassName("divrenamecontrols");
    if (buttons != null) {
        for (var i = 0; i < buttons.length; ++i) {
            buttons[i].style.display = "inline";
        }
    }

    if (renames != null) {
        for (var i = 0; i < renames.length; ++i) {
            renames[i].style.display = "none";
        }
    }
}
</script>
""")

    htmlcommon.show_sidebar(response, tourney)

    response.writeln("<div class=\"mainpane\">");
    response.writeln("<h1>Division Setup</h1>");

    name_to_position = dict()
    name_to_div_position = dict()
    num_divisions = tourney.get_num_divisions()
    for s in tourney.get_standings():
        name_to_position[s.name] = s.position

    if request_method == "POST":
        # Have we been asked to change the number of divisions?
        if "setdivcount" in form:
            div_count = int_or_none(form.getfirst("divcount"))
            if div_count is None or div_count < 1 or div_count > countdowntourney.MAX_DIVISIONS:
                htmlcommon.show_error_text(response, "Invalid number of divisions: must be between 1 and %d." % (countdowntourney.MAX_DIVISIONS))
            else:
                players_moved = tourney.set_num_divisions(div_count)
                text = "Number of divisions set to %d." % (div_count)
                if players_moved:
                    if div_count > 1:
                        text += " %d player%s promoted to %s." % (
                                players_moved,
                                "" if players_moved == 1 else "s",
                                tourney.get_division_name(div_count - 1)
                        )
                    else:
                        text += " All players are now in the same division."
                htmlcommon.show_success_box(response, text)

        # setdivplayers: main submit button. User may have changed the division
        # associated with one or more players, and/or may have changed the
        # division names.
        if "setdivplayers" in form:
            players = tourney.get_players()
            num_divisions = tourney.get_num_divisions()
            previous_div_names = [ tourney.get_division_name(div_index) for div_index in range(num_divisions) ]
            num_divisions_renamed = 0
            div_rename_old_name = None
            div_rename_new_name = None

            # Deal with division renames first
            for div_index in range(num_divisions):
                new_name = form.getfirst("newdivname%d" % (div_index), "").strip()
                if new_name and new_name != previous_div_names[div_index]:
                    tourney.set_division_name(div_index, new_name)
                    div_rename_old_name = previous_div_names[div_index]
                    div_rename_new_name = new_name
                    num_divisions_renamed += 1

            # Now deal with player/division reassignments
            num_players_reassigned = 0
            first_player_name_reassigned = None
            first_player_name_new_division = None
            for p in players:
                player_id = p.get_id()
                player_current_division = p.get_division()
                input_name = "player%d_div" % (player_id)
                player_new_division = int_or_none(form.getfirst(input_name))
                if player_new_division is None or player_new_division < 0 or player_new_division >= num_divisions:
                    continue
                if player_new_division != player_current_division:
                    tourney.set_player_division(p.get_name(), player_new_division)
                    num_players_reassigned += 1
                    if first_player_name_reassigned is None:
                        first_player_name_reassigned = p.get_name()
                        first_player_name_new_division = tourney.get_division_name(player_new_division)

            # Finally, announce what we did
            if num_divisions_renamed == 1:
                htmlcommon.show_success_box(response, "Successfully renamed \"%s\" to \"%s\"." % (div_rename_old_name, div_rename_new_name))
            elif num_divisions_renamed > 1:
                htmlcommon.show_success_box(response, "Successfully renamed %d divisions." % (num_divisions_renamed))

            if num_players_reassigned == 1:
                htmlcommon.show_success_box(response, "Successfully reassigned %s to %s." % (first_player_name_reassigned, first_player_name_new_division))
            elif num_players_reassigned > 1:
                htmlcommon.show_success_box(response, "Successfully reassigned %d players to new divisions." % (num_players_reassigned))


    players = tourney.get_players()
    num_divisions = tourney.get_num_divisions()
    num_games = tourney.get_num_games()

    # Constants needed for event handlers for automatic division assignment.
    response.writeln("""
<script>
const numDivisions = %(numdivisions)d;
const numPlayers = %(numplayers)d;
""" % {
        "numdivisions" : num_divisions,
        "numplayers" : len(players)
    })

    response.writeln("const playerIdToRating = {")
    response.writeln(", ".join(["%d: %f" % (p.get_id(), p.get_rating()) for p in players ]))
    response.writeln("};")
    response.writeln("const playerIdToStandingsPosition = {")
    response.writeln(", ".join(["%d: %d" % (p.get_id(), name_to_position.get(p.get_name())) for p in players ]))
    response.writeln("};")

    # Event handlers for changing number of players per division, reassigning
    # divisions by rating/standings/etc.
    response.writeln("""
function autoAssignDivPlayerCountChanged() {
    /* Sum the values of all the number-of-players-in-division edit boxes */
    let inputs = document.getElementsByClassName("autoassigndivplayercounts");
    let sumOfInputs = 0;
    for (let i = 0; i < inputs.length; i++) {
        let value = parseInt(inputs[i].value);
        if (!isNaN(value)) {
            sumOfInputs += value;
        }
    }
    let lastDivisionCount = numPlayers - sumOfInputs;
    if (lastDivisionCount < 0) {
        lastDivisionCount = 0;
    }
    let lastDiv = document.getElementById("autoassigndivplayercount" + (numDivisions - 1).toString());
    if (lastDiv) {
        lastDiv.innerText = lastDivisionCount.toString();
    }
}

function autoAssign(playerIdToSortKey, reverse=false) {
    let table = document.getElementById("div0table");
    let rows = table.getElementsByTagName("TR");
    let playerIds = [];
    let playerIdToRow = {};
    let playersRemainingEachDivision = [];
    let rowParentElement = null;

    for (let i = 0; i < rows.length; i++) {
        if (rows[i].getAttribute("data-player-id")) {
            let playerId = parseInt(rows[i].getAttribute("data-player-id"));
            playerIds.push(playerId);
            playerIdToRow[playerId] = rows[i];
            rowParentElement = rows[i].parentElement;
        }
    }

    if (rowParentElement) {
        for (let i = 0; i < playerIds.length; i++) {
            rowParentElement.removeChild(playerIdToRow[playerIds[i]]);
        }
    }

    /* How many players in each division? */
    for (let i = 0; i < numDivisions; i++) {
        let count;
        let element = document.getElementById("autoassigndivplayercount" + i.toString());
        if (i == numDivisions - 1) {
            /* Read the non-number-input box */
            count = parseInt(element.innerText);
        }
        else {
            /* Read the number input box */
            count = parseInt(element.value);
        }
        playersRemainingEachDivision.push(count);
    }

    /* Sort the players in order */
    if (playerIdToSortKey == null) {
        playerIds.sort(function(x, y) { return x - y; });
    }
    else if (reverse) {
        playerIds.sort(function(x, y) {
            return playerIdToSortKey[y] - playerIdToSortKey[x];
        });
    }
    else {
        playerIds.sort(function(x, y) {
            return playerIdToSortKey[x] - playerIdToSortKey[y];
        });
    }

    /* Now put the rows back in the table in the new order */
    for (let i = 0; i < playerIds.length; i++) {
        rowParentElement.appendChild(playerIdToRow[playerIds[i]]);
    }

    /* Set each player's drop-down box to the correct division */
    let divIndex = 0;
    for (let i = 0; i < playerIds.length; i++) {
        let dropDown = document.getElementById("player" + playerIds[i].toString() + "_div");
        /* If this division already has the right number of players in it,
           move on to the next division */
        while (divIndex < numDivisions && playersRemainingEachDivision[divIndex] <= 0) {
            divIndex++;
        }

        /* If we can't find a suitable division, default to the last one */
        if (divIndex >= numDivisions) {
            divIndex = numDivisions - 1;
        }
        dropDown.selectedIndex = divIndex;
        playersRemainingEachDivision[divIndex]--;
    }
}

function autoAssignByPlayerID() {
    autoAssign(null);
}

function autoAssignByRating() {
    autoAssign(playerIdToRating, true);
}

function autoAssignByStandingsPosition() {
    autoAssign(playerIdToStandingsPosition);
}
</script>
""")

    response.writeln("<h2>Number of divisions</h2>")
    if num_divisions <= 1:
        response.writeln("<p>This tourney is not currently divisioned. All the players are in the same division.</p>")
        response.writeln("<p>If you create more divisions, they will initially be empty. You will be able to add players to the new divisions afterwards.</p>")
    else:
        response.writeln("<p>This tourney currently has %d divisions.</p>" % (num_divisions))
        response.writeln("<p>If you increase the number below, empty divisions will be created. If you decrease it, lower divisions will be removed and their players will be promoted to the lowest still-existing division.</p>")

    response.writeln("""
<form method="POST">
<label for="divcount">Number of divisions: <input type="number" min="1" max="%(maxdivs)d" name="divcount" id="divcount" value="%(numdivs)d"></label>
<div style="margin-top: 20px; margin-bottom: 20px;">
<input type="submit" name="setdivcount" class="bigbutton" value="Set number of divisions">
</div>
</form>
""" % {
        "numdivs" : num_divisions,
        "maxdivs" : countdowntourney.MAX_DIVISIONS
    })

    response.writeln("<hr />")

    for div_index in range(num_divisions):
        for s in tourney.get_standings(div_index):
            name_to_div_position[s.name] = s.position

    div_players = [ [] for i in range(num_divisions) ]
    for p in players:
        div_players[p.get_division()].append(p)

    div_active_player_count = [ len([p for p in div_players[div_index] if not p.is_withdrawn()]) for div_index in range(num_divisions) ]
    div_withdrawn_player_count = [ len([p for p in div_players[div_index] if p.is_withdrawn()]) for div_index in range(num_divisions) ]

    div_names = [ tourney.get_division_name(div_index) for div_index in range(num_divisions) ]

    response.writeln("<h2>Division names and players</h2>")
    if num_games > 0:
        htmlcommon.show_warning_box(response, "The tourney has already started. Reassigning player divisions will only take effect for rounds whose fixtures have yet to be generated. Existing games will not be changed.")

    if num_divisions > 1 and len(div_players[0]) == len(players):
        # All the players are in the top division but there is more than
        # one division. Offer to set the drop-down boxes to assign the
        # players by rating, or by standings position, or by player ID.
        write_auto_assignment_controls(response, players, div_names)

    # Start of division/player assignment form
    response.writeln("<form method=\"POST\">")

    # Show a table for each division, containing its players
    players_in_earlier_divisions = 0
    for div_index in range(0, num_divisions):
        div_name = tourney.get_division_name(div_index)
        response.writeln("<h3>%s</h3>" % (htmlcommon.escape(div_name)))
        if len(div_players[div_index]) == 0:
            response.writeln("<p>There are no players in this division.</p>")
            continue

        response.writeln("""
<div class="divrenamecontrols" id="divrenamecontrols%(divindex)d">
<input type="text" id="newdivnameinput%(divindex)d" name="newdivname%(divindex)d" value="%(divname)s" disabled>
<input type="button" name="canceldivrename%(divindex)d" value="Cancel" onclick="hide_div_rename(%(divindex)d);">
</div>
<div class="divrenamebutton" id="divrenamebutton%(divindex)d">
<input type="button" name="showdivrename%(divindex)d" value="Rename..." onclick="show_div_rename(%(divindex)d);">
</div>""" % {
            "divindex" : div_index,
            "divname" : div_names[div_index]
        })
        response.write("<p>")
        response.write("%d active player%s" % (div_active_player_count[div_index], "" if div_active_player_count[div_index] == 1 else "s"))
        if div_withdrawn_player_count[div_index] > 0:
            response.write(", %d withdrawn" % (div_withdrawn_player_count[div_index]))
        response.writeln(".</p>")

        response.writeln("""<table class="misctable" id="div%dtable">
<tr>
<th rowspan="2">Name</th>
<th rowspan="2">Rating</th>
<th colspan="2">Position</th>
%s
</tr>
<tr>
<th>Division</th><th>Overall</th>
</tr>""" % (div_index, "<th rowspan=\"2\">Change division</th>" if num_divisions > 1 else ""))
        # Write one table row per player in this division
        for p in div_players[div_index]:
            # data-player-id attribute is used by the auto division assigner
            # functions to correctly re-order the rows
            response.writeln("<tr data-player-id=\"%d\">" % (p.get_id()))
            response.writeln("<td class=\"text\">%s%s</td>" % (htmlcommon.player_to_link(p, tourney.get_name()), " (withdrawn)" if p.is_withdrawn() else ""))
            response.writeln("<td class=\"number\">%g</td>" % (p.get_rating()))
            response.writeln("<td class=\"number\">%d</td>" % (name_to_div_position[p.get_name()]))
            response.writeln("<td class=\"number\">%d</td>" % (players_in_earlier_divisions + name_to_div_position[p.get_name()]))
            if num_divisions > 1:
                response.writeln("<td class=\"control\">")
                write_division_selector(response, p, div_names)
                response.writeln("</td>")
            response.writeln("</tr>")
        response.writeln("</table>")
        players_in_earlier_divisions += len(div_players[div_index])

    response.writeln("<div style=\"margin-top: 30px; margin-bottom: 30px;\">")
    response.writeln("<input type=\"submit\" name=\"setdivplayers\" class=\"bigbutton\" value=\"Save new division details\">")
    response.writeln("</div>")

    response.writeln("</form>")

    response.writeln("</div>")
    response.writeln("</body>")
    response.writeln("</html>")
