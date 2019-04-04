#!/usr/bin/python3

import cgi
import cgitb
import cgicommon
import sys
import urllib.request, urllib.parse, urllib.error
import os

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;

def int_or_zero(s):
    if s is None:
        return 0
    try:
        return int(s)
    except ValueError:
        return 0

def float_or_none(s):
    if s is None:
        return None;
    try:
        return float(s);
    except ValueError:
        return None;

cgitb.enable();

cgicommon.set_module_path();
import countdowntourney;

def show_division_drop_down_box(control_name, tourney, player):
    num_divisions = tourney.get_num_divisions()
    cgicommon.writeln("<select name=\"%s\">" % (cgicommon.escape(control_name, True)))
    for div in range(num_divisions):
        cgicommon.writeln("<option value=\"%d\" %s >%s (%d active players)</option>" % (div,
                "selected" if (player is not None and div == player.get_division()) or (player is None and div == 0) else "",
                cgicommon.escape(tourney.get_division_name(div)),
                tourney.get_num_active_players(div)))
    cgicommon.writeln("</select>")

def show_player_search_form(tourney):
    cgicommon.writeln("<form method=\"GET\" action=\"%s\">" % (cgicommon.escape(baseurl, True)))
    cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourney.get_name())))
    cgicommon.writeln("<p>")
    cgicommon.writeln("Search player name: <input type=\"text\" name=\"searchname\" value=\"\" /> ")
    cgicommon.writeln("<input type=\"submit\" name=\"searchsubmit\" value=\"Search\" />")
    cgicommon.writeln("</p>")
    cgicommon.writeln("</form>")

def fatal_error(text):
    cgicommon.print_html_head("Player View")
    cgicommon.writeln("<body>")
    cgicommon.writeln("<p>%s</p>" % (cgicommon.escape(text)))
    cgicommon.writeln("</body></html>")
    sys.exit(1)

def fatal_exception(exc, tourney=None):
    cgicommon.print_html_head("Player View")
    cgicommon.writeln("<body>")
    if tourney:
        cgicommon.show_sidebar(tourney)
    cgicommon.writeln("<div class=\"mainpane\">")
    cgicommon.show_tourney_exception(exc)
    cgicommon.writeln("</div>")
    cgicommon.writeln("</body></html>")
    sys.exit(1)

