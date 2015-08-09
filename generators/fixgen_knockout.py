import countdowntourney;
import htmlform;
import urllib;
import random;
import cgi;
import cgicommon;

name = "Knockout Fixture Generator";

# This can generate many subtly different knockout series, so we need to ask
# the user quite a few questions.

# Page 1:
# How many players in the knockout (minimum 2)?
# If this is not a power of two, some players may be given byes to the second
# round.
#
# What is this knockout series called? [optional]
# You only really need to fill this in if you're generating multiple knockout
# series, such as one for each of a series of divisions. You are going to
# generate the whole knockout series through to the final, so don't call this
# something like "Quarter Finals" because then you'll end up with rounds called
# "Quarter Finals Quarter Finals", "Quarter Finals Semi Finals" and
# "Quarter Finals Final". Call it something like "Division A". Or leave it
# blank.

# Page 2:
# How should we determine which players play in the knockout, and in what order?
#   * Top N players by performance in prelims
#   * Top N players by rating
#   * N players in a random draw
#   * N players which I will specify
#
# From what stage should losers proceed to a losers' playoff, such as the
# Third/Fourth Place playoff, the Fifth/Sixth/Seventh/Eighth place playoff, etc?
#   * No playoffs
#   * Third/fourth place
#   * 5th-8th place
#   * 9th-16th place
#     (and so on depending on how many players, but only players who played in
#      a round with a power of two players can proceed to playoffs)

# Page 3:
# Each player has been assigned a number between 1 and N.
# [ Players 1-M will receive a bye. ]
#
# If you want to modify the draw, do so now and press "Use modified draw".
# 
# #1  [dropdown]  Conor Travers (6 wins, 380 points)
# #2  [dropdown]  Innis Carson (6 wins, 377 points)
# #3  [dropdown]  Mark Deeks (6 wins, 371 points)
# #4  [dropdown]  Jonathan Rawlinson (5 wins, 373 points, 5 vowels)
# #5  [dropdown]  ... etc.
#
# [submit] Use modified draw
#
# Quarter-final:
# 1  (#1) Conor Travers v (#8) Jon Corby
# 2  (#2) Innis Carson v (#7) Ryan Taylor
# 3  (#3) Mark Deeks v (#6) Kirk Bevins
# 4  (#4) Jonathan Rawlinson v (#5) Jack Worsley
#
# Semi-final: 
# 1  Winner QF1 v Winner QF4
# 2  Winner QF2 v Winner QF3
#
# Final:
# 1  Winner SF1 v Winner SF2
#
# [submit] Accept Fixtures


# Procedure:
# Take the top N players, ranked in order according to the tournament rules
# and/or the user's request for this knockout series. We'll call these "seeds"
# regardless of whether they're based on performance. So even if the draw was
# random, there's still a No.1 Seed. We'll call these #1, #2, ... etc for short.
# 
#    If N is not a power of two:
#        Find the largest power of two, T, smaller than N
#        Take the bottom 2(N-T) players, that is, players numbered from
#        #(T - (N - T - 1)) to #N, and make them play in prelims, in the
#        manner #(T-(N-T-1)) v #N, #(T-(N-T)) v #(N-1), etc.
#
#        The top N - 2(N - T) players get a bye.
#        In the first (non-prelim) knockout round, containing T players,
#        F(1) plays F(T)
#        F(2) plays F(T-1)
#        and so on.
#        
#        F(x) is defined as:
#            if x <= N - 2(N - T), then #x              (player with a bye)
#            else, winner of prelim 1 + N-T - (T-x)     (player who won a prelim)
#    else:
#        #1 plays #N
#        #2 plays #(N-1)
#        etc.
#
#    Subsequent rounds:
#        Match M of a round is the winner of match M of the previous round
#        versus the winner of match G-(M-1) of the previous round, where G
#        is the number of games in the previous round.
#
#        If necessary, match M of a play-off round is the loser of match M of
#        the previous round versus the loser of match G-(M-1) of the previous
#        round, with G having the same definition as above.

name = "Knockout Fixture Generator"
description = "Generate a series of knockout rounds starting with a specified set of players, to form a single-elimination tournament.";

