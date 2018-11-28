#!/usr/bin/python3

import cgi;
import cgitb;
import cgicommon;
import sys;
import csv;
import os;
import json
import io
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
    cgicommon.writeln("<select name=\"%s\">" % (control_name))
    cgicommon.writeln("<option value=\"\">-- select player --</option>")
    for p in players:
        cgicommon.writeln("<option value=\"%s\">%s (%g)</option>" % (cgicommon.escape(p.name, True), cgicommon.escape(p.name), p.rating));
    cgicommon.writeln("</select>")

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

player_list_rating_help = "To give a player a rating, put a comma after the player's name and put the rating number after that, e.g. <span class=\"fixedwidth\">Harry Peters,1860</span>"

cgitb.enable();

cgicommon.set_module_path();
import countdowntourney;

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

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
accessible_tables_default = int_or_none(form.getfirst("accessibletablesdefault"))
accessible_tables_string = form.getfirst("accessibletables")
if not accessible_tables_string:
    accessible_tables_string = ""
rules_submit = form.getfirst("rulessubmit");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Tourney Setup: " + str(tourneyname));

cgicommon.writeln("<body>");

cgicommon.writeln("<script>")
cgicommon.writeln("""
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
    cgicommon.writeln("""
        case %d:
            element.innerText = %s;
            break;
    """ % (num, json.dumps(text)))

cgicommon.writeln("""
    }
}
</script>
""")

cgicommon.assert_client_from_localhost()

if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);
        cgicommon.writeln("<p><a href=\"/cgi-bin/home.py\">Home</a></p>")
        cgicommon.writeln("</body></html>")
        sys.exit(1)

cgicommon.show_sidebar(tourney);

cgicommon.writeln("<div class=\"mainpane\">");
cgicommon.writeln("<h1>Tourney Setup</h1>");

if tourneyname is None:
    cgicommon.writeln("<h1>Sloblock</h1>");
    cgicommon.writeln("<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>");
elif not tourney:
    cgicommon.writeln("<p>No valid tourney name specified</p>");
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
            cgicommon.writeln("<p><strong>Player list updated successfully.</strong></p>");
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);

    num_divisions = tourney.get_num_divisions()

    if request_method == "POST" and rules_submit:
        try:
            # User submitted new tourney rules, so set them

            # Accessible tables
            try:
                if not accessible_tables_string:
                    accessible_tables = []
                else:
                    accessible_tables = [ int(x) for x in accessible_tables_string.split(",") ]
                    for x in accessible_tables:
                        if x <= 0:
                            raise countdowntourney.TourneyException("Accessible table list, if set, must be a comma-separated list of positive integers.")
                tourney.set_accessible_tables(accessible_tables, accessible_tables_default != 0)
            except ValueError:
                raise countdowntourney.TourneyException("Accessible table list, if set, must be a comma-separated list of positive integers.")

            # Rank method
            tourney.set_rank_method(rank);
            
            # Whether draws are a thing
            tourney.set_show_draws_column(show_draws_column);

            # Qualification analysis
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
            cgicommon.writeln("<p><strong>Rules updated successfully.</strong></p>");
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);

    players = tourney.get_players();
    players = sorted(players, key=lambda x : x.name);

    cgicommon.writeln("<p>")
    if tourney.get_num_games() > 0:
        cgicommon.writeln("The tournament has started.")
    if len(players) == 0:
        cgicommon.writeln("There are no players in the tourney yet.")
    else:
        cgicommon.writeln("There are <a href=\"player.py?tourney=%s\">%d players</a>," % (urllib.parse.quote_plus(tourney.get_name()), len(players)))
        num_active = len([x for x in players if not x.is_withdrawn()])
        if num_active != len(players):
            cgicommon.writeln("of whom %d %s active and %d %s withdrawn." % (num_active, "is" if num_active == 1 else "are", len(players) - num_active, "has" if len(players) - num_active == 1 else "have"))
        else:
            cgicommon.writeln("none withdrawn.")
    cgicommon.writeln("</p>")

    if tourney.get_num_games() == 0:
        if players:
            cgicommon.show_info_box("""<p>
