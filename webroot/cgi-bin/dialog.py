import cgicommon

# Produce HTML for a modal dialog box containing a form with Submit and Cancel
# buttons. The Submit button submits the form and the Cancel button closes the
# dialog box. The form elements should be given in form_html.
def get_html(dialog_id, title, submit_button_label, cancel_button_label,
        request_method, form_action, submit_button_name, form_html):
    # Background which fills the screen and dims it. Be nice to the user:
    # if they click anywhere on the background and not on the dialog box,
    # make the dialog box go away with no other effect.
    return """
<div class="dialogbackground" style="display: none;" id="%(dialog_id)s" onclick="if (event.target.id == '%(dialog_id)s') { document.getElementById('%(dialog_id)s').style.display='none'; }">
    <div class="dialogboxcontainer">
        <div class="dialogbox">
            <h1>%(title)s</h1>
            <form method="%(request_method)s" action="%(form_action)s">
                %(form_html)s
                <div class="formcontrolrowactions">
                    <input type="submit" name="%(submit_button_name)s" value="%(submit_button_label)s">
                    <button type="button" onclick="document.getElementById('%(dialog_id)s').style.display = 'none'; return false;">%(cancel_button_label)s</button>
                </div>
            </form>
        </div>
    </div>
</div>
""" % {
        "dialog_id" : cgicommon.escape(dialog_id),
        "request_method" : cgicommon.escape(request_method),
        "form_action" : cgicommon.escape(form_action),
        "title" : cgicommon.escape(title),
        "submit_button_name" : cgicommon.escape(submit_button_name),
        "submit_button_label" : cgicommon.escape(submit_button_label),
        "cancel_button_label" : cgicommon.escape(cancel_button_label),
        "form_html" : form_html
    }
