#!/usr/bin/python3

import cgi
import cgitb
import cgicommon
import sys
import urllib.request, urllib.parse, urllib.error
import os

cgitb.enable();

cgicommon.set_module_path();
import countdowntourney

HTML_TICK_SYMBOL = '<span style="background-color: hsl(120, 60%, 90%); color: green; padding: 2px;">✓</span>'
HTML_CROSS_SYMBOL = '<span style="background-color: hsl(0, 80%, 20%); color: white; padding: 2px;">&#x2716;</span>'
HTML_TRASHCAN_SYMBOL = "&#x1F5D1;"

# Number of rows in the table of player buttons. If there are more than
# 4 * ROWS_PER_COLUMN players, we may add more rows than this per column,
# but never more than four columns.
ROWS_PER_COLUMN = 12

def int_or_zero(s):
    if s is None:
        return 0
    try:
        return int(s)
    except ValueError:
        return 0

def int_or_none(s):
    if s is None:
        return None
    try:
        return int(s)
    except:
        return None

# When making changes, one or other of these might be filled up with exceptions
# or strings explaining what changed. When we present the page, we'll display
# them.
exceptions_to_show = []
notifications = []

# Functions for stuff we do when certain submit buttons are pressed...
def withdraw_player(tourney, form):
    player_name = form.getfirst("playername")
    if not player_name:
        raise countdowntourney.TourneyException("Withdraw player: no player name given? This is a bug.")
    tourney.withdraw_player(player_name)

def reinstate_player(tourney, form):
    player_name = form.getfirst("playername")
    if not player_name:
        raise countdowntourney.TourneyException("Reinstate player: no player name given? This is a bug.")
    tourney.unwithdraw_player(player_name)

def add_new_player(tourney, form):
    try:
        cgicommon.add_new_player_from_form(tourney, form)
        notifications.append("Added new player %s." % (form.getfirst("setname")))
    except countdowntourney.TourneyException as e:
        exceptions_to_show.append(e)

def withdraw_all(tourney, form):
    try:
        tourney.withdraw_all_players()
    except countdowntourney.TourneyException as e:
        exceptions_to_show.append(e)

def reinstate_all(tourney, form):
    try:
        tourney.unwithdraw_all_players()
    except countdowntourney.TourneyException as e:
        exceptions_to_show.append(e)

def delete_withdrawn(tourney, form):
    try:
        count = tourney.delete_all_withdrawn_players()
        notifications.append("%d withdrawn player%s deleted." % (count, "" if count == 1 else "s"))
    except countdowntourney.TourneyException as e:
        exceptions_to_show.append(e)

def delete_player(tourney, form):
    try:
        player_id = int_or_none(form.getfirst("popupsubmitarg"))
        if player_id is not None:
            player_name = tourney.get_player_name(player_id)
            tourney.delete_player(player_name)
            notifications.append("%s has been deleted." % (player_name))
    except countdowntourney.TourneyException as e:
        exceptions_to_show.append(e)

# Write out HTML for the popup box we show when the user presses something
# we want them to confirm they're sure about. This form will have the supplied
# query string and hidden inputs.
# Most elements of this form get tinkered with at runtime in JavaScript,
# such as the submit button name, the title and body text, and the value of
# the hidden argument popupsubmitarg.
def generate_hidden_confirm_box(tourney, form_query_string, hidden_inputs):
    hidden_inputs_html = [
        "<input type=\"hidden\" name=\"%s\" value=\"%s\">" % (cgicommon.escape(name), cgicommon.escape(str(value))) for (name, value) in hidden_inputs
    ]
    hidden_inputs_html.append("<input type=\"hidden\" name=\"tourney\" value=\"%s\">" % (cgicommon.escape(tourney.get_name())))
    cgicommon.writeln("""
<div id="popupdiv" style="display: none;">
    <div class="popupwindow">
        <h2 id="popuptitle"></h2>
        <p id="popupbody"></p>
        <div class="popupwindowcontrols">
            <form action="{baseurl}?{form_query_string}" method="POST">
                {hidden_inputs}
                <input type="hidden" name="popupsubmitarg" value="" id="popupsubmitarg">
                <input type="submit" class="bigbutton" id="popupsubmit" name="popupsubmit" value="OK">
                <button type="button" onclick="killPopup();" class="bigbutton">Cancel</button>
            </form>
        </div>
    </div>
</div>
""".format(baseurl=baseurl, form_query_string=form_query_string,
    hidden_inputs="\n".join(hidden_inputs_html))
    )

