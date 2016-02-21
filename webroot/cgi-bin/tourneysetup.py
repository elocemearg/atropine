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

def show_player_drop_down_box(players, control_name):
    print "<select name=\"%s\">" % (control_name)
    print "<option value=\"\">-- select player --</option>"
    for p in players:
        print "<option value=\"%s\">%s (%d)</option>" % (cgi.escape(p.name, True), cgi.escape(p.name), p.rating);
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
rules_submit = form.getfirst("rulessubmit");
withdraw_player_submit = form.getfirst("withdrawplayersubmit");
unwithdraw_player_submit = form.getfirst("unwithdrawplayersubmit");
withdraw_player_name = form.getfirst("withdrawplayername");
unwithdraw_player_name = form.getfirst("unwithdrawplayername");


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
            #tourney.set_table_size(players_per_table);
            print "<p><strong>Rules updated successfully.</strong></p>";
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);
    if request_method == "POST" and modify_player_submit:
        try:
            cur_name = form.getfirst("playername")
            if cur_name:
                new_name = form.getfirst("newplayername")
                new_rating = form.getfirst("newplayerrating")
                if new_name:
                    tourney.rename_player(cur_name, new_name);
                    cur_name = new_name;
                if new_rating:
                    try:
                        new_rating = int(new_rating);
                        tourney.rerate_player(cur_name, new_rating);
                    except ValueError:
                        print "<p><strong>Failed to rerate player: \"%s\" is not a valid rating.</strong></p>" % cgi.escape(new_rating);
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);
    if request_method == "POST" and withdraw_player_submit and withdraw_player_name: 
        try:
            tourney.withdraw_player(withdraw_player_name)
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);
    if request_method == "POST" and unwithdraw_player_submit and unwithdraw_player_name:
        try:
            tourney.unwithdraw_player(unwithdraw_player_name)
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e)

    players = tourney.get_players();
    players = sorted(players, key=lambda x : x.name);

    print "<p>"
    if tourney.get_num_games() > 0:
        print "The tournament has started."
    print "There are %d players," % len(players)
    num_active = len(filter(lambda x : not x.is_withdrawn(), players))
    if num_active != len(players):
        print "of whom %d are active and %d withdrawn." % (num_active, len(players) - num_active)
    else:
        print "none withdrawn."
    print "</p>"

    num_divisions = tourney.get_num_divisions()
    if num_divisions > 1:
        print "<p>The players are distributed into %d divisions.</p>" % (num_divisions)
        print "<blockquote>"
        for div_index in range(num_divisions):
            print "<li>%s: %d active players.</li>" % (tourney.get_division_name(div_index), tourney.get_num_active_players(div_index))
        print "</blockquote>"


    if tourney.get_num_games() > 0:
        print "<h2>Modify player</h2>"
        print "<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.quote_plus(tourneyname))
        print "<p>"
        print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % cgi.escape(tourneyname, True)
        show_player_drop_down_box(players, "playername")
        print "</p>"

        print "<p>"
        print "New name <input type=\"text\" name=\"newplayername\" /> (blank to leave unchanged)"
        print "</p>"
        print "<p>"
        print "New rating <input type=\"text\" name=\"newplayerrating\" /> (blank to leave unchanged)"
        print "</p>"
        print "<p>"
        print "<input type=\"submit\" name=\"modifyplayersubmit\" value=\"Modify Player\" />"
        print "</p>"
        print "</form>"
    else:
        players = tourney.get_players();
        print "<h2>Player list</h2>";
        print "<p>"
        print "Enter player names in this box, one player per line. Blank lines are ignored."
        print "</p><p>"
        print "To give a player a rating, put a comma after the player's name and put the rating number after that, e.g. <tt>Harry Peters,1860</tt>"
        print "</p><p>"
        print "To indicate that a player is a patzer, give them a rating of zero: <tt>Apterous Prune,0</tt>"
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
                    writer.writerow((cgi.escape(name), str(rating)));
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

        print "<p>"
        print '<input type="submit" name="playerlistsubmit" value="Save Player List" />'
        print "</p>"
        print '</form>'

    rank = tourney.get_rank_method();
    print "<h2>Tourney rules</h2>";
    print '<form action="%s?tourney=%s" method="post" />' % (baseurl, urllib.quote_plus(tourneyname));
    print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname, True);
    print "<h3>Rank players by</h3>";
    print "<blockquote>";
    print '<input type="radio" name="rank" value="%d" %s /> Wins, then points. Draws are worth half a win. A win on a tiebreak is a win, not a draw.<br />' % (countdowntourney.RANK_WINS_POINTS, "checked" if rank == countdowntourney.RANK_WINS_POINTS else "");
    print '<input type="radio" name="rank" value="%d" %s /> Wins, then cumulative winning margin. Draws are worth half a win.<br />' % (countdowntourney.RANK_WINS_SPREAD, "checked" if rank == countdowntourney.RANK_WINS_SPREAD else "")
    print '<input type="radio" name="rank" value="%d" %s /> Points only.' % (countdowntourney.RANK_POINTS, "checked" if rank == countdowntourney.RANK_POINTS else "");
    print '</blockquote>';

    print "<h3>Draws</h3>"
    print "<blockquote>"
    print "<input type=\"checkbox\" name=\"showdrawscolumn\" value=\"1\" %s />" % ("checked" if tourney.get_show_draws_column() else "")
    print "Show draws column in standings table"
    print "</blockquote>"

    print "<p>"
    print '<input type="submit" name="rulessubmit" value="Save Rules" />';
    print "</p>"
    print "</form>";

    print '<h2>Division Setup</h2>'
    print "<p>"
    print '<a href="/cgi-bin/divsetup.py?tourney=%s">Assign players to divisions</a>' % (urllib.quote_plus(tourneyname))
    print "</p>"

    print '<h2>Team Setup</h2>'
    print '<p>'
    print '<a href="/cgi-bin/teamsetup.py?tourney=%s">Assign players to teams</a>' % (urllib.quote_plus(tourneyname))
    print '</p>'

    active_players = tourney.get_active_players();
    active_players = sorted(active_players, key=lambda x : x.name);
    if len(active_players) > 0:
        print '<h2>Withdraw player</h2>'
        print '<p>'
        print 'If you withdraw a player, they will not be included in future rounds unless and until they are reinstated.'
        print 'Withdrawn players will still appear in the standings table, and any fixtures already played or generated will stand.'
        print '</p>'
        print '<form action="%s?tourney=%s" method="post" />' % (baseurl, urllib.quote_plus(tourneyname))
        print '<p>'
        show_player_drop_down_box(active_players, "withdrawplayername")
        print '</p><p>'
        print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname);
        print "<input type=\"submit\" name=\"withdrawplayersubmit\" value=\"Withdraw Player\" />"
        print '</p>'
        print '</form>'

    withdrawn_players = tourney.get_withdrawn_players()
    if withdrawn_players:
        withdrawn_players = sorted(withdrawn_players, key=lambda x : x.name)
        print '<h2>Reinstate player</h2>'
        print '<p>The following players are currently withdrawn from the tourney.</p>'
        print '<blockquote>'
        for p in withdrawn_players:
            print '<li>%s</li>' % (cgi.escape(p.name))
        print '</blockquote>'

        print '<p>These players will not be included in future rounds until reinstated below.</p>'
        print '<form action="%s?tourney=%s" method="post" />' % (baseurl, urllib.quote_plus(tourneyname))
        print '<p>'
        show_player_drop_down_box(withdrawn_players, "unwithdrawplayername")
        print '</p><p>'
        print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname);
        print '<input type=\"submit\" name=\"unwithdrawplayersubmit\" value=\"Reinstate Player\" />'
        print '</p>'
        print '</form>'

    if tourney.get_num_games() > 0:
        print '<h2>Delete rounds</h2>'
        print '<p>Press this button to delete the most recent round. You\'ll be asked to confirm on the next screen.</p>'
        print '<form action="/cgi-bin/delround.py" method="get" />'
        print '<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname)
        print '<input type="submit" name="delroundsetupsubmit" value="Delete most recent round" />'
        print '</form>'
    
    if len(players) > 0:
        print '<h2>Export standings and results</h2>'
        print '<p>'
        print '<a href="/cgi-bin/export.py?tourney=%s&format=html" target="_blank">HTML (opens in new window)</a>' % urllib.quote_plus(tourneyname)
        print '</p><p>'
        print '<a href="/cgi-bin/export.py?tourney=%s&format=text" target="_blank">Plain text (opens in new window)</a>' % urllib.quote_plus(tourneyname)
        print '</p>'

print "</div>";

print "</body>";
print "</html>";
