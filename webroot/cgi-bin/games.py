#!/usr/bin/python

import sys;
import cgicommon;
import urllib;
import cgi;
import cgitb;
import os;
import re;
import random;
import json;

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def ordinal_suffix(num):
    if (num / 10) % 10 == 1:
        return "th"
    elif num % 10 == 1:
        return "st"
    elif num % 10 == 2:
        return "nd"
    elif num % 10 == 3:
        return "rd"
    else:
        return "th"

def write_autocomplete_scripts(tourney, games):
    print "<script>"
    print "var previous_control_values = {};"
    print "var control_last_change_was_manual = {};"

    players_dict = dict()
    players_tables = dict()

    print "var players = "

    if not games:
        print "{}"
    else:
        for g in games:
            names = g.get_player_names()
            for idx in range(2):
                name = names[idx]
                opponent_name = names[1 - idx]
                opponent_list = players_dict.get(name, [])
                if opponent_name not in opponent_list:
                    opponent_list.append({
                        "opponent_name" : opponent_name,
                        "score" : g.get_player_name_score(name),
                        "opponent_score" : g.get_player_name_score(opponent_name),
                        "tb" : g.tb,
                        "seq" : g.seq,
                        }
                    )
                    players_dict[name] = opponent_list
                if name not in players_tables:
                    players_tables[name] = [g.table_no]
                elif g.table_no not in players_tables[name]:
                    players_tables[name] = sorted(players_tables[name] + [g.table_no])

        print json.dumps(players_dict, indent=4)
    print ";"

    print "var player_snapshots = "

    players_summaries = dict()
    num_divisions = tourney.get_num_divisions()
    div_standings = [ tourney.get_standings(div) for div in range(num_divisions) ]
    for div in range(len(div_standings)):
        for row in div_standings[div]:
            if row.name not in players_tables:
                table_field = "Tx"
            else:
                table_field = "T" + ",".join([str(x) for x in players_tables[row.name]])
            if num_divisions > 1:
                division_field = tourney.get_short_division_name(div) + " "
            else:
                division_field = ""

            # define "win marks" is 2 * wins + draws, and display that divided
            # by two, using the half symbol if necessary
            #
            #win_marks = row.wins * 2 + row.draws
            #if win_marks == 1:
            #    win_marks_str = "&frac12;"
            #else:
            #    win_marks_str = str(int(win_marks / 2))
            #    if win_marks % 2 == 1:
            #        win_marks_str += "&frac12;"
            #
            #players_summaries[row.name] = "%s %s%d%s %s/%d %d" % (
            #        table_field, division_field, row.position,
            #        ordinal_suffix(row.position), win_marks_str, row.played,
            #        row.points)
            if row.draws == 0:
                draw_string = ""
            else:
                draw_string = " D%d" % (row.draws)
            players_summaries[row.name] = "%s %s%d%s P%d W%d%s L%d %dpts" % (
                    table_field, division_field, row.position,
                    ordinal_suffix(row.position), row.played, row.wins,
                    draw_string, row.played - row.wins - row.draws, row.points)

    print json.dumps(players_summaries, indent=4)
    print ";"

    player_links = dict()
    tourney_name = tourney.get_name()
    for name in players_summaries:
        try:
            p = tourney.get_player_from_name(name)
            player_links[name] = cgicommon.player_to_link(p, tourney_name, False, False, True, players_summaries[name])
        except PlayerDoesNotExistException:
            pass

    print "var player_links = "
    print json.dumps(player_links, indent=4)
    print ";"
    print

    print """
var tiebreak_prev_state = false;
var tiebreak_visible = false;

function set_infobox(name_control_id, info_control_id) {
    var name_control = document.getElementById(name_control_id);
    var info_control = document.getElementById(info_control_id);

    if (name_control.value in player_links) {
        info_control.innerHTML = player_links[name_control.value];
    }
    else {
        info_control.innerHTML = "";
    }
}

function set_infoboxes() {
    set_infobox("entryname1", "entryinfo1");
    set_infobox("entryname2", "entryinfo2");
}

function entry_name_change(control_id, opponent_control_id) {
    var control = document.getElementById(control_id);
    var opponent_control = document.getElementById(opponent_control_id);
    var diag_control = document.getElementById("diag");
    var player_info_control_id = control_id.replace("name", "info");

    if (control == null) {
        return;
    }

    /* What was the previous value of this control? If the length has got
       bigger, then proceed. Otherwise don't do any fancy auto-completion
       because that would interfere with the user's attempt to backspace out
       the text. */
    var previous_value;
    if (control_id in previous_control_values) {
        previous_value = previous_control_values[control_id];
    }
    else {
        previous_value = "";
    }

    previous_control_values[control_id] = control.value;

    control_last_change_was_manual[control_id] = true;

    if (control.value.length <= previous_value.length) {
        /* User has shortened the text in the box - don't complete anything. */
        set_infobox(control_id, player_info_control_id);
        return;
    }

    /* First, determine the set of players which are acceptable in this box.
       If the other player's edit box already has a player name in it, and
       that is a valid player name from the list, then the set of possible
       players for *this* box is only those players who are playing that player
       in this round.
       If the opponent's box doesn't contain a valid player name, then the set
       of possible players is every player who is playing a game in this
       round. */
    var possible_players;

    var opponent_name = opponent_control.value;
    if (!opponent_name) {
        opponent_name = "";
    }

    if (opponent_name in players) {
        possible_players = []
        var opponents = players[opponent_name];
        for (var i = 0; i < opponents.length; ++i) {
            possible_players.push(opponents[i]["opponent_name"])
        }
    }
    else {
        possible_players = [];
        for (var p in players) {
            possible_players.push(p);
        }
    }

    var sel_start = control.selectionStart;

    /* Take the portion of the control's value from the start of the string
       to sel_start. If that string is the start of exactly one player's name,
       then:
       * set the control's value to the player's full name
       * highlight the added portion
       * leave the cursor where it was before
    */


    var head = control.value.substring(0, sel_start);
    //diag_control.innerHTML = sel_start.toString() + "; ";
    var num_matches = 0;
    var last_match = "";
    for (var i = 0; i < possible_players.length; ++i) {
        var p = possible_players[i];
        if (p.substring(0, head.length).toLowerCase() === head.toLowerCase()) {
            num_matches++;
            last_match = p;
        }
    }

    //diag_control.innerHTML += num_matches.toString() + " matches";

    if (num_matches == 1) {
        control.focus();
        control.value = last_match;
        control.setSelectionRange(head.length, last_match.length);
    }
    set_infobox(control_id, player_info_control_id);
}

function is_valid_player(player_name) {
    return player_name in players;
}

function entry_name_change_finished(control_id, opponent_control_id) {
    var edited_control = document.getElementById(control_id);
    var opponent_control = document.getElementById(opponent_control_id);
    var score_control_id = control_id.replace("name", "score");
    var opponent_score_control_id = opponent_control_id.replace("name", "score");
    
    var player_score_control = document.getElementById(score_control_id);
    var opponent_score_control = document.getElementById(opponent_score_control_id);
    var tiebreak_control = document.getElementById("entrytiebreak");

    /* If one name is filled in, and the other box doesn't contain user input,
       then if there is only one possible value for the other box then fill
       that in. Note that if the last change to the other box was us
       automatically filling in a name, that doesn't count as user input. */
    var opponent_last_modified_manually;
    if (opponent_control_id in control_last_change_was_manual) {
        opponent_last_modified_manually = control_last_change_was_manual[opponent_control_id];
    }
    else {
        opponent_last_modified_manually = false;
    }

    var player_name = edited_control.value.trim();

    if (is_valid_player(player_name) && (opponent_control.value.trim().length == 0 || !opponent_last_modified_manually)) {
        var possible_opponents = players[player_name];
        if (possible_opponents.length == 1) {
            opponent_control.value = possible_opponents[0]["opponent_name"];
            control_last_change_was_manual[opponent_control_id] = false;
        }
    }

    /* If the names have changed, don't remember the tiebreak checkbox's
       state any more, just default it to off. */
    tiebreak_prev_state = false;

    var opponent_name = opponent_control.value.trim()
    
    /* If both names are now filled in, and there is exactly one game in this
       round between these two players, then fill in the score and
       tiebreak checkbox. */
    if (is_valid_player(player_name) && is_valid_player(opponent_name)) {
        var player_games = players[player_name];
        var last_match = null;
        var num_matches = 0;
        for (var i = 0; i < player_games.length; ++i) {
            var match = player_games[i];
            if (match["opponent_name"].toLowerCase() == opponent_name.toLowerCase()) {
                num_matches++;
                last_match = match;
            }
        }

        if (num_matches == 1) {
            if (last_match["score"] == null || last_match["opponent_score"] == null) {
                player_score_control.value = "";
                opponent_score_control.value = "";
                tiebreak_control.checked = false;
            }
            else {
                player_score_control.value = last_match["score"].toString();
                opponent_score_control.value = last_match["opponent_score"].toString();
                tiebreak_control.checked = last_match["tb"];
            }
            entry_score_change();
            highlight_game_button(last_match["seq"]);
        }
        else {
            unhighlight_game_button();
        }
    }
    else {
        unhighlight_game_button();
    }
    set_infoboxes();
}

function entry_score_change() {
    var control1 = document.getElementById("entryscore1");
    var control2 = document.getElementById("entryscore2");
    var tiebreak_div = document.getElementById("tiebreakdiv");
    var name1_div = document.getElementById("name1div");
    var name2_div = document.getElementById("name2div");
    var tiebreak_control = document.getElementById("entrytiebreak");
    var possible_tiebreak = false;
    var p1_win = false;
    var p2_win = false;

    /* If both scores are valid integers and they are 10 apart, make the
       tiebreak tickbox a bit less subtle. Otherwise resubtlify it. */
    score1 = control1.value.match(/-?[0-9]+/);
    score2 = control2.value.match(/-?[0-9]+/);

    if (score1 != null && score2 != null) {
        score1 = parseInt(score1);
        score2 = parseInt(score2);

        if (Math.abs(score1 - score2) == 10) {
            possible_tiebreak = true;
        }
        if (score1 > score2) {
            p1_win = true;
        }
        else if (score1 < score2) {
            p2_win = true;
        }
    }

    if (possible_tiebreak) {
        tiebreak_div.style = "display: block;";
        tiebreak_control.checked = tiebreak_prev_state;
        tiebreak_visible = true;
    }
    else {
        if (tiebreak_visible) {
            tiebreak_div.style = "display: none;";
            tiebreak_prev_state = tiebreak_control.checked;
            tiebreak_visible = false;
            tiebreak_control.checked = false;
        }
    }

    /*
    if (p1_win) {
        name1_div.style = "background-color: #aaffaa;";
        name2_div.style = "background-color: #ffaaaa;";
    }
    else if (p2_win) {
        name1_div.style = "background-color: #ffaaaa;";
        name2_div.style = "background-color: #aaffaa;";
    }
    else {
        name1_div.style = "";
        name2_div.style = "";
    }
    */
}

function load_data_entry_form(name1, name2, score1, score2, tb) {
    document.getElementById("entryname1").value = name1;
    document.getElementById("entryname2").value = name2;
    if (score1 == null) {
        document.getElementById("entryscore1").value = "";
    }
    else {
        document.getElementById("entryscore1").value = score1.toString();
    }
    if (score2 == null) {
        document.getElementById("entryscore2").value = "";
    }
    else {
        document.getElementById("entryscore2").value = score2.toString();
    }
    entry_score_change();
    document.getElementById("entrytiebreak").checked = tb;
    set_infoboxes();
}

"""
    print "</script>"

