import sys
import random;
import countdowntourney;
import htmlform;
import swissN;

name = "Swiss Army Blunderbuss";
description = "Players are matched against opponents who have performed similarly to them so far in the tourney, but repeats of previous fixtures are avoided.";
valid_group_sizes = (2, 3, 4, 5, -5)

def get_user_form(tourney, settings):
    players = tourney.get_players();

    max_time = None;
    if settings.get("maxtime", None) is not None:
        try:
            max_time = int(settings["maxtime"]);
        except ValueError:
            max_time = None;

    group_size = None
    if settings.get("groupsize", None) is not None:
        try:
            group_size = int(settings["groupsize"])
        except ValueError:
            group_size = None

    init_max_rematches = 0
    if settings.get("initmaxrematches", None) is not None:
        try:
            init_max_rematches = int(settings["initmaxrematches"])
        except ValueError:
            init_max_rematches = 0

    games = tourney.get_games(game_type='P');

    rounds = tourney.get_rounds();
    rounds = filter(lambda x : x.get("type", None) == "P", rounds);

    if max_time > 0 and group_size in valid_group_sizes and (group_size == -5 or len(players) % group_size == 0):
        return None;
    else:
        # Default to 30 seconds, group size of 3
        if max_time is None or max_time == 0:
            max_time = 30;
        if group_size is None or group_size not in valid_group_sizes:
            if len(players) % 3 == 0:
                group_size = 3
            elif len(players) % 2 == 0:
                group_size = 2
            elif len(players) % 5 == 0:
                group_size = 5
            elif len(players) >= 8:
                group_size = -5
            elif len(players) % 4 == 0:
                group_size = 4
            else:
                group_size = None

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
            "Abbreviating", "Underestimating", "Misappropriating"];
var nouns = ["seeding list", "rule book", "hypergrid",
            "network services", "timestamps", "multidimensional array",
            "decision tree", "player list", "weighting matrix",
            "instrument panel", "database", "videprinter",
            "standings table", "preclusion rules", "event handler",
            "dynamic modules", "hypertext", "fixture generator",
            "linked lists", "hash tables", "system clock", "file descriptors",
            "syntax tree", "binary tree", "dictionary", "homework",
            "breakfast", "contextualiser", "splines", "supercluster",
            "record books", "sandwiches", "grouping strategy",
            "reality"];

