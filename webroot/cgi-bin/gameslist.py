#!/usr/bin/python

import sys;
import cgicommon;
import urllib;
import cgi;
import cgitb;
import os;
import re;
import random;

CONFLICT_STRATEGY_FORCE = 0
CONFLICT_STRATEGY_DO_NOT_EMBLANKIFY = 1
CONFLICT_STRATEGY_ONLY_FILL_BLANKS = 2
CONFLICT_STRATEGY_DISCARD = 3

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def parse_score(score):
    # We used to be pretty liberal about what a score looked
    # like, until we started allowing negative scores. Now
    # we have to be a bit more strict so that a regexp can
    # always tell the difference between a minus sign
    # that's intended to separate one score from another,
    # and a minus sign that's intended to mean a score is
    # negative.

    # A score is a number (which may be negative), followed
    # by an optional *, followed by a minus sign, followed
    # by a number (which again may be negative), followed by
    # an optional *. Either * means it was a tiebreak. Any
    # number of spaces are allowed between any of these
    # tokens, but you can't put a space in the middle
    # of a number, or between a negative sign and a number.
    
    # If the score consists only of whitespace, then the
    # game hasn't been played.
    if not score or re.match("^\s*$", score):
        return (None, None, False)
    else:
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

def set_random_score(game, rounds, scrabble):
    r1 = game.p1.rating;
    r2 = game.p2.rating;

    if r1 + r2 == 0:
        game.set_score(0, 0, False);
        return;


    p1_threshold = float(r1) / float(r1 + r2);
    p2_threshold = p1_threshold;
    p1_threshold *= 0.8
    p2_threshold = 1 - ((1 - p2_threshold) * 0.8)

    #print "%g %g %.3f %.3f" % (game.p1.rating, game.p2.rating, p1_threshold, p2_threshold);

    p1_score = 0;
    p2_score = 0;

    for i in range(rounds):
        x = random.random();
        round_score = random.randint(5, 10);
        if round_score == 9:
            if random.randint(1, 4) == 1:
                round_score = 18;
            else:
                round_score = 7;
        if scrabble:
            round_score *= random.randint(2, 4)
        if r1 > 0 and x < p1_threshold:
            p1_score += round_score;
        elif r2 > 0 and x > p2_threshold:
            p2_score += round_score;
        else:
            if r1 > 0:
                p1_score += round_score;
            if r2 > 0:
                p2_score += round_score;

    if p1_score == p2_score and not(scrabble):
        if random.randint(0, 1) == 0:
            p1_score += 10;
        else:
            p2_score += 10;
        tb = True;
    else:
        tb = False;

    game.set_score(p1_score, p2_score, tb);


