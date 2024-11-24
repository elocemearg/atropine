#!/usr/bin/python3

from countdowntourney import FixtureGeneratorException

class GeneratedGroupsDivision(object):
    def __init__(self, division):
        self.division = division
        self.groups = []
        self.repeat_threes = False
        self.game_type = "P"

    # "group" should be a list of countdowntourney.Player objects
    def add_group(self, group):
        self.groups.append(group[:])

    def get_groups(self):
        return self.groups[:]

    def get_division(self):
        return self.division

    def set_repeat_threes(self, value=True):
        self.repeat_threes = value

    def get_repeat_threes(self):
        return self.repeat_threes

    def set_game_type(self, game_type):
        self.game_type = game_type

    def get_game_type(self):
        return self.game_type

class GeneratedGroupsRound(object):
    def __init__(self, round_no):
        self.round_no = round_no
        self.divisions = {}
        self.name = None

    def get_or_create_division_object(self, division):
        div_obj = self.divisions.get(division, None)
        if div_obj is None:
            div_obj = GeneratedGroupsDivision(division)
            self.divisions[division] = div_obj
        return div_obj

    def add_group(self, division, group):
        div_obj = self.get_or_create_division_object(division)
        div_obj.add_group(group)

    def get_round_no(self):
        return self.round_no

    def set_round_name(self, name):
        self.name = name

    def get_round_name(self):
        if self.name is None:
            return "Round %d" % (self.round_no)
        else:
            return self.name

    def get_divisions(self):
        return [ self.divisions[div] for div in sorted(self.divisions) ]

    def set_repeat_threes(self, division, value=True):
        div_obj = self.get_or_create_division_object(division)
        div_obj.set_repeat_threes(value)

    def set_game_type(self, division, game_type):
        self.get_or_create_division_object(division).set_game_type(game_type)

class GeneratedGroups(object):
    def __init__(self):
        self.rounds = {}

    def get_or_create_round_object(self, round_no):
        round_obj = self.rounds.get(round_no, None)
        if round_obj is None:
            round_obj = GeneratedGroupsRound(round_no)
            self.rounds[round_no] = round_obj
        return round_obj

    def add_group(self, round_no, division, group):
        round_obj = self.get_or_create_round_object(round_no)
        round_obj.add_group(division, group)

    def set_round_name(self, round_no, round_name):
        round_obj = self.get_or_create_round_object(round_no)
        round_obj.set_round_name(round_name)

    def set_repeat_threes(self, round_no, division, value=True):
        round_obj = self.get_or_create_round_object(round_no)
        round_obj.set_repeat_threes(division, value)

    def set_game_type(self, round_no, division, game_type):
        self.get_or_create_round_object(round_no).set_game_type(division, game_type)

    def get_rounds(self):
        return [ self.rounds[r] for r in sorted(self.rounds) ]

def get_table_sizes(num_players, table_size):
    if table_size == -5:
        # Tables of 5 and 3, where the tables of 3 play each other twice
        sizes = []
        if num_players < 8:
            raise FixtureGeneratorException("Number of players (%d) not compatible with selected table configuration (5&3)." % (num_players))
        while num_players > 0 and num_players % 5 != 0:
            sizes.append(3)
            num_players -= 3
        sizes += [ 5 for x in range(num_players // 5) ]
        prunes_required = 0
    else:
        prunes_required = (table_size - (num_players % table_size)) % table_size
        sizes = [ table_size for x in range((num_players + prunes_required) // table_size) ]
    return (sizes, prunes_required)
