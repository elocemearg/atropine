#!/usr/bin/python

import cgi
import cgitb
import cgicommon
import sys
import urllib
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
    print "<select name=\"%s\">" % (cgi.escape(control_name, True))
    for div in range(num_divisions):
        print "<option value=\"%d\" %s >%s (%d active players)</option>" % (div,
                "selected" if (player is not None and div == player.get_division()) or (player is None and div == 0) else "",
                cgi.escape(tourney.get_division_name(div)),
                tourney.get_num_active_players(div))
    print "</select>"

def show_player_search_form(tourney):
    print "<form method=\"GET\" action=\"%s\">" % (cgi.escape(baseurl, True))
    print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgi.escape(tourney.get_name()))
    print "<p>"
    print "Search player name: <input type=\"text\" name=\"searchname\" value=\"\" /> "
    print "<input type=\"submit\" name=\"searchsubmit\" value=\"Search\" />"
    print "</p>"
    print "</form>"

def fatal_error(text):
    cgicommon.print_html_head("Player View")
    print "<body>"
    print "<p>%s</p>" % (cgi.escape(text))
    print "</body></html>"
    sys.exit(1)

def fatal_exception(exc, tourney=None):
    cgicommon.print_html_head("Player View")
    print "<body>"
    if tourney:
        cgicommon.show_sidebar(tourney)
    print "<div class=\"mainpane\">"
    cgicommon.show_tourney_exception(exc)
    print "</div>"
    print "</body></html>"
    sys.exit(1)

print "Content-Type: text/html; charset=utf-8";
print "";

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

if request_method == "POST" and form.getfirst("editplayer"):
    new_rating = float_or_none(form.getfirst("setrating"))
    new_name = form.getfirst("setname")
    new_withdrawn = int_or_none(form.getfirst("setwithdrawn"))
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
elif request_method == "POST" and form.getfirst("newplayersubmit"):
    new_player_name = form.getfirst("newplayername")
    new_player_rating = float_or_none(form.getfirst("newplayerrating"))
    new_player_division = int_or_none(form.getfirst("newplayerdivision"))
    try_to_add_player = True

    if not new_player_name:
        exceptions_to_show.append(("<p>Can't add new player...</p>", countdowntourney.TourneyException("Player name may not be blank.")))
        try_to_add_player = False
    if new_player_rating is None:
        exceptions_to_show.append(("<p>Can't add new player...</p>", countdowntourney.TourneyException("To add a new player, you must specify a rating and this must be a number.")))
        try_to_add_player = False
    if new_player_division is None:
        new_player_division = 0

    if try_to_add_player:
        try:
            tourney.add_player(new_player_name, new_player_rating, new_player_division)
        except countdowntourney.TourneyException as e:
            exceptions_to_show.append(("<p>Failed to add new player %s...</p>" % (cgi.escape(new_player_name)), e))

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

cgicommon.show_sidebar(tourney)

print "<div class=\"mainpane\">"

if player:
    print "<h1>%s%s</h1>" % (cgi.escape(player_name), " (withdrawn)" if player.is_withdrawn() else "")

for (html, exc) in exceptions_to_show:
    print html
    if exc is not None:
        cgicommon.show_tourney_exception(exc)

if edit_notifications:
    print "<h2>Player details changed</h2>"
    print "<blockquote>"

for item in edit_notifications:
    print "<li>%s</li>" % (cgi.escape(item))

if edit_notifications:
    print "</blockquote>"
    print "<blockquote>"
    print "<a href=\"%s?tourney=%s&id=%d\">OK</a>" % (cgi.escape(baseurl, True), urllib.quote_plus(tourney.get_name()), player.get_id())
    print "</blockquote>"


