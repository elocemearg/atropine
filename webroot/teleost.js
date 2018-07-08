var gameState = null;
var gameStateRevision = 0;

var gameStateFetchRequest = null;

var viewUpdateInterval = null;
var refreshGameStateInterval = null;
var currentView = null;
var currentViewDrawn = false;
var viewRefreshFrameInterval = null;
var animationFrameMs = 50;
var updatesSkipped = 0;
var updatesMaxSkip = 5;

var teleostMode = null;
var teleostModeOptions = {};
var teamIndicatorHTML = "&#10022;"

function refreshFrameCurrentView() {
    var cont = currentView.refreshFrame(new Date().getTime());
    if (!cont) {
        /* animation complete - refreshFrame() calls no longer needed */
        clearInterval(viewRefreshFrameInterval);
        viewRefreshFrameInterval = null;
    }
}

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

var teleostModesToCreateFunctions = {};

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

function displaySetup() {
    teleostModesToCreateFunctions[TELEOST_MODE_STANDINGS] = createStandingsScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_STANDINGS_VIDEPRINTER] = createStandingsAndVideprinterScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_STANDINGS_RESULTS] = createStandingsAndRoundResultsScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_TECHNICAL_DIFFICULTIES] = createTechnicalDifficultiesScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_FIXTURES] = createFixturesScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_TABLE_NUMBER_INDEX] = createTableNumberIndexScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_OVERACHIEVERS] = createOverachieversScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_TUFF_LUCK] = createTuffLuckScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_RECORDS] = createPlaceholderScreen;
    teleostModesToCreateFunctions[TELEOST_MODE_FASTEST_FINISHERS] = createPlaceholderScreen;

    fetchGameState();
    viewUpdateInterval = setInterval(updateCurrentView, 1000);
    refreshGameStateInterval = setInterval(fetchGameState, 5000);
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


