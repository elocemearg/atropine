import sys
import random;
import countdowntourney;
import htmlform;
import swissN;
import cgicommon
import fixgen
import urllib
import gencommon

name = "Swiss Army Blunderbuss";
description = "Players are matched against opponents who have performed similarly to them so far in the tourney, but repeats of previous fixtures are avoided. This is the most commonly-used fixture generator for the second round onwards.";
valid_group_sizes = (2, 3, 4, 5, -5)

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def get_valid_group_sizes(num_players, num_rounds, has_auto_prune):
    sizes = [ gs for gs in valid_group_sizes if gs > 0 and (has_auto_prune or num_players % gs == 0) ]
    if num_players >= 8 and num_rounds > 0:
        sizes.append(-5)
    return sizes

def get_default_group_size(num_players, num_rounds, has_auto_prune):
    valid_sizes = get_valid_group_sizes(num_players, num_rounds, has_auto_prune)
    for size in (3, 2, 5, -5, 4):
        if size in valid_sizes:
            return size
    return None

def get_user_form(tourney, settings, div_rounds):
    div_group_size = dict()
    div_init_max_rematches = dict()
    div_init_max_win_diff = dict()

    prev_settings = settings.get_previous_settings()
    for key in prev_settings:
        if key not in settings and key != "submit":
            settings[key] = prev_settings[key]

    rounds = tourney.get_rounds();

    num_divisions = tourney.get_num_divisions()

    max_time = int_or_none(settings.get("maxtime", None))
    ignore_rematches_before_round = int_or_none(settings.get("ignorerematchesbefore", None))

    div_ready = []
    for div in range(num_divisions):
        if div in div_rounds:
            div_ready.append(False)
        else:
            div_ready.append(True)

    default_group_size = int_or_none(settings.get("groupsize", None))

    for div_index in sorted(div_rounds):
        group_size = int_or_none(settings.get("d%d_groupsize" % (div_index), None))
        if group_size is None or group_size == 0:
            group_size = default_group_size

        init_max_rematches = int_or_none(settings.get("d%d_initmaxrematches" % (div_index), "0"))

        init_max_win_diff = int_or_none(settings.get("d%d_initmaxwindiff" % (div_index), 2))

        games = tourney.get_games(game_type='P', division=div_index);
        players = [x for x in tourney.get_active_players() if x.division == div_index];

        if max_time is not None and max_time > 0 and group_size in valid_group_sizes and (group_size == -5 or tourney.has_auto_prune() or len(players) % group_size == 0):
            div_ready[div_index] = True

        div_group_size[div_index] = group_size
        div_init_max_rematches[div_index] = init_max_rematches
        div_init_max_win_diff[div_index] = init_max_win_diff

    if False not in div_ready and settings.get("submit") is not None:
        return None

    elements = [];
    javascript = """
<script type="text/javascript">
let click_time = 0;
let limit_seconds = 0;
let noticed_results_overdue = false;
let current_progress_text = "";


const gerunds = [
    "Exaggerating", "Refrigerating", "Bisecting", "Reordering", "Unseeding",
    "Reconstituting", "Inverting", "Convolving", "Reinventing",
    "Overpopulating", "Unwedging", "Tenderising", "Refactoring",
    "Frobnicating", "Normalising", "Factorising", "Transforming", "Relaying",
    "Decoupling", "Randomising", "Ignoring", "Disposing of", "Translating",
    "Restarting", "Entertaining", "Checking", "Verifying", "Flushing",
    "Contextualising", "Deconstructing", "Justifying", "Hacking", "Redrawing",
    "Reimagining", "Reinterpreting", "Reasoning with", "Impersonating",
    "Abbreviating", "Underestimating", "Misappropriating", "Constructing",
    "Preparing", "Redelivering", "Arguing over", "Grilling", "Baking",
    "Poaching", "Washing", "Stealing", "Emulsifying", "Discombobulating",
    "Correcting", "Extracting", "Unspooling", "Descaling", "Duplicating",
    "Overwriting", "Containerising", "Resetting", "Evaluating", "Compressing",
    "Plotting", "Mapping", "Indexing", "Cancelling", "Distributing",
    "Reconsidering", "Backtracking", "Avoiding", "Collecting", "Downloading",
    "Decompressing", "Connecting"
];

const nouns = [
    "seeding list", "rule book", "hypergrid", "network services", "timestamps",
    "multidimensional array", "decision tree", "player list",
    "weighting matrix", "instrument panel", "database", "videprinter",
    "standings table", "preclusion rules", "event handlers", "dynamic modules",
    "hypertext", "fixture generator", "linked lists", "hash tables",
    "system clock", "file descriptors", "syntax tree", "binary tree",
    "dictionary", "homework", "breakfast", "contextualiser", "supercluster",
    "record books", "sandwiches", "grouping strategy", "reality", "spatula",
    "Eyebergine", "scripts", "blockchain", "phone charger", "fixtures",
    "associative arrays", "browser window", "subfolders", "scorecard",
    "references", "ranking order", "to-do list", "column headings", "fonts"
];

const specials = [
    "Bribing officials", "Emptying bins", "Feeding cat",
    "Rewinding tape", "Invading privacy", "Walking plank",
    "Kicking tyres", "Tapping barometer", "Serving hot",
    "Deploying parachute", "Cleaning up mess", "Straightening tie",
    "Seasoning to taste", "Stealing towels", "Reversing polarity",
    "Untangling headphones", "Compounding misery", "Reticulating splines",
    "Hoisting flag", "Ringing bell", "Clearing paper jam", "Potting black",
    "Walking dog", "Checking glossary", "Fetching larger tool"
];

function spam_progress_label() {
    let ms_elapsed = 0;
    let secs_remaining = 0;
    let time_text;

    if (limit_seconds != NaN) {
        current_time = new Date();
        ms_elapsed = current_time.getTime() - click_time.getTime();
        secs_remaining = limit_seconds - Math.floor(ms_elapsed / 1000.0);
    }
    else {
        secs_remaining = "?";
    }

    if (ms_elapsed < 500) {
        current_progress_text = "Generating fixtures...";
    }
    else if (secs_remaining > 0) {
        if (Math.random() < 0.4) {
            /* 40% chance of changing the progress text. */
            if (Math.random() < 0.1) {
                /* 10% chance of getting one of the special pieces of text... */
                current_progress_text = specials[Math.floor(Math.random() * specials.length)] + "...";
            }
            else {
                /* 90% chance of getting a random "verbing noun". */
                let gerund = gerunds[Math.floor(Math.random() * gerunds.length)];
                let noun = nouns[Math.floor(Math.random() * nouns.length)];
                current_progress_text = gerund + " " + noun + "...";
            }
        }
    }
    else if (ms_elapsed < limit_seconds * 1000 + 3000) {
        if (!noticed_results_overdue) {
            let ending = specials[Math.floor(Math.random() * specials.length)];
            current_progress_text = ending + "...";
            noticed_results_overdue = true;
        }
    }
    else {
        current_progress_text = "We ought to have finished by now.";
    }
    if (secs_remaining <= 0) {
        time_text = "";
    }
    else {
        time_text = "Up to " + secs_remaining.toString() + " seconds remaining.";
    }
    document.getElementById('progresstext').innerText = current_progress_text;
    document.getElementById('progresstime').innerText = time_text;
}

function generate_fixtures_clicked() {
    click_time = new Date();
    noticed_results_overdue = false;
    limit_seconds = parseInt(document.getElementById('maxtime').value) * parseInt(document.getElementById('numdivisions').value);
    spam_progress_label();
    setInterval(function() { spam_progress_label(); }, 300);
}
</script>""";
    elements.append(htmlform.HTMLFragment(javascript));

    elements.append(htmlform.HTMLFragment("<h2>Overall settings</h2>"))

    div_valid_table_sizes = []
    for div_index in sorted(div_rounds):
        div_players = [x for x in tourney.get_active_players() if x.get_division() == div_index]
        sizes = get_valid_group_sizes(len(div_players), len(rounds), tourney.has_auto_prune())
        div_valid_table_sizes.append(sizes)

    table_sizes_valid_for_all_divs = []
    for size in valid_group_sizes:
        for div_sizes in div_valid_table_sizes:
            if size not in div_sizes:
                break
        else:
            table_sizes_valid_for_all_divs.append(size)
    for size in (3, 2, 5, -5, 4):
        if size in table_sizes_valid_for_all_divs:
            default_default_group_size = size
            break
    else:
        default_default_group_size = None

    if num_divisions > 1 and len(table_sizes_valid_for_all_divs) > 0:
        elements.append(htmlform.HTMLFragment("<p>"))
        group_size_choices = [ htmlform.HTMLFormChoice(str(gs),
            "5&3" if gs == -5 else str(gs),
            int_or_none(settings.get("groupsize", default_default_group_size)) == gs) for gs in table_sizes_valid_for_all_divs ]
        elements.append(htmlform.HTMLFormRadioButton("groupsize", "Default players per table", group_size_choices))
        elements.append(htmlform.HTMLFragment("</p>"))

    elements.append(htmlform.HTMLFragment("<p>\n"))
    elements.append(htmlform.HTMLFormNumberInput("Fixture generator time limit %s(seconds)" % ("per division " if num_divisions > 1 else ""),
        "maxtime", settings.get("maxtime", "30"),
        other_attrs={"id" : "maxtime", "min" : 1}));
    elements.append(htmlform.HTMLFragment("</p>\n<p>\n"))
    elements.append(htmlform.HTMLFormNumberInput("For the purpose of avoiding rematches, disregard games before round ", "ignorerematchesbefore", str(ignore_rematches_before_round) if ignore_rematches_before_round is not None else "0", other_attrs={"min" : "0"}));
    elements.append(htmlform.HTMLFragment(" (enter 0 to count all rematches)"))
    elements.append(htmlform.HTMLFormHiddenInput("numdivisions", str(len(div_rounds)), other_attrs={"id" : "numdivisions"}))
    elements.append(htmlform.HTMLFragment("</p>\n"))
    elements.append(htmlform.HTMLFragment("<hr />\n"))

    for div_index in sorted(div_rounds):
        group_size = div_group_size[div_index]
        init_max_rematches = div_init_max_rematches[div_index]
        init_max_win_diff = div_init_max_win_diff[div_index]
        players = [x for x in tourney.get_active_players() if x.division == div_index];
        div_prefix = "d%d_" % (div_index)

        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<h2>%s</h2>" % (cgicommon.escape(tourney.get_division_name(div_index)))))
        else:
            elements.append(htmlform.HTMLFragment("<h2>Fixture generation</h2>"))
        elements.append(htmlform.HTMLFragment("<p>%s contains <strong>%d active players</strong>.</p>" % ("This division" if num_divisions > 1 else "The tournament", len(players))))

        if not tourney.has_auto_prune():
            if len(players) % 2 != 0 and len(players) % 3 != 0:
                elements.append(htmlform.HTMLWarningBox("swissunusualplayercount", "The number of active players is not a multiple of 2 or 3. Do you want to add one or more Prune players on the <a href=\"/cgi-bin/player.py?tourney=%s\">Player Setup</a> page?</p>" % (
                    urllib.parse.quote_plus(tourney.get_name())
                )))

        elements.append(htmlform.HTMLFragment("<p>"))

        div_valid_sizes = get_valid_group_sizes(len(players), len(rounds), tourney.has_auto_prune())
        ticked_group_size = int_or_none(settings.get(div_prefix + "groupsize"))
        if ticked_group_size is None:
            if len(table_sizes_valid_for_all_divs) > 0 and num_divisions > 1:
                # There is a "default table size" option
                ticked_group_size = 0
            else:
                ticked_group_size = get_default_group_size(len(players), len(rounds), tourney.has_auto_prune())
        if not div_valid_sizes:
            raise countdowntourney.FixtureGeneratorException("Can't use Swiss fixture generator: number of players%s is not compatible with any supported table size." % (" in a division" if num_divisions > 1 else ""))

        group_size_choices = [ htmlform.HTMLFormChoice(str(gs), "5&3" if gs == -5 else str(gs), gs == ticked_group_size) for gs in div_valid_sizes ]
        if num_divisions > 1 and len(table_sizes_valid_for_all_divs) > 0:
            group_size_choices = [ htmlform.HTMLFormChoice("0", "Round default (above)", ticked_group_size == 0) ] + group_size_choices

        if tourney.has_auto_prune():
            format_str = "If this does not exactly divide the number of active players in the %s, prunes will automatically take up the empty slots."
        else:
            format_str = "This must exactly divide the number of active players in the %s."
        elements.append(htmlform.HTMLFormRadioButton(div_prefix + "groupsize", ("How many players per table? " + format_str) % ("division" if num_divisions > 1 else "tournament"), group_size_choices))
        elements.append(htmlform.HTMLFragment("</p>\n"))

        elements.append(htmlform.HTMLFragment("<div style=\"margin-top: 5px; margin-bottom: 5px;\">"))
        elements.append(htmlform.HTMLFormCheckBox(div_prefix + "equalwinsareequalplayers",
            "Match players by number of wins then random chance, ignoring standings position",
            bool(settings.get(div_prefix + "equalwinsareequalplayers", False)),
            small_print="This option tries to match every player with random opponents on the same number of wins as them. Specific standings position is disregarded, except that if someone must play an opponent with more wins than them, prefer that to be the highest-ranked player(s) on the lower number of wins.")
        )
        elements.append(htmlform.HTMLFragment("</div>\n"))

        elements.append(htmlform.HTMLFragment("<p>Increase the following values if the fixture generator has trouble finding a grouping within the time limit.</p>\n"));

        elements.append(htmlform.HTMLFragment("<blockquote>"))
        elements.append(htmlform.HTMLFormNumberInput("Initial maximum rematches between players", div_prefix + "initmaxrematches", str(init_max_rematches), other_attrs={"min" : 0}))
        elements.append(htmlform.HTMLFragment("</blockquote>\n<blockquote>"))
        elements.append(htmlform.HTMLFormNumberInput("Initial maximum win count difference between players", div_prefix + "initmaxwindiff", str(init_max_win_diff), other_attrs={"min" : "0"}))
        elements.append(htmlform.HTMLFragment("</blockquote>\n"))

        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<hr />\n"))

    elements.append(htmlform.HTMLFormSubmitButton("submit", "Generate Fixtures", other_attrs={"onclick": "generate_fixtures_clicked();", "id": "generatefixtures", "class" : "bigbutton"}));
    elements.append(htmlform.HTMLFragment("<p id=\"progresstext\">For large numbers of players or unusual formats, fixture generation is not immediate - it can take up to the specified number of seconds. If no permissible configurations are found in that time, an error occurs.</p><p id=\"progresstime\"></p><hr /><p></p>"));
    elements.append(htmlform.HTMLFragment("<noscript>Your browser doesn't have Javascript enabled, which means you miss out on progress updates while fixtures are being generated.</noscript>"));

    form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py", elements);
    return form;

