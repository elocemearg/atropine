import random
import time
import countdowntourney
import htmlform
import cgi
import gencommon
import fixgen

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
    elements.append(htmlform.HTMLFragment("<p>"))
    elements.append(htmlform.HTMLFormCheckBox("avoidrematches", "Avoid rematches", bool(settings.get("avoidrematches", True))))
    elements.append(htmlform.HTMLFragment("</p>"))
    return gencommon.get_user_form_div_table_size(tourney, settings, div_rounds, True, elements)

def check_ready(tourney, div_rounds):
    return gencommon.check_ready_existing_games_and_table_size(tourney, div_rounds)


def random_without_rematches_aux(tables, players, player_indices_remaining, table_sizes, potential_opponents, id_to_index, start_time, time_limit_ms):
    if len(player_indices_remaining) == 0:
        return tables

    if time.time() > start_time + time_limit_ms / 1000.0:
        raise countdowntourney.FixtureGeneratorException("Timed out before finding a set of fixtures with no rematches.")

    # Find the first table without its full complement of players
    table_index = 0
    while table_index < len(tables):
        if len(tables[table_index]) < table_sizes[table_index]:
            break
        else:
            table_index += 1

    if table_index >= len(tables):
        return tables

    # Put the remaining players in a random order
    player_indices_remaining_shuffled = player_indices_remaining[:]
    random.shuffle(player_indices_remaining_shuffled)

    # Starting with the first player in the shuffled list, try to place that
    # player on this table. If we can't, try to place the next player here, and
    # so on, until we find something that works or we run out of options.
    for player_index in player_indices_remaining_shuffled:
        tables_copy = []
        for t in tables:
            tables_copy.append(t[:])

        for opponent in tables[table_index]:
            opp_index = id_to_index.get(opponent.get_id())
            if opp_index is not None:
                if opp_index not in potential_opponents[player_index]:
                    break;
        else:
            # This player hasn't played anyone on this table. Place them
            # here, and recurse to place the remaining players.
            tables_copy[table_index].append(players[player_index])
            new_player_indices_remaining = player_indices_remaining[:]
            new_player_indices_remaining.remove(player_index)

            finished_tables = random_without_rematches_aux(tables_copy,
                    players, new_player_indices_remaining, table_sizes,
                    potential_opponents, id_to_index, start_time, time_limit_ms)
            if finished_tables:
                # We have a complete solution
                return finished_tables

    # We can't place any player on this table without either having them play
    # someone they've played before, or forcing a rematch later in the
    # recursive process, so the task is impossible.
    return None


def random_without_rematches(players, table_sizes, previous_games, time_limit_ms):
    tables = [ [] for x in table_sizes ]

    id_to_index = {}
    for pi in range(len(players)):
        id_to_index[players[pi].get_id()] = pi

    # For each index into "player", make a list of potential opponents
    potential_opponents = {}
    for pi in range(len(players)):
        potential_opponents[pi] = set([ opp for opp in range(len(players)) if opp != pi ])

    prunes = [ p for p in players if p.is_prune() ]
    non_prunes = [ p for p in players if not p.is_prune() ]

    for g in previous_games:
        game_players = g.get_players()
        pi0 = id_to_index.get(game_players[0].get_id())
        pi1 = id_to_index.get(game_players[1].get_id())

        if pi0 is not None and pi1 is not None:
            potential_opponents[pi0].discard(pi1)
            potential_opponents[pi1].discard(pi0)

            # If a player has played a prune, behave as if they've played all
            # the prunes
            if game_players[0].is_prune() or game_players[1].is_prune():
                for p in prunes:
                    prune_index = id_to_index.get(p.get_id())
                    potential_opponents[pi0].discard(prune_index)
                    potential_opponents[pi1].discard(prune_index)
                    potential_opponents[prune_index].discard(pi0)
                    potential_opponents[prune_index].discard(pi1)

    # First, put the prunes on separate tables.
    for i in range(len(prunes)):
        tables[i % len(tables)].append(prunes[i])

    player_indices_remaining = [ id_to_index[p.get_id()] for p in non_prunes ]
    return random_without_rematches_aux(tables, players, player_indices_remaining, table_sizes, potential_opponents, id_to_index, time.time(), time_limit_ms)


# Generate and return a list of fixtures. This function does NOT add them
# to the tourney database. It's the caller's responsibility to do that, and
# it might choose not to, if, for example, the user decides they don't want
# to accept the fixtures.
def generate(tourney, settings, div_rounds):
    (ready, excuse) = check_ready(tourney, div_rounds);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    avoid_rematches = bool(settings.get("avoidrematches", False))

    generated_groups = fixgen.GeneratedGroups()

    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        players = [x for x in tourney.get_active_players() if x.get_division() == div_index];
        tables = [];
        table_size = int(settings.get("d%d_groupsize" % (div_index)))
        (table_sizes, prunes_required) = gencommon.get_table_sizes(len(players), table_size)

        for i in range(prunes_required):
            players.append(tourney.get_auto_prune())

        if avoid_rematches:
            tables = random_without_rematches(players, table_sizes, tourney.get_games(game_type="P"), 10000)

            if not tables:
                raise countdowntourney.FixtureGeneratorException("Failed to find a set of fixtures with no rematches.")

            # Put any Pruney tables at the end
            tables.reverse()
        else:
            # Randomly shuffle the player list, but always put any prunes at the
            # end of the list. This will ensure they all go on separate tables
            # if possible, if the tables are the same size. If we're using the
            # weird 5&3 thing then we don't need Prunes anyway.
            prunes = [ p for p in players if p.is_prune() ]
            non_prunes = [ p for p in players if not p.is_prune() ]
            random.shuffle(non_prunes);
            players = non_prunes + prunes

            tables = []
            for x in table_sizes:
                tables.append([])

            # If the tables are of unequal size, put the large tables first.
            table_sizes.sort(reverse=True)

            # Distribute the players amongst the tables. Deal them like cards
            # rather than cutting the pack, otherwise we'll end up with all
            # the prunes on the last table.
            ti = 0
            for p in players:
                orig_ti = ti
                # Put this player on the next table which has space
                while len(tables[ti]) >= table_sizes[ti]:
                    ti = (ti + 1) % len(table_sizes)
                    if ti == orig_ti:
                        # We shouldn't go into an infinite loop, but if we
                        # do, then it means the sum of all the values in
                        # table_sizes is less than the number of players we
                        # have, which shouldn't have happened.
                        raise countdowntourney.FixtureGeneratorException("I didn't set up the tables correctly and now I don't have enough spaces for the players. This is my problem. It's a bug in Atropine. Please report it.")
                tables[ti].append(p)
                ti = (ti + 1) % len(table_sizes)

        for tab in tables:
            generated_groups.add_group(round_no, div_index, tab)

        generated_groups.set_repeat_threes(round_no, div_index, table_size == -5)

    return generated_groups

def save_form_on_submit():
    return False
