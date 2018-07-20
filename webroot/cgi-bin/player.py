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

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

baseurl = "/cgi-bin/player.py";
form = cgi.FieldStorage();
tourneyname = form.getfirst("tourney");

player_id = int_or_none(form.getfirst("id"))

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
    new_withdrawn = int_or_none(form.getfirst("setwithdrawn"))
    new_avoid_prune = int_or_none(form.getfirst("setavoidprune"))
    new_division = int_or_none(form.getfirst("setdivision"))

    if new_rating is not None and player.get_rating() != new_rating:
        try:
            tourney.rerate_player(player.get_name(), new_rating)
            edit_notifications.append("%s's rating changed to %g" % (player.get_name(), new_rating))
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to set player rating...</p>", e))

    if player.is_withdrawn() != (new_withdrawn is not None and new_withdrawn != 0):
        try:
            if new_withdrawn:
                tourney.withdraw_player(player.get_name())
                edit_notifications.append("%s withdrawn" % (player.get_name()))
            else:
                tourney.unwithdraw_player(player.get_name())
                edit_notifications.append("%s reinstated" % (player.get_name()))
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to change player withdrawn status...</p>", e))

    if player.is_avoiding_prune() != (new_avoid_prune is not None and new_avoid_prune != 0):
        try:
            tourney.set_player_avoid_prune(player.get_name(), new_avoid_prune)
            edit_notifications.append("%s is now %savoiding Prune" % (player.get_name(), "not " if not new_avoid_prune else ""))
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to change player avoiding-prune status...</p>", e))
        
    if new_division is not None and player.get_division() != new_division:
        try:
            tourney.set_player_division(player.get_name(), new_division)
            edit_notifications.append("%s moved to %s" % (player.get_name(), tourney.get_division_name(new_division)))
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to change player's division...</p>", e))

    if new_name is not None and new_name != "" and player.get_name() != new_name:
        try:
            tourney.rename_player(player.get_name(), new_name)
            edit_notifications.append("%s renamed to %s" % (player_name, new_name))
            player_name = new_name
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to change player's name...</p>", e))
    player = tourney.get_player_from_id(player_id)
elif cgicommon.is_client_from_localhost() and request_method == "POST" and form.getfirst("newplayersubmit"):
    new_player_name = form.getfirst("newplayername")

    # If no rating has been entered, default to 1000
    rating_str = form.getfirst("newplayerrating")
    if rating_str is None or rating_str.strip() == "":
        new_player_rating = 1000.0
    else:
        new_player_rating = float_or_none(rating_str)
    new_player_division = int_or_none(form.getfirst("newplayerdivision"))
    try_to_add_player = True

    if not new_player_name:
        exceptions_to_show.append(("<p>Can't add new player...</p>", countdowntourney.TourneyException("Player name may not be blank.")))
        try_to_add_player = False
    if new_player_rating is None:
        exceptions_to_show.append(("<p>Can't add new player...</p>", countdowntourney.TourneyException("A new player's rating, if specified, must be a number.")))
        try_to_add_player = False
    if new_player_division is None:
        new_player_division = 0

    if try_to_add_player:
        try:
            tourney.add_player(new_player_name, new_player_rating, new_player_division)
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to add new player %s...</p>" % (cgicommon.escape(new_player_name)), e))

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

