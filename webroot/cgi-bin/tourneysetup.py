#!/usr/bin/python

import cgi;
import cgitb;
import cgicommon;
import sys;
import csv;
import os;
import urllib;

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

def show_player_drop_down_box(players, control_name):
    print "<select name=\"%s\">" % (control_name)
    print "<option value=\"\">-- select player --</option>"
    for p in players:
        print "<option value=\"%s\">%s (%g)</option>" % (cgi.escape(p.name, True), cgi.escape(p.name), p.rating);
    print "</select>"

cgitb.enable();

cgicommon.set_module_path();
import countdowntourney;

print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/tourneysetup.py";
form = cgi.FieldStorage();
tourneyname = form.getfirst("tourney");
playerlist = form.getfirst("playerlist");
player_list_submit = form.getfirst("playerlistsubmit");
auto_rating_behaviour = int_or_none(form.getfirst("autoratingbehaviour"))
if auto_rating_behaviour is None:
    auto_rating_behaviour = countdowntourney.RATINGS_UNIFORM
modify_player_submit = form.getfirst("modifyplayersubmit");
rank = form.getfirst("rank");
rank = int_or_none(rank);
show_draws_column = int_or_none(form.getfirst("showdrawscolumn"))
show_tournament_rating = bool(int_or_none(form.getfirst("showtournamentratingcolumn")))
tr_bonus = float_or_none(form.getfirst("tournamentratingbonus"))
tr_diff_cap = float_or_none(form.getfirst("tournamentratingdiffcap"))
rules_submit = form.getfirst("rulessubmit");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Tourney Setup: " + str(tourneyname));

print "<body>";



if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);

cgicommon.show_sidebar(tourney);

print "<div class=\"mainpane\">";
print "<h1>Tourney Setup</h1>";

if tourneyname is None:
    print "<h1>Sloblock</h1>";
    print "<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>";
elif not tourney:
    print "<p>No valid tourney name specified</p>";
