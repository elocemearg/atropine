#!/usr/bin/python3

import io
import re

import countdowntourney
import htmlcommon

ALIGN_NONE = 0
ALIGN_LEFT = 1
ALIGN_CENTRE = 2
ALIGN_RIGHT = 3

ALIGN_CSS_VALUES = [ "none", "left", "center", "right" ]
ALIGN_FORMATS = [ "", "<", "^", ">" ]

MAX_ABBR_LENGTH = 6

WORD_DELIM = re.compile(r"\W+")
def split_into_words(s: str) -> list[str]:
    return [ word for word in WORD_DELIM.split(s) if len(word) > 0 ]

# Yield all permutations of n positive integers which sum to total.
def get_permutations_with_sum(n, total):
    if n < 1 or total < n:
        return
    if n == 1:
        if total >= 1:
            yield [ total ]
    else:
        for first_number in range(total - (n - 1), 0, -1):
            for remainder in get_permutations_with_sum(n - 1, total - first_number):
                yield [ first_number ] + remainder

def disallow_for_prefixes_matching_another_name(word_prefix_lengths, proposed_abbr, this_name, names_to_words):
    proposed_abbr = proposed_abbr.upper()
    this_name_words = names_to_words[this_name]
    longest_word_prefix_length = max(MAX_ABBR_LENGTH - len(this_name_words), 1)
    for other_name in names_to_words:
        if other_name == this_name:
            continue
        other_name_words = names_to_words[other_name]

        # Check that the corresponding abbreviation of the other name doesn't
        # match this name, ignoring case.
        # Note that if word_prefix_lengths[i] is greater than the length of
        # this_name_words[i], (example: this_name is "Tom Frobnicate",
        # other_name is "Tombola Frobnicate", word_prefix_lengths = [ 4, 2 ])
        # then we don't return True here. We allow it, because no amount of
        # extra letters from "Tom Frobnicate" can make it truly unambiguous
        # from "Tombola Frobnicate", but we've included the full first word.
        other_abbr = "".join([ other_name_words[i][0:word_prefix_lengths[i]] for i in range(min(len(other_name_words), len(word_prefix_lengths)))])
        if other_abbr.upper() == proposed_abbr:
            return True
    return False

def find_unique_abbreviations(names: list[str],
        names_to_words: dict[str, list[str]], banned_abbrs: set[str]) -> dict[str, str]:
    num_words = min([ len(names_to_words[name]) for name in names ])
    num_words = min(num_words, MAX_ABBR_LENGTH)

    names_remaining = set(names)
    abbrs_assigned = set()
    name_to_abbr = {}
    for abbr_length in range(num_words, MAX_ABBR_LENGTH + 1):
        for word_prefix_lengths in get_permutations_with_sum(num_words, abbr_length):
            # get_permutations_with_sum will return permutations with high
            # numbers in the first position first. But we'd rather use
            # letters from the surname first, then the first name, then any
            # other names, so remove the first number from word_prefix_lengths
            # and stick it on the end.
            word_prefix_lengths = word_prefix_lengths[1:] + [ word_prefix_lengths[0] ]
            candidate_name_to_abbr = {}
            for name in sorted(names_remaining):
                words = names_to_words[name][0:MAX_ABBR_LENGTH]
                abbr = "".join([ words[i][0:word_prefix_lengths[i]] for i in range(len(word_prefix_lengths))])
                abbr_up = abbr.upper()
                if abbr_up != name.upper() and (abbr_up in banned_abbrs or abbr_up in abbrs_assigned):
                    # abbr isn't unique
                    pass
                elif disallow_for_prefixes_matching_another_name(word_prefix_lengths, abbr_up, name, names_to_words):
                    # This set of word prefixes could also describe
                    # another name, even if that name hasn't actually been
                    # assigned this abbreviation.
                    pass
                else:
                    # We can assign this abbreviation to this name, unless we
                    # find later on that this list of prefix lengths also gives
                    # this same abbreviation when applied to another name.
                    candidate_name_to_abbr[name] = abbr
            # Anything left in candidate_name_to_abbr is good to assign
            for name in candidate_name_to_abbr:
                names_remaining.remove(name)
                abbrs_assigned.add(candidate_name_to_abbr[name].upper())
                name_to_abbr[name] = candidate_name_to_abbr[name]
            if len(names_remaining) == 0:
                break
        if len(names_remaining) == 0:
            break

    # If there are still names which haven't been assigned an abbreviation,
    # then give up - choose an abbreviation containing the maximum number of
    # letters we allow, and stick a serial number on the end.
    for name in sorted(names_remaining):
        word_prefix_lengths = []
        words = names_to_words[name]
        abbr_length = 0
        # Choose how many letters we're going to use from each word
        for x in range(min(len(words), MAX_ABBR_LENGTH)):
            word_prefix_lengths.append(1)
            abbr_length += 1
        # Prefer to use letters from the last name
        for word_index in range(len(words) - 1, -1, -1):
            if abbr_length >= MAX_ABBR_LENGTH:
                break
            extra_letters = min(len(words[word_index]) - 1, MAX_ABBR_LENGTH - abbr_length)
            word_prefix_lengths[word_index] += extra_letters
            abbr_length += extra_letters

        abbr = "".join([ words[i][0:word_prefix_lengths[i]] for i in range(len(word_prefix_lengths)) ])
        n = 1
        found = False
        while not found:
            numbered_abbr = abbr + str(n)
            numbered_abbr_up = numbered_abbr.upper()
            if numbered_abbr_up not in abbrs_assigned and numbered_abbr_up not in banned_abbrs:
                abbrs_assigned.add(numbered_abbr_up)
                name_to_abbr[name] = numbered_abbr
                found = True
            else:
                n += 1

    return name_to_abbr


