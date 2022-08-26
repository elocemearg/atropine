#!/usr/bin/python3

import os
import sys
import shutil

sys.path.append("py")

import countdowntourney

class FinalsTestFailedException(Exception):
    pass

pre_finals_setup = {
    # 12 players
    "players" : [ "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L" ],

    # Each plays one game, so we have some sort of standings table
    "games" : [
        (1, 1, 1, "A", "B", 50, 30),
        (1, 2, 2, "C", "D", 67, 32),
        (1, 3, 3, "E", "F", 41, 48),
        (1, 4, 4, "G", "H", 25, 88),
        (1, 5, 5, "I", "J", 49, 51),
        (1, 6, 6, "K", "L", 71, 75)
    ],

    "expected_standings_order" : [
        "H", "L", "C", "J", "A", "F", # 88, 75, 67, 51, 50, 48
        "K", "I", "E", "D", "B", "G", # 71, 49, 41, 32, 30, 25
    ]
}

# Top 8 going into final:
# 1. H
# 2. L
# 3. C
# 4. J
# 5. A
# 6. F
# 7. K
# 8. I

scenarios = [
    {
        "name" : "Quarter-finals, winners play in semis, winners of semis play in a final",
        "rounds" : [
            {
                "game_type" : "QF",
                "games" : [
                    ( 2, 1, 1, "H", "I", 56, 41 ),
                    ( 2, 2, 2, "L", "K", 33, 50 ),
                    ( 2, 3, 3, "C", "F", 70, 61 ),
                    ( 2, 4, 4, "J", "A", 42, 45 )
                ]
            },
            {
                "game_type" : "SF",
                "games" : [
                    (3, 1, 1, "H", "C", 51, 57),
                    (3, 2, 2, "K", "A", 66, 40)
                ]
            },
            {
                "game_type" : "F",
                "games" : [
                    (4, 1, 1, "C", "K", 58, 48 )
                ],
                "expected_standings_order" : [
                    # Same as standings order after prelims except that C and K
                    # occupy the first two positions, in that order.
                    "C", "K", "H", "L", "J", "A", "F", "I", "E", "D", "B", "G"
                ]
            }
        ]
    },
    {
        "name" : "Quarter-finals, winners play in semis, losers of semis play in 3P, winners of semis play in final",
        "rounds" : [
            {
                "game_type" : "QF",
                "games" : [
                    ( 2, 1, 1, "H", "I", 41, 56 ),
                    ( 2, 2, 2, "L", "K", 50, 33 ),
                    ( 2, 3, 3, "C", "F", 61, 70 ),
                    ( 2, 4, 4, "J", "A", 45, 42 )
                ]
            },
            {
                "game_type" : "SF",
                "games" : [
                    ( 3, 1, 1, "I", "F", 57, 51),
                    ( 3, 2, 2, "L", "J", 40, 66),
                ]
            },
            {
                "game_type" : "3P",
                "games" : [
                    (4, 1, 1, "F", "L", 72, 52)
                ],
                "expected_standings_order" : [
                    # Same as original standings order except that F and L have
                    # now been parachuted into third and fourth.
                    "H", "C", "F", "L", "J", "A", "K", "I", "E", "D", "B", "G"
                ]
            },
            {
                "game_type" : "F",
                "games" : [
                    (5, 1, 1, "I", "J", 46, 57)
                ],
                "expected_standings_order" : [
                    # Same as original except first four are J, I, F, L
                    "J", "I", "F", "L", "H", "C", "A", "K", "E", "D", "B", "G"
                ]
            }
        ]
    },
    {
        "name" : "Quarter-finals, all eight play in semis, all eight play in final, to fix positions 1-8",
        "rounds" : [
            {
                "game_type" : "QF",
                "games" : [
                    ( 2, 1, 1, "H", "I", 56, 41 ),
                    ( 2, 2, 2, "L", "K", 33, 50 ),
                    ( 2, 3, 3, "C", "F", 70, 61 ),
                    ( 2, 4, 4, "J", "A", 42, 45 )
                ]
            },
            {
                "game_type" : "SF",
                "games" : [
                    ( 3, 1, 1, "H", "A", 59, 52 ),
                    ( 3, 2, 2, "K", "C", 40, 60 ),
                    ( 3, 3, 3, "I", "J", 46, 33 ),
                    ( 3, 4, 4, "L", "F", 55, 41 )
                ]
            },
            {
                "game_type" : "F",
                "games" : [
                    ( 4, 1, 1, "H", "C", 56, 51 ), # 1st/2nd
                    ( 4, 2, 2, "A", "K", 44, 59 ), # 3rd/4th
                    ( 4, 3, 3, "I", "L", 60, 70 ), # 5th/6th
                    ( 4, 4, 4, "J", "F", 43, 37 ), # 7th/8th
                ],
                "expected_standings_order" : [
                    "H", "C", "K", "A", "L", "I", "J", "F", "E", "D", "B", "G"
                ]
            }
        ]
    },
    {
        "name" : "Top four play semis, then one 3P, then one final",
        "rounds" : [
            {
                "game_type" : "SF",
                "games" : [
                    ( 2, 1, 1, "H", "J", 60, 50 ),
                    ( 2, 2, 2, "L", "C", 50, 55 ),
                ]
            },
            {
                "game_type" : "3P",
                "games" : [
                    (3, 1, 1, "J", "L", 52, 66 )
                ],
                "expected_standings_order" : [
                    "H", "C", "L", "J", "A", "F", "K", "I", "E", "D", "B", "G",
                ]
            },
            {
                "game_type" : "F",
                "games" : [
                    (4, 1, 1, "H", "C", 47, 61 )
                ],
                "expected_standings_order" : [
                    "C", "H", "L", "J", "A", "F", "K", "I", "E", "D", "B", "G"
                ]
            }
        ]
    },
    {
        "name" : "Top four play semis, then both play in \"final\" even though one is really a 3P",
        "rounds" : [
            {
                "game_type" : "SF",
                "games" : [
                    ( 2, 1, 1, "H", "J", 60, 50 ),
                    ( 2, 2, 2, "L", "C", 50, 55 ),
                ]
            },
            {
                "game_type" : "F",
                "games" : [
                    (3, 1, 1, "J", "L", 52, 66 ),
                    (3, 2, 2, "H", "C", 47, 61 )
                ],
                "expected_standings_order" : [
                    "C", "H", "L", "J", "A", "F", "K", "I", "E", "D", "B", "G"
                ]
            }
        ]
    },
    {
        "name" : "Third place between 3rd and 4th, Final between top two",
        "rounds" : [
            {
                "game_type" : "3P",
                "games" : [
                    ( 2, 1, 1, "C", "J", 40, 49 )
                ],
                "expected_standings_order" : [
                    "H", "L", "J", "C", "A", "F", "K", "I", "E", "D", "B", "G"
                ]
            },
            {
                "game_type" : "F",
                "games" : [
                    ( 3, 1, 1, "H", "L", 52, 69 ),
                ],
                "expected_standings_order" : [
                    "L", "H", "J", "C", "A", "F", "K", "I", "E", "D", "B", "G"
                ]
            }
        ]
    },
    {
        "name" : "Final between the top two: 1st place wins",
        "rounds" : [
            {
                "game_type" : "F",
                "games" : [
                    (2, 1, 1, "H", "L", 70, 45)
                ],
                "expected_standings_order" : [
                    "H", "L", "C", "J", "A", "F", "K", "I", "E", "D", "B", "G"
                ]
            }
        ]
    },
    {
        "name" : "Final between the top two: 2nd place wins",
        "rounds" : [
            {
                "game_type" : "F",
                "games" : [
                    (2, 1, 1, "H", "L", 45, 70)
                ],
                "expected_standings_order" : [
                    "L", "H", "C", "J", "A", "F", "K", "I", "E", "D", "B", "G"
                ]
            }
        ]
    },
    {
        "name" : "1st gets a bye to the final, 2nd-5th play semi-final and not-a-final for the other final spot",
        "rounds" : [
            {
                "game_type" : "SF",
                "games" : [
                    (2, 1, 1, "L", "A", 47, 80),
                    (2, 2, 2, "C", "J", 57, 51)
                ]
            },
            {
                "game_type" : "N",
                "games" : [
                    (3, 1, 1, "A", "C", 57, 40)
                ]
            },
            {
                "game_type" : "F",
                "games" : [
                    (4, 1, 1, "H", "A", 62, 42)
                ],
                "expected_standings_order" : [
                    # H and A in the first two positions, then as before
                    "H", "A", "L", "C", "J", "F", "K", "I", "E", "D", "B", "G"
                ]
            }
        ]
    }
]

