#!/usr/bin/python3

import htmlcommon
import countdowntourney

def int_or_none(s):
    if s is None:
        return None
    else:
        try:
            return int(s)
        except:
            return None

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    # Read parameters to adjust how the table is formatted
    max_columns = int_or_none(form.getfirst("maxcols"))
    if max_columns is None or max_columns < 1:
        max_columns = 3
    names_per_column = int_or_none(form.getfirst("namespercol"))
    if names_per_column is None or names_per_column <= 0:
        names_per_column = 20
    min_names_per_column = int_or_none(form.getfirst("minnamespercol"))
    if min_names_per_column is None or min_names_per_column < 0:
        min_names_per_column = 5

    htmlcommon.print_html_head(response, "Table assignment")

    response.writeln("<body>")

    htmlcommon.show_sidebar(response, tourney)

    response.writeln("<div class=\"mainpane\">")

    rd = tourney.get_current_round()

    if rd is None:
        response.writeln("<h1>Table assignment</h1>")
        response.writeln("<p>There are no fixtures yet.</p>")
    else:
        round_no = rd["num"]
        round_name = rd["name"]

        response.writeln("<h1>Table assignment: %s</h1>" % (htmlcommon.escape(round_name)))
        games = tourney.get_games(round_no)

        # Map of player name -> list of table numbers they're on in this round
        player_name_to_table_list = dict()

        # Map of player name -> player object
        player_name_to_player = dict()

        # Map of table number -> list of players
        table_to_player_list = dict()

        for g in games:
            names = []
            current_player_list = table_to_player_list.get(g.table_no, [])
            for p in [g.p1, g.p2]:
                if not p.is_prune():
                    names.append(p.get_name())
                    player_name_to_player[p.get_name()] = p
                    if p not in current_player_list:
                        current_player_list.append(p)
            table_to_player_list[g.table_no] = current_player_list
            for name in names:
                current_table_list = player_name_to_table_list.get(name, [])
                if g.table_no not in current_table_list:
                    player_name_to_table_list[name] = current_table_list + [g.table_no]

        # Display the index in several columns, so we use more horizontal space
        # and save vertical space.

        num_names = len(player_name_to_table_list)

        if num_names > 0:
            num_columns = (num_names + names_per_column - 1) // names_per_column
            if num_columns <= 2:
                names_per_column = num_names

            # If there would be fewer than five names in the last column, use
            # one fewer column and extend the earlier columns.
            if num_columns > 1 and num_names % names_per_column > 0 and num_names % names_per_column < min_names_per_column:
                num_columns -= 1
                names_per_column = (num_names + num_columns - 1) // num_columns

            # Don't display more than the maximum number of columns. If we have
            # more than this many columns, make the columns longer.
            if num_columns > max_columns:
                num_columns = max_columns
                names_per_column = (num_names + num_columns - 1) // num_columns

            response.writeln("<table class=\"misctable\">")
            columns = [ [] for i in range(num_columns) ]
            sorted_names = sorted(player_name_to_table_list)
            for position_in_column in range(0, names_per_column):
                response.writeln("<tr>")
                for column in range(0, num_columns):
                    position_in_list = column * names_per_column + position_in_column
                    if position_in_list < len(sorted_names):
                        name = sorted_names[position_in_list]
                        player = player_name_to_player.get(name, None)
                        if player:
                            response.writeln(("<td class=\"text tableindexname\">%s</td>" % (htmlcommon.player_to_link(player, tourney.get_name()))))
                        else:
                            response.writeln(("<td class=\"text tableindexname\">%s</td>" % (htmlcommon.escape(name))))

                        # Show the list of tables this player is on in this
                        # round. This will almost always be one table, but it
                        # is possible to construct a round in which a player
                        # has to be in two places.
                        response.writeln("<td class=\"tableindexnumber\" style=\"border-left: none\" >")
                        table_list = player_name_to_table_list[name]
                        for index in range(len(table_list)):
                            # Print the table number, with a mouseover-text
                            # listing all the players on that table.
                            player_list = table_to_player_list.get(table_list[index], [])
                            title = "Table %d: %s" % (table_list[index], ", ".join(sorted([x.get_name() for x in player_list])))
                            response.writeln(("<div class=\"tablebadgenaturalsize\" style=\"margin-top: 2px; margin-bottom: 2px;\" title=\"%s\">" % htmlcommon.escape(title, True)));
                            response.writeln(("%d" % (table_list[index])))
                            response.writeln("</div>")
                            if index < len(table_list) - 1:
                                response.writeln(", ");
                        response.writeln("</td>")

                        if column < num_columns - 1:
                            response.writeln("<td class=\"columnspacer\"> </td>")

                response.writeln("</tr>")
            response.writeln("</table>")

    response.writeln("</div>")
    response.writeln("</body>")
    response.writeln("</html>")