def check_ready(tourney, div_rounds):
    num_divisions = tourney.get_num_divisions()

    for div_index in sorted(div_rounds):
        players = tourney.get_active_players();
        players = [x for x in players if x.division == div_index]

        round_no = div_rounds[div_index]

        existing_games = tourney.get_games(round_no=round_no, division=div_index)
        if existing_games:
            return (False, "%s: there are already %d games for this division in round %d." % (tourney.get_division_name(div_index), len(existing_games), round_no))

        for size in valid_group_sizes:
            if tourney.has_auto_prune() or len(players) % size == 0:
                break
        else:
            if len(players) < 8:
                return (False, "%s: Number of players (%d) is not a multiple of any of %s" % (tourney.get_division_name(div_index), len(players), ", ".join([ str(x) for x in valid_group_sizes if x >= 0] )))

    for div in div_rounds:
        games = tourney.get_games(game_type='P', division=div);
        num_incomplete = 0;
        first_incomplete = None;
        for g in games:
            if not g.is_complete():
                if not first_incomplete:
                    first_incomplete = g;
                num_incomplete += 1;
        if num_incomplete > 0:
            if num_incomplete == 1:
                return (False, "%s: Cannot generate the next round because there is still a heat game unplayed: %s" % (tourney.get_division_name(div), str(g)));
            else:
                return (False, "%s: Cannot generate the next round because there are still %d heat games unplayed. The first one is: %s" % (tourney.get_division_name(div), num_incomplete, str(first_incomplete)));

    return (True, None);

