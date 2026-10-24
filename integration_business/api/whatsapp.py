import frappe
from werkzeug.wrappers import Response

@frappe.whitelist(allow_guest=True)
def webhook():
    if frappe.request.method == "GET":
        mode = frappe.form_dict.get("hub.mode")
        token = frappe.form_dict.get("hub.verify_token")
        challenge = frappe.form_dict.get("hub.challenge")
        verify_token = frappe.conf.get("meta_verify_token")

        if mode == "subscribe" and token and token == verify_token and challenge is not None:
            return Response(challenge, status=200, mimetype="text/plain")

        return Response("Forbidden", status=403, mimetype="text/plain")

    if frappe.request.method == "POST":
        payload = frappe.request.get_json(silent=True)
        frappe.log_error(
            title="WhatsApp webhook recibido",
            message=frappe.as_json(payload) if payload is not None else frappe.request.get_data(as_text=True)
        )
        return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")

    return Response("Method Not Allowed", status=405, mimetype="text/plain")
