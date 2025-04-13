#!/usr/bin/python3

import io

import countdowntourney
import htmlcommon

ALIGN_NONE = 0
ALIGN_LEFT = 1
ALIGN_CENTRE = 2
ALIGN_RIGHT = 3

ALIGN_CSS_VALUES = [ "none", "left", "center", "right" ]
ALIGN_FORMATS = [ "", "<", "^", ">" ]

class FormattedTableCell(object):
    def __init__(self, content, align=ALIGN_NONE, colspan=1, classes=[]):
        self.content = str(content)
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
        out.write(htmlcommon.escape(self.content))
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

    def append_cell(self, row_number, content, align=ALIGN_NONE, colspan=1, classes=[]):
        self._append_cell(row_number, FormattedTableCell(content, align=align, colspan=colspan, classes=classes))

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


class ProgressiveStandings(FormattedTable):
    def __init__(self, tourney: countdowntourney.Tourney, round_standings: dict[int, list[countdowntourney.StandingsRow]]):
        super().__init__()
        self.table_classes = [ "ranktable" ]

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

                # Make sure we start in the correct column - earlier rounds
                # might have omitted some players who hadn't played any games.
                self.pad_row(row_number, col_no)

                # Show players who have the same number of wins in the same colour
                classes = [ "windifferentiator%d" % (win_bgcolor_idx + 1) ]

                # Append the standings info for this player for this round
                # on to the end of the current table row.
                self.append_cell(row_number, sr.position, align=ALIGN_RIGHT, classes=classes + ["rankpos"])
                self.append_cell(row_number, sr.name, classes=classes + ["rankname"])
                self.append_cell(row_number, wins_str, align=ALIGN_RIGHT, classes=classes + ["ranknumber"])
                for val in sr.get_secondary_rank_values():
                    self.append_cell(row_number, str(val), align=ALIGN_RIGHT, classes=classes + ["ranknumber"])
                row_number += 1
                prev_wins_inc_draws = wins_inc_draws
            col_no += len(round_standings_headings)