function escapeHTML(str) {
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

function formatScore(s1, s2, tb) {
    var text;
    if (s1 == null || s2 == null) {
        /* Game hasn't been played yet */
        text = "&ndash;";
    }
    else if (s1 == 0 && s2 == 0 && tb) {
        /* Double-loss, for when we eventually support this: X - X */
        text = "&#10006 &ndash; &#10006;";
    }
    else {
        /* Game is complete */
        text = s1.toString();
        if (tb && s1 > s2) {
            text += "*";
        }
        text += " &ndash; ";
        text += s2.toString();
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

class View {
    constructor (tourneyName, leftPc, topPc, widthPc, heightPc) {
        this.tourneyName = tourneyName;
        this.leftPc = leftPc;
        this.topPc = topPc;
        this.widthPc = widthPc;
        this.heightPc = heightPc;
    }

    setup(container) {
        this.container = container;
        this.container.style.position = "absolute";
        this.container.style.top = this.topPc.toString() + "%";
        this.container.style.left = this.leftPc.toString() + "%";
        this.container.style.width = this.widthPc.toString() + "%";
        this.container.style.height = this.heightPc.toString() + "%";
    }

    /* Gives the view an opportunity to repaint itself using information in
     * the global gameState variable.
     * Return true if the refresh operation needs to be animated. In that
     * case refreshFrame() will be called after every animationFrameMs
     * milliseconds until refreshFrame() returns false.
     *
     * If enableAnimation is false, refresh() must complete the repaint
     * operation and must return false. refreshFrame() will not be called.
     */
    refresh(timeNow, enableAnimation) {
    }

    refreshFrame(timeNow) {
    }

    redraw() {
    }

    getGameState() {
        if (gameState == null) {
            return { "success" : false, "description" : "Please wait..." };
        }
        return gameState;
    }

    findSelectedDivisions(games, whichDiv) {
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

    findSelectedRoundsPerDivision(games, whichRnd) {
        var ret = {};
        var divisions = games.divisions;

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

                if (whichRnd == -1) {
                    /* All rounds */
                    for (var r in roundGameCounts) {
                        selectedRounds.push(r);
                    }
                }
                else if (whichRnd == -2) {
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
                else if (whichRnd == -3) {
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
                else if (whichRnd == -4) {
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
        return ret;
    }
}

class PagedTableView extends View {
    /* Any view consisting of a number of pages, each with a number of rows,
     * and we scroll from page to page periodically */
    constructor (tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
        this.rowsPerPage = rowsPerPage;
        this.currentPageIndex = 0;
        this.lastScroll = 0;
        this.newPageInfo = null;
        this.scrollPeriod = scrollPeriod;
    }

    nextPage() {
        this.currentPageIndex += 1;
    }

    getFrameSlowdownFactor() {
        return 1;
    }

    refresh(timeNow, enableAnimation) {
        var doRedraw = (this.lastGameRevisionSeen == null || this.lastGameRevisionSeen != gameStateRevision);
        var doScroll = false;
        var oldPageIndex = this.currentPageIndex;

        if (this.lastScroll + this.scrollPeriod <= timeNow) {
            if (this.lastScroll > 0) {
                /* We want to scroll to the next page */
                this.nextPage();
                doScroll = true;
            }
            this.lastScroll = timeNow;
            doRedraw = true;
        }

        if (doRedraw) {
            this.newPageInfo = this.getPageInfo();

            /* Don't do the scrolly effect if we're scrolling from one
             * page to the same page, e.g. if there's only one page. */
            if (oldPageIndex == this.currentPageIndex)
                doScroll = false;
        }

        if (this.pageInfoIsSuccessful(this.newPageInfo) && enableAnimation) {
            if (doScroll) {
                this.animateFrameNumber = 0;
                this.animateFramesMoved = 0;
                this.animateNumRowsCleared = 0;
                this.animateNumRowsFilled = 0;
                return true;
            }
        }
        if (doRedraw) {
            if (this.pageInfoIsSuccessful(this.newPageInfo))
                this.redraw(this.newPageInfo);
            else
                this.redrawError(this.newPageInfo);
        }
        return false;
    }

    refreshFrame(timeNow) {
        if (this.animateFrameNumber % this.getFrameSlowdownFactor() == 0) {
            /* Fill in a row this many frames after it was cleared */
            var replaceRowDelay = this.rowsPerPage / 2 + 1;
            if (replaceRowDelay < 3)
                replaceRowDelay = 3;
            if (replaceRowDelay > this.rowsPerPage)
                replaceRowDelay = this.rowsPerPage;

            if (this.animateNumRowsCleared < this.rowsPerPage) {
                this.clearRow(this.animateNumRowsCleared);
                this.animateNumRowsCleared++;
            }

            if (this.animateFramesMoved >= replaceRowDelay || this.animateFramesMoved >= this.rowsPerPage) {
                if (this.animateNumRowsFilled == 0)
                    this.redrawHeadings(this.newPageInfo);
                this.redrawRow(this.newPageInfo, this.animateNumRowsFilled);
                this.animateNumRowsFilled++;
            }
            this.animateFramesMoved++;
        }
        this.animateFrameNumber++;

        return (this.animateNumRowsFilled < this.rowsPerPage);
    }

    redraw(page) {
        this.redrawHeadings(page);

        for (var tableRow = 0; tableRow < this.rowsPerPage; ++tableRow) {
            this.redrawRow(page, tableRow);
        }
    }
}

class FixturesView extends PagedTableView {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod, whichDivision, whichRound) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod);
        this.lastGameRevisionSeen = null;

        /* whichDivision: if it's -1, then it means all divisions. */
        this.whichDivision = whichDivision;

        /* whichRound:
         * -1: all rounds
         * -2: the last round in the division with at least one completed game
         * -3: the round after the last completed round, or the last completed
         *     round if that is the last round
         * -4: the earliest round in the division with no completed games
         */
        this.whichRound = whichRound;

        this.numDivisions = 0;
    }

    setup(container) {
        super.setup(container);
        container.style.maxWidth = "100%";

        var html = "";
        html += "<div class=\"fixturescontainer\">";
        html += "<div class=\"headingbar fixturesheading\" id=\"fixturesheading\">";
        html += "<div class=\"fixturesheadingtext\" id=\"fixturesheadingtext\">";
        html += "&nbsp;";
        html += "</div>";
        html += "</div>";

        html += "<table class=\"fixtures\">";

        for (var row = 0; row < this.rowsPerPage; ++row) {
            html += "<tr id=\"fixturesrow" + row.toString() + "\">";
            html += "<td class=\"fixturestablenumbercell\"><div class=\"fixturestablenumber\">&nbsp;</div></td>";
            html += "</tr>";
        }

        html += "</table>";
        html += "</div>";

        container.innerHTML = html;
    }


    getPageInfo() {
        this.lastGameRevisionSeen = gameStateRevision;
        var gameState = this.getGameState();

        // games, partitioned into division&round, then table number
        var gamesGroups = [];
        
        var pages = [];
        var page = [];
        var errorString = null;
        var teamScores = null;

        if (gameState.success) {
            var selectedDivisions = this.findSelectedDivisions(gameState.games, this.whichDivision);
            var selectedRoundsPerDivision = this.findSelectedRoundsPerDivision(gameState.games, this.whichRound);

            var divRoundGroup = [];
            var tableGroup = [];

            var divisionInfo = gameState.structure.divisions;
            var roundInfo = gameState.structure.rounds;

            var divisions = gameState.games.divisions;
            var prevGame = null;
            for (var divIndex = 0; divIndex < divisions.length; ++divIndex) {
                var divNum = divisions[divIndex].div_num;
                var showDivision = false;
                for (var i = 0; i < selectedDivisions.length; ++i) {
                    if (selectedDivisions[i] == divNum) {
                        showDivision = true;
                        break;
                    }
                }
                if (!showDivision)
                    continue;

                var selectedRounds = selectedRoundsPerDivision[divNum];

                var games = divisions[divNum].games;

                for (var roundListIndex = 0; roundListIndex < selectedRounds.length; ++roundListIndex) {
                    var selectedRound = selectedRounds[roundListIndex];
                    
                    for (var gameIndex = 0; gameIndex < games.length; ++gameIndex) {
                        var game = games[gameIndex];
                        if (game.round != selectedRound)
                            continue;

                        game.divNum = divNum;
                        game.divName = divisions[divNum].div_name;

                        var roundName = null;
                        for (var roundIndex = 0; roundIndex < roundInfo.length; ++roundIndex) {
                            if (roundInfo[roundIndex].num == game.round)
                                roundName = roundInfo[roundIndex].name;
                        }
                        if (roundName != null) {
                            game.roundName = roundName;
                        }
                        else {
                            game.roundName = "Round " + game.round.toString();
                        }

                        if (prevGame != null && (prevGame.divNum != divNum ||
                                prevGame.round != game.round ||
                                prevGame.table != game.table)) {
                            /* This is a new division, round or table number,
                             * so this game needs to be at least in a new
                             * block */
                            divRoundGroup.push(tableGroup);
                            tableGroup = [];

                            if (prevGame.divNum != divNum || prevGame.round != game.round) {
                                /* This is a new division or round number, so
                                 * as well as being a new block, this block
                                 * needs to start a new page. */
                                gamesGroups.push(divRoundGroup);
                                divRoundGroup = [];
                            }
                        }

                        tableGroup.push(game);
                        prevGame = game;
                    }
                }
            }

            this.numDivisions = divisionInfo.length;

            if (tableGroup.length > 0) {
                divRoundGroup.push(tableGroup);
                tableGroup = [];
            }
            if (divRoundGroup.length > 0) {
                gamesGroups.push(divRoundGroup);
                divRoundGroup = [];
            }

            /* Now we've got the games grouped by division&round, then by
             * table number, we can separate them out into pages.
             * 
             * The rules are:
             * 
             * A new round, or a new division, always starts on a new page.
             * 
             * Games on the same table, in the same round of the same division,
             * are all shown on the same page if possible. This means if we
             * have two rows of space left on this page, and the next table
             * group has three games in it, the whole table group has to go
             * on a new page.
             * 
             * If we start a new page, and the table has so many games in it
             * that they won't even fit on an empty page, then and only
             * then do we split that table across two (or more) pages.
             */
            for (var divRoundIndex = 0; divRoundIndex < gamesGroups.length; ++divRoundIndex) {
                var roundGroup = gamesGroups[divRoundIndex];
                for (var tableIndex = 0; tableIndex < roundGroup.length; ++tableIndex) {
                    var tableGroup = roundGroup[tableIndex];
                    var pageRowCount = 0;
                    for (var i = 0; i < page.length; ++i) {
                        pageRowCount += page[i].length;
                    }
                    if (pageRowCount + tableGroup.length > this.rowsPerPage) {
                        /* This table won't all fit on this page. If the page
                         * is empty, then put as much as we can in this page
                         * and the remainder in new pages.
                         * If the current page is not empty, then start a
                         * new page. */
                        if (pageRowCount == 0) {
                            /* Split the table */
                            var partialTableGroup = [];
                            for (var gameIndex = 0; gameIndex < tableGroup.length; ++gameIndex) {
                                if (partialTableGroup.length >= this.rowsPerPage) {
                                    page.push(partialTableGroup);
                                    pages.push(page);
                                    page = [];
                                    partialTableGroup = [];
                                }
                                partialTableGroup.push(tableGroup[gameIndex]);
                            }
                            if (partialTableGroup.length > 0) {
                                page.push(partialTableGroup);
                            }
                        }
                        else {
                            // Start a new page, and add the table group to it
                            pages.push(page);
                            page = [];
                            page.push(tableGroup);
                        }
                    }
                    else {
                        // add this table to the page, we know it'll fit
                        page.push(tableGroup);
                    }
                }

                pages.push(page);
                page = [];
            }

            if (gameState.structure.teams) {
                teamScores = gameState.structure.teams;
            }
        }
        else {
            pages = [];
            errorString = gameState.description;
        }

        /* Then after all that, we only return one page */
        if (this.currentPageIndex >= pages.length)
            this.currentPageIndex = 0;
        if (this.currentPageIndex >= pages.length)
            return { "teamScores" : teamScores, "page" : [] };

        return {
            "teamScores" : teamScores,
            "page" : pages[this.currentPageIndex],
            "errorString" : errorString
        };
    }

    removeRow(rowNum) {
        var rowName = "fixturesrow" + rowNum.toString();
        document.getElementById(rowName).style.display = "none";
    }

    pageInfoIsSuccessful(fixturesObject) {
        return !("errorString" in fixturesObject) || (fixturesObject.errorString == null)
    }

    redrawHeadings(fixturesObject) {
        if (fixturesObject == null)
           return;

        var page = fixturesObject.page;

        var firstGame = page[0][0];
        var headingElement = document.getElementById("fixturesheadingtext");
        if (headingElement != null) {
            var html = "";
            if (this.numDivisions > 1) {
                html += "<span class=\"fixturesheadingdivision\">" +
                    escapeHTML(firstGame.divName) + "</span>";
            }
            html += "<span class=\"fixturesheadinground\">" +
                escapeHTML(firstGame.roundName) + "</span>";

            if (fixturesObject.teamScores) {
                html += "<span class=\"fixturesheadingteamscore\" style=\"margin-top: 0.6vh;\">";
                for (var i = fixturesObject.teamScores.length - 1; i >= 0; --i) {
                    var team = fixturesObject.teamScores[i];
                    html += "<div class=\"teamscore teamscoreright\" style=\"background-color: " + teamColourToHTML(team.colour) + "\">";
                    html += team.score.toString();
                    html += "</div>";
                }
                html += "</span>";
            }

            headingElement.innerHTML = html;
        }
    }

    redrawError(fixturesObject) {
        var headingElement = document.getElementById("fixturesheadingtext");
        headingElement.innerText = "" + fixturesObject.errorString;
    }

    redrawRow(fixturesObject, tableRow) {
        if (fixturesObject != null && fixturesObject.page != null) {
            /* If the row specified by tableRow refers to the first game on a
             * table, then this will redraw the table number as well. */
            var page = fixturesObject.page;
            var rowsInPrevBlock = 0;
            var game = null;
            var isFirstInBlock = false;
            var isLastInBlock = false;
            var numGamesInBlock = 0;

            for (var tableGroupIndex = 0; tableGroupIndex < page.length; ++tableGroupIndex) {
                var tableGroup = page[tableGroupIndex];
                if (rowsInPrevBlock + tableGroup.length <= tableRow) {
                    rowsInPrevBlock += tableGroup.length;
                }
                else {
                    game = tableGroup[tableRow - rowsInPrevBlock];
                    isFirstInBlock = (tableRow - rowsInPrevBlock == 0);
                    isLastInBlock = (tableRow - rowsInPrevBlock == tableGroup.length - 1);
                    numGamesInBlock = tableGroup.length;
                    break;
                }
            }
            if (game != null) {
                this.setRow(tableRow, game, isFirstInBlock, isLastInBlock, numGamesInBlock);
            }
            else {
                while (tableRow < this.rowsPerPage) {
                    this.removeRow(tableRow);
                    tableRow++;
                }
            }
        }
    }

    clearRow(rowNum) {
        var rowName = "fixturesrow" + rowNum.toString();
        var tr = document.getElementById(rowName);
        if (tr != null) {
            /* Remove the text in everything */
            var next = null;
            for (var child = tr.firstChild; child != null; child = next) {
                next = child.nextSibling;
                child.innerText = "";
            }
        }
    }

    setRow(rowNum, game, isFirstInBlock, isLastInBlock, numGamesInBlock) {
        var rowName = "fixturesrow" + rowNum.toString();
        var tr = document.getElementById(rowName);

        if (tr == null)
            return;

        /* First, clear the appropriate tr element of everything, even
         * the table number */
        while (tr.firstChild) {
            tr.removeChild(tr.firstChild);
        }

        if (isLastInBlock)
            tr.classList.add("fixturesrowlastinblock");
        else
            tr.classList.remove("fixturesrowlastinblock");

        /* If this is the first game in a table block, draw the table number,
         * which spans the appropriate number of rows */
        if (isFirstInBlock) {
            var td = document.createElement("td");
            var tabNumPadding = null;
            td.classList.add("fixturestablenumbercell");
            td.setAttribute("rowspan", numGamesInBlock.toString());
            if (numGamesInBlock <= 1) {
                td.style.fontSize = "4vmin";
            }
            else if (numGamesInBlock == 2) {
                td.style.fontSize = "5.5vmin";
            }
            else {
                td.style.fontSize = "7vmin";
                tabNumPadding = "1vmin";
            }

            var tabNumDiv = document.createElement("div");
            tabNumDiv.classList.add("fixturestablenumber");
            if (tabNumPadding != null) {
                tabNumDiv.style.paddingTop = tabNumPadding;
                tabNumDiv.style.paddingBottom = tabNumPadding;
            }
            tabNumDiv.innerText = game.table.toString();
            td.appendChild(tabNumDiv);
            tr.appendChild(td);
        }

        var team1html = "";
        var team2html = "";

        if (game.teamcolour1) {
            team1html = " <span class=\"teamdotleftplayer\" style=\"color: " + teamColourToHTML(game.teamcolour1) + "\">" + teamIndicatorHTML + "</span>";
        }
        if (game.teamcolour2) {
            team2html = "<span class=\"teamdotleftplayer\" style=\"color: " + teamColourToHTML(game.teamcolour2) + "\">" + teamIndicatorHTML + "</span> ";
        }

        var td_p1 = document.createElement("td");
        td_p1.classList.add("fixturesp1");
        td_p1.innerHTML = escapeHTML(game.name1) + team1html;
        tr.appendChild(td_p1);

        var td_score = document.createElement("td");
        td_score.classList.add("fixturesscore");
        if (game.complete)
            td_score.innerHTML = formatScore(game.score1, game.score2, game.tb);
        else
            td_score.innerText = "v";
        tr.appendChild(td_score);

        var td_p2 = document.createElement("td");
        td_p2.classList.add("fixturesp2");
        td_p2.innerHTML = team2html + escapeHTML(game.name2);
        tr.appendChild(td_p2);

        tr.style.display = null;
    }
}

class RoundResultsView extends PagedTableView {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage < 2 ? 2 : rowsPerPage, scrollPeriod);
        this.lastGameRevisionSeen = null;
    }

    setup(container) {
        super.setup(container);
        container.style.maxWidth = "100%";

        var html = "";
        html += "<div class=\"headingbar roundresultsheading\" id=\"roundresultsheading\">";
        html += "<span class=\"roundresultsdivision\" id=\"roundresultsdivision\">&nbsp;</span>";
        html += "<span class=\"roundresultsround\" id=\"roundresultsround\">&nbsp;</span>";
        html += "</div>";

        html += "<table class=\"roundresults\">";
        html += "<colgroup>";
        html += "<col class=\"roundresultscolp1\" />";
        html += "<col class=\"roundresultscolscore\" />";
        html += "<col class=\"roundresultscolp2\" />";
        html += "</colgroup>";
        for (var i = 0; i < this.rowsPerPage; ++i) {
            var rowName = "resultsrow" + i.toString();
            html += "<tr id=\"" + rowName + "\">";
            html += "<td class=\"roundresultsp1\" id=\"" + rowName + "_p1\">&nbsp;</td>";
            html += "<td class=\"roundresultsscore\" id=\"" + rowName + "_score\">&nbsp;</td>";
            html += "<td class=\"roundresultsp2\" id=\"" + rowName + "_p2\">&nbsp;</td>";
            html += "</tr>";
        }
        html += "</table>";

        container.innerHTML = html;
    }

    getPageInfo() {
        this.lastGameRevisionSeen = gameStateRevision;
        var gameState = this.getGameState();
        var pages = [];
        var page = [];
        var divisionToCurrentRound = {};
        var divisionToMaxGamesPerTable = {};

        if (gameState.success) {
            var games = gameState.games;
            var divisions = games.divisions;
            /* For each division, find the latest round which has at least
             * one game completed, and call that the "current" round for the
             * purpose of this view */
            for (var divIndex = 0; divIndex < divisions.length; ++divIndex) {
                var divGames = divisions[divIndex].games;
                for (var gameIndex = 0; gameIndex < divGames.length; ++gameIndex) {
                    if (divGames[gameIndex].complete) {
                        var rnd = divGames[gameIndex].round;
                        if (divIndex in divisionToCurrentRound) {
                            if (rnd > divisionToCurrentRound[divIndex])
                                divisionToCurrentRound[divIndex] = rnd;
                        }
                        else {
                            divisionToCurrentRound[divIndex] = rnd;
                        }
                    }
                }
            }

            for (var divIndex = 0; divIndex < divisions.length; ++divIndex) {
                if (!(divIndex in divisionToCurrentRound))
                    continue;
                var maxGamesPerTable = divisions[divIndex].max_games_per_table;
                var divGames = divisions[divIndex].games;
                for (var gameIndex = 0; gameIndex < divGames.length; ++gameIndex) {
                    var game = divGames[gameIndex];

                    if (game.round != divisionToCurrentRound[divIndex])
                        continue;
                    if (page.length > 0) {
                        /* If we already have an entry on this page, and this
                         * game is for a different round number or
                         * table number, then start a new page.
                         * Also start a new page if we've already filled
                         * this one. */
                        if (page.length >= this.rowsPerPage + 1 ||
                                page[0].roundNumber != game.round ||
                                (maxGamesPerTable > 1 && page[0].tableNumber != game.table)) {
                            pages.push(page);
                            page = [];
                        }
                    }
                    if (page.length == 0) {
                        /* First, set the heading for this page */
                        page.push( { "errorString" : null,
                                     "divName" : (divisions.length > 1 ? divisions[divIndex].div_name : ""),
                                     "roundNumber" : game.round,
                                     "roundName" : ("Round " + game.round.toString()),
                                     "tableNumber" : (maxGamesPerTable > 1 ? game.table : null)
                                    });
                    }

                    /* Elements 1 and up of the "page" array contain
                     * dictionary objects, each describing a game. */
                    page.push(game);
                }

                if (page.length > 0) {
                    pages.push(page);
                    page = [];
                }
            }
        }
        else {
            pages = [ [ { "errorString" : gameState.description } ] ];
        }

        if (this.currentPageIndex >= pages.length)
            this.currentPageIndex = 0;

        if (this.currentPageIndex >= pages.length)
            return [];
        else
            return pages[this.currentPageIndex];
    }

    getFrameSlowdownFactor() {
        if (this.rowsPerPage > 4)
            return 1;
        else
            return 2;
    }

    removeRow(rowNum) {
        var rowName = "resultsrow" + rowNum.toString();
        document.getElementById(rowName).style.display = "none";
    }

    pageInfoIsSuccessful(page) {
        return page != null && (page.length == 0 || page[0].errorString == null);
    }

    redrawHeadings(page) {
        var divisionHeading = document.getElementById("roundresultsdivision");
        var roundHeading = document.getElementById("roundresultsround");
        if (page.length < 1) {
            divisionHeading.innerHTML = "&nbsp;";
            roundHeading.innerHTML = "&nbsp;";
        }
        else {
            divisionHeading.innerText = page[0].divName;
            var roundMarkup = "";
            if (page[0].tableNumber != null) {
                roundMarkup = "<span class=\"roundresultsleftheading\">";
                roundMarkup += escapeHTML(page[0].roundName);
                roundMarkup += "</span> ";
                roundMarkup += "<span class=\"roundresultsrightheading\">";
                roundMarkup += "Table " + escapeHTML(page[0].tableNumber.toString());
                roundMarkup += "</span>";
            }
            else {
                roundMarkup = "<span class=\"roundresultscentreheading\">";
                roundMarkup += escapeHTML(page[0].roundName);
                roundMarkup += "</span> ";
            }
            roundHeading.innerHTML = roundMarkup;
        }
    }

    redrawError(page) {
        var heading = document.getElementById("resultsrow0_p1");
        heading.innerText = "" + page[0].errorString;
    }

    redrawRow(page, tableRow) {
        if (page != null) {
            if (tableRow + 1 < page.length) {
                this.setRow(tableRow, page[tableRow + 1]);
            }
            else {
                while (tableRow < this.rowsPerPage) {
                    this.removeRow(tableRow);
                    tableRow++;
                }
            }
        }
    }

    clearRow(rowNum) {
        var rowName = "resultsrow" + rowNum.toString();
        var p1_element = document.getElementById(rowName + "_p1");
        var score_element = document.getElementById(rowName + "_score");
        var p2_element = document.getElementById(rowName + "_p2");

        p1_element.innerHTML = "&nbsp;";
        p2_element.innerHTML = "&nbsp;";
        score_element.innerHTML = "&nbsp;";
    }

    setRow(tableRow, row) {
        var rowName = "resultsrow" + tableRow.toString();
        var p1_element = document.getElementById(rowName + "_p1");
        var score_element = document.getElementById(rowName + "_score");
        var p2_element = document.getElementById(rowName + "_p2");
        var team1html = "";
        var team2html = "";

        if (row.teamcolour1) {
            team1html = " <span class=\"teamdotleftplayer\" style=\"color: " + teamColourToHTML(row.teamcolour1) + "\">" + teamIndicatorHTML + "</span>"
        }
        if (row.teamcolour2) {
            team2html = "<span class=\"teamdotrightplayer\" style=\"color: " + teamColourToHTML(row.teamcolour2) + "\">" + teamIndicatorHTML + "</span> "
        }

        document.getElementById(rowName).style.display = null;

        p1_element.innerHTML = escapeHTML(row.name1) + team1html;
        p2_element.innerHTML = team2html + escapeHTML(row.name2);
        if (row.complete) {
            score_element.innerHTML = formatScore(row.score1, row.score2, row.tb);
        }
        else {
            score_element.innerHTML = "&ndash;";
        }
    }
}

class StandingsView extends PagedTableView {
    constructor (tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod);
        this.lastGameRevisionSeen = null;
    }

    setup(container) {
        super.setup(container);
        container.style.maxWidth = "100%";
        var html = "";
        html += "<table class=\"teleoststandings\">";
        html += "<colgroup>";
        html += "<col class=\"teleoststandingscolpos teleostnumber\" />";
        html += "<col class=\"teleoststandingscolname\" />";
        html += "<col class=\"teleoststandingscolplayed teleostnumber\" />";
        html += "<col class=\"teleoststandingscolwins teleostnumber\" />";
        html += "<col class=\"teleoststandingscolpoints teleostnumber\" />";
        html += "</colgroup>";
        html += "<tr class=\"headingbar teleoststandingsheadingrow\">";
        html += "<th class=\"teleoststandingsheadingnumber\"></th>";
        html += "<th id=\"teleoststandingsdivisionname\" class=\"teleoststandingsheadingstring\"></th>";
        html += "<th class=\"teleoststandingsheadingnumber\">P</th>";
        html += "<th class=\"teleoststandingsheadingnumber\">W</th>";
        html += "<th id=\"teleoststandingspointsheading\" class=\"teleoststandingsheadingnumber\">Pts</th>";
        html += "</tr>";
        for (var i = 0; i < this.rowsPerPage; ++i) {
            var rowName = "standingsrow" + i.toString();
            html += "<tr id=\"" + rowName + "\">";
            html += "<td class=\"teleoststandingspos teleostnumber\" id=\"" + rowName + "_pos\"></td>";
            html += "<td id=\"" + rowName + "_name\"></td>";
            html += "<td class=\"teleoststandingsnumbercol teleostnumber\" id=\"" + rowName + "_played\"></td>";
            html += "<td class=\"teleoststandingsnumbercol teleostnumber\" id=\"" + rowName + "_wins\"></td>";
            html += "<td class=\"teleoststandingsnumbercol teleostnumber\" id=\"" + rowName + "_points\">---</td>";
            html += "</tr>";
        }
        html += "</table>";
        container.innerHTML = html;
    }


    getPageInfo() {
        this.lastGameRevisionSeen = gameStateRevision;
        var gameState = this.getGameState();
        var pages = [];
        var pageDivisions = [];
        var pageRows = [];
        var page = null;
        var divisionName = "";
        var rankFields = [];
        var useSpread = false;
        var showDivisionName = false;
        var standings = null;
        var errorString = null;
        var teamScores = null;

        if (gameState.success) {
            standings = gameState.standings;
            for (var divIndex = 0; divIndex < standings.divisions.length; divIndex++) {
                var divStandings = standings.divisions[divIndex].standings;
                for (var standingsIndex = 0; standingsIndex < divStandings.length; ++standingsIndex) {
                    if (pageRows.length >= this.rowsPerPage) {
                        pages.push(pageRows);
                        pageDivisions.push(standings.divisions[divIndex].div_name);
                        pageRows = [];
                    }
                    pageRows.push(divStandings[standingsIndex]);
                }
                if (pageRows.length > 0) {
                    pages.push(pageRows);
                    pageDivisions.push(standings.divisions[divIndex].div_name);
                    pageRows = [];
                }
            }

            if (standings.divisions.length > 1)
                showDivisionName = true;

            rankFields = standings.rank_fields;

            if (this.currentPageIndex >= pages.length) {
                this.currentPageIndex = 0;
            }
            if (this.currentPageIndex >= pages.length) {
                page = [];
                divisionName = "";
            }
            else {
                page = pages[this.currentPageIndex];
                divisionName = pageDivisions[this.currentPageIndex];
            }

            if (gameState.structure.teams) {
                teamScores = gameState.structure.teams;
            }
        }
        else {
            errorString = gameState.description;
        }

        for (var i = 0; i < rankFields.length; ++i) {
            if (rankFields[i] == "points") {
                break;
            }
            if (rankFields[i] == "spread") {
                useSpread = true;
                break;
            }
        }

        return {
            "standingsPage" : page,
            "divisionName" : divisionName,
            "showDivisionName" : showDivisionName,
            "useSpread" : useSpread,
            "teamScores" : teamScores,
            "errorString" : errorString
        };
    }

    clearRow(rowNum) {
        var rowName = "standingsrow" + rowNum.toString();

        document.getElementById(rowName + "_pos").innerHTML = "&nbsp;";
        document.getElementById(rowName + "_name").innerHTML = "&nbsp;";
        document.getElementById(rowName + "_played").innerHTML = "&nbsp;";
        document.getElementById(rowName + "_wins").innerHTML = "&nbsp;";
        document.getElementById(rowName + "_points").innerHTML = "&nbsp;";
        document.getElementById(rowName).style.display = null;
    }

    removeRow(rowNum) {
        var rowName = "standingsrow" + rowNum.toString();
        document.getElementById(rowName).style.display = "none";
    }

    setRow(tableRow, standing, useSpread) {
        var pos = "";
        var name = "";
        var played = "";
        var wins = "";
        var wins_string = "";
        var points = "";
        var spread = "";
        var rowName = "standingsrow" + tableRow.toString();
        var withdrawn = false;

        pos = standing.position;
        name = standing.name;
        played = standing.played;
        wins = standing.wins;
        var draws = standing.draws;
        if (draws > 0) {
            wins += Math.floor(draws / 2);
            wins_string = wins.toString();
            if (draws % 2 == 1) {
                if (wins == 0)
                    wins_string = "";
                wins_string += "&frac12;";
            }
        }
        else {
            wins_string = wins.toString();
        }

        points = standing.points;
        spread = standing.spread;
        withdrawn = standing.withdrawn;
        if (spread > 0)
            spread = "+" + spread.toString();

        var rowElement = document.getElementById(rowName);
        rowElement.style.display = null;

        if (withdrawn) {
            pos = makeWithdrawn(pos.toString(), true);
            name = makeWithdrawn(name, true);
            played = makeWithdrawn(played.toString(), true);
            wins_string = makeWithdrawn(wins_string.toString(), false);
            spread = makeWithdrawn(spread.toString(), true);
            points = makeWithdrawn(points.toString(), true);
        }
        else {
            name = escapeHTML(name);
        }

        if (standing.team_colour) {
            name = "<span class=\"teamdotrightplayer\" style=\"color: " + teamColourToHTML(standing.team_colour) + ";\">" + teamIndicatorHTML + "</span> " + name;
        }

        document.getElementById(rowName + "_pos").innerHTML = pos;
        document.getElementById(rowName + "_name").innerHTML = name;
        document.getElementById(rowName + "_played").innerHTML = played;
        document.getElementById(rowName + "_wins").innerHTML = wins_string;

        var pointsElement = document.getElementById(rowName + "_points");
        if (useSpread)
            pointsElement.innerHTML = spread;
        else
            pointsElement.innerHTML = points;
    }

    pageInfoIsSuccessful(standingsObject) {
        return standingsObject != null && standingsObject.errorString == null;
    }

    redrawHeadings(standingsObject) {
        var pointsHeading = document.getElementById("teleoststandingspointsheading");
        if (standingsObject.useSpread) {
            pointsHeading.innerText = "Spr";
        }
        else {
            pointsHeading.innerText = "Pts";
        }

        var divisionNameElement = document.getElementById("teleoststandingsdivisionname");
        if (standingsObject.showDivisionName) {
            divisionNameElement.innerHTML = escapeHTML(standingsObject.divisionName);
        }
        else {
            divisionNameElement.innerHTML = " ";
        }
        
        /* If there are teams, squeeze the team score into here as well */
        var teamScores = standingsObject.teamScores;
        if (teamScores) {
            var html = " ";
            for (var i = 0; i < teamScores.length; ++i) {
                html += "<div class=\"teamscore teamscoreleft\" style=\"background-color: " + teamColourToHTML(teamScores[i].colour) + "\">";
                html += teamScores[i].score.toString();
                html += "</div>"
            }
            divisionNameElement.innerHTML += html;
        }
    }

    redrawError(standingsObject) {
        for (var i = 0; i < this.rowsPerPage; ++i) {
            this.clearRow(i);
        }
        document.getElementById("standingsrow0_name").innerText = standingsObject.errorString;
    }

    redrawRow(standingsObject, tableRow) {
        var page = standingsObject.standingsPage;

        if (page != null) {
            if (tableRow < page.length) {
                this.setRow(tableRow, page[tableRow], standingsObject.useSpread);
            }
            else {
                while (tableRow < this.rowsPerPage) {
                    this.removeRow(tableRow);
                    tableRow++;
                }
            }
        }
    }
}

class VideprinterView extends View {
    constructor (tourneyName, leftPc, topPc, widthPc, heightPc, numRows) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
        this.numRows = numRows;
        this.latestGameRevisionSeen = null;
        this.latestLogSeqShown = null;
    }

    setup(container) {
        super.setup(container);
        var html = "";

        html += "<div class=\"videprintercontainer\">"
        html += "<table class=\"teleostvideprinter\">";

        for (var row = 0; row < this.numRows; ++row) {
            html += "<tr class=\"teleostvideprinterrow\">";
            html += "<td class=\"teleostvideprinterentry\" id=\"videprinterrow" + row.toString() + "_main\">-</td>";
            html += "</tr>";
        }
        html += "</table>";
        html += "</div>";

        container.innerHTML = html;
    }

    format_videprinter_preamble(entry) {
        var html = "";
        var supersededClass = entry.superseded ? " videprintersuperseded" : "";

        html += "<span class=\"videprinterroundandtable" + supersededClass + "\">";
        if (entry.game_type == "P" || entry.game_type == "N") {
            html += "R" + entry.round_no.toString() + "T" + entry.table_no.toString();
        }
        else {
            html += escapeHTML(entry.game_type) + " " + entry.table_no.toString();
        }
        html += "</span>";
        return html;
    }

    format_videprinter_entry(entry) {
        var html = "";
        var supersededClass = entry.superseded ? " videprintersuperseded" : "";

        html += "<span class=\"videprinterplayer" + supersededClass + "\">";
        html += escapeHTML(entry.p1);
        if (entry.tc1 != null) {
            html += "<span class=\"teamdotleftplayer\" style=\"color: " + teamColourToHTML(entry.tc1) + ";\">" + teamIndicatorHTML + "</span>";
        }
        html += "</span>";

        html += "<span class=\"videprinterscore" + supersededClass + "\">";
        if (entry.s1 == null || entry.s2 == null) {
            html += " - ";
        }
        else if (entry.s1 == 0 && entry.s2 == 0 && entry.tb) {
            html += "&#10006; - &#10006;";
        }
        else {
            html += " ";
            html += entry.s1.toString();
            if (entry.tb && entry.s1 > entry.s2)
                html += "*";
            html += " - ";
            html += entry.s2.toString();
            if (entry.tb && entry.s2 >= entry.s1)
                html += "*";
            html += " ";
        }
        html += "</span>";
        html += "<span class=\"videprinterplayer" + supersededClass + "\">";
        if (entry.tc2 != null) {
            html += "<span class=\"teamdotrightplayer\" style=\"color: " + teamColourToHTML(entry.tc2) + ";\">" + teamIndicatorHTML + "</span>";
        }
        html += escapeHTML(entry.p2);
        html += "</span>";

        return html;
    }

    refresh(timeNow, enableAnimation) {
        if (this.latestGameRevisionSeen == null || gameStateRevision != this.latestGameRevisionSeen) {
            this.redraw();
        }
        return false;
    }

    redraw() {
        this.latestGameRevisionSeen = gameStateRevision;
        var gameState = this.getGameState();
        var logs_reply = null;
        var log_entries = [];
        var maxLogSeq = null;

        if (gameState.success) {
            logs_reply = gameState.logs;
            var start = logs_reply.logs.length - this.numRows;
            if (start < 0) {
                start = 0;
            }
            for (var i = start; i < logs_reply.logs.length; ++i) {
                log_entries.push(logs_reply.logs[i]);
                if (maxLogSeq == null || logs_reply.logs[i].seq > maxLogSeq)
                    maxLogSeq = logs_reply.logs[i].seq;
            }
        }

        for (var row = 0; row < this.numRows; ++row) {
            var entry_preamble = "&nbsp;";
            var entry_main = "&nbsp;";
            var animate_entry = false;
            if (row < log_entries.length) {
                entry_preamble = this.format_videprinter_preamble(log_entries[row]);
                if (this.latestLogSeqShown != null && log_entries[row].seq > this.latestLogSeqShown) {
                    animate_entry = true;
                }
                entry_main = this.format_videprinter_entry(log_entries[row]);
            }

            var main_td = document.getElementById("videprinterrow" + row.toString() + "_main");

            /* If this is a new entry and so we're animating it, put it inside
             * an animation div */
            if (animate_entry) {
                main_td.innerHTML = "<div class=\"videprinteranimatescoreline\">" + entry_preamble + " " + entry_main + "</div>";
            }
            else {
                main_td.innerHTML = entry_preamble + " " + entry_main;
            }
        }
        if (this.latestLogSeqShown == null || (maxLogSeq != null && maxLogSeq > this.latestLogSeqShown)) {
            this.latestLogSeqShown = maxLogSeq;
        }
    }
}

