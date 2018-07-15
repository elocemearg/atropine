function createStandingsAndVideprinterScreen(tourneyName, options) {
    return new MultipleView(tourneyName, 0, 0, 100, 100, [
        new StandingsView(tourneyName, 0, 0, 100, 70,
            dictGet(options, "standings_videprinter_standings_lines", 8),
            dictGet(options, "standings_videprinter_standings_scroll", 10) * 1000),
        new VideprinterView(tourneyName, 0, 70, 100, 30, 4)
    ]);
}

function createStandingsScreen(tourneyName, options) {
    return new StandingsView(tourneyName, 0, 0, 100, 100,
            dictGet(options, "standings_only_lines", 12),
            dictGet(options, "standings_only_scroll", 12) * 1000);
}

function createVideprinterScreen(tourneyName, options) {
    return new VideprinterView(tourneyName, 0, 0, 100, 100, 16);
}

function createStandingsAndRoundResultsScreen(tourneyName, options) {
    return new MultipleView(tourneyName, 0, 0, 100, 100, [
            new StandingsView(tourneyName, 0, 0, 100, 70,
                dictGet(options, "standings_results_standings_lines", 8),
                dictGet(options, "standings_results_standings_scroll", 10) * 1000),
            new RoundResultsView(tourneyName, 0, 70, 100, 30, 3, 5000)
    ]);
}

function createRoundResultsScreen(tourneyName, options) {
    return new RoundResultsView(tourneyName, 0, 0, 100, 100, 14, 10000);
}

function createFixturesScreen(tourneyName, options) {
    return new FixturesView(tourneyName, 0, 0, 100, 100,
            dictGet(options, "fixtures_lines", 12),
            dictGet(options, "fixtures_scroll", 10) * 1000,
            -1, -3);
}

function createTableNumberIndexScreen(tourneyName, options) {
    return new TableNumberIndexView(tourneyName, 0, 0, 100, 100,
            dictGet(options, "table_index_rows", 12),
            dictGet(options, "table_index_columns", 2),
            dictGet(options, "table_index_scroll", 12) * 1000);
}

function createTuffLuckScreen(tourneyName, options) {
    return new TuffLuckView(tourneyName, 0, 0, 100, 100)
}

function createOverachieversScreen(tourneyName, options) {
    return new OverachieversView(tourneyName, 0, 0, 100, 100)
}

function createPlaceholderScreen(tourneyName, options) {
    return new PlaceholderView(tourneyName, 0, 0, 100, 100);
}

function createTechnicalDifficultiesScreen(tourneyName, options) {
    return new ImageView(tourneyName, 0, 0, 100, 100, "/images/technical_difficulties.jpg");
}

function createHighScoresScreen(tourneyName, options) {
    return new HighScoresView(tourneyName, 0, 0, 100, 100);
}

/*function createClockScreen(tourneyName, options) {
    return new ClockView(tourneyName, 0, 0, 100, 100);
}*/

var teleostModesToCreateFunctions = {};

function showBanner(text) {
    var bannerDiv = document.getElementById("teleostbanner");
    var mainPane = document.getElementById("displaymainpane");

    if (bannerDiv != null) {
        bannerDiv.style.display = "block";
        bannerDiv.innerText = text;
    }
    if (mainPane != null) {
        mainPane.style.top = "5vh";
        mainPane.style.height = "95vh";
    }
}

function clearBanner() {
    var bannerDiv = document.getElementById("teleostbanner");
    var mainPane = document.getElementById("displaymainpane");

    if (bannerDiv != null) {
        bannerDiv.style.display = "none";
        bannerDiv.innerText = "";
    }
    if (mainPane != null) {
        mainPane.style.top = "0%";
        mainPane.style.height = "100%";
    }
}


function updateCurrentView() {
    if (currentView == null)
        return;

    /* If an animation is still going on, awkwardly walk back out of the room,
       unless we've skipped updatesMaxSkip updates consecutively in this way,
       in which case kill the animation and do the next refresh without
       animating. */
    var enableAnimation = true;
    if (viewRefreshFrameInterval != null) {
        if (updatesSkipped < updatesMaxSkip) {
            updatesSkipped++;
            return;
        }
        else {
            clearInterval(viewRefreshFrameInterval);
            viewRefreshFrameInterval = null;
            enableAnimation = false;
        }
    }

    if (gameState && "teleost" in gameState && "banner_text" in gameState.teleost) {
        if (gameState.teleost.banner_text.length > 0) {
            showBanner(gameState.teleost.banner_text);
        }
        else {
            clearBanner();
        }
    }

    updatesSkipped = 0;
    var animate = currentView.refresh(new Date().getTime(), enableAnimation);
    currentViewDrawn = true;
    if (animate && enableAnimation) {
        viewRefreshFrameInterval = setInterval(refreshFrameCurrentView, animationFrameMs);
    }
}

