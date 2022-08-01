#!/usr/bin/env python3

import os
import sys

sys.path.append("py")

import countdowntourney

verbose = False

tests = [
    {
        "name" : "ranktest_wins_points",
        "player_names" : [ "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliet", "Kilo", "Prune" ],
        "games_per_round" : {
            1 : [
                (1, "Alpha", 60, "Echo", 40),
                (1, "Echo", 41, "India", 31),
                (1, "India", 58, "Alpha", 68, True),
                (2, "Bravo", 46, "Foxtrot", 31),
                (2, "Foxtrot", 37, "Juliet", 30),
                (2, "Juliet", 60, "Bravo", 55),
                (3, "Charlie", 45, "Golf", 59),
                (3, "Golf", 72, "Kilo", 52),
                (3, "Kilo", 50, "Charlie", 51),
                (4, "Delta", 60, "Hotel", 30),
                (4, "Hotel", 66, "Prune", 0),
                (4, "Prune", 0, "Delta", 70)
            ],
            2 : [
                (1, "Golf", 50, "Delta", 60),
                (1, "Delta", 65, "Alpha", 45),
                (1, "Alpha", 49, "Golf", 41),
                (2, "Bravo", 56, "Charlie", 52),
                (2, "Charlie", 61, "Hotel", 41),
                (2, "Hotel", 49, "Bravo", 37),
                (3, "Juliet", 50, "Echo", 60),
                (3, "Echo", 53, "Foxtrot", 44),
                (3, "Foxtrot", 25, "Juliet", 57),
                (4, "Kilo", 49, "India", 47),
                (4, "India", 56, "Prune", 0),
                (4, "Prune", 0, "Kilo", 58),
            ],
            3 : [
                (1, "Delta", 72, "Alpha", 62),
                (1, "Alpha", 58, "Echo", 47),
                (1, "Echo", 41, "Delta", 68),
                (2, "Golf", 50, "Charlie", 60, True),
                (2, "Charlie", 56, "Kilo", 30),
                (2, "Kilo", 41, "Golf", 47),
                (3, "Juliet", 41, "Bravo", 49),
                (3, "Bravo", 40, "Hotel", 50),
                (3, "Hotel", 54, "Juliet", 55),
                (4, "India", 40, "Foxtrot", 53),
                (4, "Foxtrot", 60, "Prune", 0),
                (4, "Prune", 0, "India", 70),
            ]
        },
        "standings_per_round" : {
            1 : [
                ( 1, "Golf",    2, 2, 131),
                ( 2, "Delta",   2, 2, 130),
                ( 3, "Alpha",   2, 2, 118),
                ( 4, "Bravo",   2, 1, 101),
                ( 5, "Charlie", 2, 1,  96),
                ( 5, "Hotel",   2, 1,  96),
                ( 7, "Juliet",  2, 1,  90),
                ( 8, "Echo",    2, 1,  81),
                ( 9, "Foxtrot", 2, 1,  68),
                (10, "Kilo",    2, 0, 102),
                (11, "India",   2, 0,  89),
                (12, "Prune",   2, 0,   0),
            ],
            2 : [
                ( 1, "Delta",   4, 4, 255),
                ( 2, "Alpha",   4, 3, 212),
                ( 3, "Echo",    4, 3, 194),
                ( 4, "Golf",    4, 2, 222),
                ( 5, "Charlie", 4, 2, 209),
                ( 5, "Kilo",    4, 2, 209),
                ( 7, "Juliet",  4, 2, 197),
                ( 8, "Bravo",   4, 2, 194),
                ( 9, "Hotel",   4, 2, 186),
                (10, "India",   4, 1, 192),
                (11, "Foxtrot", 4, 1, 137),
                (12, "Prune",   4, 0,   0),
            ],
            3 : [
                ( 1, "Delta",   6, 6, 395),
                ( 2, "Alpha",   6, 4, 332),
                ( 3, "Charlie", 6, 4, 315),
                ( 4, "Golf",    6, 3, 319),
                ( 5, "Juliet",  6, 3, 293),
                ( 6, "Hotel",   6, 3, 290),
                ( 7, "Bravo",   6, 3, 283),
                ( 8, "Echo",    6, 3, 282),
                ( 9, "Foxtrot", 6, 3, 250),
                (10, "India",   6, 2, 302),
                (11, "Kilo",    6, 2, 280),
                (12, "Prune",   6, 0,   0),
            ]
        },
        "rank" : countdowntourney.RANK_WINS_POINTS
    },
    {
        "name" : "ranktest_neustadtl",
        "player_names" : [ "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliet", "Kilo", "Prune" ],
        "rank" : countdowntourney.RANK_WINS_NEUSTADTL,
        "games_per_round" : {
            1 : [
                (1, "Alpha", 60, "Echo", 40),
                (1, "Echo", 41, "India", 31),
                (1, "India", 75, "Alpha", 75),
                (2, "Bravo", 46, "Foxtrot", 31),
                (2, "Foxtrot", 37, "Juliet", 30),
                (2, "Juliet", 60, "Bravo", 55),
                (3, "Charlie", 45, "Golf", 59),
                (3, "Golf", 72, "Kilo", 52),
                (3, "Kilo", 50, "Charlie", 51),
                (4, "Delta", 60, "Hotel", 30),
                (4, "Hotel", 66, "Prune", 0),
                (4, "Prune", 0, "Delta", 70)
            ],
            # Defeated opponents after round 1:
            # Alpha:    Echo, India(D)
            # Bravo:    Foxtrot
            # Charlie:  Kilo
            # Delta:    Hotel, Prune
            # Echo:     India
            # Foxtrot:  Juliet
            # Golf:     Charlie, Kilo
            # Hotel:    Prune
            # India:    Alpha(D)
            # Juliet:   Bravo
            # Kilo:
            # Prune:
            # Hotel withdraws, Prune II is added.
            # Anyone who beat Hotel in the first round has their Neustadtl
            # score calculated as if Hotel drew their missing games.
            2 : [
                (1, "Golf", 56, "Delta", 72),
                (1, "Delta", 61, "Alpha", 50),
                (1, "Alpha", 54, "Golf", 39),
                (2, "Bravo", 49, "Juliet", 32),
                (2, "Juliet", 44, "Foxtrot", 40),
                (2, "Foxtrot", 40, "Bravo", 66),
                (3, "Echo", 62, "Charlie", 52),
                (3, "Charlie", 65, "Prune", 0),
                (3, "Prune", 0, "Echo", 59),
                (4, "India", 52, "Kilo", 39),
                (4, "Kilo", 70, "Prune II", 0),
                (4, "Prune II", 0, "India", 69)
            ],
            # Defeated opponents after round 2:
            #           R1                R2
            # Alpha:    Echo, India(D),   Golf
            # Bravo:    Foxtrot,          Juliet, Foxtrot
            # Charlie:  Kilo,             Prune
            # Delta:    Hotel, Prune,     Alpha, Golf
            # Echo:     India,            Charlie, Prune
            # Foxtrot:  Juliet
            # Golf:     Charlie, Kilo
            # Hotel:    Prune
            # India:    Alpha(D),         Kilo, Prune II
            # Juliet:   Bravo,            Foxtrot
            # Kilo:                       Prune II
            # Prune:
            # Prune II:
            3 : [
                (1, "Delta", 60, "Echo", 55),
                (1, "Echo", 65, "Alpha", 50),
                (1, "Alpha", 59, "Delta", 69),
                (2, "India", 32, "Bravo", 48),
                (2, "Bravo", 50, "Golf", 31),
                (2, "Golf", 48, "India", 30),
                (3, "Juliet", 40, "Charlie", 77),
                (3, "Charlie", 56, "Foxtrot", 51),
                (3, "Foxtrot", 41, "Juliet", 59),
                (4, "Kilo", 40, "Late", 30),
                (4, "Late", 59 , "Prune", 0),
                (4, "Prune", 0, "Kilo", 79)
            ]
            # Defeated opponents after round 3:
            #           R1                R2                 R3
            # Alpha:    Echo, India(D),   Golf
            # Bravo:    Foxtrot,          Foxtrot, Juliet    Golf, India
            # Charlie:  Kilo,             Prune,             Foxtrot, Juliet
            # Delta:    Hotel, Prune,     Alpha, Golf,       Echo, Alpha
            # Echo:     India,            Charlie, Prune,    Alpha
            # Foxtrot:  Juliet
            # Golf:     Charlie, Kilo,                       India
            # Hotel:    Prune
            # India:    Alpha(D),         Kilo, Prune II
            # Juliet:   Bravo,            Foxtrot,           Foxtrot
            # Kilo:                       Prune II,          Late, Prune
            # Late:                                          Prune
            # Prune:
            # Prune II:
        },
        "standings_per_round" : {
            1 : [
                ( 1, "Golf",    2, 2, 1, 131),
                ( 2, "Delta",   2, 2, 1, 130),
                ( 3, "Alpha",   2, 1.5, 1.25, 135),
                ( 4, "Bravo",   2, 1, 1, 101),
                ( 5, "Juliet",  2, 1, 1, 90),
                ( 6, "Foxtrot", 2, 1, 1, 68),
                ( 7, "Echo",    2, 1, 0.5, 81),
                ( 8, "Charlie", 2, 1, 0, 96),
                ( 8, "Hotel",   2, 1, 0, 96),
                (10, "India",   2, 0.5, 0.75, 106),
                (11, "Kilo",    2, 0, 0, 102),
                (12, "Prune",   2, 0, 0, 0),
            ],
            2 : [
                ( 1, "Delta",   4, 4, 6.5, 263),
                ( 2, "Echo",    4, 3, 4.5, 202),
                ( 3, "Bravo",   4, 3, 4, 216),
                ( 4, "Alpha",   4, 2.5, 6.25, 239),
                ( 5, "India",   4, 2.5, 2.25, 227),
                ( 6, "Juliet",  4, 2, 4, 166),
                ( 7, "Golf",    4, 2, 3, 226),
                ( 8, "Charlie", 4, 2, 1, 213),
                ( 9, "Foxtrot", 4, 1, 2, 148),
                (10, "Kilo",    4, 1, 0, 211),
                (11, "Hotel",   2, 1, 0, 96),
                (12, "Prune",   4, 0, 0, 0),
                (12, "Prune II",2, 0, 0, 0),
            ],
            3 : [
                ( 1, "Delta",   6, 6, 15, 392),
                ( 2, "Bravo",   6, 5, 10.5, 314),
                ( 3, "Echo",    6, 4, 9, 322),
                ( 4, "Charlie", 6, 4, 7, 346),
                ( 5, "Golf",    6, 3, 9.5, 305),
                ( 6, "Juliet",  6, 3, 7, 265),
                ( 7, "Kilo",    6, 3, 3, 330),
                ( 8, "Alpha",   6, 2.5, 8.25, 348),
                ( 9, "India",   6, 2.5, 4.25, 289),
                (10, "Foxtrot", 6, 1, 3, 240),
                (11, "Hotel",   2, 1, 0, 96),
                (12, "Late",    2, 1, 0, 89),
                (13, "Prune",   6, 0, 0, 0),
                (13, "Prune II",2, 0, 0, 0),
            ],
        },
        "withdrawals_after_round" : {
            1 : [ "Hotel" ],
            2 : [ "Prune II" ]
        },
        "additions_after_round" : {
            1 : [ "Prune II" ],
            2 : [ "Late" ]
        }
    }
]