class TableNumberIndexView extends PagedTableView {
    constructor (tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerColumn, colsPerPage, scrollPeriod) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerColumn, scrollPeriod);
        this.rowsPerColumn = rowsPerColumn;
        this.colsPerPage = colsPerPage;
        this.latestGameRevisionSeen = null;
    }

    setup(container) {
        super.setup(container);
        var html = "";

        html += "<div class=\"headingbar tabindexheading\">";
        html += "<div class=\"tabindexheadingtext\">";
        html += "Table numbers";
        html += "</div>";
        html += "</div>";

        html += "<div class=\"tabindexerror\" id=\"tabindexerror\"></div>";

        html += "<div class=\"tabindexbigtable\">";

        var colWidthPc;
        var colSpaceWidthPc;

        colWidthPc = 80.0 / this.colsPerPage;
        colSpaceWidthPc = 12.0 / this.colsPerPage;

        for (var col = 0; col < this.colsPerPage; ++col) {
            if (col > 0) {
                html += "<div class=\"tabindexcolumnspace\" " +
                    "style=\"width: " + colSpaceWidthPc.toString() + "vw;\">&nbsp;</div>";
            }
            html += "<div class=\"tabindexcolumn\" " +
                "style=\"max-width: " + colWidthPc.toString() + "vw;\">";

            html += "<table class=\"tabindextable\">";
            for (var row = 0; row < this.rowsPerColumn; ++row) {
                var entryNo = col * this.rowsPerColumn + row;
                html += "<tr>";
                html += "<td class=\"tabindexname\" id=\"tabindexname" + entryNo.toString() + "\"></td>";
                html += "<td class=\"tabindexnumber\" id=\"tabindexnumber" + entryNo.toString() + "\"></td>";
                html += "</tr>";
            }
            html += "</table>";

            html += "</div>";
        }

        html += "</div>"


        container.innerHTML = html;
    }

    getPageInfo() {
        this.lastGameRevisionSeen = gameStateRevision;
        var gameState = this.getGameState();
        var pages = [];
        var page = [];

        if (gameState.success) {
            var divisions = gameState.structure.divisions;
            var selectedRoundsPerDiv = this.findSelectedRoundsPerDivision(gameState.games, -3);
            var namesToTables = {};
            var games = gameState.games;

            for (var divIndex = 0; divIndex < games.divisions.length; ++divIndex) {
                var selectedRounds = selectedRoundsPerDiv[divIndex];
                var selectedRound = null;
                if (selectedRounds)
                    selectedRound = selectedRounds[0];

                var divGames = games.divisions[divIndex].games;
                for (var gameIndex = 0; gameIndex < divGames.length; ++gameIndex) {
                    var game = divGames[gameIndex];
                    if (game.round != selectedRound)
                        continue;

                    var playerNames = [ game.name1, game.name2 ];
                    for (var i = 0; i < playerNames.length; ++i) {
                        /* Find the list of tables this player is playing
                         * on in this round */
                        var name = playerNames[i];
                        var tableList;
                        if (name in namesToTables) {
                            tableList = namesToTables[name];
                        }
                        else {
                            tableList = [];
                        }

                        /* If the table number for this game isn't in the
                         * list, add it */
                        var found = false;
                        for (var j = 0; j < tableList.length; ++j) {
                            if (tableList[j] == game.table) {
                                found = true;
                                break;
                            }
                        }
                        if (!found) {
                            tableList.push(game.table);
                        }
                        namesToTables[name] = tableList;
                    }
                }
            }

            /* Now sort the names alphabetically */
            var nameList = [];
            for (var name in namesToTables) {
                nameList.push(name);
            }
            nameList.sort();

            for (var nameIndex = 0; nameIndex < nameList.length; ++nameIndex) {
                var name = nameList[nameIndex];
                var tableList = namesToTables[name];
                if (page.length >= this.rowsPerColumn * this.colsPerPage) {
                    pages.push(page);
                    page = [];
                }
                page.push( { "name" : name, "tables" : tableList } );
            }

            if (page.length > 0) {
                pages.push(page);
                page = [];
            }
        }
        else {
            pages = [ [ { "errorString" : gameState.description } ] ];
        }

        if (this.currentPageIndex >= pages.length)
            this.currentPageIndex = 0;
        if (this.currentPageIndex >= pages.length)
            return [];
        else
            return pages[this.currentPageIndex];
    }

    removeCell(cellNumber) {
        var cellName = "tabindexname" + cellNumber.toString();
        document.getElementById(cellName).style.visibility = "hidden";
        cellName = "tabindexnumber" + cellNumber.toString();
        document.getElementById(cellName).style.visibility = "hidden";
    }

    clearRow(rowNum) {
        for (var col = 0; col < this.colsPerPage; ++col) {
            var cellNum = rowNum + col * this.rowsPerColumn;
            var cellName = "tabindexname" + cellNum.toString();
            var nameElement = document.getElementById(cellName);
            cellName = "tabindexnumber" + cellNum.toString();
            var numberElement = document.getElementById(cellName);

            nameElement.innerHTML = "&nbsp;";
            numberElement.innerHTML = "&nbsp;";
            nameElement.style.visibility = null;
            numberElement.style.visibility = null;
        }
    }

    pageInfoIsSuccessful(page) {
        return page != null && (page.length == 0 ||
                !("errorString" in page[0]));
    }

    redrawHeadings(page) {
    }

    redrawError(page) {
        var element = document.getElementById("tabindexerror");
        element.innerText = page[0].errorString;
    }

    redrawRow(page, tableRow) {
        if (page != null) {
            for (var col = 0; col < this.colsPerPage; ++col) {
                var cellNumber = tableRow + col * this.rowsPerColumn;
                if (cellNumber < page.length) {
                    this.setCell(cellNumber, page[cellNumber]);
                }
                else {
                    this.removeCell(cellNumber);
                }
            }
        }
    }

    setCell(cellNumber, entry) {
        var nameElement = document.getElementById("tabindexname" + cellNumber.toString());
        var numberElement = document.getElementById("tabindexnumber" + cellNumber.toString());
        if (nameElement == null || numberElement == null)
            return;

        var tableListString = "";
        for (var i = 0; i < entry.tables.length; ++i) {
            if (i > 0)
                tableListString += ",";
            tableListString += entry.tables[i].toString();
        }

        nameElement.innerText = entry.name;
        numberElement.innerText = tableListString;
        nameElement.style.visibility = null;
        numberElement.style.visibility = null;
    }
}