When you're happy with the player list and the tourney rules below, head to
<a href="/cgi-bin/fixturegen.py?tourney=%s">Generate fixtures</a> to generate
the first games. Once you've generated the first games, you won't be able to
delete players, but you can always withdraw them, edit names and ratings, or
add new players.</p>""" % (urllib.parse.quote_plus(tourney.get_name())))
        else:
            cgicommon.show_info_box("<p>This tourney has no players defined yet. Before doing anything else, enter the list of player names below. You can always add more players, or withdraw them, later on if necessary.</p>");


    if num_divisions > 1:
        cgicommon.writeln("<p>The players are distributed into <a href=\"divsetup.py?tourney=%s\">%d divisions</a>.</p>" % (urllib.parse.quote_plus(tourney.get_name()), num_divisions))
        cgicommon.writeln("<blockquote>")
        for div_index in range(num_divisions):
            cgicommon.writeln("<li>%s: %d active players.</li>" % (tourney.get_division_name(div_index), tourney.get_num_active_players(div_index)))
        cgicommon.writeln("</blockquote>")

    if tourney.get_num_games() == 0:
        players = sorted(tourney.get_players(), key=lambda x : (x.get_division(), x.get_id()))
        cgicommon.writeln("<hr />")
        cgicommon.writeln("<h2>Player list setup</h2>");

        cgicommon.writeln(("<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.parse.quote_plus(tourneyname))))

        cgicommon.writeln("<p>")
        cgicommon.writeln("How do you want to assign ratings to players? Ratings are used by the Overachievers table and some fixture generators. If you don't know what ratings are, or you don't care, select \"This tournament is not seeded\".")
        cgicommon.writeln("</p>")
        cgicommon.writeln("<blockquote>")
        auto_rating_behaviour = tourney.get_auto_rating_behaviour()
        cgicommon.writeln(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" %s />" % (countdowntourney.RATINGS_MANUAL, countdowntourney.RATINGS_MANUAL, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_MANUAL else "")))
        cgicommon.writeln("<strong>Ratings are specified manually in the player list.</strong> If you select this option, it is an error if you try to submit a player without a rating.")
        cgicommon.writeln("<br />")
        cgicommon.writeln(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" %s />" % (countdowntourney.RATINGS_GRADUATED, countdowntourney.RATINGS_GRADUATED, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_GRADUATED else "")))
        cgicommon.writeln("<strong>The player list is in rating order with the highest-rated player at the top</strong>. Ratings will be assigned automatically, with the player at the top of the list receiving a rating of 2000, and the player at the bottom 1000. If you select this option, it is an error to specify any ratings manually in the player list except a rating of zero to indicate a prune.")
        cgicommon.writeln("<br />")
        cgicommon.writeln(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" %s />" % (countdowntourney.RATINGS_UNIFORM, countdowntourney.RATINGS_UNIFORM, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_UNIFORM else "")))
        cgicommon.writeln("<strong>This tournament is not seeded.</strong> Assign every non-prune player a rating of 1000. If you select this option, it is an error to specify any ratings manually in the player list except a rating of zero to indicate a prune. If unsure, select this option.")
        cgicommon.writeln("</blockquote>")

        cgicommon.writeln("<p>")
        cgicommon.writeln("A player's rating may still be changed after the tournament has started.")
        cgicommon.writeln("</p>")

        cgicommon.writeln("<h2>Player list</h2>");
        cgicommon.writeln("<p>")
        cgicommon.writeln("Enter player names in this box, one player per line, then click <em>Save Player List</em>.")
        cgicommon.writeln("</p>")

        cgicommon.writeln("<div class=\"playerlist\">")
        cgicommon.writeln("<div class=\"playerlistpane\">")
        cgicommon.writeln("<p>")
        cgicommon.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname));
        cgicommon.writeln('<textarea rows="28" cols="40" name="playerlist">');
        if request_method == "POST" and playerlist:
            # If the user has submitted something, display what the user
            # submitted rather than what's in the database - this gives them
            # a chance to correct any errors without typing in the whole
            # change again.
            cgicommon.write(cgicommon.escape(playerlist).strip())
        else:
            string_stream = io.StringIO()
            auto_rating = tourney.get_auto_rating_behaviour()
            writer = csv.writer(string_stream);
            prev_div_index = 0
            # Write player names, or player names and ratings if the user
            # specified the players' ratings.
            for p in players:
                (name, rating, div_index) = p;
                if div_index != prev_div_index:
                    writer.writerow(("-",))
                if auto_rating != countdowntourney.RATINGS_MANUAL and rating != 0:
                    writer.writerow((cgicommon.escape(name),));
                else:
                    writer.writerow((cgicommon.escape(name), "%g" % (rating)));
                prev_div_index = div_index
            cgicommon.write(string_stream.getvalue())
        cgicommon.writeln("</textarea>");
        cgicommon.writeln("</p>")

        cgicommon.writeln("<p>")
        cgicommon.writeln('<input type="submit" name="playerlistsubmit" value="Save Player List" />')
        cgicommon.writeln("</p>")

        cgicommon.writeln("</div>")

        cgicommon.writeln("<div class=\"playerlisthelp\">")
        cgicommon.writeln("<h3>Example</h3>")
        cgicommon.writeln("<pre id=\"playerlistexamplepre\">")
        if auto_rating_behaviour == countdowntourney.RATINGS_UNIFORM:
            cgicommon.writeln(player_list_example_uniform)
        elif auto_rating_behaviour == countdowntourney.RATINGS_GRADUATED:
            cgicommon.writeln(player_list_example_graduated)
        else:
            cgicommon.writeln(player_list_example_manual)
        cgicommon.writeln("</pre>")
        cgicommon.writeln("<p id=\"playerlistratinghelp\">")
        if auto_rating_behaviour == countdowntourney.RATINGS_MANUAL:
            cgicommon.writeln(player_list_rating_help);
        cgicommon.writeln("</p>")

        cgicommon.writeln("<p>")
        cgicommon.writeln("To indicate that a player is a prune or bye, which affects how the fixture generators assign fixtures, give them a rating of zero: <span class=\"fixedwidth\">Apterous Prune,0</span>")
        cgicommon.writeln("</p>")

        cgicommon.writeln("<p>")
        cgicommon.writeln("To divide the players into divisions, put a line containing only a dash (<span class=\"fixedwidth\">-</span>) between the desired divisions.")
        cgicommon.writeln("</p>")
        cgicommon.writeln("</div>")
        cgicommon.writeln("</div>")
        cgicommon.writeln("</form>")
        cgicommon.writeln("<div class=\"playerlistclear\"></div>")

    if tourney.get_players():
        # We'll only show these controls when the user has entered some player
        # names.
        cgicommon.writeln("<hr />")
        cgicommon.writeln("<h2>Tourney rules</h2>");
        rank = tourney.get_rank_method();
        cgicommon.writeln(('<form action="%s?tourney=%s" method="post">' % (baseurl, urllib.parse.quote_plus(tourneyname))));
        cgicommon.writeln(('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname, True)));
        cgicommon.writeln("<h3>Ranking order</h3>");
        cgicommon.writeln("<p>How do you want to rank players in the standings table?</p>");
        cgicommon.writeln(('<input type="radio" name="rank" value="%d" %s /> Wins, then points. Draws are worth half a win. A win on a tiebreak is a win, not a draw.<br />' % (countdowntourney.RANK_WINS_POINTS, "checked" if rank == countdowntourney.RANK_WINS_POINTS else "")));
        cgicommon.writeln(('<input type="radio" name="rank" value="%d" %s /> Wins, then cumulative winning margin (spread). Draws are worth half a win.<br />' % (countdowntourney.RANK_WINS_SPREAD, "checked" if rank == countdowntourney.RANK_WINS_SPREAD else "")))
        cgicommon.writeln(('<input type="radio" name="rank" value="%d" %s /> Points only.' % (countdowntourney.RANK_POINTS, "checked" if rank == countdowntourney.RANK_POINTS else "")));

        (table_list, accessible_default) = tourney.get_accessible_tables()
        cgicommon.writeln("<h3>Accessibility</h3>")
        cgicommon.writeln("<p>If a player requires an accessible table, you can set this on the <a href=\"/cgi-bin/player.py?tourney=%s\">configuration page for that player</a>." % (urllib.parse.quote_plus(tourney.get_name())))
        cgicommon.writeln("<p>")
        cgicommon.writeln("<input type=\"radio\" name=\"accessibletablesdefault\" value=\"0\" %s /> The following table numbers are the accessible tables." % ("" if accessible_default else "checked"))
        cgicommon.writeln("<br />")
        cgicommon.writeln("<input type=\"radio\" name=\"accessibletablesdefault\" value=\"1\" %s /> All tables are accessible <em>except</em> for the following table numbers." % ("checked" if accessible_default else ""))
        cgicommon.writeln("</p>")
        cgicommon.writeln("<p style=\"margin-left: 30px\">")
        cgicommon.writeln("<input type=\"text\" name=\"accessibletables\" value=\"%s\" />" % (", ".join([ str(x) for x in table_list ])))
        cgicommon.writeln(" <span style=\"color: #808080; font-size: 10pt\">(Enter table numbers separated by commas, e.g. <em>1, 2, 5</em>)</span>")
        cgicommon.writeln("</p>")


        cgicommon.writeln("<h3>Draws</h3>")
        cgicommon.writeln("<p>")
        cgicommon.writeln("""
        Tick this box if draws are possible in your tournament.
        Leaving it unticked won't stop you recording a drawn game - it only
        affects analysis of whether a player is guaranteed to finish in the
        qualification zone, and whether the draws column is shown in exported
        HTML or text results.
        The <a href=\"/cgi-bin/standings.py?tourney=%s\">standings page</a>
        will always show a draws column regardless.""" % (urllib.parse.quote_plus(tourney.get_name())))
        cgicommon.writeln("</p><p>")
        cgicommon.writeln(("<input type=\"checkbox\" name=\"showdrawscolumn\" value=\"1\" %s />" % ("checked" if tourney.get_show_draws_column() else "")))
        cgicommon.writeln("Expect that draws might happen")
        cgicommon.writeln("</p>")

        cgicommon.writeln("<h3>Intended number of rounds, and qualification</h3>")
        cgicommon.writeln("<p>")
        cgicommon.writeln("If you fill in these values, Atropine will automatically work out when a player is guaranteed to finish in the qualification zone, and highlight them in green in the standings table.")
        cgicommon.writeln("If you don't fill these in, or if you set them to zero, Atropine won't do that.")
        cgicommon.writeln("</p>")

        for div_index in range(num_divisions):
            if num_divisions > 1:
                cgicommon.writeln("<h4>%s</h4>" % (cgicommon.escape(tourney.get_division_name(div_index))))
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

            cgicommon.writeln("<div class=\"tourneyqualifyingcontrols\">")
            cgicommon.writeln("The last round is expected to be round number <input class=\"tourneysetupnumber\" type=\"number\" name=\"%slastround\" value=\"%s\" />" % (div_prefix, cgicommon.escape(last_round, True)))
            cgicommon.writeln("</div>")
            cgicommon.writeln("<div class=\"tourneyqualifyingcontrols\">")
            cgicommon.writeln("Each player is expected to play <input class=\"tourneysetupnumber\" type=\"number\" name=\"%snumgamesperplayer\" value=\"%s\" /> games" % (div_prefix, cgicommon.escape(num_games_per_player, True)))
            cgicommon.writeln("</div>")
            cgicommon.writeln("<div class=\"tourneyqualifyingcontrols\">")
            cgicommon.writeln("The qualification zone is the top <input class=\"tourneysetupnumber\" type=\"number\" name=\"%squalplaces\" value=\"%s\" /> places in the standings table" % (div_prefix, cgicommon.escape(qual_places, True)))
            cgicommon.writeln("</div>")

        cgicommon.writeln('<p><input type="submit" name="rulessubmit" value="Save Rules" /></p>')
        cgicommon.writeln("</form>");

        if tourney.get_num_games() > 0:
            cgicommon.writeln("<hr />")
            cgicommon.writeln('<h2>Delete rounds</h2>')
            cgicommon.writeln('<p>Press this button to delete the most recent round. You\'ll be asked to confirm on the next screen.</p>')
            cgicommon.writeln('<form action="/cgi-bin/delround.py" method="get">')
            cgicommon.writeln(('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname)))
            cgicommon.writeln('<input type="submit" name="delroundsetupsubmit" value="Delete most recent round" />')
            cgicommon.writeln('</form>')

cgicommon.writeln("</div>");

cgicommon.writeln("</body>");
cgicommon.writeln("</html>");
