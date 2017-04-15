import sys
import random;
import countdowntourney;
import htmlform;
import swissN;
import cgi

name = "Swiss Army Blunderbuss";
description = "Players are matched against opponents who have performed similarly to them so far in the tourney, but repeats of previous fixtures are avoided.";
valid_group_sizes = (2, 3, 4, 5, -5)

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def get_valid_group_sizes(num_players, num_rounds):
    sizes = [ gs for gs in valid_group_sizes if gs > 0 and num_players % gs == 0 ]
    if num_players >= 8 and num_rounds > 0:
        sizes.append(-5)
    return sizes

def get_default_group_size(num_players, num_rounds):
    valid_sizes = get_valid_group_sizes(num_players, num_rounds)
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

        init_max_win_diff = int_or_none(settings.get("d%d_initmaxwindiff" % (div_index), 0))

        games = tourney.get_games(game_type='P', division=div_index);
        players = filter(lambda x : x.division == div_index, tourney.get_active_players());

        if max_time > 0 and group_size in valid_group_sizes and (group_size == -5 or len(players) % group_size == 0):
            div_ready[div_index] = True
#        else:
#            if max_time is None or max_time == 0:
#                max_time = 30;
#            if group_size is None or group_size not in valid_group_sizes:
#                if len(players) % 3 == 0:
#                    group_size = 3
#                elif len(players) % 2 == 0:
#                    group_size = 2
#                elif len(players) % 5 == 0:
#                    group_size = 5
#                elif len(players) >= 8:
#                    group_size = -5
#                elif len(players) % 4 == 0:
#                    group_size = 4
#                else:
#                    group_size = None

        div_group_size[div_index] = group_size
        div_init_max_rematches[div_index] = init_max_rematches
        div_init_max_win_diff[div_index] = init_max_win_diff

    if False not in div_ready and settings.get("submit") is not None:
        return None

    elements = [];
    javascript = """
<script type="text/javascript">
var click_time = 0;
var limit_seconds = 0;
var noticed_results_overdue = false;

var gerunds = ["Reticulating", "Exaggerating", "Refrigerating",
            "Bisecting", "Reordering", "Unseeding", "Reconstituting",
            "Inverting", "Convolving", "Reinventing", "Overpopulating",
            "Unwedging", "Tenderising", "Refactoring", "Frobnicating",
            "Normalising", "Factorising", "Transforming", "Relaying",
            "Decoupling", "Randomising", "Ignoring", "Disposing of",
            "Translating", "Restarting", "Entertaining", "Checking",
            "Verifying", "Flushing", "Contextualising", "Deconstructing",
            "Justifying", "Hacking", "Redrawing", "Reimagining",
            "Reinterpreting", "Reasoning with", "Impersonating",
            "Abbreviating", "Underestimating", "Misappropriating",
            "Constructing", "Preparing", "Redelivering", "Arguing over" ];
var nouns = ["seeding list", "rule book", "hypergrid",
            "network services", "timestamps", "multidimensional array",
            "decision tree", "player list", "weighting matrix",
            "instrument panel", "database", "videprinter",
            "standings table", "preclusion rules", "event handler",
            "dynamic modules", "hypertext", "fixture generator",
            "linked lists", "hash tables", "system clock", "file descriptors",
            "syntax tree", "binary tree", "dictionary", "homework",
            "breakfast", "contextualiser", "splines", "supercluster",
            "record books", "sandwiches", "grouping strategy", "reality" ];

var endings = [
    "Bribing officials", "Talking bollocks", "Feeding cat",
    "Rewinding tape", "Invading privacy", "Falling off cliff",
    "Kicking tyres", "Tapping barometer", "Serving hot",
    "Deploying parachute", "Cleaning up mess", "Straightening tie",
    "Seasoning to taste", "Stealing towels", "Reversing polarity"
];

function spam_progress_label() {
    var progress = "";
    var pc = 0;
    var ms_elapsed = 0;

    if (limit_seconds != NaN) {
        current_time = new Date();
        ms_elapsed = current_time.getTime() - click_time.getTime();
        pc = Math.floor(ms_elapsed * 100 / (limit_seconds * 1000));
        if (pc > 100) {
            pc = 100;
        }
        progress = pc.toString() + "%";
    }

    if (ms_elapsed < 500) {
        document.getElementById('progresslabel').innerHTML = "Generating fixtures...";
    }
    else if (pc < 100) {
        if (Math.random() < 0.4) {
            var gerund = "";
            var noun = "";

            gerund = gerunds[Math.floor(Math.random() * gerunds.length)];
            noun = nouns[Math.floor(Math.random() * nouns.length)];

            document.getElementById('progresslabel').innerHTML = progress + " " + gerund + " " + noun + "...";
        }
    }
    else if (ms_elapsed < limit_seconds * 1000 + 3000) {
        if (!noticed_results_overdue) {
            var ending = endings[Math.floor(Math.random() * endings.length)];
            document.getElementById('progresslabel').innerHTML = "100% " + ending + "...";
            noticed_results_overdue = true;
        }
    }
    else {
        document.getElementById('progresslabel').innerHTML = "We ought to have finished by now.";
    }
}
function generate_fixtures_clicked() {
    click_time = new Date();
    noticed_results_overdue = false;
    limit_seconds = parseInt(document.getElementById('maxtime').value) * parseInt(document.getElementById('numdivisions').value);
    // document.getElementById('generatefixtures').disabled = true;
    spam_progress_label();
    setInterval(function() { spam_progress_label(); }, 300);
}
</script>""";
    elements.append(htmlform.HTMLFragment(javascript));

    elements.append(htmlform.HTMLFragment("<h3>Overall settings</h3>"))

    div_valid_table_sizes = []
    for div_index in sorted(div_rounds):
        div_players = filter(lambda x : x.get_division() == div_index, tourney.get_active_players())
        sizes = get_valid_group_sizes(len(div_players), len(rounds))
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

    elements.append(htmlform.HTMLFragment("</p>\n<p>\n"))
    elements.append(htmlform.HTMLFormTextInput("Fixture generator time limit %s(seconds)" % ("per division " if num_divisions > 1 else ""),
        "maxtime", settings.get("maxtime", "30"),
        other_attrs={"size": "3", "id" : "maxtime"}));
    elements.append(htmlform.HTMLFragment("</p>\n<p>\n"))
    elements.append(htmlform.HTMLFormTextInput("For the purpose of avoiding rematches, disregard games before round ", "ignorerematchesbefore", str(ignore_rematches_before_round) if ignore_rematches_before_round is not None else "", other_attrs={"size": "3"}));
    elements.append(htmlform.HTMLFragment(" (leave blank to count all rematches)"))
    elements.append(htmlform.HTMLFormHiddenInput("numdivisions", str(num_divisions), other_attrs={"id" : "numdivisions"}))
    elements.append(htmlform.HTMLFragment("</p>\n"))
    elements.append(htmlform.HTMLFragment("<hr />\n"))

    for div_index in sorted(div_rounds):
        group_size = div_group_size[div_index]
        init_max_rematches = div_init_max_rematches[div_index]
        init_max_win_diff = div_init_max_win_diff[div_index]
        players = filter(lambda x : x.division == div_index, tourney.get_active_players());
        div_prefix = "d%d_" % (div_index)

        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<h3>%s</h3>" % (cgi.escape(tourney.get_division_name(div_index)))))
        else:
            elements.append(htmlform.HTMLFragment("<h3>Division settings</h3>"))
        elements.append(htmlform.HTMLFragment("<p>"))

        div_valid_sizes = get_valid_group_sizes(len(players), len(rounds))
        ticked_group_size = int_or_none(settings.get(div_prefix + "groupsize"))
        if ticked_group_size is None:
            if len(table_sizes_valid_for_all_divs) > 0 and num_divisions > 1:
                # There is a "default table size" option
                ticked_group_size = 0
            else:
                ticked_group_size = get_default_group_size(len(players), len(rounds))
        group_size_choices = [ htmlform.HTMLFormChoice(str(gs), "5&3" if gs == -5 else str(gs), gs == ticked_group_size) for gs in div_valid_sizes ]
        if num_divisions > 1 and len(table_sizes_valid_for_all_divs) > 0:
            group_size_choices = [ htmlform.HTMLFormChoice("0", "Round default (above)", ticked_group_size == 0) ] + group_size_choices

        elements.append(htmlform.HTMLFormRadioButton(div_prefix + "groupsize", "Players per table", group_size_choices))
        elements.append(htmlform.HTMLFragment("</p>\n"))
        elements.append(htmlform.HTMLFragment("<p>Increase the following values if the fixture generator has trouble finding a grouping within the time limit.</p>\n"));
        
        elements.append(htmlform.HTMLFragment("<blockquote>"))
        elements.append(htmlform.HTMLFormTextInput("Initial maximum rematches between players", div_prefix + "initmaxrematches", str(init_max_rematches), other_attrs={"size" : "3"}))
        elements.append(htmlform.HTMLFragment("</blockquote>\n<blockquote>"))
        elements.append(htmlform.HTMLFormTextInput("Initial maximum win count difference between players", div_prefix + "initmaxwindiff", str(init_max_win_diff), other_attrs={"size" : "3"}))
        elements.append(htmlform.HTMLFragment("</blockquote>\n"))
        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<hr />\n"))

    elements.append(htmlform.HTMLFormSubmitButton("submit", "Generate Fixtures", other_attrs={"onclick": "generate_fixtures_clicked();", "id": "generatefixtures"}));
    elements.append(htmlform.HTMLFragment("<p id=\"progresslabel\">For large numbers of players or unusual formats, fixture generation is not immediate - it can take up to the specified number of seconds, or longer if no permissible configurations are found in that time.</p><hr /><p></p>"));
    elements.append(htmlform.HTMLFragment("<noscript>Your browser doesn't have Javascript enabled, which means you miss out on progress updates while fixtures are being generated.</noscript>"));

    form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py", elements);
    return form;