def make_short_name(num_players):
    if num_players == 2:
        return "FINAL";
    elif num_players == 4:
        return "SF";
    elif num_players == 8:
        return "QF";
    else:
        return "L%d" % num_players;

def make_round_name(num_players):
    if num_players == 2:
        return "Final";
    elif num_players == 4:
        return "Semi-Finals";
    elif num_players == 8:
        return "Quarter-Finals";
    else:
        return "Last %d" % num_players;

def generate_knockout(tourney, seeds, next_round_no=None):
    rounds = [];
    fixtures = [];

    num_players = len(seeds);

    if num_players < 2:
        return ([], []);

    # Find largest power of two not larger than num_players
    base = 1;
    while 2 ** base < num_players:
        base += 1;
    
    po2 = 2 ** base;
    if po2 > num_players:
        po2 = 2 ** (base - 1);
    
    if next_round_no is None:
        current_rounds = tourney.get_rounds();
        if not current_rounds:
            next_round_no = 1;
        else:
            next_round_no = max(map(lambda x : x["num"], current_rounds)) + 1;

    if po2 != num_players:
        # The bottom 2(num_players - po2) play in prelims

        nonbyed = seeds[-(2 * (num_players - po2)):];
        short_name = "L%d" % num_players;
        left = 0;
        right = len(nonbyed) - 1;
        seq = 1;
        while left < right:
            g = countdowntourney.Game(next_round_no, seq, seq, short_name, nonbyed[left], nonbyed[right]);
            seq += 1;
            left += 1;
            right -= 1;
            fixtures.append(g);
        rounds.append({
            "round" : next_round_no,
            "name" : "Last %d" % num_players,
            "type" : short_name
        });

        seeds_next_round = seeds[0:(num_players - len(nonbyed))];
        for f in fixtures:
            seeds_next_round.append(countdowntourney.PlayerPending(f.round_no, f.seq, True, short_name))
    else:
        # Play seeds[0] against seeds[n-1], seeds[1] against seeds[n-2], etc
        left = 0;
        right = num_players - 1;
        seq = 1;
        short_name = make_short_name(num_players);
        round_name = make_round_name(num_players);
        seeds_next_round = [];
        while left < right:
            g = countdowntourney.Game(next_round_no, seq, seq, short_name, seeds[left], seeds[right]);
            left += 1;
            right -= 1;
            seq += 1;
            fixtures.append(g);
            seeds_next_round.append(countdowntourney.PlayerPending(g.round_no, g.seq, True, short_name));
        rounds.append({
            "round" : next_round_no,
            "name" : round_name,
            "type" : short_name
        });

    (next_rounds, next_fixtures) = generate_knockout(tourney, seeds_next_round, next_round_no + 1);

    return (rounds + next_rounds, fixtures + next_fixtures);

###############################################################################

def get_player_standing(standings, player_name):
    for s in standings:
        if s[1] == player_name:
            return s;
    return None;

