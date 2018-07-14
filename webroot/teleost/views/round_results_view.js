class RoundResultsView extends PagedTableView {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage < 2 ? 2 : rowsPerPage, scrollPeriod);
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
        var gameState = this.getGameState();
        var pages = [];
        var page = [];
        var divisionToCurrentRound = {};
        var divisionToMaxGamesPerTable = {};
        var roundToName = {};

        if (gameState.success) {
            var games = gameState.games;
            var divisions = games.divisions;

            for (var idx = 0; idx < gameState.structure.rounds.length; ++idx) {
                var r = gameState.structure.rounds[idx];
                roundToName[r.num] = r.name;
            }

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
                var currentRound = divisionToCurrentRound[divIndex];
                var maxGamesPerTable = divisions[divIndex].max_games_per_table_per_round[currentRound];
                var divGames = divisions[divIndex].games;
                for (var gameIndex = 0; gameIndex < divGames.length; ++gameIndex) {
                    var game = divGames[gameIndex];

                    if (game.round != currentRound)
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
                                     "roundName" : (roundToName[game.round]),
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
