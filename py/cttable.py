#!/usr/bin/python3

import sys

# Classes used for assigning table numbers to groups, taking into account any
# accessibility requirements. This is nothing to do with fixture generation
# (who plays whom) - that's done by the fixture generators.

class CandidateTable(object):
    def __init__(self, group, round_no, division, table_no, game_type, repeat_threes):
        self.group = group
        self.round_no = round_no
        self.division = division
        self.table_no = table_no
        self.game_type = game_type
        self.repeat_threes = repeat_threes

    def get_group(self):
        return self.group

    def get_round_no(self):
        return self.round_no

    def get_division(self):
        return self.division

    def get_table_no(self):
        return self.table_no

    def get_game_type(self):
        return self.game_type

    def get_repeat_threes(self):
        return self.repeat_threes

    def set_table_no(self, table_no):
        self.table_no = table_no

class TableVotingGroup(object):
    def __init__(self, division, group, accessible_tables, acc_default, natural_table_numbers, initial_order_position):
        self.division = division
        self.group = group[:]
        self.accessible_tables = accessible_tables
        self.acc_default = acc_default
        self.natural_table_numbers = natural_table_numbers[:]
        self.occupied_tables = set()
        self.initial_order_position = initial_order_position

    def is_phantom_group(self):
        return False

    def get_division(self):
        return self.division

    def get_group(self):
        return self.group

    def get_player_names_by_priority(self):
        # Return the list of player names by priority, with the highest
        # priority first. Priority is (requires accessible, has preference).
        players = sorted(self.group, key=lambda x : (int(x.is_requiring_accessible_table()), int(x.get_preferred_table() is not None)), reverse=True)
        return tuple([ p.get_name() for p in players ])

    def is_accessible_table(self, table_no):
        if self.acc_default:
            return table_no not in self.accessible_tables
        else:
            return table_no in self.accessible_tables

    def set_occupied_tables(self, occupied_tables):
        self.occupied_tables = occupied_tables.copy()

    def get_pref_sort_key(self):
        return (-self.get_winner_weight(), int(self.is_phantom_group()),
                self.get_division(), self.get_player_names_by_priority())

    def get_pref_sort_key_preserve_original_order(self):
        return (int(self.is_phantom_group()), self.get_division(),
                self.initial_order_position)

    def get_preferred_table_aux(self, occupied_tables):
        preferred_table = None
        pref_weight = 0
        num_acc_players = 0

        # Ask if any players have any specific table numbers they prefer, or
        # if they require an accessible table.
        acc_tables_pref = {}
        all_tables_pref = {}
        for player in self.group:
            player_pref_weight = 0
            pref = player.get_preferred_table()
            if pref is not None and pref not in occupied_tables:
                if self.is_accessible_table(pref):
                    acc_tables_pref[pref] = acc_tables_pref.get(pref, 0) + 1
                else:
                    all_tables_pref[pref] = all_tables_pref.get(pref, 0) + 1
                if player.is_requiring_accessible_table():
                    # Player requires a specific accessible table
                    player_pref_weight = 1000000
                else:
                    # Player requires a specific table, but not accessible
                    player_pref_weight = 1
            elif player.is_requiring_accessible_table():
                # Player requires an accessible table, but not a specific one
                player_pref_weight = 1000

            if player.is_requiring_accessible_table():
                num_acc_players += 1

            pref_weight += player_pref_weight

        # If there are any players in this group who require an accessible
        # table, make sure they get one.
        if num_acc_players > 0:
            if len(acc_tables_pref) == 0:
                pref_tables = all_tables_pref
            else:
                pref_tables = acc_tables_pref
        else:
            pref_tables = all_tables_pref

        if len(pref_tables) > 0:
            # Pick the most-preferred table in pref_tables. In the event of a
            # tie, pick the most-preferred table in pref_tables which is also
            # in the natural list. If it's still a tie, pick the lowest such
            # table.
            max_pref = max([pref_tables[x] for x in pref_tables])
            candidate_tables = set([ t for t in pref_tables if pref_tables[t] == max_pref ])
            for t in self.natural_table_numbers:
                if t in candidate_tables:
                    preferred_table = t
                    break
            if preferred_table is None:
                preferred_table = min(candidate_tables)
        else:
            # There are no specific preferences. If at least one player
            # requires an accessible table, choose an accessible table from
            # the natural list, or any accessible table if there are no
            # accessible tables in the natural list.
            for t in self.natural_table_numbers:
                if t not in occupied_tables and (num_acc_players == 0 or self.is_accessible_table(t)):
                    preferred_table = t
                    break
            if preferred_table is None:
                if self.acc_default:
                    # All tables are accessible except those listed
                    t = 1
                    while not (t not in occupied_tables and (num_acc_players == 0 or self.is_accessible_table(t))):
                        t += 1
                    preferred_table = t
                else:
                    if num_acc_players > 0:
                        # Pick the lowest-numbered unoccupied accessible table.
                        for t in sorted(self.accessible_tables):
                            if t not in occupied_tables:
                                preferred_table = t
                                break

                    if preferred_table is None:
                        # If nobody in this group needs an accessible table, or
                        # there are no accessible tables left, pick the lowest-
                        # numbered unoccupied table.
                        t = 1
                        while t in occupied_tables:
                            t += 1
                        preferred_table = t

        # Return the preferred table, and how much we prefer it.
        return (preferred_table, pref_weight)

    def get_winner_weight(self):
        return self.get_preferred_table_aux(self.occupied_tables)[1]

    def get_preferred_table(self):
        return self.get_preferred_table_aux(self.occupied_tables)[0]

