import countdowntourney
import fixgen
import random

name = "Round Robin"
description = "Pairs only. Every player plays every other player in their division once. We generate N-1 rounds, where N is the number of players in the largest selected division. Smaller selected divisions will sit out later rounds."

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def get_user_form(tourney, settings, div_rounds):
    return None

def check_ready(tourney, div_rounds):
    # Make sure all divisions have an even number of players
    num_divisions = tourney.get_num_divisions()
    players = tourney.get_active_players()
    for div in div_rounds:
        div_players = [x for x in players if x.get_division() == div]
        if len(div_players) < 2:
            if num_divisions == 1:
                div_name = "The tournament"
            else:
                div_name = tourney.get_division_name(div)
            return (False, "%s does not have at least two players (it has %d). The Round Robin generator needs at least two players." % (div_name, len(div_players)))

    # It's not necessary that the games in the previous round have all been
    # completed.

    # It's also not necessary that there's an even number of players in a
    # division. If a division has an odd number of players, then one player
    # will sit out each round.
    return (True, None)

def generate(tourney, settings, div_rounds):
    (ready, excuse) = check_ready(tourney, div_rounds)
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse)

    num_divisions = tourney.get_num_divisions()
    players = tourney.get_active_players()

    generated_groups = fixgen.GeneratedGroups()

    for div in div_rounds:
        div_players = sorted([x for x in players if x.get_division() == div], key=lambda x : x.get_rating(), reverse=True)

        if len(div_players) % 2 == 0:
            # N is even.
            # N players, everyone plays in every round, so N-1 rounds
            num_rounds = len(div_players) - 1
        else:
            # N is odd.
            # N players, everyone sits out a different round, so N rounds.
            num_rounds = len(div_players)

        if num_rounds <= 0:
            # Erm...
            continue

        start_round_no = div_rounds[div]

        # In the classic round robin algorithm where you have an even number
        # of players N, each of whom must play each opponent exactly once, we
        # write the players in two lines like this, as if they're sitting
        # in pairs on opposite sides of N/2 tables, rightwards along the top
        # line then leftwards along the bottom line. Then after each round,
        # keep the top-left player where they are and rotate all the others
        # clockwise.
        #
        # As an example, if N=8, the first round is 0v7, 1v6, 2v5, 3v4:
        #
        # 0 1 2 3
        # 7 6 5 4
        #
        # The full 7-round round-robin looks like this:
        #
        # Round 1   Round 2   Round 3   Round 4   Round 5   Round 6   Round 7
        #
        # 0 1 2 3   0 7 1 2   0 6 7 1   0 5 6 7   0 4 5 6   0 3 4 5   0 2 3 4
        # 7 6 5 4   6 5 4 3   5 4 3 2   4 3 2 1   3 2 1 7   2 1 7 6   1 7 6 5
        #
        # If the number of players is odd, the static position 0 is always
        # occupied by an empty space, and the player sitting opposite that
        # space sits out the round, so it looks like this:
        #
        # Round 1   Round 2   Round 3   Round 4   Round 5   Round 6   Round 7
        #
        # - 0 1 2   - 6 0 1   - 5 6 0   - 4 5 6   - 3 4 5   - 2 3 4   - 1 2 3
        # 6 5 4 3   5 4 3 2   4 3 2 1   3 2 1 0   2 1 0 6   1 0 6 5   0 6 5 4
        #
        # Players can be arbitrarily assigned numbers 0..N-1, then we just need
        # to know who is going first and who's going second in each match.
        #
        # In the following paragraphs, to avoid confusion, I'll call the player
        # on the left of a scoreline "White" (Countdown = "picking first") and
        # the player on the right "Black" (Countdown = "picking second"), to
        # avoid the "P1" and "P2" terminology which will be hopelessly
        # ambiguous having already assigned numbers to all the players.
        #
        # The above rules will make each player play as even as possible a
        # split of White and Black, but it might be that they play White three
        # times in a row and Black four times in a row, which is undesirable.
        # So rather than the top line always being White and the bottom line
        # always being Black, we'll do this:
        #
        #   - The first table switches White/Black order after every round,
        #     otherwise the player at index 0 will always be White.
        #   - The other tables alternate their White/Black top/bottom meanings:
        #   - The second, fourth, sixth etc table define the player on the top
        #     line as Black and the one on the bottom as White.
        #   - The other tables (third, fifth, etc) define the player on the top
        #     line as White and the one on the bottom as Black.

        # These "player numbers" 0..n-1 are assigned to the players at random.
        div_players_random = div_players[:]
        random.shuffle(div_players_random)

        if len(div_players) % 2 == 0:
            top_line = list(range(len(div_players) // 2))
        else:
            # Dummy player in the static top-left position
            top_line = [ None ] + list(range(len(div_players) // 2))
        bottom_line = list(range(len(div_players) - 1, len(div_players) // 2 - 1, -1))
        for round_offset in range(num_rounds):
            # Check there aren't already games in this round for this division
            existing_games = tourney.get_games(round_no=(start_round_no + round_offset), division=div)
            if existing_games:
                raise countdowntourney.FixtureGeneratorException("%s: can't generate fixtures for round %d because there are already %d fixtures for this division in this round." % (tourney.get_division_name(div), start_round_no + round_offset, len(existing_games)))

            tables = []
            for table_index in range(len(top_line)):
                # As explained above, on the first table, the White/Black
                # top/bottom mapping swaps every round, and for the other
                # tables, the second, fourth, sixth etc have Black on top and
                # White on the bottom, while the third, fifth, seventh etc
                # tables have White on the top and Black on the bottom.
                top_is_p2 = (table_index == 0 and round_offset % 2 == 1) or (table_index % 2 == 1)
                if top_is_p2:
                    tables.append((bottom_line[table_index], top_line[table_index]))
                else:
                    tables.append((top_line[table_index], bottom_line[table_index]))
            groups = []
            for (i1, i2) in tables:
                if i1 is not None and i2 is not None:
                    generated_groups.add_group(start_round_no + round_offset, div, (div_players_random[i1], div_players_random[i2]))

            # Take the last element from top_line and put it on the end of
            # bottom_line, and take the first element of bottom_line and put
            # it after the first element of top_line
            bottom_line.append(top_line[-1])
            top_line = [top_line[0]] + [bottom_line[0]] + top_line[1:-1]
            bottom_line = bottom_line[1:]

    return generated_groups

def save_form_on_submit():
    return False
