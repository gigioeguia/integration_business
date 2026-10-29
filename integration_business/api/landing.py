import time
import uuid

import frappe
from .processMensagger import process_messenger_event


def process_chat_message(channel, message_id, session_id, page_id, message):
    timestamp = int(time.time() * 1000)

    payload = {
        "object": channel,
        "entry": [
            {
                "id": page_id,
                "time": timestamp,
                "messaging": [
                    {
                        "sender": {"id": session_id},
                        "recipient": {"id": page_id},
                        "timestamp": timestamp,
                        "message": {
                            "mid": message_id,
                            "text": message,
                        },
                    }
                ],
            }
        ],
    }
    return process_messenger_event(payload); 


@frappe.whitelist(allow_guest=True)
def capture():
    
    if frappe.request.method == "GET":
        return {"hola":"hola"}
        
    if frappe.request.method == "POST": 
        payload = frappe.request.get_json(silent=True) or {}
        message = (payload.get("message") or "").strip()
        session_id = payload.get("session_id")
        page_id = payload.get("page_id")
        message_id = payload.get("message_id") or str(uuid.uuid4())
           
        message = (message or "").strip()

        if not message or not session_id or not page_id:
            frappe.throw(
                "Faltan el mensaje, el identificador de sesión o el identificador de página."
            )

        if not message_id:
            message_id = str(uuid.uuid4())

        reply = process_chat_message(
            channel="web",
            message_id=message_id,
            session_id=session_id,
            page_id=page_id,
            message=message,
        )

        return {"reply": reply}