class PlaceholderView extends View {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
    }

    setup(container) {
        var child = document.createElement("div");
        child.classList.add("placeholder");
        child.innerText = "Ignore this. It's just a figment of your imagination.";
        container.appendChild(child);
    }

    refresh(timeNow, enableAnimation) {
        return false;
    }
}

class ImageView extends View {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc, imageUrl) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
        this.imageUrl = imageUrl;
    }

    setup(container) {
        var html = "<div class=\"imageviewcontainer\">";
        //html += "<img src=\"/images/test_card_f.png\" class=\"failimage\" />";
        html += "<img src=\"" + escapeHTML(this.imageUrl) + "\" class=\"imageviewimage\" />";
        html += "</div>";
        container.innerHTML = html;
    }

    refresh(timeNow, enableAnimation) {
        return false;
    }
}

class TuffLuckView extends View {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
        this.numRows = 10;
        this.lastGameStateRevisionSeen = null;
        this.lastUpdate = null;
    }

    setup(container) {
        super.setup(container);
        container.style.maxWidth = "100%";
        var html = "";
        html += "<div class=\"headingbar tabindexheading\">";
        html += "<div class=\"tabindexheadingtext\">";
        html += "Tuff Luck";
        html += "</div>";
        html += "</div>";

        html += "<table class=\"teleostmaintable\">";
        html += "<colgroup>";
        html += "<col class=\"teleosttuffluckcolpos teleostnumber\" />";
        html += "<col class=\"teleosttuffluckcolname\" />";
        html += "<col class=\"teleosttuffluckcoltuffness teleostnumber\" />";
        html += "</colgroup>";
        html += "<tr class=\"headingbar teleoststableheadingrow\">";
        html += "<th class=\"teleosttableheadingnumber\"></th>";
        html += "<th class=\"teleosttableheadingstring\"></th>";
        html += "<th class=\"teleosttableheadingnumber\">Tuffness</th>";
        html += "</tr>";

        for (var row = 0; row < this.numRows; ++row) {
            var rowName = "teleosttuffluck" + row.toString();
            html += "<tr id=\"" + rowName + "\">";
            html += "<td class=\"teleosttablecellpos teleostnumber\" id=\"" + rowName + "_pos\">&nbsp;</td>";
            html += "<td class=\"teleosttablecellname\" id=\"" + rowName + "_name\">&nbsp;</td>";
            html += "<td class=\"teleosttablecelltuffness teleostnumber\" id=\"" + rowName + "_tuffness\">&nbsp;</td>";
            html += "</tr>"
        }
        html += "</table>";
        container.innerHTML = html;
    }

    setRowDisplay(rowNum, value) {
        var rowName = "teleosttuffluck" + rowNum.toString();
        document.getElementById(rowName).style.display = value;
    }

    removeRow(rowNum) {
        this.setRowDisplay(rowNum, "none");
    }

    showRow(rowNum) {
        this.setRowDisplay(rowNum, null);
    }

    refresh(timeNow, enableAnimation) {
        if (this.lastGameStateRevisionSeen != null && this.lastGameStateRevisionSeen == gameStateRevision)
            return false;

        if (this.lastUpdate != null && this.lastUpdate + this.refreshPeriod > timeNow)
            return false;

        this.lastUpdate = timeNow;
        this.lastGameStateRevisionSeen = gameStateRevision;

        if (gameState != null && gameState.success && gameState.tuffluck) {
            var tuffluck = gameState.tuffluck;
            var table = tuffluck.table;
            for (var idx = 0; idx < this.numRows; ++idx) {
                var pos = "";
                var name = "";
                var tuffness = "";
                var rowName = "teleosttuffluck" + idx.toString();

                if (idx >= table.length) {
                    this.removeRow(idx);
                }
                else {
                    var entry = table[idx];

                    pos = entry.pos.toString();
                    name = entry.name;
                    tuffness = entry.tuffness.toString();

                    this.showRow(idx);
                }
                
                document.getElementById(rowName + "_pos").innerText = pos;
                document.getElementById(rowName + "_name").innerText = name;
                document.getElementById(rowName + "_tuffness").innerText = tuffness;
            }
        }

        return false;
    }

    refreshFrame(timeNow) {
        return false;
    }
}

