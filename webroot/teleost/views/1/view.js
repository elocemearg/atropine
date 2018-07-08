class View {
    constructor (tourneyName, leftPc, topPc, widthPc, heightPc) {
        this.tourneyName = tourneyName;
        this.leftPc = leftPc;
        this.topPc = topPc;
        this.widthPc = widthPc;
        this.heightPc = heightPc;
    }

    setup(container) {
        this.container = container;
        this.container.style.position = "absolute";
        this.container.style.top = this.topPc.toString() + "%";
        this.container.style.left = this.leftPc.toString() + "%";
        this.container.style.width = this.widthPc.toString() + "%";
        this.container.style.height = this.heightPc.toString() + "%";
    }

    /* Gives the view an opportunity to repaint itself using information in
     * the global gameState variable.
     * Return true if the refresh operation needs to be animated. In that
     * case refreshFrame() will be called after every animationFrameMs
     * milliseconds until refreshFrame() returns false.
     *
     * If enableAnimation is false, refresh() must complete the repaint
     * operation and must return false. refreshFrame() will not be called.
     */
    refresh(timeNow, enableAnimation) {
    }

    refreshFrame(timeNow) {
    }

    redraw() {
    }

    getGameState() {
        if (gameState == null) {
            return { "success" : false, "description" : "Please wait..." };
        }
        return gameState;
    }
}
