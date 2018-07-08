class FixturesView extends PagedTableView {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod, whichDivision, whichRound) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod);

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
        var gameState = this.getGameState();

        // games, partitioned into division&round, then table number
        var gamesGroups = [];

        var pages = [];
        var page = [];
        var errorString = null;
        var teamScores = null;

        if (gameState.success) {
            var selectedDivisions = findSelectedDivisions(gameState.games, this.whichDivision);
            var selectedRoundsPerDivision = findSelectedRoundsPerDivision(gameState.games, this.whichRound);

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