def escape_double_quotes(value):
    return "".join([ x if x not in ('\\', '\"') else "\\\\" + x for x in value ])

def write_new_data_entry_controls(tourney, round_no, last_entry_valid=False,
        last_entry_error=None, last_entry_names=None,
        last_entry_scores=None, last_entry_tiebreak=False):

    # If there was an error with the user's last entry, leave the edit boxes
    # how they were.
    if not last_entry_valid and last_entry_error:
        default_names = []
        default_scores = []
        default_score_ints = []
        for name in last_entry_names:
            if name is None:
                name = ""
            default_names.append(name)
        for score in last_entry_scores:
            if score is None:
                score = ""
                default_score_ints.append(None)
            else:
                try:
                    default_score_ints.append(int(score))
                except ValueError:
                    default_score_ints.append(None)
            default_scores.append(str(score))
        if default_score_ints[0] is None or default_score_ints[1] is None or abs(default_score_ints[0] - default_score_ints[1]) != 10:
            default_tiebreak = False
        else:
            default_tiebreak = last_entry_tiebreak
    else:
        default_names = ["", ""]
        default_scores = ["", ""]
        default_tiebreak = False

    if not last_entry_valid and last_entry_error:
        cgicommon.show_tourney_exception(countdowntourney.InvalidEntryException(last_entry_error))

    tourney_name = tourney.get_name()
    print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % cgi.escape(tourney_name, True);
    print "<input type=\"hidden\" name=\"round\" value=\"%d\" />" % round_no;

    # Print new-fangled friendlier data-entry controls
    print "<div class=\"scoreentry boxshadow\">"
    print "<div class=\"resultsentrytitle\">Result entry</div>"
    print "<div class=\"scoreentryheaderrow\">"
    print "<div class=\"scoreentryplayerinfo scoreentryplayerinfo1\" id=\"entryinfo1\"></div>"
    print "<div class=\"scoreentryplayerinfo scoreentryplayerinfo2\" id=\"entryinfo2\"></div>"
    print "<div class=\"scoreentryclear\">"
    print "<label class=\"closeselectedgame\" onclick=\"deselect_game();\">clear</label>"
    print "</div>"
    print "</div>"

    print "<div class=\"scoreentrynamerow\">"

    print "<div class=\"scoreentryspacer\"></div>"

    print "<div class=\"scoreentryname\" id=\"name1div\">"
    print ("<input class=\"entryname\" type=\"text\" name=\"entryname1\" " +
        "id=\"entryname1\" placeholder=\"Player name...\" value=\"%s\" " +
        "oninput=\"entry_name_change('entryname1', 'entryname2');\" " +
        "onchange=\"entry_name_change_finished('entryname1', 'entryname2');\"" +
        " />") % (cgi.escape(default_names[0], True))
    print "</div>"
    print "<div class=\"scoreentryname\" id=\"name2div\">"
    print ("<input class=\"entryname\" type=\"text\" name=\"entryname2\" " +
        "id=\"entryname2\" placeholder=\"Player name...\" value=\"%s\" " +
        "oninput=\"entry_name_change('entryname2', 'entryname1');\" " +
        "onchange=\"entry_name_change_finished('entryname2', 'entryname1');\"" +
        " />") % (cgi.escape(default_names[1], True))
    print "</div>"
    print "</div>" # scoreentrynamerow

    print "<div class=\"scoreentryspacer\"></div>"

    print "<div class=\"scoreentryscorerow\">"
    print "<div class=\"scoreentryscore\" id=\"score1div\">"
    print ("<input class=\"entryscore\" type=\"text\" name=\"entryscore1\" " +
            "id=\"entryscore1\" placeholder=\"Score\" value=\"%s\" " +
            "oninput=\"entry_score_change();\" />") % (cgi.escape(default_scores[0], True))
    print "</div>"
    print "<div class=\"scoreentryscore\" id=\"score2div\">"
    print ("<input class=\"entryscore\" type=\"text\" name=\"entryscore2\" " +
            "id=\"entryscore2\" placeholder=\"Score\" value=\"%s\" " +
            "oninput=\"entry_score_change();\" />") % (cgi.escape(default_scores[1], True))
    print "</div>"
    print "</div>" # scoreentryscorerow

    print "<div class=\"scoreentryspacer\"></div>"

    print "<div class=\"scoreentryotherrow\">"
    print "<div class=\"scoreentrytiebreak\" id=\"tiebreakdiv\">"
    print "<input class=\"entrytiebreak\" type=\"checkbox\" name=\"entrytiebreak\" id=\"entrytiebreak\" value=\"1\" style=\"cursor: pointer;\" %s />" % ("checked=\"checked\"" if default_tiebreak else "")
    print "<label for=\"entrytiebreak\" style=\"cursor: pointer;\">Game won on tiebreak?</label>"
    print "</div>"
    print "<div class=\"scoreentrysubmit\">"
    print "<input type=\"submit\" name=\"entrysubmit\" value=\"Submit result\" />"
    print "</div>"
    print "</div>" #scoreentryotherrow
    print "<div class=\"scoreentryspacer\"></div>"

    print "</div>" # scoreentry

    print "<p id=\"diag\"></p>"

