#!/usr/bin/python3

import htmlcommon
import htmldialog
import countdowntourney

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

def show_player_search_form(response, tourney):
    response.writeln("<form method=\"GET\">")
    response.writeln("<p>")
    response.writeln("Search player name: <input type=\"text\" name=\"searchname\" value=\"\" /> ")
    response.writeln("<input type=\"submit\" name=\"searchsubmit\" value=\"Search\" />")
    response.writeln("</p>")
    response.writeln("</form>")

def fatal_error(response, text):
    htmlcommon.print_html_head(response, "Player View")
    response.writeln("<body>")
    response.writeln("<p>%s</p>" % (htmlcommon.escape(text)))
    response.writeln("</body></html>")

def fatal_exception(response, exc, tourney=None):
    htmlcommon.print_html_head(response, "Player View")
    response.writeln("<body>")
    if tourney:
        htmlcommon.show_sidebar(response, tourney)
    response.writeln("<div class=\"mainpane\">")
    htmlcommon.show_tourney_exception(response, exc)
    response.writeln("</div>")
    response.writeln("</body></html>")

def write_h2(response, player, text):
    classes = ""
    if player and player.is_withdrawn():
        classes = " class=\"withdrawnplayer\""
    response.writeln("<h2%s>%s</h2>" % (classes, htmlcommon.escape(text)))

def show_player_delete_form(response, tourney, player):
    response.writeln('<p>If you delete this player, they will be removed from the database entirely.</p>')
    response.writeln("<button class=\"bigbutton\" onclick=\"showDeletePlayerDialog();\">Delete %s</button>" % (htmlcommon.escape(player.get_name())))

