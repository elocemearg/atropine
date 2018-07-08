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
