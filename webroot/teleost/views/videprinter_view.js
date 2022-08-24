var zero_to_nineteen = ["zero", "one", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
    "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
var decades = [ "zero", "ten", "twenty", "thirty", "forty", "fifty", "sixty",
    "seventy", "eighty", "ninety" ];

/* It's just possible this is slightly overengineered */
var thousand_powers = [ "thousand", "million", "billion", "trillion",
    "quadrillion", "quintillion", "sextillion", "septillion", "octillion",
    "nonillion", "decillion" ];

function number_to_words(number) {
    if (number < 0) {
        return "minus " + number_to_words(-number);
    }
    else if (number < 20) {
        return zero_to_nineteen[number]
    }
    else if (number < 100) {
        var ret = decades[Math.floor(number / 10)];
        if (number % 10 > 0)
            ret += "-" + zero_to_nineteen[number % 10];
        return ret;
    }
    else {
        var thousands = Math.floor(number / 1000);
        var hundreds = Math.floor(number / 100) % 10;
        var units = number % 100;
        var kpow = 0;
        var ret = "";

        while (kpow <= thousand_powers.length && thousands > 0) {
            var term = thousands % 1000;
            if (term > 0) {
                if (kpow >= thousand_powers.length) {
                    return "I'm going to call that infinity";
                }
                var prefix = number_to_words(term) + " " + thousand_powers[kpow];
                if (ret.length > 0) {
                    ret = prefix + " " + ret;
                }
                else {
                    ret = prefix;
                }
            }
            kpow++;
            thousands = Math.floor(thousands / 1000);
        }
        if (hundreds > 0) {
            if (ret.length > 0)
                ret += " ";
            ret += number_to_words(hundreds) + " hundred";
        }
        if (units > 0) {
            ret += " and " + number_to_words(units);
        }
        return ret;
    }
}

class VideprinterView extends View {
    constructor (tourneyName, leftPc, topPc, widthPc, heightPc, numRows, scoreBracketThreshold) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
        this.numRows = numRows;
        this.latestGameRevisionSeen = null;
        this.scoreBracketThreshold = scoreBracketThreshold;

        /* Milliseconds taken for the videprinter's scroll-up animation */
        this.scrollAnimateTime = 500;

        /* Milliseconds taken to horizontally animate a "typing" line of text */
        this.rowAnimateTime = 1000;

        /* List of all the applicable log entries in the tourney. "applicable"
         * means "we print this on the videprinter". */
        this.logList = [];

        /* An index to the next entry in logList yet to be printed. If
         * logListPrintPosition == logList.length, we're up to date and nothing
         * else is waiting to be printed. */
        this.logListPrintPosition = 0;

        /* Initially false - the first time we display anything, we just fill
         * the visible videprinter rows with the last N log entries. Then we
         * set animateVideprinter to true, and later log entries will be
         * animated. */
        this.animateVideprinter = false;

        /* If true, redraw() returns having done nothing, because we're still
         * waiting for some animation to complete after which we'll call
         * redraw() again. */
        this.redrawInProgress = false;

        /* <table> element */
        this.videprinterTable = null;

        /* Array of <td> elements in the videprinter, count = this.numRows */
        this.videprinterRows = [];

        /* Set by setup(), cleared by notifyClosed(). Handy if a timeout
         * fires after the view is no longer in use. */
        this.active = false;
    }

    setup(container) {
        super.setup(container);

        let videprinterContainer = document.createElement("DIV");
        videprinterContainer.className = "videprintercontainer";
        this.videprinterTable = document.createElement("TABLE");
        this.videprinterTable.className = "teleostvideprinter";
        this.videprinterRows = [];

        for (let row = 0; row < this.numRows; ++row) {
            let tr = document.createElement("TR");
            let td = document.createElement("TD");
            tr.className = "teleostvideprinterrow";
            td.className = "teleostvideprinterentry";
            td.id = "videprinterrow" + row.toString() + "_main";
            td.innerHTML = "&nbsp;";
            this.videprinterRows.push(td);
            tr.appendChild(td);
            this.videprinterTable.appendChild(tr);
        }

        videprinterContainer.appendChild(this.videprinterTable);

        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
        container.appendChild(videprinterContainer);

        this.logList = [];
        this.logListPrintPosition = 0;
        this.animateVideprinter = false;
        this.redrawInProgress = false;
        this.active = true;
    }

    format_videprinter_preamble(entry) {
        if (entry.log_type == 1 || entry.log_type == 2) {
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
        else {
            return "";
        }
    }

    format_videprinter_entry(entry) {
        if (entry.log_type == 1 || entry.log_type == 2) {
            var html = "";
            var supersededClass = entry.superseded ? " videprintersuperseded" : "";

            html += "<span class=\"videprinterplayer" + supersededClass + "\">";
            html += escapeHTML(entry.p1);
            if (entry.tc1 != null) {
                html += "<span class=\"teamdotleftplayer\"";
                if (!entry.superseded)
                    html += " style=\"color: " + teamColourToHTML(entry.tc1) + ";\"";
                html += ">" + teamIndicatorHTML + "</span>";
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
                if (this.scoreBracketThreshold != null && entry.s1 >= this.scoreBracketThreshold)
                    html += " (" + number_to_words(entry.s1) + ")";
                if (entry.tb && entry.s1 > entry.s2)
                    html += "*";
                html += " - ";
                html += entry.s2.toString();
                if (this.scoreBracketThreshold != null && entry.s2 >= this.scoreBracketThreshold)
                    html += " (" + number_to_words(entry.s2) + ")";
                if (entry.tb && entry.s2 >= entry.s1)
                    html += "*";
                html += " ";
            }
            html += "</span>";
            html += "<span class=\"videprinterplayer" + supersededClass + "\">";
            if (entry.tc2 != null) {
                html += "<span class=\"teamdotrightplayer\"";
                if (!entry.superseded)
                    html += " style=\"color: " + teamColourToHTML(entry.tc2) + ";\"";
                html += ">" + teamIndicatorHTML + "</span>";
            }
            html += escapeHTML(entry.p2);
            html += "</span>";

            return html;
        }
        else if ((entry.log_type & 97) != 0) {
            if (entry.comment == null) {
                return "";
            }
            else {
                var html = "<span class=\"videprintercommentbullet\">&#8227;</span>";
                html += " <span class=\"videprintercomment\">";
                html += escapeHTML(entry.comment);
                html += "</span>";
                return html;
            }
        }
        else {
            return "?";
        }
    }

    refresh(timeNow, enableAnimation) {
        if (this.latestGameRevisionSeen == null || gameStateRevision != this.latestGameRevisionSeen) {
            this.redraw();
        }
        return false;
    }

    /* Called externally. We ignore it if we're still animating a previous
     * redraw. */
    redraw() {
        if (!this.redrawInProgress) {
            this.redrawInternal();
        }
    }

    redrawInternal() {
        this.latestGameRevisionSeen = gameStateRevision;
        let gameState = this.getGameState();
        let applicableLogs = [];

        if (!gameState || !gameState.success || !gameState.logs || !this.active) {
            return;
        }

        /* We only want the log types we're interested in */
        for (var i = 0; i < gameState.logs.logs.length; ++i) {
            var lt = gameState.logs.logs[i].log_type;
            if (lt == 1 || lt == 2 || ((lt & 96) != 0 && (lt & 1) != 0)) {
                applicableLogs.push(gameState.logs.logs[i])
            }
        }

        this.logList = applicableLogs;
        if (!this.animateVideprinter || this.logListPrintPosition >= this.logList.length) {
            /* Refresh the whole videprinter without animating, and show the
             * last numRows rows. */
            let applicableLogsStart = applicableLogs.length - this.numRows;
            for (let row = 0; row < this.numRows; ++row) {
                let logRow = applicableLogsStart + row;
                if (logRow >= 0 && logRow < applicableLogs.length) {
                    this.populateRow(row, applicableLogs[logRow], false);
                }
                else {
                    this.clearRow(row);
                }
            }
            this.animateVideprinter = true;
            this.redrawInProgress = false;
            this.logListPrintPosition = this.logList.length;
        }
        else {
            /* There's at least one new log entry in logList which we haven't
             * printed yet. Set the animation wheels in motion. */
            this.redrawInProgress = true;
            this.servicePrintQueue();
        }
    }

    servicePrintQueue() {
        if (this.active && this.logListPrintPosition < this.logList.length) {
            let videprinter = this;
            this.startScrollAnimate();
            setTimeout(function() {
                videprinter.addRowAfterScrollAnimate();
            }, this.scrollAnimateTime);
        }
        else {
            this.redrawInProgress = false;
        }
    }

    addRowAfterScrollAnimate() {
        if (!this.active) {
            cancelScrollAnimate();
            this.redrawInProgress = false;
            return;
        }
        /* Set the first N-1 rows of the videprinter to the last N-1
         * rows in the complete log list which are before this entry, and
         * the Nth row of the videprinter to the new entry. */
        let logListPos = this.logListPrintPosition - this.numRows + 1;
        let videprinter = this;
        for (let row = 0; row < this.numRows; row++) {
            if (logListPos + row >= 0) {
                this.populateRow(row, this.logList[logListPos + row], logListPos + row >= this.logListPrintPosition);
            }
        }

        /* We've now printed this log entry */
        this.logListPrintPosition++;

        /* Remove the animation class from the videprinter table, which moves
         * it back down to its original position. */
        this.cancelScrollAnimate();

        /* When the new row finishes animating itself horizontally, call
         * redrawInternal() again to check if there is anything more we need
         * to print. */
        setTimeout(function() {
            videprinter.redrawInternal();
        }, this.rowAnimateTime);
    }

    populateRow(row, entry, animate) {
        let entry_preamble = this.format_videprinter_preamble(entry);
        let entry_main = this.format_videprinter_entry(entry);
        let main_td = this.videprinterRows[row];
        if (main_td) {
            /* If this is a new entry and so we're animating it, put it inside
             * an animation div */
            if (animate) {
                main_td.innerHTML = "<div class=\"videprinteranimatescoreline\">" + entry_preamble + " " + entry_main + "</div>";
            }
            else {
                main_td.innerHTML = entry_preamble + " " + entry_main;
            }
        }
    }

    clearRow(row) {
        let main_td = this.videprinterRows[row];
        if (main_td) {
            main_td.innerHTML + "&nbsp;";
        }
    }

    startScrollAnimate() {
        this.videprinterTable.classList.add("teleostvideprintertablescroll");
    }

    cancelScrollAnimate() {
        this.videprinterTable.classList.remove("teleostvideprintertablescroll");
    }

    notifyClosed() {
        this.active = false;
    }
}