class TestFailedException(Exception):
    pass

def testfail(test_name, s):
    print(test_name + ": TEST FAILED")
    print(s)
    raise TestFailedException(test_name + ": " + s)

# tourney_name: name of the test and the tourney
# player_names: list of names, one for each player. Players whose names start
#     with "Prune" will get a rating of 0.
# games_per_round: dict of round numbers to [ (table_number, p1name, p1score, p2name, p2score, tb) ]
# expected_standings_per_round: dict of round numbers to [ (pos, name, played, wins, secondary rank values...) ]
def run_rank_test(tourney_name, player_names, games_per_round,
        expected_standings_per_round,
        rank_method_id=countdowntourney.RANK_WINS_POINTS,
        withdrawals_after_round={}, unwithdrawals_after_round={},
        additions_after_round={}):
    if not tourney_name.startswith("_"):
        tourney_name = "_" + tourney_name
    dbfilename = "./tourneys/" + tourney_name + ".db"
    if os.path.isfile(dbfilename):
        os.unlink(dbfilename)

    tourney = countdowntourney.tourney_create(tourney_name, "./tourneys")

    player_list = [ countdowntourney.EnteredPlayer(p, 0 if p.startswith("Prune") else None) for p in player_names ]
    tourney.set_players(player_list, countdowntourney.RATINGS_UNIFORM)
    tourney.set_rank_method(rank_method_id)

    rank_method = tourney.get_rank_method()

    players = tourney.get_players()
    if len(players) != len(player_names):
        testfail(tourney_name, "tourney.get_players() returned wrong number of players: expected %d, got %d" % (len(player_names), len(players)))

    for round_no in games_per_round:
        games = games_per_round[round_no]

        tourney.name_round(round_no, "Round %d" % (round_no))

        # First, set up fixtures for this round
        round_seq = 1
        fixtures = []
        for row in games:
            (table_no, p1name, p1score, p2name, p2score) = row[0:5]
            tb = (len(row) >= 6 and row[5])
            fixtures.append(countdowntourney.Game(round_no, round_seq, table_no, 0, 'P', tourney.get_player_from_name(p1name), tourney.get_player_from_name(p2name)))
            round_seq += 1
        tourney.merge_games(fixtures)

        # Now fill in the results
        round_seq = 1
        for row in games:
            (table_no, p1name, p1score, p2name, p2score) = row[0:5]
            tb = (len(row) >= 6 and row[5])
            game = fixtures[round_seq - 1]
            game.set_score(p1score, p2score, tb)
            tourney.merge_games([game])
            round_seq += 1

        # Now check the standings
        standings = tourney.get_standings()
        expected_standings = expected_standings_per_round.get(round_no)
        if expected_standings:
            if len(standings) != len(expected_standings):
                testfail(tourney_name, "round %d: tourney.get_standings() returned wrong number of rows: expected %d, got %d" % (round_no, len(expected_standings), len(standings)))
            for standings_index in range(len(standings)):
                row_num = standings_index + 1
                obs = standings[standings_index]
                exs = expected_standings[standings_index]
                if verbose:
                    print(str(obs))
                exp_pos = exs[0]
                exp_name = exs[1]
                exp_played = exs[2]
                exp_wins = exs[3]
                exp_secondaries = exs[4:]
                obs_secondaries = obs.get_secondary_rank_values()
                if obs.position != exp_pos:
                    testfail(tourney_name, "round %d: row %d: position: expected %d, observed %d" % (round_no, row_num, exp_pos, obs.position))
                if obs.name != exp_name:
                    testfail(tourney_name, "round %d: row %d: name: expected %s, observed %s" % (round_no, row_num, exp_name, obs.name))
                if obs.played != exp_played:
                    testfail(tourney_name, "round %d: row %d: games played: expected %d, observed %d" % (round_no, row_num, exp_played, obs.played))
                if obs.wins + obs.draws * 0.5 != exp_wins:
                    testfail(tourney_name, "round %d: row %d: games won: expected %g, observed %g" % (round_no, row_num, exp_wins, obs.wins + obs.draws * 0.5))
                sec_headings = rank_method.get_secondary_rank_headings()
                if len(exp_secondaries) != len(obs_secondaries):
                    testfail(tourney_name, "round %d: row %d: expected %d secondary rank values, observed %d" % (round_no, row_num, len(exp_secondaries), len(obs_secondaries)))
                for i in range(len(exp_secondaries)):
                    if obs_secondaries[i] != exp_secondaries[i]:
                        testfail(tourney_name, "round %d: row %d: %s: expected %s, observed %s" % (round_no, row_num, sec_headings[i], str(exp_secondaries[i]), str(obs_secondaries[i])))
        else:
            print("Warning: no expected standings for round %d" % (round_no))

        # Any players withdrawing this round?
        for name in withdrawals_after_round.get(round_no, []):
            tourney.withdraw_player(name)

        # Any players returning this round?
        for name in unwithdrawals_after_round.get(round_no, []):
            tourney.unwithdraw_player(name)

        # Any new players joining in this round?
        for name in additions_after_round.get(round_no, []):
            tourney.add_player(name, 0 if name.startswith("Prune") else 1000)

        if verbose:
            print("Finished round %d." % (round_no))

def main():
    for test in tests:
        print("Test %s..." % (test["name"]))
        run_rank_test(test["name"], test["player_names"],
                test["games_per_round"], test["standings_per_round"],
                test["rank"], test.get("withdrawals_after_round", {}),
                test.get("unwithdrawals_after_round", {}),
                test.get("additions_after_round", {}))
        print("Test %s passed." % (test["name"]))

if __name__ == "__main__":
    main()