def show_player_form(tourney, player):
    num_divisions = tourney.get_num_divisions()
    tourneyname = tourney.get_name()
    if player:
        player_id = player.get_id()
    else:
        player_id = None

    if player:
        cgicommon.writeln("<form method=\"POST\" action=\"%s?tourney=%s&id=%d\">" % (cgicommon.escape(baseurl), urllib.parse.quote_plus(tourneyname), player_id))
    else:
        cgicommon.writeln("<form method=\"POST\" action=\"%s?tourney=%s\">" % (cgicommon.escape(baseurl), urllib.parse.quote_plus(tourneyname)))
    cgicommon.writeln("<table>")
    cgicommon.writeln("<tr><td>Name</td><td><input type=\"text\" name=\"setname\" value=\"%s\" /></td></tr>" % ("" if not player else cgicommon.escape(player.get_name(), True)))
    cgicommon.writeln("<tr><td>Rating</td><td><input type=\"text\" name=\"setrating\" value=\"%g\"/></td></tr>" % (1000 if not player else player.get_rating()))
    if num_divisions > 1:
        cgicommon.writeln("<tr><td>Division</td>")
        cgicommon.writeln("<td>")
        show_division_drop_down_box("setdivision", tourney, player)
        cgicommon.writeln("</td></tr>")
    cgicommon.writeln("<tr><td>Withdrawn?</td><td><input type=\"checkbox\" name=\"setwithdrawn\" value=\"1\" %s /> <span class=\"playercontrolhelp\">(if ticked, fixture generators will not include this player)</span></td></tr>" % ("checked" if player and player.is_withdrawn() else ""))
    cgicommon.writeln("<tr><td>Requires accessible table?</td><td><input type=\"checkbox\" name=\"setrequiresaccessibletable\" value=\"1\" %s /> <span class=\"playercontrolhelp\">(if ticked, fixture generators will place this player and their opponents on an accessible table, as defined in <a href=\"/cgi-bin/tourneysetup.py?tourney=%s\">General Setup</a>)</span></td></tr>" % (
        "checked" if player and player.is_requiring_accessible_table() else "",
        urllib.parse.quote_plus(tourneyname)
    ))

    if player is None:
        pref = None
    else:
        pref = player.get_preferred_table()
    cgicommon.writeln("<tr><td>Preferred table number</td><td><input type=\"text\" name=\"setpreferredtable\" value=\"%s\" /> <span class=\"playercontrolhelp\">(player will be assigned this table number if possible - if blank, player has no specific table preference)</span></td></tr>" % (cgicommon.escape(str(pref)) if pref is not None else ""))

    cgicommon.writeln("<tr><td>Avoid Prune?</td><td><input type=\"checkbox\" name=\"setavoidprune\" value=\"1\" %s /> <span class=\"playercontrolhelp\">(if ticked, the Swiss fixture generator will behave as if this player has already played a Prune)</span></td></tr>" % ("checked" if player and player.is_avoiding_prune() else ""))
    cgicommon.writeln("</table>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourneyname, True)))
    if player:
        cgicommon.writeln("<input type=\"hidden\" name=\"id\" value=\"%d\" />" % (player_id))
    
    if player:
        cgicommon.writeln("<input type=\"submit\" name=\"editplayer\" class=\"bigbutton\" value=\"Save Changes\" />")
    else:
        cgicommon.writeln("<input type=\"submit\" name=\"newplayersubmit\" class=\"bigbutton\" value=\"Create Player\" />")
    cgicommon.writeln("</p>")
    cgicommon.writeln("</form>")

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

baseurl = "/cgi-bin/player.py";
form = cgi.FieldStorage();
tourneyname = form.getfirst("tourney");

player_id = int_or_none(form.getfirst("id"))
add_player = int_or_none(form.getfirst("addplayer"))
if add_player is None:
    add_player = False
else:
    add_player = bool(add_player)

request_method = os.environ.get("REQUEST_METHOD", "")

tourney = None
if tourneyname is None:
    fatal_error("No tourney name specified.")

try:
    tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir)
except countdowntourney.TourneyException as e:
    fatal_exception(e, None)

if player_id is not None:
    try:
        player = tourney.get_player_from_id(player_id)
        player_name = player.get_name()
        player_id = player.get_id()
    except countdowntourney.TourneyException as e:
        fatal_exception(e, tourney)
else:
    player = None
    player_name = ""
    player_id = None

exceptions_to_show = []
edit_notifications = []



if cgicommon.is_client_from_localhost() and request_method == "POST" and form.getfirst("reratebyplayerid") and form.getfirst("reratebyplayeridconfirm"):
    try:
        tourney.rerate_players_by_id()
        edit_notifications.append("Players rerated by player ID")
    except countdowntourney.TourneyException as e:
        exceptions_to_show.append(("<p>Failed to rerate players...</p>", e))