# Given a list of all player names, find an abbreviation for each one which
# isn't the same as any other player's abbreviation. Return a dict which
# maps each player name to its abbreviation.
def abbreviate_names(names: list[str]) -> dict[str, str]:
    # First, split each name into words.
    names_to_words = {}
    for name in names:
        names_to_words[name] = split_into_words(name)

    # As an initial attempt (ho ho!), abbreviate each player's name to the
    # first letter of each word. If a player's name is only one word,
    # also count any capital letters in that word. Do not use more than
    # MAX_ABBR_LENGTH initials.
    # For example:
    #   "Fred Bloggs" becomes "FB"
    #   "Mary O'Brien" becomes "MOB"
    #   "Joe Smith-Jones" becomes "JSJ"
    #   "Iron de Havilland" becomes "IdH"
    #   "Pierre LAPIN" becomes "PL"
    #   "My Name Is Far Too Long To Use All My Initials" becomes "MNIFTL"
    #   "ConundrumMachine" becomes "CM"
    #   "MSR" becomes "MSR"
    name_to_abbr = {}
    abbr_to_names = {}

    # Upcased abbreviations we have decided must not be used even if no other
    # name uses it, because it's equal to someone else's full name.
    ambiguous_abbrs = set()
    for name in names:
        ambiguous_abbrs.add(name.upper())

    for name in sorted(names_to_words):
        words = names_to_words[name][0:MAX_ABBR_LENGTH]
        if len(words) == 0:
            # Name consists only of non-word characters?
            abbr = name[0]
        elif len(words) == 1:
            abbr = words[0][0] + "".join([ x for x in words[0][1:] if x.isupper() ])
        else:
            abbr = "".join([ word[0] for word in words ])
        name_to_abbr[name] = abbr
        abbr_upcased = abbr.upper()
        if abbr_upcased not in abbr_to_names:
            abbr_to_names[abbr_upcased] = []
        abbr_to_names[abbr_upcased].append(name)

    # Acceptable abbreviations which we have assigned to a player, so no
    # other player is allowed to use it.
    used_abbrs = set()

    # If any abbreviation has been used for more than one name (disregarding
    # case of abbreviation) then we have to disambiguate them by adding other
    # characters from the name.
    # For example, if we have Joe Bloggs and Jim Blaggs, we might abbreviate
    # them to JoB and JiB, provided there were no other players with those
    # abbrevations.
    for abbr_upcased in abbr_to_names:
        if len(abbr_to_names[abbr_upcased]) == 1:
            # We can use this abbreviation if it matches the player's name or
            # doesn't match any player's name.
            if abbr_upcased == abbr_to_names[abbr_upcased][0].upper() or abbr_upcased not in ambiguous_abbrs:
                used_abbrs.add(abbr_upcased)

    for abbr_upcased in sorted(abbr_to_names):
        abbr_names = abbr_to_names[abbr_upcased]
        if len(abbr_names) > 1 or (abbr_upcased != abbr_names[0].upper() and abbr_upcased in ambiguous_abbrs):
            # This abbreviation isn't acceptable.
            # Find unique abbreviations for this set of names.
            # If some of these names have a different number of words
            # to other names with the same abbreviation, deal with them
            # separately. find_unique_abbreviations() only works if all
            # the names you give it have the same number of words.
            word_counts_done = set()
            finished = False
            while not finished:
                word_count = None
                name_sub_list = []
                for name in sorted(abbr_names):
                    words = names_to_words[name][0:MAX_ABBR_LENGTH]
                    if word_count is None and len(words) not in word_counts_done:
                        word_count = len(words)
                    if word_count is not None and word_count == len(words):
                        name_sub_list.append(name)
                if word_count:
                    these_names_to_abbrs = find_unique_abbreviations(name_sub_list, names_to_words, ambiguous_abbrs | used_abbrs)
                    for n in these_names_to_abbrs:
                        a = these_names_to_abbrs[n]
                        used_abbrs.add(a)
                        name_to_abbr[n] = a
                    word_counts_done.add(word_count)
                else:
                    finished = True
    return name_to_abbr


