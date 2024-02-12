import random
import countdowntourney
import htmlform
import gencommon
import fixgen

# Who is "Random", and where is "Seeded Pots"?
name = "Random from Seeded Pots"

description = "Divide the players by rating into pots, the number of pots being the desired group size. Each group contains one randomly-selected player from each pot, thus keeping the highest-rated players apart. Any prunes are placed on the highest-numbered tables."

def get_user_form(tourney, settings, div_rounds):
    if tourney.get_active_newbie_count() > 0:
        elements = [
            htmlform.HTMLFragment("<p>"),
            htmlform.HTMLFormCheckBox("avoidallnewbietables", "Put at least one non-newbie on each table", True),
            htmlform.HTMLFragment("</p>")
        ]
    else:
        elements = []
    return gencommon.get_user_form_div_table_size(tourney, settings, div_rounds, include_5and3=False, additional_elements=elements)

def check_ready(tourney, div_rounds):
    players = tourney.get_active_players()
    num_divs = tourney.get_num_divisions()
    for div_index in div_rounds:
        div_players = [ p for p in players if p.get_division() == div_index ]
        prev_rating = None
        for p in div_players:
            rating = p.get_rating()
            if not p.is_prune():
                if prev_rating is None:
                    prev_rating = rating
                elif rating != prev_rating:
                    # We've found two non-Pruney players with different
                    # ratings, so we know we're not in the unfortunate
                    # situation where the user has selected the Random from
                    # Seeded Pots generator but forgotten to set any ratings
                    break
        else:
            reason = ""
            if num_divs > 1:
                reason += tourney.get_division_name(div_index) + ": "
            reason += "All players have the same rating, so the Random from Seeded Pots generator isn't much use to you. Try the Random fixture generator instead, or give the players ratings. Perhaps you need to select the option labelled \"This player list is in rating order\" on the Tourney Setup page?"
            return (False, reason)
    return gencommon.check_ready_existing_games_and_table_size(tourney, div_rounds, include_5and3=False)

def generate(tourney, settings, div_rounds):
    (ready, excuse) = check_ready(tourney, div_rounds)
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse)

    avoid_all_newbie_tables = bool(settings.get("avoidallnewbietables", False))

    generated_groups = fixgen.GeneratedGroups()
    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        players = [ x for x in tourney.get_active_players() if x.get_division() == div_index ]

        table_size = int(settings.get("d%d_groupsize" % (div_index)))

        # Put the players in order of rating, from highest to lowest. If two
        # players have the same rating, sort them by player ID (lowest first).
        players = sorted(players, key=lambda x : (x.get_rating(), -x.get_id()), reverse=True)

        if len(players) % table_size != 0:
            # Make the length of the "players" list a multiple of table_size
            if tourney.has_auto_prune():
                gencommon.add_auto_prunes(tourney, players, table_size)
            else:
                raise countdowntourney.FixtureGeneratorException("Well, this is awkward... Division \"%s\" has %d active players, which isn't a multiple of %d." % (tourney.get_division_name(div_index), len(players), table_size))

        # If we've been asked to ensure each table contains at least one
        # non-newbie, check that that's possible first. The number of
        # non-newbies must be at least the number of tables.
        if avoid_all_newbie_tables:
            # The players list may contain Prunes, which are treated as
            # newbies for this calculation.
            num_non_newbies = len([p for p in players if not p.is_prune() and not p.is_newbie() ])
            if num_non_newbies < len(players) // table_size:
                div_str = "" if len(div_rounds) == 1 else tourney.get_division_name(div_index) + ": "
                raise countdowntourney.FixtureGeneratorException(div_str + "There are not enough non-newbies to have at least one on every table!")

        # Now randomly distribute the players amongst the tables, subject to:
        #   1. Each table must contain one player from each pot.
        #   2. If avoid_all_newbie_tables, every table must contain at least
        #      one non-newbie human player.

        # { player_id -> pot [0, num_tables) }
        player_id_to_pot = {}
        assert(len(players) % table_size == 0)
        pot_size = len(players) // table_size
        for i in range(len(players)):
            player_id_to_pot[players[i].get_id()] = i // pot_size

        if avoid_all_newbie_tables:
            non_newbies = [ p for p in players if not p.is_prune() and not p.is_newbie() ]
            newbies = [ p for p in players if p.is_newbie() or p.is_prune() ]
        else:
            # If avoid_all_newbie_tables is not set, treat everyone as a non-newbie.
            non_newbies = players[:]
            newbies = []

        # Initialise "tables", a 2D array, one element for each table, each
        # of which has table_size players in it. At first, each table in tables
        # is a table_size-length array of None values.
        num_tables = pot_size
        tables = []
        for t in range(num_tables):
            tables.append([ None for i in range(table_size) ])

        # Place the non-newbies, in a random order, followed by the newbies
        # in a random order.
        #
        # For the first table_size players in the non_newbies list, put each
        # player on the first table which has no non-newbies on it. This
        # ensures each table gets a non-newbie.
        #
        # Always put the player in their correct pot, and after the first
        # table_size players, put each player on the first table that doesn't
        # yet have a player of their pot on it.
        random.shuffle(non_newbies)
        random.shuffle(newbies)
        num_players_placed = 0
        for p in non_newbies + newbies:
            pot = player_id_to_pot[p.get_id()]
            if num_players_placed < num_tables:
                table_idx = num_players_placed
            else:
                table_idx = 0
                while table_idx < num_tables and tables[table_idx][pot] is not None:
                    table_idx += 1
                assert(table_idx < num_tables)
            assert(tables[table_idx][pot] is None)
            tables[table_idx][pot] = p
            num_players_placed += 1

        # We now know who is playing whom.
        # Finally, rearrange the list of tables so tha tables which contain a
        # Prune are at the end of the list.
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

        # Sanity check that what we've generated satisfies the requirements...
        if avoid_all_newbie_tables:
            for t in tables:
                for p in t:
                    if not p.is_newbie() and not p.is_prune():
                        break
                else:
                    # Oops
                    raise countdowntourney.FixtureGeneratorException("Internal error: I've accidentally generated a table with all newbies on it. This is a bug. Table: %s" % ( ", ".join([ p.get_name() for p in t ])))
        for t in tables:
            for (pot, p) in enumerate(t):
                if pot != player_id_to_pot[p.get_id()]:
                    raise countdowntourney.FixtureGeneratorException("Internal error: I've accidentally generated a table which doesn't have one player from each pot. This is a bug. Table: %s" % (", ".join([x.get_name() for x in t])))

        for tab in tables:
            generated_groups.add_group(round_no, div_index, tab)

    return generated_groups

def save_form_on_submit():
    return False
