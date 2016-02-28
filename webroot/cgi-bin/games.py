#!/usr/bin/python

import sys;
import cgicommon;
import urllib;
import cgi;
import cgitb;
import os;
import re;
import random;

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def set_random_score(game, rounds, scrabble):
    r1 = game.p1.rating;
    r2 = game.p2.rating;

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
    document.getElementById(control_name).style = 'background-color: #ffffcc;';
    set_unsaved_data_warning();
}
""";

        print "</script>"
        
        if "save" in form or "randomresults" in form:
            # If the user clicked Save, then save the new scores to the
            # database.
            gamenum = 0;

            last_modified_element = form.getfirst("lastmodified");
            if last_modified_element:
                if not re.match("^gamescore_[0-9]+_[0-9]+$", last_modified_element):
                    last_modified_element = None;

            for g in games:
                if "randomresults" in form and not g.is_complete():
                    set_random_score(g, 15 if int_or_none(form.getfirst("scrabbleresults")) else 9, int_or_none(form.getfirst("scrabbleresults")) > 0);
                else:
                    score = form.getfirst("gamescore_%d_%d" % (g.round_no, g.seq));
                    # We used to be pretty liberal about what a score looked
                    # like, until we started allowing negative scores. Now we
                    # have to be a bit more strict so that a regexp can always
                    # tell the difference between a minus sign that's intended
                    # to separate one score from another, and a minus sign
                    # that's intended to mean a score is negative.

                    # A score is a number (which may be negative), followed by
                    # an optional asterisk, followed by a minus sign, followed
                    # by a number (which again may be negative), followed by
                    # an optional asterisk. Either asterisk means it was a
                    # tiebreak. Any number of spaces are allowed between any
                    # of these tokens, but you can't put a space in the middle
                    # of a number, or between a negative sign and a number.
                    
                    # If the score consists only of whitespace, then the game
                    # hasn't been played.
                    if not score or re.match("^\s*$", score):
                        g.set_score(None, None, False);
                    else:
                        m = re.match("^\s*(-?\d+)\s*(\*?)\s*-\s*(-?\d+)\s*(\*?)\s*$", score);
                        if not m:
                            remarks[(g.round_no, g.seq)] = "Invalid score: %s" % score;
                        else:
                            s1 = int(m.group(1));
                            s2 = int(m.group(3));
                            if m.group(2) == "*" or m.group(4) == "*":
                                tb = True;
                            else:
                                tb = False;
                            g.set_score(s1, s2, tb);

                gamenum += 1;
            tourney.merge_games(games);

        num_divisions = tourney.get_num_divisions()

        print "<div class=\"scorestable\">";
        print "<form method=\"POST\" action=\"%s?tourney=%s&amp;round=%d\">" % (baseurl, urllib.quote_plus(tourney_name), round_no);
        print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % cgi.escape(tourney_name, True);
        print "<input type=\"hidden\" name=\"round\" value=\"%d\" />" % round_no;
        print "<input type=\"hidden\" id=\"lastmodified\" name=\"lastmodified\" value=\"\" />";
        for div_index in range(num_divisions):
            if num_divisions > 1:
                print "<h2>%s</h2>" % (cgi.escape(tourney.get_division_name(div_index)))

            if tourney.are_players_assigned_teams():
                team_scores = tourney.get_team_scores()
                cgicommon.show_team_score_table(team_scores)
                print '<br />'

            div_games = tourney.get_games(round_no=round_no, only_players_known=False, division=div_index);

            cgicommon.show_games_as_html_table(div_games, editable=True, remarks=remarks, include_round_column=False, round_namer=None, player_to_link=lambda x : cgicommon.player_to_link(x, tourney.get_name(), False, True))

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
                # The box with focus should be the next unfilled box equal to
                # or after the one that was last modified. If they're all
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