class PhantomTableVotingGroup(TableVotingGroup):
    def __init__(self, division, group, accessible_tables, acc_default, natural_table_numbers, initial_order_position):
        super(PhantomTableVotingGroup, self).__init__(division, group, accessible_tables, acc_default, natural_table_numbers, initial_order_position)

    def is_phantom_group(self):
        return True

def find_next_not_in_set(cur, s):
    cur += 1
    while cur in s:
        cur += 1
    return cur

def get_candidate_tables(generated_groups_round, players_without_games, occupied_tables, accessible_tables, acc_default):
    current_table_no = 0
    voting_groups = []

    # Mapping of division numbers to a list of table numbers which the
    # groups for that division would naturally use if they were just
    # handed out in order
    natural_div_to_table_numbers = {}

    div_game_type = {}
    div_repeat_threes = {}

    lowest_not_in_natural = None
    round_no = generated_groups_round.get_round_no()
    initial_order_position = 0

    for dv in generated_groups_round.get_divisions():
        div_num = dv.get_division()
        div_game_type[div_num] = dv.get_game_type()
        div_repeat_threes[div_num] = dv.get_repeat_threes()
        num_groups = len(dv.get_groups())
        table_number_list = []

        for i in range(len(dv.get_groups())):
            current_table_no = find_next_not_in_set(current_table_no, occupied_tables)
            table_number_list.append(current_table_no)
            lowest_not_in_natural = current_table_no + 1
        natural_div_to_table_numbers[div_num] = table_number_list

        for group in dv.get_groups():
            voting_groups.append(TableVotingGroup(div_num, group, accessible_tables, acc_default, natural_div_to_table_numbers.get(div_num, []), initial_order_position))
            initial_order_position += 1
            for p in group:
                if p in players_without_games:
                    players_without_games.remove(p)

    # Each player not given a game in this round yet forms their own
    # "phantom" voting group. This group can reserve tables if it
    # prefers a particular table, but can't actually have any fixtures
    # generated for it.
    if lowest_not_in_natural is None:
        remaining_tables = []
    else:
        # The "natural" list of tables for these phantom players is
        # whatever tables are left after we've generated the natural
        # lists for the other divisions.
        remaining_tables = range(lowest_not_in_natural, lowest_not_in_natural + len(players_without_games))

    for rp in players_without_games:
        voting_groups.append(PhantomTableVotingGroup(rp.get_division(), [rp], accessible_tables, acc_default, natural_div_to_table_numbers.get(rp.get_division(), remaining_tables), initial_order_position))
        initial_order_position += 1

    for vg in voting_groups:
        vg.set_occupied_tables(occupied_tables)

    preference_voting_groups = []
    ordinary_voting_groups = []
    for v in voting_groups:
        if v.get_winner_weight() > 0:
            preference_voting_groups.append(v)
        else:
            ordinary_voting_groups.append(v)

    # Order the voting groups which have a preference by vehemence of
    # preference descending, then by whether it's a phantom group
    # (prefer groups we're assigning now to hypothetical future groups),
    # then by division (prefer earlier divisions), then by the names of
    # the players who have preferences (so that if multiple players
    # require accessible tables they're more likely to stay where they
    # are between rounds because they'll be in the same place relative
    # to each other in the pecking order).
    #preference_voting_groups = sorted(preference_voting_groups, key=lambda x : (-x.get_winner_weight(occupied_tables), int(x.is_phantom_group()), x.get_division(), x.get_player_names_by_priority()))
    preference_voting_groups = sorted(preference_voting_groups, key=lambda x : x.get_pref_sort_key())

    # Starting with the group with the strongest preference, ask each
    # voting group which table it prefers, not including the set of
    # tables which have already been taken. The voting groups without
    # preferences then choose the remaining tables in the order those
    # groups were originally given to us.
    candidate_tables = []

    voting_groups = preference_voting_groups + ordinary_voting_groups
    while preference_voting_groups or ordinary_voting_groups:
        if preference_voting_groups:
            vg = preference_voting_groups[0]
        else:
            vg = ordinary_voting_groups[0]

        vg.set_occupied_tables(occupied_tables)
        div = vg.get_division()
        preferred_table = vg.get_preferred_table()

        #sys.stderr.write("%s: preferred table %d, weight %d\n" % (", ".join(list(vg.get_player_names_by_priority())), preferred_table, vg.get_winner_weight()))

        occupied_tables.add(preferred_table)
        if not vg.is_phantom_group():
            ct = CandidateTable(vg.get_group(), round_no, div, preferred_table, div_game_type[div], div_repeat_threes[div])
            candidate_tables.append(ct)

        if preference_voting_groups:
            # Recalculate the order of the remaining preference voting groups,
            # taking into account that a previously unoccupied table is now
            # occupied.
            new_preference_voting_groups = []
            new_ordinary_voting_groups = []
            for vg in preference_voting_groups:
                vg.set_occupied_tables(occupied_tables)
            for vg in preference_voting_groups[1:]:
                if vg.get_winner_weight() == 0:
                    # A preference group has become an ordinary group
                    # because all its preferences have been occupied.
                    new_ordinary_voting_groups.append(vg)
                else:
                    new_preference_voting_groups.append(vg)

            preference_voting_groups = sorted(new_preference_voting_groups, key=lambda x : x.get_pref_sort_key())
            if new_ordinary_voting_groups:
                ordinary_voting_groups = sorted(ordinary_voting_groups + new_ordinary_voting_groups, key=lambda x : x.get_pref_sort_key_preserve_original_order())
        else:
            # We picked an ordinary voting group from the front of that list,
            # so remove it.
            ordinary_voting_groups = ordinary_voting_groups[1:]

    # Sort the list of candidate tables by round, division and table
    # number, then convert them into fixtures.
    candidate_tables = sorted(candidate_tables, key=lambda x : (x.get_round_no(), x.get_division(), x.get_table_no()))

    return candidate_tables
