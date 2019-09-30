class StandingsView extends PagedTableView {
    constructor (tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod, alternateColourRows) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod);
        this.alternateColourRows = alternateColourRows;
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
            var rowClassAttr;
            if (this.alternateColourRows)
                rowClassAttr = (i % 2 == 0 ? "class=\"teleoststandingsevenrow\"" : "class=\"teleoststandingsoddrow\"");
            else
                rowClassAttr = "";
            
            html += "<tr id=\"" + rowName + "\" " + rowClassAttr + ">";
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

        document.getElementById(rowName).classList.remove("teleoststandingsqualified")
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
        var finalsForm = standing.finals_form;

        while (finalsForm.length > 0 && finalsForm[0] == '-') {
            finalsForm = finalsForm.substring(1);
        }

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

        if (finalsForm.length > 0) {
            played = played.toString() + "(+" + finalsForm + ")";
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

        if (standing.qualified) {
            document.getElementById(rowName).classList.add("teleoststandingsqualified");
        }
        else {
            document.getElementById(rowName).classList.remove("teleoststandingsqualified");
        }
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