if player:
    cgicommon.writeln("<h1>%s%s</h1>" % (cgicommon.escape(player_name), " (withdrawn)" if player.is_withdrawn() else ""))

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

    cgicommon.writeln("<h2>Stats Corner</h2>")
    standings = tourney.get_standings(player.get_division())
    standing = None
    for s in standings:
        if s.name == player.get_name():
            standing = s
            break
    else:
        cgicommon.writeln("<p>%s isn't in the standings table for %s. This is... odd.</p>" % (cgicommon.escape(player.get_name()), cgicommon.escape(tourney.get_division_name(player.get_division()))))

    games = tourney.get_games()
    games = [x for x in games if x.contains_player(player)]

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

    cgicommon.writeln("<h2>Games</h2>")
    if not games:
        cgicommon.writeln("<p>None.</p>")
    else:
        cgicommon.show_games_as_html_table(games, False, None, True, lambda x : tourney.get_short_round_name(x), player_to_link)

    cgicommon.writeln("<hr />")

    cgicommon.writeln("<h2>Edit player</h2>")
    cgicommon.writeln("<form method=\"POST\" action=\"%s?tourney=%s&id=%d\">" % (cgicommon.escape(baseurl), urllib.parse.quote_plus(tourneyname), player_id))
    cgicommon.writeln("<table>")
    cgicommon.writeln("<tr><td>Name</td><td><input type=\"text\" name=\"setname\" value=\"%s\" /></td></tr>" % (cgicommon.escape(player.get_name(), True)))
    cgicommon.writeln("<tr><td>Rating</td><td><input type=\"text\" name=\"setrating\" value=\"%g\"/></td></tr>" % (player.get_rating()))
    if num_divisions > 1:
        cgicommon.writeln("<tr><td>Division</td>")
        cgicommon.writeln("<td>")
        show_division_drop_down_box("setdivision", tourney, player)
        cgicommon.writeln("</td></tr>")
    cgicommon.writeln("<tr><td>Withdrawn?</td><td><input type=\"checkbox\" name=\"setwithdrawn\" value=\"1\" %s /> <em>(if ticked, the fixture generator will not include this player)</em></td></tr>" % ("checked" if player.is_withdrawn() else ""))
    cgicommon.writeln("<tr><td>Avoid Prune?</td><td><input type=\"checkbox\" name=\"setavoidprune\" value=\"1\" %s /> <em>(if ticked, the Swiss fixture generator will behave as if this player has already played a Prune)</em></td></tr>" % ("checked" if player.is_avoiding_prune() else ""))
    cgicommon.writeln("</table>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourneyname, True)))
    cgicommon.writeln("<input type=\"hidden\" name=\"id\" value=\"%d\" />" % (player_id))
    cgicommon.writeln("<input type=\"submit\" name=\"editplayer\" value=\"Save Changes\" />")
    cgicommon.writeln("</p>")
    cgicommon.writeln("</form>")
    cgicommon.writeln("<hr />")
else:
    cgicommon.writeln("<h1>Players</h1>")
    players = tourney.get_players()
    active_players = tourney.get_active_players()
    num_divisions = tourney.get_num_divisions()
    num_withdrawn = len(players) - len(active_players)

    if len(players):
        cgicommon.write("<p>Your tourney has %d players" % (len(players)))
        if num_divisions > 1:
            cgicommon.write(" in %d divisions" % (num_divisions))
        if len(active_players) != len(players):
            cgicommon.writeln(". %d of these players %s withdrawn." % (num_withdrawn, "has" if num_withdrawn == 1 else "have"))
        else:
            cgicommon.writeln(".")
        cgicommon.writeln("</p>")
        cgicommon.writeln("<p>Click on a player's name to view or edit information about them.</p>")
    else:
        cgicommon.writeln("<p>")
        cgicommon.writeln("Your tourney doesn't have any players yet.")
        if tourney.get_num_games() == 0:
            cgicommon.writeln("You can add players below or you can paste a list of players on the <a href=\"tourneysetup.py?tourney=%s\">Tourney Setup</a> page." % (urllib.parse.quote_plus(tourney.get_name())))
        else:
            cgicommon.writeln("Yet somehow you've managed to create fixtures. I'm not quite sure how you've managed that, but meh. You can add players using the form below.")
        cgicommon.writeln("</p>")

    for div in range(num_divisions):
        div_players = [x for x in players if x.get_division() == div]
        div_players = sorted(div_players, key=lambda x : x.get_name())

        if num_divisions > 1:
            cgicommon.writeln("<h2>%s (%d active players)</h2>" % (tourney.get_division_name(div), len([x for x in div_players if not x.is_withdrawn()])))

        cgicommon.writeln("<ul>")
        for p in div_players:
            cgicommon.writeln("<li>%s%s%s</li>" % (
                    cgicommon.player_to_link(p, tourney.get_name()),
                    " (withdrawn)" if p.is_withdrawn() else "",
                    " (avoiding Prune)" if p.is_avoiding_prune() else ""))
        cgicommon.writeln("</ul>")

show_player_search_form(tourney)

if player is None:
    cgicommon.writeln("<hr />")

    cgicommon.writeln("<h2>Add player</h2>")
    if tourney.get_num_games() > 0:
        cgicommon.writeln("<p>The tournament has already started. You may add new players, but these new players will not be added to any rounds whose fixtures have already been generated.</p>")
        cgicommon.writeln("<p>Note that <strong>you cannot delete a player</strong> once the tournament has started, although you can <em>withdraw</em> them, which prevents them from being included in the fixture list for future rounds. You can withdraw a player or edit their details by clicking their name.</p>")

    cgicommon.writeln("<form method=\"POST\" action=\"%s?tourney=%s\">" % (cgicommon.escape(baseurl), urllib.parse.quote_plus(tourney.get_name())))
    cgicommon.writeln("<table>")
    cgicommon.writeln("<tr><td>New player name</td>")
    cgicommon.writeln("<td><input type=\"text\" name=\"newplayername\" value=\"\" /></td></tr>")
    cgicommon.writeln("<tr><td>New player rating</td>")
    cgicommon.writeln("<td><input type=\"text\" name=\"newplayerrating\" value=\"\" /> <em>(leave blank for the default rating 1000; enter 0 if this is a prune or bye)</em></td></tr>")
    if tourney.get_num_divisions() > 1:
        cgicommon.writeln("<tr><td>Division</td><td>")
        show_division_drop_down_box("newplayerdivision", tourney, None)
        cgicommon.writeln("</td></tr>")
    cgicommon.writeln("</table>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourney.get_name(), True)))
    cgicommon.writeln("<input type=\"submit\" name=\"newplayersubmit\" value=\"Add New Player\" />")
    cgicommon.writeln("</p>")
    cgicommon.writeln("</form>")

    if tourney.get_num_games() > 0:
        cgicommon.writeln("<hr />")
        cgicommon.writeln("<h2>Rerate players by player ID</h2>")
        cgicommon.writeln("<p>")
        cgicommon.writeln("""
        Set the ratings of players in order, by player ID, which corresponds
        to the order in which they appeared in the list you put into the text
        box at the start of the tournament. The player at the top of the list
        (the lowest player ID) gets the highest rating, and the player at the
        bottom of the list (the highest player ID) gets the lowest rating. Any
        player with a rating of zero remains unchanged.""")
        cgicommon.writeln("</p>")
        cgicommon.writeln("<p>")
        cgicommon.writeln("""
        This is useful if when you pasted in the player list you forgot to
        select the option which tells Atropine that they're in rating order,
        and now the Overachievers page thinks they're all seeded the same.
        """)
        cgicommon.writeln("</p>")

        cgicommon.writeln("<p>")
        cgicommon.writeln("""
        If you press this button, it will overwrite all other non-zero ratings
        you may have given the players. That's why you need to tick the box as
        well.
        """)
        cgicommon.writeln("</p>")

        cgicommon.writeln("<p>")
        cgicommon.writeln("<form method=\"POST\" action=\"%s?tourney=%s\">" % (cgicommon.escape(baseurl), urllib.parse.quote_plus(tourneyname)))
        cgicommon.writeln("<input type=\"submit\" name=\"reratebyplayerid\" value=\"Rerate players by player ID\" />")
        cgicommon.writeln("<input type=\"checkbox\" name=\"reratebyplayeridconfirm\" id=\"reratebyplayeridconfirm\" style=\"margin-left: 20px\" />")
        cgicommon.writeln("<label for=\"reratebyplayeridconfirm\">Yes, I'm sure</label>")

        cgicommon.writeln("</form>")
        cgicommon.writeln("</p>")

cgicommon.writeln("<hr />")

cgicommon.writeln("</div>")
cgicommon.writeln("</body>")
cgicommon.writeln("</html>")

sys.exit(0)
