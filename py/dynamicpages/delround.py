#!/usr/bin/python3

import htmlcommon
import countdowntourney

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    round_no = int_or_none(form.getfirst("round"))
    confirm = int_or_none(form.getfirst("confirm"))
    tourneyname = tourney.name

    htmlcommon.print_html_head(response, "Delete round: " + str(tourneyname))

    response.writeln("<body>");

    if confirm:
        try:
            tourney.delete_round(round_no)
            htmlcommon.show_sidebar(response, tourney);
            response.writeln("<div class=\"mainpane\">");
            response.writeln("<h1>Delete round</h1>");
            htmlcommon.show_success_box(response, "Round %d deleted successfully." % (round_no))
            response.writeln('<p><a href="/atropine/%s/tourneysetup">Back to tourney setup</a></p>' % (htmlcommon.escape(tourneyname)))
        except countdowntourney.TourneyException as e:
            htmlcommon.show_sidebar(response, tourney);
            response.writeln("<div class=\"mainpane\">");
            response.writeln("<h1>Delete round</h1>");
            htmlcommon.show_tourney_exception(response, e)
    else:
        htmlcommon.show_sidebar(response, tourney);
        response.writeln("<div class=\"mainpane\">");
        response.writeln("<h1>Delete round</h1>");
        latest_round_no = tourney.get_latest_round_no()
        if latest_round_no is None:
            response.writeln('<p>There are no rounds to delete!</p>')
            response.writeln('<p><a href="/atropine/%s/tourneysetup">Back to tourney setup</a></p>' % (htmlcommon.escape(tourneyname)))
        else:
            round_name = tourney.get_round_name(latest_round_no)
            response.writeln('<p>The most recent round is shown below.</p>')
            htmlcommon.show_warning_box(response, "You are about to delete this round and all the fixtures in it. <strong>This cannot be undone.</strong> Are you sure you want to delete it?")
            response.writeln('<form method="post">')
            response.writeln('<input type="hidden" name="tourney" value="%s" />' % htmlcommon.escape(tourneyname))
            response.writeln('<input type="hidden" name="round" value="%d" />' % latest_round_no)
            response.writeln('<input type="hidden" name="confirm" value="1" />')
            response.writeln('<p>')
            response.writeln('<input type="submit" class="bigbutton destroybutton" name="delroundsubmit" value="Yes, I\'m sure. Delete the round and all its games." />')
            response.writeln('</p>')
            response.writeln('</form>')
            response.writeln('<form action="/atropine/%s/tourneysetup" method="post">')
            response.writeln('<input type="hidden" name="tourney" value="%s" />' % htmlcommon.escape(tourneyname))
            response.writeln('<input type="submit" class="bigbutton chickenoutbutton" name="arrghgetmeoutofhere" value="No. Cancel this and take me back to the tourney setup page." />')
            response.writeln('</form>')

            num_divisions = tourney.get_num_divisions()
            response.writeln("<h2>%s</h2>" % (round_name))
            for div_index in range(num_divisions):
                response.writeln("<h3>%s</h3>" % htmlcommon.escape(tourney.get_division_name(div_index)))
                games = tourney.get_games(round_no=latest_round_no, division=div_index)
                htmlcommon.show_games_as_html_table(response, games, False, None, False, None, lambda x : htmlcommon.player_to_link(x, tourneyname))

    response.writeln("</div>")

    response.writeln("</body>")
    response.writeln("</html>")
