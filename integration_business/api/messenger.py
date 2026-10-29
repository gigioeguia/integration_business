import frappe

from werkzeug.wrappers import Response
from .processMensagger import process_messenger_event 

""" Obtener el token verificacion de meta-facebook """
def get_verify_token():
    return frappe.conf.get("meta_verify_token")

""" 1er step:
    si todo ok, continua process_messenger_event
"""
def process_payload(payload):
    if payload.get("object") != "page":
        return
    for entry in payload.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            process_messenger_event(messaging_event)


@frappe.whitelist(allow_guest=True)
def webhook():
    """Servcio que usa meta-facebook para validar servicio"""
    if frappe.request.method == "GET":
        mode = frappe.form_dict.get("hub.mode")
        token = frappe.form_dict.get("hub.verify_token")
        challenge = frappe.form_dict.get("hub.challenge")

        if ( mode == "subscribe"
            and token == get_verify_token()
            and challenge
        ):
            return Response(
                challenge,
                status=200,
                mimetype="text/plain"
            )

        return Response(
            "Forbidden",
            status=403,
            mimetype="text/plain"
        )

    """Servcio que usa meta-facebook para mandar los mensajes"""
    if frappe.request.method == "POST":
        payload = frappe.request.get_json(silent=True)

        frappe.logger().info({
            "event": "messenger_webhook",
            "payload": payload
        })

        try:
            process_payload(payload or {})
            frappe.db.commit()

        except Exception:
            frappe.log_error(
                title="Messenger Webhook Error",
                message=frappe.get_traceback()
            )

        return Response(
            "EVENT_RECEIVED",
            status=200,
            mimetype="text/plain"
        )

    return Response(
        "Method Not Allowed",
        status=405,
        mimetype="text/plain"
    )