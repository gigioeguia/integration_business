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
        
        # 1. Registrar para depuración (mantenlo temporalmente)
        frappe.log_error(title="WhatsApp webhook recibido", message=frappe.as_json(payload))

        # 2. Lógica para procesar y crear Lead
        try:
            if payload and "entry" in payload:
                for entry in payload["entry"]:
                    for change in entry.get("changes", []):
                        value = change.get("value", {})
                        messages = value.get("messages", [])

                        for message in messages:
                            sender_phone = message.get("from")
                            
                            # Validar si el lead ya existe para no duplicar (opcional)
                            if not frappe.db.exists("Lead", {"mobile_no": sender_phone}):
                                lead = frappe.get_doc({
                                    "doctype": "Lead",
                                    "lead_name": f"WhatsApp Lead {sender_phone}",
                                    "mobile_no": sender_phone,
                                    "status": "Open",
                                    "source": "WhatsApp" # Asegúrate de tener esta fuente configurada
                                })
                                lead.insert(ignore_permissions=True)
                                frappe.db.commit()
                                
        except Exception as e:
            frappe.log_error(title="Error al crear Lead desde Webhook", message=str(e))

        return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")

    return Response("Method Not Allowed", status=405, mimetype="text/plain")
