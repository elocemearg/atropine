
class WelcomeView extends View {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
        this.lastGameStateRevisionSeen = null;
        this.background = null;
        this.heading1 = null;
        this.heading2 = null;
    }

    setup(container) {
        super.setup(container);
        container.style.maxWidth = "100%";

        container.innerHTML = "";
        this.background = document.createElement("DIV");
        this.background.className = "movingbackground";
        this.heading1 = document.createElement("DIV");
        this.heading1.id = "welcomeheading1";
        this.heading1.innerHTML = "&nbsp;";
        this.heading1.className = "welcomeheading";
        this.heading2 = document.createElement("DIV");
        this.heading2.id = "welcomeheading2";
        this.heading2.innerText = "Welcome";
        this.heading2.className = "welcomeheading";
        this.container.appendChild(this.background);
        this.container.appendChild(this.heading1);
        this.container.appendChild(this.heading2);
    }

    refresh(timeNow, enableAnimation) {
        /* To be called by superclass */
        if (this.latestGameRevisionSeen == null || gameStateRevision != this.latestGameRevisionSeen) {
            let gameState = this.getGameState();
            if (gameState != null && gameState.success && gameState.tourney &&
                    gameState.tourney.success) {
                let tourney = gameState.tourney;
                let eventName = tourney.full_name;

                if (eventName && eventName != "") {
                    this.heading1.innerText = "Welcome to";
                    this.heading2.innerText = eventName;
                }
                else {
                    this.heading1.innerHTML = "&nbsp;";
                    this.heading2.innerText = "Welcome";
                }
            }
            this.latestGameRevisionSeen = gameStateRevision;
        }
        return false;
    }
}
