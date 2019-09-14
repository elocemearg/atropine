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
        this.latestLogSeqShown = null;
        this.scoreBracketThreshold = scoreBracketThreshold;
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
        else if (entry.log_type == 101) {
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