def write_videprinter(tourney, round_no):
    print "<div class=\"videprinter boxshadow\" id=\"videprinterdiv\">"
    print "<div class=\"resultsentrytitle\">Recent results</div>"
    print "<div class=\"videprinterwindow\" id=\"videprinterwindow\">"

    logs = tourney.get_logs_since(None, False, round_no)
    num_divisions = tourney.get_num_divisions()

    for entry in logs:
        (seq_no, timestamp, rno, round_seq, table_no, game_type, name1, score1, name2, score2, tiebreak, log_type, division, superseded) = entry
        print "<div class=\"videprinterentry\" onclick=\"select_game(%d, true);\">" % (round_seq)

        if score1 is not None and score2 is not None:
            scorestr1 = str(score1)
            scorestr2 = str(score2)
            if tiebreak:
                if score1 > score2:
                    scorestr1 += "*"
                else:
                    scorestr2 += "*"
        else:
            scorestr1 = ""
            scorestr2 = ""

        if superseded:
            print "<span class=\"videprintersuperseded\">"
            if division:
                print cgi.escape(tourney.get_short_division_name(division))
            print cgi.escape("R%dT%d %s %s-%s %s" % (rno, table_no, name1, scorestr1, scorestr2, name2))
            print "</span>"
        else:
            if num_divisions > 1 and division is not None:
                print "<span class=\"videprinterdivision\">%s</span>" % (tourney.get_short_division_name(division))
            print "<span class=\"videprinterroundandtable\">R%dT%d</span>" % (rno, table_no)

            player_classes = [ "videprinterplayer", "videprinterplayer" ]
            if score1 is not None and score2 is not None:
                if score1 > score2:
                    player_classes = [ "videprinterwinningplayer", "videprinterlosingplayer" ]
                elif score2 > score1:
                    player_classes = [ "videprinterlosingplayer", "videprinterwinningplayer" ]

            print "<span class=\"%s\">%s</span>" % (player_classes[0], cgi.escape(name1))
            print "<span class=\"videprinterscore\">%s-%s</span>" % (scorestr1, scorestr2)
            print "<span class=\"%s\">%s</span>" % (player_classes[1], cgi.escape(name2))
        print "</div>"
    print "</div>" # videprinterwindow
    print "</div>" # videprinter

