#!/usr/bin/python3

import cgi;
import cgitb;
import cgicommon;
import sys;
import csv;
import os;
import json
import urllib.request, urllib.parse, urllib.error;

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
    print("<select name=\"%s\">" % (control_name))
    print("<option value=\"\">-- select player --</option>")
    for p in players:
        print("<option value=\"%s\">%s (%g)</option>" % (cgi.escape(p.name, True), cgi.escape(p.name), p.rating));
    print("</select>")

def make_double_quoted_string(s):
    new_string = ['\"']
    for l in s:
        if l == '\n':
            new_string += ['\\', 'n']
        elif l == '\r':
            new_string += ['\\', 'r']
        elif l == '\t':
            new_string += ['\\', 't']
        else:
            if l == '\\' or l == '\"':
                new_string.append('\\')
            new_string.append(l)
    new_string.append('\"')
    return "".join(new_string)

player_list_example_uniform = """Lavinia Splatterbury
Cymbelina Spatchcock
Compton Spongeworthy
Plungemaster Thompson
Flopsbourne McJumble
Apterous Prune,0"""

player_list_example_graduated = """Lavinia Splatterbury
Cymbelina Spatchcock
Compton Spongeworthy
Plungemaster Thompson
Flopsbourne McJumble
Apterous Prune,0"""

player_list_example_manual = """Lavinia Splatterbury,1953
Cymbelina Spatchcock,1901
Compton Spongeworthy,1874
Plungemaster Thompson,1640
Flopsbourne McJumble,1559
Apterous Prune,0"""

player_list_rating_help = "To give a player a rating, put a comma after the player's name and put the rating number after that, e.g. <tt>Harry Peters,1860</tt>"

cgitb.enable();

cgicommon.set_module_path();
import countdowntourney;

print("Content-Type: text/html; charset=utf-8");
print("");

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

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Tourney Setup: " + str(tourneyname));

print ("<script>")
print ("""
function set_player_list_example(which) {
    var element = document.getElementById("playerlistexamplepre");
    if (element == null)
        return;

    switch (which) {
""")

for (num, text) in [
        (countdowntourney.RATINGS_UNIFORM, player_list_example_uniform),
        (countdowntourney.RATINGS_GRADUATED, player_list_example_graduated),
        (countdowntourney.RATINGS_MANUAL, player_list_example_manual)]:
    print ("""
        case %d:
            element.innerText = %s;
            break;
    """ % (num, json.dumps(text)))

print ("""
    }
}
</script>
""")

print("<body>");

cgicommon.assert_client_from_localhost()

if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);
        print("<p><a href=\"/cgi-bin/home.py\">Home</a></p>")
        print("</body></html>")
        sys.exit(1)

cgicommon.show_sidebar(tourney);

print("<div class=\"mainpane\">");
print("<h1>Tourney Setup</h1>");

if tourneyname is None:
    print("<h1>Sloblock</h1>");
    print("<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>");
elif not tourney:
    print("<p>No valid tourney name specified</p>");