def generate(tourney, settings, div_rounds):
    (ready, excuse) = check_ready(tourney, div_rounds);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    max_time = settings.get("maxtime", 30);
    try:
        limit_ms = int(max_time) * 1000;
    except ValueError:
        limit_ms = 30000;

    ignore_rematches_before = settings.get("ignorerematchesbefore", None)
    if ignore_rematches_before:
        try:
            ignore_rematches_before = int(ignore_rematches_before)
        except ValueError:
            ignore_rematches_before = None
    else:
        ignore_rematches_before = None

    default_group_size = settings.get("groupsize", None)
    if default_group_size is not None:
        try:
            default_group_size = int(default_group_size)
        except ValueError:
            default_group_size = None

    num_divisions = tourney.get_num_divisions()
    generated_groups = fixgen.GeneratedGroups()
    for div_index in sorted(div_rounds):
        players = tourney.get_active_players()
        players = [x for x in players if x.division == div_index]

        div_prefix = "d%d_" % (div_index)

        group_size = settings.get(div_prefix + "groupsize", default_group_size)
        try:
            group_size = int(group_size)
        except ValueError:
            group_size = default_group_size
        if group_size == 0:
            group_size = default_group_size

        init_max_rematches = settings.get(div_prefix + "initmaxrematches", 0)
        try:
            init_max_rematches = int(init_max_rematches)
        except ValueError:
            init_max_rematches = 0

        init_max_win_diff = settings.get(div_prefix + "initmaxwindiff", 0)
        try:
            init_max_win_diff = int(init_max_win_diff)
        except ValueError:
            init_max_win_diff = 0

        if group_size < 2 and group_size != -5:
            raise countdowntourney.FixtureGeneratorException("%s: The table size is less than 2 (%d)" % (tourney.get_division_name(div_index), group_size))

        if group_size > 0 and not tourney.has_auto_prune() and len(players) % group_size != 0:
            raise countdowntourney.FixtureGeneratorException("%s: Number of players (%d) is not a multiple of the table size (%d)" % (tourney.get_division_name(div_index), len(players), group_size));

        if group_size == -5 and len(players) < 8:
            raise countdowntourney.FixtureGeneratorException("%s: Number of players (%d) is not valid for the 5&3 fixture generator - you need at least 8 players" % (tourney.get_division_name(div_index), len(players)))

        # Top up the player list with automatic prunes if necessary.
        if group_size > 0 and tourney.has_auto_prune():
            gencommon.add_auto_prunes(tourney, players, group_size)

        equal_wins_are_equal_players = settings.get(div_prefix + "equalwinsareequalplayers", False)

        # Set a sensible cap of five minutes, in case the user has entered a
        # huge number to be clever
        if limit_ms > 300000:
            limit_ms = 300000;

        rank_by_wins = tourney.is_ranked_by_wins()
        round_no = div_rounds[div_index]
        games = tourney.get_games(game_type="P", division=div_index)
        if len(games) == 0:
            (weight, groups) = swissN.swissN_first_round(players, group_size)
        else:
            (weight, groups) = swissN.swissN(games, players,
                    tourney.get_standings(div_index), group_size,
                    rank_by_wins=rank_by_wins, limit_ms=limit_ms,
                    init_max_rematches=init_max_rematches,
                    init_max_win_diff=init_max_win_diff,
                    ignore_rematches_before=ignore_rematches_before,
                    equal_wins_are_equal_players=equal_wins_are_equal_players)

        if groups is None:
            raise countdowntourney.FixtureGeneratorException("%s: Unable to generate any permissible groupings in the given time limit." % (tourney.get_division_name(div_index)))

        for g in groups:
            generated_groups.add_group(round_no, div_index, g)
        generated_groups.set_repeat_threes(round_no, div_index, group_size == -5)

    return generated_groups

def save_form_on_submit():
    return False
