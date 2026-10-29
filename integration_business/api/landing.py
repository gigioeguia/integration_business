import time
import uuid

import frappe
from .processMensagger import process_messenger_event


def process_chat_message(channel, payload):
    timestamp = int(time.time() * 1000)
    payload = {
        'channel': channel,
        'sender': {'id': payload.get("session_id")}, 
        'recipient': {'id': payload.get("page_id")}, 
        'timestamp': timestamp, 
        'message': {'mid': payload.get("message_id"), 'text': (payload.get("message") or "").strip()}
    }
    return process_messenger_event(payload); 


@frappe.whitelist(allow_guest=True)
def capture():
    
    if frappe.request.method == "GET":
        return {"hola":"hola"}
        
    if frappe.request.method == "POST": 
        payload = frappe.request.get_json(silent=True) or {}
          
        message = (payload.get("message") or "").strip()

        if not message or not payload.get("session_id") or not payload.get("page_id"):
            frappe.throw(
                "Faltan el mensaje, el identificador de sesión o el identificador de página."
            )

        reply = process_chat_message( "web", payload )

        return {"reply": reply}
