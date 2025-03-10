#!/usr/bin/python3

import datetime
import calendar
import csv
from io import StringIO

import countdowntourney
import htmlcommon

def int_or_none(s):
    try:
        i = int(s)
        return i
    except:
        return None

def valid_date(d, m, y):
    try:
        datetime.datetime.strptime("%04d-%02d-%02d" % (y, m, d), "%Y-%m-%d")
        return True
    except ValueError:
        return False

def show_error(response, err_str, non_local_client):
    htmlcommon.print_html_head(response, "Export results: %s" % tourney_name);

    response.writeln("<body>");

    htmlcommon.show_sidebar(response, tourney, non_local_client=non_local_client)

    response.writeln("<div class=\"mainpane\">")
    response.writeln("<p><strong>%s</strong></p>" % err_str)
    response.writeln("</div>")
    response.writeln("</body>")
    response.writeln("</html>")

form_letter_to_word = {
    "W" : "won",
    "D" : "drew",
    "L" : "lost"
}

def get_date_string(tourney):
    (date_year, date_month, date_day) = tourney.get_event_date()
    if date_year and date_month and date_day:
        date_string = "%d %s %04d" % (date_day, "Octember" if date_month < 1 or date_month > 12 else calendar.month_name[date_month], date_year)
    else:
        date_string = None
    return date_string

def get_top_placings(tourney, div_index, show_standings_after_finals):
    standings = tourney.get_standings(division=div_index, rank_finals=show_standings_after_finals)

    # Was there a final?
    finals = tourney.get_games(game_type="F", division=div_index, only_complete=True)
    semi_finals = tourney.get_games(game_type="SF", division=div_index, only_complete=True)
    third_place = tourney.get_games(game_type="3P", division=div_index, only_complete=True)

    excuse = None
    top_placings = []
    if len(finals) == 1 and finals[0].is_complete():
        # The winner of the final is in 1st place, and the loser of the
        # final is in 2nd place. If the final is drawn, then I guess the
        # two players are both in 1st place?
        final = finals[0]
        final_players = final.get_players()
        if not final.is_draw():
            winner = final.get_winner()
            loser = final.get_loser()
            top_placings.append((1, winner.get_name(), "Won final %s against %s" % (final.format_score(force_winner_first=True), loser.get_name())))
            top_placings.append((2, loser.get_name(), "Lost final"))
        else:
            top_placings.append((1, final_players[0].get_name(), "Drew final %s against %s" % (final.format_score(), final_players[1].get_name())))
            top_placings.append((1, final_players[1].get_name(), "Drew final"))
        if not semi_finals:
            # If there are no semi-finals, 3rd place is just whoever is
            # third in the standings. Add to the podium anyone who is 3rd or
            # higher and didn't play in the final.
            if len(standings) >= 3:
                i = 0
                while i < len(standings) and standings[i].position <= 3:
                    if standings[i].name != final_players[0].get_name() and standings[i].name != final_players[1].get_name():
                        top_placings.append((standings[i].position, standings[i].name, ""))
                    i += 1
        elif len(third_place) == 1 and third_place[0].is_complete():
            # If there are semi-finals but there's also a third-place
            # play-off, the person in third is the winner of that.
            if third_place[0].is_draw():
                # Both in third place
                ps = third_place[0].get_players()
                for p in ps:
                    top_placings.append((3, p.get_name(), "Drew third-place playoff %s" % (third_place[0].format_score(force_winner_first=True))))
            else:
                winner = third_place[0].get_winner()
                loser = third_place[0].get_loser()
                top_placings.append((3, winner.get_name(), "Won third-place playoff %s against %s" % (third_place[0].format_score(force_winner_first=True), loser.get_name())))
        # Otherwise there is no easily-agreed third place
    else:
        if len(finals) > 1:
            # Huh?
            excuse = "More than one final (game type F) played: can't calculate winners."
        else:
            # No final: 1st, 2nd and 3rd are looked up from the standings
            i = 0
            while i < len(standings) and standings[i].position <= 3:
                top_placings.append((standings[i].position, standings[i].name, ""))
                i += 1
    return (top_placings, excuse)