if cgicommon.is_client_from_localhost() and request_method == "POST" and form.getfirst("editplayer"):
    new_rating = float_or_none(form.getfirst("setrating"))
    new_name = form.getfirst("setname")
    new_withdrawn = int_or_zero(form.getfirst("setwithdrawn"))
    new_avoid_prune = int_or_zero(form.getfirst("setavoidprune"))
    new_division = int_or_none(form.getfirst("setdivision"))
    new_requires_accessible_table = int_or_zero(form.getfirst("setrequiresaccessibletable"))
    new_preferred_table = int_or_none(form.getfirst("setpreferredtable"))
    if new_preferred_table is not None and new_preferred_table <= 0:
        new_preferred_table = None

    if new_rating is not None and player.get_rating() != new_rating:
        try:
            tourney.rerate_player(player.get_name(), new_rating)
            edit_notifications.append("%s's rating changed to %g" % (player.get_name(), new_rating))
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to set player rating...</p>", e))

    # Set player withdrawn status
    if player.is_withdrawn() != (new_withdrawn != 0):
        try:
            if new_withdrawn:
                tourney.withdraw_player(player.get_name())
                edit_notifications.append("%s withdrawn" % (player.get_name()))
            else:
                tourney.unwithdraw_player(player.get_name())
                edit_notifications.append("%s is now active" % (player.get_name()))
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to change player withdrawn status...</p>", e))

    # Set player requires-accessible-table status
    if player.is_requiring_accessible_table() != (new_requires_accessible_table != 0):
        try:
            tourney.set_player_requires_accessible_table(player.get_name(), new_requires_accessible_table != 0)
            if new_requires_accessible_table != 0:
                edit_notifications.append("%s now requires an accessible table" % player.get_name())
            else:
                edit_notifications.append("%s no longer requires an accessible table" % player.get_name())
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to change player accessibility status...</p>", e))

    # Set player's preferred table, if any
    if (player.get_preferred_table() is None) != (new_preferred_table is None) or (new_preferred_table is not None and player.get_preferred_table() is not None and new_preferred_table != player.get_preferred_table()):
        try:
            tourney.set_player_preferred_table(player.get_name(), new_preferred_table)
            if new_preferred_table is None:
                edit_notifications.append("%s now has no specific table preference" % (player.get_name()))
            else:
                edit_notifications.append("%s's preferred table is now %d" % (player.get_name(), new_preferred_table))
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to change player's preferred table...</p>", e))

    # Set whether player should be made to avoid prune
    if player.is_avoiding_prune() != (new_avoid_prune != 0):
        try:
            tourney.set_player_avoid_prune(player.get_name(), new_avoid_prune)
            edit_notifications.append("%s is now %savoiding Prune" % (player.get_name(), "not " if not new_avoid_prune else ""))
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to change player avoiding-prune status...</p>", e))
        
    # Set player's division
    if new_division is not None and player.get_division() != new_division:
        try:
            tourney.set_player_division(player.get_name(), new_division)
            edit_notifications.append("%s moved to %s" % (player.get_name(), tourney.get_division_name(new_division)))
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to change player's division...</p>", e))

    # Set player's name
    if new_name is not None and new_name != "" and player.get_name() != new_name:
        try:
            tourney.rename_player(player.get_name(), new_name)
            edit_notifications.append("%s renamed to %s" % (player_name, new_name))
            player_name = new_name
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to change player's name...</p>", e))
    player = tourney.get_player_from_id(player_id)
elif cgicommon.is_client_from_localhost() and request_method == "POST" and form.getfirst("newplayersubmit"):
    new_player_name = form.getfirst("setname")

    # If no rating has been entered, default to 1000
    rating_str = form.getfirst("setrating")
    if rating_str is None or rating_str.strip() == "":
        new_player_rating = 1000.0
    else:
        new_player_rating = float_or_none(rating_str)
    new_player_division = int_or_none(form.getfirst("setdivision"))
    try_to_add_player = True

    if not new_player_name:
        exceptions_to_show.append(("<p>Can't add new player...</p>", countdowntourney.TourneyException("Player name may not be blank.")))
        try_to_add_player = False
    if new_player_rating is None:
        exceptions_to_show.append(("<p>Can't add new player...</p>", countdowntourney.TourneyException("A new player's rating, if specified, must be a number.")))
        try_to_add_player = False
    if new_player_division is None:
        new_player_division = 0

    new_withdrawn = int_or_zero(form.getfirst("setwithdrawn"))
    new_avoid_prune = int_or_zero(form.getfirst("setavoidprune"))
    new_requires_accessible_table = int_or_zero(form.getfirst("setrequiresaccessibletable"))

    if try_to_add_player:
        try:
            tourney.add_player(new_player_name, new_player_rating, new_player_division)
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to add new player \"%s\"...</p>" % (cgicommon.escape(new_player_name)), e))

        try:
            if new_withdrawn:
                tourney.set_player_withdrawn(new_player_name, True)
            if new_avoid_prune:
                tourney.set_player_avoid_prune(new_player_name, True)
            if new_requires_accessible_table:
                tourney.set_player_requires_accessible_table(new_player_name, True)
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Added player \"%s\" but failed to set attributes...</p>" % (cgicommon.escape(new_player_name)), e))