class OverachieversView extends PagedTableView {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc, 10, 10000);
        this.numRows = 10;
        this.lastGameRevisionSeen = null;
    }

    setup(container) {
        super.setup(container);
        container.style.maxWidth = "100%";
        var html = "";
        html += "<div class=\"headingbar tabindexheading\">";
        html += "<div class=\"tabindexheadingtext\">";
        html += "Overachievers";
        html += "</div>";
        html += "</div>";

        html += "<table class=\"teleostmaintable\">";
        html += "<colgroup>";
        html += "<col class=\"teleostoverachieverscolpos teleostnumber\" />";
        html += "<col class=\"teleostoverachieverscolname\" />";
        html += "<col class=\"teleostoverachieverscolseed teleostnumber\" />";
        html += "<col class=\"teleostoverachieverscolrank teleostnumber\" />";
        html += "<col class=\"teleostoverachieverscoldiff teleostnumber\" />";
        html += "</colgroup>";
        html += "<tr class=\"headingbar teleoststableheadingrow\">";
        html += "<th class=\"teleosttableheadingnumber\"></th>";
        html += "<th class=\"teleosttableheadingstring\" id=\"teleostoverachieversdivision\"></th>";
        html += "<th class=\"teleosttableheadingnumber\">Seed</th>";
        html += "<th class=\"teleosttableheadingnumber\">Pos</th>";
        html += "<th class=\"teleosttableheadingnumber\">+/-</th>";
        html += "</tr>";

        for (var row = 0; row < this.numRows; ++row) {
            var rowName = "teleostoverachievers" + row.toString();
            html += "<tr id=\"" + rowName + "\">";
            html += "<td class=\"teleosttablecellpos teleostnumber\" id=\"" + rowName + "_pos\">&nbsp;</td>";
            html += "<td class=\"teleosttablecellname\" id=\"" + rowName + "_name\">&nbsp;</td>";
            html += "<td class=\"teleosttablecellnumber teleostnumber\" id=\"" + rowName + "_seed\">&nbsp;</td>";
            html += "<td class=\"teleosttablecellnumber teleostnumber\" id=\"" + rowName + "_rank\">&nbsp;</td>";
            html += "<td class=\"teleosttablecellnumber teleostnumber\" id=\"" + rowName + "_diff\">&nbsp;</td>";
            html += "</tr>"
        }
        html += "</table>";
        container.innerHTML = html;
    }

    setRowDisplay(rowNum, value) {
        var rowName = "teleostoverachievers" + rowNum.toString();
        document.getElementById(rowName).style.display = value;
    }

    removeRow(rowNum) {
        this.setRowDisplay(rowNum, "none");
    }

    showRow(rowNum) {
        this.setRowDisplay(rowNum, null);
    }

    getPageInfo() {
        this.lastGameRevisionSeen = gameStateRevision;
        var gameState = this.getGameState();
        var pages = [];
        var page = [];

        if (gameState.success) {
            var divisions = gameState.overachievers.divisions;
            for (var div_index = 0; div_index < divisions.length; ++div_index) {
                var division = divisions[div_index];

                /* Take the first numRows of each division's overachievers
                 * table, and put each division's table on a different page.
                 * This means we have one page per division, and we only show
                 * the first numRows entries of each division. */
                for (var idx = 0; idx < division.table.length && idx < this.numRows; ++idx) {
                    page.push(division.table[idx])
                }
                pages.push({
                    "success" : true,
                    "div_name" : (divisions.length > 1 ? division.div_name : ""),
                    "table" : page
                });
                page = []
            }
        }
        else {
            pages = [ { "success" : false, "error" : gameState.description } ]
        }

        if (this.currentPageIndex >= pages.length)
            this.currentPageIndex = 0;
        if (this.currentPageIndex >= pages.length)
            return [];
        else
            return pages[this.currentPageIndex];
    }

    pageInfoIsSuccessful(page) {
        if (page == null) {
            return false;
        }
        else if (("success" in page) && !page.success) {
            return false;
        }
        else {
            return true;
        }
    }

    redrawHeadings(page) {
        var divName = page.div_name;
        document.getElementById("teleostoverachieversdivision").innerText = divName;
    }

    redrawError(page) {
        document.getElementById("teleostoverachieversdivision").innerText = page.error;
    }

    clearRow(rowNum) {
        var rowName = "teleostoverachievers" + rowNum.toString();
        var suffixes = [ "pos", "name", "rank", "seed", "diff" ];
        for (var i = 0; i < suffixes.length; ++i) {
            var elementName = rowName + "_" + suffixes[i];
            document.getElementById(elementName).innerHTML = "&nbsp;";
        }
    }

    redrawRow(page, rowNum) {
        if (page != null) {
            if (rowNum >= page.table.length) {
                while (rowNum < this.numRows) {
                    this.removeRow(rowNum);
                    rowNum++;
                }
            }
            else {
                var entry = page.table[rowNum];
                var pos = "";
                var name = "";
                var seed = "";
                var rank = "";
                var diff = ""

                var rowName = "teleostoverachievers" + rowNum.toString();

                pos = entry.pos.toString();
                name = entry.name;
                seed = entry.seed.toString();
                rank = entry.rank.toString();
                if (entry.diff > 0)
                    diff = "+" + entry.diff.toString();
                else
                    diff = entry.diff.toString()
     
                document.getElementById(rowName + "_pos").innerText = pos;
                document.getElementById(rowName + "_name").innerText = name;
                document.getElementById(rowName + "_seed").innerText = seed;
                document.getElementById(rowName + "_rank").innerText = rank;
                document.getElementById(rowName + "_diff").innerText = diff;

                this.showRow(rowNum);
            }
        }
    }
}

