#!/usr/bin/python3

import random;
import countdowntourney;
import htmlform;
import cgicommon
import gencommon
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

# Get the table size (2, 3, 4, 5, or -5) for each division, from the
# settings, and return it as a map of { div : size }
def get_div_table_sizes(settings, div_rounds):
    div_table_sizes = {}
    for div_index in div_rounds:
        table_size_name = "d%d_groupsize" % (div_index)
        if settings.get(table_size_name, None) is not None:
            try:
                div_table_sizes[div_index] = int(settings.get(table_size_name))
            except ValueError:
                div_table_sizes[div_index] = None
        else:
            div_table_sizes[div_index] = None
    return div_table_sizes

# Given a list of table sizes for a division (e.g. [3, 3, 3, 3]) and a slot
# index, return which table index this slot is on. Tables are numbered from 0.
# For example, if table_sizes is [5, 3, 3] and slot_index is 7, return 1.
def get_table_index_from_slot(table_sizes, slot_index):
    table_index = 0
    for size in table_sizes:
        if slot_index < size:
            return table_index
        table_index += 1
        slot_index -= size
    return None

# Given a list of table sizes for a division (e.g. [3, 3, 3, 3]) and a table
# index (numbered from 0), return a list of the slot numbers on that table.
# For example, if table_sizes is [5, 3, 3] and table_index is 1, we return
# [5, 6, 7].
def get_slots_on_table(table_sizes, table_index):
    base = sum(table_sizes[0:table_index])
    return [ base + i for i in range(table_sizes[table_index]) ]