elif request_method == "GET" and form.getfirst("searchsubmit"):
    player_name = form.getfirst("searchname")
    try:
        player = tourney.get_player_from_name(player_name)
        player_name = player.get_name()
        player_id = player.get_id()
    except countdowntourney.TourneyException as e:
        player = None
        player_name = None
        player_id = None
        exceptions_to_show.append(("", e))

if player:
    cgicommon.print_html_head(player_name)
else:
    cgicommon.print_html_head("Player View")

cgicommon.writeln("<body>")

cgicommon.assert_client_from_localhost()

cgicommon.show_sidebar(tourney)

cgicommon.writeln("<div class=\"mainpane\">")

cgicommon.writeln("<div class=\"playersetupcontainer\">")

cgicommon.writeln("<div class=\"playersetuplistpanecontainer\">")
cgicommon.writeln("<div class=\"playersetuplistpane\">")
cgicommon.writeln("<h1>Players</h1>")
players = tourney.get_players()
active_players = tourney.get_active_players()
num_divisions = tourney.get_num_divisions()
num_withdrawn = len(players) - len(active_players)

cgicommon.writeln("<p>")
cgicommon.writeln("<a href=\"/cgi-bin/player.py?tourney=%s&addplayer=1\">Add new player...</a>" % (urllib.parse.quote_plus(tourney.get_name())))
cgicommon.writeln("</p>")

if not players:
    cgicommon.writeln("<p>")
    cgicommon.writeln("Your tourney doesn't have any players yet.")
    if tourney.get_num_games() == 0:
        cgicommon.writeln("You can add players below or you can paste a list of players on the <a href=\"tourneysetup.py?tourney=%s\">Tourney Setup</a> page." % (urllib.parse.quote_plus(tourney.get_name())))
    else:
        cgicommon.writeln("Yet somehow you've managed to create fixtures. I'm not quite sure how you've managed that, but meh. You can add players using the form below.")
    cgicommon.writeln("</p>")

cgicommon.writeln("<table class=\"playerlisttable\">")
for div in range(num_divisions):
    div_players = [x for x in players if x.get_division() == div]
    div_players = sorted(div_players, key=lambda x : x.get_name())

    num_active_players = len([ x for x in div_players if not x.is_withdrawn() ])
    cgicommon.writeln("<tr class=\"playerlistdivision\"><td colspan=\"2\" class=\"playerlistdivision\">")
    cgicommon.writeln("<span style=\"font-weight: bold; float: left;\">")
    if num_divisions == 1:
        cgicommon.writeln(cgicommon.escape(tourney.get_name()))
    else:
        cgicommon.writeln(cgicommon.escape(tourney.get_division_name(div)))
    cgicommon.writeln("</span>")
    cgicommon.writeln("<span style=\"color: gray; float: right;\" title=\"Number of active players in %s\">%d</span>" % ("the tournament" if num_divisions == 1 else "this division", num_active_players))
    cgicommon.writeln("</td></tr>")

    for p in div_players:
        player_selected = (player and player.get_name() == p.get_name())
    
        cgicommon.writeln("<tr class=\"playerlistrow %s\">" % ("playerlistrowselected" if player_selected else ""));

        cgicommon.writeln("<td class=\"playerlistname\">");
        cgicommon.writeln(cgicommon.player_to_link(p, tourney.get_name(), emboldenise=player_selected, withdrawn=p.is_withdrawn()))
        cgicommon.writeln("</td>")

        cgicommon.writeln("<td class=\"playerlistflags\">")
        if p.get_rating() == 0:
            cgicommon.write("&nbsp;<span title=\"Prune\">&#9898;</span>")
        if p.is_avoiding_prune():
            cgicommon.write("&nbsp;<span title=\"Swiss fixture generator will behave as if this player has already played a Prune\">&#9899;</span>")
        if p.is_requiring_accessible_table():
            cgicommon.write("&nbsp;<span title=\"Requires accessible table\">&#9855;</span>");
        pref_table = p.get_preferred_table()
        if pref_table is not None:
            cgicommon.write("&nbsp;<span title=\"Prefers table %d\" class=\"playerlisttablepreficon\">%d</span>" % (pref_table, pref_table))
        cgicommon.writeln("</td>")
        cgicommon.writeln("</tr>")
