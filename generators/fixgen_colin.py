import random;
import countdowntourney;
import htmlform;
import swiss3;

name = "COLIN Fixture Generator";
description = "In round 1, place higher-rated players on different tables. In subsequent rounds, group together players who have performed similarly so far, without rematches.";

def get_user_form(tourney, settings):
	max_time = None;
	if settings.get("maxtime", None) is not None:
		try:
			max_time = int(settings["maxtime"]);
		except ValueError:
			max_time = None;
	
	games = tourney.get_games(game_type='P');

	if max_time > 0:
		return None;
	elif len(games) == 0:
		return None;
	else:
		# Default to 30 seconds
		max_time = 30;

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
			"Verifying", "Flushing"];
var nouns = ["seeding list", "rule book", "hypergrid",
			"network services", "timestamps", "multidimensional array",
			"decision tree", "player list", "weighting matrix",
			"instrument panel", "eyebrows", "videprinter",
			"standings table", "preclusion rules", "event handler",
			"dynamic modules", "hypertext", "fixture generator",
			"linked lists", "hash tables", "system clock", "file descriptors"];

var endings = [
	"Bribing officials", "Talking bollocks", "Feeding cat",
	"Rewinding tape", "Invading privacy", "Falling off cliff",
	"Kicking tyres", "Tapping barometer", "Serving hot",
	"Deploying parachute", "Cleaning up mess", "Straightening tie",
	"Seasoning to taste"
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
		var gerund = "";
		var noun = "";

		gerund = gerunds[Math.floor(Math.random() * gerunds.length)];
		noun = nouns[Math.floor(Math.random() * nouns.length)];

		document.getElementById('progresslabel').innerHTML = progress + " " + gerund + " " + noun + "...";
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
	setInterval(function() { if (Math.random() < 0.4) { spam_progress_label(); } }, 200);
}
</script>""";
	elements.append(htmlform.HTMLFragment(javascript));
	elements.append(htmlform.HTMLFormTextInput("Time limit for finding optimal grouping (seconds)", "maxtime", str(max_time), length=3, other_attrs={"id": "maxtime"}));
	elements.append(htmlform.HTMLFragment("<br />"));
	elements.append(htmlform.HTMLFormSubmitButton("submit", "Generate Fixtures", other_attrs={"onclick": "generate_fixtures_clicked();", "id": "generatefixtures"}));
	elements.append(htmlform.HTMLFragment("<p id=\"progresslabel\">For large numbers of players, fixture generation is not immediate - it can take up to the specified number of seconds.</p>"));
	elements.append(htmlform.HTMLFragment("<noscript>Your browser doesn't have Javascript enabled, which means you miss out on progress updates while fixtures are being generated.</noscript>"));

	form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py", elements);
	return form;

def check_ready(tourney):
	players = tourney.get_players();
	table_size = tourney.get_table_size();

	if len(players) % table_size != 0:
		return (False, "Number of players (%d) is not a multiple of the table size (%d)" % (len(players), table_size));
	
	if table_size != 3:
		return (False, "The COLIN fixture generator can only be used when there are three players per table.");
	
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

	(ready, excuse) = check_ready(tourney);
	if not ready:
		raise countdowntourney.FixtureGeneratorException(excuse);

	rounds = tourney.get_rounds();
	rounds = filter(lambda x : x.get("type", None) == "P", rounds);

	max_time = settings.get("maxtime", 10);
	try:
		limit_ms = int(max_time) * 1000;
	except ValueError:
		limit_ms = 10000;

	rank_by_wins = (rank_method == countdowntourney.RANK_WINS_POINTS);

	if len(rounds) == 0:
		(weight, groups) = swiss3.swiss3_first_round(players);
		round_no = 1;
	else:
		games = tourney.get_games(game_type="P");
		(weight, groups) = swiss3.swiss3(games, players, rank_by_wins=rank_by_wins, limit_ms=limit_ms);
		round_no = len(rounds) + 1;
	
	fixtures = [];
	table_no = 1;
	round_seq = 1;
	for group in groups:
		for i in range(0, len(group)):
			for j in range(i + 1, len(group)):
				p1 = group[i];
				p2 = group[j];
				if (i + j) % 2 == 0:
					(p1, p2) = (p2, p1);
				fixture = countdowntourney.Game(round_no, round_seq, table_no, 'P', p1, p2);
				fixtures.append(fixture);
				round_seq += 1;
		table_no += 1;
	
	d = dict();
	d["fixtures"] = fixtures;
	d["rounds"] = [ {
			"round": round_no,
			"name": "Round %d" % round_no,
			"type": "P"
	} ];
	
	return d;