def get_user_form(tourney, settings):
    elements = [];

    num_players = settings.get("num_players");
    if num_players:
        try:
            num_players = int(num_players);
            num_players_in_tourney = len(tourney.get_active_players());
            if num_players < 2 or num_players > num_players_in_tourney:
                elements.append(htmlform.HTMLFragment("<p><strong>%d is an invalid number of players: must be between 2 and %d.</strong></p>" % (num_players, num_players_in_tourney)));
                num_players = None;
        except ValueError:
            elements.append(htmlform.HTMLFragment("<p><strong>The number of players must be a number.</strong></p>"));
            num_players = None;

    player_selection_mode = settings.get("player_sel_mode");
    if player_selection_mode not in ("topntable", "topnrating", "random", "manual"):
        player_selection_mode = None;

    if not num_players:
        # Page 1
        elements.append(htmlform.HTMLFormTextInput("How many players?", "num_players", "", other_attrs={ "size" : "4" } ));
        elements.append(htmlform.HTMLFormSubmitButton("submit", "Submit"));
    elif not player_selection_mode:
        # Page 2
        elements.append(htmlform.HTMLFragment("<p>How do you want to pick these %d players?</p>" % num_players));
        sel_options = [];
        sel_options.append(htmlform.HTMLFormDropDownOption("topntable", "Top %d players by table position" % num_players));
        sel_options.append(htmlform.HTMLFormDropDownOption("topnrating", "Top %d players by rating" % num_players));
        sel_options.append(htmlform.HTMLFormDropDownOption("random", "%d players in a random draw" % num_players));
        sel_options.append(htmlform.HTMLFormDropDownOption("manual", "Specify draw manually"));
        elements.append(htmlform.HTMLFragment("<p>"));
        elements.append(htmlform.HTMLFormDropDownBox("player_sel_mode", sel_options));
        elements.append(htmlform.HTMLFormHiddenInput("page2", "1"));
        elements.append(htmlform.HTMLFragment("</p><p>"));
        elements.append(htmlform.HTMLFormSubmitButton("submit", "Pick Players"));
        elements.append(htmlform.HTMLFragment("</p>"));
    else:
        # Page 3

        players = tourney.get_active_players();
        standings = tourney.get_standings();

        # If we've just come from page 2, decide on initial player names in
        # "settings" for seed1 ... seedN.
        if settings.get("page2"):
            del settings["page2"];
            if player_selection_mode == "topntable":
                seed = 1;
                for standing in standings[0:num_players]:
                    settings["seed%d" % seed] = standing[1];
                    seed += 1;
            elif player_selection_mode == "topnrating":
                players_by_rating = sorted(players, key=lambda x : x.rating, reverse=True);
                seed = 1;
                for p in players_by_rating[0:num_players]:
                    settings["seed%d" % seed] = p.name;
                    seed += 1;
            elif player_selection_mode == "random":
                random_player_order = players[:];
                random.shuffle(random_player_order);
                seed = 1;
                for p in random_player_order[0:num_players]:
                    settings["seed%d" % seed] = p.name;
                    seed += 1;
        
        all_seeds_set = True;
        found_dupes = False;
        seed_players = [ None for i in range(num_players) ];

        elements.append(htmlform.HTMLFragment("<p>Use the following %d players in the knockout series...</p>" % num_players));
        
        # Make N drop-down boxes, each containing the N players
        for seed_index in range(1, num_players + 1):
            keyname = "seed%d" % seed_index;
            current_player_name = settings.get(keyname);

            if current_player_name:
                for p in players:
                    if current_player_name == p.get_name():
                        break;
                else:
                    # Don't recognise this player
                    current_player_name = None;
            else:
                current_player_name = None;

            if not current_player_name:
                all_seeds_set = False;

            options = [];
            options.append(htmlform.HTMLFormDropDownOption("", "--- select player ---", current_player_name is None));
            for standing in standings:
                player = tourney.get_player_from_name(standing[1]);
                player_string = "%d. %s (%d wins, %d draws, %d points)" % (standing[0], player.get_name(), standing[3], standing[5], standing[4]);
                options.append(htmlform.HTMLFormDropDownOption(player.get_name(), player_string, (player.get_name() == current_player_name)));
                if player.get_name() == current_player_name:
                    if player in seed_players:
                        # player is already in seed_players, so we have
                        # a duplicate
                        found_dupes = True;
                        all_seeds_set = False;
                    seed_players[seed_index - 1] = player;

            elements.append(htmlform.HTMLFragment("#%d " % seed_index));
            elements.append(htmlform.HTMLFormDropDownBox("seed%d" % seed_index, options));
            elements.append(htmlform.HTMLFragment("<br />"));

        if found_dupes:
            elements.append(htmlform.HTMLFragment("<p><strong>Warning</strong>: one or more players appears more than once above. You need to fix this before generating fixtures.</p>"));

        # Are any of the seeds involved in a tie?
        if player_selection_mode == "topntable":
            ties_mentioned = [];
            for p in seed_players:
                if p:
                    player_standing = None;
                    for s in standings:
                        if s[1] == p.name:
                            player_standing = s;
                            break;
                    for s in standings:
                        if (s[3] * 2 + s[5] == player_standing[3] * 2 + player_standing[5] and
                                s[4] == player_standing[4] and
                                s[1] != player_standing[1] and
                                (s[1], player_standing[1]) not in ties_mentioned
                                and (player_standing[1], s[1]) not in ties_mentioned):
                            elements.append(htmlform.HTMLFragment("<p><strong>Warning:</strong> %s and %s have the same number of wins and points and have been ordered arbitrarily.</p>" % (player_standing[1], s[1])));
                            ties_mentioned.append((s[1], player_standing[1]));

        elements.append(htmlform.HTMLFormSubmitButton("setseeds", "Save Order"));

        if all_seeds_set:
            # All seed positions have a player in them and no player appears
            # more than once.

            # Work out fixtures and display them.
            (rounds, fixtures) = generate_knockout(tourney, seed_players);
            
            if settings.get("generate"):
                # The fixtures have already been okayed, so nothing more to do
                return None;

            html = "<h2>Fixture list</h2>\n";
            html += "<p>The following rounds will be generated</p>\n";
            html += "<blockquote>\n";
            for r in rounds:
                html += "<li>%s</li>\n" % cgi.escape(r["name"]);
            html += "</blockquote>\n";
            elements.append(htmlform.HTMLFragment(html));

            html = "<p>The following fixtures will be generated</p>\n";
            prev_round_no = None;
            html += "<table>";
            for g in fixtures:
                if g.round_no != prev_round_no:
                    round_name = None;
                    for r in rounds:
                        if r["round"] == g.round_no:
                            round_name = r["name"];
                            break;
                    if not round_name:
                        round_name = "Round %d" % g.round_no;
                    html += "<tr><th colspan=\"4\">%s</td></tr>\n" % round_name;
                prev_round_no = g.round_no;
                html += "<tr>";
                html += "<td>%d</td>" % g.seq;
                html += "<td>%s</td>" % str(g.p1);
                html += "<td>v</td>";
                html += "<td>%s</td>" % str(g.p2);
                html += "</tr>";
            html += "</table>";
            elements.append(htmlform.HTMLFragment(html));

            elements.append(htmlform.HTMLFragment("<p>Click the button below to proceed. On the next screen you can review the fixtures and accept them.</p>"));
            elements.append(htmlform.HTMLFormSubmitButton("generate", "Yep, looks good to me"));
        else:
            if "generate" in settings:
                del settings["generate"];
    
    return htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s" % urllib.quote_plus(tourney.name), elements);

