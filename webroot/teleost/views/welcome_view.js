class WelcomeView extends View {
    constructor(tourneyName, leftPc, topPc, widthPc, heightPc) {
        super(tourneyName, leftPc, topPc, widthPc, heightPc);
        this.lastGameStateRevisionSeen = null;
        this.lastUpdate = null;
        this.background = null;
        this.heading1 = null;
        this.heading2 = null;
    }

    setup(container) {
        super.setup(container);
        container.style.maxWidth = "100%";

        container.innerHTML = "";
        this.background = document.createElement("DIV");
        this.background.className = "welcomebackground";
        this.heading1 = document.createElement("DIV");
        this.heading1.id = "welcomeheading1";
        this.heading1.innerHTML = "&nbsp;";
        this.heading1.className = "welcomeheading";
        this.heading2 = document.createElement("DIV");
        this.heading2.id = "welcomeheading2";
        this.heading2.innerText = "Welcome";
        this.heading2.className = "welcomeheading";
        this.background.appendChild(this.heading1);
        this.background.appendChild(this.heading2);
        container.appendChild(this.background);
    }

    refresh(timeNow, enableAnimation) {
        if (this.lastGameStateRevisionSeen != null && this.lastGameStateRevisionSeen == gameStateRevision) {
            return false;
        }
        if (this.lastUpdate != null && this.lastUpdate + this.refreshPeriod > timeNow) {
            return false;
        }
        this.lastUpdate = timeNow;
        this.lastGameStateRevisionSeen = gameStateRevision;

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
        return false;
    }

    refreshFrame(timeNow) {
        return false;
    }
}
