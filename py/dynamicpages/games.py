#!/usr/bin/python3

import re
import json
import random

import htmlcommon
import countdowntourney
import uploadercli

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def ordinal_suffix(num):
    if (num // 10) % 10 == 1:
        return "th"
    elif num % 10 == 1:
        return "st"
    elif num % 10 == 2:
        return "nd"
    elif num % 10 == 3:
        return "rd"
    else:
        return "th"

def write_autocomplete_scripts(response, tourney, games):
    response.writeln("<script>")
    response.writeln("var previous_control_values = {};")

    # Act as if the initial value of the score boxes is user input, otherwise
    # if a user mistypes a name, submits the form, then corrects it, correcting
    # the name would load the old (blank) score into the score boxes.
    response.writeln("var control_last_change_was_manual = { \"scores\" : true };")

    players_dict = dict()
    players_tables = dict()

    # players_Cased_names
    # Dictionary which maps lowercased player names back to their original
    # case. In the other dictionaries below, the key is always the lowercased
    # player name, so that we treat player names case-insensitively.
    response.writeln("const players_cased_names = ")
    players_cased_names = {}
    for p in tourney.get_players(include_prune=True):
        players_cased_names[p.get_name().lower()] = p.get_name()
    response.writeln(json.dumps(players_cased_names, indent=4))
    response.writeln(";")
    response.writeln()

    # players
    # Dictionary mapping lowercased player names to a list of their opponents
    # in this round.
    # lowercase player name -> {
    #     "opponent_name" : opponent name (original case),
    #     "score" : player's score in this game,
    #     "opponent_score" : opponent's score in this game,
    #     "tb" : tiebreak (true/false)
    #     "seq" : this game's sequence number within the round
    # }
    response.writeln("const players = ")

    if not games:
        response.writeln("{}")
    else:
        for g in games:
            names = g.get_player_names()
            for idx in range(2):
                name = names[idx].lower()
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

        response.writeln(json.dumps(players_dict, indent=4))
    response.writeln(";")

    # player_snapshots
    # Another dictionary mapping lowercased player names to a snapshot string
    # suitable for the link text which appears above the edit box. A snapshot
    # string looks like "T6 B 7th P4 W1 L3 178pts".
    # lowercase player name -> snapshot string
    response.writeln("const player_snapshots = ")

    players_summaries = dict()
    num_divisions = tourney.get_num_divisions()
    div_standings = [ tourney.get_standings(div) for div in range(num_divisions) ]
    for div in range(len(div_standings)):
        for row in div_standings[div]:
            lname = row.name.lower()
            if lname not in players_tables:
                table_field = "Tx"
            else:
                table_field = "T" + ",".join([str(x) for x in players_tables[lname]])
            if num_divisions > 1:
                division_field = tourney.get_short_division_name(div) + " "
            else:
                division_field = ""

            if row.draws == 0:
                draw_string = ""
            else:
                draw_string = " D%d" % (row.draws)
            players_summaries[lname] = "%s %s%d%s P%d W%d%s L%d %dpts" % (
                    table_field, division_field, row.position,
                    ordinal_suffix(row.position), row.played, row.wins,
                    draw_string, row.played - row.wins - row.draws, row.points)

    response.writeln(json.dumps(players_summaries, indent=4))
    response.writeln(";")

    # player_links
    # A dictionary mapping lowercase player names to "<a href=...>" HTML.
    response.writeln("const player_links = ")
    player_links = dict()
    tourney_name = tourney.get_name()
    for name in players_summaries:
        try:
            p = tourney.get_player_from_name(name)
            player_links[name] = htmlcommon.player_to_link(p, tourney_name, False, False, True, players_summaries[name])
        except PlayerDoesNotExistException:
            pass
    response.writeln(json.dumps(player_links, indent=4))
    response.writeln(";")
    response.writeln()

    # prunes
    # A dictionary which is really just a set. Its keys are only the lowercased
    # names of prunes. Ordinary players do not appear in this dictionary at all.
    # lowercase player name -> true
    response.writeln("const prunes = ")
    prune_dict = {}
    for p in tourney.get_players(include_prune=True):
        if p.is_prune():
            prune_dict[p.get_name().lower()] = True
    response.writeln(json.dumps(prune_dict, indent=4))
    response.writeln(";")
    response.writeln()


    response.writeln("""
var tiebreak_prev_state = false;
var tiebreak_visible = false;

function restore_player_case(name) {
    let lname = name.toLowerCase()
    if (lname in players_cased_names) {
        return players_cased_names[lname];
    }
    else {
        return name;
    }
}

function set_infobox(name_control_id, info_control_id) {
    var name_control = document.getElementById(name_control_id);
    var info_control = document.getElementById(info_control_id);

    if (name_control != null && info_control != null) {
        let name_key = name_control.value.toLowerCase();
        if (name_key in player_links) {
            info_control.innerHTML = player_links[name_key];
        }
        else {
            info_control.innerHTML = "";
        }
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
    opponent_name = opponent_name.toLowerCase();

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
        control.value = restore_player_case(last_match);
        control.setSelectionRange(head.length, last_match.length);
    }
    set_infobox(control_id, player_info_control_id);
}

function is_valid_player(player_name) {
    return player_name.toLowerCase() in players;
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
        var possible_opponents = players[player_name.toLowerCase()];
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
       round between these two players, and the score fields are either blank
       or contain something not entered by the user, then fill in the score
       and tiebreak checkbox. */
    if (is_valid_player(player_name) && is_valid_player(opponent_name) &&
            ((player_score_control.value == "" && opponent_score_control.value == "") ||
               !("scores" in control_last_change_was_manual) ||
               !control_last_change_was_manual["scores"])) {
        var player_games = players[player_name.toLowerCase()];
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
                if (player_name.toLowerCase() in prunes) {
                    player_score_control.value = "0";
                }
                else {
                    player_score_control.value = "";
                }
                if (opponent_name.toLowerCase() in prunes) {
                    opponent_score_control.value = "0";
                }
                else {
                    opponent_score_control.value = "";
                }
                tiebreak_control.checked = false;
            }
            else {
                player_score_control.value = last_match["score"].toString();
                opponent_score_control.value = last_match["opponent_score"].toString();
                tiebreak_control.checked = last_match["tb"];
            }
            entry_score_change(false);
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

function entry_score_change(was_user_input) {
    var control1 = document.getElementById("entryscore1");
    var control2 = document.getElementById("entryscore2");
    var tiebreak_div = document.getElementById("tiebreakdiv");
    var name1_div = document.getElementById("name1div");
    var name2_div = document.getElementById("name2div");
    var tiebreak_control = document.getElementById("entrytiebreak");
    var tiebreak_label = document.getElementById("tiebreaklabel");
    var possible_tiebreak = false;
    var possible_double_loss = false;
    var p1_win = false;
    var p2_win = false;

    control_last_change_was_manual["scores"] = was_user_input;

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
        else if (score1 == 0 && score2 == 0) {
            possible_double_loss = true;
        }
        if (score1 > score2) {
            p1_win = true;
        }
        else if (score1 < score2) {
            p2_win = true;
        }
    }

    if (possible_tiebreak || possible_double_loss) {
        tiebreak_div.style = "display: block;";
        if (was_user_input) {
            /* The user filled in the score, so set the tiebreak checkbox
               to the same checked state it was before. If this isn't user
               input - that is, a script has filled the scores in - then it
               would also have filled in the tiebreak checkbox so don't
               fiddle with it. */
            tiebreak_control.checked = tiebreak_prev_state;
        }
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

    if (possible_double_loss) {
        tiebreak_label.innerText = "Loss for both players?";
    }
    else {
        tiebreak_label.innerText = "Game won on tiebreak?";
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

    /* If the game has not yet been played and one of the players is a prune,
       automatically load 0 into that box. */
    if (score1 == null && name1.toLowerCase() in prunes) {
        score1 = 0;
    }
    if (score2 == null && name2.toLowerCase() in prunes) {
        score2 = 0;
    }

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
    entry_score_change(false);
    document.getElementById("entrytiebreak").checked = tb;
    set_infoboxes();
}

var videprinterDivEditing = null;

function news_edit_close() {
    var newsPost = document.getElementById("newspost");
    var newsEdit = document.getElementById("newsedit");
    var inputText = document.getElementById("newsformtext");

    /* If any news entry is highlighted, unhighlight it */
    if (videprinterDivEditing != null) {
        videprinterDivEditing.classList.remove("videprinternewsentryediting");
        videprinterDivEditing = null;
    }

    /* Hide the comment-editing box, show the comment-posting box, and give
       the latter focus */
    newsPost.style.display = null;
    newsEdit.style.display = "none";
    inputText.focus();
}

function news_edit_open(seq, currentText, postedToVideprinter, postedToWeb) {
    var newsPost = document.getElementById("newspost");
    var newsEdit = document.getElementById("newsedit");
    var newsEditVideprinter = document.getElementById("posttovideprinter1")
    var newsEditWeb = document.getElementById("posttoweb1")
    var entryDiv = document.getElementById("videprinter_news_" + seq.toString());

    /* Hide the comment-posting box and show the comment-editing box */
    newsPost.style.display = "none";
    newsEdit.style.display = null;

    if (newsEditVideprinter != null) {
        if (newsEditVideprinter.type == "checkbox") {
            newsEditVideprinter.checked = postedToVideprinter;
        }
        else if (newsEditVideprinter.type == "hidden") {
            newsEditVideprinter.value = (postedToVideprinter ? "1" : "0");
        }
    }
    if (newsEditWeb != null) {
        if (newsEditWeb.type == "checkbox") {
            newsEditWeb.checked = postedToWeb;
        }
        else if (newsEditWeb.type == "hidden") {
            newsEditWeb.value = (postedToWeb ? "1" : "0");
        }
    }

    /* If any news entry is highlighted, unhighlight it... */
    if (videprinterDivEditing != null) {
        videprinterDivEditing.classList.remove("videprinternewsentryediting");
        videprinterDivEditing = null;
    }

    /* ... and highlight the news entry we just clicked */
    if (entryDiv != null) {
        videprinterDivEditing = entryDiv;
        entryDiv.classList.add("videprinternewsentryediting");
    }

    /* Populate the comment-editing form and give it focus */
    var inputSeq = document.getElementById("newseditseq")
    inputSeq.value = seq.toString();

    var inputText = document.getElementById("newsformedittext");
    inputText.value = currentText;
    inputText.focus();
}

""")
    response.writeln("</script>")

def escape_double_quotes(value):
    return "".join([ x if x not in ('\\', '\"') else "\\" + x for x in value ])

def js_quote_string(s):
    return "\"" + escape_double_quotes(s) + "\""

def write_new_data_entry_controls(response, tourney, round_no,
        last_entry_valid=False, last_entry_error=None, last_entry_names=None,
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
        htmlcommon.show_tourney_exception(response, countdowntourney.InvalidEntryException(last_entry_error))

    tourney_name = tourney.get_name()

    # Print new-fangled friendlier data-entry controls
    response.writeln("<div class=\"scoreentry boxshadow\">")
    response.writeln("<div class=\"resultsentrytitle\">Result entry</div>")
    response.writeln("<div class=\"scoreentryheaderrow\">")
    response.writeln("<div class=\"scoreentryplayerinfo scoreentryplayerinfo1\" id=\"entryinfo1\"></div>")
    response.writeln("<div class=\"scoreentryplayerinfo scoreentryplayerinfo2\" id=\"entryinfo2\"></div>")
    response.writeln("<div class=\"scoreentryclear\">")
    response.writeln("<label class=\"closeselectedgame\" onclick=\"deselect_game();\">clear</label>")
    response.writeln("</div>")
    response.writeln("</div>")

    response.writeln("<div class=\"scoreentryspacer\"></div>")

    response.writeln("<div class=\"scoreentryeditboxes\">")

    name1div = "<div class=\"scoreentryname\" id=\"name1div\">"
    name1div += ("<input class=\"entryname\" type=\"text\" name=\"entryname1\" " +
        "id=\"entryname1\" placeholder=\"Player name\" value=\"%s\" " +
        "oninput=\"entry_name_change('entryname1', 'entryname2');\" " +
        "onchange=\"entry_name_change_finished('entryname1', 'entryname2');\"" +
        " />") % (htmlcommon.escape(default_names[0], True))
    name1div += "</div>"

    name2div = "<div class=\"scoreentryname\" id=\"name2div\">"
    name2div += ("<input class=\"entryname\" type=\"text\" name=\"entryname2\" " +
        "id=\"entryname2\" placeholder=\"Player name\" value=\"%s\" " +
        "oninput=\"entry_name_change('entryname2', 'entryname1');\" " +
        "onchange=\"entry_name_change_finished('entryname2', 'entryname1');\"" +
        " />") % (htmlcommon.escape(default_names[1], True))
    name2div += "</div>"

    score1div = "<div class=\"scoreentryscore\" id=\"score1div\">"
    score1div += ("<input class=\"entryscore\" type=\"text\" name=\"entryscore1\" " +
            "id=\"entryscore1\" placeholder=\"Score\" value=\"%s\" " +
            "autocomplete=\"off\" " +
            "oninput=\"entry_score_change(true);\" />") % (htmlcommon.escape(default_scores[0], True))
    score1div += "</div>"

    score2div = "<div class=\"scoreentryscore\" id=\"score2div\">"
    score2div += ("<input class=\"entryscore\" type=\"text\" name=\"entryscore2\" " +
            "id=\"entryscore2\" placeholder=\"Score\" value=\"%s\" " +
            "autocomplete=\"off\" " +
            "oninput=\"entry_score_change(true);\" />") % (htmlcommon.escape(default_scores[1], True))
    score2div += "</div>"

    prefs = countdowntourney.get_global_preferences()
    tab_order = prefs.get_result_entry_tab_order()
    if tab_order == "nsns":
        div_order = [ name1div, score1div, name2div, score2div ]
    elif tab_order == "nssn":
        div_order = [ name1div, score1div, score2div, name2div ]
    else:
        div_order = [ name1div, name2div, score1div, score2div ]

    for div in div_order:
        response.writeln(div)

    response.writeln("</div>") # scoreentryeditboxes

    response.writeln("<div class=\"scoreentryspacer\"></div>")

    response.writeln("<div class=\"scoreentryotherrow\">")
    response.writeln("<div class=\"scoreentrytiebreak\" id=\"tiebreakdiv\">")
    response.writeln("<input class=\"entrytiebreak\" type=\"checkbox\" name=\"entrytiebreak\" id=\"entrytiebreak\" value=\"1\" style=\"cursor: pointer;\" %s />" % ("checked=\"checked\"" if default_tiebreak else ""))
    response.writeln("<label for=\"entrytiebreak\" style=\"cursor: pointer;\" id=\"tiebreaklabel\">Game won on tiebreak?</label>")
    response.writeln("</div>")
    response.writeln("<div class=\"scoreentrysubmit\">")
    response.writeln("<input type=\"submit\" name=\"entrysubmit\" value=\"Submit result\" />")
    response.writeln("</div>")
    response.writeln("</div>") #scoreentryotherrow
    response.writeln("<div class=\"scoreentryspacer\"></div>")

    response.writeln("</div>") # scoreentry

    response.writeln("<p id=\"diag\"></p>")

def write_news_form_tick_box_div(response, tourney, publishing, is_edit):
    if is_edit:
        id_suffix = "1"
    else:
        id_suffix = "0"

    response.writeln("<div class=\"newsformheadingoptions\">")
    if publishing or is_edit:
        tick_box_html_format = """
        <input type="checkbox" name="posttovideprinter" id="posttovideprinter%s" value="1" %s />
        <label for="posttovideprinter%s">To display</label>
        <input type="checkbox" name="posttoweb" id="posttoweb%s" value="1" %s />
        <label for="posttoweb%s">To web</label>
        """
        response.writeln(tick_box_html_format % (
            str(id_suffix),
            "checked" if tourney.is_post_to_videprinter_set() else "",
            str(id_suffix),
            str(id_suffix),
            "checked" if tourney.is_post_to_web_set() else "",
            str(id_suffix)
        ))
    else:
        response.writeln("<input type=\"hidden\" name=\"posttovideprinter\" id=\"posttovideprinter%s\" value=\"1\" />" % (str(id_suffix)))
        response.writeln("<input type=\"hidden\" name=\"posttoweb\" id=\"posttoweb%s\" value=\"1\" />" % (str(id_suffix)))

    if is_edit:
        response.writeln("<button type=\"button\" onclick=\"news_edit_close();\">Close</button>")
    response.writeln("</div>")

def write_videprinter(response, tourney, round_no):
    tourney_name = tourney.get_name()
    try:
        upload_state = uploadercli.get_tourney_upload_state(tourney.get_name())
        if upload_state and upload_state.get("publishing", False):
            publishing = True
        else:
            publishing = False
    except uploadercli.UploaderClientException:
        publishing = False

    response.writeln("<div class=\"videprinter boxshadow\" id=\"videprinterdiv\">")
    response.writeln("<div class=\"resultsentrytitle\">News feed</div>")
    response.writeln("<div class=\"videprinterwindow\" id=\"videprinterwindow\">")

    logs = tourney.get_logs_since(None, False, round_no)
    num_divisions = tourney.get_num_divisions()

    for entry in logs:
        (seq_no, timestamp, rno, round_seq, table_no, game_type, name1, score1, name2, score2, tiebreak, log_type, division, superseded, comment) = entry

        if log_type in (1, 2):
            response.writeln("<div class=\"videprinterentry\" onclick=\"select_game(%d, true);\">" % (round_seq))

            if score1 is not None and score2 is not None:
                if score1 == 0 and score2 == 0 and tiebreak:
                    scorestr1 = "&#10006"
                    scorestr2 = "&#10006"
                else:
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
                response.writeln("<span class=\"videprintersuperseded\">")
                if division:
                    response.writeln(htmlcommon.escape(tourney.get_short_division_name(division)))
                response.writeln(htmlcommon.escape("R%dT%d %s " % (rno, table_no, name1)));
                response.writeln("%s-%s" % (scorestr1, scorestr2))
                response.writeln(htmlcommon.escape(" %s" % (name2)))
                response.writeln("</span>")
            else:
                if num_divisions > 1 and division is not None:
                    response.writeln("<span class=\"videprinterdivision\">%s</span>" % (tourney.get_short_division_name(division)))
                response.writeln("<span class=\"videprinterroundandtable\">R%dT%d</span>" % (rno, table_no))

                player_classes = [ "videprinterplayer", "videprinterplayer" ]
                if score1 is not None and score2 is not None:
                    if score1 == 0 and score2 == 0 and tiebreak:
                        player_classes = [ "videprinterlosingplayer", "videprinterlosingplayer" ]
                    elif score1 > score2:
                        player_classes = [ "videprinterwinningplayer", "videprinterlosingplayer" ]
                    elif score2 > score1:
                        player_classes = [ "videprinterlosingplayer", "videprinterwinningplayer" ]

                response.writeln("<span class=\"%s\">%s</span>" % (player_classes[0], htmlcommon.escape(name1)))
                response.writeln("<span class=\"videprinterscore\">%s-%s</span>" % (scorestr1, scorestr2))
                response.writeln("<span class=\"%s\">%s</span>" % (player_classes[1], htmlcommon.escape(name2)))
            response.writeln("</div>")
        elif (log_type & countdowntourney.LOG_TYPE_COMMENT) != 0:
            # News item
            if comment is None:
                comment = ""
            post_to_videprinter = (log_type & countdowntourney.LOG_TYPE_COMMENT_VIDEPRINTER_FLAG) != 0
            post_to_web = (log_type & countdowntourney.LOG_TYPE_COMMENT_WEB_FLAG) != 0
            response.writeln("<div class=\"videprinterentry videprinternewsentry\" id=\"videprinter_news_%d\" onclick=\"news_edit_open(%d, %s, %s, %s);\">" % (
                seq_no, seq_no,
                htmlcommon.escape(js_quote_string(comment), True),
                "true" if post_to_videprinter else "false",
                "true" if post_to_web else "false"
            ))
            response.writeln("&#8227; " + htmlcommon.escape(comment))
            response.writeln("</div>")

    response.writeln("</div>") # videprinterwindow

    # Form to post a new comment
    response.writeln("<div class=\"newsform\" id=\"newspost\">")
    response.writeln("<form method=\"POST\">")
    response.writeln("<div class=\"newsformheading\">")
    response.writeln("<div class=\"newsformheadingtext\">Post comment</div>")

    write_news_form_tick_box_div(response, tourney, publishing, False)
    response.writeln("</div>")
    response.writeln("<div class=\"newsformbody\">")
    response.writeln("<input type=\"text\" class=\"newsformtext\" name=\"newsformtext\" id=\"newsformtext\" value=\"\" />")
    response.writeln("<input type=\"submit\" class=\"newsformbutton\" name=\"newsformsubmit\" id=\"newsformbutton\" value=\"Post\" />")
    response.writeln("</div>")
    response.writeln("</form>")
    response.writeln("</div>") # newsform

    # Form to edit an existing comment
    response.writeln("<div class=\"newsform\" id=\"newsedit\" style=\"display: none;\">")
    response.writeln("<form method=\"POST\">")
    response.writeln("<div class=\"newsformheading newsformheadingedit\">")
    response.writeln("<div class=\"newsformheadingtext\">Editing comment</div>")
    write_news_form_tick_box_div(response, tourney, publishing, True)
    response.writeln("</div>")

    response.writeln("<div class=\"newsformbody\">")
    response.writeln("<input type=\"hidden\" name=\"newseditseq\" value=\"\" id=\"newseditseq\" />")
    response.writeln("<input type=\"text\" class=\"newsformtext\" name=\"newsformedittext\" id=\"newsformedittext\" value=\"\" />")
    response.writeln("<input type=\"submit\" class=\"newsformbutton\" name=\"newsformeditsubmit\" id=\"newsformeditbutton\" value=\"Save\" />")
    response.writeln("</div>")
    response.writeln("</form>")
    response.writeln("</div>") # newsform

    response.writeln("</div>") # videprinter

def write_blinkenlights(response, tourney, round_no):
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

    response.writeln("<script>")
    response.writeln("var games_this_round = ");

    response.writeln(json.dumps(game_seq_to_game, indent=4))
    response.writeln(";")

    response.writeln("var player_name_to_link_html = ");
    link_dict = dict()
    for p in tourney.get_players():
        link_dict[p.get_name()] = htmlcommon.player_to_link(p, tourney.get_name(), False, False, True)
    response.writeln(json.dumps(link_dict, indent=4))
    response.writeln(";")

    response.writeln("var round_no = %d;" % (round_no))

    response.writeln("""
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

        element = document.getElementById("gamelistscore_" + round_no.toString() + "_" + selected_game_seq.toString());
        if (element != null) {
            element.style.backgroundColor = null;
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

    element = document.getElementById("gamelistscore_" + round_no.toString() + "_" + selected_game_seq.toString());
    if (element != null) {
        element.style.backgroundColor = "#ffff66";
    }
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

    /* Give the score1 field focus, unless that's a prune with a zero or
       empty score, in which case give score2 focus. */
    let scoreElement;
    let nameKey = (select_repeat_parity % 2 == 0 ? "name1" : "name2");
    let scoreKey = (select_repeat_parity % 2 == 0 ? "score1" : "score2");
    if (game[nameKey].toLowerCase() in prunes && (game[scoreKey] == 0 || game[scoreKey] == null)) {
        scoreElement = document.getElementById("entryscore2");
    }
    else {
        scoreElement = document.getElementById("entryscore1");
    }
    scoreElement.focus();
    scoreElement.select();
}

function set_blinkenlights_mouseover(text) {
    var element = document.getElementById("blinkenlightsmouseoverlabel");
    if (element != null) {
        element.innerHTML = text;
    }
}
    """)
    response.writeln("</script>")

    max_games_on_table = max([ len(tables_to_games[t]) for t in tables_to_games ])

    response.writeln("<div class=\"blinkenlights boxshadow\">")
    response.writeln("<div class=\"resultsentrytitle\" style=\"padding: 7px;\">Blinkenlights</div>")
    response.writeln("<table class=\"blinkenlightstable\">")

    num_tables_drawn = 0
    tables_per_row = 8

    for table_no in sorted(tables_to_games):
        division_letters = set()
        players_on_table = set()
        table_games = tables_to_games[table_no]

        if num_tables_drawn % tables_per_row == 0:
            if num_tables_drawn > 0:
                response.writeln("</tr>")
            response.writeln("<tr class=\"blinkenlightsrow\">")

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

        mouseover_event = htmlcommon.escape("set_blinkenlights_mouseover(\"" + htmlcommon.escape(", ".join(sorted(players_on_table)), True) + "\");", True)

        response.writeln("<td class=\"blinkenlightscell\">")
        response.writeln("<div class=\"blinkenlightsdivision\">")
        response.writeln(htmlcommon.escape(division_letters_string))
        response.writeln("</div>")
        num_games_left = len([ x for x in table_games if not x.is_complete() ])
        response.writeln("<div class=\"blinkenlightstablenumber%s\" onmouseover=\"%s\" onmouseout=\"set_blinkenlights_mouseover(&quot;&quot;);\">%d</div>" % (
            " blinkenlightstablenumbernomoregames" if num_games_left == 0 else "",
            mouseover_event,
            table_no
        ))

        response.writeln("<div class=\"blinkenlightsgamesleft\">")
        response.writeln("<table><tr>")
        for g in table_games:
            onclick_script = "select_game(%d, false);" % (g.seq)
            element_id = "gameselectionbutton%d" % (g.seq)
            mouseover_event = htmlcommon.escape("set_blinkenlights_mouseover(\"" + htmlcommon.escape(g.get_short_string(), True) + "\");", True);
            if g.is_complete():
                tdclass = "blinkenlightsgameplayed"
            else:
                tdclass = "blinkenlightsgameleft"
            response.writeln("<td class=\"%s\" onclick=\"%s\" id=\"%s\" onmouseover=\"%s\" onmouseout=\"set_blinkenlights_mouseover(&quot;&quot;);\"> </td>" % (tdclass, onclick_script, element_id, mouseover_event))
        response.writeln("</tr></table>")
        response.writeln("</div>")
        response.writeln("</td>")
        num_tables_drawn += 1

    # Draw dummy table cells to fill out the row
    while num_tables_drawn % 8 != 0:
        response.writeln("<td class=\"blinkenlightspaddingcell\"></td>")
        num_tables_drawn += 1

    response.writeln("</tr>")
    response.writeln("</table>")

    response.writeln("<div class=\"blinkenlightsfooter\">")
    response.writeln("<div class=\"blinkenlightsmouseovertext\">")
    response.writeln("<span id=\"blinkenlightsmouseoverlabel\"></span>")
    response.writeln("</div>")
    response.writeln("</div>")

    response.writeln("</div>")

    response.writeln("<div style=\"clear: both;\"></div>")


def parse_score(score):
    m = re.match(r"^\s*(-?\d+)\s*(\*?)\s*-\s*(-?\d+)\s*(\*?)\s*$", score);
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

# Set the game's scores randomly, with probabilities weighted by the player's
# ratings. round_format should be a string consisting of "L", "N" and "C",
# for example "LLLNLLLNC" or "LLNLLNLLNLLLLNC".
# Adapted from set_random_score() gameslist.py, but refined a bit and with the
# stuff about Scrabble removed.
def set_random_score(game, round_format):
    r1 = game.p1.rating
    r2 = game.p2.rating

    if r1 + r2 == 0:
        game.set_score(0, 0, False)
        return

    p1_threshold = r1 / (r1 + r2)
    p2_threshold = r2 / (r1 + r2)
    p1_threshold *= 0.7
    p2_threshold *= 0.7
    p2_threshold = 1.0 - p2_threshold

    p1_score = 0
    p2_score = 0

    for r in round_format.upper():
        x = random.random()
        if r == "L":
            # Choose the score the winning player will get: 5, 6, 7, 8 or 18.
            round_score = random.randint(5, 10)
            if round_score == 9:
                # Make nines rare; 75% of the time change it to a more common 7
                if random.randint(1, 4) == 1:
                    round_score = 18
                else:
                    round_score = 7
        elif r == "N":
            # Choose the score the winning player will get, biasing more
            # towards solving the numbers exactly.
            round_score = random.choice([0, 5, 7, 7, 10, 10, 10])
        elif r == "C":
            # Conundrum: score is always 10.
            round_score = 10
        else:
            # What round is this?
            round_score = 0

        if r == "C":
            # Simulate conundrum: only one player can score
            if (r1 > 0 or r2 > 0) and random.random() >= 0.2:
                if r2 == 0 or random.random() < (r1 / (r1 + r2)):
                    p1_score += round_score
                else:
                    p2_score += round_score
        else:
            # Simulate letters or numbers round: either player might score
            if r1 > 0 and x < p1_threshold:
                p1_score += round_score
            elif r2 > 0 and x > p2_threshold:
                p2_score += round_score
            else:
                if r1 > 0:
                    p1_score += round_score
                if r2 > 0:
                    p2_score += round_score

    if p1_score == p2_score:
        # Simulate tiebreak, make this a 50-50 tossup
        if random.randint(0, 1) == 0:
            p1_score += 10
        else:
            p2_score += 10
        tb = True
    else:
        tb = False

    game.set_score(p1_score, p2_score, tb)

# Fill in random scores for all unplayed games in this round.
# For testing purposes only.
def set_random_scores(tourney, round_no, round_format="LLLNLLLNC"):
    games = tourney.get_games(round_no=round_no, only_unplayed=True)
    for g in games:
        set_random_score(g, round_format)
    tourney.merge_games(games)


def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourney_name = tourney.get_name()
    htmlcommon.print_html_head(response, "Games: " + str(tourney_name), othercssfiles=["games.css"])

    response.writeln("<body onload=\"games_on_load();\">");

    response.writeln("""
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
""");

    # Round number is expected as the first path component after
    # /atropine/<tourney>/games/
    if len(extra_components) > 0:
        round_no = extra_components[0]
    else:
        round_no = None

    try:
        htmlcommon.show_sidebar(response, tourney);

        response.writeln("<div class=\"mainpane\">");
        response.writeln("<div class=\"entrymainpane\">");

        # Round number is mandatory
        if round_no is None:
            response.writeln("<h1>No round number specified</h1>");
            response.writeln("</div></div></body></html>")
            return

        # If a round is selected, show the scores for that round.
        try:
            round_no = int(round_no)
        except ValueError:
            response.writeln("<h1>Invalid round number</h1>");
            response.writeln("<p>\"%s\" is not a valid round number.</p>" % (htmlcommon.escape(round_no)));
            response.writeln("</div></div></body></html>")
            return

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
        response.writeln("<div class=\"roundnamebox boxshadow\">")
        response.writeln(htmlcommon.escape(round_name));
        response.writeln("</div>")

        response.writeln("<div style=\"clear: both;\"></div>")

        last_entry_valid = False
        last_entry_error = None
        last_entry_names = None
        last_entry_scores = None
        last_entry_tb = False
        control_with_error = None
        default_control_focus = "entryname1"

        if "entrysubmit" in form:
            # If the user entered names and a score into the data entry
            # panel, we'll need to add the result for that game. We do this
            # as well as applying any changes made to the scores in the
            # main game list.
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
                elif name1.lower() == "random scores" and name2.lower() == "random scores":
                    # Special testing feature: fill in unplayed games with
                    # random scores, using player ratings as a guide.
                    # Assume 9-rounders unless the first score box has 15 in it.
                    set_random_scores(tourney, round_no, round_format=("LLNLLNLLNLLLLNC" if score1 == "15" else "LLLNLLLNC"))
                    last_entry_valid = True
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
                            last_entry_error = "There are %d games in this round between %s and %s. Please use the old results interface (see link at bottom of page) to enter results for these matches." % (len(matching_games), name1, name2)
                        else:
                            # There is exactly one game in this round
                            # between these two players.
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

                            # If the user has typed a complete score into
                            # one of the score boxes, then split them up
                            # into the two boxes.
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
                                elif tb and abs(score_ints[0] - score_ints[1]) != 10 and not(score_ints[0] == 0 and score_ints[1] == 0):
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
        elif "newsformsubmit" in form:
            news_text = form.getfirst("newsformtext")
            post_to_videprinter = bool(int_or_none(form.getfirst("posttovideprinter")))
            post_to_web = bool(int_or_none(form.getfirst("posttoweb")))
            if news_text:
                tourney.post_news_item(round_no, news_text, post_to_videprinter, post_to_web)
            tourney.set_post_to_videprinter(post_to_videprinter)
            tourney.set_post_to_web(post_to_web)
            default_control_focus = "newsformtext"
        elif "newsformeditsubmit" in form:
            news_text = form.getfirst("newsformedittext")
            post_to_videprinter = bool(int_or_none(form.getfirst("posttovideprinter")))
            post_to_web = bool(int_or_none(form.getfirst("posttoweb")))
            if news_text is None:
                news_text = ""
            news_entry_seq = int_or_none(form.getfirst("newseditseq"))
            if news_entry_seq is not None:
                tourney.edit_news_item(news_entry_seq, news_text, post_to_videprinter, post_to_web)
            default_control_focus = "newsformtext"

        num_divisions = tourney.get_num_divisions()

        response.writeln("<form method=\"POST\">")

        write_new_data_entry_controls(response, tourney, round_no,
                last_entry_valid, last_entry_error, last_entry_names,
                last_entry_scores, last_entry_tb)

        response.writeln("</form>")

        write_videprinter(response, tourney, round_no)

        write_blinkenlights(response, tourney, round_no)

        # Fetch the games in the tourney now, after any changes which may
        # have just been applied.
        games = tourney.get_games(round_no=round_no)

        # If the user got something wrong, the control with the mistake
        # should have focus. If the user just submitted a news item then
        # the news text box should have focus. Otherwise, the player 1 text
        # box should have focus.
        if control_with_error or games:
            highlight_control = False
            if control_with_error:
                control_with_focus = control_with_error
                highlight_control = True
            else:
                control_with_focus = default_control_focus
            response.writeln("<script>")
            response.writeln("document.getElementById('" + control_with_focus + "').focus();")
            if highlight_control:
                response.writeln("document.getElementById('" + control_with_focus + "').select();")
            response.writeln("</script>")

        # For the auto-completion of player names in the data entry box, we
        # need a Javascript-accessible mapping of all the players playing
        # in this round mapped to the list of player names they're playing.
        write_autocomplete_scripts(response, tourney, games)


        response.writeln("<div style=\"margin-top: 10px\">")
        response.writeln("<span style=\"font-size: 10pt; margin-right: 20px;\">");
        response.writeln("<a href=\"/atropine/%s/fixtureedit/%d\">Edit fixture list</a>" % (htmlcommon.escape(tourney_name), round_no));
        response.writeln("</span>");
        response.writeln("<span style=\"font-size: 10pt; margin-right: 20px;\">");
        response.writeln("<a href=\"/atropine/%s/gameslist/%d\">Old results interface</a>" % (htmlcommon.escape(tourney_name), round_no));
        response.writeln("</span>");
        response.writeln("</div>");

        response.writeln("</div>"); #entrymainpane

        # Show games as a list, to the right of the entry controls, or, if
        # it won't fit there, below the entry controls. Put an "Edit fixtures"
        # link in the top-right hand corner.
        response.writeln("<div class=\"gamelistpane boxshadow\">")
        response.writeln("""
<div class="resultsentrytitle">
Games
<div class="resultsentryeditlink">
<a href="/atropine/%s/fixtureedit/%d" title="Add or remove games, or change the players involved in a game">Edit fixtures</a>
</div>
</div>
""" % (htmlcommon.escape(tourney_name), round_no))

        response.writeln("<div class=\"gamelistpanebody\">")
        games_by_division = dict()
        num_divisions = tourney.get_num_divisions()
        for g in games:
            if g.division in games_by_division:
                games_by_division[g.division].append(g)
            else:
                games_by_division[g.division] = [g]

        for div in sorted(games_by_division):
            div_games = games_by_division[div]
            if num_divisions > 1:
                response.writeln("<div class=\"gamelistdivisionheading\">")
                response.writeln(htmlcommon.escape(tourney.get_division_name(div)))
                response.writeln("</div>")
            htmlcommon.show_games_as_html_table(response,
                    div_games, editable=False, remarks=None,
                    include_round_column=False, round_namer=None,
                    player_to_link=None, remarks_heading="",
                    show_game_type=True,
                    game_onclick_fn=lambda rnd, seq : "select_game(%d, false);" % (seq),
                    colour_win_loss=False, score_id_prefix="gamelistscore",
                    show_heading_row=False, hide_game_type_if_p=True)

        response.writeln("</div>") #gamelistpanebody
        response.writeln("</div>") #gamelistpane

        response.writeln("</div>"); #mainpane

    except countdowntourney.TourneyException as e:
        htmlcommon.show_tourney_exception(response, e);

    response.writeln("</body>");
    response.writeln("</html>");
