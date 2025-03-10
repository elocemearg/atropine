#!/usr/bin/python3

import sys
import os
import subprocess

# Test must be run from the directory above "test"
# i.e.
# ./test/tourneytest.py
sys.path.append(os.path.join(os.getcwd(), "py"))
sys.path.append(os.path.join(os.getcwd(), "py", "dynamicpages"))

import countdowntourney
import httpresponse
import fieldstorage
import export as export_page_module

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
    "expected_second_wind" : [
        [
            # Division A
            ( "P2", 2, 3, 43, 76, 33 ),
            ( "P1", 1, 2, 40, 70, 30 ),
            ( "P4", 1, 2, 51, 81, 30 ),
            ( "P3", 1, 2, 57, 55, -2 ),
            ( "P2", 1, 2, 50, 43, -7 ),
            ( "P3", 2, 3, 55, 41, -14 ),
            ( "P4", 2, 3, 81, 60, -21 ),
            ( "P1", 2, 3, 70, 30, -40 ),
        ],
        [
            # Division B
            ( "P7", 2, 3, 36, 53, 17 ),
            ( "P5", 2, 3, 50, 63, 13 ),
            ( "P7", 1, 2, 24, 36, 12 ),
            ( "P8", 2, 3, 40, 42, 2 ),
            ( "P6", 1, 2, 61, 60, -1 ),
            ( "P5", 1, 2, 60, 50, -10 ),
            ( "P8", 1, 2, 50, 40, -10 ),
            ( "P6", 2, 3, 60, 20, -40 ),
        ],
        [
            # Division C
            ( "P10", 2, 3, 31, 55, 24 ),
            ( "P11", 2, 3, 43, 56, 13 ),
            ( "P12", 2, 3, 44, 48, 4 ),
            ( "P11", 1, 2, 42, 43, 1 ),
            ( "P9", 2, 3, 51, 43, -8 ),
            ( "P9", 1, 2, 62, 51, -11 ), # first game score of 72 was on a tiebreak
            ( "P12", 1, 2, 56, 44, -12 ),
            ( "P10", 1, 2, 62, 31, -31 ),
        ]
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

def export_text(tourney, output_file):
    """Export a tourney report as plain text.

    Run py/dynamicpages/export.py's handle() function to generate a tournament
    report as plain text, and write it to output_file."""

    if os.path.exists(output_file):
        os.unlink(output_file)
    with open(output_file, "w") as out:
        response = httpresponse.HTTPResponse()
        query_string = "tourney=%s&format=text&submitview=1" % (tourney.get_name())
        form = fieldstorage.FieldStorage(request_method="GET", query_string=query_string, post_data=None)
        export_page_module.handle(None, response, tourney, "GET", form, query_string, [])
        out.write(response.get_string())

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

def check_second_wind(tourney, scenario):
    # If the scenario has an "expected_second_wind" member, check that the
    # results of tourney.get_adj_round_score_diffs() match its contents.
    if "expected_second_wind" in scenario:
        for (div_index, expected_second_wind) in enumerate(scenario["expected_second_wind"]):
            observed_second_wind = tourney.get_adj_round_score_diffs(div_index, limit=None)

            if len(expected_second_wind) != len(observed_second_wind):
                print("second wind, div %d: expected %d rows, observed %d rows" % (div_index, len(expected_second_wind), len(observed_second_wind)))
                return False
            for rownum in range(len(expected_second_wind)):
                observed_player_name = observed_second_wind[rownum][0].get_name()
                expected_player_name = expected_second_wind[rownum][0]
                fail_reason = None
                if observed_player_name != expected_player_name:
                    fail_reason = "expected player %s, observed player %s" % (expected_player_name, observed_player_name)
                else:
                    col_names = [ "name", "round", "score", "nextround", "nextscore", "difference" ]
                    for col in (1, 2, 3, 4, 5):
                        if observed_second_wind[rownum][col] != expected_second_wind[rownum][col]:
                            fail_reason = "column \"%s\": expected %d, observed %d" % (col_names[col], expected_second_wind[rownum][col], observed_second_wind[rownum][col])
                            break
                if fail_reason:
                    print("second wind, div %d, row %d: %s" % (div_index, rownum, fail_reason))
                    return False
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

    if not check_second_wind(tourney, scenario):
        return False

    # Export the tourney as plain text and check the output is as it should be.
    # We compare the output file with the appropriately named *.expected
    # file in test/tourneytestfiles.
    output_file = os.path.join("test", "tourneytestfiles", "%s.out" % (test_name))
    expected_file = os.path.join("test", "tourneytestfiles", "%s.expected" % (test_name))

    export_text(tourney, output_file)
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
