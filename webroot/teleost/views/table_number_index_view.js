class TableNumberIndexView extends PagedTableView {
    constructor (tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerColumn, colsPerPage, scrollPeriod) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerColumn, scrollPeriod);
        this.rowsPerColumn = rowsPerColumn;
        this.colsPerPage = colsPerPage;
    }

    setup(container) {
        super.setup(container);
        var html = "";

        html += "<div class=\"headingbar viewheading\">";
        html += "<div class=\"viewheadingtext\" id=\"tablenumberindexheading\">";
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
                html += "<td class=\"tabindexname" + (this.colsPerPage >= 3 ? " condensedtext" : "") + "\" id=\"tabindexname" + entryNo.toString() + "\"></td>";
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
        var gameState = this.getGameState();
        var pages = [];
        var page = [];

        if (gameState.success) {
            var divisions = gameState.structure.divisions;
            var selectedRoundsPerDiv = findSelectedRoundsPerDivision(gameState.games, -3);
            var namesToTables = {};
            var games = gameState.games;
            var selectedRound = 0;
            var roundName = null;

            /* If the divisions don't all want to display the same round, show
             * the table numbers for the latest round. */
            for (var divIndex = 0; divIndex < games.divisions.length; ++divIndex) {
                var roundList = selectedRoundsPerDiv[divIndex];
                for (var i = 0; i < roundList.length; ++i) {
                    if (roundList[i] > selectedRound) {
                        selectedRound = roundList[i];
                    }
                }
            }

            if (gameState.structure.rounds) {
                for (var roundIndex = 0; roundIndex < gameState.structure.rounds.length; ++roundIndex) {
                    if (gameState.structure.rounds[roundIndex].num == selectedRound) {
                        roundName = gameState.structure.rounds[roundIndex].name;
                        if (gameState.structure.rounds[roundIndex].name) {
                            roundName = gameState.structure.rounds[roundIndex].name;
                        }
                    }
                }
            }

            for (var divIndex = 0; divIndex < games.divisions.length; ++divIndex) {
                var divGames = games.divisions[divIndex].games;
                for (var gameIndex = 0; gameIndex < divGames.length; ++gameIndex) {
                    var game = divGames[gameIndex];
                    if (game.round != selectedRound)
                        continue;

                    var playerNames = [ game.name1, game.name2 ];
                    var playersArePrunes = [ game.prune1, game.prune2 ];
                    for (var i = 0; i < playerNames.length; ++i) {
                        if (playersArePrunes[i]) {
                            continue;
                        }
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
                page.push( { "name" : name, "tables" : tableList, "roundname" : roundName } );
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
        if (page != null && page.length != 0 && "roundname" in page[0]) {
            var roundName = page[0].roundname;
            var element = document.getElementById("tablenumberindexheading");
            if (element) {
                if (roundName) {
                    element.innerText = roundName + " - Table Numbers";
                }
                else {
                    element.innerText = "Table Numbers";
                }
            }
        }
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
