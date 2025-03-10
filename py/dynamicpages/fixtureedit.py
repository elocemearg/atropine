#!/usr/bin/python3

import htmlcommon
import countdowntourney

def show_player_selection(response, players, control_name, value=None):
    response.writeln("<select name=\"%s\">" % htmlcommon.escape(control_name, True));
    if value is None:
        response.writeln("<option value=\"\" selected>--- select player ---</option>")
    for p in players:
        player_name = p.get_name();
        if player_name == value:
            sel = " selected";
        else:
            sel = "";
        response.writeln("<option value=\"%s\"%s>%s</option>" % (htmlcommon.escape(player_name, True), sel, htmlcommon.escape(player_name)));
    response.writeln("</select>");

def lookup_player(players, name):
    for p in players:
        if p.get_name() == name:
            return p;
    raise countdowntourney.PlayerDoesNotExistException("Player \"%s\": I've never heard of them." % name);

def write_table_header_row(response, add_game, div_index):
    if not add_game:
        response.writeln("<tr>");
        response.writeln("<th colspan=\"5\"></th>")
        response.writeln("<th>Game type</th>")
        response.writeln("<th>Delete game?</th>")
        response.writeln("<th></th>")
        response.writeln("</tr>")
    response.writeln("<tr>")
    response.writeln("<th>Table</th>")
    if not add_game:
        response.writeln("<th></th>");
    response.writeln("<th>Player 1</th>")
    if not add_game:
        response.writeln("<th>Score</th>")
    else:
        response.writeln("<th></th>")
    response.writeln("<th>Player 2</th>")

    if add_game:
        response.writeln("<th>Game type</th>")
    else:
        response.writeln("<th>")
        response.writeln("<input type=\"button\" name=\"div%d_set_all\" value=\"Set all to match first game\" onclick=\"div_type_select(%d);\" />" % (div_index, div_index))
        response.writeln("</th>")
        response.writeln("<th>")
        response.writeln("<input type=\"button\" name=\"div%d_del_all\" value=\"All\" onclick=\"div_delete_select(%d, true);\" />" % (div_index, div_index))
        response.writeln("<input type=\"button\" name=\"div%d_del_none\" value=\"None\" onclick=\"div_delete_select(%d, false);\" />" % (div_index, div_index))
        response.writeln("</th>")

    if not add_game:
        response.writeln("<th></th>")
    response.writeln("</tr>");

def write_game_type_selection(response, game_types, selected_code, control_name, control_id):
    response.writeln("<select name=\"%s\" id=\"%s\">" % (control_name, control_id))
    for game_type in game_types:
        response.writeln("<option value=\"%s\" %s >%s (%s)</option>" % (
                htmlcommon.escape(game_type["code"], True),
                "selected" if selected_code == game_type["code"] else "",
                htmlcommon.escape(game_type["name"]),
                htmlcommon.escape(game_type["code"])
        ))
    response.writeln("</select>")


