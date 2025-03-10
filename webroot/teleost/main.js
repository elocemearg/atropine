var gameState = null;
var gameStateRevision = 0;

var gameStateFetchRequest = null;

var viewUpdateInterval = null;
var refreshGameStateInterval = null;
var currentView = null;
var currentViewDrawn = false;
var viewRefreshFrameInterval = null;
var animationFrameMs = 40;
var updatesSkipped = 0;
var updatesMaxSkip = 5;

var teleostMode = null;
var teleostModeOptions = {};
var teamIndicatorHTML = "&#x25cf;"

/* Special constants for the whichRnd parameter of findSelectedRoundsPerDivision(). */

/* Select all rounds for each division. */
const SELECT_ALL_ROUNDS = -1;

/* Select the last round in each division with at least one completed game. */
const SELECT_LAST_ROUND_IN_DIV_WITH_PLAYED_GAMES = -2;

/* For each division, find the last round in the division which is complete and
 * select the *next* round, or that round if there is no next round. */
const SELECT_ROUND_AFTER_LAST_COMPLETED_ROUND = -3;

/* Select the earliest round in each division with no completed games. */
const SELECT_EARLIEST_UNPLAYED_ROUND = -4;

/* For all divisions, select the last round in the *tourney* with at least one
 * completed game. Exception: if for any division this would select a round
 * with no games at all in that division, for that division select the last
 * round before then with at least one game. */
const SELECT_LAST_ROUND_IN_TOURNEY_WITH_PLAYED_GAMES = -5;

function escapeHTML(str) {
    if (str === null) {
        return "(null)";
    }
    else if (str === undefined) {
        return "(undefined)";
    }
    return str.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#039;");
}

function dictGet(dict, key, def) {
    if (key in dict) {
        return dict[key];
    }
    else {
        return def;
    }
}

function makeWithdrawn(str, esc) {
    var spanned = "<span class=\"withdrawn\">";
    if (esc)
        spanned += escapeHTML(str);
    else
        spanned += str;
    spanned += "</span>";
    return spanned;
}

function highlightScore(score) {
    return "<span class=\"highlightscore\">" + score.toString() + "</span>";
}

function formatScore(s1, s2, tb, highlight1=false, highlight2=false) {
    var text;
    if (s1 == null || s2 == null) {
        /* Game hasn't been played yet */
        text = "&ndash;";
    }
    else if (s1 == 0 && s2 == 0 && tb) {
        /* Double-loss: X - X */
        text = "&#10006; &ndash; &#10006;";
    }
    else {
        /* Game is complete */
        text = highlight1 ? highlightScore(s1) : s1.toString();
        if (tb && s1 > s2) {
            text += "*";
        }
        text += " &ndash; ";
        text += highlight2 ? highlightScore(s2) : s2.toString();
        if (tb && s2 >= s1) {
            text += "*";
        }
    }
    return text;
}

function teamColourToHTML(rgbList) {
    var html = "#";
    for (var i = 0; i < 3; ++i) {
        var component;
        if (i >= rgbList.length)
            component = 0;
        else
            component = rgbList[i];
        component %= 256;
        if (component < 16)
            html += "0";
        html += component.toString(16);
    }
    return html;
}

// See https://www.w3.org/TR/AERT/#color-contrast
var brightnessCoeffs = [ 0.299, 0.587, 0.114 ];
function teamColourIsLight(rgbList) {
    /* Get a rough guess of the brightness of this colour, and return true if
     * it's greater than 50%. This is quite unscientific and ignores the
     * requirement to apply something something colour space something
     * something gamma decoding, but it's good enough to tell a "dark" colour
     * from a "light" colour for the purposes of deciding whether text on it
     * should be white or black. */

    if (rgbList.length < 3) {
        return false;
    }

    var roughBrightness = 0;
    for (var i = 0; i < 3; ++i) {
        roughBrightness += brightnessCoeffs[i] * rgbList[i] / 255.0;
    }
    return roughBrightness > 0.5;
}

function teamScoreBoxDivHTML(colour, score, additionalClassName) {
    var teamColourClass;
    var html = "";
    if (teamColourIsLight(colour))
        teamColourClass = "teamscorelight";
    else
        teamColourClass = "";
    html += "<div class=\"teamscore " + additionalClassName + " " +
        teamColourClass + "\" style=\"background-color: " +
        teamColourToHTML(colour) + "\">";
    html += score.toString();
    html += "</div>";
    return html;
}

function findSelectedDivisions(games, whichDiv) {
    if (whichDiv == -1) {
        var divs = [];
        for (var divIndex = 0; divIndex < games.divisions.length; ++divIndex) {
            divs.push(games.divisions[divIndex].div_num);
        }
        return divs;
    }
    else {
        return [whichDiv];
    }
}