class FormattedTableCell(object):
    def __init__(self, content, align=ALIGN_NONE, colspan=1, classes=[], html_content=None):
        self.content = str(content)
        if html_content:
            self.html_content = str(html_content)
        else:
            self.html_content = htmlcommon.escape(self.content)
        self.align = align
        self.colspan = colspan
        self.classes = classes[:]
        self.content_width = len(self.content)

    def get_colspan(self):
        return self.colspan

    def get_content_width(self):
        return self.content_width

    def to_html(self, out, tag):
        out.write("<")
        out.write(tag)
        if self.colspan != 1:
            out.write(" colspan=\"%d\"" % (self.colspan))
        if self.align != ALIGN_NONE and self.align >= 0 and self.align < len(ALIGN_CSS_VALUES):
            out.write(" style=\"text-align: %s;\"" % (ALIGN_CSS_VALUES[self.align]))
        if self.classes:
            out.write(" class=\"")
            out.write(" ".join([ htmlcommon.escape(c) for c in self.classes ]))
            out.write("\"")
        out.write(">")
        out.write(self.html_content)
        out.write("</")
        out.write(tag)
        out.write(">\n")

    def to_text(self, out, width):
        formatter = "{:"
        if self.align >= 0 and self.align < len(ALIGN_FORMATS):
            formatter += ALIGN_FORMATS[self.align]
        formatter += str(width)
        formatter += "}"
        out.write(formatter.format(self.content))

