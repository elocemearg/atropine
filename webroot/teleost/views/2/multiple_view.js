class MultipleView extends View {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc, views) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
        this.views = views;
        this.animatingViews = [];
        for (var i = 0; i < views.length; ++i) {
            this.animatingViews.push(false);
        }
    }

    setup(container) {
        for (var i = 0; i < this.views.length; ++i) {
            var child = document.createElement("div");
            container.appendChild(child);
            this.views[i].setup(child);
        }
    }

    refresh(timeNow, enableAnimation) {
        var anyTrue = false;
        /* If any of the views want to do an animation, record which views
         * want to do that, and we'll call refreshFrame on them */
        for (var i = 0; i < this.views.length; ++i) {
            var animate = this.views[i].refresh(timeNow, enableAnimation);
            if (!enableAnimation)
                animate = false;
            this.animatingViews[i] = animate;
            if (animate)
                anyTrue = true;
        }
        return anyTrue;
    }

    refreshFrame(timeNow) {
        /* Keep returning true until all our views return false from
         * their refreshFrame() method */
        var anyTrue = false;
        for (var i = 0; i < this.views.length; ++i) {
            if (this.animatingViews[i]) {
                this.animatingViews[i] = this.views[i].refreshFrame(timeNow);
            }
            if (this.animatingViews[i])
                anyTrue = true;
        }
        return anyTrue;
    }
}