def show_conflict_resolution_box(tourney, games, round_no, stored_revision_no, stored_revision_timestamp, form):
    tourney_name = tourney.get_name()
    existing_strategy = int_or_none(form.getfirst("conflictstrategy"))
    
    if existing_strategy is None:
        existing_strategy = CONFLICT_STRATEGY_DO_NOT_EMBLANKIFY

    print """
<script>
function update_conflict_resolution_example(value) {
    var blank_to_non_blank = document.getElementById("cr_blanktononblank");
    var non_blank_to_non_blank = document.getElementById("cr_nonblanktononblank");
    var non_blank_to_blank = document.getElementById("cr_nonblanktoblank");

    if (value == 0) { /* CONFLICT_STRATEGY_FORCE */
        blank_to_non_blank.innerHTML = "88-88";
        non_blank_to_non_blank.innerHTML = "88-88";
        non_blank_to_blank.innerHTML = "-";
    }
    else if (value == 1) { /* CONFLICT_STRATEGY_DO_NOT_EMBLANKIFY */
        blank_to_non_blank.innerHTML = "88-88";
        non_blank_to_non_blank.innerHTML = "88-88";
        non_blank_to_blank.innerHTML = "77-77";
    }
    else if (value == 2) { /* CONFLICT_STRATEGY_ONLY_FILL_BLANKS */
        blank_to_non_blank.innerHTML = "88-88";
        non_blank_to_non_blank.innerHTML = "77-77";
        non_blank_to_blank.innerHTML = "77-77";
    }
    else if (value == 3) { /* CONFLICT_STRATEGY_DISCARD */
        blank_to_non_blank.innerHTML = "-";
        non_blank_to_non_blank.innerHTML = "77-77";
        non_blank_to_blank.innerHTML = "77-77";
    }
}
</script>
    """

    print "<div class=\"conflictresolution\">"
    print "<form method=\"POST\" action=\"%s?tourney=%s&amp;round=%d\">" % (baseurl, urllib.quote_plus(tourney_name), round_no);
    print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgi.escape(tourney_name, True));
    print "<input type=\"hidden\" name=\"round\" value=\"%d\" />" % (round_no);
    print "<input type=\"hidden\" name=\"revision\" value=\"%d\" />" % (stored_revision_no)

    # Include the submitted scores in this conflict resolution form, so that
    # when the user presses "Resolve Conflicts" we remember what the original
    # submissions were.
    for g in games:
        input_name = "gamescore_%d_%d" % (g.round_no, g.seq)
        submitted_score = form.getfirst(input_name)
        if submitted_score is not None:
            print "<input type=\"hidden\" name=\"%s\" value=\"%s\" />" % (cgi.escape(input_name), cgi.escape(submitted_score, True))

    score = form.getfirst("gamescore_%d_%d" % (g.round_no, g.seq));
    print "<div class=\"conflictresolutiontoprow\">"
    print "Last conflicting modification occurred at: %s" % (cgi.escape(stored_revision_timestamp))
    print "</div>"

    print "<div class=\"conflictresolutionchoicerow\">"
    print "<div class=\"conflictresolutionradiobutton\">"
    print "<input type=\"radio\" name=\"conflictstrategy\" id=\"conflictstrategydiscard\" value=\"%d\" onchange=\"update_conflict_resolution_example(this.value)\" %s />" % (CONFLICT_STRATEGY_DISCARD, "checked" if existing_strategy == CONFLICT_STRATEGY_DISCARD else "")
    print "</div>"
    print "<div class=\"conflictresolutionlabel\">"
    print "<label for=\"conflictstrategydiscard\">Discard my submission - go with what's currently in the database.</label>"
    print "</div>"
    print "</div>"

    print "<div class=\"conflictresolutionchoicerow\">"
    print "<div class=\"conflictresolutionradiobutton\">"
    print "<input type=\"radio\" name=\"conflictstrategy\" id=\"conflictstrategyfillblanks\" value=\"%d\" onchange=\"update_conflict_resolution_example(this.value)\" %s />" % (CONFLICT_STRATEGY_ONLY_FILL_BLANKS, "checked" if existing_strategy == CONFLICT_STRATEGY_ONLY_FILL_BLANKS else "")
    print "</div>"
    print "<div class=\"conflictresolutionlabel\">"
    print "<label for=\"conflictstrategyfillblanks\">If a game currently has no result but my submission provides one, fill in that game's result with my submission. Discard any other changes.</label>"
    print "</div>"
    print "</div>"

    print "<div class=\"conflictresolutionchoicerow\">"
    print "<div class=\"conflictresolutionradiobutton\">"
    print "<input type=\"radio\" name=\"conflictstrategy\" id=\"conflictstrategydonotemblankify\" value=\"%d\" onchange=\"update_conflict_resolution_example(this.value);\" %s />" % (CONFLICT_STRATEGY_DO_NOT_EMBLANKIFY, "checked" if existing_strategy == CONFLICT_STRATEGY_DO_NOT_EMBLANKIFY else "")
    print "</div>"
    print "<div class=\"conflictresolutionlabel\">"
    print "<label for=\"conflictstrategydonotemblankify\">If my submission has a result for a game, overwrite the existing result with my submission, but do not overwrite an existing result with a blank one.</label>"
    print "</div>"
    print "</div>"

    print "<div class=\"conflictresolutionchoicerow\">"
    print "<div class=\"conflictresolutionradiobutton\">"
    print "<input type=\"radio\" name=\"conflictstrategy\" id=\"conflictstrategyforce\" value=\"%d\" onchange=\"update_conflict_resolution_example(this.value);\" %s />" % (CONFLICT_STRATEGY_FORCE, "checked" if existing_strategy == CONFLICT_STRATEGY_FORCE else "")
    print "</div>"
    print "<div class=\"conflictresolutionlabel\">"
    print "<label for=\"conflictstrategyforce\">Overwrite everything with my submission, even if that means overwriting existing results with blank results.</label>"
    print "</div>"
    print "</div>"

    show_conflict_resolution_example(existing_strategy)

    print "<div class=\"conflictresolutionbottomrow\">"
    print "<div class=\"conflictresolutionsubmit\">"
    print "<input type=\"submit\" name=\"save\" value=\"Resolve Conflicts\" />"
    print "</div>"
    print "</div>"

    print "</form>"
    print "</div>"

