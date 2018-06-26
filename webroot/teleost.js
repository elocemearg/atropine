var game_state = null;
var game_state_revision = 0;

var game_state_fetch_request = null;

function fetch_game_state_callback() {
    var req = game_state_fetch_request;
    if (req.readyState == 4) {
        if (req.status == 200 && req.responseText != null) {
            game_state = JSON.parse(req.responseText);
            game_state_revision++;
            game_state_fetch_request = null;
        }
        else {
            game_state = { "success" : false, "description" : req.statusText };
            game_state_revision++;
            game_state_fetch_request = null;
        }
        if (!currentViewDrawn)
            update_current_view();
    }
}

function fetch_game_state_error(req) {
    game_state = { "success" : false, "description" : req.statusText };
    game_state_revision++;
    game_state_fetch_request = null;
}

function fetch_game_state() {
    if (game_state_fetch_request != null) {
        /* Previous request is still running */
        return;
    }

    game_state_fetch_request = new XMLHttpRequest();

    game_state_fetch_request.open("GET",
            "/cgi-bin/jsonreq.py?tourney=" + encodeURIComponent(tourney_name) +
            "&request=all", true);
    game_state_fetch_request.onreadystatechange = fetch_game_state_callback;
    game_state_fetch_request.onerror = fetch_game_state_error;
    game_state_fetch_request.send(null);
}