class FormattedTable(object):
    def __init__(self):
        self.rows = []
        self.header_rows = set()
        self.separator_before_columns = set()
        self.table_classes = []

    def mark_header_row(self, row_number, is_header=True):
        if is_header:
            self.header_rows.add(row_number)
        else:
            if row_number in self.header_rows:
                self.header_rows.remove(row_number)

    def add_vertical_separator(self, before_column):
        self.separator_before_columns.add(before_column)

    def _append_cell(self, row_number, cell):
        if row_number < 0:
            return
        # If we don't have this row yet, add it and all the other missing rows before it.
        if row_number >= len(self.rows):
            num_new_rows = 1 + row_number - len(self.rows)
            for i in range(num_new_rows):
                self.rows.append([])

        self.rows[row_number].append(cell)

        # If this cell is supposed to span multiple columns, add None entries
        # after it, up to the number of columns it spans.
        if cell.get_colspan() > 1:
            for i in range(cell.get_colspan() - 1):
                self.rows[row_number].append(None)

    def append_cell(self, row_number, content, align=ALIGN_NONE, colspan=1, classes=[], html_content=None):
        self._append_cell(row_number, FormattedTableCell(content, align=align, colspan=colspan, classes=classes, html_content=html_content))

    def get_num_cells(self, row_number):
        if row_number < 0 or row_number >= len(self.rows):
            return 0
        else:
            return len(self.rows[row_number])

    # If the given row has fewer than next_column_number columns in it,
    # add empty cells until the row has next_column_number columns.
    def pad_row(self, row_number, next_column_number):
        if row_number < 0:
            return
        while self.get_num_cells(row_number) < next_column_number:
            self._append_cell(row_number, FormattedTableCell("", classes=["emptycell"]))

    def to_html(self):
        out = io.StringIO()
        split_tables = (len(self.separator_before_columns) > 0)
        if split_tables:
            # We will write out a number of tables side by side
            out.write("<div class=\"formattedtableset\">\n")

        first_columns = [0] + sorted(list(self.separator_before_columns))
        for (idx, first_column) in enumerate(first_columns):
            if idx + 1 >= len(first_columns):
                last_column = None
            else:
                last_column = first_columns[idx + 1] - 1

            if split_tables:
                out.write("<div class=\"formattedtablecontainer\">\n")
            out.write("<table")
            if self.table_classes:
                out.write(" class=\"")
                out.write(" ".join([ htmlcommon.escape(c) for c in self.table_classes]))
                out.write("\"")
            out.write(">\n")
            for (row_number, row) in enumerate(self.rows):
                td = "th" if row_number in self.header_rows else "td"
                out.write("<tr>\n")
                column_index = first_column
                while column_index < len(row) and (last_column is None or column_index <= last_column):
                    if row[column_index]:
                        row[column_index].to_html(out, td)
                    column_index += 1
                out.write("</tr>\n")
            out.write("</table>\n")
            if split_tables:
                out.write("</div>\n")

        if split_tables:
            out.write("</div>\n")

        return out.getvalue()

    def to_text(self):
        if not self.rows:
            return ""

        # For each column, find the longest cell content. We'll start with
        # the single columns (colspan=1).
        coords_to_colspan = {}
        max_col_index = None
        for (row_index, row) in enumerate(self.rows):
            for (col_index, cell) in enumerate(row):
                if cell:
                    coords_to_colspan[(row_index, col_index)] = cell.get_colspan()
                    if max_col_index is None or col_index > max_col_index:
                        max_col_index = col_index

        if max_col_index is None:
            return ""

        col_width = [ 0 for x in range(0, max_col_index + 1) ]
        coords_sorted_by_colspan = sorted(list(coords_to_colspan), key=lambda x : coords_to_colspan[x])

        # Find the longest cell content for each column. If a cell spans
        # multiple columns, size its content against the widths of all the
        # columns it spans.
        vertical_separator = "   "
        internal_cell_border = " "
        internal_border_width = len(internal_cell_border)
        for (row_index, col_index) in coords_sorted_by_colspan:
            cell = self.rows[row_index][col_index]
            if cell:
                width = cell.get_content_width()
                current_col_width = col_width[col_index]
                colspan = cell.get_colspan()
                if colspan > 1:
                    # Required width for this cell is the cell content plus
                    # the borders between the spanned cells.
                    for i in range(1, colspan):
                        if col_index + i < len(col_width):
                            current_col_width += col_width[col_index + i]
                    current_col_width += internal_border_width * (colspan - 1)
                    if width > current_col_width:
                        # This cell spans multiple columns, but its content
                        # is still larger than the space we currently allow
                        # for all those columns combined. Increase the sizes
                        # of each of these columns by a single space each
                        # until the multi-column-spanning cell is wide enough.
                        extra_needed = width - current_col_width
                        for i in range(colspan):
                            col_width[col_index + i] += (extra_needed + colspan - 1) // colspan
                else:
                    # Just a simple colspan=1 cell - make sure the column is wide enough for it.
                    if width > col_width[col_index]:
                        col_width[col_index] = width

        out = io.StringIO()
        for row in self.rows:
            for (col_index, cell) in enumerate(row):
                if col_index in self.separator_before_columns:
                    out.write(vertical_separator)
                if cell:
                    colspan = cell.get_colspan()
                    if colspan > 1:
                        # Width of this cell is the sum of the widths of the
                        # columns it spans, plus inter-cell border widths.
                        cell_width = 0
                        for x in range(col_index, col_index + colspan):
                            if x >= len(col_width):
                                break
                            cell_width += col_width[x]
                        cell_width += internal_border_width * (colspan - 1)
                    else:
                        cell_width = col_width[col_index]
                    cell.to_text(out, cell_width)
                    if col_index < len(row) - 1:
                        out.write(internal_cell_border)
            out.write("\n")
        return out.getvalue()

