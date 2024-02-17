import random
import itertools

import countdowntourney
import htmlform
import gencommon
import fixgen
import randomdraw

name = "Random Pairings/Groups"
description = """Randomly assign players to tables, avoiding rematches if
required. Prunes, if any, are placed on the highest numbered tables and are
kept separate from each other if possible."""

# If this fixture generator is now able to generate a new round without
# any further information from the user, return None.
# Otherwise, return a FixtureForm object for the user to fill in.
# The settings obtained from this should be passed in the dictionary "settings".
# Note that subsequent calls might return further forms, and the settings
# obtained from them should be added to the "settings" dictionary and the
# call made again.
def get_user_form(tourney, settings, div_rounds):
    elements = []
    constraint_choices = []

    # User can choose to avoid rematches, or to avoid all-newbie tables, but
    # not both. Very likely you will only be using the Random fixture generator
    # in round 1 anyway, and if you're using it in later rounds there isn't
    # much point requiring a non-newbie on each table because everybody has
    # now played a game.
    if tourney.get_num_games(game_type="P") > 0:
        # If games have been played, offer to avoid rematches
        constraint_choices.append(htmlform.HTMLFormChoice("avoidrematches", "Do not allow rematches", selected=True))
    if tourney.has_player_newbie_feature() and tourney.get_active_newbie_count() > 0:
        # If there are newbies, offer to avoid all-newbie tables
        constraint_choices.append(htmlform.HTMLFormChoice("avoidallnewbietables", "Put at least one non-newbie on each table", selected=(len(constraint_choices) == 0)))

    # If either of the above are true, draw some radio buttons
    if constraint_choices:
        constraint_choices = [ htmlform.HTMLFormChoice("none", "None", selected=False) ] + constraint_choices
        radio_button = htmlform.HTMLFormRadioButton("constraint", "Special constraints:", constraint_choices)
        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(radio_button)
        elements.append(htmlform.HTMLFragment("</p>"))
    return gencommon.get_user_form_div_table_size(tourney, settings, div_rounds, True, elements)

def check_ready(tourney, div_rounds):
    return gencommon.check_ready_existing_games_and_table_size(tourney, div_rounds)


def random_without_rematches(players, table_sizes, previous_games, time_limit_ms):
    # Prunes have already been added to "players" so we have the right number
    # for the required table sizes. We'll just check this...
    assert(len(players) == sum(table_sizes))

    # We represent each player by their index in "players". invalid_pairs is
    # a list of player indexes (x, y), representing pairs of players who have
    # already played each other.
    invalid_pairs = []

    # Build a map: { player ID -> index into players array }
    id_to_index = {}
    for pi in range(len(players)):
        id_to_index[players[pi].get_id()] = pi

    # The prunes will probably all have the same player ID, so
    # id_to_index[prune_id] will only refer to one index. Build a set of all
    # the array indices which have prunes.
    prune_indices = set()
    for (i, p) in enumerate(players):
        if p.is_prune():
            prune_indices.add(i)

    # Add to invalid_pairs details of who's played whom so far. If a player has
    # played a prune, we need to add an entry for every slot in "players" in
    # which a prune appears.
    for g in previous_games:
        gp = g.get_players()

        # For this game, get each player's index in the "players" array.
        pi0 = id_to_index.get(gp[0].get_id())
        pi1 = id_to_index.get(gp[1].get_id())

        if pi0 is None or pi1 is None:
            # This game involves a player who isn't playing in this round, so
            # there's no danger of the other player playing them again.
            # Ignore this game.
            continue
        if pi0 in prune_indices:
            # pi0 is a Prune; prevent pi1 from playing any Prune
            for prune_index in prune_indices:
                invalid_pairs.append((prune_index, pi1))
        elif pi1 in prune_indices:
            # pi1 is a Prune; prevent pi0 from playing any Prune
            for prune_index in prune_indices:
                invalid_pairs.append((pi0, prune_index))
        else:
            invalid_pairs.append((pi0, pi1))

    # Also add every pair of prunes to this list, so that all prunes go on
    # separate tables.
    if len(prune_indices) >= 2:
        for (x, y) in itertools.combinations(list(prune_indices), 2):
            invalid_pairs.append((x, y))

    try:
        # Get a list of lists of player indices which fit these requirements.
        (tables_nums, search_required) = randomdraw.draw(table_sizes, invalid_pairs, search_time_limit_ms=time_limit_ms)
    except randomdraw.RandomDrawTimeoutException:
        raise countdowntourney.FixtureGeneratorException("Timed out: failed to find an acceptable set of fixtures within the time limit.")
    if tables_nums is None:
        # No solution found!
        raise countdowntourney.FixtureGeneratorException("Failed to find any set of fixtures%s." % (" without rematches" if previous_games else ""))

    # Convert it to a list of lists of players...
    tables = []
    for t in tables_nums:
        tables.append([ players[i] for i in t ])

    return tables


