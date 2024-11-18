import htmlcommon

# Produce HTML for a modal dialog box containing a form with Submit and Cancel
# buttons. The Submit button submits the form and the Cancel button closes the
# dialog box.
#
# To show the dialog box, call the Javascript function dialogBoxShow(), which
# is defined in DIALOG_JAVASCRIPT. The calling page should emit the contents of
# DIALOG_JAVASCRIPT in a <script> tag somewhere.
def get_html(dialog_id):
    # The background element fills the screen and dims it. Be nice to the user:
    # if they click anywhere on the background and not on the dialog box,
    # make the dialog box go away with no other effect.
    #
    # Most of the blank elements in this HTML are filled in by dialogBoxShow().
    return """
<div class="dialogbackground" style="display: none;" id="%(dialog_id)s" onclick="if (event.target.id == '%(dialog_id)s') { document.getElementById('%(dialog_id)s').style.display='none'; }">
    <div class="dialogboxcontainer">
        <div class="dialogbox">
            <h2 class="dialogboxtitle"></h1>
            <form class="dialogboxform" method="POST" action="">
                <div class="dialogboxformcontrols"></div>
                <div class="formcontrolrowactions">
                    <input type="submit" class="dialogboxsubmit bigbutton" name="dialogsubmit" value="OK">
                    <button type="button" class="dialogboxcancel bigbutton">Cancel</button>
                </div>
            </form>
        </div>
    </div>
</div>
""" % {
        "dialog_id" : htmlcommon.escape(dialog_id)
    }

DIALOG_JAVASCRIPT = """
function dialogBoxCancelHandler(event) {
    let element = event.target;

    /* Find the nearest enclosing element with a class of "dialogbackground */ 
    while (element != null && !element.classList.contains("dialogbackground")) {
        element = element.parentElement;
    }

    /* This is the dialog box background. Make it invisible again. */
    if (element) {
        element.style.display = "none";
    }
    return false;
}

function dialogBoxShow(dialogId, title, submitButtonLabel, cancelButtonLabel,
        requestMethod, formAction, submitButtonName, formInputElements, formHiddenInputs={}) {
    let dialogBox = document.getElementById(dialogId);
    if (dialogBox == null) {
        return;
    }
    dialogBox.style.display = "block";

    let titleElements = dialogBox.getElementsByClassName("dialogboxtitle");
    for (let i = 0; i < titleElements.length; i++) {
        titleElements[i].innerText = title;
    }

    let forms = dialogBox.getElementsByClassName("dialogboxform");
    for (let i = 0; i < forms.length; i++) {
        let form = forms[i];
        form.method = requestMethod;
        if (formAction) {
            form.action = formAction;
        }
        let controlsDiv = form.getElementsByClassName("dialogboxformcontrols");
        if (controlsDiv.length > 0) {
            controlsDiv = controlsDiv[0];
            while (controlsDiv.firstChild) {
                controlsDiv.removeChild(controlsDiv.firstChild);
            }
            for (let j = 0; j < formInputElements.length; j++) {
                controlsDiv.appendChild(formInputElements[j]);
            }
            for (let name in formHiddenInputs) {
                let hiddenInput = document.createElement("INPUT");
                hiddenInput.type = "hidden";
                hiddenInput.name = name;
                hiddenInput.value = formHiddenInputs[name].toString();
                controlsDiv.appendChild(hiddenInput);
            }
        }
    }

    /* Assume one each of these */
    let submitButton = dialogBox.getElementsByClassName("dialogboxsubmit");
    if (submitButton.length > 0) {
        /* The submit button submits the form and hence reloads the page */
        submitButton = submitButton[0];
        submitButton.name = submitButtonName;
        submitButton.value = submitButtonLabel;
    }
    let cancelButton = dialogBox.getElementsByClassName("dialogboxcancel");
    if (cancelButton.length > 0) {
        /* The cancel button just closes the dialog box */
        cancelButton = cancelButton[0];
        cancelButton.innerText = cancelButtonLabel;
        cancelButton.removeEventListener("click", dialogBoxCancelHandler);
        cancelButton.addEventListener("click", dialogBoxCancelHandler);
    }

    /* Finally, if any element has the focusifvisible class, focus it. */
    let focused = dialogBox.getElementsByClassName("focusifvisible");
    for (let i = 0; i < focused.length; i++) {
        if (focused[i].style.visibility != "hidden") {
            focused[i].focus();
            break;
        }
    }
}
"""
