import frappe

from frappe.utils import now_datetime

from .processMensagger import process_messenger_event 

def process_chat_message(channel, message_id, session_id, page_id, message):
    timestamp = now_datetime()
    payload = {
        "object": channel,
        "entry": [
            {
            "id": page_id,
            "time": now_datetime(),
            "messaging": [
                {
                "sender": {
                    "id": session_id
                },
                "recipient": {
                    "id": page_id
                },
                "timestamp": now_datetime(),
                "message": {
                    "mid": message_id,
                    "text": "Hola, este es el mensaje"
                }
                }
            ]
            }
        ]
        }
    return process_messenger_event(payload)

@frappe.whitelist(allow_guest=True)
def capture(message_id=None, session_id=None, page_id=None, message=None):
    if not message or not session_id or not message_id:
        frappe.throw("Faltan el mensaje, el identificador de sesión o el identificador del mensaje.")
    channel="web"
    reply = process_chat_message( channel, message_id, session_id, page_id, message )

    return {"reply": reply}