def write_blinkenlights(tourney, round_no):
    games = tourney.get_games(round_no)

    if not games:
        return

    num_divisions = tourney.get_num_divisions()
    tables_to_games = dict()
    game_seq_to_game = dict()
    for g in games:
        table = tables_to_games.get(g.table_no, [])
        table.append(g)
        tables_to_games[g.table_no] = table
        if g.p1 and g.p2:
            names = g.get_player_names()
        else:
            names = [ None, None ]

        game_seq_to_game[g.seq] = {
                "table_no" : g.table_no,
                "name1" : names[0],
                "name2" : names[1],
                "score1" : g.s1,
                "score2" : g.s2,
                "tb" : g.tb,
                "division" : tourney.get_short_division_name(g.division),
                "type" : g.game_type
        }

    print "<script>"
    print "var games_this_round = ";

    print json.dumps(game_seq_to_game, indent=4)
    print ";"

    print "var player_name_to_link_html = ";
    link_dict = dict()
    for p in tourney.get_players():
        link_dict[p.get_name()] = cgicommon.player_to_link(p, tourney.get_name(), False, False, True)
    print json.dumps(link_dict, indent=4)
    print ";"

    print """
function get_link_html(name) {
    if (name == null) {
        return "";
    }
    var link = player_name_to_link_html[name];
    if (link == null) {
        return "";
    }
    else {
        return link;
    }
}

var selected_game_seq = null;
var select_repeat_parity = 0;

function unhighlight_game_button() {
    if (selected_game_seq != null) {
        /* Remove the highlight around the old button */
        element = document.getElementById("gameselectionbutton" + selected_game_seq.toString());
        if (element != null) {
            element.style = "";
        }
    }
}

function deselect_game() {
    unhighlight_game_button();

    select_repeat_parity = 0;
    selected_game_seq = null;
    load_data_entry_form("", "", null, null, false);
}

function highlight_game_button(game_seq) {
    var selected_game_button = document.getElementById("gameselectionbutton" + game_seq.toString())
    unhighlight_game_button();
    selected_game_button.style = "border: 2px solid yellow;";
    selected_game_seq = game_seq;
}

function select_game(game_seq, from_videprinter) {
    var game = games_this_round[game_seq];
    if (game == null)
        return;

    /* Remember if this game was already selected... we'll see why later */
    var already_selected = (!from_videprinter && game_seq == selected_game_seq);

    highlight_game_button(game_seq);

    /* If this game was already selected when we clicked it then swap the
       names over. */
    if (already_selected) {
        select_repeat_parity++;
        if (select_repeat_parity % 2 != 0) {
            load_data_entry_form(game["name2"], game["name1"], game["score2"], game["score1"], game["tb"]);
        }
        else {
            load_data_entry_form(game["name1"], game["name2"], game["score1"], game["score2"], game["tb"]);
        }
    }
    else {
        select_repeat_parity = 0;
        load_data_entry_form(game["name1"], game["name2"], game["score1"], game["score2"], game["tb"]);
    }

    /* If this game has not been played, give score1 focus */
    if (game["score1"] == null || game["score2"] == null) {
        var score1element = document.getElementById("entryscore1");
        score1element.focus();
    }
}

function set_blinkenlights_mouseover(text) {
    var element = document.getElementById("blinkenlightsmouseoverlabel");
    if (element != null) {
        element.innerHTML = text;
    }
}
    """
    print "</script>"

    max_games_on_table = max([ len(tables_to_games[t]) for t in tables_to_games ])

    print "<div class=\"blinkenlights boxshadow\">"
    print "<div class=\"resultsentrytitle\" style=\"padding: 7px;\">Blinkenlights</div>"
    print "<table class=\"blinkenlightstable\">"
    
    num_tables_drawn = 0
    tables_per_row = 8

    for table_no in sorted(tables_to_games):
        division_letters = set()
        players_on_table = set()
        table_games = tables_to_games[table_no]

        if num_tables_drawn % tables_per_row == 0:
            if num_tables_drawn > 0:
                print "</tr>"
            print "<tr class=\"blinkenlightsrow\">"

        for g in table_games:
            for p in g.get_player_names():
                if p is not None and p not in players_on_table:
                    players_on_table.add(p)
            div_short_name = tourney.get_short_division_name(g.division)
            if div_short_name not in division_letters:
                division_letters.add(div_short_name)

        if num_divisions > 1:
            division_letters_string = "".join(sorted(division_letters))
        else:
            division_letters_string = ""

        mouseover_event = cgi.escape("set_blinkenlights_mouseover(\"" + cgi.escape(", ".join(sorted(players_on_table)), True) + "\");", True)

        print "<td class=\"blinkenlightscell\">"
        print "<div class=\"blinkenlightsdivision\">"
        print cgi.escape(division_letters_string)
        print "</div>"
        print "<div class=\"blinkenlightstablenumber\" onmouseover=\"%s\" onmouseout=\"set_blinkenlights_mouseover(&quot;&quot;)\">" % (mouseover_event)

        num_games_left = len([ x for x in table_games if not x.is_complete() ])
        if num_games_left == 0:
            print "<span style=\"color: gray;\">%d</span>" % (table_no)
        else:
            print "%d" % (table_no)
        print "</div>"

        print "<div class=\"blinkenlightsgamesleft\">"
        print "<table><tr>"
        for g in table_games:
            onclick_script = "select_game(%d, false);" % (g.seq)
            element_id = "gameselectionbutton%d" % (g.seq)
            mouseover_event = cgi.escape("set_blinkenlights_mouseover(\"" + cgi.escape(g.get_short_string(), True) + "\");", True);
            if g.is_complete():
                tdclass = "blinkenlightsgameplayed"
            else:
                tdclass = "blinkenlightsgameleft"
            print "<td class=\"%s\" onclick=\"%s\" id=\"%s\" onmouseover=\"%s\" onmouseout=\"set_blinkenlights_mouseover(&quot;&quot;);\"> </td>" % (tdclass, onclick_script, element_id, mouseover_event)
        print "</tr></table>"
        print "</div>"
        print "</td>"
        num_tables_drawn += 1

    # Draw dummy table cells to fill out the row
    while num_tables_drawn % 8 != 0:
        print "<td class=\"blinkenlightspaddingcell\"></td>"
        num_tables_drawn += 1

    print "</tr>"
    print "</table>"

    print "<div class=\"blinkenlightsfooter\">"
    print "<div class=\"blinkenlightsmouseovertext\">"
    print "<span id=\"blinkenlightsmouseoverlabel\"></span>"
    print "</div>"
    print "</div>"

    print "</div>"

    print "<div style=\"clear: both;\"></div>"