# If there are any tables containing all newbies, we don't want that, so
# suitably redistribute the newbies in a random fashion.
# tables is a list of lists of Player objects, where every player playing in
# this round appears in one of the lists.
def redistribute_newbies(tables):
    # table_newbie_spaces: the number of additional newbies this table could accommodate.
    # An all-newbie table has a count of -1. A table with only one non-newbie
    # on it cannot have that non-newbie swapped for a newbie so the count is 0.
    table_newbie_spaces = []
    for t in tables:
        table_newbie_spaces.append(len([ p for p in t if not p.is_prune() and not p.is_newbie() ]) - 1)

    # We shouldn't get as far as redistribute_newbies() if there aren't enough
    # non-newbies in the first place.
    assert(sum(table_newbie_spaces) >= 0)

    for table_idx in range(len(tables)):
        if table_newbie_spaces[table_idx] < 0:
            assert(table_newbie_spaces[table_idx] == -1)
            # Swap a random newbie on this table with a random non-newbie on
            # a random other table which currently has >= 2 non-newbies on it.
            newbie_idx = random.randint(0, len(tables[table_idx]) - 1)

            # Choose a random other table which has space for >= 1 newbie
            other_table_idx = random.choice([i for i in range(len(tables)) if table_newbie_spaces[i] >= 1 ])

            # Choose a random non-newbie on that table
            other_table_non_newbie_indexes = [ i for i in range(len(tables[other_table_idx])) if not tables[other_table_idx][i].is_prune() and not tables[other_table_idx][i].is_newbie() ]
            other_table_player_idx = random.choice(other_table_non_newbie_indexes)

            # Swap that non-newbie for the newbie on this table
            tmp = tables[table_idx][newbie_idx]
            tables[table_idx][newbie_idx] = tables[other_table_idx][other_table_player_idx]
            tables[other_table_idx][other_table_player_idx] = tmp
            table_newbie_spaces[table_idx] += 1
            table_newbie_spaces[other_table_idx] -= 1

# Generate and return a list of fixtures. This function does NOT add them
# to the tourney database. It's the caller's responsibility to do that, and
# it might choose not to, if, for example, the user decides they don't want
# to accept the fixtures.
def generate(tourney, settings, div_rounds):
    (ready, excuse) = check_ready(tourney, div_rounds);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    constraint = settings.get("constraint", "none")
    avoid_rematches = (constraint == "avoidrematches")
    avoid_all_newbie_tables = (constraint == "avoidallnewbietables")

    generated_groups = fixgen.GeneratedGroups()

    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        players = [x for x in tourney.get_active_players() if x.get_division() == div_index];
        tables = [];
        table_size = int(settings.get("d%d_groupsize" % (div_index)))
        (table_sizes, prunes_required) = gencommon.get_table_sizes(len(players), table_size)

        if avoid_all_newbie_tables:
            # Guarantee that every table has at least one newbie on it.
            # Before we start, check that this is actually possible!
            # Prune counts as a newbie: a table with two newbies and one Prune
            # on it should be counted as an all-newbie table.
            num_newbies = len([ p for p in players if p.is_newbie() ]) + prunes_required
            num_spaces_for_newbies = sum([ n - 1 for n in table_sizes ])
            if num_newbies > num_spaces_for_newbies:
                div_str = "" if len(div_rounds) == 1 else tourney.get_division_name(div_index) + ": "
                raise countdowntourney.FixtureGeneratorException(div_str + "There are not enough non-newbies to have at least one on every table!")

        # Add any necessary prunes
        for i in range(prunes_required):
            players.append(tourney.get_auto_prune())

        # Total number of auto and non-auto prunes (if anyone still uses non-auto prunes?)
        num_prunes = len([ p for p in players if p.is_prune() ])

        if avoid_rematches:
            tables = random_without_rematches(players, table_sizes, tourney.get_games(game_type="P"), 10000)

            if not tables:
                raise countdowntourney.FixtureGeneratorException("Failed to find a set of fixtures with no rematches.")
        else:
            # Use random_without_rematches(), but give it no rematches.
            tables = random_without_rematches(players, table_sizes, [], 10000)
            if avoid_all_newbie_tables:
                # If there are any all-newbie tables, swap them with random
                # non-newbies on other tables so that every table has at least
                # one non-newbie on it.
                redistribute_newbies(tables)

        # If there are Prunes, put the Pruney tables last. Otherwise, put the
        # tables in order of size if they're not all the same size.
        if num_prunes > 0:
            prune_tables = []
            non_prune_tables = []
            for t in tables:
                for p in t:
                    if p.is_prune():
                        prune_tables.append(t)
                        break
                else:
                    non_prune_tables.append(t)
            tables = non_prune_tables + prune_tables
        else:
            tables.sort(key=lambda x : len(x))

        for tab in tables:
            generated_groups.add_group(round_no, div_index, tab)

        generated_groups.set_repeat_threes(round_no, div_index, table_size == -5)

    return generated_groups

def save_form_on_submit():
    return False