def export_html(tourney, response, filename, show_standings_before_finals, show_standings_after_finals, finals_noun):
    full_name = tourney.get_full_name() or tourney.get_name()
    venue = tourney.get_venue()
    date_string = get_date_string(tourney)
    rank_method = tourney.get_rank_method()
    show_draws_column = tourney.get_show_draws_column()

    if filename:
        response.add_header("Content-Disposition", "attachment; filename=\"%s.html\"" % (filename))

    started_html = True;

    htmlcommon.print_html_head_local(response, full_name);

    response.writeln("<body>");
    response.writeln("<div class=\"exportedstandings\">")
    response.writeln("<h1>%s</h1>" % (htmlcommon.escape(full_name)))
    if venue:
        response.writeln("<p>%s</p>" % (htmlcommon.escape(venue)))
    if date_string:
        response.writeln("<p>%s</p>" % (htmlcommon.escape(date_string)))

    response.writeln("<h2>Podium</h2>")
    num_divisions = tourney.get_num_divisions()
    for div_index in range(num_divisions):
        if num_divisions > 1:
            response.writeln("<h3>%s</h3>" % (tourney.get_division_name(div_index)))
        (top_placings, excuse) = get_top_placings(tourney, div_index, show_standings_after_finals)
        if excuse:
            response.writeln("<p>%s</p>" % (excuse))
        else:
            response.writeln("<table class=\"ranktable\">")
            num_non_empty_remarks = len([ p[2] for p in top_placings if p[2] ])
            for (position, name, remark) in top_placings:
                response.writeln("<tr>")
                response.writeln("<td>%s place</td><td>%s</td>" % (
                    htmlcommon.ordinal_number(position),
                    htmlcommon.escape(name),
                ))
                if num_non_empty_remarks > 0:
                    response.writeln("<td>%s</td>" % (
                        htmlcommon.escape(remark)
                    ))
                response.writeln("</tr>")
            response.writeln("</table>")

    response.writeln("<h2>Standings</h2>")
    num_divisions = tourney.get_num_divisions()
    response.writeln("<p>")
    response.writeln(htmlcommon.escape(rank_method.get_short_description()))
    if show_draws_column:
        response.writeln("Draws count as half a win.")
    response.writeln("</p>")

    if show_standings_before_finals:
        if show_standings_before_finals and show_standings_after_finals:
            response.writeln("<h3>Before %s</h3>" % (finals_noun))
        htmlcommon.show_standings_table(response, tourney, show_draws_column,
                tourney.is_ranked_by_points(), tourney.is_ranked_by_spread(),
                show_first_second_column=False, linkify_players=False,
                show_tournament_rating_column=None, show_qualified=True,
                which_division=None, show_finals_column=False,
                rank_finals=False)
    if show_standings_after_finals:
        if show_standings_before_finals and show_standings_after_finals:
            response.writeln("<h3>After %s</h3>" % (finals_noun))
        htmlcommon.show_standings_table(response, tourney, show_draws_column,
                tourney.is_ranked_by_points(), tourney.is_ranked_by_spread(),
                show_first_second_column=False, linkify_players=False,
                show_tournament_rating_column=None, show_qualified=True,
                which_division=None, show_finals_column=True,
                rank_finals=True)

    response.writeln("</div>")

    response.writeln("<div class=\"exportedresults\">")
    response.writeln("<h2>Results</h2>")
    prev_round_no = None
    prev_table_no = None
    prev_division = None
    show_table_numbers = None
    game_seq = 0
    games = tourney.get_games()
    for g in games:
        if prev_round_no is None or prev_round_no != g.round_no:
            if prev_round_no is not None:
                response.writeln("</table>")
                response.writeln("<br />")
            response.writeln("<h3>%s</h3>" % (htmlcommon.escape(tourney.get_round_name(g.round_no))))
            response.writeln("<table class=\"scorestable\">")
            prev_table_no = None
            prev_division = None
        if prev_division is None or prev_division != g.division:
            if num_divisions > 1:
                response.writeln("<tr class=\"divisionrow\"><th colspan=\"3\">%s</th></tr>" % (htmlcommon.escape(tourney.get_division_name(g.division))))

            # If this division has a table with more than one game on it
            # then show the table numbers, otherwise don't bother.
            prev_table_no = g.table_no
            show_table_numbers = False
            i = 1
            while game_seq + i < len(games) and games[game_seq + i].round_no == g.round_no and games[game_seq + i].division == g.division:
                if games[game_seq + i].table_no == prev_table_no:
                    show_table_numbers = True
                    break
                prev_table_no = games[game_seq + i].table_no
                i += 1
            prev_table_no = None
        if prev_table_no is None or prev_table_no != g.table_no:
            if show_table_numbers:
                response.writeln("<tr class=\"tablenumberrow\"><th colspan=\"3\">Table %d</th></tr>" % g.table_no)
        response.writeln("<tr class=\"gamerow\">")
        names = g.get_player_names();
        response.writeln("<td class=\"gameplayer1\">%s</td>" % names[0]);
        if g.s1 is None or g.s2 is None:
            response.writeln("<td class=\"gamescore\"> v </td>")
        else:
            response.writeln("<td class=\"gamescore\">%s</td>" % htmlcommon.escape(g.format_score()));
        response.writeln("<td class=\"gameplayer2\">%s</td>" % names[1]);
        response.writeln("</tr>")
        prev_table_no = g.table_no
        prev_round_no = g.round_no
        prev_division = g.division
        game_seq += 1
    if prev_round_no is not None:
        response.writeln("</table>")
    response.writeln("</div>")
    response.writeln("</body></html>");