# Write out a load of JavaScript functions we're going to need. This is mainly
# for the buttons which cause a popup box to appear asking the user if they're
# sure they want to do something.
def generate_scripts(tourney):
    players = tourney.get_players()
    active_players = [ p for p in players if not p.is_prune() and not p.is_withdrawn() ]
    withdrawn_players = [ p for p in players if not p.is_prune() and p.is_withdrawn() ]
    num_games = tourney.get_num_games()

    script = """
<script>
function killPopup() {
    let popupWindow = document.getElementById("popupdiv");
    if (popupWindow) {
        popupWindow.style.display = "none";
    }
}

function initPage() {
    let popupDiv = document.getElementById("popupdiv");
    popupDiv.addEventListener("click", function(e) {
        if (e.target.id === "popupdiv") {
            killPopup();
        }
    });
}

function escapeHTML(str) {
    if (str === null) {
        return "(null)";
    }
    else if (str === undefined) {
        return "(undefined)";
    }
    return str.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#039;");
}

function confirmBox(title, html, submitName, argument) {
    let popupWindow = document.getElementById("popupdiv");
    if (popupWindow) {
        popupWindow.style.display = "block";
    }
    let popupTitle = document.getElementById("popuptitle");
    if (popupTitle) {
        popupTitle.innerText = title;
    }
    let popupBody = document.getElementById("popupbody");
    if (popupBody) {
        popupBody.innerHTML = html;
    }
    if (argument != null) {
        let popupSubmitArg = document.getElementById("popupsubmitarg");
        if (popupSubmitArg) {
            popupSubmitArg.value = argument.toString();
        }
    }
    let popupSubmit = document.getElementById("popupsubmit");
    popupSubmit.name = submitName;
}

function showWithdrawAllConfirm() {
    confirmBox("Are you sure?", "You are about to set %(num_active_players)d active players as withdrawn.", "withdrawallsubmit", null);
}

function showReinstateAllConfirm() {
    confirmBox("Are you sure?", "You are about to set %(num_withdrawn_players)d withdrawn players as active.", "reinstateallsubmit", null);
}

function showDeleteWithdrawnConfirm() {
    confirmBox("Are you sure?", "You are about to delete %(num_withdrawn_players)d withdrawn players. If you want to add them again you will have to add each player individually. %(delete_gamed_player_warning)s", "deletewithdrawnsubmit", null);
}

function showDeletePlayerConfirm(playerId, playerName) {
    confirmBox("Delete player?", "Are you sure you want to delete the player <span style=\\"font-weight: bold;\\">" + playerName + "</span>?", "deleteplayersubmit", playerId);
}
</script>
""" % {"num_active_players" : len(active_players),
        "num_withdrawn_players" : len(withdrawn_players),
        "delete_gamed_player_warning" : "Note that any players who have had a game created for them will <em>not</em> be deleted." if num_games > 0 else "" }
    cgicommon.writeln(script)



# START HERE

cgicommon.writeln("Content-Type: text/html; charset=utf-8")
cgicommon.writeln("")

baseurl = "/cgi-bin/checkin.py"
form = cgi.FieldStorage()
tourneyname = form.getfirst("tourney")
hide_help = int_or_zero(form.getfirst("hidehelp"))

tourney = None
if tourneyname is None:
    fatal_error("No tourney name specified.")

try:
    tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir)
except countdowntourney.TourneyException as e:
    fatal_exception(e, None)

request_method = os.environ.get("REQUEST_METHOD", "")

