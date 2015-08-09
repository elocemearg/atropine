import random
import countdowntourney
import htmlform

name = "Random Fixture Generator"
description = """Randomly assign players to tables, without regard for previous
games. No attempt is made to avoid rematches. Patzers, if any, are placed on
the highest numbered tables and are kept separate from each other if possible.
Other than that, the fixtures are random."""

# If this fixture generator is now able to generate a new round without
# any further information from the user, return None.
# Otherwise, return a FixtureForm object for the user to fill in.
# The settings obtained from this should be passed in the dictionary "settings".
# Note that subsequent calls might return further forms, and the settings
# obtained from them should be added to the "settings" dictionary and the
# call made again.
def get_user_form(tourney, settings):
    players = tourney.get_active_players();
    table_size = None
    if settings.get("tablesize", None) is not None:
        try:
            table_size = int(settings.get("tablesize"))
        except ValueError:
            table_size = None

    if table_size is not None:
        if table_size == -5 and len(players) >= 8:
            return None
        elif len(players) % table_size == 0:
            return None

    if table_size is None:
        if len(players) % 3 == 0:
            table_size = 3
        elif len(players) % 2 == 0:
            table_size = 2
        elif len(players) % 5 == 0:
            table_size = 5
        elif len(players) < 8:
            table_size = -5
        elif len(players) % 4 == 0:
            table_size = 4

    table_size_choices = []
    for size in (2,3,4,5):
        if len(players) % size == 0:
            table_size_choices.append(htmlform.HTMLFormChoice(str(size), str(size), table_size == size))
    if len(players) >= 8:
        table_size_choices.append(htmlform.HTMLFormChoice("-5", "5&3", table_size == -5))

    elements = []
    elements.append(htmlform.HTMLFormRadioButton("tablesize", "Players per table", table_size_choices))
    elements.append(htmlform.HTMLFragment("<p>"))
    elements.append(htmlform.HTMLFormSubmitButton("submit", "Generate Fixtures"));
    elements.append(htmlform.HTMLFragment("</p>"))
    form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py", elements)
    return form;

def check_ready(tourney):
    players = tourney.get_active_players();

    for size in (2,3,4,5):
        if len(players) % size == 0:
            break
    else:
        if len(players) < 8:
            return (False, "Number of players (%d) not compatible with any supported table configuration" % (len(players)))

    return (True, None)

# Generate and return a list of fixtures. This function does NOT add them
# to the tourney database. It's the caller's responsibility to do that, and
# it might choose not to, if, for example, the user decides they don't want
# to accept the fixtures.
def generate(tourney, settings):
    players = tourney.get_active_players();

    (ready, excuse) = check_ready(tourney);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    tables = [];
    
    # Randomly shuffle the player list, but always put any patzers at the end
    # of the list. This will ensure they all go on separate tables if possible.
    patzers = [ p for p in players if p.rating == 0 ]
    non_patzers = [ p for p in players if p.rating != 0 ]
    random.shuffle(non_patzers);
    players = non_patzers + patzers

    table_size = int(settings.get("tablesize"))

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

        # Reverse the list so we use the patzers first, and they can go 
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

    fixtures = [];
    current_games = tourney.get_games(game_type='P');
    if len(current_games) == 0:
        max_round_no = 0;
    else:
        max_round_no = max(map(lambda x : x.round_no, current_games));

    round_no = max_round_no + 1;
    fixtures = countdowntourney.make_fixtures_from_groups(tables, round_no, table_size == -5)
    
    d = dict();
    d["fixtures"] = fixtures;
    d["rounds"] = [{
        "round": round_no,
        "name": "Round %d" % round_no,
        "type": "P"
    }];
    return d;