def export_text_standings(tourney, response, max_name_len, rank_finals,
        rank_method, show_draws_column, show_points_column,
        show_tournament_rating_column):
    num_divisions = tourney.get_num_divisions()

    div_standings = {}
    for div_index in range(num_divisions):
        div_standings[div_index] = tourney.get_standings(div_index,
                exclude_withdrawn_with_no_games=True,
                calculate_qualification=False,
                rank_finals=rank_finals
        )

    for div_index in range(num_divisions):
        standings = div_standings[div_index]
        if num_divisions > 1:
            response.writeln(tourney.get_division_name(div_index))

        # Show the position, then the name, then games played, then the
        # number of wins, then the number of draws if applicable, then any
        # secondary ranking columns, then points if they weren't in the
        # secondary ranking columns, then tournament rating if applicable.
        header_line = ("%%%ds" % (max_name_len + 6)) % ("")
        header_line += "    P   W"
        row_format = "%(pos)5d %(name)-" + str(max_name_len) + "s  %(played)3d %(wins)3d"
        if show_draws_column:
            header_line += "   D"
            row_format += " %(draws)3d"
        shown_points = False
        sec_index = 0
        sec_rank_headings = rank_method.get_secondary_rank_headings(short=True)
        for sec_index in range(len(sec_rank_headings)):
            heading = sec_rank_headings[sec_index]
            width = max(4, len(heading))
            header_line += (" %" + str(width) + "s") % (heading)
            row_format += " %(secondary" + str(sec_index) + ")" + str(width) + "s"
            if heading == "Pts":
                shown_points = True
        if show_points_column and not shown_points:
            header_line += "  Pts"
            row_format += " %(points)4d"
        if show_tournament_rating_column:
            header_line += "      TR"
            row_format += " %(tr)7s"

        response.writeln(header_line)
        for s in standings:
            fields = {
                    "pos" : s.position,
                    "name" : s.name,
                    "played" : s.played,
                    "wins" : s.wins,
                    "draws" : s.draws,
                    "points" : s.points,
                    "tr" : ("" if s.tournament_rating is None else "%7.2f" % (s.tournament_rating))
            }
            secondary_rank_value_strings = s.get_secondary_rank_value_strings()
            for i in range(len(secondary_rank_value_strings)):
                fields["secondary" + str(i)] = secondary_rank_value_strings[i]
            response.write(row_format % fields)

            if rank_finals:
                # If this player has played in any QF, SF, final or third place
                # playoff, insert a parenthetical explanatory note as to why
                # their position in the table might not match their wins/points
                # total.
                finals_form = s.finals_form
                # Remove any leading dashes from finals form
                while finals_form and finals_form[0] == '-':
                    finals_form = finals_form[1:]
                if finals_form:
                    if len(finals_form) == 1 and s[0] <= 4:
                        match_type = ("final" if s[0] <= 2 else "third place")
                        response.write(" (%s %s)" % (form_letter_to_word.get(finals_form), match_type))
                    else:
                        # Not just a single finals match, so display
                        # something like "(finals: WWL)".
                        response.write(" (finals: " + finals_form + ")")
            response.writeln("")
        response.writeln("")
        response.writeln("")