if request_method == "POST":
    # If we've got a POST, we probably need to change something. Work out
    # which submit button was pressed.
    try:
        if "newplayersubmit" in form:
            add_new_player(tourney, form)
        elif "withdrawsubmit" in form:
            withdraw_player(tourney, form)
        elif "reinstatesubmit" in form:
            reinstate_player(tourney, form)
        elif "withdrawallsubmit" in form:
            withdraw_all(tourney, form)
        elif "reinstateallsubmit" in form:
            reinstate_all(tourney, form)
        elif "deletewithdrawnsubmit" in form:
            delete_withdrawn(tourney, form)
        elif "deleteplayersubmit" in form:
            delete_player(tourney, form)
    except countdowntourney.TourneyException as e:
        exceptions_to_show.append(e)


# Now present the current state of the player list to the user...

cgicommon.print_html_head("Player Check-In")

cgicommon.writeln("<body onload=\"initPage();\">")
cgicommon.assert_client_from_localhost()

# Each submit button has to preserve the settings such as tourney=... and
# hidehelp=... so building this query string is useful.
form_query_string = "tourney=%s" % (urllib.parse.quote_plus(tourneyname))
if hide_help:
    form_query_string += "&hidehelp=1"

# Write out our (initially invisible) popup box and the JavaScript to go with it
generate_hidden_confirm_box(tourney, form_query_string, [ ("hidehelp", 1 if hide_help else 0) ])
generate_scripts(tourney)

cgicommon.show_sidebar(tourney)

cgicommon.writeln("<div class=\"mainpane\">")

players = [ p for p in tourney.get_players() if not p.is_prune() ]

players.sort(key=lambda x : x.get_name())

cgicommon.writeln("<h1>Player Check-In</h1>")

# Show the help, unless the user has asked to hide it.
if hide_help:
    cgicommon.writeln("""
<p style="font-size: 10pt;">
<a href="{baseurl}?tourney={tourneyname}">Show help</a>
</p>
""".format(baseurl=baseurl, tourneyname=urllib.parse.quote_plus(tourneyname)))
else:
    cgicommon.writeln("""
<p style="font-size: 10pt;">
<a href="{baseurl}?tourney={tourneyname}&hidehelp=1">Hide this help</a>
</p>
<p>
This page is intended for before you've generated the first round, to help you
keep track of who has arrived and who is still missing. Use of it is optional.
</p>
<p>
Each button shows whether a player is currently active {tick}
or currently withdrawn {cross}.
Clicking the button will change the status of that player.
</p>
<p>
Suggested usage is as follows:
</p>
<ol>
<li>Mark all players as withdrawn using the button at the bottom of the page.</li>
<li>Mark individual players as active as they arrive.</li>
<li>When you want to generate fixtures for the first round, either keep
or delete the still-withdrawn players as necessary, then move on to
<a href="/cgi-bin/fixturegen.py?tourney={tourneyname}">Generate Fixtures</a>.</li>
</ol>
<p>
Only players currently active {tick}
appear in the list of players on the public display screen.
</p>
""".format(baseurl=baseurl, tourneyname=urllib.parse.quote_plus(tourneyname),
    tick=HTML_TICK_SYMBOL, cross=HTML_CROSS_SYMBOL))

# Show any exceptions or notifications generated if we just acted on a form
# submission.
for e in exceptions_to_show:
    if e is not None:
        cgicommon.show_tourney_exception(e)

if notifications:
    cgicommon.writeln("<hr>")
    cgicommon.writeln("<ul>")
for n in notifications:
    cgicommon.writeln("<li>%s</li>" % (cgicommon.escape(n)))
if notifications:
    cgicommon.writeln("</ul>")

