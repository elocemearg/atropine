import random
import countdowntourney
import htmlform
import cgi
import gencommon
import fixgen

# Who is "Random", and where is "Seeded Pots"?
name = "Random from Seeded Pots"

description = "Divide the players by rating into pots, the number of pots being the desired group size. Each group contains one randomly-selected player from each pot. If two or more players have the same rating, the player with the lower player ID is rated higher. Any prunes are placed on the highest-numbered tables."

def get_user_form(tourney, settings, div_rounds):
    return gencommon.get_user_form_div_table_size(tourney, settings, div_rounds, include_5and3=False)

def check_ready(tourney, div_rounds):
    return gencommon.check_ready_existing_games_and_table_size(tourney, div_rounds, include_5and3=False)

def generate(tourney, settings, div_rounds):
    (ready, excuse) = check_ready(tourney, div_rounds)
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse)

    generated_groups = fixgen.GeneratedGroups()
    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        players = [ x for x in tourney.get_active_players() if x.get_division() == div_index ]

        table_size = int(settings.get("d%d_groupsize" % (div_index)))
        
        # Put the players in order of rating, from highest to lowest. If two
        # players have the same rating, sort them by player ID (lowest first).
        players = sorted(players, key=lambda x : (x.get_rating(), -x.get_id()), reverse=True)

        if len(players) % table_size != 0:
            raise countdowntourney.FixtureGeneratorException("Well, this is awkward... Division \"%s\" has %d active players, which isn't a multiple of %d." % (tourney.get_division_name(div_index), len(players), table_size))

        pots = [ players[(pot_num * len(players) // table_size):((pot_num+1) * len(players) // table_size)] for pot_num in range(table_size) ]

        tables = []

        # Now randomly shuffle the order of each pot, with the proviso that any
        # prunes go at the end of the list, so they end up on the
        # highest-numbered tables.
        for pot_num in range(table_size):
            prunes = [ p for p in pots[pot_num] if p.get_rating() == 0 ]
            non_prunes = [ p for p in pots[pot_num] if p.get_rating() != 0 ]
            random.shuffle(non_prunes)
            pots[pot_num] = non_prunes + prunes

        # Now distribute the players across the tables
        num_tables = len(players) // table_size

        for table_index in range(num_tables):
            # Each table contains one player from each pot
            tables.append([ pots[pot_num][table_index] for pot_num in range(table_size) ])

        for tab in tables:
            generated_groups.add_group(round_no, div_index, tab)

    return generated_groups

def save_form_on_submit():
    return False