def export_text(tourney, response, filename, show_standings_before_finals, show_standings_after_finals, finals_noun):
    full_name = tourney.get_full_name() or tourney.get_name()
    venue = tourney.get_venue()
    date_string = get_date_string(tourney)
    rank_method = tourney.get_rank_method()
    show_draws_column = tourney.get_show_draws_column()
    show_points_column = tourney.is_ranked_by_points()
    show_tournament_rating_column = tourney.get_show_tournament_rating_column()
    num_divisions = tourney.get_num_divisions()

    max_name_len = 0
    for p in tourney.get_players():
        if max_name_len < len(p.get_name()):
            max_name_len = len(p.get_name())

    response.set_content_type("text/plain; charset=utf-8")
    if filename:
        response.add_header("Content-Disposition", "attachment; filename=\"%s.txt\""% (filename))

    response.writeln(full_name)
    if venue:
        response.writeln(venue)
    if date_string:
        response.writeln(date_string)

    response.writeln("")
    response.writeln("PODIUM")
    response.writeln("")
    num_divisions = tourney.get_num_divisions()
    for div_index in range(num_divisions):
        if num_divisions > 1:
            response.writeln("%s" % (tourney.get_division_name(div_index)))
        (top_placings, excuse) = get_top_placings(tourney, div_index, show_standings_after_finals)
        if excuse:
            response.writeln("%s" % (excuse))
        else:
            longest_name_length = max([ len(p[1]) for p in top_placings ])
            for (position, name, remark) in top_placings:
                if remark:
                    remark = "(" + remark + ")"
                response.writeln("%4s place: %-*s %s" % (
                    htmlcommon.ordinal_number(position),
                    longest_name_length,
                    htmlcommon.escape(name),
                    htmlcommon.escape(remark)
                ))
        response.writeln("")

    response.writeln("")
    response.writeln("STANDINGS")
    response.writeln("")
    response.writeln(rank_method.get_short_description())
    if show_draws_column:
        response.writeln("Draws count as half a win.")
    response.writeln("")
    response.writeln("")

    # Show standings table before and/or after finals
    if show_standings_before_finals:
        if show_standings_before_finals and show_standings_after_finals:
            response.writeln("Before %s" % (finals_noun))
            response.writeln("")
        export_text_standings(tourney, response, max_name_len, False,
                rank_method, show_draws_column, show_points_column,
                show_tournament_rating_column)
    if show_standings_after_finals:
        if show_standings_before_finals and show_standings_after_finals:
            response.writeln("After %s" % (finals_noun))
            response.writeln("")
        export_text_standings(tourney, response, max_name_len, True,
                rank_method, show_draws_column, show_points_column,
                show_tournament_rating_column)

    response.writeln("RESULTS")
    prev_round_no = None
    prev_table_no = None
    prev_division = None
    show_table_numbers = False
    game_seq = 0
    games = tourney.get_games()
    for g in games:
        if prev_round_no is None or prev_round_no != g.round_no:
            response.writeln("")
            response.writeln(tourney.get_round_name(g.round_no))
            prev_table_no = None
            prev_division = None
        if prev_division is None or prev_division != g.division:
            if num_divisions > 1:
                response.writeln("")
                response.writeln(tourney.get_division_name(g.division))
            i = 1
            prev_table_no = g.table_no
            show_table_numbers = False
            # If this division in this round has a table with more than
            # one game on it, show the table numbers, else don't.
            while game_seq + i < len(games) and games[game_seq + i].round_no == g.round_no and games[game_seq + i].division == g.division:
                if games[game_seq + i].table_no == prev_table_no:
                    show_table_numbers = True
                    break
                prev_table_no = games[game_seq + i].table_no
                i += 1
            prev_table_no = None
        if prev_table_no is None or prev_table_no != g.table_no:
            if show_table_numbers:
                response.writeln("")
                response.writeln("Table %d" % g.table_no)
        if g.s1 is None or g.s2 is None:
            score_str = "    -    "
        elif g.is_double_loss():
            score_str = "  X - X  "
        else:
            score_str = "%3d%s-%s%d" % (g.s1, "*" if g.tb and g.s1 > g.s2 else " ", "*" if g.tb and g.s2 >= g.s1 else " ", g.s2)
        names = g.get_player_names()
        response.writeln("%*s %-9s %s" % (max_name_len, names[0], score_str, names[1]))
        prev_round_no = g.round_no
        prev_table_no = g.table_no
        prev_division = g.division
        game_seq += 1

def export_wikitext(tourney, response, filename, show_standings_before_finals,
        show_standings_after_finals, finals_noun, date_d, date_m, date_y,
        game_prefix):
    full_name = tourney.get_full_name() or tourney.get_name()
    venue = tourney.get_venue()
    date_string = get_date_string(tourney)
    rank_method = tourney.get_rank_method()
    show_draws_column = tourney.get_show_draws_column()
    show_points_column = tourney.is_ranked_by_points()
    show_spread_column = tourney.is_ranked_by_spread()
    show_tournament_rating_column = tourney.get_show_tournament_rating_column()
    num_divisions = tourney.get_num_divisions()

    response.set_content_type("text/plain; charset=utf-8")
    if filename:
        response.add_header("Content-Disposition", "attachment; filename=\"%s.txt\"" % (filename))

    for rank_finals in [ False, True ]:
        # Skip this version of the standings table if we haven't been asked
        # for it
        if not rank_finals and not show_standings_before_finals:
            continue
        if rank_finals and not show_standings_after_finals:
            continue

        # Write a heading: if we're writing both before-finals and
        # after-finals standings, indicate atop each which it is.
        standings_heading = ""
        if show_standings_before_finals and show_standings_after_finals:
            if rank_finals:
                standings_heading = " (after %s)" % (finals_noun)
            else:
                standings_heading = " (before %s)" % (finals_noun)
        response.writeln("==Standings%s==" % (standings_heading))
        response.writeln()

        # Show the standings for each division
        sec_rank_headings = rank_method.get_secondary_rank_headings()
        for div_index in range(num_divisions):
            if num_divisions > 1:
                response.writeln("===%s===" % (tourney.get_division_name(div_index)))
            standings = tourney.get_standings(div_index, True, False, rank_finals=rank_finals)
            response.writeln("{|")
            response.write("! Rank !! Name !! Games !! Wins")
            if show_draws_column:
                response.write(" !! Draws")
            for head in sec_rank_headings:
                response.write(" !! " + head)
            if show_points_column and "Points" not in sec_rank_headings:
                response.write(" !! Points")
            if show_spread_column and "Spread" not in sec_rank_headings:
                response.write(" !! Spread")
            if show_tournament_rating_column:
                response.write(" !! Tournament rating")
            response.writeln("")
            for s in standings:
                response.writeln("|-")
                response.write("| %3d || %s || %d || %d" % (s.position, s.name, s.played, s.wins))
                if show_draws_column:
                    response.write(" || %d" % (s.draws))
                for val in s.get_secondary_rank_value_strings():
                    response.write(" || %s" % (val))
                if show_points_column and "Points" not in sec_rank_headings:
                    response.write(" || %d" % (s.points))
                if show_spread_column and "Spread" not in sec_rank_headings:
                    response.write(" || %+d" % (s.spread))
                if show_tournament_rating_column:
                    response.write(" || %d" % (s.tournament_rating))
                response.writeln("")
            response.writeln("|-")
            response.writeln("|}")
            response.writeln()

    # Show the results for each game
    response.writeln("==Results==")
    num_tiebreaks = 0
    game_serial_no = 1
    if date_d and date_m and date_y:
        wikitext_date = "%02d/%02d/%04d" % (date_d, date_m, date_y)
    else:
        wikitext_date = ""
    games = tourney.get_games()
    for div_index in range(num_divisions):
        if num_divisions > 1:
            response.writeln("===%s===" % (tourney.get_division_name(div_index)))
        response.writeln("{{game table}}")
        div_games = [x for x in games if x.get_division() == div_index]
        prev_round_no = None
        for g in div_games:
            if g.round_no != prev_round_no:
                response.writeln("{{game table block|%s}}" % (tourney.get_round_name(g.round_no)))
            response.writeln("{{game | %s%03d | %s | Table %d | %s | %s | %s | }}" % (
                    game_prefix, game_serial_no, wikitext_date,
                    g.table_no, g.get_player_names()[0], g.format_score(),
                    g.get_player_names()[1]))
            if g.tb:
                num_tiebreaks += 1
            prev_round_no = g.round_no
            game_serial_no += 1
        response.writeln("{{game table end}}")
        response.writeln("")

    if num_tiebreaks > 0:
        response.writeln("<center>* includes 10 points from a tie-break conundrum</center>")