def show_conflict_resolution_example(existing_strategy):
    print "<div class=\"conflictresolutionexample\">"
    print "<div class=\"conflictresolutionexampletitle\">Example:</div>"
    print "<table class=\"conflictresolutionexampletable\">"
    print "<tr>"
    print "<th>Current result</th><th>Your submission</th><th>New result</th>"
    print "</tr>"
    print "<tr>"
    print "<td>-</td><td>88-88</td><td class=\"cr_newresultcol\" id=\"cr_blanktononblank\">%s</td>" % ("88-88" if existing_strategy != CONFLICT_STRATEGY_DISCARD else "-")
    print "</tr>"
    print "<tr>"
    print "<td>77-77</td><td>88-88</td><td class=\"cr_newresultcol\" id=\"cr_nonblanktononblank\">%s</td>" % ("88-88" if existing_strategy in (CONFLICT_STRATEGY_FORCE, CONFLICT_STRATEGY_DO_NOT_EMBLANKIFY) else "77-77")
    print "</tr>"
    print "<tr>"
    print "<td>77-77</td><td>-</td><td class=\"cr_newresultcol\" id=\"cr_nonblanktoblank\">%s</td>" % ("-" if existing_strategy == CONFLICT_STRATEGY_FORCE else "77-77")
    print "</tr>"
    print "</table>"
    print "</div>"

cgitb.enable();

print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/gameslist.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

import countdowntourney;

cgicommon.print_html_head("Games: " + str(tourney_name));

print "<body>";