class PlayerArrangement(object):
    def __init__(self, tourney, settings, div_rounds):
        num_divisions = tourney.get_num_divisions()
        div_table_sizes = get_div_table_sizes(settings, div_rounds)
        players = sorted(tourney.get_active_players(), key=lambda x : x.get_name())
        div_num_slots = {}
        div_table_size_list = {}

        for div_index in div_rounds:
            num_groups = int_or_none(settings.get("d%d_num_groups" % (div_index)))
            div_players = [x for x in players if x.get_division() == div_index];
            table_size = div_table_sizes[div_index]
            table_size_list = []

            if num_groups:
                # If num_groups is specified, then we can't use the 5&3 setup.
                # If it's any other table setup then the number of player slots
                # is the number of players per table times num_groups.
                if table_size <= 0:
                    raise countdowntourney.FixtureGeneratorException("%s: invalid table size for fully-manual setup" % (tourney.get_division_name(div_index)))
                else:
                    num_slots = table_size * num_groups
                    table_size_list = [ table_size for i in range(num_groups) ]
            else:
                # If num_groups is not specified, then the number if slots is
                # simply the number of active players in this division, rounded
                # up to the nearest multiple of the group size with prunes.
                num_slots = len(div_players)
                (table_size_list, prunes_required) = gencommon.get_table_sizes(num_slots, table_size)
                if tourney.has_auto_prune():
                    num_slots += prunes_required

            div_table_size_list[div_index] = table_size_list
            div_num_slots[div_index] = num_slots

            if table_size > 0 and num_slots % table_size != 0:
                # If tourney db supports auto prune, we will already have
                # rounded num_slots up to the nearest table_size multiple
                # by adding Prunes.
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
        div_unselected_names = dict()
        div_duplicate_within_group_slots = dict()
        finished = True

        if tourney.has_auto_prune():
            prune = tourney.get_auto_prune()
            prune_name = tourney.get_auto_prune_name()
        else:
            prune = None
            prune_name = None

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

            allow_player_repetition = to_bool(settings.get("d%d_allow_player_repetition" % (div_index)), False)
            allow_unselected_players = to_bool(settings.get("d%d_allow_unselected_players" % (div_index)), False)

            unselected_names = [x.get_name() for x in div_players]

            # Ask the user to fill in N little drop-down boxes, where N is the
            # number of players, to decide who's going on what table.
            for slot_index in range(0, num_slots):
                # d0_player0 contans the existing value in division 0, slot 0
                name = settings.get("d%d_player%d" % (div_index, slot_index));
                if name is None:
                    name = ""
                set_text[slot_index] = name
                if name:
                    set_players[slot_index] = lookup_player(div_players, name, prune_name, prune);
                    if set_players[slot_index] is None:
                        invalid_slots.append(slot_index)
                    if name in unselected_names:
                        unselected_names.remove(name)
                else:
                    set_players[slot_index] = None

            # Slot numbers which contain a player already contained in another
            # slot, except where allow_player_repetition is set.
            duplicate_slots = [];

            # Slot numbers which don't contain a player.
            empty_slots = [];

            # Slots which contain a player which also appears in a different
            # slot in the same group, EVEN IF allow_player_repetition is set.
            duplicate_within_group_slots = []

            # Check every slot so far. If any slots are unfilled, or any
            # player exists twice where not permitted, then the form isn't
            # complete and we must present it to the user again.
            slot_index = 0
            for p in set_players:
                if slot_index in invalid_slots:
                    finished = False
                elif p is None:
                    empty_slots.append(slot_index);
                    finished = False;
                else:
                    if not allow_player_repetition and not p.is_auto_prune():
                        count = 0;
                        for q in set_players:
                            if q is not None and q.get_name() == p.get_name():
                                count += 1;
                        if count > 1:
                            duplicate_slots.append(slot_index);
                            finished = False;

                    # If this player appears anywhere else in the same group,
                    # this is illegal even if allow_player_repetition is set.
                    table_index = get_table_index_from_slot(div_table_size_list[div_index], slot_index)
                    slots_on_table = get_slots_on_table(div_table_size_list[div_index], table_index)
                    for other_slot in slots_on_table:
                        q = set_players[other_slot]
                        if other_slot != slot_index and q and q.get_name() == p.get_name():
                            duplicate_within_group_slots.append(slot_index)
                            finished = False
                slot_index += 1

            # If this is the Manual (not Raw) fixture generator, every player
            # must be assigned to a slot before the form is complete.
            if not allow_unselected_players and unselected_names:
                finished = False

            div_set_players[div_index] = set_players
            div_duplicate_slots[div_index] = duplicate_slots
            div_empty_slots[div_index] = empty_slots
            div_invalid_slots[div_index] = invalid_slots
            div_count_in_standings[div_index] = count_in_standings
            div_set_text[div_index] = set_text
            div_game_type[div_index] = game_type
            div_unselected_names[div_index] = unselected_names
            div_duplicate_within_group_slots[div_index] = duplicate_within_group_slots
        self.div_set_players = div_set_players
        self.div_duplicate_slots = div_duplicate_slots
        self.div_duplicate_within_group_slots = div_duplicate_within_group_slots
        self.div_empty_slots = div_empty_slots
        self.div_invalid_slots = div_invalid_slots
        self.div_count_in_standings = div_count_in_standings
        self.div_set_text = div_set_text
        self.div_game_type = div_game_type
        self.div_unselected_names = div_unselected_names
        self.div_table_size_list = div_table_size_list
        self.div_num_slots = div_num_slots

        self.complete = finished

    def is_complete(self):
        return self.complete

    def get_player_in_slot(self, div, slot_number):
        slots = self.div_set_players.get(div, [])
        if slot_number < 0 or slot_number >= len(slots):
            return None
        else:
            return slots[slot_number]

    def get_duplicate_slot_numbers(self, div):
        return self.div_duplicate_slots.get(div, [])[:]

    def get_duplicate_within_group_slot_numbers(self, div):
        return self.div_duplicate_within_group_slots.get(div, [])[:]

    def get_empty_slot_numbers(self, div):
        return self.div_empty_slots.get(div, [])[:]

    def get_invalid_slot_numbers(self, div):
        return self.div_invalid_slots.get(div, [])[:]

    def get_count_in_standings(self, div):
        return self.div_count_in_standings.get(div, True)

    def get_slot_text(self, div, slot):
        slots = self.div_set_text.get(div, [])
        if slot < 0 or slot >= len(slots):
            return None
        else:
            return slots[slot]

    def get_game_type(self, div):
        return self.div_game_type.get(div, None)

    def get_unselected_names(self, div):
        return self.div_unselected_names.get(div, [])[:]

    def get_num_slots(self, div):
        return self.div_num_slots.get(div, 0)

    def get_table_size_list(self, div):
        return self.div_table_size_list.get(div, [])[:]

    def validate_slot(self, div, slot):
        if slot in self.div_duplicate_slots.get(div, []):
            return (False, "duplicateplayer")
        elif slot in self.div_duplicate_within_group_slots.get(div, []):
            return (False, "duplicateplayer")
        elif slot in self.div_empty_slots.get(div, []):
            return (False, "emptyslot")
        elif slot in self.div_invalid_slots.get(div, []):
            return (False, "invalidslot")
        else:
            return (True, "validslot")

    def make_player_selector(self, div_players, div_index, slot_index, interface_type, show_already_assigned_players, prune_name):
        (value_is_valid, td_class) = self.validate_slot(div_index, slot_index)
        unselected_names = self.get_unselected_names(div_index)
        p = self.get_player_in_slot(div_index, slot_index)

        # Make a drop down list with every unassigned player in it
        player_option_list = [];

        if interface_type == INTERFACE_DROP_DOWN:
            # Drop-down list needs an initial "nothing selected" option
            player_option_list.append(htmlform.HTMLFormDropDownOption("", " -- select --"));
        selected_name = "";

        # Show a selection of names in the drop-down list. This includes all
        # players not so far put in a slot, plus the current value if valid,
        # plus the automatic Prune if it exists.
        if show_already_assigned_players:
            # Include all the names
            name_list = [ x.get_name() for x in div_players ]
        else:
            if p:
                name_list = unselected_names + [p.get_name()]
            else:
                name_list = unselected_names
        if prune_name and prune_name not in name_list:
            name_list.append(prune_name)
        name_list.sort()
        for q in name_list:
            if p is not None and q == p.get_name():
                selected_name = p.get_name()
            if interface_type == INTERFACE_DROP_DOWN:
                player_option_list.append(htmlform.HTMLFormDropDownOption(q, q))
            else:
                player_option_list.append(q)
        if interface_type != INTERFACE_DROP_DOWN and not selected_name:
            selected_name = self.get_slot_text(div_index, slot_index)

        # Create a form input control of the requested type, with the
        # appropriate value selected.
        control_name = "d%d_player%d" % (div_index, slot_index)
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
        if sel:
            sel.set_value(selected_name);
        return sel

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def to_bool(value, default):
    i = int_or_none(value)
    if i is None:
        return default
    else:
        return bool(i)