function escapeHTML(str) {
    return str.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#039;");
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

class View {
    constructor (tourney_name, leftPc, topPc, widthPc, heightPc) {
        this.tourney_name = tourney_name;
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
     * the global game_state variable.
     * Return true if the refresh operation needs to be animated. In that
     * case refreshFrame() will be called after every frame_ms milliseconds
     * until refreshFrame() returns false.
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

    get_game_state() {
        if (game_state == null) {
            return { "success" : false, "description" : "Please wait..." };
        }
        return game_state;
    }
}

class StandingsView extends View {
    constructor (tourney_name, leftPc, topPc, widthPc, heightPc, scrollPeriod) {
        super(tourney_name, leftPc, topPc, widthPc, heightPc);
        this.rowsPerPage = 8;
        this.currentPageIndex = 0;
        this.lastScroll = 0;
        this.newDisplay = null;
        this.scrollPeriod = scrollPeriod;
        this.lastGameRevisionSeen = null;
    }

    setup(container) {
        super.setup(container);
        container.style.maxWidth = "100%";
        var html = "<div class=\"teleoststandingsdivisionname\" id=\"teleoststandingsdivisionname\"></div>";
        html += "<table class=\"teleoststandings\">";
        html += "<colgroup>";
        html += "<col class=\"teleoststandingscolpos teleostnumber\" />";
        html += "<col class=\"teleoststandingscolname\" />";
        html += "<col class=\"teleoststandingscolplayed teleostnumber\" />";
        html += "<col class=\"teleoststandingscolwins teleostnumber\" />";
        html += "<col class=\"teleoststandingscolpoints teleostnumber\" />";
        html += "</colgroup>";
        html += "<tr>";
        html += "<th></th>";
        html += "<th></th>";
        html += "<th>P</th>";
        html += "<th>W</th>";
        html += "<th id=\"teleoststandingspointsheading\">Pts</th>";
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

    nextPage() {
        this.currentPageIndex += 1;
    }

    refresh(timeNow, enableAnimation) {
        var doRedraw = (this.lastGameRevisionSeen == null || this.lastGameRevisionSeen != game_state_revision);
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
            this.newDisplay = this.getPageInfo();

            /* Don't do the scrolly effect if we're scrolling from one
             * page to the same page, e.g. if there's only one page. */
            if (oldPageIndex == this.currentPageIndex)
                doScroll = false;
        }

        if (enableAnimation) {
            if (doScroll) {
                this.animateFrameNumber = 0;
                this.animateNumRowsCleared = 0;
                this.animateNumRowsFilled = 0;
                return true;
            }
        }
        if (doRedraw)
            this.redraw(this.newDisplay);
        return false;
    }

    refreshFrame(timeNow) {
        /* Fill in a row this many frames after it was cleared */
        var replaceRowDelay = 5;

        if (this.animateNumRowsCleared < this.rowsPerPage) {
            this.clearRow(this.animateNumRowsCleared);
            this.animateNumRowsCleared++;
        }

        if (this.animateFrameNumber >= replaceRowDelay || this.animateFrameNumber >= this.rowsPerPage) {
            if (this.animateNumRowsFilled == 0)
                this.redrawHeadings(this.newDisplay);
            this.redrawRow(this.newDisplay, this.animateNumRowsFilled);
            this.animateNumRowsFilled++;
        }
        this.animateFrameNumber++;

        return (this.animateNumRowsFilled < this.rowsPerPage);
    }

    getPageInfo() {
        this.lastGameRevisionSeen = game_state_revision;
        var game_state = this.get_game_state();
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

        if (game_state.success) {
            standings = game_state.standings;
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
        }
        else {
            errorString = game_state.description;
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

    redrawHeadings(standingsObject) {
        var pointsHeading = document.getElementById("teleoststandingspointsheading");
        if (standingsObject.useSpread) {
            pointsHeading.innerText = "Spr";
        }
        else {
            pointsHeading.innerText = "Pts";
        }

        var divisionNameElement = document.getElementById("teleoststandingsdivisionname");
        divisionNameElement.innerText = standingsObject.divisionName;
        if (standingsObject.showDivisionName) {
            divisionNameElement.style.display = null;
        }
        else {
            divisionNameElement.style.display = "none";
        }
    }

    redrawRow(standingsObject, tableRow) {
        var page = standingsObject.standingsPage;
        var success = (standingsObject.errorString == null);

        if (success && page != null) {
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
        else {
            this.clearRow(tableRow);
            document.getElementById("standingsrow0_name").innerText = standingsObject.errorString;
        }
    }

    redraw(standingsObject) {
        this.redrawHeadings(standingsObject);

        for (var tableRow = 0; tableRow < this.rowsPerPage; ++tableRow) {
            this.redrawRow(standingsObject, tableRow);
        }
    }
}

class VideprinterView extends View {
    constructor (tourney_name, leftPc, topPc, widthPc, heightPc, numRows) {
        super(tourney_name, leftPc, topPc, widthPc, heightPc);
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
            html += "<td class=\"teleostvideprinterpreamble\" id=\"videprinterrow" + row.toString() + "_preamble\">-</td>";
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
        html += "</span>";

        html += "<span class=\"videprinterscore" + supersededClass + "\">";
        if (entry.s1 == null || entry.s2 == null) {
            html += " - ";
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
        html += escapeHTML(entry.p2);
        html += "</span>";

        return html;
    }

    refresh(timeNow, enableAnimation) {
        if (this.latestGameRevisionSeen == null || game_state_revision != this.latestGameRevisionSeen) {
            this.redraw();
        }
        return false;
    }

    redraw() {
        this.latestGameRevisionSeen = game_state_revision;
        var game_state = this.get_game_state();
        var logs_reply = null;
        var log_entries = [];
        var maxLogSeq = null;

        if (game_state.success) {
            logs_reply = game_state.logs;
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
            var entry_preamble = "";
            var entry_main = "";
            var animate_entry = false;
            if (row < log_entries.length) {
                entry_preamble = this.format_videprinter_preamble(log_entries[row]);
                if (this.latestLogSeqShown != null && log_entries[row].seq > this.latestLogSeqShown) {
                    animate_entry = true;
                }
                entry_main = this.format_videprinter_entry(log_entries[row]);
            }

            var preamble_td = document.getElementById("videprinterrow" + row.toString() + "_preamble")
            var main_td = document.getElementById("videprinterrow" + row.toString() + "_main");

            /* If this is a new entry and so we're animating it, put it inside
             * an animation div */
            if (animate_entry) {
                preamble_td.innerHTML = "<div class=\"videprinteranimatepreamble\">" + entry_preamble + "</div>";
                main_td.innerHTML = "<div class=\"videprinteranimatescoreline\">" + entry_main + "</div>";
            }
            else {
                preamble_td.innerHTML = entry_preamble;
                main_td.innerHTML = entry_main;
            }
        }
        if (this.latestLogSeqShown == null || (maxLogSeq != null && maxLogSeq > this.latestLogSeqShown)) {
            this.latestLogSeqShown = maxLogSeq;
        }
    }
}

class MultipleView extends View {
    constructor(tourney_name, leftPc, topPc, widthPc, heightPc, views) {
        super(tourney_name, leftPc, topPc, widthPc, heightPc);
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

function create_standings_and_videprinter(tourney_name) {
    return new MultipleView(tourney_name, 0, 0, 100, 100, [
        new StandingsView(tourney_name, 0, 0, 100, 70, 6000),
        new VideprinterView(tourney_name, 0, 70, 100, 30, 4)
    ]);
}