def parse_score(score):
    m = re.match("^\s*(-?\d+)\s*(\*?)\s*-\s*(-?\d+)\s*(\*?)\s*$", score);
    if not m:
        return None
    else:
        s1 = int(m.group(1));
        s2 = int(m.group(3));
        if m.group(2) == "*" or m.group(4) == "*":
            tb = True;
        else:
            tb = False;
        return (s1, s2, tb)

cgitb.enable();

print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/games.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

import countdowntourney;

cgicommon.print_html_head("Games: " + str(tourney_name));

print "<body onload=\"games_on_load();\">";

if tourney_name is None:
    print "<h1>No tourney specified</h1>";
    print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>";
    print "</body></html>";
    sys.exit(0);

print """
<script>
function scroll_to_bottom(element) {
    element.scrollTop = element.scrollHeight - element.clientHeight;
}

function games_on_load() {
    element = document.getElementById("videprinterwindow");
    if (element != null) {
        scroll_to_bottom(element);
    }
    set_infoboxes();
}
</script>
""";

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

    cgicommon.show_sidebar(tourney);

    print "<div class=\"mainpane\">";

    # If a round is selected, show the scores for that round, in editable
    # boxes so they can be changed.
    round_no = None;
    if "round" in form:
        try:
            round_no = int(form.getfirst("round"));
        except ValueError:
            print "<h1>Invalid round number</h1>";
            print "<p>\"%s\" is not a valid round number.</p>" % (cgi.escape(form.getfirst("round")));
    else:
        print "<h1>No round number specified</h1>";
    
    if round_no is not None:
        games = tourney.get_games(round_no=round_no);
        rounds = tourney.get_rounds();
        round_name = None;
        for r in rounds:
            if r["num"] == round_no:
                round_name = r.get("name", None);
                break;
        if not round_name:
            round_name = "Round " + str(round_no);

        remarks = dict();
        print "<div class=\"roundnamebox boxshadow\">"
        print cgi.escape(round_name);
        print "</div>"

        print "<div style=\"clear: both;\"></div>"

        last_entry_valid = False
        last_entry_error = None
        last_entry_names = None
        last_entry_scores = None
        last_entry_tb = False
        control_with_error = None

        if "entrysubmit" in form:
            # If the user entered names and a score into the data entry panel,
            # we'll need to add the result for that game. We do this as well as
            # applying any changes made to the scores in the main game list.
            name1 = form.getfirst("entryname1")
            name2 = form.getfirst("entryname2")
            score1 = form.getfirst("entryscore1")
            score2 = form.getfirst("entryscore2")
            tb = form.getfirst("entrytiebreak")

            # Check if the user entered anything in the data entry panel,
            # and if they did, check that it's valid.
            if name1 or name2:
                if not name1 or not name2:
                    # Must fill in both names or neither
                    last_entry_error = "Only one name is filled in. You need to fill in both."
                    control_with_error = "entryname1" if not name1 else "entryname2"
                else:
                    # Check that the player names exist
                    try:
                        p1 = tourney.get_player_from_name(name1)
                    except countdowntourney.PlayerDoesNotExistException:
                        p1 = None
                    try:
                        p2 = tourney.get_player_from_name(name2)
                    except countdowntourney.PlayerDoesNotExistException:
                        p2 = None

                    if p1 is None and p2 is None:
                        control_with_error = "entryname1"
                        last_entry_error = "The players \"%s\" and \"%s\" do not exist in this tournament." % (name1, name2)
                    elif p1 is None:
                        control_with_error = "entryname1"
                        last_entry_error = "The player \"%s\" does not exist in this tournament." % (name1)
                    elif p2 is None:
                        control_with_error = "entryname2"
                        last_entry_error = "The player \"%s\" does not exist in this tournament." % (name2)
                    else:
                        # Both players have been specified, and they exist.
                        # Good so far. Now let's check that there is a game
                        # in this round between those two players. Note that
                        # it is not necessary for the users to enter the
                        # player names the "correct" way round.
                        matching_games = tourney.get_games_between(round_no, name1, name2)
                        if len(matching_games) == 0:
                            control_with_error = "entryname1"
                            last_entry_error = "There is no game in this round between %s and %s." % (name1, name2)
                        elif len(matching_games) > 1:
                            control_with_error = "entryname1"
                            last_entry_error = "There are %d games in this round between %s and %s. Please use the game list (see link at bottom of page) to enter results for these matches." % (len(matching_games), name1, name2)
                        else:
                            # There is exactly one game in this round between
                            # these two players.
                            game = matching_games[0]
                            score1int = None
                            score2int = None
                            unplayed = False
                            score_valid = True
                            players_swapped = False

                            game_players = game.get_player_names()
                            assert(game.is_between_names(game_players[0], game_players[1]))
                            if game_players[0].lower() == p1.get_name().lower():
                                players_swapped = False
                            else:
                                players_swapped = True

                            # If the user has typed a complete score into one
                            # of the score boxes, then split them up into the
                            # two boxes.
                            score_tuple = None
                            if not score1 and score2:
                                score_tuple = parse_score(score2);
                            elif not score2 and score1:
                                score_tuple = parse_score(score1)

                            if score_tuple:
                                score1 = str(score_tuple[0])
                                score2 = str(score_tuple[1])
                                tb = score_tuple[2]

                            # If both scores are blank, then the game is
                            # unplayed. Otherwise, both scores must be
                            # numbers.

                            if not score1 or not score2:
                                # Both scores are blank. Remove the result.
                                if not score1 and not score2:
                                    unplayed = True
                                else:
                                    last_entry_error = "Both scores must be filled in. Alternatively, leave both scores blank to remove the result."
                                    control_with_error = ("entryscore1" if score1 is None or len(score1) == 0 else "entryscore2")
                                    score_valid = False
                            else:
                                # Both scores have something in them.
                                score_strings = [score1, score2]
                                score_ints = [None, None]
                                for i in range(2):
                                    # If the score has an asterisk in it,
                                    # then it was a tiebreak, regardless of
                                    # what the checkbox says.
                                    score_string = score_strings[i]
                                    if "*" in score_string:
                                        tb = "1"
                                        score_string = "".join([ x for x in score_string if x != "*" ])
                                        score_strings[i] = score_string
                                    try:
                                        score_ints[i] = int(score_string)
                                    except ValueError:
                                        pass

                                if score_ints[0] is None or score_ints[1] is None:
                                    last_entry_error = "\"%s\" is not a valid score. This must be an integer." % (score1 if score_ints[0] is None else score2)
                                    score_valid = False
                                    control_with_error = ("entryscore1" if score_ints[0] is None else "entryscore2")
                                elif tb and abs(score_ints[0] - score_ints[1]) != 10:
                                    last_entry_error = "This can't be a tiebreak game: the winning margin is not 10."
                                    control_with_error = "entryscore1"
                                    score_valid = False

                            
                            if score_valid:
                                if tb:
                                    tb = True
                                else:
                                    tb = False

                                if unplayed:
                                    game.set_score(None, None, False)
                                elif players_swapped:
                                    game.set_score(score_ints[1], score_ints[0], tb)
                                else:
                                    game.set_score(score_ints[0], score_ints[1], tb)

                                tourney.merge_games([game]);
                                last_entry_valid = True
            else:
                # User didn't use the data entry panel
                last_entry_valid = False

            if last_entry_error:
                last_entry_valid = False

            last_entry_names = (name1, name2)
            last_entry_scores = (score1, score2)
            last_entry_tb = tb

        num_divisions = tourney.get_num_divisions()

        print "<form method=\"POST\" action=\"%s?tourney=%s&amp;round=%d\">" % (baseurl, urllib.quote_plus(tourney_name), round_no);

        write_new_data_entry_controls(tourney, round_no, last_entry_valid,
                last_entry_error, last_entry_names, last_entry_scores,
                last_entry_tb)

        print "</form>"

        write_videprinter(tourney, round_no)

        write_blinkenlights(tourney, round_no)

        # Fetch the games in the tourney now, after any changes which may have
        # just been applied.
        games = tourney.get_games(round_no=round_no, only_players_known=False);

        if control_with_error or games:
            highlight_control = False
            if control_with_error:
                control_with_focus = control_with_error
                highlight_control = True
            else:
                control_with_focus = "entryname1"
            print "<script>"
            print "document.getElementById('" + control_with_focus + "').focus();"
            if highlight_control:
                print "document.getElementById('" + control_with_focus + "').select();"
            print "</script>"

        # For the auto-completion of player names in the data entry box, we need
        # a Javascript-accessible mapping of all the players playing in this
        # round mapped to the list of player names they're playing.
        write_autocomplete_scripts(tourney, games)


    if round_no is not None:
        print "<p style=\"font-size: 10pt;\">";
        print "<a href=\"/cgi-bin/gameslist.py?tourney=%s&amp;round=%d\">Show all the games in this round as a list</a>" % (urllib.quote_plus(tourney_name), round_no);
        print "</p>";

    print "</div>"; #mainpane

except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);

print "</body>";
print "</html>";

sys.exit(0);
