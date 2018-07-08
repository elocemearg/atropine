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
