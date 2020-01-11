#!/usr/bin/python3

import random;
import countdowntourney;
import htmlform;
import cgicommon
import urllib.request, urllib.parse, urllib.error;
import re
import fixgen
import json

name = "Manual Pairings/Groups"
description = "Player groups are specified manually. A fixture is generated between each pair in a group. Use this fixture generator if you're generating fixtures yourself, for example by picking names out of a hat."

INTERFACE_DROP_DOWN = 0
INTERFACE_AUTOCOMPLETE = 1
INTERFACE_DATALIST = 2

interface_type = INTERFACE_AUTOCOMPLETE

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def lookup_player(players, name):
    for p in players:
        if p.get_name().lower() == name.lower():
            return p;
    return None

def get_user_form(tourney, settings, div_rounds):
    num_divisions = tourney.get_num_divisions()
    div_table_sizes = dict()
    players = sorted(tourney.get_active_players(), key=lambda x : x.get_name());

    latest_round_no = tourney.get_latest_round_no()
    if latest_round_no is None:
        latest_round_no = 0

    prev_settings = settings.get_previous_settings()
    for key in prev_settings:
        if key not in settings and re.match("^d[0-9]*_groupsize$", key):
            settings[key] = prev_settings[key]
    if settings.get("submitrestore", None):
        for key in prev_settings:
            if key not in ["submit", "submitrestore", "submitplayers"]:
                settings[key] = prev_settings[key]

    elements = []
    elements.append(htmlform.HTMLFormHiddenInput("tablesizesubmit", "1"))
    elements.append(htmlform.HTMLFormHiddenInput("roundno", str(latest_round_no + 1)))

    # If there's a previously-saved form for this round, offer to load it
    prev_settings = settings.get_previous_settings()
    round_no = int_or_none(prev_settings.get("roundno", None))
    if round_no is not None and round_no == latest_round_no + 1:
        elements.append(htmlform.HTMLFragment("<div class=\"infoboxcontainer\">"))
        elements.append(htmlform.HTMLFragment("<div class=\"infoboximage\">"))
        elements.append(htmlform.HTMLFragment("<img src=\"/images/info.png\" alt=\"Info\" />"))
        elements.append(htmlform.HTMLFragment("</div>"))
        elements.append(htmlform.HTMLFragment("<div class=\"infoboxmessagecontainer\">"))
        elements.append(htmlform.HTMLFragment("<div class=\"infoboxmessage\">"))
        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(htmlform.HTMLFragment("There is an incomplete fixtures form saved. Do you want to carry on from where you left off?"))
        elements.append(htmlform.HTMLFragment("</p>"))
        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(htmlform.HTMLFormSubmitButton("submitrestore", "Restore previously-saved form"))
        elements.append(htmlform.HTMLFragment("</p>"))
        elements.append(htmlform.HTMLFragment("</div></div></div>"))

    for div_index in div_rounds:
        div_players = [x for x in players if x.get_division() == div_index]
        table_size = None
        table_size_name = "d%d_groupsize" % (div_index)
        if settings.get(table_size_name, None) is not None:
            try:
                div_table_sizes[div_index] = int(settings.get(table_size_name))
            except ValueError:
                div_table_sizes[div_index] = None
        else:
            div_table_sizes[div_index] = None
        choices = []

        # Number of groups may be specified by fully-manual generator.
        # If it isn't, then use all the players.
        num_groups = int_or_none(settings.get("d%d_num_groups" % (div_index)))
        if num_groups:
            if div_table_sizes[div_index] is not None and div_table_sizes[div_index] <= 0:
                raise countdowntourney.FixtureGeneratorException("%s: invalid table size for fully-manual setup." % (tourney.get_division_name(div_index)))

        for size in (2,3,4,5):
            if num_groups or len(div_players) % size == 0:
                choices.append(htmlform.HTMLFormChoice(str(size), str(size), size == div_table_sizes[div_index]))
        if len(div_players) >= 8:
            choices.append(htmlform.HTMLFormChoice("-5", "5&3", div_table_sizes[div_index] == -5))
        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<h2>%s</h2>" % (cgicommon.escape(tourney.get_division_name(div_index)))))
        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(htmlform.HTMLFormRadioButton(table_size_name, "Players per table", choices))
        elements.append(htmlform.HTMLFragment("</p>"))

    all_table_sizes_given = True
    for div in div_table_sizes:
        if div_table_sizes.get(div) is None:
            all_table_sizes_given = False

    if not all_table_sizes_given or not(settings.get("tablesizesubmit", "")):
        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(htmlform.HTMLFormSubmitButton("submit", "Submit table sizes and select players"))
        elements.append(htmlform.HTMLFragment("</p>"))
        return htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s" % (urllib.parse.quote_plus(tourney.name)), elements)
    
    show_already_assigned_players = bool(settings.get("showallplayers"))

    div_num_slots = dict()
    for div_index in div_rounds:
        num_groups = int_or_none(settings.get("d%d_num_groups" % (div_index)))
        div_players = [x for x in players if x.get_division() == div_index];
        table_size = div_table_sizes[div_index]

        if num_groups:
            # If num_groups is specified, then we can't use the 5&3 setup.
            # If it's any other table setup then the number of player slots is
            # the number of players per table times num_groups.
            if table_size <= 0:
                raise countdowntourney.FixtureGeneratorException("%s: invalid table size for fully-manual setup" % (tourney.get_division_name(div_index)))
            else:
                num_slots = table_size * num_groups
        else:
            # If num_groups is not specified, then the number if slots is
            # simply the number of active players in this division.
            num_slots = len(div_players)

        div_num_slots[div_index] = num_slots

        if table_size > 0 and num_slots % table_size != 0:
            raise countdowntourney.FixtureGeneratorException("%s: table size of %d is not allowed, as the number of player slots (%d) is not a multiple of it." % (tourney.get_division_name(div_index), table_size, num_slots))

        if table_size == -5 and num_slots < 8:
            raise countdowntourney.FixtureGeneratorException("%s: can't use table sizes of five and three - you need at least 8 players and you have %d" % (tourney.get_division_name(div_index), num_slots))

        if table_size not in (2,3,4,5,-5):
            raise countdowntourney.FixtureGeneratorException("%s: invalid table size: %d" % (tourney.get_division_name(div_index), table_size))

    div_set_players = dict()
    div_duplicate_slots = dict()
    div_empty_slots = dict()
    div_invalid_slots = dict()
    div_count_in_standings = dict()
    div_set_text = dict()
    div_game_type = dict()
    all_filled = True
    for div_index in div_rounds:
        div_players = [x for x in players if x.get_division() == div_index];
        num_groups = int_or_none(settings.get("d%d_num_groups" % (div_index)))

        num_slots = div_num_slots[div_index]

        set_players = [ None for i in range(0, num_slots) ];
        set_text = [ "" for i in range(0, num_slots) ]

        game_type = settings.get("d%d_game_type" % (div_index))

        if not game_type:
            if not settings.get("submitplayers"):
                count_in_standings = True
            else:
                count_in_standings = settings.get("d%d_heats" % (div_index))
                if count_in_standings is None:
                    count_in_standings = False
                else:
                    count_in_standings = True
        else:
            count_in_standings = (game_type == "P")

        # Slot numbers which contain text that doesn't match any player name
        invalid_slots = []

        # Ask the user to fill in N little drop-down boxes, where N is the
        # number of players, to decide who's going on what table.
        for player_index in range(0, num_slots):
            name = settings.get("d%d_player%d" % (div_index, player_index));
            if name is None:
                name = ""
            set_text[player_index] = name
            if name:
                set_players[player_index] = lookup_player(div_players, name);
                if set_players[player_index] is None:
                    invalid_slots.append(player_index)
            else:
                set_players[player_index] = None
    
        # Slot numbers which contain a player already contained in another slot
        duplicate_slots = [];

        # Slot numbers which don't contain a player
        empty_slots = [];

        player_index = 0;
        for p in set_players:
            if player_index in invalid_slots:
                all_filled = False
            elif p is None:
                empty_slots.append(player_index);
                all_filled = False;
            else:
                count = 0;
                for q in set_players:
                    if q is not None and q.get_name() == p.get_name():
                        count += 1;
                if count > 1:
                    duplicate_slots.append(player_index);
                    all_filled = False;
            player_index += 1;

        div_set_players[div_index] = set_players
        div_duplicate_slots[div_index] = duplicate_slots
        div_empty_slots[div_index] = empty_slots
        div_invalid_slots[div_index] = invalid_slots
        div_count_in_standings[div_index] = count_in_standings
        div_set_text[div_index] = set_text
        div_game_type[div_index] = game_type

    interface_type = int_or_none(settings.get("interfacetype", INTERFACE_AUTOCOMPLETE))

    if all_filled and settings.get("submitplayers"):
        # All slots filled, don't need to ask the user anything more
        return None

    elements = [];
    elements.append(htmlform.HTMLFormHiddenInput("roundno", str(latest_round_no + 1)))
    elements.append(htmlform.HTMLFragment("""<style type=\"text/css\">
table.seltable {
    margin-top: 20px;
}
.seltable td {
    padding: 2px;
    border: 2px solid white;
}
td.tablenumber {
    font-family: "Cabin";
    background-color: blue;
    color: white;
    text-align: center;
    min-width: 1.5em;
}
.duplicateplayer {
    background-color: violet;
}
.emptyslot {
    /*background-color: #ffaa00;*/
}
.invalidslot {
    background-color: red;
}
.validslot {
    background-color: #00cc00;
}
</style>
"""));
    elements.append(htmlform.HTMLFragment("""<script>
function set_unsaved_data_warning() {
    if (window.onbeforeunload == null) {
        window.onbeforeunload = function() {
            return "You have modified entries on this page and not submitted them. If you navigate away from the page, these changes will be lost.";
        };
    }
}

function unset_unsaved_data_warning() {
    window.onbeforeunload = null;
}
</script>
"""));

    autocomplete_script = "<script>\n"
    autocomplete_script += "var divPlayerNames = ";

    div_player_names = {}
    for div_index in div_rounds:
        name_list = [ x.get_name() for x in players if x.get_division() == div_index ]
        div_player_names[div_index] = name_list
    autocomplete_script += json.dumps(div_player_names, indent=4) + ";\n"

    autocomplete_script += """
function setLastEditedBox(controlId) {
    var lastEdited = document.getElementById("lasteditedinput");
    if (lastEdited != null) {
        lastEdited.value = controlId;
    }
}

function editBoxEdit(divIndex, controlId) {
    var control = document.getElementById(controlId);
    if (control == null)
        return;

    setLastEditedBox(controlId);

    var value = control.value;
    //console.log("editBoxEdit() called, value " + value);
    var previousValue = control.getAttribute("previousvalue");

    /* If the change has made the value longer, then proceed. Otherwise don't
       do any autocompletion because that would interfere with the user's
       attempt to backspace out the text. */
    //console.log("editBoxEdit() called, value " + value + ", previousValue " + previousValue);

    control.setAttribute("previousvalue", value);

    if (previousValue != null && value.length <= previousValue.length) {
        return;
    }

    /* Take the portion of the control's value from the start of the string
       to the start of the selected part. If that string is the start of
       exactly one player's name, then:
       1. Set the control's value to the player's full name
       2. Highlight the added portion
       3. Leave the cursor where it was before.
    */
    var validNames = divPlayerNames[divIndex];
    if (validNames) {
        var lastMatch = null;
        var numMatches = 0;
        var selStart = control.selectionStart;

        // head is the part the user typed in, i.e. the bit not highlighted
        var head = value.toLowerCase().substring(0, selStart);
        for (var i = 0; i < validNames.length; ++i) {
            if (validNames[i].toLowerCase().startsWith(head)) {
                numMatches++;
                lastMatch = validNames[i];
            }
        }

        if (numMatches == 1) {
            control.focus();
            control.value = lastMatch;
            control.setSelectionRange(head.length, lastMatch.length);
        }
    }
}
""";

    autocomplete_script += "</script>\n"
    elements.append(htmlform.HTMLFragment(autocomplete_script))

    elements.append(htmlform.HTMLFragment("<p>Enter player names below. Each horizontal row is one group, or table.</p>"))

    choice_data = [
            ("Auto-completing text boxes", INTERFACE_AUTOCOMPLETE),
            ("Drop-down boxes", INTERFACE_DROP_DOWN),
            ("Combo boxes (not supported on all browsers)", INTERFACE_DATALIST)
    ]
    choices = [ htmlform.HTMLFormChoice(str(x[1]), x[0], interface_type == x[1]) for x in choice_data ]
    interface_menu = htmlform.HTMLFormRadioButton("interfacetype", "Player name selection interface", choices)
    elements.append(interface_menu)

    if interface_type == INTERFACE_DROP_DOWN:
        elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
        elements.append(htmlform.HTMLFormCheckBox("showallplayers", "Show all players in drop-down boxes, even those already assigned a table", show_already_assigned_players))
        elements.append(htmlform.HTMLFragment("</div>"))

    (acc_tables, acc_default) = tourney.get_accessible_tables()

    table_no = 1;
    for div_index in div_rounds:
        div_players = [x for x in players if x.get_division() == div_index];
        player_index = 0;
        table_size = div_table_sizes[div_index]
        duplicate_slots = div_duplicate_slots[div_index]
        invalid_slots = div_invalid_slots[div_index]
        empty_slots = div_empty_slots[div_index]
        set_players = div_set_players[div_index]
        set_text = div_set_text[div_index]
        num_slots = div_num_slots[div_index]
        game_type = div_game_type[div_index]

        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<h2>%s</h2>" % (cgicommon.escape(tourney.get_division_name(div_index)))))

        if not game_type:
            # Ask the user if they want these games to count towards the
            # standings table (this is pretty much universally yes)
            elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
            elements.append(htmlform.HTMLFormCheckBox("d%d_heats" % (div_index), "Count the results of these matches in the standings table", div_count_in_standings[div_index]))
            elements.append(htmlform.HTMLFragment("</div>"))

        # Show the table of groups for the user to fill in
        elements.append(htmlform.HTMLFragment("<table class=\"seltable\">\n"));
        prev_table_no = None;
        unselected_names = [x.get_name() for x in div_players];

        if table_size > 0:
            table_sizes = [table_size for i in range(0, num_slots // table_size)]
        else:
            table_sizes = countdowntourney.get_5_3_table_sizes(num_slots)

        for p in set_players:
            if p and p.get_name() in unselected_names:
                unselected_names.remove(p.get_name())
        
        for table_size in table_sizes:
            elements.append(htmlform.HTMLFragment("<tr>\n"))
            elements.append(htmlform.HTMLFragment(
                "<td>%s</td><td class=\"tablenumber\">%d</td>\n" % (
                    " &#9855;" if (table_no in acc_tables) != acc_default else "",
                    table_no
                )
            ));
            if game_type is not None:
                elements.append(htmlform.HTMLFragment("<td class=\"fixturegametype\">%s</td>" % (cgicommon.escape(game_type, True))))
            for i in range(table_size):
                p = set_players[player_index]
                td_style = "";
                value_is_valid = False
                if player_index in duplicate_slots:
                    td_style = "class=\"duplicateplayer\"";
                elif player_index in empty_slots:
                    td_style = "class=\"emptyslot\"";
                elif player_index in invalid_slots:
                    td_style = "class=\"invalidslot\"";
                else:
                    td_style = "class=\"validslot\"";
                    value_is_valid = True
                elements.append(htmlform.HTMLFragment("<td %s>" % td_style));

                # Make a drop down list with every unassigned player in it
                player_option_list = [];

                if interface_type == INTERFACE_DROP_DOWN:
                    # Drop-down list needs an initial "nothing selected" option
                    player_option_list.append(htmlform.HTMLFormDropDownOption("", " -- select --"));
                selected_name = "";
                
                if show_already_assigned_players:
                    name_list = [ x.get_name() for x in div_players ]
                else:
                    if p:
                        name_list = sorted(unselected_names + [p.get_name()])
                    else:
                        name_list = unselected_names

                for q in name_list:
                    if p is not None and q == p.get_name():
                        selected_name = p.get_name()
                    if interface_type == INTERFACE_DROP_DOWN:
                        player_option_list.append(htmlform.HTMLFormDropDownOption(q, q))
                    else:
                        player_option_list.append(q)
                if interface_type != INTERFACE_DROP_DOWN and not selected_name:
                    selected_name = set_text[player_index]

                # Select the appropriate player
                control_name = "d%d_player%d" % (div_index, player_index)
                if interface_type == INTERFACE_DATALIST:
                    sel = htmlform.HTMLFormComboBox(control_name, player_option_list, other_attrs={"onchange": "set_unsaved_data_warning();"})
                elif interface_type == INTERFACE_DROP_DOWN:
                    sel = htmlform.HTMLFormDropDownBox(control_name, player_option_list, other_attrs={"onchange": "set_unsaved_data_warning();"});
                elif interface_type == INTERFACE_AUTOCOMPLETE:
                    sel = htmlform.HTMLFormTextInput("",
                            control_name,
                            selected_name,
                            other_attrs={"oninput":"editBoxEdit(%d, \"%s\");" % (div_index, control_name),
                                "onclick" : "if (this.selectionStart == this.selectionEnd) { this.select(); }",
                                "id" : control_name,
                                "validvalue" : "1" if value_is_valid else "0",
                                "previousvalue" : selected_name,
                                "class" : "playerslot"
                            }
                    )
                else:
                    sel = None

                sel.set_value(selected_name);

                elements.append(sel);
                elements.append(htmlform.HTMLFragment("</td>"));
                player_index += 1
            table_no += 1
            elements.append(htmlform.HTMLFragment("</tr>\n"))

        elements.append(htmlform.HTMLFragment("</table>\n"));

        if len(acc_tables) > 0:
            # Warn the user that the table numbers displayed above might not
            # end up being the final table numbers.
            elements.append(htmlform.HTMLFragment("<p style=\"font-size: 10pt\">Note: You have designated accessible tables, so the table numbers above may be automatically reassigned to fulfil accessibility requirements.</p>"))

        # Add the submit button
        elements.append(htmlform.HTMLFragment("<p>\n"))
        elements.append(htmlform.HTMLFormHiddenInput("submitplayers", "1"))
        elements.append(htmlform.HTMLFormHiddenInput("lasteditedinput", "", other_attrs={"id" : "lasteditedinput"}))
        elements.append(htmlform.HTMLFormSubmitButton("submit", "Submit", other_attrs={ "onclick": "unset_unsaved_data_warning();", "class" : "bigbutton" }));
        elements.append(htmlform.HTMLFragment("</p>\n"))

        if invalid_slots:
            elements.append(htmlform.HTMLFragment("<p>You have slots with unrecognised player names; these are highlighted in <span style=\"color: red; font-weight: bold;\">red</span>.</p>"));
        if duplicate_slots:
            elements.append(htmlform.HTMLFragment("<p>You have players in multiple slots; these are highlighted in <span style=\"color: violet; font-weight: bold;\">violet</span>.</p>"));

        if unselected_names:
            elements.append(htmlform.HTMLFragment("<p>Players still to be given a table:\n"));
            for i in range(len(unselected_names)):
                name = unselected_names[i]
                elements.append(htmlform.HTMLFragment("%s%s" % (cgicommon.escape(name, True), "" if i == len(unselected_names) - 1 else ", ")));
            elements.append(htmlform.HTMLFragment("</p>\n"));

        elements.append(htmlform.HTMLFormHiddenInput("d%d_groupsize" % (div_index), str(div_table_sizes[div_index])))

        show_standings = int_or_none(settings.get("d%d_show_standings" % (div_index)))
        if show_standings:
            elements.append(htmlform.HTMLFormStandingsTable("d%d_standings" % (div_index), tourney, div_index))

    last_edited_input_name = settings.get("lasteditedinput", "")
    set_element_focus_script = """
<script>
var lastEditedElementName = %s;

var playerBoxes = document.getElementsByClassName("playerslot");
var playerBoxesBefore = [];
var playerBoxesAfter = [];
var foundElement = false;

for (var i = 0; i < playerBoxes.length; ++i) {
    if (playerBoxes[i].name == lastEditedElementName) {
        foundElement = true;
    }
    if (foundElement) {
        playerBoxesAfter.push(playerBoxes[i]);
    }
    else {
        playerBoxesBefore.push(playerBoxes[i]);
    }
}
//console.log("playerBoxesAfter " + playerBoxesAfter.length.toString() + ", playerBoxesBefore " + playerBoxesBefore.length.toString());

/* Give focus to the first text box equal to or after this one which
   does not have a valid value in it. If there are no such text boxes,
   search from the beginning of the document onwards. */
var playerBoxOrder = playerBoxesAfter.concat(playerBoxesBefore);

for (var i = 0; i < playerBoxOrder.length; ++i) {
    var box = playerBoxOrder[i];
    var validValue = box.getAttribute("validvalue");
    if (validValue == null || validValue == "0") {
        box.focus();
        box.select();
        break;
    }
}
</script>
""" % (json.dumps(last_edited_input_name))
    elements.append(htmlform.HTMLFragment(set_element_focus_script))

    form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s" % (urllib.parse.quote_plus(tourney.name)), elements);
    return form;

def check_ready(tourney, div_rounds):
    for div in div_rounds:
        round_no = div_rounds[div]
        existing_games = tourney.get_games(round_no=round_no, game_type="P", division=div)
        if existing_games:
            return (False, "%s: round %d already has %d games in it." % (tourney.get_division_name(div), round_no, len(existing_games)))
    return (True, None)

def generate(tourney, settings, div_rounds):
    num_divisions = tourney.get_num_divisions()
    div_table_sizes = dict()

    players = tourney.get_active_players();
    for div_index in div_rounds:
        table_size = int_or_none(settings.get("d%d_groupsize" % (div_index)))
        div_players = [x for x in players if x.get_division() == div_index]

        # Reject if table size is not specified
        if table_size is None:
            raise countdowntourney.FixtureGeneratorException("%s: No table size specified" % tourney.get_division_name(div_index))
        else:
            try:
                table_size = int(table_size)
            except ValueError:
                raise countdowntourney.FixtureGeneratorException("%s: Invalid table size %s" % (tourney.get_division_name(div_index), table_size))

        # Reject if table size is nonsense
        if table_size not in (2,3,4,5,-5):
            raise countdowntourney.FixtureGeneratorException("%s: Invalid table size: %d" % (tourney.get_division_name(div_index), table_size))

        # Work out the number of player slots we're generating for this
        # division. This may be implied by the number of groups, or if that's
        # not given, it's the number of active players in this division.
        num_groups = int_or_none(settings.get("d%d_num_groups" % (div_index)))
        if num_groups is None:
            # No number of groups specified, so the number of players is all
            # the active players in this division.
            num_slots = len(div_players)
        else:
            if table_size <= 1:
                raise countdowntourney.FixtureGeneratorException("%s: invalid number of players per table for fully-manual setup." % (tourney.get_division_name(div_ikndeX)))
            num_slots = num_groups * table_size

        
        if table_size > 0:
            if num_slots % table_size != 0:
                raise countdowntourney.FixtureGeneratorException("%s: Number of player slots (%d) is not a multiple of the table size (%d)" % (tourney.get_division_name(div_index), num_slots, table_size))
            table_sizes = [ table_size for i in range(0, num_slots // table_size) ]
        else:
            if num_slots < 8:
                raise countdowntourney.FixtureGeneratorException("%s: Can't use a 5&3 configuration if there are fewer than 8 player slots, and there are %d" % (tourney.get_division_name(div_index), num_slots))
            table_sizes = countdowntourney.get_5_3_table_sizes(num_slots)
        div_table_sizes[div_index] = table_sizes

    (ready, excuse) = check_ready(tourney, div_rounds);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    #latest_round_no = tourney.get_latest_round_no('P')
    #if latest_round_no is None:
    #    round_no = 1
    #else:
    #    round_no = latest_round_no + 1

    generated_groups = fixgen.GeneratedGroups()
    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        groups = [];
        table_sizes = div_table_sizes[div_index]
        div_players = [x for x in players if x.get_division() == div_index]
        game_type = settings.get("d%d_game_type" % (div_index))
        if not game_type:
            if settings.get("d%d_heats" % (div_index)):
                game_type = "P"
            else:
                game_type = "N"

        num_slots = 0
        for size in table_sizes:
            num_slots += size

        # Player names should have been specified by a series of drop-down
        # boxes.
        player_names = [];
        for i in range(0, num_slots):
            name = settings.get("d%d_player%d" % (div_index, i));
            if name:
                player_names.append(name);
            else:
                raise countdowntourney.FixtureGeneratorException("%s: Player %d not specified. This is probably a bug, as the form should have made you fill in all the boxes." % (tourney.get_division_name(div_index), i));

        selected_players = [lookup_player(div_players, x) for x in player_names];

        player_index = 0
        groups = []
        for size in table_sizes:
            group = []
            for i in range(size):
                group.append(selected_players[player_index])
                player_index += 1
            groups.append(group)

        for g in groups:
            generated_groups.add_group(round_no, div_index, g)
        generated_groups.set_repeat_threes(round_no, div_index, table_size == -5)

        round_name = settings.get("d%d_round_name" % (div_index))
        if round_name:
            generated_groups.set_round_name(round_no, round_name)
        generated_groups.set_game_type(round_no, div_index, game_type)

    return generated_groups

def save_form_on_submit():
    return True
