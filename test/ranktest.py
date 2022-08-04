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
    },
    {
        "name" : "ranktest_solkoff",
        "player_names" : [ "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliet", "Kilo", "Prune" ],
        "rank" : countdowntourney.RANK_WINS_SOW,
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
            # Opponents faced after round 1:
            #
            # Alpha:   Echo, India
            # Bravo:   Foxtrot, Juliet
            # Charlie: Golf, Kilo
            # Delta:   Hotel, Prune
            # Echo:    Alpha, India
            # Foxtrot: Bravo, Juliet
            # Golf:    Charlie, Kilo
            # Hotel:   Delta, Prune
            # India:   Alpha, Echo
            # Juliet:  Bravo, Foxtrot
            # Kilo:    Charlie, Golf
            # Prune:   Delta, Hotel

            # Prune withdraws, Late is added. Players who have played Prune
            # do not get a bonus of 0.5 Solkoff points for each of Prune's
            # missed games, but players who play Late DO get a bonus of 0.5
            # Solkoff points for each of Late's two missed games.
            2 : [
                (1, "Golf", 50, "Delta", 60),
                (1, "Delta", 42, "Alpha", 55),
                (1, "Alpha", 61, "Golf", 30),
                (2, "Bravo", 55, "Hotel", 50),
                (2, "Hotel", 41, "Charlie", 57),
                (2, "Charlie", 48, "Bravo", 38),
                (3, "Juliet", 56, "Echo", 46),
                (3, "Echo", 41, "Foxtrot", 35),
                (3, "Foxtrot", 65, "Juliet", 40),
                (4, "India", 50, "Kilo", 49 ),
                (4, "Kilo", 56, "Late", 30),
                (4, "Late", 45, "India", 41)
            ],

            # Opponents faced after round 2:
            #
            # Alpha:   Echo, India, Delta, Golf
            # Bravo:   Foxtrot, Juliet, Charlie, Hotel
            # Charlie: Golf, Kilo, Bravo, Hotel
            # Delta:   Hotel, Prune, Alpha, Golf
            # Echo:    Alpha, India, Foxtrot, Juliet
            # Foxtrot: Bravo, Juliet, Echo, Juliet
            # Golf:    Charlie, Kilo, Alpha, Delta
            # Hotel:   Delta, Prune, Bravo, Charlie
            # India:   Alpha, Echo, Kilo, Late
            # Juliet:  Bravo, Foxtrot, Echo, Foxtrot
            # Kilo:    Charlie, Golf, India, Late
            # Late:                   India, Kilo
            # Prune:   Delta, Hotel

            3 : [
                (1, "Alpha", 49, "Delta", 62),
                (1, "Delta", 55, "Charlie", 57),
                (1, "Charlie", 41, "Alpha", 70),
                (2, "Golf", 41, "Echo", 59),
                (2, "Echo", 37, "Bravo", 60),
                (2, "Bravo", 72, "Golf", 52),
                (3, "Juliet", 55, "Foxtrot", 62),
                (3, "Foxtrot", 51, "India", 59),
                (3, "India", 58, "Juliet", 45),
                (4, "Kilo", 50, "Hotel", 66),
                (4, "Hotel", 52, "Late", 50),
                (4, "Late", 59, "Kilo", 31)
            ]
            # Opponents faced after round 2:
            #
            # Alpha:   Echo, India, Delta, Golf, Charlie, Delta
            # Bravo:   Foxtrot, Juliet, Charlie, Hotel, Echo, Golf
            # Charlie: Golf, Kilo, Bravo, Hotel, Alpha, Delta
            # Delta:   Hotel, Prune, Alpha, Golf, Alpha, Charlie
            # Echo:    Alpha, India, Foxtrot, Juliet, Bravo, Golf
            # Foxtrot: Bravo, Juliet, Echo, Juliet, India, Juliet
            # Golf:    Charlie, Kilo, Alpha, Delta, Bravo, Echo
            # Hotel:   Delta, Prune, Bravo, Charlie, Kilo, Late
            # India:   Alpha, Echo, Kilo, Late, Foxtrot, Juliet
            # Juliet:  Bravo, Foxtrot, Echo, Foxtrot, Foxtrot, India
            # Kilo:    Charlie, Golf, India, Late, Hotel, Late
            # Late:                   India, Kilo, Hotel, Kilo
            # Prune:   Delta, Hotel
        },
        "standings_per_round" : {
            1 : [
                ( 1, "Golf",    2, 2, 1, 131),
                ( 2, "Delta",   2, 2, 1, 130),
                ( 3, "Alpha",   2, 1.5, 1.5, 135),
                ( 4, "Bravo",   2, 1, 2, 101),
                ( 5, "Charlie", 2, 1, 2, 96),
                ( 5, "Hotel",   2, 1, 2, 96),
                ( 7, "Juliet",  2, 1, 2, 90),
                ( 8, "Echo",    2, 1, 2, 81),
                ( 9, "Foxtrot", 2, 1, 2, 68),
                (10, "India",   2, 0.5, 2.5, 106),
                (11, "Kilo",    2, 0, 3, 102),
                (12, "Prune",   2, 0, 3, 0),
            ],
            2 : [
                ( 1, "Alpha",   4, 3.5, 8.5, 251),
                ( 2, "Delta",   4, 3, 6.5, 232),
                ( 3, "Charlie", 4, 3, 6, 201),
                ( 4, "Golf",    4, 2, 10.5, 211),
                ( 5, "Echo",    4, 2, 9, 168),
                ( 6, "Bravo",   4, 2, 8, 194),
                ( 7, "Juliet",  4, 2, 8, 186),
                ( 8, "Foxtrot", 4, 2, 8, 168),
                ( 9, "India",   4, 1.5, 8.5, 197),  # played Late, bonus 2*0.5
                (10, "Kilo",    4, 1, 8.5, 207), # played Late, bonus 2*0.5
                (11, "Hotel",   4, 1, 8, 187),
                (12, "Late",    2, 1, 2.5, 75),
                (13, "Prune",   2, 0, 4, 0),
            ],
            3 : [
                ( 1, "Alpha",   6, 4.5, 20.5, 370),
                ( 2, "Charlie", 6, 4, 18.5, 299),
                ( 3, "Delta",   6, 4, 18, 349),
                ( 4, "Bravo",   6, 4, 17, 326),
                ( 5, "India",   6, 3.5, 16.5, 314),  # played Late, bonus 2*0.5
                ( 6, "Echo",    6, 3, 19, 264),
                ( 7, "Foxtrot", 6, 3, 16.5, 281),
                ( 8, "Hotel",   6, 3, 16, 305), # played Late, bonus 2*0.5
                ( 9, "Golf",    6, 2, 20.5, 304),
                (10, "Juliet",  6, 2, 19.5, 286),
                (11, "Late",    4, 2, 8.5, 184),
                (12, "Kilo",    6, 1, 18.5, 288), # played Late*2, bonus 2*2*0.5
                (13, "Prune",   2, 0, 7, 0),
            ],
        },
        "withdrawals_after_round" : {
            1 : [ "Prune" ]
        },
        "additions_after_round" : {
            1 : [ "Late" ]
        }
    },
    {
        "name" : "ranktest_cumulative",
        "player_names" : [ "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliet", "Kilo", "Lima" ],
        "rank" : countdowntourney.RANK_WINS_CUMULATIVE,
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
                (4, "Hotel", 66, "Lima", 33),
                (4, "Lima", 70, "Delta", 50)
            ],
            # Foxtrot withdraws, Prune is added
            2 : [
                (1, "Golf", 55, "Alpha", 51),
                (1, "Alpha", 61, "Delta", 40),
                (1, "Delta", 56, "Golf", 72),
                (2, "Lima", 50, "Bravo", 51),
                (2, "Bravo", 59, "Charlie", 35),
                (2, "Charlie", 64, "Lima", 60),
                (3, "Hotel", 40, "Juliet", 65),
                (3, "Juliet", 46, "Echo", 41),
                (3, "Echo", 56, "Hotel", 51),
                (4, "Prune", 0, "India", 68),
                (4, "India", 57, "Kilo", 41),
                (4, "Kilo", 82, "Prune", 0)
            ],
            # Foxtrot returns, Prune withdraws. Foxtrot didn't play in round
            # 2 so gets no cumulative effect for that round.
            3 : [
                (1, "Golf", 50, "Bravo", 60),
                (1, "Bravo", 63, "Juliet", 51),
                (1, "Juliet", 41, "Golf", 49),
                (2, "Alpha", 56, "India", 55),
                (2, "India", 75, "Charlie", 40),
                (2, "Charlie", 51, "Alpha", 30),
                (3, "Echo", 59, "Lima", 52),
                (3, "Lima", 41, "Delta", 60),
                (3, "Delta", 55, "Echo", 45),
                (4, "Hotel", 50, "Kilo", 66),
                (4, "Kilo", 56, "Foxtrot", 39),
                (4, "Foxtrot", 61, "Hotel", 41),
            ]
        },
        "standings_per_round" : {
            1 : [
                ( 1, "Golf",    2, 2, 2, 131),
                ( 2, "Alpha",   2, 1.5, 1.5, 135),
                ( 3, "Delta",   2, 1, 1, 110),
                ( 4, "Lima",    2, 1, 1, 103),
                ( 5, "Bravo",   2, 1, 1, 101),
                ( 6, "Charlie", 2, 1, 1, 96),
                ( 6, "Hotel",   2, 1, 1, 96),
                ( 8, "Juliet",  2, 1, 1, 90),
                ( 9, "Echo",    2, 1, 1, 81),
                (10, "Foxtrot", 2, 1, 1, 68),
                (11, "India",   2, 0.5, 0.5, 106),
                (12, "Kilo",    2, 0, 0, 102)
            ],
            2 : [
                ( 1, "Golf",    4, 4, 6, 258),
                ( 2, "Bravo",   4, 3, 4, 211),
                ( 3, "Juliet",  4, 3, 4, 201),
                ( 4, "Alpha",   4, 2.5, 4, 247),
                ( 5, "India",   4, 2.5, 3, 231),
                ( 6, "Charlie", 4, 2, 3, 195),
                ( 7, "Echo",    4, 2, 3, 178),
                ( 8, "Lima",    4, 1, 2, 213),
                ( 9, "Delta",   4, 1, 2, 206),
                (10, "Hotel",   4, 1, 2, 187),
                (11, "Kilo",    4, 1, 1, 225),
                (12, "Foxtrot", 2, 1, 1, 68),
                (13, "Prune",   2, 0, 0, 0)
            ],
            3 : [
                ( 1, "Golf",    6, 5, 11, 357),
                ( 2, "Bravo",   6, 5, 9, 334),
                ( 3, "Alpha",   6, 3.5, 7.5, 333),
                ( 4, "India",   6, 3.5, 6.5, 361),
                ( 5, "Juliet",  6, 3, 7, 293),
                ( 6, "Charlie", 6, 3, 6, 286),
                ( 7, "Echo",    6, 3, 6, 282),
                ( 8, "Delta",   6, 3, 5, 321),
                ( 9, "Kilo",    6, 3, 4, 347),
                (10, "Foxtrot", 4, 2, 3, 168),
                (11, "Lima",    6, 1, 3, 306),
                (12, "Hotel",   6, 1, 3, 278),
                (13, "Prune",   2, 0, 0, 0)
            ],
        },
        "withdrawals_after_round" : {
            1 : [ "Foxtrot" ],
            2 : [ "Prune" ],
        },
        "unwithdrawals_after_round" : {
            2 : [ "Foxtrot" ],
        },
        "additions_after_round" : {
            1 : [ "Prune" ],
        }
    },
    {
        "name" : "ranktest_spread",
        "player_names" : [ "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliet", "Kilo", "Lima" ],
        "rank" : countdowntourney.RANK_WINS_SPREAD,
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
                (4, "Hotel", 66, "Lima", 51),
                (4, "Lima", 69, "Delta", 70)
            ],
            2 : [
                (1, "Golf", 56, "Delta", 51),
                (1, "Delta", 44, "Alpha", 38),
                (1, "Alpha", 50, "Golf", 70),
                (2, "Bravo", 52, "Juliet", 42),
                (2, "Juliet", 49, "Foxtrot", 41),
                (2, "Foxtrot", 44, "Bravo", 50),
                (3, "Echo", 46, "Charlie", 41),
                (3, "Charlie", 55, "Hotel", 55),
                (3, "Hotel", 56, "Echo", 60),
                (4, "India", 45, "Lima", 41),
                (4, "Lima", 44, "Kilo", 56),
                (4, "Kilo", 52, "India", 50)
            ],
            3 : [
                (1, "Golf", 72, "Delta", 62),
                (1, "Delta", 52, "Bravo", 54),
                (1, "Bravo", 55, "Golf", 63),
                (2, "Echo", 57, "Juliet", 41),
                (2, "Juliet", 52, "Alpha", 51),
                (2, "Alpha", 60, "Echo", 59),
                (3, "Kilo", 45, "Charlie", 35),
                (3, "Charlie", 47, "Hotel", 42),
                (3, "Hotel", 44, "Kilo", 70),
                (4, "India", 40, "Foxtrot", 52),
                (4, "Foxtrot", 48, "Lima", 56),
                (4, "Lima", 43, "India", 60)
            ]
        },
        "standings_per_round" : {
            1 : [
                ( 1, "Golf",    2, 2,  34),
                ( 2, "Delta",   2, 2,  31),
                ( 3, "Alpha",   2, 2,  20),
                ( 4, "Bravo",   2, 1,  10),
                ( 5, "Juliet",  2, 1,  -2),
                ( 6, "Foxtrot", 2, 1,  -8),
                ( 7, "Echo",    2, 1, -10),
                ( 8, "Charlie", 2, 1, -13),
                ( 9, "Hotel",   2, 1, -15),
                (10, "India",   2, 0, -10),
                (11, "Lima",    2, 0, -16),
                (12, "Kilo",    2, 0, -21),
            ],
            2 : [
                ( 1, "Golf",    4, 4,  59),
                ( 2, "Delta",   4, 3,  32),
                ( 3, "Bravo",   4, 3,  26),
                ( 4, "Echo",    4, 3,  -1),
                ( 5, "Juliet",  4, 2,  -4),
                ( 6, "Alpha",   4, 2,  -6),
                ( 7, "Kilo",    4, 2,  -7),
                ( 8, "Charlie", 4, 1.5, -18),
                ( 9, "Hotel",   4, 1.5, -19),
                (10, "India",   4, 1,  -8),
                (11, "Foxtrot", 4, 1, -22),
                (12, "Lima",    4, 0, -32),
            ],
            3 : [
                ( 1, "Golf",    6, 6,  77),
                ( 2, "Kilo",    6, 4,  29),
                ( 3, "Bravo",   6, 4,  20),
                ( 4, "Echo",    6, 4,  14),
                ( 5, "Delta",   6, 3,  20),
                ( 6, "Alpha",   6, 3,  -6),
                ( 7, "Juliet",  6, 3, -19),
                ( 8, "Charlie", 6, 2.5, -23),
                ( 9, "India",   6, 2,  -3),
                (10, "Foxtrot", 6, 2, -18),
                (11, "Hotel",   6, 1.5, -50),
                (12, "Lima",    6, 1, -41),
            ],
        },
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
    tourney.set_rank_method_id(rank_method_id)

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
    desired_tests = sys.argv[1:]
    desired_tests = set(desired_tests)
    for test in tests:
        if desired_tests and test["name"] not in desired_tests:
            continue
        print("Test %s..." % (test["name"]))
        run_rank_test(test["name"], test["player_names"],
                test["games_per_round"], test["standings_per_round"],
                test["rank"], test.get("withdrawals_after_round", {}),
                test.get("unwithdrawals_after_round", {}),
                test.get("additions_after_round", {}))
        print("Test %s passed." % (test["name"]))

if __name__ == "__main__":
    main()
