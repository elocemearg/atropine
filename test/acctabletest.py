#!/usr/bin/python3

import sys

sys.path.append("py")

import random
import countdowntourney
import fixgen
import getopt
import cttable

def dump_test_info(test_num, players, accessible_tables, acc_players, ggr, candidate_tables):
    print("")
    print("TEST %d" % (test_num))
    print("Input groups:")
    for ggd in ggr.get_divisions():
        for ggg in ggd.get_groups():
            print("Group: " + " ".join([str(x.get_id()) for x in ggg]))
    print("Accessible tables: " + " ".join([ str(x) for x in sorted(accessible_tables) ] ))
    print("Players requiring accessible table: " + " ".join([ str(p.get_id()) for p in acc_players ]))
    print("Players preferring specific tables: " + ", ".join([ "%d->%d" % (p.get_id(), p.get_preferred_table()) for p in players if p.get_preferred_table() is not None ]))
    print("Candidate tables: ")
    for ct in candidate_tables:
        print("%3d: %s" % (ct.get_table_no(), " ".join([ str(p.get_id()) for p in ct.get_group() ])))
    print("")

def run_cttable_tests(num_players, players_per_table, num_tests, verbose=False):
    test_num = 1
    while test_num <= num_tests:
        # Generate a random list of players
        players = []
        preferred_tables = set()
        num_acc_players = 0
        round_no = 1
        div = 0
        for i in range(num_players):
            p = countdowntourney.Player(name=("Player %d" % (i)), rating=1000,
                    team=None, short_name=None, withdrawn=False, division=div,
                    division_fixed=False, player_id=i)

            # Make some players require an accessible table, and some of those
            # prefer a specific table number.
            if random.randint(0, 9) == 0:
                p.require_accessible_table = True
                num_acc_players += 1
                if random.randint(0, 2) == 0:
                    pref_table = random.randint(1, num_players // players_per_table)
                    p.preferred_table = pref_table
                    preferred_tables.add(pref_table)
            players.append(p)

        accessible_tables = []
        num_tables = num_players // players_per_table
        tab_nums = list(range(1, num_tables + 1))
        random.shuffle(tab_nums)
        for pref_table in preferred_tables:
            accessible_tables.append(pref_table)
            tab_nums.remove(pref_table)
        for i in range(len(preferred_tables), min(num_acc_players, num_tables)):
            accessible_tables.append(tab_nums[i - len(preferred_tables)])

        # We should now have enough accessible tables for everybody, and each of
        # the specific tables preferred by a player will be accessible

        # Come up with random groups
        ggr = fixgen.GeneratedGroupsRound(round_no)
        shuffled_players = players[:]
        random.shuffle(shuffled_players)
        groups = []
        active_players_not_grouped = [ p for p in players if not p.is_withdrawn() ]
        num_tables_to_gen = num_players // players_per_table

        for i in range(num_tables_to_gen):
            group = []
            for j in range(players_per_table):
                p = shuffled_players[i * players_per_table + j]
                active_players_not_grouped.remove(p)
                group.append(p)
            ggr.add_group(div, group)

        candidate_tables = cttable.get_candidate_tables(ggr, active_players_not_grouped, set(), accessible_tables, False)
        acc_players = [ p for p in players if p.is_requiring_accessible_table() ]

        if verbose:
            dump_test_info(test_num, players, accessible_tables, acc_players, ggr, candidate_tables)

        # Check that every player who requires an accessible table is on one,
        # and that either every player who prefers a specific table is on their
        # preferred table, or:
        #     every player not on their preferred table:
        #       shares it with someone who requires an accessible table and who
        #         is on their preferred table
        #       isn't on their preferred table because their preferred table is
        #         occupied by a player who has an accessibility requirement and
        #         prefers that table
        assert(len(candidate_tables) == num_tables_to_gen)
        for ct in candidate_tables:
            assert(ct.get_round_no() == round_no)
            table_no = ct.get_table_no()
            is_acc = (table_no in accessible_tables)
            for p in ct.get_group():
                if p.is_requiring_accessible_table():
                    if not is_acc:
                        if not verbose:
                            dump_test_info(test_num, players, accessible_tables, acc_players, ggr, candidate_tables)
                        print("Player %d isn't on an accessible table" % (p.get_id()))
                        assert(False)
                pref_table = p.get_preferred_table()
                if pref_table is not None:
                    if pref_table != table_no:
                        for otherp in ct.get_group():
                            if otherp.is_requiring_accessible_table() and otherp.get_preferred_table() == table_no:
                                break
                        else:
                            for otherct in candidate_tables:
                                if otherct.get_table_no() == pref_table:
                                    for otherp in otherct.get_group():
                                        if otherp.is_requiring_accessible_table() and otherp.get_preferred_table() == pref_table:
                                            break
                                    else:
                                        if not verbose:
                                            dump_test_info(test_num, players, accessible_tables, acc_players, ggr, candidate_tables)
                                        print("Player %d isn't on their preferred table (%d) for some reason" % (p.get_id(), pref_table))
                                        assert(False)
        test_num += 1

def main():
    num_players = 36
    players_per_table = 3
    num_tests = 100
    verbose = False

    opts, args = getopt.getopt(sys.argv[1:], "p:t:n:v")
    for o, a in opts:
        if o == "-p":
            num_players = int(a)
        elif o == "-t":
            players_per_table = int(a)
        elif o == "-n":
            num_tests = int(a)
        elif o == "-v":
            verbose = True
        else:
            print("lol wat")
            sys.exit(1)

    if num_players <= 0:
        sys.stderr.write("Number of players (-p %d) must be a positive number.\n" % (num_players))
        sys.exit(1)
    if players_per_table < 2:
        sys.stderr.write("Number of players per table (-t %d) must be at least 2.\n" % (players_per_table))
        sys.exit(1)
    if num_players % players_per_table != 0:
        sys.stderr.write("Number of players (-p %d) must be a multiple of the number of players per table (-t %d).\n" % (num_players, players_per_table))
        sys.exit(1)

    run_cttable_tests(num_players, players_per_table, num_tests, verbose)
    print("Successfully ran %d random tests with %d players, %d players per table." % (num_tests, num_players, players_per_table))

# Test routine
if __name__ == "__main__":
    main()