var endings = [
    "Bribing officials", "Talking bollocks", "Feeding cat",
    "Rewinding tape", "Invading privacy", "Falling off cliff",
    "Kicking tyres", "Tapping barometer", "Serving hot",
    "Deploying parachute", "Cleaning up mess", "Straightening tie",
    "Seasoning to taste", "Stealing towels"
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
    limit_seconds = parseInt(document.getElementById('maxtime').value);
    // document.getElementById('generatefixtures').disabled = true;
    spam_progress_label();
    setInterval(function() { spam_progress_label(); }, 300);
}
</script>""";
    elements.append(htmlform.HTMLFragment(javascript));
    elements.append(htmlform.HTMLFragment("<p>"))
    elements.append(htmlform.HTMLFormTextInput("Time limit for finding optimal grouping (seconds)", "maxtime", str(max_time), other_attrs={"id": "maxtime", "size": "3"}));
    elements.append(htmlform.HTMLFragment("<br />"));

    elements.append(htmlform.HTMLFragment("</p><p>"))
    group_size_choices = [ htmlform.HTMLFormChoice(str(gs), str(gs), gs == group_size) for gs in valid_group_sizes if gs > 0 and len(players) % gs == 0 ]
    if len(players) >= 8 and len(rounds) > 0:
        group_size_choices.append(htmlform.HTMLFormChoice("-5", "5&3", group_size == -5))

    elements.append(htmlform.HTMLFormRadioButton("groupsize", "Players per table", group_size_choices))
    elements.append(htmlform.HTMLFragment("</p><p>"))
    elements.append(htmlform.HTMLFormTextInput("Try to avoid matches between players who have played each other more than ", "initmaxrematches", str(init_max_rematches), other_attrs={"size" : "3"}))
    elements.append(htmlform.HTMLFragment(" times before.</p><p>"))
    elements.append(htmlform.HTMLFormSubmitButton("submit", "Generate Fixtures", other_attrs={"onclick": "generate_fixtures_clicked();", "id": "generatefixtures"}));
    elements.append(htmlform.HTMLFragment("</p>"))
    elements.append(htmlform.HTMLFragment("<p id=\"progresslabel\">For large numbers of players or unusual formats, fixture generation is not immediate - it can take up to the specified number of seconds, or longer if no permissible configurations are found in that time.</p>"));
    elements.append(htmlform.HTMLFragment("<noscript>Your browser doesn't have Javascript enabled, which means you miss out on progress updates while fixtures are being generated.</noscript>"));

    form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py", elements);
    return form;

def check_ready(tourney):
    players = tourney.get_players();

    for size in valid_group_sizes:
        if len(players) % size == 0:
            break
    else:
        if len(players) < 8:
            return (False, "Number of players (%d) is not a multiple of any of %s" % (len(players), ", ".join(map(str, valid_group_sizes))))
    
    games = tourney.get_games(game_type='P');
    num_incomplete = 0;
    first_incomplete = None;
    for g in games:
        if not g.is_complete():
            if not first_incomplete:
                first_incomplete = g;
            num_incomplete += 1;
    if num_incomplete > 0:
        if num_incomplete == 1:
            return (False, "Cannot generate the next round because there is still a heat game unplayed: %s" % str(g));
        else:
            return (False, "Cannot generate the next round because there are still %d heat games unplayed. The first one is: %s" % (num_incomplete, str(first_incomplete)));
    
    return (True, None);

def generate(tourney, settings):
    players = tourney.get_players();
    table_size = tourney.get_table_size();
    rank_method = tourney.get_rank_method();

    rounds = tourney.get_rounds();
    rounds = filter(lambda x : x.get("type", None) == "P", rounds);

    max_time = settings.get("maxtime", 30);
    try:
        limit_ms = int(max_time) * 1000;
    except ValueError:
        limit_ms = 30000;

    group_size = settings.get("groupsize", 3)
    try:
        group_size = int(group_size)
    except ValueError:
        group_size = 3

    init_max_rematches = settings.get("initmaxrematches", 0)
    try:
        init_max_rematches = int(init_max_rematches)
    except ValueError:
        init_max_rematches = 0

    (ready, excuse) = check_ready(tourney);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    if group_size < 2 and group_size != -5:
        raise countdowntourney.FixtureGeneratorException("The table size is less than 2 (%d)" % group_size)

    if group_size > 0 and len(players) % group_size != 0:
        raise countdowntourney.FixtureGeneratorException("Number of players (%d) is not a multiple of the table size (%d)" % (len(players), group_size));

    if group_size == -5 and len(players) < 8:
        raise countdowntourney.FixtureGeneratorException("Number of players (%d) is not valid for the 5&3 fixture generator - you need at least 8 players" % len(players))

    # Set a sensible cap of five minutes, in case the user has entered a
    # huge number to be clever
    if limit_ms > 300000:
        limit_ms = 300000;

    rank_by_wins = (rank_method == countdowntourney.RANK_WINS_POINTS);

    if len(rounds) == 0:
        (weight, groups) = swissN.swissN_first_round(players, group_size);
        round_no = 1;
    else:
        games = tourney.get_games(game_type="P");
        (weight, groups) = swissN.swissN(games, players, group_size, rank_by_wins=rank_by_wins, limit_ms=limit_ms, init_max_rematches=init_max_rematches);
        round_no = len(rounds) + 1;

    fixtures = countdowntourney.make_fixtures_from_groups(groups, round_no, group_size == -5)
    
    d = dict();
    d["fixtures"] = fixtures;
    d["rounds"] = [ {
            "round": round_no,
            "name": "Round %d" % round_no,
            "type": "P"
    } ];
    
    return d;