function findSelectedRoundsPerDivision(games, whichRnd) {
    var ret = {};
    var divisions = games.divisions;
    let gameCountsPerDivPerRound = {};

    for (var divIndex = 0; divIndex < divisions.length; ++divIndex) {
        var divNum = divisions[divIndex].div_num;
        var selectedRounds = [];
        var roundGameCounts = {};
        var divGames = divisions[divIndex].games;

        if (whichRnd >= 0) {
            selectedRounds = [whichRnd];
        }
        else {
            for (var gameIndex = 0; gameIndex < divGames.length; ++gameIndex) {
                var game = divGames[gameIndex];
                if (!(game.round in roundGameCounts)) {
                    roundGameCounts[game.round] = {
                        "numGames" : 0,
                        "numComplete" : 0,
                        "numIncomplete" : 0
                    }
                }
                if (game.complete) {
                    roundGameCounts[game.round].numComplete++;
                }
                else {
                    roundGameCounts[game.round].numIncomplete++;
                }
                roundGameCounts[game.round].numGames++;
            }
            gameCountsPerDivPerRound[divNum] = roundGameCounts;

            if (whichRnd == SELECT_ALL_ROUNDS) {
                /* All rounds */
                for (var r in roundGameCounts) {
                    selectedRounds.push(r);
                }
            }
            else if (whichRnd == SELECT_LAST_ROUND_IN_DIV_WITH_PLAYED_GAMES || whichRnd == SELECT_LAST_ROUND_IN_TOURNEY_WITH_PLAYED_GAMES) {
                /* Latest round with at least one completed game, or if
                 * there is no such round, the first round */
                var latestRound = null;
                var firstRound = null;
                for (var r in roundGameCounts) {
                    if (roundGameCounts[r].numComplete > 0) {
                        if (latestRound == null || latestRound < r)
                            latestRound = r;
                    }
                    if (firstRound == null || r < firstRound)
                        firstRound = r;
                }
                if (latestRound != null)
                    selectedRounds.push(latestRound);
                else if (firstRound != null)
                    selectedRounds.push(firstRound);
            }
            else if (whichRnd == SELECT_ROUND_AFTER_LAST_COMPLETED_ROUND) {
                /* The round following the last completed round, or the
                 * last completed round if no round follows that, or the
                 * first round if there is no completed round. */
                var lastCompletedRound = null;
                var firstRound = null;
                var roundNumbers = [];
                for (var r in roundGameCounts) {
                    if (roundGameCounts[r].numComplete > 0 &&
                            roundGameCounts[r].numIncomplete == 0) {
                        if (lastCompletedRound == null || lastCompletedRound < r)
                            lastCompletedRound = r;
                    }
                    if (firstRound == null || r < firstRound)
                        firstRound = r;
                    roundNumbers.push(r);
                }
                roundNumbers.sort(function(a, b) { return a-b; });

                if (lastCompletedRound != null) {
                    var i = roundNumbers.indexOf(lastCompletedRound);
                    if (i + 1 >= roundNumbers.length)
                        selectedRounds.push(roundNumbers[i]);
                    else
                        selectedRounds.push(roundNumbers[i+1]);
                }
                else if (firstRound != null) {
                    selectedRounds.push(firstRound);
                }
            }
            else if (whichRnd == SELECT_EARLIEST_UNPLAYED_ROUND) {
                /* The earliest round with no completed games in it, or
                 * if all rounds have completed games, the last round */
                var earliestUnplayedRound = null;
                var lastRound = null;
                for (var r in roundGameCounts) {
                    if (roundGameCounts[r].numComplete == 0) {
                        if (earliestUnplayedRound == null || earliestUnplayedRound > r)
                            earliestUnplayedRound = r;
                    }
                    if (lastRound == null || r > lastRound)
                        lastRound = r;
                }
                if (earliestUnplayedRound != null)
                    selectedRounds.push(earliestUnplayedRound);
                else if (lastRound != null)
                    selectedRounds.push(lastRound);
            }
        }

        ret[divNum] = selectedRounds;
    }

    if (whichRnd == SELECT_LAST_ROUND_IN_TOURNEY_WITH_PLAYED_GAMES) {
        /* We want the last round in the *tourney* with at least one completed
         * game, not just the last round per division with at least one
         * completed game. */
        let maxRound = 0;
        let newRet = {};
        for (let divNum in ret) {
            /* if whichRnd == SELECT_LAST_ROUND_IN_TOURNEY_WITH_PLAYED_GAMES, ret[divNum].length == 1 */
            if (ret[divNum][0] > maxRound) {
                maxRound = ret[divNum][0];
            }
        }

        /* As a special case, if for any division, the selected round has no
         * games at all, for that division we'll show the last round before
         * then that has games. */
        for (let divNum in ret) {
            let roundGameCounts = gameCountsPerDivPerRound[divNum];
            if (roundGameCounts != null) {
                let lastRoundWithGames = maxRound;
                while (lastRoundWithGames > 1 && (roundGameCounts[lastRoundWithGames] == null || roundGameCounts[lastRoundWithGames].numGames == 0)) {
                    lastRoundWithGames--;
                }
                newRet[divNum] = [ lastRoundWithGames ];
            }
            else {
                newRet[divNum] = [ 1 ];
            }
        }
        ret = newRet;
    }

    return ret;
}