def export_csv(tourney, response, filename, show_standings, selected_divisions, rank_finals, event_code, game_format):
    num_divisions = tourney.get_num_divisions()
    show_draws_column = tourney.get_show_draws_column()
    show_points_column = tourney.is_ranked_by_points()
    show_spread_column = tourney.is_ranked_by_spread()
    show_tournament_rating_column = tourney.get_show_tournament_rating_column()
    rank_method = tourney.get_rank_method()

    if filename:
        if show_standings:
            filename += "_standings"
        else:
            filename += "_results"
        response.set_content_type("text/csv; charset=utf-8")
        response.add_header("Content-Disposition", "attachment; filename=\"%s.csv\"" % (filename))
    else:
        response.set_content_type("text/plain; charset=utf-8")

    csv_string = StringIO()
    if show_standings:
        sec_rank_headings = rank_method.get_secondary_rank_headings()
        writer = csv.writer(csv_string, delimiter=",", quotechar="\"", quoting=csv.QUOTE_MINIMAL)
        if num_divisions == 1:
            selected_divisions = [0]

        # Write header row
        header_row = [ "Position", "Name", "Finals", "Played", "Wins", "Draws" ]
        if not rank_finals:
            del header_row[2]
        for heading in sec_rank_headings:
            header_row.append(heading)
        if show_points_column and "Points" not in sec_rank_headings:
            header_row.append("Points")
        if show_spread_column and "Spread" not in sec_rank_headings:
            header_row.append("Spread")
        writer.writerow(tuple(header_row))
        last_div_position = 0
        for div in sorted(selected_divisions):
            standings = tourney.get_standings(division=div,
                    calculate_qualification=False,
                    rank_finals=rank_finals)
            for s in standings:
                finals_form = s.finals_form
                while finals_form and finals_form[0] == '-':
                    finals_form = finals_form[1:]
                row = [ last_div_position + s.position, s.name, finals_form,
                        s.played, s.wins, s.draws ]
                if not rank_finals:
                    del row[2]
                for val in s.get_secondary_rank_value_strings():
                    row.append(val)
                if show_points_column and "Points" not in sec_rank_headings:
                    row.append(s.points)
                if show_spread_column and "Spread" not in sec_rank_headings:
                    row.append(s.spread)
                writer.writerow(tuple(row))

            if standings:
                last_div_position = standings[-1].position
    else:
        games = tourney.get_games()
        games = sorted(games, key=lambda x : (x.get_round_no(), x.get_division(), x.get_table_no(), x.get_round_seq()))

        writer = csv.writer(csv_string, delimiter=',', quotechar='\"', quoting=csv.QUOTE_MINIMAL)

        # Write header row
        writer.writerow(("Event code", "Player 1", "Player 1's score", "Player 2's score", "Player 2", "Round", "Format", "Tiebreak?"))
        for g in games:
            # If there's more than one division, then don't output a game
            # from a division that wasn't ticked when we submitted the form
            div = g.get_division()
            if num_divisions > 1 and div not in selected_divisions:
                continue

            player_names = g.get_player_names()
            game_type = g.get_game_type()
            if game_type in ('P', 'N'):
                round_text = str(g.get_round_no())
            else:
                # If it's QF, SF etc, use that rather than the round number
                round_text = game_type

            if len(selected_divisions) > 1:
                if div > 26:
                    round_text = tourney.get_short_division_name(div) + "." + round_text
                else:
                    round_text = tourney.get_short_division_name(div) + round_text
            # Write one row for each game
            score = g.get_score()
            writer.writerow((event_code,
                player_names[0], score[0], score[1], player_names[1],
                round_text, game_format, 1 if g.is_tiebreak() else None))
    response.write(csv_string.getvalue())

