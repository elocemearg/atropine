class ImageView extends View {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc, imageUrl) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
        this.imageUrl = imageUrl;
    }

    setup(container) {
        var html = "<div class=\"imageviewcontainer\">";
        //html += "<img src=\"/images/test_card_f.png\" class=\"failimage\" />";
        html += "<img src=\"" + escapeHTML(this.imageUrl) + "\" class=\"imageviewimage\" />";
        html += "</div>";
        container.innerHTML = html;
    }

    refresh(timeNow, enableAnimation) {
        return false;
    }
}