# Show a big grid of buttons, one for each player.
num_columns = min(4, (len(players) + ROWS_PER_COLUMN - 1) // ROWS_PER_COLUMN)
if num_columns == 0:
    rows_per_column = 0
else:
    rows_per_column = (len(players) + num_columns - 1) // num_columns
num_active_players = len([p for p in players if not p.is_withdrawn()])
cgicommon.writeln("<h2>Players</h2>")
cgicommon.writeln("<p>%d of %d players active.</p>" % (num_active_players, len(players)))
cgicommon.writeln("<table class=\"playercheckin\">")

for row in range(rows_per_column):
    cgicommon.writeln("<tr>")
    for col in range(num_columns):
        cell_number = col * rows_per_column + row
        if cell_number >= len(players):
            player = None
        else:
            player = players[cell_number]
        cgicommon.writeln("<td class=\"playercheckincol\">")
        if player:
            cgicommon.writeln("<form method=\"POST\" id=\"formcell%d\" action=\"%s?%s\">" % (
                cell_number,
                cgicommon.escape(baseurl),
                form_query_string
            ))
            # Withdraw/reinstate button
            cgicommon.writeln("<button type=\"submit\" form=\"formcell%d\" name=\"%s\" class=\"playercheckinbutton %s\" id=\"regslot%d\" value=\"1\">%s %s</button>" % (
                cell_number,
                "reinstatesubmit" if player.is_withdrawn() else "withdrawsubmit",
                "playercheckinbuttonwithdrawn" if player.is_withdrawn() else "playercheckinbuttonactive",
                cell_number,
                "&#x2716;" if player.is_withdrawn() else "<span style=\"color: green;\">✓</span>",
                cgicommon.escape(player.get_name())
            ))
            cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourneyname)))
            cgicommon.writeln("<input type=\"hidden\" name=\"playername\" value=\"%s\" />" % (cgicommon.escape(player.get_name())))
            if hide_help:
                cgicommon.writeln("<input type=\"hidden\" name=\"hidehelp\" value=\"1\" />")
            cgicommon.writeln("<input type=\"hidden\" name=\"%s\" value=\"1\" />" % ("reinstatesubmit" if player.is_withdrawn() else "withdrawsubmit"))
            cgicommon.writeln("</form>")
        cgicommon.writeln("</td>")

        if player:
            # Small button to delete this player
            cgicommon.writeln("<td class=\"playercheckincolspace\"><button type=\"button\" class=\"playercheckindeletebutton\" title=\"Delete %s\" onclick=\"showDeletePlayerConfirm(%d, &quot;%s&quot;);\">%s</button></td>" % (
                cgicommon.escape(player.get_name()), player.get_id(),
                cgicommon.escape(cgicommon.escape(player.get_name())),
                HTML_TRASHCAN_SYMBOL))
        else:
            cgicommon.writeln("<td class=\"playercheckincolspace\"></td>")
    cgicommon.writeln("</tr>")
cgicommon.writeln("</table>")
cgicommon.writeln("<hr>")

# A row of buttons on the bottom to activate or withdraw all players, or delete
# all withdrawn players, all subject to confirmation from the popup box which
# actually submits the form.
cgicommon.writeln("""
<div style="margin-top: 20px">
<button class="bigbutton" onclick="showReinstateAllConfirm();" %(reinstate_disabled)s>%(tick_symbol)s Mark all as Active</button>
<button class="bigbutton" style="margin-left: 20px;" onclick="showWithdrawAllConfirm();" %(withdraw_disabled)s>%(cross_symbol)s Mark all as Withdrawn</button>
<button class="bigbutton" style="margin-left: 20px;" onclick="showDeleteWithdrawnConfirm();" %(reinstate_disabled)s>%(trashcan_symbol)s Delete all Withdrawn players</button>
</div>
""" % {
    "cross_symbol" : HTML_CROSS_SYMBOL,
    "tick_symbol" : HTML_TICK_SYMBOL,
    "trashcan_symbol" : HTML_TRASHCAN_SYMBOL,
    "reinstate_disabled" : "disabled" if len(players) == num_active_players else "",
    "withdraw_disabled" : "disabled" if num_active_players == 0 else ""
})

# And finally, have an "add new player" form for the common case where someone
# just rocks up to the venue unannounced.
cgicommon.writeln("<h2>Add new player</h2>")
cgicommon.show_player_form(baseurl, tourney, None, "hidehelp=1" if hide_help else "")

cgicommon.writeln("</div>") #mainpane
cgicommon.writeln("</body>")
cgicommon.writeln("</html>")