def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourney_name = tourney.name

    htmlcommon.print_html_head(response, "Edit fixtures: " + str(tourney_name), othercssfiles=["fixtures.css"])

    response.writeln("<body onload=\"relabel_save_button();\">");

    # Round number is mandatory and it's the first component of the path after
    # /atropine/<tourney>/fixtureedit/
    if len(extra_components) > 0:
        round_no = extra_components[0]
    else:
        round_no = None

    if not round_no:
        response.writeln("<h1>No round number specified</h1>");
        response.writeln("<p><a href=\"/\">Home</a></p>");
        response.writeln("</body></html>");
        return

    try:
        round_no = int(round_no);
    except ValueError:
        response.writeln("<h1>Round number is not a number</h1>");
        response.writeln("<p><a href=\"/\">Home</a></p>");
        response.writeln("</body></html>");
        return

    try:
        htmlcommon.show_sidebar(response, tourney);

        response.writeln("<div class=\"mainpane\">");

        round_name = tourney.get_round_name(round_no);
        response.writeln("<h1>Fixture editor: %s</h1>" % round_name);

        # Javascript function to tick/untick all heat game boxes for a division
        response.writeln("""
<script>
//<![CDATA[
// Set all drop-down boxes in this division to have the value of the first one
function div_type_select(div) {
    var idStub = "div" + div.toString() + "_gametype_";

    var dropDown = document.getElementById(idStub + "0");

    if (dropDown) {
        var selectedValue = null;
        for (var i = 0; i < dropDown.options.length; ++i) {
            if (dropDown.options[i].selected) {
                selectedValue = dropDown.options[i].text;
                break;
            }
        }
        if (selectedValue) {
            var otherDropDown;
            var num = 0;
            do {
                ++num;
                otherDropDown = document.getElementById(idStub + num.toString());
                if (otherDropDown) {
                    for (var i = 0; i < otherDropDown.options.length; ++i) {
                        if (otherDropDown.options[i].text == selectedValue) {
                            otherDropDown.options[i].selected = true;
                        }
                        else {
                            otherDropDown.options[i].selected = false;
                        }
                    }
                }
            } while (otherDropDown);
        }
    }
}

function relabel_save_button() {
    let button = document.getElementById("savebutton");
    if (button) {
        let numToAdd = 0;
        let numToDelete = 0;
        let label = "Save changes"
        let addBoxes = document.getElementsByClassName("addgamecheckbox");
        let deleteBoxes = document.getElementsByClassName("deletegamecheckbox");
        for (let i = 0; i < addBoxes.length; ++i) {
            if (addBoxes[i].checked)
                numToAdd++;
        }
        for (let i = 0; i < deleteBoxes.length; ++i) {
            if (deleteBoxes[i].checked)
                numToDelete++;
        }
        if (numToAdd > 0) {
            label += " and add " + numToAdd.toString() + " game" + (numToAdd == 1 ? "" : "s");
        }
        if (numToDelete > 0) {
            label += " and delete " + numToDelete.toString() + " game" + (numToDelete == 1 ? "" : "s");
        }
        button.value = label;
    }
}

function div_delete_select(div_index, checked) {
    let checkboxes = document.getElementsByClassName("deletegame_div" + div_index.toString());
    for (let i = 0; i < checkboxes.length; ++i) {
        checkboxes[i].checked = checked;
    }
    relabel_save_button();
}

function add_game_checkbox_click(div_index) {
    let addGameCheckBox = document.getElementById("addgame_div" + div_index.toString());
    let addGameDetailsBox = document.getElementById("addgamedetails_div" + div_index.toString());
    if (addGameDetailsBox && addGameCheckBox) {
        if (addGameCheckBox.checked) {
            addGameDetailsBox.style.display = "block";
        }
        else {
            addGameDetailsBox.style.display = "none";
        }
    }
    relabel_save_button();
}
//]]>
</script>
""")
        players = sorted(tourney.get_players(include_prune=True), key=lambda x : x.get_name());

        remarks = dict();
        remarks_add_game = dict()

        num_divisions = tourney.get_num_divisions()

        num_games_updated = None;
        num_games_deleted = 0
        add_game_divs_checked = set()
        add_game_divs_values = {}
        if "save" in form:
            games = tourney.get_games(round_no=round_no);
            alterations = []
            additions = []
            deletions = []
            for g in games:
                set1 = form.getfirst("gamep1_%d_%d" % (g.round_no, g.seq));
                set2 = form.getfirst("gamep2_%d_%d" % (g.round_no, g.seq));
                set_type = form.getfirst("gametype_%d_%d" % (g.round_no, g.seq))
                delete_game = form.getfirst("deletegame_%d_%d" % (g.round_no, g.seq))
                if delete_game and delete_game == "1":
                    deletions.append((g.round_no, g.seq))
                else:
                    new_p1 = lookup_player(players, set1);
                    new_p2 = lookup_player(players, set2);
                    if not set_type:
                        new_game_type = "P"
                    else:
                        new_game_type = set_type

                    if new_p1 == new_p2:
                        remarks[(g.round_no, g.seq)] = "Not updated (%s v %s): players can't play themselves" % (new_p1.get_name(), new_p2.get_name());
                    elif g.p1 != new_p1 or g.p2 != new_p2 or g.game_type != new_game_type:
                        alterations.append((g.round_no, g.seq, new_p1, new_p2, new_game_type));

            # Check the add-game section of each division form, and add the new
            # game details to "additions".
            for div_index in range(num_divisions):
                addgame = form.getfirst("addgame_div%d" % (div_index))
                if addgame:
                    # Add game box was checked for this division. Read the
                    # form elements...
                    add_game_divs_checked.add(div_index)
                    set1 = form.getfirst("addgame_p1_div%d" % (div_index))
                    set2 = form.getfirst("addgame_p2_div%d" % (div_index))
                    set_type = form.getfirst("addgame_type_div%d" % (div_index))
                    if not set_type:
                        new_game_type = "P"
                    else:
                        new_game_type = set_type
                    table_number = form.getfirst("addgame_table_div%d" % (div_index))

                    # add_game_divs_values[div_index] is set to what we want to
                    # set the form values to after the operation. If successful
                    # then we want them cleared, but if we fail then we want to
                    # leave the controls as they are so the user can correct the
                    # problem without having to set every field again.
                    add_game_divs_values[div_index] = {
                        "p1" : set1,
                        "p2" : set2,
                        "type" : set_type,
                        "table" : table_number
                    }
                    # If the table number is absent or anything other than a
                    # positive integer, reject it.
                    try:
                        if table_number is None:
                            raise ValueError
                        table_number = int(table_number)
                        if table_number <= 0:
                            raise ValueError
                    except ValueError:
                        table_number = None
                        del add_game_divs_values[div_index]["table"]
                        remarks_add_game[div_index] = "Not added: invalid table number"
                    if table_number is not None:
                        # If all is well, add (round_no, div, table_number, p1, p2, game_type) to additions.
                        try:
                            new_p1 = lookup_player(players, set1)
                            new_p2 = lookup_player(players, set2)
                            if new_p1 == new_p2:
                                remarks_add_game[div_index] = "Not added (%s v %s): players can't play themselves" % (new_p1.get_name(), new_p2.get_name())
                            else:
                                additions.append((round_no, div_index, table_number, new_p1, new_p2, new_game_type))
                                # Don't want to leave the Add Game checkbox
                                # checked after we successfully added the game.
                                add_game_divs_checked.remove(div_index)
                                del add_game_divs_values[div_index]
                        except countdowntourney.PlayerDoesNotExistException:
                            del add_game_divs_values[div_index]["p1"]
                            del add_game_divs_values[div_index]["p2"]
                            remarks_add_game[div_index] = "Not added: please select two valid players"

            # Now carry out any alterations, additions and deletions we've been
            # asked to do.
            if alterations:
                num_games_updated = tourney.alter_games(alterations);

            if additions:
                # Use tourney.merge_games() to add new games, giving each one a
                # new sequence number unique within that round.
                merged_games = []
                seq = tourney.get_max_game_seq_in_round(round_no)
                if seq is None:
                    seq = 1
                else:
                    seq += 1
                for (r, div_index, table_number, new_p1, new_p2, new_game_type) in additions:
                    new_game = countdowntourney.Game(r, seq, table_number, div_index, new_game_type, new_p1, new_p2);
                    merged_games.append(new_game)
                    seq += 1
                num_games_added = tourney.merge_games(merged_games)

            # Delete all games in "deletions" matching on (round_no, seq).
            if deletions:
                num_games_deleted = tourney.delete_games(deletions)

            for (r, seq, new_p1, new_p2, new_game_type) in alterations:
                remarks[seq] = "Updated";

        score_editor_url = "/atropine/%s/games/%d" % (htmlcommon.escape(tourney_name), round_no)
        round_name = tourney.get_round_name(round_no)
        response.writeln("""<p>
On this page you can add or remove games in this round, or change which players
are involved in a game.
</p>
<p>
You cannot use this page to enter or edit the score of a game. Use the
<a href="%s">%s Results Entry</a> page to do that.
</p>
""" % (score_editor_url, round_name))

        if num_games_updated:
            response.writeln("<p>%d games updated.</p>" % (num_games_updated));
        if num_games_deleted:
            response.writeln("<p>%d games deleted.</p>" % (num_games_deleted))

        game_types = countdowntourney.get_game_types()

        response.writeln("<div class=\"scorestable\">");
        response.writeln("<form method=\"POST\" action=\"/atropine/%s/fixtureedit/%d\">" % (htmlcommon.escape(tourney_name), round_no));
        for div_index in range(num_divisions):
            largest_table_size = 0
            last_table_size = 0
            games = tourney.get_games(round_no=round_no, division=div_index);
            games.sort(key=lambda g : (g.round_no, g.table_no, g.seq))

            if num_divisions > 1:
                response.writeln("<h2>%s</h2>" % (tourney.get_division_name(div_index)))
            response.writeln("<table class=\"scorestable\">");

            write_table_header_row(response, False, div_index)

            gamenum = 0;
            last_table_no = None;
            for g in games:
                game_player_names = g.get_player_names();
                tr_classes = ["gamerow"];

                if last_table_no is None or last_table_no != g.table_no:
                    tr_classes.append("firstgameintable");
                    # Count how many consecutive games appear with this table
                    # number, so we can group them together in the table.
                    num_games_on_table = 0;
                    while gamenum + num_games_on_table < len(games) and games[gamenum + num_games_on_table].table_no == g.table_no:
                        num_games_on_table += 1;
                    if num_games_on_table > largest_table_size:
                        largest_table_size = num_games_on_table
                    last_table_size = num_games_on_table
                    first_game_in_table = True;
                else:
                    first_game_in_table = False;

                response.writeln("<tr class=\"%s\">" % " ".join(tr_classes));

                # Table number and sequence number. The sequence number uniquely
                # identifies a game within a round.
                if first_game_in_table:
                    response.writeln("<td class=\"tableno\" rowspan=\"%d\"><div class=\"tablebadge\">%d</div></td>" % (num_games_on_table, g.table_no));
                response.writeln("<td class=\"gameseq\">%d</td>" % g.seq);

                # Dropdown box for player 1
                response.writeln("<td class=\"gameplayer1\">")
                show_player_selection(response, players, "gamep1_%d_%d" % (g.round_no, g.seq), game_player_names[0]);
                response.writeln("</td>");

                # Current score for the game, but you can't edit it on this page
                if g.is_complete():
                    score_str = g.format_score();
                else:
                    score_str = "-";
                response.writeln("<td class=\"gamescore\">%s</td>" % (htmlcommon.escape(score_str)));

                # Dropdown box for player 2
                response.writeln("<td class=\"gameplayer2\">")
                show_player_selection(response, players, "gamep2_%d_%d" % (g.round_no, g.seq), game_player_names[1]);
                response.writeln("</td>");

                # Dropdown box to change an existing game's type.
                response.writeln("<td class=\"gameheat\">")
                write_game_type_selection(response, game_types, g.game_type, "gametype_%d_%d" % (g.round_no, g.seq), "div%d_gametype_%d" % (div_index, gamenum))
                response.writeln("</td>")

                # Associate a checkbox with every existing game. If the checkbox
                # is checked when the user saves changes, we delete the game.
                response.writeln("<td style=\"text-align: center;\">")
                response.writeln("<input type=\"checkbox\" name=\"deletegame_%d_%d\" class=\"deletegamecheckbox deletegame_div%d\" value=\"1\" onclick=\"relabel_save_button();\" />" % (g.round_no, g.seq, div_index))
                response.writeln("</td>")

                # Remarks, such as "couldn't edit this game because..."
                this_game_remarks = remarks.get((g.round_no, g.seq), "")
                response.writeln("<td class=\"gameremarks\" %s>" % ("style=\"background-color: #ffff88;\"" if this_game_remarks else ""));
                response.writeln(htmlcommon.escape(this_game_remarks));
                response.writeln("</td>");
                response.writeln("</tr>");
                gamenum += 1;
                last_table_no = g.table_no;
            response.writeln("</table>");

            # Checkbox which when checked reveals some form elements to add a new
            # fixture to this division.
            response.writeln("<div class=\"addgamebox\">")
            response.writeln("<div>")
            response.writeln("<label for=\"addgame_div%d\"><input type=\"checkbox\" class=\"addgamecheckbox\" name=\"addgame_div%d\" id=\"addgame_div%d\" value=\"1\" onclick=\"add_game_checkbox_click(%d);\" %s /> Add new game</label>" % (
                div_index, div_index, div_index, div_index,
                "checked" if div_index in add_game_divs_checked else ""
            ))
            response.writeln("</div>")
            response.writeln("<div class=\"addgamedetails\" id=\"addgamedetails_div%d\" style=\"display: %s;\">" % (div_index, "block" if div_index in add_game_divs_checked else "none"))
            response.writeln("<table class=\"scorestable\">")
            write_table_header_row(response, True, div_index)
            response.writeln("<tr>")

            existing_values = add_game_divs_values.get(div_index, {})

            # If the last table has a full complement of players (at least as many
            # as the largest table), then if no table number was given on the
            # previous submission, the default value for the new game's table
            # number should be a new table number. Otherwise, the default
            # value should be the last table number.
            new_table_no = existing_values.get("table")
            if not new_table_no:
                if last_table_no:
                    if last_table_size < largest_table_size:
                        new_table_no = last_table_no
                    else:
                        new_table_no = last_table_no + 1
                else:
                    new_table_no = 1
            else:
                new_table_no = int(new_table_no)
            response.writeln("<td><input type=\"number\" name=\"addgame_table_div%d\" value=\"%d\" min=\"1\" style=\"width: 4em;\" /></td>" % (div_index, new_table_no))
            response.writeln("<td>")

            show_player_selection(response, players, "addgame_p1_div%d" % (div_index), value=existing_values.get("p1"))
            response.writeln("</td><td style=\"text-align: center;\">v</td><td>")
            show_player_selection(response, players, "addgame_p2_div%d" % (div_index), value=existing_values.get("p2"))
            response.writeln("</td>")
            response.writeln("<td class=\"gameheat\">")
            write_game_type_selection(response, game_types, existing_values.get("type"), "addgame_type_div%d" % (div_index), "addgame_type_div%d" % (div_index))
            response.writeln("</td>")

            # Remarks for this added game, if the user just tried to add a game
            # but failed.
            if div_index in remarks_add_game:
                rem = remarks_add_game[div_index]
            else:
                rem = ""
            response.writeln("<td class=\"gameremarks\" %s>%s</td>" % ("style=\"background-color: #ffff88;\"" if rem else "", rem))
            response.writeln("</tr>")
            response.writeln("</table>")
            response.writeln("</div>")
            response.writeln("</div>") #addgamebox

        response.writeln("<div>")
        response.writeln("<input type=\"submit\" class=\"bigbutton\" name=\"save\" value=\"Save changes\" id=\"savebutton\" />");
        response.writeln("</div>")
        response.writeln("</form>");

        response.writeln("</div>"); # scorestable

        response.writeln("</div>"); # mainpane

    except countdowntourney.TourneyException as e:
        htmlcommon.show_tourney_exception(response, e);

    response.writeln("</body>");
    response.writeln("</html>");