def add_round(tourney, game_type, round_name, games):
    # Add the fixtures first
    fixtures = []
    for (round_no, seq, table_no, p1, p2, s1, s2) in games:
        fixtures.append(countdowntourney.Game(round_no, seq, table_no, 0, game_type,
            tourney.get_player_from_name(p1), tourney.get_player_from_name(p2)))
    tourney.merge_games(fixtures)
    tourney.name_round(games[0][0], round_name)

    # Now add the results
    results = []
    for (round_no, seq, table_no, p1, p2, s1, s2) in games:
        g = countdowntourney.Game(round_no, seq, table_no, 0, game_type,
                tourney.get_player_from_name(p1), tourney.get_player_from_name(p2))
        g.set_score(s1, s2, False)
        results.append(g)
    tourney.merge_games(results)

def standings_fail(observed, expected, context_string):
    observed_order = ", ".join([ s.name for s in observed ])
    expected_order = ", ".join(expected)
    print("Test failed: %s" % (context_string))
    print("Expected standings order: " + expected_order)
    print("Observed standings order: " + observed_order)
    raise FinalsTestFailedException()

def verify_standings_order(tourney, expected_standings_order, context_string):
    standings = tourney.get_standings()
    if len(standings) != len(expected_standings_order):
        standings_fail(standings, expected_standings_order, context_string)
    for (i, s) in enumerate(standings):
        if s.name != expected_standings_order[i]:
            standings_fail(standings, expected_standings_order, context_string)