def check_ready(tourney, div_rounds):
    num_divisions = tourney.get_num_divisions()

    for div_index in sorted(div_rounds):
        players = tourney.get_active_players();
        players = filter(lambda x : x.division == div_index, players)

        round_no = div_rounds[div_index]

        existing_games = tourney.get_games(round_no=round_no, division=div_index)
        if existing_games:
            return (False, "%s: there are already %d games for this division in round %d." % (tourney.get_division_name(div_index), len(existing_games), round_no))

        for size in valid_group_sizes:
            if len(players) % size == 0:
                break
        else:
            if len(players) < 8:
                return (False, "%s: Number of players (%d) is not a multiple of any of %s" % (tourney.get_division_name(div_index), len(players), ", ".join(map(str, valid_group_sizes))))

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
    rank_method = tourney.get_rank_method();

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
    fixtures = []
    for div_index in sorted(div_rounds):
        players = tourney.get_active_players()
        players = filter(lambda x : x.division == div_index, players)

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

        if group_size > 0 and len(players) % group_size != 0:
            raise countdowntourney.FixtureGeneratorException("%s: Number of players (%d) is not a multiple of the table size (%d)" % (tourney.get_division_name(div_index), len(players), group_size));

        if group_size == -5 and len(players) < 8:
            raise countdowntourney.FixtureGeneratorException("%s: Number of players (%d) is not valid for the 5&3 fixture generator - you need at least 8 players" % (tourney.get_division_name(div_index), len(players)))

        # Set a sensible cap of five minutes, in case the user has entered a
        # huge number to be clever
        if limit_ms > 300000:
            limit_ms = 300000;

        rank_by_wins = (rank_method == countdowntourney.RANK_WINS_POINTS or rank_method == countdowntourney.RANK_WINS_SPREAD);

        round_no = div_rounds[div_index]
        games = tourney.get_games(game_type="P");
        if len(games) == 0:
            (weight, groups) = swissN.swissN_first_round(players, group_size);
        else:
            (weight, groups) = swissN.swissN(games, players,
                    tourney.get_standings(div_index), group_size,
                    rank_by_wins=rank_by_wins, limit_ms=limit_ms,
                    init_max_rematches=init_max_rematches,
                    init_max_win_diff=init_max_win_diff,
                    ignore_rematches_before=ignore_rematches_before);

        if groups is None:
            raise countdowntourney.FixtureGeneratorException("%s: Unable to generate any permissible groupings in the given time limit." % (tourney.get_division_name(div_index)))

        fixtures += tourney.make_fixtures_from_groups(groups, fixtures, round_no, group_size == -5, division=div_index)
    
    d = dict();
    d["fixtures"] = fixtures;
    d["rounds"] = [ {
            "round": round_no,
            "name": "Round %d" % round_no
    } ];
    
    return d;

def save_form_on_submit():
    return False