def lookup_player(players, name, prune_name, prune):
    if prune_name is not None and name == prune_name:
        return prune
    for p in players:
        if p.get_name().lower() == name.lower():
            return p;
    return None


def get_user_form(tourney, settings, div_rounds):
    prev_settings = settings.get_previous_settings()
    for key in prev_settings:
        if key not in settings and re.match("^d[0-9]*_groupsize$", key):
            settings[key] = prev_settings[key]
    if settings.get("submitrestore", None):
        for key in prev_settings:
            if key not in ["submit", "submitrestore", "submitplayers"]:
                settings[key] = prev_settings[key]

    latest_round_no = tourney.get_latest_round_no()
    if latest_round_no is None:
        latest_round_no = 0

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

    num_divisions = tourney.get_num_divisions()
    players = sorted(tourney.get_active_players(), key=lambda x : x.get_name());

    div_table_sizes = get_div_table_sizes(settings, div_rounds)
    for div_index in div_rounds:
        # Number of groups may be specified by fully-manual generator.
        # If it isn't, then use all the players.
        div_players = [x for x in players if x.get_division() == div_index]
        num_groups = int_or_none(settings.get("d%d_num_groups" % (div_index)))
        table_size_name = "d%d_groupsize" % (div_index)
        choices = []
        if num_groups:
            if div_table_sizes[div_index] is not None and div_table_sizes[div_index] <= 0:
                raise countdowntourney.FixtureGeneratorException("%s: invalid table size for fully-manual setup." % (tourney.get_division_name(div_index)))
        else:
            for size in (2,3,4,5):
                if num_groups or tourney.has_auto_prune() or len(div_players) % size == 0:
                    choices.append(htmlform.HTMLFormChoice(str(size), str(size), size == div_table_sizes[div_index]))
            if len(div_players) >= 8:
                choices.append(htmlform.HTMLFormChoice("-5", "5&3", div_table_sizes[div_index] == -5))

            if not choices:
                raise countdowntourney.FixtureGeneratorException("%s: number of players (%d) is not compatible with any supported table size." % (tourney.get_division_name(div_index), len(div_players)))

        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<h2>%s</h2>" % (cgicommon.escape(tourney.get_division_name(div_index)))))

        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(htmlform.HTMLFormRadioButton(table_size_name, "Players per table", choices))
        elements.append(htmlform.HTMLFragment("</p>"))

    # We need the user to select a table size for every division before we
    # move on to ask which players the user wants where. If any division
    # doesn't have a table size given for it, ask for the table sizes.
    all_table_sizes_given = True
    for div in div_table_sizes:
        if div_table_sizes.get(div) is None:
            all_table_sizes_given = False

    if not all_table_sizes_given or not(settings.get("tablesizesubmit", "")):
        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(htmlform.HTMLFormSubmitButton("submit", "Submit table sizes and select players"))
        elements.append(htmlform.HTMLFragment("</p>"))
        return htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s" % (urllib.parse.quote_plus(tourney.name)), elements)

    arrangement = PlayerArrangement(tourney, settings, div_rounds)
    if arrangement.is_complete() and settings.get("submitplayers"):
        # All slots filled, don't need to ask the user anything more
        return None

    # If we get here, we don't have all the information we need. Either there
    # are still some empty slots, or the user has made a mistake like using
    # the same player twice or entering an invalid player name.
    # Build the form to show the user, colouring each slot according to
    # whether it's valid, and if not, why not.

    show_already_assigned_players = bool(settings.get("showallplayers"))
    interface_type = int_or_none(settings.get("interfacetype", INTERFACE_AUTOCOMPLETE))

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
    text-align: center;
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

    # Get the list of players in each division. This is used as a list of
    # valid entries for auto-complete purposes.
    div_player_names = {}
    for div_index in div_rounds:
        name_list = [ x.get_name() for x in players if x.get_division() == div_index ]
        if tourney.has_auto_prune():
            name_list.append(tourney.get_auto_prune_name())
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

    # Give the user a choice of input methods...
    elements.append(htmlform.HTMLFragment("<p>Enter player names below. Each horizontal row is one group, or table.</p>"))
    choice_data = [
            ("Auto-completing text boxes", INTERFACE_AUTOCOMPLETE),
            ("Drop-down boxes", INTERFACE_DROP_DOWN),
            ("Combo boxes (not supported on all browsers)", INTERFACE_DATALIST)
    ]
    choices = [ htmlform.HTMLFormChoice(str(x[1]), x[0], interface_type == x[1]) for x in choice_data ]
    interface_menu = htmlform.HTMLFormRadioButton("interfacetype", "Player name selection interface", choices)
    elements.append(interface_menu)

    # Usually if we're using drop-down boxes we only list in the drop-down
    # box the list of players not already used elsewhere, but this can be
    # overridden by this check box.
    if interface_type == INTERFACE_DROP_DOWN:
        elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
        elements.append(htmlform.HTMLFormCheckBox("showallplayers", "Show all players in drop-down boxes, even those already assigned a table", show_already_assigned_players))
        elements.append(htmlform.HTMLFragment("</div>"))

    (acc_tables, acc_default) = tourney.get_accessible_tables()

    table_no = 1;
    prune_name = tourney.get_auto_prune_name()
    for div_index in div_rounds:
        # For each division we're generating fixtures for, we will display a
        # grid of slots, each inviting the name of a player.

        div_players = [x for x in players if x.get_division() == div_index];
        slot_index = 0

        # All the games we generate in a division are the same type. The type
        # may not be explicitly specified. If it isn't, then if the "count the
        # results of these games in the standings" box is ticked then it's P,
        # otherwise it's N.
        game_type = arrangement.get_game_type(div_index)

        # List of names yet to be put in a slot
        unselected_names = arrangement.get_unselected_names(div_index)

        # allow_unselected_players is set by the Raw fixgen, which uses this one
        allow_unselected_players = to_bool(settings.get("d%d_allow_unselected_players" % (div_index)), False)

        if num_divisions > 1:
            # Display heading containing division name.
            elements.append(htmlform.HTMLFragment("<h2>%s</h2>" % (cgicommon.escape(tourney.get_division_name(div_index)))))

        if not game_type:
            # Ask the user if they want these games to count towards the
            # standings table (this is pretty much universally yes).
            elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
            elements.append(htmlform.HTMLFormCheckBox("d%d_heats" % (div_index), "Count the results of these matches in the standings table", arrangement.get_count_in_standings(div_index)))
            elements.append(htmlform.HTMLFragment("</div>"))

        # Show the table of groups for the user to fill in
        elements.append(htmlform.HTMLFragment("<table class=\"seltable\">\n"));
        prev_table_no = None;

        # table_sizes: array of numbers, one for each table, telling us how
        # many players must go on that table.
        table_sizes = arrangement.get_table_size_list(div_index)
        for table_size in table_sizes:
            # Each "table" (or "group") is a row of this HTML table. Each
            # cell is a slot.
            elements.append(htmlform.HTMLFragment("<tr>\n"))
            elements.append(htmlform.HTMLFragment(
                "<td>%s</td><td class=\"tablenumber\"><div class=\"tablebadgenaturalsize\" style=\"padding-top: 2px; padding-bottom: 2px;\">%d</div></td>\n" % (
                    " &#9855;" if (table_no in acc_tables) != acc_default else "",
                    table_no
                )
            ));
            if game_type is not None:
                elements.append(htmlform.HTMLFragment("<td class=\"fixturegametype\">%s</td>" % (cgicommon.escape(game_type, True))))
            for i in range(table_size):
                # Colour the table cell background in an appropriate colour
                # depending on whether it's valid, and if not, why not.
                (value_is_valid, td_class) = arrangement.validate_slot(div_index, slot_index)
                elements.append(htmlform.HTMLFragment("<td class=\"%s\">" % td_class));

                # Put a drop-down, combo box or auto-complete text box in
                # the table cell, as desired. The PlayerArrangement object
                # already knows what was in this slot when the form was last
                # submitted and therefore what to pre-select.
                sel = arrangement.make_player_selector(div_players, div_index,
                        slot_index, interface_type,
                        show_already_assigned_players, prune_name)
                if sel:
                    elements.append(sel);
                elements.append(htmlform.HTMLFragment("</td>"));
                slot_index += 1
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

        # Describe all the things the user has got wrong so far...
        invalid_slots = arrangement.get_invalid_slot_numbers(div_index)
        duplicate_slots = arrangement.get_duplicate_slot_numbers(div_index)
        duplicate_within_group_slots = arrangement.get_duplicate_within_group_slot_numbers(div_index)
        unselected_names = arrangement.get_unselected_names(div_index)
        empty_slots = arrangement.get_empty_slot_numbers(div_index)
        if invalid_slots:
            elements.append(htmlform.HTMLFragment("<p>You have slots with unrecognised player names; these are highlighted in <span style=\"color: red; font-weight: bold;\">red</span>.</p>"));
        if duplicate_slots:
            elements.append(htmlform.HTMLFragment("<p>You have players in multiple slots; these are highlighted in <span style=\"color: violet; font-weight: bold;\">violet</span>.</p>"));
        if duplicate_within_group_slots:
            elements.append(htmlform.HTMLFragment("<p>You have players appearing more than once on the same table; these are highlighted in <span style=\"color: violet; font-weight: bold;\">violet</span>.</p>"))
        if not allow_unselected_players and unselected_names and not invalid_slots and not empty_slots:
            elements.append(htmlform.HTMLFragment("<p>You have filled all the slots but not all players have not been assigned to a table. See below. Have you put a Prune into too many slots?</p>"))

        # Show a list of all players yet to be put in a slot.
        if unselected_names:
            elements.append(htmlform.HTMLFragment("<p>Players still to be given a table:\n"));
            if not allow_unselected_players and not invalid_slots and not empty_slots:
                # All slots are filled validly but some players don't have a
                # slot (perhaps you used an automatic Prune too many times).
                # Write the unslotted players in red to highlight that this is
                # now the problem.
                span_style = "style=\"color: red; font-weight: bold;\""
            else:
                span_style = ""
            for i in range(len(unselected_names)):
                name = unselected_names[i]
                elements.append(htmlform.HTMLFragment("<span %s>%s</span>%s" % (span_style, cgicommon.escape(name, True), "" if i == len(unselected_names) - 1 else ", ")));
            elements.append(htmlform.HTMLFragment("</p>\n"));

        # Remind the player how to invoke the automatic prune
        if tourney.has_auto_prune():
            elements.append(htmlform.HTMLFragment("<p>Automatic prune player name: %s</p>" % (cgicommon.escape(tourney.get_auto_prune_name()))))

        # Add some hidden inputs containing state we want to keep for the next
        # time the form is submitted...
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
    players = tourney.get_active_players()
    for div in div_rounds:
        div_players = [x for x in players if x.get_division() == div]
        round_no = div_rounds[div]

        existing_games = tourney.get_games(round_no=round_no, game_type="P", division=div)
        if existing_games:
            return (False, "%s: round %d already has %d games in it." % (tourney.get_division_name(div), round_no, len(existing_games)))

        if tourney.has_auto_prune():
            possible_sizes = [2, 3, 4, 5]
        else:
            possible_sizes = []
            for size in (2,3,4,5):
                if tourney.has_auto_prune() or len(div_players) % size == 0:
                    possible_sizes.append(size)
        if len(div_players) >= 8:
            possible_sizes.append(-5)
        if not possible_sizes:
            return (False, "%s: number of players (%d) is not compatible with any supported table size." % (tourney.get_division_name(div), len(div_players)))
    return (True, None)