else:
    if request_method == "POST" and player_list_submit:
        div_index = 0
        if not playerlist:
            playerlist = ""
        lines = playerlist.split("\n");
        lines = [x for x in [x.rstrip() for x in lines] if len(x) > 0];
        reader = csv.reader(lines);
        player_rating_list = [];
        prev_player_name = "-"
        for row in reader:
            if len(row) == 1:
                if row[0].strip() == "-":
                    if prev_player_name != "-":
                        # This is a division separator - it tells us that the
                        # players after this point go in the next division down.
                        div_index += 1
                else:
                    player_rating_list.append((row[0].lstrip().rstrip(), None, div_index));
            else:
                player_rating_list.append((row[0].lstrip().rstrip(), row[1], div_index));
            prev_player_name = row[0].strip()
        try:
            tourney.set_players(player_rating_list, auto_rating_behaviour);
            print("<p><strong>Player list updated successfully.</strong></p>");
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);

    num_divisions = tourney.get_num_divisions()

    if request_method == "POST" and rules_submit:
        try:
            tourney.set_rank_method(rank);
            tourney.set_show_draws_column(show_draws_column);
            for div_index in range(num_divisions):
                div_prefix = "div%d_" % (div_index)
                suffixes = [ "lastround", "numgamesperplayer", "qualplaces" ]
                for suffix in suffixes:
                    name = div_prefix + suffix
                    value = form.getfirst(name)
                    if value is None:
                        value = 0
                    else:
                        try:
                            value = int(value)
                        except ValueError:
                            value = 0
                        if value < 0:
                            value = 0
                    tourney.set_attribute(name, value)
            print("<p><strong>Rules updated successfully.</strong></p>");
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);

    players = tourney.get_players();
    players = sorted(players, key=lambda x : x.name);

    print("<p>")
    if tourney.get_num_games() > 0:
        print("The tournament has started.")
    if len(players) == 0:
        print("There are no players in the tourney yet.")
    else:
        print("There are <a href=\"player.py?tourney=%s\">%d players</a>," % (urllib.parse.quote_plus(tourney.get_name()), len(players)))
        num_active = len([x for x in players if not x.is_withdrawn()])
        if num_active != len(players):
            print("of whom %d %s active and %d %s withdrawn." % (num_active, "is" if num_active == 1 else "are", len(players) - num_active, "has" if len(players) - num_active == 1 else "have"))
        else:
            print("none withdrawn.")
    print("</p>")

    if tourney.get_num_games() == 0:
        if players:
            cgicommon.show_info_box("""<p>
When you're happy with the player list and the
<a href="#tourneyrules">tourney rules</a> below, head to
<a href="/cgi-bin/fixturegen.py?tourney=%s">Generate fixtures</a> to generate
the first games. Once you've generated the first games, you won't be able to
delete players, but you can always withdraw them, edit names and ratings, or
add new players.</p>""" % (urllib.parse.quote_plus(tourney.get_name())))
        else:
            cgicommon.show_info_box("<p>This tourney has no players defined yet. Before doing anything else, enter the list of player names below. You can always add more players, or withdraw them, later on if necessary.</p>");


    if num_divisions > 1:
        print("<p>The players are distributed into <a href=\"divsetup.py?tourney=%s\">%d divisions</a>.</p>" % (urllib.parse.quote_plus(tourney.get_name()), num_divisions))
        print("<blockquote>")
        for div_index in range(num_divisions):
            print("<li>%s: %d active players.</li>" % (tourney.get_division_name(div_index), tourney.get_num_active_players(div_index)))
        print("</blockquote>")

    if tourney.get_num_games() == 0:
        players = sorted(tourney.get_players(), key=lambda x : (x.get_division(), x.get_id()))
        print("<hr />")
        print("<h2>Player list setup</h2>");

        print(("<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.parse.quote_plus(tourneyname))))

        print("<p>")
        print("How do you want to assign ratings to players? Ratings are used by the Overachievers table and some fixture generators. If you don't know what ratings are, or you don't care, select \"This tournament is not seeded\".")
        print("</p>")
        print("<blockquote>")
        auto_rating_behaviour = tourney.get_auto_rating_behaviour()
        print(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" %s />" % (countdowntourney.RATINGS_MANUAL, countdowntourney.RATINGS_MANUAL, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_MANUAL else "")))
        print("<strong>Ratings are specified manually in the player list below.</strong> If you select this option, it is an error if you try to submit a player without a rating.")
        print("<br />")
        print(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" %s />" % (countdowntourney.RATINGS_GRADUATED, countdowntourney.RATINGS_GRADUATED, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_GRADUATED else "")))
        print("<strong>The player list above is in rating order with the highest-rated player at the top</strong>. Ratings will be assigned automatically, with the player at the top of the list receiving a rating of 2000, and the player at the bottom 1000. If you select this option, it is an error to specify any ratings manually in the player list above except a rating of zero to indicate a prune.")
        print("<br />")
        print(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" %s />" % (countdowntourney.RATINGS_UNIFORM, countdowntourney.RATINGS_UNIFORM, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_UNIFORM else "")))
        print("<strong>This tournament is not seeded.</strong> Assign every non-prune player a rating of 1000. If you select this option, it is an error to specify any ratings manually in the player list above except a rating of zero to indicate a prune. If unsure, select this option.")
        print("</blockquote>")

        print("<p>")
        print("A player's rating may still be changed after the tournament has started.")
        print("</p>")

        print("<h2>Player list</h2>");
        print("<p>")
        print("Enter player names in this box, one player per line, then click <em>Save Player List</em>.")
        print("</p>")

        print("<div class=\"playerlist\">")
        print("<div class=\"playerlistpane\">")
        print("<p>")
        print('<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname));
        print('<textarea rows="28" cols="40" name="playerlist">');
        if request_method == "POST" and playerlist:
            # If the user has submitted something, display what the user
            # submitted rather than what's in the database - this gives them
            # a chance to correct any errors without typing in the whole
            # change again.
            sys.stdout.write(cgi.escape(playerlist).strip() + '\n')
        else:
            auto_rating = tourney.get_auto_rating_behaviour()
            writer = csv.writer(sys.stdout);
            prev_div_index = 0
            # Write player names, or player names and ratings if the user
            # specified the players' ratings.
            for p in players:
                (name, rating, div_index) = p;
                if div_index != prev_div_index:
                    writer.writerow(("-",))
                if auto_rating != countdowntourney.RATINGS_MANUAL and rating != 0:
                    writer.writerow((cgi.escape(name),));
                else:
                    writer.writerow((cgi.escape(name), "%g" % (rating)));
                prev_div_index = div_index
        print("</textarea>");
        print("</p>")

        print("<p>")
        print('<input type="submit" name="playerlistsubmit" value="Save Player List" />')
        print("</p>")

        print("</div>")

        print("<div class=\"playerlisthelp\">")
        print("<h3>Example</h3>")
        print("<p id=\"playerlistexample\">")
        print("<pre id=\"playerlistexamplepre\">")
        if auto_rating_behaviour == countdowntourney.RATINGS_UNIFORM:
            print(player_list_example_uniform)
        elif auto_rating_behaviour == countdowntourney.RATINGS_GRADUATED:
            print(player_list_example_graduated)
        else:
            print(player_list_example_manual)
        print("</pre>")
        print("</p>")
        print("<p id=\"playerlistratinghelp\">")
        if auto_rating_behaviour == countdowntourney.RATINGS_MANUAL:
            print(player_list_rating_help);
        print("</p>")

        print("<p>")
        print("To indicate that a player is a prune or bye, which affects how the fixture generators assign fixtures, give them a rating of zero: <tt>Apterous Prune,0</tt>")
        print("</p>")

        print("<p>")
        print("To divide the players into divisions, put a line containing only a dash (<tt>-</tt>) between the desired divisions.")
        print("</p>")
        print("</div>")
        print("</div>")
        print("</form>")
        print("<div class=\"playerlistclear\"></div>")

    if tourney.get_players():
        # We'll only show these controls when the user has entered some player
        # names.
        print("<hr />")
        print("<a name=\"tourneyrules\">")
        print("<h2>Tourney rules</h2>");
        rank = tourney.get_rank_method();
        print(('<form action="%s?tourney=%s" method="post" />' % (baseurl, urllib.parse.quote_plus(tourneyname))));
        print(('<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname, True)));
        print("<h3>Ranking order</h3>");
        print("<p>How do you want to rank players in the standings table?</p>");
        print(('<input type="radio" name="rank" value="%d" %s /> Wins, then points. Draws are worth half a win. A win on a tiebreak is a win, not a draw.<br />' % (countdowntourney.RANK_WINS_POINTS, "checked" if rank == countdowntourney.RANK_WINS_POINTS else "")));
        print(('<input type="radio" name="rank" value="%d" %s /> Wins, then cumulative winning margin (spread). Draws are worth half a win.<br />' % (countdowntourney.RANK_WINS_SPREAD, "checked" if rank == countdowntourney.RANK_WINS_SPREAD else "")))
        print(('<input type="radio" name="rank" value="%d" %s /> Points only.' % (countdowntourney.RANK_POINTS, "checked" if rank == countdowntourney.RANK_POINTS else "")));
        print('</p>');

        print("<h3>Draws</h3>")
        print("<p>")
        print("""
        Tick this box if draws are possible in your tournament.
        Leaving it unticked won't stop you recording a drawn game - it only
        affects analysis of whether a player is guaranteed to finish in the
        qualification zone, and whether the draws column is shown in exported
        HTML or text results.
        The <a href=\"/cgi-bin/standings.py?tourney=%s\">standings page</a>
        will always show a draws column regardless.""" % (urllib.parse.quote_plus(tourney.get_name())))
        print("</p><p>")
        print(("<input type=\"checkbox\" name=\"showdrawscolumn\" value=\"1\" %s />" % ("checked" if tourney.get_show_draws_column() else "")))
        print("Expect that draws might happen")
        print("</p>")

        print("<h3>Intended number of rounds, and qualification</h3>")
        print("<p>")
        print("If you fill in these values, Atropine will automatically work out when a player is guaranteed to finish in the qualification zone, and highlight them in green the standings table.")
        print("If you don't fill these in, or if you set them to zero, Atropine won't do that.")
        print("</p>")

        for div_index in range(num_divisions):
            if num_divisions > 1:
                print("<h4>%s</h4>" % (cgi.escape(tourney.get_division_name(div_index))))
            div_prefix = "div%d_" % (div_index)
            
            last_round = str(tourney.get_attribute(div_prefix + "lastround", ""))
            if last_round == "0":
                last_round = ""

            num_games_per_player = str(tourney.get_attribute(div_prefix + "numgamesperplayer", ""))
            if num_games_per_player == "0":
                num_games_per_player = ""

            qual_places = str(tourney.get_attribute(div_prefix + "qualplaces", ""))
            if qual_places == "0":
                qual_places = ""

            print("<div class=\"tourneyqualifyingcontrols\">")
            print("The last round is expected to be round number <input class=\"tourneysetupnumber\" type=\"number\" name=\"%slastround\" value=\"%s\" />" % (div_prefix, cgi.escape(last_round, True)))
            print("</div>")
            print("<div class=\"tourneyqualifyingcontrols\">")
            print("Each player is expected to play <input class=\"tourneysetupnumber\" type=\"number\" name=\"%snumgamesperplayer\" value=\"%s\" /> games" % (div_prefix, cgi.escape(num_games_per_player, True)))
            print("</div>")
            print("<div class=\"tourneyqualifyingcontrols\">")
            print("The qualification zone is the top <input class=\"tourneysetupnumber\" type=\"number\" name=\"%squalplaces\" value=\"%s\" /> places in the standings table" % (div_prefix, cgi.escape(qual_places, True)))
            print("</div>")

        print('<p><input type="submit" name="rulessubmit" value="Save Rules" /></p>')
        print("</form>");

        if tourney.get_num_games() > 0:
            print("<hr />")
            print('<h2>Delete rounds</h2>')
            print('<p>Press this button to delete the most recent round. You\'ll be asked to confirm on the next screen.</p>')
            print("<p>")
            print('<form action="/cgi-bin/delround.py" method="get" />')
            print(('<input type="hidden" name="tourney" value="%s" />' % cgi.escape(tourneyname)))
            print('<input type="submit" name="delroundsetupsubmit" value="Delete most recent round" />')
            print('</form>')
            print("</p>")

print("</div>");

print("</body>");
print("</html>");
