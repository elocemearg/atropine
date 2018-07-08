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