cgicommon.writeln("</table>")
cgicommon.writeln("</div>") # end list pane
cgicommon.writeln("</div>") # end list pane container

cgicommon.writeln("<div class=\"playersetupformpanecontainer\">")
cgicommon.writeln("<div class=\"playersetupformpane\">")

if player:
    cgicommon.writeln("<h1>%s%s</h1>" % (cgicommon.escape(player_name), " (withdrawn)" if player.is_withdrawn() else ""))
elif add_player:
    cgicommon.writeln("<h1>Add new player</h1>")

for (html, exc) in exceptions_to_show:
    cgicommon.writeln(html)
    if exc is not None:
        cgicommon.show_tourney_exception(exc)

if edit_notifications:
    cgicommon.writeln("<h2>Player details changed</h2>")
    cgicommon.writeln("<blockquote>")

for item in edit_notifications:
    cgicommon.writeln("<li>%s</li>" % (cgicommon.escape(item)))

if edit_notifications:
    cgicommon.writeln("</blockquote>")
    cgicommon.writeln("<blockquote>")
    if player:
        cgicommon.writeln("<a href=\"%s?tourney=%s&id=%d\">OK</a>" % (cgicommon.escape(baseurl, True), urllib.parse.quote_plus(tourney.get_name()), player.get_id()))
    else:
        cgicommon.writeln("<a href=\"%s?tourney=%s\">OK</a>" % (cgicommon.escape(baseurl, True), urllib.parse.quote_plus(tourney.get_name())))
    cgicommon.writeln("</blockquote>")