class MultipleView extends View {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc, views) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
        this.views = views;
        this.animatingViews = [];
        for (var i = 0; i < views.length; ++i) {
            this.animatingViews.push(false);
        }
    }

    setup(container) {
        for (var i = 0; i < this.views.length; ++i) {
            var child = document.createElement("div");
            container.appendChild(child);
            this.views[i].setup(child);
        }
    }

    refresh(timeNow, enableAnimation) {
        var anyTrue = false;
        /* If any of the views want to do an animation, record which views
         * want to do that, and we'll call refreshFrame on them */
        for (var i = 0; i < this.views.length; ++i) {
            var animate = this.views[i].refresh(timeNow, enableAnimation);
            if (!enableAnimation)
                animate = false;
            this.animatingViews[i] = animate;
            if (animate)
                anyTrue = true;
        }
        return anyTrue;
    }

    refreshFrame(timeNow) {
        /* Keep returning true until all our views return false from
         * their refreshFrame() method */
        var anyTrue = false;
        for (var i = 0; i < this.views.length; ++i) {
            if (this.animatingViews[i]) {
                this.animatingViews[i] = this.views[i].refreshFrame(timeNow);
            }
            if (this.animatingViews[i])
                anyTrue = true;
        }
        return anyTrue;
    }
}

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
