class PagedTableView extends View {
    /* Any view consisting of a number of pages, each with a number of rows,
     * and we scroll from page to page periodically */
    constructor (tourneyName, leftPc, topPc, widthPc, heightPc, rowsPerPage, scrollPeriod) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
        this.rowsPerPage = rowsPerPage;
        this.currentPageIndex = 0;
        this.lastScroll = 0;
        this.newPageInfo = null;
        this.scrollPeriod = scrollPeriod;
        this.lastGameRevisionSeen = null;
    }

    nextPage() {
        this.currentPageIndex += 1;
    }

    getFrameSlowdownFactor() {
        return 1;
    }

    refresh(timeNow, enableAnimation) {
        var doRedraw = (this.lastGameRevisionSeen == null || this.lastGameRevisionSeen != gameStateRevision);
        var doScroll = false;
        var oldPageIndex = this.currentPageIndex;

        if (this.lastScroll + this.scrollPeriod <= timeNow) {
            if (this.lastScroll > 0) {
                /* We want to scroll to the next page */
                this.nextPage();
                doScroll = true;
            }
            this.lastScroll = timeNow;
            doRedraw = true;
        }

        if (doRedraw) {
            this.lastGameRevisionSeen = gameStateRevision;
            this.newPageInfo = this.getPageInfo();

            /* Don't do the scrolly effect if we're scrolling from one
             * page to the same page, e.g. if there's only one page. */
            if (oldPageIndex == this.currentPageIndex)
                doScroll = false;
        }

        if (this.pageInfoIsSuccessful(this.newPageInfo) && enableAnimation) {
            if (doScroll) {
                this.animateFrameNumber = 0;
                this.animateFramesMoved = 0;
                this.animateNumRowsCleared = 0;
                this.animateNumRowsFilled = 0;
                return true;
            }
        }
        if (doRedraw) {
            if (this.pageInfoIsSuccessful(this.newPageInfo))
                this.redraw(this.newPageInfo);
            else
                this.redrawError(this.newPageInfo);
        }
        return false;
    }

    refreshFrame(timeNow) {
        if (this.animateFrameNumber % this.getFrameSlowdownFactor() == 0) {
            /* Fill in a row this many frames after it was cleared */
            var replaceRowDelay = this.rowsPerPage / 2 + 1;
            if (replaceRowDelay < 3)
                replaceRowDelay = 3;
            if (replaceRowDelay > this.rowsPerPage)
                replaceRowDelay = this.rowsPerPage;

            if (this.animateNumRowsCleared < this.rowsPerPage) {
                this.clearRow(this.animateNumRowsCleared);
                this.animateNumRowsCleared++;
            }

            if (this.animateFramesMoved >= replaceRowDelay || this.animateFramesMoved >= this.rowsPerPage) {
                if (this.animateNumRowsFilled == 0)
                    this.redrawHeadings(this.newPageInfo);
                this.redrawRow(this.newPageInfo, this.animateNumRowsFilled);
                this.animateNumRowsFilled++;
            }
            this.animateFramesMoved++;
        }
        this.animateFrameNumber++;

        return (this.animateNumRowsFilled < this.rowsPerPage);
    }

    redraw(page) {
        this.redrawHeadings(page);

        for (var tableRow = 0; tableRow < this.rowsPerPage; ++tableRow) {
            this.redrawRow(page, tableRow);
        }
    }
}