if player:
    cgicommon.writeln("<hr />")
    def player_to_link(p):
        return cgicommon.player_to_link(p, tourneyname, p == player)

    num_divisions = tourney.get_num_divisions()

    pref_table = player.get_preferred_table()
    if pref_table is not None and player.is_requiring_accessible_table() and not tourney.is_table_accessible(pref_table):
        (table_list, acc_default) = tourney.get_accessible_tables()
        if acc_default:
            acc_list_preamble = "all except "
            acc_list = ", ".join([str(x) for x in table_list])
        else:
            acc_list_preamble = ""
            if not table_list:
                acc_list = "None"
            else:
                acc_list = ", ".join([str(x) for x in table_list])

        cgicommon.show_warning_box("<p>%s requires an accessible table, but their preferred table is table %d, which is not an accessible table. This player's requirement for an accessible table will be given a higher priority than their specific preference for table %d.</p><p>The accessible table numbers defined in <a href=\"%s?tourney=%s\">General Setup</a> are: %s%s.</p>" % (
            cgicommon.escape(player.get_name()), pref_table, pref_table,
            "/cgi-bin/tourneysetup.py", urllib.parse.quote_plus(tourney.get_name()),
            acc_list_preamble, acc_list
            ), wide=True)

    cgicommon.writeln("<h2>Edit player</h2>")
    show_player_form(tourney, player)

    cgicommon.writeln("<hr />")

    cgicommon.writeln("<h2>Games</h2>")
    games = tourney.get_games()
    games = [x for x in games if x.contains_player(player)]

    if not games:
        cgicommon.writeln("<p>None.</p>")
    else:
        cgicommon.show_games_as_html_table(games, False, None, True, lambda x : tourney.get_short_round_name(x), player_to_link)

    cgicommon.writeln("<hr />")
    cgicommon.writeln("<h2>Stats Corner</h2>")
    standings = tourney.get_standings(player.get_division())
    standing = None
    for s in standings:
        if s.name == player.get_name():
            standing = s
            break
    else:
        cgicommon.writeln("<p>%s isn't in the standings table for %s. This is... odd.</p>" % (cgicommon.escape(player.get_name()), cgicommon.escape(tourney.get_division_name(player.get_division()))))

    if standing:
        highest_score = None
        lowest_score = None
        for g in games:
            if g.is_complete():
                if g.tb:
                    player_score = g.get_opponent_score(player)
                else:
                    player_score = g.get_player_score(player)
                if highest_score is None or player_score > highest_score:
                    highest_score = player_score
                if lowest_score is None or player_score < lowest_score:
                    lowest_score = player_score
        div_players = [x for x in tourney.get_players(exclude_withdrawn=False) if x.get_division() == player.get_division()]
        div_players = sorted(div_players, key=lambda x : x.get_rating(), reverse=True)
        seed = 1
        joint = 1
        prev_rating = None
        for p in div_players:
            if prev_rating == p.get_rating():
                joint += 1
            elif prev_rating is not None:
                seed += joint
                joint = 1
            if p == player:
                break
            prev_rating = p.get_rating()
        else:
            seed = None

        if num_divisions > 1:
            indiv_string = " in %s" % (tourney.get_division_name(player.get_division()))
        else:
            indiv_string = ""

        cgicommon.writeln("<table class=\"statscorner\">")
        cgicommon.writeln("<tr class=\"statsrow\"><th colspan=\"2\">%s</th></tr>" % (cgicommon.escape(player.get_name())))
        cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Rating</td>")
        cgicommon.writeln("<td class=\"statsnumvalue\">%g</td></tr>" % (player.get_rating()))
        cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Tournament rating</td>")
        if standing.tournament_rating is not None:
            cgicommon.writeln("<td class=\"statsnumvalue\">%.2f</td></tr>" % (standing.tournament_rating))
        else:
            cgicommon.writeln("<td class=\"statsnumvalue\"></td></tr>")
        cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Position%s</td>" % (indiv_string))
        cgicommon.writeln("<td class=\"statsnumvalue\">%s</td></tr>" % (cgicommon.ordinal_number(standing.position)))
        if seed is not None:
            cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Rating rank%s</td>" % (indiv_string))
            cgicommon.writeln("<td class=\"statsnumvalue\">%s</td></tr>" % (cgicommon.ordinal_number(seed)))

        cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Games played</td>")
        cgicommon.writeln("<td class=\"statsnumvalue\">%d</td></tr>" % (standing.played))
        cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Wins</td>")
        cgicommon.writeln("<td class=\"statsnumvalue\">%d</td></tr>" % (standing.wins))
        cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Draws</td>")
        cgicommon.writeln("<td class=\"statsnumvalue\">%d</td></tr>" % (standing.draws))
        if highest_score is not None:
            cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Highest score</td>")
            cgicommon.writeln("<td class=\"statsnumvalue\">%d</td></tr>" % (highest_score))
        if lowest_score is not None:
            cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Lowest score</td>")
            cgicommon.writeln("<td class=\"statsnumvalue\">%d</td></tr>" % (lowest_score))
        cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Points scored</td>")
        cgicommon.writeln("<td class=\"statsnumvalue\">%d</td></tr>" % (standing.points))
        cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Points against</td>")
        cgicommon.writeln("<td class=\"statsnumvalue\">%d</td></tr>" % (-(standing.spread - standing.points)))
        cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Spread</td>")
        cgicommon.writeln("<td class=\"statsnumvalue\">%+d</td></tr>" % (standing.spread))
        cgicommon.writeln("<tr class=\"statsrow\"><td class=\"statsname\">Played 1st/2nd</td>")
        cgicommon.writeln("<td class=\"statsnumvalue\">%d/%d</td></tr>" % (standing.played_first, standing.played - standing.played_first))

        cgicommon.writeln("</table>")
    cgicommon.writeln("<hr />")
elif add_player:
    show_player_form(tourney, None)

cgicommon.writeln("</div>") # end form pane
cgicommon.writeln("</div>") # end form pane container
cgicommon.writeln("</div>") # end double-pane container

cgicommon.writeln("</div>") # end main pane
cgicommon.writeln("</body>")
cgicommon.writeln("</html>")

sys.exit(0)