def check_ready(tourney):
    # If there are at least two players registered, that's fine
    players = tourney.get_active_players();
    if len(players) >= 2:
        return (True, None);
    else:
        return (False, "At least two players are required.");

def generate(tourney, settings):
    # Use num_players and seed1 ... seedN to generate the knockout series
    # and return the new rounds and fixtures.

    (ready, excuse) = check_ready(tourney);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    players = tourney.get_active_players();

    num_players = settings.get("num_players");
    if not num_players:
        raise countdowntourney.FixtureGeneratorException("Number of players not specified");
    try:
        num_players = int(num_players);
        if num_players < 2 or num_players > len(players):
            raise countdowntourney.FixtureGeneratorException("Number of players must be between 2 and %d" % len(players));
    except ValueError:
        raise countdowntourney.FixtureGeneratorException("Number of players is not valid");
    
    seeds = [];
    for seed in range(1, num_players + 1):
        player_name = settings.get("seed%d" % seed);
        if player_name:
            for p in players:
                if p.name == player_name:
                    if p in seeds:
                        raise countdowntourney.FixtureGeneratorException("Player \"%s\" appears more than once in the seed list" % player_name);
                    seeds.append(p);
                    break;
            else:
                raise countdowntourney.FixtureGeneratorException("Seed %d \"%s\" is not a known player name" % (seed, player_name));
        else:
            raise countdowntourney.FixtureGeneratorException("Seed %d is not specified" % seed);
    
    (rounds, fixtures) = generate_knockout(tourney, seeds);

    d = dict();
    d["fixtures"] = fixtures;
    d["rounds"] = rounds;

    return d;