def show_player_withdrawal_form(response, tourney, player):
    player_id = player.get_id()
    player_name = player.get_name()
    tourneyname = tourney.get_name()
    if player.is_withdrawn():
        response.writeln('<p>%s is currently <span style="font-weight: bold; color: red;">withdrawn</span>, which means newly-generated rounds will not include this player.</p>' % (htmlcommon.escape(player_name)))
        response.writeln('<p>If you reinstate them as an active player, they will be included in any subsequent fixtures you generate.</p>')
    else:
        response.writeln('<p>%s is currently an <span style="font-weight: bold; color: #008800"">active player</span>, which means they will be included when fixtures are generated.</p>' % (htmlcommon.escape(player_name)))
        response.writeln('<p>If you withdraw this player, they will be excluded from later rounds. You can reinstate a withdrawn player at any time.</p>')
    response.writeln('<form method="POST">')
    #response.writeln('<input type="hidden" name="id" value="%d">' % (player_id))
    if player.is_withdrawn():
        response.writeln('<input type="submit" name="reinstateplayer" class="bigbutton" value="Reinstate %s">' % (htmlcommon.escape(player_name)))
    else:
        response.writeln('<input type="submit" name="withdrawplayer" class="bigbutton" value="Withdraw %s">' % (htmlcommon.escape(player_name)))
    response.writeln('</form>')

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourneyname = tourney.get_name()

    # If player_id is given, it's the first extra component after
    # /atropine/<tourney>/player/
    if len(extra_components) > 0:
        player_id = int_or_none(extra_components[0])
    else:
        player_id = None

    add_player = int_or_none(form.getfirst("addplayer"))
    if add_player is None:
        add_player = False
    else:
        add_player = bool(add_player)
    player_name_deleted = None

    if player_id is not None:
        try:
            if player_id < 0:
                # Don't let the player view or try to edit information for the
                # automatic Prune player.
                e = countdowntourney.TourneyException("Can't view player with ID < 0. If you followed a link to get here, that is a bug.")
                fatal_exception(response, e, tourney)
                return
            player = tourney.get_player_from_id(player_id)
            player_name = player.get_name()
            player_id = player.get_id()
        except countdowntourney.TourneyException as e:
            fatal_exception(response, e, tourney)
            return
    else:
        player = None
        player_name = ""
        player_id = None

    exceptions_to_show = []
    edit_notifications = []

    if httpreq.is_client_from_localhost() and request_method == "POST":
        if form.getfirst("editplayer"):
            new_rating = float_or_none(form.getfirst("setrating"))
            new_name = form.getfirst("setname")

            # Withdrawn checkbox might not be present for editplayer. If it
            # isn't, leave the player's withdrawn status as it is.
            if form.getfirst("setwithdrawn") is None:
                new_withdrawn = 1 if player.is_withdrawn() else 0
            else:
                new_withdrawn = int_or_zero(form.getfirst("setwithdrawn"))

            new_avoid_prune = int_or_zero(form.getfirst("setavoidprune"))
            new_division = int_or_none(form.getfirst("setdivision"))
            new_requires_accessible_table = int_or_zero(form.getfirst("setrequiresaccessibletable"))
            new_preferred_table = int_or_none(form.getfirst("setpreferredtable"))
            if new_preferred_table is not None and new_preferred_table <= 0:
                new_preferred_table = None
            new_newbie = int_or_zero(form.getfirst("setnewbie"))

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

            # Set player's newbie status
            if (new_newbie != 0) != player.is_newbie():
                try:
                    tourney.set_player_newbie(player.get_name(), new_newbie != 0)
                    edit_notifications.append("%s is now %sa newbie" % (player_name, "" if new_newbie else "not "))
                except countdowntourney.TourneyException as e:
                    exceptions_to_show.append(("<p>Failed to set player's newbie status...</p>", e))

            player = tourney.get_player_from_id(player_id)
        elif form.getfirst("newplayersubmit"):
            try:
                htmlcommon.add_new_player_from_form(tourney, form)
            except countdowntourney.TourneyException as e:
                exceptions_to_show.append(("<p>Error when adding new player...</p>", e))
        elif form.getfirst("reinstateplayer"):
            if player_name:
                try:
                    tourney.unwithdraw_player(player_name)
                except countdowntourney.TourneyException as e:
                    exceptions_to_show.append(("<p>Failed to reinstate player \"%s\"...</p>" % (htmlcommon.escape(player_name)), e))
                player = tourney.get_player_from_id(player_id)
        elif form.getfirst("withdrawplayer"):
            if player_name:
                try:
                    tourney.withdraw_player(player_name)
                except countdowntourney.TourneyException as e:
                    exceptions_to_show.append(("<p>Failed to withdraw player \"%s\"...</p>" % (htmlcommon.escape(player_name)), e))
                player = tourney.get_player_from_id(player_id)
        elif form.getfirst("deleteplayer"):
            if player_name:
                try:
                    tourney.delete_player(player_name)
                    player_name_deleted = player_name
                except countdowntourney.TourneyException as e:
                    exception_to_show.append(("<p>Failed to delete player \"%s\"...</p>" % (htmlcommon.escape(player_name)), e))
                player = None
                player_id = None
                player_name = ""

    if request_method == "GET" and form.getfirst("searchsubmit"):
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
        htmlcommon.print_html_head(response, player_name, othercssfiles=["player.css"])
    else:
        htmlcommon.print_html_head(response, "Player View", othercssfiles=["player.css"])

    response.writeln("<body>")

    htmlcommon.show_sidebar(response, tourney)

    response.writeln("<script>")
    response.writeln(htmldialog.DIALOG_JAVASCRIPT)

    if player_id is not None:
        response.writeln("const playerId = %d;" % (player_id))
    if player_name is not None:
        response.writeln("const playerName = %s;" % (htmlcommon.js_string(player_name)))

    response.writeln("""
function showDeletePlayerDialog() {
    let elements = [];
    let p = document.createElement("P");
    p.innerText = "Are you sure you want to delete this player? The only way to undo this is to add a new player with this name.";
    elements.push(p);
    dialogBoxShow("playerdialog", playerName, "Delete", "Cancel",
            "POST", "", "deleteplayer", elements, { "id" : playerId });
}
""")

    response.writeln("</script>")

    response.writeln("<div class=\"mainpane\">")

    response.writeln("<div class=\"playersetupcontainer\">")

    response.writeln("<div class=\"playersetuplistpanecontainer\">")
    response.writeln("<div class=\"playersetuplistpane\">")
    response.writeln("<h1>Players</h1>")
    players = tourney.get_players()
    active_players = tourney.get_active_players()
    num_divisions = tourney.get_num_divisions()
    num_withdrawn = len(players) - len(active_players)

    response.writeln("<p>")
    response.writeln("<a href=\"/atropine/%s/player?addplayer=1\">Add new player...</a>" % (htmlcommon.escape(tourney.get_name())))
    response.writeln("</p>")

    if not players:
        response.writeln("<p>")
        response.writeln("Your tourney doesn't have any players yet.")
        if tourney.get_num_games() == 0:
            response.writeln("You can add players with the link above or you can paste a list of players on the <a href=\"/atropine/%s/tourneysetup\">Tourney Setup</a> page." % (htmlcommon.escape(tourney.get_name())))
        else:
            response.writeln("Yet somehow you've managed to create fixtures. I'm not quite sure how you've managed that, but meh. You can add players using the form below.")
        response.writeln("</p>")

    response.writeln("<table class=\"playerlisttable\">")
    for div in range(num_divisions):
        div_players = [x for x in players if x.get_division() == div]
        div_players = sorted(div_players, key=lambda x : x.get_name())

        num_active_players = len([ x for x in div_players if not x.is_withdrawn() ])
        response.writeln("<tr class=\"playerlistdivision\"><td colspan=\"2\" class=\"playerlistdivision\">")
        response.writeln("<span style=\"font-weight: bold; float: left;\">")
        if num_divisions == 1:
            response.writeln(htmlcommon.escape(tourney.get_name()))
        else:
            response.writeln(htmlcommon.escape(tourney.get_division_name(div)))
        response.writeln("</span>")
        response.writeln("<span style=\"color: gray; float: right;\" title=\"Number of active players in %s\">%d</span>" % ("the tournament" if num_divisions == 1 else "this division", num_active_players))
        response.writeln("</td></tr>")

        for p in div_players:
            player_selected = (player and player.get_name() == p.get_name())

            response.writeln("<tr class=\"playerlistrow %s\">" % ("playerlistrowselected" if player_selected else ""));

            response.writeln("<td class=\"playerlistname\">");
            response.writeln(htmlcommon.player_to_link(p, tourney.get_name(), emboldenise=player_selected, withdrawn=p.is_withdrawn()))
            response.writeln("</td>")

            response.writeln("<td class=\"playerlistflags\">")
            if p.is_prune():
                response.write("&nbsp;<span title=\"Prune\">&#9898;</span>")
            if p.is_avoiding_prune():
                response.write("&nbsp;<span title=\"Swiss fixture generator will behave as if this player has already played a Prune\">&#9899;</span>")
            if p.is_requiring_accessible_table():
                response.write("&nbsp;<span title=\"Requires accessible table\">&#9855;</span>");
            if p.is_newbie():
                response.write("&nbsp;<span title=\"Newbie\">&#x1F476;</span>")
            pref_table = p.get_preferred_table()
            if pref_table is not None:
                response.write("&nbsp;<span title=\"Prefers table %d\"><div class=\"tablebadgenaturalsize\">%d</div></span>" % (pref_table, pref_table))
            response.writeln("</td>")
            response.writeln("</tr>")
    response.writeln("</table>")
    response.writeln("</div>") # end list pane
    response.writeln("</div>") # end list pane container

    response.writeln("<div class=\"playersetupformpanecontainer\">")
    response.writeln("<div class=\"playersetupformpane\">")

    if player:
        response.writeln("<h1>%s%s</h1>" % (htmlcommon.escape(player_name), " (withdrawn)" if player.is_withdrawn() else ""))
    elif add_player:
        response.writeln("<h1>Add new player</h1>")

    for (html, exc) in exceptions_to_show:
        response.writeln(html)
        if exc is not None:
            htmlcommon.show_tourney_exception(response, exc)

    if edit_notifications:
        write_h2(response, player, "Player details changed")
        response.writeln("<blockquote>")

    for item in edit_notifications:
        response.writeln("<li>%s</li>" % (htmlcommon.escape(item)))

    if edit_notifications:
        response.writeln("</blockquote>")
        response.writeln("<blockquote>")
        if player:
            response.writeln("<a href=\"/atropine/%s/player/%d\">OK</a>" % (htmlcommon.escape(tourney.get_name()), player.get_id()))
        else:
            response.writeln("<a href=\"/atropine/%s/player\">OK</a>" % (htmlcommon.escape(tourney.get_name())))
        response.writeln("</blockquote>")

    if player_name_deleted:
        response.writeln("<h1>Player deleted</h1>")
        response.writeln("<blockquote>")
        response.writeln(("<li>%s has been deleted. If you didn't mean to do " +
                "this, you can add them again on the " +
                "<a href=\"/atropine/%s/player?addplayer=1\">Add New Player</a> page.</li>") % (
                    htmlcommon.escape(player_name_deleted),
                    htmlcommon.escape(tourney.get_name())
                )
        )
        response.writeln("</blockquote>")


    if player:
        response.writeln("<hr />")
        def player_to_link(p):
            return htmlcommon.player_to_link(p, tourneyname, p == player)

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

            htmlcommon.show_warning_box(response, "<p>%s requires an accessible table, but their preferred table is table %d, which is not an accessible table. This player's requirement for an accessible table will be given a higher priority than their specific preference for table %d.</p><p>The accessible table numbers defined in <a href=\"/atropine/%s/tourneysetup\">Tourney Setup</a> are: %s%s.</p>" % (
                htmlcommon.escape(player.get_name()), pref_table, pref_table,
                htmlcommon.escape(tourney.get_name()),
                acc_list_preamble, acc_list
                ), wide=True)

        write_h2(response, player, "Edit player")
        htmlcommon.show_player_form(response, tourney, player)

        response.writeln("<hr />")

        write_h2(response, player, '%s player' % ("Reinstate" if player.is_withdrawn() else "Withdraw"))
        show_player_withdrawal_form(response, tourney, player)

        response.writeln("<hr />")

        games = tourney.get_games()

        games = [x for x in games if x.contains_player(player)]

        standings = tourney.get_standings(player.get_division())
        rank_method = tourney.get_rank_method()
        standing = None
        for s in standings:
            if s.name == player.get_name():
                standing = s
                break
        else:
            response.writeln("<p>%s isn't in the standings table for %s. This is... odd.</p>" % (htmlcommon.escape(player.get_name()), htmlcommon.escape(tourney.get_division_name(player.get_division()))))

        if not games:
            write_h2(response, player, "Delete player")
            show_player_delete_form(response, tourney, player)
        else:
            write_h2(response, player, "Games")

            # Show win-loss summary first
            form_dict = tourney.get_player_win_loss_strings(game_type=None, player=player)
            if len(form_dict) > 0:
                # form_dict will contain only one element
                form = htmlcommon.win_loss_string_to_html(form_dict[next(iter(form_dict))])
            else:
                form = None
            win_loss_record = "%d-%d" % (standing.wins, standing.played - standing.wins - standing.draws)
            if standing.draws:
                win_loss_record += "-%d" % (standing.draws)
            if form:
                response.writeln("<p>%s %s</p>" % (form, win_loss_record))

            # Now show all games involving this player
            htmlcommon.show_games_as_html_table(response, games, False, None, True, lambda x : tourney.get_short_round_name(x), player_to_link)

        response.writeln("<hr />")
        write_h2(response, player, "Stats Corner")
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

            response.writeln("<table class=\"misctable\">")
            response.writeln("<tr><th colspan=\"2\">%s</th></tr>" % (htmlcommon.escape(player.get_name())))
            response.writeln("<tr><td class=\"text\">Rating</td>")
            response.writeln("<td class=\"number\">%g</td></tr>" % (player.get_rating()))
            response.writeln("<tr><td class=\"text\">Tournament rating</td>")
            if standing.tournament_rating is not None:
                response.writeln("<td class=\"number\">%.2f</td></tr>" % (standing.tournament_rating))
            else:
                response.writeln("<td class=\"number\"></td></tr>")
            response.writeln("<tr><td class=\"text\">Position%s</td>" % (indiv_string))
            response.writeln("<td class=\"number\">%s</td></tr>" % (htmlcommon.ordinal_number(standing.position)))
            if seed is not None:
                response.writeln("<tr><td class=\"text\">Rating rank%s</td>" % (indiv_string))
                response.writeln("<td class=\"number\">%s</td></tr>" % (htmlcommon.ordinal_number(seed)))

            response.writeln("<tr><td class=\"text\">Games played</td>")
            response.writeln("<td class=\"number\">%d</td></tr>" % (standing.played))
            response.writeln("<tr><td class=\"text\">Wins</td>")
            response.writeln("<td class=\"number\">%d</td></tr>" % (standing.wins))
            response.writeln("<tr><td class=\"text\">Draws</td>")
            response.writeln("<td class=\"number\">%d</td></tr>" % (standing.draws))
            if highest_score is not None:
                response.writeln("<tr><td class=\"text\">Highest score</td>")
                response.writeln("<td class=\"number\">%d</td></tr>" % (highest_score))
            if lowest_score is not None:
                response.writeln("<tr><td class=\"text\">Lowest score</td>")
                response.writeln("<td class=\"number\">%d</td></tr>" % (lowest_score))
            response.writeln("<tr><td class=\"text\">Points scored</td>")
            response.writeln("<td class=\"number\">%d</td></tr>" % (standing.points))
            response.writeln("<tr><td class=\"text\">Points against</td>")
            response.writeln("<td class=\"number\">%d</td></tr>" % (-(standing.spread - standing.points)))
            response.writeln("<tr><td class=\"text\">Spread</td>")
            response.writeln("<td class=\"number\">%+d</td></tr>" % (standing.spread))
            response.writeln("<tr><td class=\"text\">Played 1st/2nd</td>")
            response.writeln("<td class=\"number\">%d/%d</td></tr>" % (standing.played_first, standing.played - standing.played_first))

            # Anything else which isn't covered above but is something we're using
            # to rank the standings table, put that here.
            sec_rank_headings = rank_method.get_secondary_rank_headings()
            sec_rank_values = standing.get_secondary_rank_value_strings()
            for i in range(len(sec_rank_headings)):
                heading = sec_rank_headings[i]
                if heading not in ("Points", "Spread"):
                    response.writeln("<tr>")
                    response.writeln("<td class=\"text\">%s</td>" % (htmlcommon.escape(heading)))
                    response.writeln("<td class=\"number\">%s</td>" % (htmlcommon.escape(sec_rank_values[i])))
                    response.writeln("</tr>")
            response.writeln("</table>")
        response.writeln("<hr />")
    elif add_player:
        htmlcommon.show_player_form(response, tourney, None)

    response.writeln("</div>") # end form pane
    response.writeln("</div>") # end form pane container
    response.writeln("</div>") # end double-pane container

    response.writeln("</div>") # end main pane

    # Invisible dialog box which appears when we're about to delete a player
    response.writeln(htmldialog.get_html("playerdialog"))

    response.writeln("</body>")
    response.writeln("</html>")
