import random
import countdowntourney
import htmlform

name = "Random Fixture Generator";
description = "Randomly distribute players between tables, without regard for previous results.";

# If this fixture generator is now able to generate a new round without
# any further information from the user, return None.
# Otherwise, return a FixtureForm object for the user to fill in.
# The settings obtained from this should be passed in the dictionary "settings".
# Note that subsequent calls might return further forms, and the settings
# obtained from them should be added to the "settings" dictionary and the
# call made again.
def get_user_form(tourney, settings):
    players = tourney.get_players();
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
    players = tourney.get_players();

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
    players = tourney.get_players();

    (ready, excuse) = check_ready(tourney);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    tables = [];
    random.shuffle(players);

    table_size = int(settings.get("tablesize"))

    if table_size > 0:
        num_tables = len(players) / table_size;
        for table_no in range(0, num_tables):
            table = [];
            for i in range(0, table_size):
                table.append(players[table_no * table_size + i]);
            tables.append(table);
    elif table_size == -5:
        players_left = len(players)
        player_pos = 0
        while players_left % 5 != 0:
            table = []
            for i in range(0, 3):
                table.append(players[player_pos + i])
            player_pos += 3
            players_left -= 3
            tables.append(table)
        while players_left > 0:
            table = []
            for i in range(0, 5):
                table.append(players[player_pos + i])
            player_pos += 5
            players_left -= 5
            tables = [table] + tables

    fixtures = [];
    current_games = tourney.get_games(game_type='P');
    if len(current_games) == 0:
        max_round_no = 0;
    else:
        max_round_no = max(map(lambda x : x.round_no, current_games));

    round_no = max_round_no + 1;
    #table_no = 1;
    #round_seq = 1;
    fixtures = countdowntourney.make_fixtures_from_groups(tables, round_no, table_size == -5)
    #for table in tables:
    #    for i in range(0, len(table)):
    #        for j in range(i + 1, len(table)):
    #            p1 = table[i];
    #            p2 = table[j];
    #            if (i + j) % 2 == 0:
    #                (p1, p2) = (p2, p1);
    #            fixture = countdowntourney.Game(round_no, round_seq, table_no, 'P', p1, p2);
    #            fixtures.append(fixture);
    #            round_seq += 1;
    #    table_no += 1;
    
    d = dict();
    d["fixtures"] = fixtures;
    d["rounds"] = [{
        "round": round_no,
        "name": "Round %d" % round_no,
        "type": "P"
    }];
    return d;