def show_export_report_form(response, tourney, num_final_games,
        num_complete_final_games, finals_noun,
        wikitext_date_y, wikitext_date_m, wikitext_date_d, wikitext_game_prefix):
    tourney_name = tourney.name

    # CSV only: let the user choose which divisions they want to include.
    division_options = ""
    num_divisions = tourney.get_num_divisions()
    if num_divisions > 1:
        # All checkboxes start checked, and also disabled because they're in
        # the CSV-specific section, which is not shown on page load.
        division_options += "<div class=\"formline\">"
        division_options += "<div class=\"formlabel\"><label>Which divisions?</label></div>"
        division_options += "<div class=\"formcontrol\">"
        for div in range(num_divisions):
            division_options += "<input type=\"checkbox\" name=\"csvdiv%d\" id=\"csvdiv%d\" value=\"1\" checked disabled /> <label for=\"csvdiv%d\">%s</label><br />" % (
                    div, div, div, htmlcommon.escape(tourney.get_division_name(div))
            )
        division_options += "</div>"
        division_options += "</div>"

    # Wikitext only: build a month selector
    month_options = ""
    for m in range(1, 13):
        month_options += '<option value="%d" %s>%s</option>' % (
                m, "selected " if m == wikitext_date_m else "",
                htmlcommon.escape(calendar.month_name[m])
        )

    finals_options = ""
    finals_warning = ""
    if num_final_games == 0:
        finals_warning = "<p><strong>Note:</strong> was a final played? If so, you haven't created a fixture for it so it will not show up in the report.</p>"
    elif num_complete_final_games == 0:
        finals_warning = "<p><strong>Note:</strong> you have created a fixture for the final but its score has not been entered.</p>"
    else:
        finals_options = """
<div class="formline">
    <div class="formlabel"><label for="finals">Standings</label></div>
    <div class="formcontrol">
        <select name="finals" id="finals">
            <option value="before">Show positions before %(finals)s</option>
            <option value="after" selected>Show positions after %(finals)s</option>
            <option value="both" id="finalsbothoption">Show positions both before and after %(finals)s</option>
        </select>
    </div>
</div>
""" % {
            "finals" : finals_noun
        }

    html = """<h1>Export results</h1>
<script>
function formatDropDownChange() {
    let formatSelect = document.getElementById("format");
    if (formatSelect == null)
        return;
    let formatValue = formatSelect.options[formatSelect.selectedIndex].value;

    /* Make all format-specific option divs invisible except the one
       corresponding to the selected format. */
    let formatSpecificDivs = document.getElementsByClassName("formatspecificoptions");
    for (let i = 0; i < formatSpecificDivs.length; i++) {
        let div = formatSpecificDivs[i];
        let affectedInputs = div.getElementsByTagName("INPUT");
        let affectedSelects = div.getElementsByTagName("SELECT");
        let disableInputs;
        if (div.id == formatValue + "options") {
            div.style.display = "block";
            disableInputs = false;
        }
        else {
            div.style.display = "none";
            disableInputs = true;
        }

        /* Disable the inputs and dropdowns in a hidden div. */
        for (let j = 0; j < affectedInputs.length; j++) {
            affectedInputs[j].disabled = disableInputs;
        }
        for (let j = 0; j < affectedSelects.length; j++) {
            affectedSelects[j].disabled = disableInputs;
        }
    }

    /* "Both before and after finals" option is available for every format
        except CSV. */
    let finalsBothOption = document.getElementById("finalsbothoption");
    let finalsSelect = document.getElementById("finals");
    if (finalsSelect && finalsBothOption) {
        if (formatValue == "csv") {
            if (finalsBothOption.selected) {
                finals.selectedIndex = 1;
            }
        }
        finalsBothOption.disabled = (formatValue == "csv");
    }
}

function validateDate() {
    let dayElement = document.getElementById("wikitextday");
    let monthElement = document.getElementById("wikitextmonth");
    let yearElement = document.getElementById("wikitextyear");
    let dateInvalid = false;
    if (dayElement && monthElement && yearElement) {
        let day = parseInt(dayElement.value);
        let month = monthElement.selectedIndex + 1;
        let year = parseInt(yearElement.value);

        if (!(isNaN(day) || isNaN(month) || isNaN(year))) {
            if (month < 1 || month > 12) {
                dateInvalid = true;
            }
            else {
                let dayMax;
                switch (month) {
                    case 4:
                    case 6:
                    case 9:
                    case 11:
                        dayMax = 30;
                        break;
                    case 2:
                        dayMax = 28;
                        if (year %% 4 == 0 && !(year %% 100 == 0 && year %% 400 != 0)) {
                            dayMax++;
                        }
                        break;
                    default:
                        dayMax = 31;
                }
                if (day < 1 || day > dayMax) {
                    dateInvalid = true;
                }
            }
        }
        else {
            dateInvalid = true;
        }
    }

    let invalidDateElement = document.getElementById("invaliddate");
    if (invalidDateElement) {
        invalidDateElement.style.display = dateInvalid ? "inline-block" : "none";
    }
}
</script>

<h2>Tournament report</h2>

<p>
Show or download a report of the tourney results and/or standings.
</p>

%(finalswarning)s

<div class="formbox exportformbox">
<form method="GET" target="_blank">

<div class="formline">
<div class="formlabel"><label for="format">Export format</label></div>
<div class="formcontrol">
<select id="format" name="format" onchange="formatDropDownChange();">
    <option value="html" selected>HTML</option>
    <option value="text">Plain text</option>
    <option value="csv">CSV</option>
    <option value="wikitext">Wikitext</option>
</select>
</div>
</div>

%(finalsoptions)s

<div class="formatspecificoptions" id="csvoptions" style="display: none;">
    <div class="formline">
        <div class="formlabel">
            <label for="csveventcode">Event code</label>
        </div>
        <div class="formcontrol">
            <input type="text" name="csveventcode" id="csveventcode" value="%(tourneyname)s" disabled />
            <span class="formcontrolhelp">(e.g. COLIN2022)</span>
        </div>
    </div>

    <div class="formline">
        <div class="formlabel">
            <label for="csvgameformat">Game format</label>
        </div>
        <div class="formcontrol">
            <input type="text" name="csvgameformat" id="csvgameformat" value="" disabled />
            <span class="formcontrolhelp">(e.g. 9R, 15R, ...)</span>
        </div>
    </div>

    %(divisionoptions)s

    <div class="formline">
        <div class="formlabel">
            <label for="csvtable">Export what?</label>
        </div>
        <div class="formcontrol">
            <select name="csvtable" id="csvtable" disabled>
                <option value="standings" selected>Standings table</option>
                <option value="results">Game results</option>
            </select>
        </div>
    </div>
</div>

<div class="formatspecificoptions" id="wikitextoptions" style="display: none;">
    <div class="formline">
        <div class="formlabel">
            <label>Event date</label>
        </div>
        <div class="formcontrol">
            <input type="number" id="wikitextday" name="wikitextday" value="%(wikitextday)d" min="1" max="31" size="2" placeholder="DD" onchange="validateDate();" disabled />
            <select name="wikitextmonth" id="wikitextmonth" onchange="validateDate();" disabled>
                %(monthoptions)s
            </select>
            <input type="number" id="wikitextyear" name="wikitextyear" value="%(wikitextyear)d" min="0" max="9999" size="4" placeholder="YYYY" onchange="validateDate();" disabled />
            <div id="invaliddate" style="display: none; background-color: #ffffdd; font-size: 10pt; margin-left: 10px; padding: 2px;">
                This isn't a valid date. I'll happily put it in the Wikitext anyway, but I just thought I'd let you know.
            </div>
        </div>
    </div>

    <div class="formline">
        <div class="formlabel"><label for="wikitextgameprefix">Game ID prefix</label></div>
        <div class="formcontrol">
            <input type="text" name="wikitextgameprefix" value="%(wikitextgameprefix)s" disabled />
        </div>
    </div>
</div>

<div class="formline" style="margin-top: 20px;">
    <div class="formlabel"></div>
    <div class="formcontrol">
        <input type="submit" name="submitview" value="Show in browser" class="bigbutton" />
        <input type="submit" name="submitdownload" value="Download" class="bigbutton" />
    </div>
</div>
</form>
</div> <!-- formbox -->
""" % {
        "tourneyname" : htmlcommon.escape(tourney_name),
        "wikitextday" : wikitext_date_d,
        "monthoptions" : month_options,
        "wikitextyear" : wikitext_date_y,
        "wikitextgameprefix" : htmlcommon.escape(wikitext_game_prefix),
        "divisionoptions" : division_options,
        "finalsoptions" : finals_options,
        "finalswarning" : finals_warning
    }
    response.writeln(html)