if tourney_name is None:
    print "<h1>No tourney specified</h1>";
    print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>";
    print "</body></html>";
    sys.exit(0);

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
            print "<p>\"%s\" is not a valid round number.</p>";
    
    if round_no is not None:
        games = tourney.get_games(round_no=round_no);
        rounds = tourney.get_rounds();
        round_name = None;
        last_modified_element = None;
        for r in rounds:
            if r["num"] == round_no:
                round_name = r.get("name", None);
                break;
        if not round_name:
            round_name = "Round " + str(round_no);

        remarks = dict();

        print "<h1>Score editor: %s</h1>" % cgi.escape(round_name);

        print "<p>";
        print "<a href=\"/cgi-bin/fixtureedit.py?tourney=%s&amp;round=%d\">Edit fixtures</a>" % (urllib.quote_plus(tourney_name), round_no);
        print "</p>";

        print "<script>"
        print """function set_unsaved_data_warning() {
    if (window.onbeforeunload == null) {
        window.onbeforeunload = function() {
            return 'You have modified scores on this page and not saved them.';
        };
    }
}

function unset_unsaved_data_warning() {
    window.onbeforeunload = null;
}

function score_modified(control_name) {
    document.getElementById('lastmodified').value = control_name;
    document.getElementById(control_name).style.backgroundColor = '#ffffcc';
    set_unsaved_data_warning();
}
""";

        print "</script>"

        conflict_resolution = False
        conflict_strategy = int_or_none(form.getfirst("conflictstrategy"))
        stored_revision_no = tourney.get_game_table_revision_no(round_no)
        stored_revision_timestamp = tourney.get_game_table_revision_time(round_no, stored_revision_no)
        
        if "save" in form or "randomresults" in form:
            # If the user clicked Save, then save the new scores to the
            # database.
            last_modified_element = form.getfirst("lastmodified");
            if last_modified_element:
                if not re.match("^gamescore_[0-9]+_[0-9]+$", last_modified_element):
                    last_modified_element = None;

            submitted_revision_no = int_or_none(form.getfirst("revision"))

            if "randomresults" not in form and submitted_revision_no < stored_revision_no:
                # One or more games in this round have changed since the user
                # last refreshed the page. Ask the user how we should cope with
                # this.
                cgicommon.show_warning_box("<p>The results for this round have been modified in another window since you last refreshed this page.</p>" +
                        "<p>The current state of the games is shown below, with your changes on the right-hand side.</p>" +
                        "<p>What do you want to do with your changes? Select one of the options below, then Resolve Conflicts.</p>");
                show_conflict_resolution_box(tourney, games, round_no, stored_revision_no, stored_revision_timestamp, form)
                conflict_resolution = True
            else:
                for g in games:
                    if "randomresults" in form and not g.is_complete():
                        set_random_score(g, 15 if int_or_none(form.getfirst("scrabbleresults")) else 9, int_or_none(form.getfirst("scrabbleresults")) > 0);
                    else:
                        score = form.getfirst("gamescore_%d_%d" % (g.round_no, g.seq));
                        parsed_score = parse_score(score)
                        if parsed_score is None:
                            remarks[(g.round_no, g.seq)] = "Invalid score: %s" % (score)
                        else:
                            apply_change = True
                            if conflict_strategy == CONFLICT_STRATEGY_DISCARD:
                                # Don't overwrite any changes
                                apply_change = False
                            elif conflict_strategy == CONFLICT_STRATEGY_ONLY_FILL_BLANKS:
                                # Prefer our changes only when that would fill
                                # in an unplayed game with a result
                                if g.is_complete():
                                    apply_change = False
                            elif conflict_strategy == CONFLICT_STRATEGY_DO_NOT_EMBLANKIFY:
                                # Prefer our changes except where that would
                                # replace a filled-in result with a blank one
                                if parsed_score[0] is None or parsed_score[1] is None:
                                    apply_change = False
                            # Otherwise, always prefer our changes

                            if apply_change:
                                g.set_score(parsed_score[0], parsed_score[1], parsed_score[2])
                tourney.merge_games(games);

        stored_revision_no = tourney.get_game_table_revision_no(round_no)
        num_divisions = tourney.get_num_divisions()

        print "<div class=\"scorestable\">";

        # If we've put up the conflict resolution form, then what we print here
        # isn't a form but an ordinary table showing the current results and
        # the user's submission.
        # The usual case is not conflict_resolution, where we put the game list
        # form here.

        if not conflict_resolution:
            print "<form method=\"POST\" action=\"%s?tourney=%s&amp;round=%d\">" % (baseurl, urllib.quote_plus(tourney_name), round_no);
            print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % cgi.escape(tourney_name, True);
            print "<input type=\"hidden\" name=\"round\" value=\"%d\" />" % round_no;
            print "<input type=\"hidden\" id=\"lastmodified\" name=\"lastmodified\" value=\"\" />";
            print "<input type=\"hidden\" name=\"revision\" value=\"%d\" />" % (stored_revision_no)
        for div_index in range(num_divisions):
            if num_divisions > 1:
                print "<h2>%s</h2>" % (cgi.escape(tourney.get_division_name(div_index)))

            if tourney.are_players_assigned_teams():
                team_scores = tourney.get_team_scores()
                cgicommon.show_team_score_table(team_scores)
                print '<br />'

            div_games = tourney.get_games(round_no=round_no, only_players_known=False, division=div_index);

            if conflict_resolution:
                for g in games:
                    score = form.getfirst("gamescore_%d_%d" % (g.round_no, g.seq));
                    parsed_score = parse_score(score)
                    if parsed_score is None:
                        remarks[(g.round_no, g.seq)] = "Invalid score: %s" % (score)
                    else:
                        # If the score the user has entered is different
                        # from the score in the table, display the
                        # user's submitted score in the Remarks column.
                        if not ((g.s1 is None and g.s2 is None and parsed_score[0] is None and parsed_score[1] is None) or (g.s1 == parsed_score[0] and g.s2 == parsed_score[1] and g.tb == parsed_score[2]) ):
                            player_names = g.get_player_names()
                            if parsed_score[0] is None or parsed_score[1] is None:
                                remarks[(g.round_no, g.seq)] = "%s - %s" % (player_names[0], player_names[1])
                            else:
                                remarks[(g.round_no, g.seq)] = "%s %d%s - %d%s %s" % (
                                        player_names[0],
                                        parsed_score[0],
                                        "*" if (parsed_score[0] > parsed_score[1] and parsed_score[2]) else "",
                                        parsed_score[1],
                                        "*" if (parsed_score[1] >= parsed_score[0] and parsed_score[2]) else "",
                                        player_names[1])

                cgicommon.show_games_as_html_table(div_games, editable=False,
                        remarks=remarks, include_round_column=False,
                        round_namer=None,
                        player_to_link=lambda x : cgicommon.player_to_link(x, tourney.get_name(), False, True),
                        remarks_heading="Your submission")
            else:
                cgicommon.show_games_as_html_table(div_games, editable=True,
                        remarks=remarks, include_round_column=False,
                        round_namer=None,
                        player_to_link=lambda x : cgicommon.player_to_link(x, tourney.get_name(), False, True))

        if not conflict_resolution:
            print "<p><input type=\"submit\" name=\"save\" value=\"Save\" onclick=\"unset_unsaved_data_warning();\" /></p>";

            if form.getfirst("showrandomresultsbutton"):
                print "<p><input type=\"submit\" name=\"randomresults\" value=\"Random Results\" /></p>";
            elif form.getfirst("showscrabbleresultsbutton"):
                print "<p><input type=\"submit\" name=\"randomresults\" value=\"Random Scrabble-ish Results\" /></p>";
                print "<p><input type=\"hidden\" name=\"scrabbleresults\" value=\"1\" /></p>";

            print "</form>"

            focus = None;
            if last_modified_element:
                m = re.match("^gamescore_([0-9]+)_([0-9]+)$", last_modified_element)
                if m:
                    lastmod_index = (int(m.group(1)), int(m.group(2)));
                    # The box with focus should be the next unfilled box equal
                    # to or after the one that was last modified. If they're all
                    # filled, put the focus on the first box.

                    for i in range(0, len(games)):
                        if games[i].round_no == lastmod_index[0] and games[i].seq == lastmod_index[1]:
                            # We've found the control we last modified;
                            for j in range(0, len(games)):
                                g = games[(i + j) % len(games)]
                                if not g.is_complete():
                                    focus = (g.round_no, g.seq)
                                    break
                            break
            if games:
                if focus is None:
                    focus = (games[0].round_no, games[0].seq);

                control_with_focus = "gamescore_%d_%d" % (focus[0], focus[1]);
                print "<script>"
                print "document.getElementById('" + control_with_focus + "').focus();"
                print "</script>"

        print "</div>"; #scorestable

    print "</div>"; #mainpane

except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);

print "</body>";
print "</html>";

sys.exit(0);