function destroyCurrentView() {
    /* Cancel any animation interval currently running */
    if (viewRefreshFrameInterval != null) {
        clearInterval(viewRefreshFrameInterval);
        viewRefreshFrameInterval = null;
    }

    /* We don't want the view updating before we've set it up */
    if (viewUpdateInterval != null) {
        clearInterval(viewUpdateInterval);
        viewUpdateInterval = null;
    }

    var mainpane = document.getElementById("displaymainpane");

    /* Get rid of anything from the previous view */
    if (mainpane != null) {
        while (mainpane.firstChild) {
            mainpane.removeChild(mainpane.firstChild);
        }
    }
}

function setCurrentView(view) {
    destroyCurrentView();

    currentView = view;

    /* Add a shiny brand new div for the new view to use */
    var viewdiv = document.createElement("div");

    var mainpane = document.getElementById("displaymainpane");
    mainpane.appendChild(viewdiv);

    /* Tell the view to set up the HTML it wants */
    currentView.setup(viewdiv);

    /* Start up the view updating interval again */
    viewUpdateInterval = setInterval(updateCurrentView, 1000);
}

function refreshFrameCurrentView() {
    var cont = currentView.refreshFrame(new Date().getTime());
    if (!cont) {
        /* animation complete - refreshFrame() calls no longer needed */
        clearInterval(viewRefreshFrameInterval);
        viewRefreshFrameInterval = null;
    }
}

function createNewViewFromTeleostMode() {
    destroyCurrentView();
    var view = null;

    if (teleostMode != null && teleostMode in teleostModesToCreateFunctions) {
        view = teleostModesToCreateFunctions[teleostMode](tourneyName, teleostModeOptions);
    }
    else {
        view = createPlaceholderScreen(tourneyName, teleostModeOptions);
    }
    setCurrentView(view);
}

function teleostOptionsEqual(oa, ob) {
    for (var key in oa) {
        if (!(key in ob) || oa[key] != ob[key])
            return false;
    }
    for (var key in ob) {
        if (!(key in oa) || oa[key] != ob[key])
            return false;
    }
    return true;
}

function fetchGameStateCallback() {
    var req = gameStateFetchRequest;
    if (req.readyState == 4) {
        if (req.status == 200 && req.responseText != null) {
            gameState = JSON.parse(req.responseText);
            gameStateRevision++;
            gameStateFetchRequest = null;

            if ("teleost" in gameState) {
                var newTeleostMode = gameState.teleost.current_mode;
                var newTeleostModeOptions = gameState.teleost.options;

                if (teleostMode == null || teleostMode != newTeleostMode ||
                        !teleostOptionsEqual(teleostModeOptions, newTeleostModeOptions)) {
                    currentViewDrawn = false;
                    currentView = null;
                    teleostMode = newTeleostMode;
                    teleostModeOptions = newTeleostModeOptions;
                    createNewViewFromTeleostMode();
                }
            }
        }
        else {
            gameState = { "success" : false, "description" : req.statusText };
            gameStateRevision++;
            gameStateFetchRequest = null;
        }

        if (!currentViewDrawn && currentView != null)
            updateCurrentView();
    }
}

function fetchGameStateError(req) {
    gameState = { "success" : false, "description" : req.statusText };
    gameStateRevision++;
    gameStateFetchRequest = null;
}

function fetchGameState() {
    var modeParam = "";
    if (displayMode >= 0) {
        modeParam = "&mode=" + displayMode.toString();
    }

    if (gameStateFetchRequest != null) {
        /* Previous request is still running */
        return;
    }

    gameStateFetchRequest = new XMLHttpRequest();

    gameStateFetchRequest.open("GET",
            "/cgi-bin/jsonreq.py?tourney=" + encodeURIComponent(tourneyName) +
            "&request=default" + modeParam, true);
    gameStateFetchRequest.onreadystatechange = fetchGameStateCallback;
    gameStateFetchRequest.onerror = fetchGameStateError;
    gameStateFetchRequest.send(null);
}


function displaySetup() {
    teleostModesToCreateFunctions[TELEOST_MODE_STANDINGS] = createStandingsScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_STANDINGS_VIDEPRINTER] = createStandingsAndVideprinterScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_STANDINGS_RESULTS] = createStandingsAndRoundResultsScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_TECHNICAL_DIFFICULTIES] = createTechnicalDifficultiesScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_FIXTURES] = createFixturesScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_TABLE_NUMBER_INDEX] = createTableNumberIndexScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_OVERACHIEVERS] = createOverachieversScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_TUFF_LUCK] = createTuffLuckScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_HIGH_SCORES] = createHighScoresScreen;
    //teleostModesToCreateFunctions[TELEOST_MODE_FASTEST_FINISHERS] = createPlaceholderScreen;
    //teleostModesToCreateFunctions[TELEOST_MODE_CLOCK] = createClockScreen;

    fetchGameState();
    viewUpdateInterval = setInterval(updateCurrentView, 1000);
    refreshGameStateInterval = setInterval(fetchGameState, 5000);
}