###############################################################################

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    started_html = False;
    tourney_name = tourney.name
    export_format = form.getfirst("format");
    wikitext_date_d = int_or_none(form.getfirst("wikitextday"));
    wikitext_date_m = int_or_none(form.getfirst("wikitextmonth"))
    wikitext_date_y = int_or_none(form.getfirst("wikitextyear"))
    wikitext_game_prefix = form.getfirst("wikitextgameprefix")
    wikitext_submit = form.getfirst("wikitextsubmit")

    csv_event_code = form.getfirst("csveventcode")
    csv_game_format = form.getfirst("csvgameformat")
    csv_table = form.getfirst("csvtable")

    standings_finals = form.getfirst("finals")
    if not standings_finals:
        standings_finals = "after"

    submit_view = form.getfirst("submitview")
    submit_download = form.getfirst("submitdownload")
    submit = submit_view or submit_download

    if csv_event_code is None:
        csv_event_code = ""
    if csv_game_format is None:
        csv_game_format = ""

    num_finals_games = tourney.get_num_games(finals_only=True)
    final_games = tourney.get_games(game_type="F")
    num_final_games = len(final_games)
    num_complete_final_games = len( [ g for g in final_games if g.is_complete() ] )
    finals_noun = "final" if num_finals_games == 1 else "finals"

    non_local_client = httpreq is not None and not httpreq.is_client_from_localhost()

    if not submit:
        # Show the form asking the user what format they want, and any other
        # options.

        # Default value for Wikitext event date is the event date recorded in
        # the tourney, or the current date if that is not set.
        (year, month, day) = tourney.get_event_date()
        if year and month and day:
            wikitext_date_d = day
            wikitext_date_m = month
            wikitext_date_y = year
        else:
            today = datetime.date.today()
            wikitext_date_d = today.day
            wikitext_date_m = today.month
            wikitext_date_y = today.year

        # Set up the default game ID prefix for the Wikitext format
        wikitext_game_prefix = ""
        for c in tourney_name.upper():
            if c.isupper() or c.isdigit():
                wikitext_game_prefix += c
        if wikitext_game_prefix[-1].isdigit():
            wikitext_game_prefix += "."

        # No format specified: display a list of possible formats to choose from
        started_html = True
        htmlcommon.print_html_head(response, "Export results: " + str(tourney_name))

        response.writeln("<body>")

        htmlcommon.show_sidebar(response, tourney, non_local_client=non_local_client)

        response.writeln("<div class=\"mainpane\">")

        # Show the form asking the user what format they want to export in,
        # and any other options.
        show_export_report_form(response, tourney, num_final_games,
                num_complete_final_games, finals_noun,
                wikitext_date_y, wikitext_date_m, wikitext_date_d,
                wikitext_game_prefix)

        if not non_local_client:
            # Write a link to grab the .db file
            response.writeln("""
<h2>Database file</h2>
<p>
Download link for the SQLite3 database file for this tourney. Useful if you
want to save a backup or import this tourney to another Atropine installation.
</p>
<blockquote>
<a href="/atropine/%(tourneyname)s/exportdbfile">%(tourneyname)s.db</a>
</blockquote>
""" % {
                "tourneyname" : htmlcommon.escape(tourney_name)
            })

        response.writeln("</div>") #mainpane
        response.writeln("</body>")
        response.writeln("</html>")
        return

    # If we get here, the form was submitted.
    # Output the exported tournament information in the requested format.
    try:
        show_standings_before_finals = (standings_finals in ("before", "both"))
        show_standings_after_finals = (standings_finals in ("after", "both"))

        if num_finals_games == 0:
            # No point showing state after finals if there are no finals...
            show_standings_before_finals = True
            show_standings_after_finals = False

        if submit_download:
            filename = tourney.get_name()
        else:
            filename = None

        started_html = True
        if export_format == "html":
            export_html(tourney, response, filename, show_standings_before_finals, show_standings_after_finals, finals_noun)
        elif export_format == "text":
            export_text(tourney, response, filename, show_standings_before_finals, show_standings_after_finals, finals_noun)
        elif export_format == "wikitext":
            export_wikitext(tourney, response, filename,
                    show_standings_before_finals, show_standings_after_finals,
                    finals_noun, wikitext_date_d, wikitext_date_m,
                    wikitext_date_y, wikitext_game_prefix)
        elif export_format == "csv":
            selected_divisions = set()
            for div_index in range(tourney.get_num_divisions()):
                if ("csvdiv%d" % (div_index)) in form:
                    selected_divisions.add(div_index)
            export_csv(tourney, response, filename, csv_table == "standings",
                    selected_divisions, show_standings_after_finals,
                    csv_event_code, csv_game_format)
        else:
            response.set_content_type("text/plain; charset=utf-8")
            response.writeln("Invalid format: " + export_format)
    except countdowntourney.TourneyException as e:
        if started_html:
            htmlcommon.show_tourney_exception(response, e);
        else:
            show_error(response, e.get_description());
