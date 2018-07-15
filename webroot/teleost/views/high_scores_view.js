class HighScoresView extends PagedTableView {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc, 10, 10000);
        this.numRows = 10;
        this.lastGameRevisionSeen = null;
    }

    setup(container) {
        super.setup(container);
        
        var html = "";
        html += "<div class=\"viewheading headingbar\">";
        html += "<div class=\"viewheadingtext\" id=\"highscoresheading\">";
        html += "</div>";
        html += "</div>";

        html += "<table class=\"tableofgames highscorestable\">";
        html += "<colgroup>";
        html += "<col class=\"highscorescolround\" />";
        html += "<col class=\"highscorescolp1\" />";
        html += "<col class=\"highscorescolscore\" />";
        html += "<col class=\"highscorescolp2\" />";
        html += "</colgroup>";

        for (var rowNum = 0; rowNum < this.numRows; ++rowNum) {
            var rowName = "highscoresrow" + rowNum.toString();
            html += "<tr id=\"" + rowName + "\">";
            html += "<td class=\"highscoresround\" id=\"" + rowName + "_round\">&nbsp;</td>";
            html += "<td class=\"roundresultsp1\" id=\"" + rowName + "_p1\">&nbsp;</td>";
            html += "<td class=\"roundresultsscore\" id=\"" + rowName + "_score\">&nbsp;</td>";
            html += "<td class=\"roundresultsp2\" id=\"" + rowName + "_p2\">&nbsp;</td>";
            html += "</tr>";
        }

        html += "</table>";

        container.innerHTML = html;
    }


    setRowDisplay(rowNum, value) {
        var rowName = "highscoresrow" + rowNum.toString();
        document.getElementById(rowName).style.display = value;
    }

    removeRow(rowNum) {
        this.setRowDisplay(rowNum, "none");
    }

    showRow(rowNum) {
        this.setRowDisplay(rowNum, null);
    }

    getPageInfo() {
        var gameState = this.getGameState();
        
        /* Page 0: Highest winning scores
         * Page 1: Highest losing scores
         * Page 2: Highest combined scores
         */

        if (this.currentPageIndex > 2) {
            this.currentPageIndex = 0;
        }

        var replyDict = {};

        if (gameState.success) {
            var gameSet = [];
            switch (this.currentPageIndex) {
                case 0:
                    gameSet = gameState.highscores.highest_winning_scores;
                    replyDict.title = "Highest winning scores";
                    break;
                case 1:
                    gameSet = gameState.highscores.highest_losing_scores;
                    replyDict.title = "Highest losing scores";
                    break;
                case 2:
                    gameSet = gameState.highscores.highest_combined_scores;
                    replyDict.title = "Highest combined scores";
                    break;
                default:
                    gameSet = [];
                    replyDict.title = "Dudley Doolittle's best jokes";
            }

            replyDict.entries = gameSet;
            replyDict.success = true;
        }
        else {
            replyDict.entries = [];
            replyDict.errorString = gameState.description;
            replyDict.success = false;
        }

        return replyDict;
    }

    pageInfoIsSuccessful(obj) {
        if (obj == null)
            return false;
        else
            return obj.success;
    }

    redrawHeadings(obj) {
        document.getElementById("highscoresheading").innerText = obj.title;
    }

    redrawError(obj) {
        document.getElementById("highscoresheading").innerText = obj.errorString;
    }

    clearRow(rowNum) {
        var rowName = "highscoresrow" + rowNum.toString();
        var suffixes = [ "round", "p1", "score", "p2" ];
        for (var i = 0; i < suffixes.length; ++i) {
            var elementName = rowName + "_" + suffixes[i];
            document.getElementById(elementName).innerHTML = "&nbsp;";
        }
    }

    redrawRow(obj, rowNum) {
        if (obj != null) {
            if (rowNum >= obj.entries.length) {
                while (rowNum < this.numRows) {
                    this.removeRow(rowNum);
                    rowNum++;
                }
            }
            else {
                var entry = obj.entries[rowNum];
                var rowName = "highscoresrow" + rowNum.toString();

                var roundText = "R" + entry.round_num.toString();
                if (entry.div_short_name) {
                    roundText += " " + entry.div_short_name;
                }

                document.getElementById(rowName + "_round").innerText = roundText;
                document.getElementById(rowName + "_p1").innerText = entry.name1;
                document.getElementById(rowName + "_score").innerHTML = formatScore(entry.score1, entry.score2, entry.tb);
                document.getElementById(rowName + "_p2").innerText = entry.name2;

                this.showRow(rowNum);
            }
        }
    }
}