def generate(tourney, settings, div_rounds, check_ready_fn=None):
    num_divisions = tourney.get_num_divisions()
    div_table_sizes = get_div_table_sizes(settings, div_rounds)

    # Check that the table size has been properly specified for each division.
    players = tourney.get_active_players();
    for div_index in div_rounds:
        table_size = div_table_sizes.get(div_index)
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

    # If check_ready() fails then something went wrong.
    if check_ready_fn:
        (ready, excuse) = check_ready_fn(tourney, div_rounds);
    else:
        (ready, excuse) = check_ready(tourney, div_rounds);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    # Gather from settings the details of which player has been put into which
    # slot. If we've got this far it should be complete - every slot filled,
    # no duplicates, etc.
    arrangement = PlayerArrangement(tourney, settings, div_rounds)
    if not arrangement.is_complete():
        raise countdowntourney.FixtureGeneratorException("get_user_form() returned None but PlayerArrangement class claims settings are not complete. This probably doesn't mean too much to you but it does mean there's a bug in Atropine.")

    # Convert the players in the PlayerArrangement object into groups of the
    # relevant size.
    generated_groups = fixgen.GeneratedGroups()
    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        groups = [];
        table_sizes = arrangement.get_table_size_list(div_index)
        div_players = [x for x in players if x.get_division() == div_index]
        game_type = arrangement.get_game_type(div_index)
        if not game_type:
            if settings.get("d%d_heats" % (div_index)):
                game_type = "P"
            else:
                game_type = "N"

        # Player names should have been specified by a series of drop-down
        # boxes, and this information is in the PlayerArrangement object.
        slot_index = 0
        groups = []
        for size in table_sizes:
            group = []
            for i in range(size):
                p = arrangement.get_player_in_slot(div_index, slot_index)
                if not p:
                    raise countdowntourney.FixtureGeneratorException("%s: Player in slot %d not specified. This is probably a bug, as the form should have made you fill in all the boxes." % (tourney.get_division_name(div_index), slot_index));
                group.append(p)
                slot_index += 1
            groups.append(group)

        # Add these groups of players to generated_groups.
        for g in groups:
            generated_groups.add_group(round_no, div_index, g)
        generated_groups.set_repeat_threes(round_no, div_index, table_size == -5)

        # Set the round name and game type for fixtures we're generating in
        # this division.
        round_name = settings.get("d%d_round_name" % (div_index))
        if round_name:
            generated_groups.set_round_name(round_no, round_name)
        generated_groups.set_game_type(round_no, div_index, game_type)

    return generated_groups

def save_form_on_submit():
    return True
