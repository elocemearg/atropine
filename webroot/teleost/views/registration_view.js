
class CheckInView extends PagedTableView {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerColumn, scrollPeriod) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerColumn, scrollPeriod);
        this.lastGameStateRevisionSeen = null;
        this.lastUpdate = null;
        this.background = null;
        this.heading1 = null;
        this.heading2 = null;
        this.playersHeadingText = null;
        this.playerListContainer = null;
        this.playersCount = null;
        this.playersPageNumber = null;
        this.playerNameCells = [];
        this.rowsPerColumn = rowsPerColumn;
        this.columnsPerPage = 4;
    }

    setup(container) {
        super.setup(container);
        container.style.maxWidth = "100%";
        container.innerHTML = "";

        /* Screen for when there are players. First we have a heading at
         * the top welcoming everyone to the event... */
        this.playersHeadingText = document.createElement("DIV");
        this.playersHeadingText.className = "viewheadingtext";
        this.playersHeadingText.innerText = "Welcome";
        let playersHeadingBar = document.createElement("DIV");
        playersHeadingBar.classList.add("headingbar");
        playersHeadingBar.classList.add("viewheading");
        playersHeadingBar.classList.add("condensedtext");
        playersHeadingBar.appendChild(this.playersHeadingText);
        container.appendChild(playersHeadingBar);

        /* Now put some text below it, reminding people that if they're not
         * on this list then they won't get to play... */
        let playersBlurb = document.createElement("DIV");
        playersBlurb.className = "checkinblurb";
        playersBlurb.innerHTML = "The host has registered the following players so far.<br>" +
            "If your name isn't here and you intend to play, please tell the host.";
        container.appendChild(playersBlurb);

        /* Player count */
        this.playersCount = document.createElement("DIV");
        this.playersCount.id = "checkincount";
        this.playersCount.innerHTML = "";
        container.appendChild(this.playersCount);

        /* Page number */
        this.playersPageNumber = document.createElement("DIV");
        this.playersPageNumber.id = "checkinpagenumber";
        this.playersPageNumber.className = "viewpagenumber";
        this.playersPageNumber.innerHTML = "";
        container.appendChild(this.playersPageNumber);

        /* Create a container for the table of players... */
        this.playerListContainer = document.createElement("DIV");
        this.playerListContainer.className = "checkinlist";
        container.appendChild(this.playerListContainer);

        /* Build the table of cells, in which we will display player names.
         * There is a fixed number of cells. If there are more players than
         * cells, we will display the list across two or more pages. */
        this.createPlayerTable(this.playerListContainer, this.rowsPerColumn, this.columnsPerPage);
    }

    getNumPages(numPlayers, numRows, numColumns) {
        let cellsPerPage = numRows * numColumns;
        return Math.floor((numPlayers + cellsPerPage - 1) / cellsPerPage);
    }

    getNumCellsOnLastPage(numPlayers, numRows, numColumns) {
        let mod = numPlayers % (numRows * numColumns);
        if (mod == 0)
            return numRows * numColumns;
        else
            return mod;
    }

    getOptimalColumnCount(numPlayers, numRows, squareScreen) {
        let columnCountOptions = [3, 4];
        let bestColumnCounts = [];
        let bestValue = null;

        if (squareScreen) {
            /* If we don't have a wide screen, never use four columns. */
            return 3;
        }

        /* Choose the column count which gives us the fewest number of pages. */
        for (let i = 0; i < columnCountOptions.length; ++i) {
            let value = this.getNumPages(numPlayers, numRows, columnCountOptions[i]);
            if (bestColumnCounts.length == 0 || value <= bestValue) {
                if (bestValue != null && value < bestValue) {
                    bestColumnCounts = [];
                }
                bestColumnCounts.push(columnCountOptions[i]);
                bestValue = value;
            }
        }

        if (bestColumnCounts.length > 1) {
            /* If there's a tie for number of pages, choose the column count
             * which gives us the most cells on the last page. */
            columnCountOptions = bestColumnCounts;
            bestColumnCounts = [];
            bestValue = null;
            for (let i = 0; i < columnCountOptions.length; ++i) {
                let value = this.getNumCellsOnLastPage(numPlayers, numRows, columnCountOptions[i]);
                if (bestColumnCounts.length == 0 || value >= bestValue) {
                    if (bestValue != null && value > bestValue) {
                        bestColumnCounts = [];
                    }
                    bestColumnCounts.push(columnCountOptions[i]);
                    bestValue = value;
                }
            }

            if (bestColumnCounts.length > 1) {
                /* If there's still a tie, pick the smaller number of columns.
                 * If we've got less than one pageworth of names either way, we
                 * might as well make the columns large. */
                bestColumnCounts = [ Math.min(...bestColumnCounts) ];
            }
        }

        if (bestColumnCounts.length == 0) {
            /* What? */
            return 4;
        }
        else {
            return bestColumnCounts[0];
        }
    }

    createPlayerTable(container, rows, columns) {
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
        let table = document.createElement("TABLE");
        table.classList.add("checkintable");
        table.classList.add("condensedtext");
        this.playerNameCells = [];
        for (let r = 0; r < rows; r++) {
            let tr = document.createElement("TR");
            for (let c = 0; c < columns; c++) {
                /* Cells are numbered so that we go down each column first
                 * before moving on to the next column. */
                let td = document.createElement("TD");
                td.id = "checkincell" + (c * rows + r).toString();
                this.playerNameCells[c * rows + r] = td;
                tr.appendChild(td);
                td.innerText = "&nbsp;";
                td.style.visibility = "hidden";
                if (c < columns - 1) {
                    let space = document.createElement("TD");
                    space.className = "checkincolumnspace";
                    tr.appendChild(space);
                }
            }
            table.appendChild(tr);
        }
        container.appendChild(table);
    }

    getActivePlayers(gameState) {
        let activePlayers = [];
        if (gameState && gameState.players && gameState.players.players) {
            let players = gameState.players.players;
            for (let i = 0; i < players.length; ++i) {
                if (!players[i].withdrawn && players[i].rating != 0) {
                    activePlayers.push({ "name" : players[i].name, "team_colour" : players[i].team_colour });
                }
            }
        }
        return activePlayers;
    }

    redrawHeadings(page) {
        /* To be called by superclass */
        let gameState = this.getGameState();
        if (gameState != null && gameState.success && gameState.tourney &&
                gameState.tourney.success && gameState.players &&
                gameState.players.success) {
            let tourney = gameState.tourney;
            let players = this.getActivePlayers(gameState);
            let eventName = tourney.full_name;
            if (eventName && eventName != "") {
                this.playersHeadingText.innerText = "Welcome to " + eventName;
            }
            else {
                this.playersHeadingText.innerText = "Welcome";
            }

            this.playersCount.innerText = players.length.toString() + " player" + (players.length == 1 ? "" : "s");
            let cellsPerPage = this.rowsPerColumn * this.columnsPerPage;
            if (players.length > cellsPerPage) {
                let pageNumber = this.currentPageIndex + 1;
                let totalPages = Math.floor((players.length + (cellsPerPage - 1)) / cellsPerPage);
                this.playersPageNumber.innerText = "Page " + pageNumber.toString() + " of " + totalPages.toString();
            }
            else {
                this.playersPageNumber.innerText = "";
            }
        }
    }

    getPageInfo() {
        /* To be called by superclass */
        let gameState = this.getGameState();
        let pages = [];
        if (gameState != null && gameState.success && gameState.players &&
                    gameState.players.success) {
            let activePlayers = this.getActivePlayers(gameState);

            /* Sort the names alphabetically */
            activePlayers.sort(function(a, b) { return a.name < b.name ? -1 : (a.name == b.name ? 0 : 1); });

            /* Does it look like we're using an old 4:3 screen rather than a
             * modern wide screen? If the aspect ratio is closer to 4/3 than
             * to 16/9, assume so. The midpoint of 4/3 and 16/9 is 14/9. */
            const aspectRatio = window.innerWidth / window.innerHeight;
            const squareScreen = (aspectRatio < 14.0 / 9.0);

            /* Set the optimal column count, which may have changed since the
             * last time we redrew the table */
            let bestColCount = this.getOptimalColumnCount(activePlayers.length, this.rowsPerColumn, squareScreen);
            if (bestColCount != this.columnsPerPage) {
                /* Redraw the table with a better number of columns */
                this.columnsPerPage = bestColCount;
                this.createPlayerTable(this.playerListContainer, this.rowsPerColumn, this.columnsPerPage);
            }

            /* Divide the names into pages */
            let page = [];
            let maxInPage = this.rowsPerColumn * this.columnsPerPage;
            for (let i = 0; i < activePlayers.length; i++) {
                if (page.length >= maxInPage) {
                    pages.push(page);
                    page = [];
                }
                page.push(activePlayers[i]);
            }
            if (page.length > 0) {
                pages.push(page);
            }
        }
        else {
            pages.push([ [ { "errorString" : gameState.description } ] ])
        }

        /* Return the relevant page */
        if (this.currentPageIndex >= pages.length) {
            this.currentPageIndex = 0;
        }
        if (this.currentPageIndex >= pages.length) {
            return [];
        }
        else {
            return pages[this.currentPageIndex];
        }
    }

    pageInfoIsSuccessful(page) {
        /* To be called by superclass */
        return page != null && (page.length == 0 || !("errorString" in page[0]));
    }

    redrawRow(page, tableRow) {
        /* To be called by superclass */
        if (page != null) {
            for (var col = 0; col < this.columnsPerPage; ++col) {
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

    removeCell(cellNumber) {
        if (cellNumber >= 0 && cellNumber < this.playerNameCells.length) {
            this.playerNameCells[cellNumber].style.visibility = "hidden";
        }
    }

    setCell(cellNumber, entry) {
        if (cellNumber >= 0 && cellNumber < this.playerNameCells.length) {
            let html = "";
            if (entry.team_colour != null) {
                html += "<span style=\"color: " + teamColourToHTML(entry.team_colour) + ";\">" + teamIndicatorHTML + "</span> ";
            }
            html += escapeHTML(entry.name);
            this.playerNameCells[cellNumber].innerHTML = html;
            this.playerNameCells[cellNumber].style.visibility = null;
        }
    }

    redrawError(page) {
        /* To be called by superclass */
        this.playersHeadingText.innerText = page[0].errorString;
        this.heading1.innerText = page[0].errorString;
    }

    clearRow(rowNum) {
        /* To be called by superclass */
        for (let col = 0; col < this.columnsPerPage; col++) {
            let cellNumber = col * this.rowsPerColumn + rowNum;
            this.playerNameCells[cellNumber].innerHTML = "&nbsp;";
            this.playerNameCells[cellNumber].style.visibility = null;
        }
    }
}
