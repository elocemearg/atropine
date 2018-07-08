class PlaceholderView extends View {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
    }

    setup(container) {
        var child = document.createElement("div");
        child.classList.add("placeholder");
        child.innerText = "Ignore this. It's just a figment of your imagination.";
        container.appendChild(child);
    }

    refresh(timeNow, enableAnimation) {
        return false;
    }
}