def main():
    tourney_dir = os.path.join(os.path.dirname(__file__), "..", "tourneys")
    tourney_path = os.path.join(tourney_dir, "_rankfinals.db")

    if os.path.isfile(tourney_path):
        os.unlink(tourney_path)

    tourney = countdowntourney.tourney_create("_rankfinals", tourney_dir)

    players = [ countdowntourney.EnteredPlayer(name, None) for name in pre_finals_setup["players"] ]

    tourney.set_players(players)

    # Play the pre-final games, not that there are many
    add_round(tourney, "P", "Round 1", pre_finals_setup["games"])

    # Check the standings table is in the right order
    verify_standings_order(tourney, pre_finals_setup["expected_standings_order"], "Pre-finals")

    tourney.close()

    # Back up the database file
    shutil.copyfile(tourney_path, tourney_path + ".backup")

    # Now run each scenario from that point
    for (scenario_number, scenario) in enumerate(scenarios):
        # Restore the tourney to immediately after the prelims
        shutil.copyfile(tourney_path + ".backup", tourney_path)

        # Open the tourney
        tourney = countdowntourney.tourney_open("_rankfinals", tourney_dir)
        print("Scenario %d/%d: %s" % (scenario_number + 1, len(scenarios), scenario["name"]))

        for round_data in scenario.get("rounds", []):
            # Add the games for this round then verify the standings table is
            # as expected. If there is no expected_standings_order specified
            # for the round, the standings order should be unchanged from the
            # pre-finals stage.
            game_type = round_data["game_type"]
            games = round_data["games"]
            expected_standings_order = round_data.get("expected_standings_order", pre_finals_setup["expected_standings_order"])

            add_round(tourney, game_type, "Round " + game_type, games)
            verify_standings_order(tourney, expected_standings_order,
                    scenario["name"] + ": round " + str(games[0][0]) + ", " + game_type)
        tourney.close()
        print("Scenario passed.")

    # Any failed scenario would have thrown an exception.
    print("All scenarios passed.")

if __name__ == "__main__":
    main()
