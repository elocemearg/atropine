#!/usr/bin/python3

import sys
import itertools

sys.path.append("py")

import randomdraw

def verify_groups(groups, num_players, invalid_pairs, table_sizes):
    # Check that every player appears exactly once in groups
    players_not_seen = set(range(num_players))
    for g in groups:
        for p in g:
            if p < 0 or p >= num_players:
                print("verify_groups(): group %s contains invalid player %d, not in range [0, %d)" % (str(g), p, num_players))
                return False
            if p not in players_not_seen:
                print("verify_groups(): groups %s contains player %d more than once." % (str(groups), p))
                return False
            players_not_seen.remove(p)
    if len(players_not_seen) != 0:
        print("verify_groups(): groups %s does not contain the following expected players: %s" % (str(groups), str(players_not_seen)))
        return False
    
    # Check that the table sizes are correct
    if len(groups) != len(table_sizes):
        print("verify_groups(): incorrect number of groups: expected %d, got %d. groups: %s" % (len(table_sizes), len(groups), str(groups)))
        return False
    for i in range(len(groups)):
        if len(groups[i]) != table_sizes[i]:
            print("verify_groups(): groups[%d] has the wrong size (expected %d, got %d). groups: %s" % (i, table_sizes[i], len(groups[i]), str(groups)))
            return False

    # Now check that no group contains an invalid pair of players.
    invalid_pair_sets = []
    for p in range(num_players):
        invalid_pair_sets.append(set())
    for (x, y) in invalid_pairs:
        invalid_pair_sets[x].add(y)
        invalid_pair_sets[y].add(x)
    for g in groups:
        for (x, y) in itertools.combinations(g, 2):
            if x in invalid_pair_sets[y] or y in invalid_pair_sets[x]:
                print("verify_groups(): group %s is not valid: %d and %d are not allowed to be in the same group." % (str(g), x, y))
                return False

    return True

def fail(message, table_conf_str, num_players, trial, num_trials, round_no, invalid_pairs):
    print("Test failed: %s, num_players %d, trial %d/%d, round %d." % (table_conf_str, num_players, trial + 1, num_trials, round_no + 1))
    print("Reason: %s" % (message))
    sys.exit(1)

def test_case(num_players, table_sizes, num_trials, table_conf_str, is_3and5):
    if is_3and5:
        # 20 players (table_sizes [5, 5, 5, 5]) can't have two rounds.
        # In a second round, each player on table 1 would need to play one
        # player from each of tables 2, 3, 4 and a fifth nonexistent table.
        # So only play a second round if there are >= 25 players.
        num_rounds = 1 + num_players // 25
    else:
        num_rounds = 1 + len(table_sizes) // 3
    print("%s, %d players, %d rounds" % (table_conf_str, num_players, num_rounds))
    for t in range(num_trials):
        # The more players we have, the more rounds we should be
        # able to draw randomly without enforced repeats.
        invalid_pairs = []
        for r in range(num_rounds):
            (groups, search_required) = randomdraw.draw(table_sizes, invalid_pairs, 0)
            if not groups:
                fail("Failed to generate any groups!", table_conf_str, num_players, t, num_trials, r, invalid_pairs)
            if not verify_groups(groups, num_players, invalid_pairs, table_sizes):
                fail("Generated invalid group!", table_conf_str, num_players, t, num_trials, r, invalid_pairs)

            # Add these games to invalid_pairs for the next round
            for group in groups:
                for (x, y) in itertools.combinations(group, 2):
                    invalid_pairs.append((x, y))
                    invalid_pairs.append((y, x))

def main():
    for table_size in (2, 3, 5):
        if table_size == 5:
            # Weird 3&5 arrangement
            min_players = 8
            max_players = 100
            step_players = 1
            num_trials = 10
        else:
            # All tables have the same number of players
            min_players = table_size
            max_players = 100 - 100 % table_size
            step_players = table_size
            num_trials = 100

        for num_players in range(min_players, max_players + 1, step_players):
            if table_size == 5:
                table_sizes = []
                n = num_players
                while n % 5 != 0:
                    table_sizes.append(3)
                    n -= 3
                for i in range(n // 5):
                    table_sizes.append(5)
                num_tables = len(table_sizes)
                table_conf_str = "tables of 3&5"
            else:
                num_tables = num_players // table_size
                assert(num_players % table_size == 0)
                table_sizes = [ table_size for i in range(num_tables) ]
                table_conf_str = "tables of " + str(table_size)
            test_case(num_players, table_sizes, num_trials, table_conf_str, table_size == 5)
    print("Passed.")

if __name__ == "__main__":
    main()
