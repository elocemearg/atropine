import random
import countdowntourney
import htmlform
import cgi
import gencommon

name = "Random Pairings/Groups"
description = """Randomly assign players to tables, without regard for previous
games. No attempt is made to avoid rematches. Prunes, if any, are placed on
the highest numbered tables and are kept separate from each other if possible.
Other than that, the fixtures are random."""

# If this fixture generator is now able to generate a new round without
# any further information from the user, return None.
# Otherwise, return a FixtureForm object for the user to fill in.
# The settings obtained from this should be passed in the dictionary "settings".
# Note that subsequent calls might return further forms, and the settings
# obtained from them should be added to the "settings" dictionary and the
# call made again.
def get_user_form(tourney, settings, div_rounds):
    return gencommon.get_user_form_div_table_size(tourney, settings, div_rounds)

def check_ready(tourney, div_rounds):
    return gencommon.check_ready_existing_games_and_table_size(tourney, div_rounds)

# Generate and return a list of fixtures. This function does NOT add them
# to the tourney database. It's the caller's responsibility to do that, and
# it might choose not to, if, for example, the user decides they don't want
# to accept the fixtures.
def generate(tourney, settings, div_rounds):
    (ready, excuse) = check_ready(tourney, div_rounds);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    fixtures = [];
    round_numbers_generated = []
    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        players = filter(lambda x : x.get_division() == div_index, tourney.get_active_players());

        tables = [];
        
        # Randomly shuffle the player list, but always put any prunes at the
        # end of the list. This will ensure they all go on separate tables if
        # possible.
        prunes = [ p for p in players if p.rating == 0 ]
        non_prunes = [ p for p in players if p.rating != 0 ]
        random.shuffle(non_prunes);
        players = non_prunes + prunes

        table_size = int(settings.get("d%d_groupsize" % (div_index)))

        if table_size > 0:
            # Distribute the players across the tables
            num_tables = len(players) / table_size;
            tables = [ [] for i in range(num_tables) ]
            table_no = 0
            for p in players:
                tables[table_no].append(p)
                table_no = (table_no + 1) % num_tables
        elif table_size == -5:
            # Have as many tables of 3 as required to take the number of players
            # remaining to a multiple of 5, then put the remaining players on
            # tables of 5.
            table_sizes = []
            players_left = len(players)
            while players_left % 5 != 0:
                table_sizes.append(3)
                players_left -= 3
            for i in range(players_left / 5):
                table_sizes.append(5)
            tables = [ [] for x in table_sizes ]

            # Reverse the list so we use the prunes first, and they can go 
            # on the 3-tables
            players.reverse()

            table_pos = 0
            for p in players:
                iterations = 0
                while len(tables[table_pos]) >= table_sizes[table_pos]:
                    table_pos = (table_pos + 1) % len(tables)
                    iterations += 1
                    assert(iterations <= len(tables))
                tables[table_pos].append(p)
                table_pos = (table_pos + 1) % len(tables)

            # Reverse the table list so the 5-tables are first
            tables.reverse()

        fixtures += tourney.make_fixtures_from_groups(tables, fixtures, round_no, table_size == -5, division=div_index)
        if round_no not in round_numbers_generated:
            round_numbers_generated.append(round_no)
    
    d = dict();
    d["fixtures"] = fixtures;
    d["rounds"] = [{
        "round": round_no,
        "name": "Round %d" % round_no
    } for round_no in round_numbers_generated ];
    return d;

def save_form_on_submit():
    return False