if player:
    print "<hr />"
    def player_to_link(p):
        return cgicommon.player_to_link(p, tourneyname, p == player)

    num_divisions = tourney.get_num_divisions()

    print "<h2>Stats Corner</h2>"
    standings = tourney.get_standings(player.get_division())
    standing = None
    for s in standings:
        if s.name == player.get_name():
            standing = s
            break
    else:
        print "<p>%s isn't in the standings table for %s. This is... odd.</p>" % (cgi.escape(player.get_name()), cgi.escape(tourney.get_division_name(player.get_division())))

    games = tourney.get_games()
    games = filter(lambda x : x.contains_player(player), games)

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
        div_players = filter(lambda x : x.get_division() == player.get_division(), tourney.get_players(exclude_withdrawn=False))
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

        print "<table class=\"statscorner\">"
        print "<tr class=\"statsrow\"><th colspan=\"2\">%s</th></tr>" % (cgi.escape(player.get_name()))
        print "<tr class=\"statsrow\"><td class=\"statsname\">Rating</td>"
        print "<td class=\"statsnumvalue\">%g</td></tr>" % (player.get_rating())
        print "<tr class=\"statsrow\"><td class=\"statsname\">Tournament rating</td>"
        if standing.tournament_rating is not None:
            print "<td class=\"statsnumvalue\">%.2f</td></tr>" % (standing.tournament_rating)
        else:
            print "<td class=\"statsnumvalue\"></td></tr>"
        print "<tr class=\"statsrow\"><td class=\"statsname\">Position%s</td>" % (indiv_string)
        print "<td class=\"statsnumvalue\">%s</td></tr>" % (cgicommon.ordinal_number(standing.position))
        if seed is not None:
            print "<tr class=\"statsrow\"><td class=\"statsname\">Rating rank%s</td>" % (indiv_string)
            print "<td class=\"statsnumvalue\">%s</td></tr>" % (cgicommon.ordinal_number(seed))

        print "<tr class=\"statsrow\"><td class=\"statsname\">Games played</td>"
        print "<td class=\"statsnumvalue\">%d</td></tr>" % (standing.played)
        print "<tr class=\"statsrow\"><td class=\"statsname\">Wins</td>"
        print "<td class=\"statsnumvalue\">%d</td></tr>" % (standing.wins)
        print "<tr class=\"statsrow\"><td class=\"statsname\">Draws</td>"
        print "<td class=\"statsnumvalue\">%d</td></tr>" % (standing.draws)
        if highest_score is not None:
            print "<tr class=\"statsrow\"><td class=\"statsname\">Highest score</td>"
            print "<td class=\"statsnumvalue\">%d</td></tr>" % (highest_score)
        if lowest_score is not None:
            print "<tr class=\"statsrow\"><td class=\"statsname\">Lowest score</td>"
            print "<td class=\"statsnumvalue\">%d</td></tr>" % (lowest_score)
        print "<tr class=\"statsrow\"><td class=\"statsname\">Points scored</td>"
        print "<td class=\"statsnumvalue\">%d</td></tr>" % (standing.points)
        print "<tr class=\"statsrow\"><td class=\"statsname\">Points against</td>"
        print "<td class=\"statsnumvalue\">%d</td></tr>" % (-(standing.spread - standing.points))
        print "<tr class=\"statsrow\"><td class=\"statsname\">Spread</td>"
        print "<td class=\"statsnumvalue\">%+d</td></tr>" % (standing.spread)
        print "<tr class=\"statsrow\"><td class=\"statsname\">Played 1st/2nd</td>"
        print "<td class=\"statsnumvalue\">%d/%d</td></tr>" % (standing.played_first, standing.played - standing.played_first)

        print "</table>"
    print "<hr />"

    print "<h2>Games</h2>"
    if not games:
        print "<p>None.</p>"
    else:
        cgicommon.show_games_as_html_table(games, False, None, True, lambda x : tourney.get_short_round_name(x), player_to_link)

    print "<hr />"

    print "<h2>Edit player</h2>"
    print "<form method=\"POST\" action=\"%s?tourney=%s&id=%d\">" % (cgi.escape(baseurl), urllib.quote_plus(tourneyname), player_id)
    print "<table>"
    print "<tr><td>Name</td><td><input type=\"text\" name=\"setname\" value=\"%s\" /></td></tr>" % (cgi.escape(player.get_name(), True))
    print "<tr><td>Rating</td><td><input type=\"text\" name=\"setrating\" value=\"%g\"/></td></tr>" % (player.get_rating())
    if num_divisions > 1:
        print "<tr><td>Division</td>"
        print "<td>"
        show_division_drop_down_box("setdivision", tourney, player)
        print "</td></tr>"
    print "<tr><td>Withdrawn?</td><td><input type=\"checkbox\" name=\"setwithdrawn\" value=\"1\" %s /></td></tr>" % ("checked" if player.is_withdrawn() else "")
    print "</table>"
    print "<p>"
    print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgi.escape(tourneyname, True))
    print "<input type=\"hidden\" name=\"id\" value=\"%d\" />" % (player_id)
    print "<input type=\"submit\" name=\"editplayer\" value=\"Save Changes\" />"
    print "</p>"
    print "</form>"
    print "<hr />"
