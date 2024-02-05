#!/usr/bin/python3

import cgitb;
import cgicommon;
import sys;
import csv;
import os;
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

cgitb.enable();

cgicommon.set_module_path();
import countdowntourney;

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

baseurl = "/cgi-bin/tourneysetupadvanced.py";
form = cgicommon.FieldStorage();
tourneyname = form.getfirst("tourney");
show_tournament_rating = bool(int_or_none(form.getfirst("showtournamentratingcolumn")))
tr_bonus = float_or_none(form.getfirst("tournamentratingbonus"))
tr_diff_cap = float_or_none(form.getfirst("tournamentratingdiffcap"))
rank = int_or_none(form.getfirst("rank"))
rank_finals = int_or_none(form.getfirst("rankfinals"))
set_prune_name = form.getfirst("prunename")

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Advanced setup: " + str(tourneyname));

cgicommon.writeln("<body>");

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
cgicommon.writeln("<h1>Advanced Setup</h1>");

if tourneyname is None:
    cgicommon.writeln("<h1>Sloblock</h1>");
    cgicommon.writeln("<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>");
elif not tourney:
    cgicommon.writeln("<p>No valid tourney name specified</p>");
else:
    if request_method == "POST" and "submit" in form:
        try:
            tourney.set_show_tournament_rating_column(show_tournament_rating)
            tourney.set_tournament_rating_config(tr_bonus, tr_diff_cap)
            tourney.set_rank_method_id(rank)
            tourney.set_rank_finals(rank_finals)
            if tourney.has_auto_prune() and set_prune_name:
                existing_prune_name = tourney.get_auto_prune_name()
                if set_prune_name != existing_prune_name:
                    tourney.set_auto_prune_name(set_prune_name)
            cgicommon.show_success_box("Options updated.");
        except countdowntourney.TourneyException as e:
            cgicommon.show_tourney_exception(e);

    cgicommon.writeln(('<form action="%s?tourney=%s" method="POST">' % (baseurl, urllib.parse.quote_plus(tourneyname))));
    cgicommon.writeln(('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname, True)));

    cgicommon.writeln("<h2>Team Setup</h2>")
    cgicommon.writeln("""<p>Atropine can assign each player to one of
two teams. Every match between players on opposing teams gives a team point to
the winner's team. The team scores are displayed alongside the standings.</p>""")
    cgicommon.writeln("""<p>
<a href=\"/cgi-bin/teamsetup.py?tourney=%s\">Go to the Team Setup page</a>
</p>""" % (urllib.parse.quote_plus(tourneyname)))

    cgicommon.writeln("<h2>Standings table ranking order</h2>");
    rank_finals = tourney.get_rank_finals()
    cgicommon.writeln("<p>The standings table decides players' finishing positions in the tournament. It is also used by some fixture generators, such as the Swiss generator, to decide who plays whom in the next round.</p>");
    cgicommon.writeln("<p>In all cases, a draw counts as half a win. If a game is won on a tiebreak, it counts as a full win but the points from the tiebreak do not count towards the winner's points total.</p>")
    cgicommon.writeln("<p>How do you want to rank players in the standings table?</p>");
    cgicommon.writeln("<div class=\"generalsetupcontrolgroup\">")
    selected_rank_method_id = tourney.get_rank_method_id();
    rank_method_list = tourney.get_rank_method_list()
    for (rank_method_id, rank_method) in rank_method_list:
        cgicommon.writeln("<div class=\"rankmethod\">")
        cgicommon.writeln("<div>")
        cgicommon.writeln("<label for=\"rankbutton%d\">" % (rank_method_id))
        cgicommon.writeln('<input type="radio" name="rank" value="%d" id="rankbutton%d" %s/> <span style=\"font-weight: bold;\">%s</span>. %s' % (
            rank_method_id, rank_method_id,
            "checked" if rank_method_id == selected_rank_method_id else "",
            cgicommon.escape(rank_method.get_name()),
            cgicommon.escape(rank_method.get_description())
        ))
        cgicommon.writeln("</label>")
        cgicommon.writeln("</div>")
        cgicommon.writeln("<div class=\"rankmethoddetails\">")
        cgicommon.writeln(rank_method.get_extra_description())
        cgicommon.writeln("</div>")
        cgicommon.writeln("</div>")

    cgicommon.writeln("</div>")

    cgicommon.writeln("<p>Finals games do not affect the number of wins, points etc shown in the standings table, but they do affect the final placings. Enable the following checkbox to reflect that in the standings table order shown on the public display.</p>")
    cgicommon.writeln("<div class=\"generalsetupcontrolgroup\">")
    cgicommon.writeln("<input type=\"checkbox\" name=\"rankfinals\" value=\"1\" id=\"rankfinals\" %s />" % ("checked" if rank_finals else ""))
    cgicommon.writeln("<label for=\"rankfinals\">Display standings order modified according to results of finals, if played</label>")
    cgicommon.writeln("</div>")
    cgicommon.writeln('<p><input type="submit" name="submit" value="Save Changes" class="bigbutton" /></p>')

    if tourney.has_auto_prune():
        prune_name = tourney.get_auto_prune_name()
        cgicommon.writeln("<h2>Automatic Prune</h2>")
        cgicommon.writeln("""<p>
Fixture generators will automatically add a virtual Prune player where
required if the number of players isn't a multiple of the group size.
It is no longer necessary for you to add a Prune player yourself for
this purpose. This virtual player can appear in a fixture but does not
appear in the standings table or in any player lists.</p>
<p>You can give this automatic prune a custom name, which will appear in
results and fixture lists. This name must not be blank or the same as any
player's name.</p>""")
        cgicommon.writeln("<div class=\"generalsetupcontrolgroup\">")
        cgicommon.writeln('<label for="prunename">Automatic Prune name: <input type="text" name="prunename" id="prunename" value="%s" /></label>' % (cgicommon.escape(prune_name, True)))
        cgicommon.writeln("</div>")
        cgicommon.writeln('<p><input type="submit" name="submit" value="Save Changes" class="bigbutton" /></p>')

    cgicommon.writeln("<h2>Tournament Ratings</h2>")
    cgicommon.writeln("<p>If you don't know what tournament ratings are, you can safely leave these as the defaults and they won't affect anything.</p>")
    cgicommon.writeln("<div class=\"generalsetupcontrolgroup\">")
    cgicommon.writeln(("<input type=\"checkbox\" name=\"showtournamentratingcolumn\" id=\"showtournamentratingcolumn\" value=\"1\" %s />" % ("checked" if tourney.get_show_tournament_rating_column() else "")))
    cgicommon.writeln("<label for=\"showtournamentratingcolumn\">Show tournament ratings in exported results standings table</label>")
    cgicommon.writeln("</div>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("For each game you play, your tournament rating is calculated as follows.")
    cgicommon.writeln("</p>")
    cgicommon.writeln("<ul>")
    cgicommon.writeln("<li>If you win, your opponent's <em>effective rating</em> plus the <em>win value</em>.</li>")
    cgicommon.writeln("<li>If you draw, your opponent's <em>effective rating</em>.</li>")
    cgicommon.writeln("<li>If you lose, your opponent's <em>effective rating</em> minus the <em>win value</em>.</li>")
    cgicommon.writeln("</ul>")
    cgicommon.writeln("<div class=\"generalsetupcontrolgroup\">")
    cgicommon.writeln(("The <em>win value</em> is <input type=\"number\" name=\"tournamentratingbonus\" value=\"%g\" style=\"width: 5em;\" />" % (tourney.get_tournament_rating_bonus_value())))
    cgicommon.writeln("</div><div class=\"generalsetupcontrolgroup\">")
    cgicommon.writeln("Your opponent's <em>effective rating</em> for a game is their rating at the start of the tournament, capped to within")
    cgicommon.writeln(("<input type=\"number\" name=\"tournamentratingdiffcap\" value=\"%g\" style=\"width: 5em;\" />" % (tourney.get_tournament_rating_diff_cap())))
    cgicommon.writeln("of your own.")
    cgicommon.writeln("</div>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("Your overall tournament rating is the mean average from all your games.")
    cgicommon.writeln("</p>")
    cgicommon.writeln('<p><input type="submit" name="submit" value="Save Changes" class="bigbutton" /></p>')
    cgicommon.writeln("</form>");

    cgicommon.writeln("<h1>Raw database access</h1>")
    cgicommon.writeln("<p>This gives you direct SQL access to the tourney database. You shouldn't normally need to use this feature. If you don't know what you're doing, you can mess up your entire tournament. Don't say you weren't warned!</p>")
    cgicommon.writeln("<p><a href=\"/cgi-bin/sql.py?tourney=%s\">I understand. Take me to the raw database access page, and on my own head be it.</a></p>" % (urllib.parse.quote_plus(tourneyname)))

cgicommon.writeln("</div>");

cgicommon.writeln("</body>");
cgicommon.writeln("</html>");
