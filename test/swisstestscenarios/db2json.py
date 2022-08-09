#!/usr/bin/python3

import sys
import json
import sqlite3

"""
Take a tourney db and produce a JSON object like the following:
{
    "players" : [
        [ "name1", rating1 ],
        [ "name2", rating2 ],
        ...
        [ "nameN", ratingN ]
    ],
    "games" : [
        [ round_no, table_no, division, p1name, p1score, p2name, p2score, tiebreak ],
        ...
    ]
}

A "test" object must then be added to the top-level object, containing at
least a "group_size" member (e.g. 3) for it to be a valid test for
swissNscenariotest.py.
"""

if len(sys.argv) < 2:
    print("Usage: db2json.py /path/to/tourney.db", file=sys.stderr)
    sys.exit(1)

dbfilename = sys.argv[1]

db = sqlite3.connect(dbfilename)

cur = db.cursor()

cur.execute("""select g.round_no, g.table_no, g.division, pleft.name,
g.p1_score, pright.name, g.p2_score, g.tiebreak
from game g,
player pleft on g.p1 = pleft.id,
player pright on g.p2 = pright.id
where g.game_type = 'P' and g.p1_score is not null and g.p2_score is not null
order by g.round_no, g.table_no, g.seq;""")

games = []
for row in cur:
    games.append(
            [int(row[0]), int(row[1]), int(row[2]), row[3], int(row[4]),
                row[5], int(row[6]), bool(int(row[7]) != 0)]
    )

cur.close()

cur = db.cursor()

cur.execute("select name, rating from player order by id;")
players = []
for row in cur:
    players.append([row[0], float(row[1])])

cur.close()

db.close()

# Only use json.dumps for the individual entries, giving us more control
# over the formatting - don't want to start a new line after every list
# element but we don't want the whole file on one line either.
print("{")
print("\t\"players\" : [")

for (i, p) in enumerate(players):
    sys.stdout.write("\t\t")
    json.dump(p, sys.stdout)
    if i < len(players) - 1:
        sys.stdout.write(",")
    print("")
print("\t],")
print("\t\"games\" : [")
for (i, g) in enumerate(games):
    sys.stdout.write("\t\t")
    json.dump(g, sys.stdout)
    if i < len(games) - 1:
        sys.stdout.write(",")
    print("")
print("\t]")
print("}")