else:
    print '<p><a href="%s?tourney=%s">%s</a></p>' % (baseurl, urllib.quote_plus(tourneyname), cgi.escape(tourneyname));
    if request_method == "POST" and player_list_submit:
        if not playerlist:
            playerlist = ""
        lines = playerlist.split("\n");
        lines = filter(lambda x : len(x) > 0, map(lambda x : x.rstrip(), lines));
        reader = csv.reader(lines);
        player_rating_list = [];
        for row in reader:
            if len(row) == 1:
                player_rating_list.append((row[0].lstrip().rstrip(), None));
            else:
                player_rating_list.append((row[0].lstrip().rstrip(), row[1]));
        try:
            tourney.set_players(player_rating_list, auto_rating_behaviour);
            print "<p><strong>Player list updated successfully.</strong></p>";
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);
    if request_method == "POST" and rules_submit:
        try:
            tourney.set_rank_method(rank);
            tourney.set_show_draws_column(show_draws_column);
            tourney.set_show_tournament_rating_column(show_tournament_rating)
            tourney.set_tournament_rating_config(tr_bonus, tr_diff_cap)
            #tourney.set_table_size(players_per_table);
            print "<p><strong>Rules updated successfully.</strong></p>";
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);

    players = tourney.get_players();
    players = sorted(players, key=lambda x : x.name);

    print "<p>"
    if tourney.get_num_games() > 0:
        print "The tournament has started."
    if len(players) == 0:
        print "There are no players in the tourney yet."
    else:
        print "There are <a href=\"player.py?tourney=%s\">%d players</a>," % (urllib.quote_plus(tourney.get_name()), len(players))
        num_active = len(filter(lambda x : not x.is_withdrawn(), players))
        if num_active != len(players):
            print "of whom %d %s active and %d %s withdrawn." % (num_active, "is" if num_active == 1 else "are", len(players) - num_active, "has" if len(players) - num_active == 1 else "have")
        else:
            print "none withdrawn."
    print "</p>"

    num_divisions = tourney.get_num_divisions()
    if num_divisions > 1:
        print "<p>The players are distributed into <a href=\"divsetup.py?tourney=%s\">%d divisions</a>.</p>" % (urllib.quote_plus(tourney.get_name()), num_divisions)
        print "<blockquote>"
        for div_index in range(num_divisions):
            print "<li>%s: %d active players.</li>" % (tourney.get_division_name(div_index), tourney.get_num_active_players(div_index))
        print "</blockquote>"

    if tourney.get_num_games() == 0:
        players = tourney.get_players();
        print "<hr />"
        print "<h2>Player list</h2>";
        print "<p>"
        print "Enter player names in this box, one player per line. Blank lines are ignored."
        print "</p><p>"
        print "To give a player a rating, put a comma after the player's name and put the rating number after that, e.g. <tt>Harry Peters,1860</tt>"
        print "</p><p>"
        print "To indicate that a player is a patzer or bye (this affects how the fixture generators assign fixtures), give them a rating of zero: <tt>Apterous Prune,0</tt>"
        print "</p>"
        print "<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.quote_plus(tourneyname))
        print "<p>"
        print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname);
        print '<textarea rows="30" cols="40" name="playerlist">';
        if request_method == "POST" and playerlist:
            # If the user has submitted something, display what the user
            # submitted rather than what's in the database - this gives them
            # a chance to correct any errors without typing in the whole
            # change again.
            print cgi.escape(playerlist).strip()
        else:
            auto_rating = tourney.get_auto_rating_behaviour()
            writer = csv.writer(sys.stdout);
            # Write player names, or player names and ratings if the user
            # specified the players' ratings.
            for p in players:
                (name, rating) = p;
                if auto_rating != countdowntourney.RATINGS_MANUAL and rating != 0:
                    writer.writerow((cgi.escape(name),));
                else:
                    writer.writerow((cgi.escape(name), "%g" % (rating)));
        print "</textarea>";
        print "</p>"

        print "<p>"
        print "<h3>Rating assignment</h3>"
        print "<p>"
        print "How do you want to assign ratings? If your answer is \"what are ratings?\" select \"This tournament is not seeded\"."
        print "</p>"
        print "<blockquote>"
        auto_rating_behaviour = tourney.get_auto_rating_behaviour()
        print "<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" %s />" % (countdowntourney.RATINGS_MANUAL, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_MANUAL else "")
        print "<strong>Ratings are specified manually in the player list above.</strong> If you select this option, it is an error if you try to submit a player without a rating."
        print "<br />"
        print "<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" %s />" % (countdowntourney.RATINGS_GRADUATED, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_GRADUATED else "")
        print "<strong>The player list above is in rating order with the highest-rated player at the top</strong>. Ratings will be assigned automatically, with the player at the top of the list receiving a rating of 2000, and the player at the bottom 1000. If you select this option, it is an error to specify any ratings manually in the player list above except a rating of zero to indicate a patzer."
        print "<br />"
        print "<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" %s />" % (countdowntourney.RATINGS_UNIFORM, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_UNIFORM else "")
        print "<strong>This tournament is not seeded.</strong> Assign every non-patzer player a rating of 1000. If you select this option, it is an error to specify any ratings manually in the player list above except a rating of zero to indicate a patzer. If you don't know what ratings are or you don't care, select this option."
        print "</blockquote>"
        print "</p>"

        print "<p>"
        print "A player's rating may still be changed after the tournament has started."
        print "</p>"

        if len(players) and num_divisions > 1:
            print "<p>"
            print "<strong>Warning:</strong> There is already a player list defined. If you submit a new list using this form, these new players will replace any existing players, and <strong>any division setup will be lost</strong>."
            print "</p>"

        print "<p>"
        print '<input type="submit" name="playerlistsubmit" value="Save Player List" />'
        print "</p>"
        print '</form>'

    print "<hr />"

    print "<h2>Tourney rules</h2>";
    rank = tourney.get_rank_method();
    print '<form action="%s?tourney=%s" method="post" />' % (baseurl, urllib.quote_plus(tourneyname));
    print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname, True);
    print "<h3>Ranking order</h3>";
    print "<p>How do you want to rank players in the standings table?</p>";
    print '<input type="radio" name="rank" value="%d" %s /> Wins, then points. Draws are worth half a win. A win on a tiebreak is a win, not a draw.<br />' % (countdowntourney.RANK_WINS_POINTS, "checked" if rank == countdowntourney.RANK_WINS_POINTS else "");
    print '<input type="radio" name="rank" value="%d" %s /> Wins, then cumulative winning margin (spread). Draws are worth half a win.<br />' % (countdowntourney.RANK_WINS_SPREAD, "checked" if rank == countdowntourney.RANK_WINS_SPREAD else "")
    print '<input type="radio" name="rank" value="%d" %s /> Points only.' % (countdowntourney.RANK_POINTS, "checked" if rank == countdowntourney.RANK_POINTS else "");
    print '</p>';

    print "<h3>Draws</h3>"
    print "<p>"
    print "Tick this box if draws are possible in your tournament."
    print "</p><p>"
    print "<input type=\"checkbox\" name=\"showdrawscolumn\" value=\"1\" %s />" % ("checked" if tourney.get_show_draws_column() else "")
    print "Show draws column in standings table"
    print "</p>"

    print "<h3>Tournament Ratings</h3>"
    print "<p>"
    print "<input type=\"checkbox\" name=\"showtournamentratingcolumn\" value=\"1\" %s />" % ("checked" if tourney.get_show_tournament_rating_column() else "")
    print "Show tournament ratings in standings table"
    print "</p>"
    print "<p>"
    print "For each game you play, your tournament rating is calculated as follows."
    print "</p>"
    print "<ul>"
    print "<li>If you win, your opponent's <em>effective rating</em> plus the <em>win value</em>.</li>"
    print "<li>If you draw, your opponent's <em>effective rating</em>.</li>"
    print "<li>If you lose, your opponent's <em>effective rating</em> minus the <em>win value</em>.</li>"
    print "</ul>"
    print "<p>"
    print "The <em>win value</em> is <input type=\"number\" name=\"tournamentratingbonus\" value=\"%g\" maxlength=\"5\" />" % (tourney.get_tournament_rating_bonus_value())
    print "</p><p>"
    print "Your opponent's <em>effective rating</em> for a game is their rating at the start of the tournament, capped to within"
    print "<input type=\"number\" name=\"tournamentratingdiffcap\" value=\"%g\" maxlength=\"5\" />" % (tourney.get_tournament_rating_diff_cap())
    print "of your own."
    print "</p>"
    print "<p>"
    print "Your overall tournament rating is the mean average from all your games."
    print "</p>"
    print '<p><input type="submit" name="rulessubmit" value="Save Rules" /></p>'
    print "</form>";

    if tourney.get_num_games() > 0:
        print "<hr />"
        print '<h2>Delete rounds</h2>'
        print '<p>Press this button to delete the most recent round. You\'ll be asked to confirm on the next screen.</p>'
        print "<p>"
        print '<form action="/cgi-bin/delround.py" method="get" />'
        print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname)
        print '<input type="submit" name="delroundsetupsubmit" value="Delete most recent round" />'
        print '</form>'
        print "</p>"

print "</div>";

print "</body>";
print "</html>";
