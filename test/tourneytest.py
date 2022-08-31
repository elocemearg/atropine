#!/usr/bin/python3

import sys
import os
import subprocess

# Test must be run from the directory above "test"
# i.e.
# ./test/tourneytest.py
sys.path.append(os.path.join(os.getcwd(), "py"))

import countdowntourney

div_scenario = {
    "full_name" : "Some Divisioned Tourney",
    "venue" : "Divisionsbury Village Hall",
    "date" : [ 2022, 8, 30 ],
    "players" : [
        {
            "name" : "P%d" % (n),
            "division" : (n - 1) // 4,
        } for n in range(1, 13)
    ],
    "rounds" : [
        {
            "name" : "Round 1",
            "games" : [
                # table, division, name1, score1, score2, name2
                ( 1, 0, "P1", 40, 50, "P2" ),
                ( 2, 0, "P3", 57, 51, "P4" ),
                ( 3, 1, "P5", 60, 61, "P6" ),
                ( 4, 1, "P7", 24, 50, "P8" ),
                ( 5, 2, "P9", 72, 62, "P10", True ),
                ( 6, 2, "P11", 42, 56, "P12" )
            ]
        },
        {
            "name" : "Round 2",
            "games" : [
                # table, division, name1, score1, score2, name2
                ( 1, 0, "P1", 70, 55, "P3" ),
                ( 2, 0, "P2", 43, 81, "P4" ),
                ( 3, 1, "P5", 50, 36, "P7" ),
                ( 4, 1, "P6", 60, 40, "P8" ),
                ( 5, 2, "P9", 51, 43, "P11" ),
                ( 6, 2, "P10", 31, 44, "P12" )
            ]
        },
        {
            "name" : "Round 3",
            "games" : [
                # table, division, name1, score1, score2, name2
                ( 1, 0, "P1", 30, 60, "P4" ),
                ( 2, 0, "P2", 76, 41, "P3" ),
                ( 3, 1, "P5", 63, 42, "P8" ),
                ( 4, 1, "P6", 20, 53, "P7" ),
                ( 5, 2, "P9", 43, 48, "P12" ),
                ( 6, 2, "P10", 55, 56, "P11" )
            ]
        }

        # Wins/points:
        #
        # P1  1 140
        # P2  2 169
        # P3  1 153
        # P4  2 192
        #
        # P5  2 173
        # P6  2 141
        # P7  1 113
        # P8  1 132
        #
        # P9  2 156
        # P10 0 148
        # P11 1 141
        # P12 3 148
    ]
}

def apply_scenario(tourney, scenario):
    """Apply a scenario to a blank tourney.

    tourney must be a countdowntourney.Tourney object.

    scenario is a dict which must contain, at a minimum:
        "players" which contains a list of objects each with a mandatory
            "name" and an optional "division". 
        "rounds" which contains a list of objects each with an optional
            "name" and a mandatory list "games", each element of which is a
            tuple (table_no, division, p1name, p1score, p2score, p2name[, tb])
    """

    if "full_name" in scenario:
        tourney.set_full_name(scenario["full_name"])
    if "venue" in scenario:
        tourney.set_venue(scenario["venue"])
    if "date" in scenario:
        tourney.set_event_date(scenario["date"][0], scenario["date"][1], scenario["date"][2])
    entered_players = [
        countdowntourney.EnteredPlayer(p["name"], None, p.get("division", 0)) for p in scenario["players"]
    ]
    tourney.set_players(entered_players)
    name_to_player = {}
    for p in tourney.get_players():
        name_to_player[p.get_name()] = p
    for (rnd_index, rnd) in enumerate(scenario["rounds"]):
        round_no = rnd_index + 1
        tourney.name_round(round_no, rnd.get("name", "Round %d" % (round_no)))

        # Set games as unplayed fixtures first
        fixtures = []
        for (seq, g) in enumerate(rnd["games"]):
            table_no = g[0]
            div = g[1]
            n1 = g[2]
            n2 = g[5]
            fixtures.append(countdowntourney.Game(round_no, seq, table_no, div, 'P', name_to_player[n1], name_to_player[n2]))
        tourney.merge_games(fixtures)

        # Now fill in the results
        for (seq, g) in enumerate(rnd["games"]):
            table_no = g[0]
            div = g[1]
            n1 = g[2]
            s1 = g[3]
            s2 = g[4]
            n2 = g[5]
            if len(g) > 6:
                tb = g[6]
            else:
                tb = False
            fixtures.append(countdowntourney.Game(round_no, seq, table_no, div, 'P', name_to_player[n1], name_to_player[n2], s1, s2, tb))
        tourney.merge_games(fixtures)

def export_text(tourney_name, output_file):
    """Export a named tourney report as plain text.

    Run cgi-bin/export.py to generate a tournament report as plain text,
    and write it to output_file."""

    if os.path.exists(output_file):
        os.unlink(output_file)
    with open(output_file, "w") as out:
        p = subprocess.run(
                ["python3", os.path.join("cgi-bin", "export.py") ],
                stdout=out,
                cwd="webroot",
                check=True,
                env={
                    "REQUEST_METHOD" : "GET",
                    "QUERY_STRING" : "tourney=%s&format=text&submitview=1" % (tourney_name),
                    "PYTHONPATH" : os.path.join(os.getcwd(), "py")
                },
                universal_newlines=True
        )

def diff_files(observed, expected):
    p = subprocess.run(
            ["diff", "-b", observed, expected],
            universal_newlines=True
    )
    if p.returncode != 0:
        print("-------------------------------------------------------------------------------")
        print("%s and %s differ." % (observed, expected))
        return False
    else:
        return True

def test_scenario(test_name, scenario):
    tourney_name = "_" + test_name
    tourney_file = os.path.join("tourneys", "%s.db" % (tourney_name))
    if os.path.exists(tourney_file):
        os.unlink(tourney_file)
    tourney = countdowntourney.tourney_create(tourney_name, "tourneys")
    tourney.close()
    tourney = countdowntourney.tourney_open(tourney_name, "tourneys")

    apply_scenario(tourney, scenario)

    # Export the tourney as plain text and check the output is as it should be.
    # We compare the output file with the appropriately named *.expected
    # file in test/tourneytestfiles.
    output_file = os.path.join("test", "tourneytestfiles", "%s.out" % (test_name))
    expected_file = os.path.join("test", "tourneytestfiles", "%s.expected" % (test_name))

    export_text(tourney_name, output_file)
    if not diff_files(output_file, expected_file):
        print("%s failed." % (test_name))
        return False
    else:
        os.unlink(output_file)
        print("%s passed." % (test_name))
        return True

def main():
    if not test_scenario("divtest", div_scenario):
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