class ProgressByPlayer(FormattedTable):
    def __init__(self, tourney: countdowntourney.Tourney, division: int,
                round_standings: dict[int, list[countdowntourney.StandingsRow]],
                names_to_abbrs=None):
        super().__init__()
        self.table_classes = [ "misctable", "progressiontable" ]

        rank_method = tourney.get_rank_method()
        round_standings_headings = [ "Pos", "W" ] + rank_method.get_secondary_rank_headings(short=True)

        round_numbers = sorted(list(round_standings))

        # Heading row:
        # Player name | Round 1 games | Pos | W | Pts | | Round 2 games | ...
        self.mark_header_row(0)
        self.append_cell(0, "Player")
        self.append_cell(0, "", classes=["progressionroundspace"])
        for round_no in round_numbers:
            self.append_cell(0, tourney.get_round_name(round_no))
            for (idx, heading) in enumerate(round_standings_headings):
                self.append_cell(0, heading, align=ALIGN_RIGHT)
            if round_no != round_numbers[-1]:
                # Add a spacer cell
                self.append_cell(0, "  ", classes=["progressionroundspace"])

        player_names = sorted([ p.get_name() for p in tourney.get_players_from_division(division) ])
        player_short_display = {}
        for name in player_names:
            if names_to_abbrs and name in names_to_abbrs and names_to_abbrs[name] != name:
                player_short_display[name] = "[" + names_to_abbrs[name] + "]"
            else:
                player_short_display[name] = name
        prune_name = tourney.get_auto_prune_name()
        player_short_display[prune_name] = "Prune"

        # Build a dict where we can look up the games any player played in a
        # given round, and another where can look up a player's standings
        # position at the end of a round.
        round_player_games = {} # (round_no, player_name) -> [ ("W"/"D"/"L"/"?", opponent_name, Game) ]
        round_player_standings_row = {} # (round_no, player_name) -> StandingsRow
        for round_no in round_numbers:
            games = tourney.get_games(round_no=round_no, division=division)
            standings = round_standings[round_no]
            for game in games:
                game_players = game.get_players()
                for i in [0, 1]:
                    gp = game_players[i]
                    gp_opp = game_players[i ^ 1]
                    dict_key = (round_no, gp.get_name())
                    if dict_key not in round_player_games:
                        round_player_games[dict_key] = []
                    if game.is_draw():
                        result = "D"
                    elif game.is_player_winner(gp):
                        result = "W"
                    elif game.is_player_loser(gp):
                        result = "L"
                    else:
                        result = "?"
                    opponent_name = gp_opp.get_name()
                    round_player_games[dict_key].append((result, opponent_name, game))
            for standing in standings:
                round_player_standings_row[(round_no, standing.name)] = standing

        row_number = 0
        for player_name in player_names:
            row_number += 1
            classes = ["progressionalternate%d" % (row_number % 2 + 1)]

            disp = player_short_display[player_name]
            td_classes = classes + ["progressionplayername"]
            if disp and disp != player_name:
                self.append_cell(row_number, player_name + " " + disp, classes=td_classes)
            else:
                self.append_cell(row_number, player_name, classes=td_classes)

            self.append_cell(row_number, "", classes=["progressionroundspace"])
            for round_no in round_numbers:
                # First cell: show this player's results in this round,
                # in a highly abbreviated form. Format this differently
                # depending on whether it will be text or HTML.
                text_results = ", ".join([
                    result + " " + player_short_display.get(opponent_name, opponent_name) \
                    for (result, opponent_name, game) in round_player_games.get((round_no, player_name), [])
                ])
                html_results = " ".join([
                    htmlcommon.win_loss_letter_to_html(result, additional_text=player_short_display.get(opponent_name, opponent_name)) + " " \
                    for (result, opponent_name, game) in round_player_games.get((round_no, player_name), [])
                ])
                self.append_cell(row_number, text_results, classes=classes + ["progressiongames"], html_content=html_results)

                # Second and subsequent cells: position, wins, secondary rankers
                standings_row = round_player_standings_row.get((round_no, player_name))
                if standings_row:
                    td_classes = classes + ["progressionstandings"]
                    self.append_cell(row_number, htmlcommon.ordinal_number(standings_row.position), align=ALIGN_RIGHT, classes=td_classes)
                    self.append_cell(row_number, standings_row.get_wins_inc_draws_str(), align=ALIGN_RIGHT, classes=td_classes)
                    sec_rank_strings = standings_row.get_secondary_rank_value_strings()
                    for (idx, val) in enumerate(sec_rank_strings):
                        self.append_cell(row_number, val, align=ALIGN_RIGHT, classes=classes + ["progressionstandings"])
                else:
                    for (idx, val) in enumerate(round_standings_headings):
                        self.append_cell(row_number, "", classes=classes)

                if round_no != round_numbers[-1]:
                    # Don't forget the spacer cell to set this apart from the next round
                    self.append_cell(row_number, "  ", classes=["progressionroundspace"])