else:
    print "<h1>Players</h1>"
    players = tourney.get_players()
    active_players = tourney.get_active_players()
    num_divisions = tourney.get_num_divisions()
    num_withdrawn = len(players) - len(active_players)

    if len(players):
        sys.stdout.write("<p>Your tourney has %d players" % (len(players)))
        if num_divisions > 1:
            sys.stdout.write(" in %d divisions" % (num_divisions))
        if len(active_players) != len(players):
            print ". %d of these players %s withdrawn." % (num_withdrawn, "has" if num_withdrawn == 1 else "have")
        else:
            print "."
        print "</p>"
        print "<p>Click on a player's name to view or edit information about them.</p>"
    else:
        print "<p>"
        print "Your tourney doesn't have any players yet."
        if tourney.get_num_games() == 0:
            print "You can add players below or you can paste a list of players on the <a href=\"tourneysetup.py?tourney=%s\">Tourney Setup</a> page." % (urllib.quote_plus(tourney.get_name()))
        else:
            print "Yet somehow you've managed to create fixtures. I'm not quite sure how you've managed that, but meh. You can add players using the form below."
        print "</p>"

    for div in range(num_divisions):
        div_players = filter(lambda x : x.get_division() == div, players)
        div_players = sorted(div_players, key=lambda x : x.get_name())

        if num_divisions > 1:
            print "<h2>%s (%d active players)</h2>" % (tourney.get_division_name(div), len(filter(lambda x : not x.is_withdrawn(), div_players)))

        print "<ul>"
        for p in div_players:
            print "<li>%s%s</li>" % (cgicommon.player_to_link(p, tourney.get_name()), " (withdrawn)" if p.is_withdrawn() else "")
        print "</ul>"

show_player_search_form(tourney)

if player is None:
    print "<hr />"
    print "<h2>Add player</h2>"
    if tourney.get_num_games() > 0:
        print "<p>The tournament has already started. You may add new players, but these new players will not be added to any rounds whose fixtures have already been generated.</p>"
        print "<p>Note that <strong>you cannot delete a player</strong> once the tournament has started, although you can <em>withdraw</em> them, which prevents them from being included in the fixture list for future rounds. You can withdraw a player or edit their details by clicking their name.</p>"

    print "<form method=\"POST\" action=\"%s?tourney=%s\">" % (cgi.escape(baseurl), urllib.quote_plus(tourney.get_name()))
    print "<table>"
    print "<tr><td>New player name</td>"
    print "<td><input type=\"text\" name=\"newplayername\" value=\"\" /></td></tr>"
    print "<tr><td>New player rating</td>"
    print "<td><input type=\"text\" name=\"newplayerrating\" value=\"\" /></td></tr>"
    if tourney.get_num_divisions() > 1:
        print "<tr><td>Division</td><td>"
        show_division_drop_down_box("newplayerdivision", tourney, None)
        print "</td></tr>"
    print "</table>"
    print "<p>"
    print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgi.escape(tourney.get_name(), True))
    print "<input type=\"submit\" name=\"newplayersubmit\" value=\"Add New Player\" />"
    print "</p>"
    print "</form>"

print "<hr />"

print "</div>"
print "</body>"
print "</html>"

sys.exit(0)