class ProgressiveStandings(FormattedTable):
    def __init__(self, tourney: countdowntourney.Tourney, round_standings: dict[int, list[countdowntourney.StandingsRow]], names_to_abbrs=None):
        super().__init__()
        self.table_classes = [ "ranktable", "progressiontable" ]

        # Build a table containing each round's standings table side by side.
        # First, work out how many columns we need for each standings row
        # of each round. This is almost always 4 (position, name, wins, points).
        rank_method = tourney.get_rank_method()
        round_standings_headings = [ "", "", "W" ] + rank_method.get_secondary_rank_headings(short=True)

        # First row: round headings.
        # Second row: labels for standings table columns.
        round_numbers = sorted(list(round_standings))
        col_no = 0
        for round_no in round_standings:
            round_name = tourney.get_round_name(round_no)
            if col_no > 0:
                self.add_vertical_separator(col_no)
            self.append_cell(0, round_name, align=ALIGN_CENTRE, colspan=len(round_standings_headings))
            for (idx, heading) in enumerate(round_standings_headings):
                self.append_cell(1, heading, align=(ALIGN_LEFT if idx == 1 else ALIGN_RIGHT))
            col_no += len(round_standings_headings)
        self.mark_header_row(0)
        self.mark_header_row(1)

        col_no = 0
        for round_no in round_numbers:
            row_number = 2

            standings = round_standings[round_no]
            win_bgcolor_idx = 0
            prev_wins_inc_draws = None
            for (sr_idx, sr) in enumerate(standings):
                if sr.played == 0:
                    # Skip players who hadn't played any games up to this point
                    continue

                wins_inc_draws = sr.get_wins_inc_draws()
                wins_str = sr.get_wins_inc_draws_str()
                if prev_wins_inc_draws is not None and wins_inc_draws != prev_wins_inc_draws:
                    win_bgcolor_idx = (win_bgcolor_idx + 1) % 2

                if len(round_numbers) > 2 and names_to_abbrs and sr.name in names_to_abbrs and sr.name != names_to_abbrs[sr.name]:
                    # This player has an abbreviation that isn't their full name
                    abbr = names_to_abbrs[sr.name]
                    if round_no == round_numbers[0] or round_no == round_numbers[-1]:
                        # This is the first or last round: show the player name
                        # in full, with the abbreviation alongside.
                        player_name = sr.name + " [" + abbr + "]"
                    else:
                        # Use the abbreviation only
                        player_name = "[" + abbr + "]"
                else:
                    player_name = sr.name

                # Make sure we start in the correct column - earlier rounds
                # might have omitted some players who hadn't played any games.
                self.pad_row(row_number, col_no)

                # Show players who have the same number of wins in the same colour
                classes = [ "windifferentiator%d" % (win_bgcolor_idx + 1) ]

                # Append the standings info for this player for this round
                # on to the end of the current table row.
                self.append_cell(row_number, sr.position, align=ALIGN_RIGHT, classes=classes + ["rankpos"])
                self.append_cell(row_number, player_name, classes=classes + ["rankname"])
                self.append_cell(row_number, wins_str, align=ALIGN_RIGHT, classes=classes + ["ranknumber"])
                for val in sr.get_secondary_rank_values():
                    self.append_cell(row_number, str(val), align=ALIGN_RIGHT, classes=classes + ["ranknumber"])
                row_number += 1
                prev_wins_inc_draws = wins_inc_draws
            col_no += len(round_standings_headings)
