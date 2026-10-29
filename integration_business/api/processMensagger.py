import re
import requests
import frappe

from openai import OpenAI

from .services import update_lead_data, should_create_lead, save_bot_response, create_initial_lead, \
    send_messenger_message, is_lead_complete, save_message_to_lead, get_next_question, get_user_profile

def ask_ai(message):

    chatbot = frappe.get_single(
        "WhatsApp Chatbot"
    )

    if not chatbot.enable_ai:
        return chatbot.default_response

    if not chatbot.ai_api_key:
        return chatbot.default_response

    try:

        client = OpenAI(
            api_key=chatbot.ai_api_key
        )

        response = client.chat.completions.create(
            model=chatbot.ai_model,
            messages=[
                {
                    "role": "system",
                    "content": chatbot.ai_system_prompt or ""
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            temperature=chatbot.ai_temperature or 0.7,
            max_tokens=chatbot.ai_max_tokens or 500
        )

        return response.choices[0].message.content

    except Exception:

        frappe.log_error(
            title="OpenAI Error",
            message=frappe.get_traceback()
        )

        return chatbot.default_response

def extract_customer_data(message):

    chatbot = frappe.get_single(
        "WhatsApp Chatbot"
    )

    client = OpenAI(
        api_key=chatbot.ai_api_key
    )

    response = client.chat.completions.create(
        model=chatbot.ai_model,
        messages=[
            {
                "role": "system",
                "content": """
                Extrae:
                - nombre
                - correo
                - telefono

                Devuelve JSON.
                """
            },
            {
                "role": "user",
                "content": message
            }
        ]
    )

    return response.choices[0].message.content

def process_messenger_event(messaging_event):
   
    channel = messaging_event.get("channel", None)

    sender_id = messaging_event.get("sender", {}).get("id")
    
    if not sender_id:
        return {"reply": None, "status": "ignored", "reason": "missing_sender_id"}

    message = messaging_event.get("message") or {}

    if message.get("is_echo"):
        return {"reply": None, "status": "ignored", "reason": "echo"}

    message_id = message.get("mid")
    if not message_id:
        frappe.logger().warning("Messenger message without mid")
        return {"reply": None, "status": "ignored", "reason": "missing_mid"}

    cache_key = f"messenger_message:{message_id}"
    if frappe.cache().get_value(cache_key):
        return {"reply": None, "status": "ignored", "reason": "duplicate"}

    message_text = message.get("text")

    if not message_text:
        reply = "Por el momento solo puedo procesar mensajes de texto."
        if channel == None:
            send_messenger_message(sender_id, reply)
        
        frappe.cache().set_value(cache_key, 1, expires_in_sec=86400)
        return {"reply": reply, "status": "ok"}

    try:
        lead_name = frappe.db.exists(
            "Lead",
            {"custom_messenger_id": sender_id},
        )

        if lead_name:
            lead_doc = frappe.get_doc("Lead", lead_name)
        else:
            lead_doc = create_initial_lead(sender_id)
            # Si create_initial_lead devuelve un nombre y no un documento:
            if isinstance(lead_doc, str):
                lead_doc = frappe.get_doc("Lead", lead_doc)

        updated = update_lead_data(sender_id, message_text)

        if not updated:
            step = frappe.db.get_value(
                "Lead",
                lead_doc.name,
                "custom_capture_step",
            )

            if step == "email":
                reply = "Ese correo no parece válido. Por favor, escríbelo nuevamente."
            elif step == "phone":
                reply = "No pude registrar ese teléfono. Por favor, escríbelo nuevamente."
            else:
                reply = get_next_question(sender_id, lead_doc)

            save_bot_response(lead_doc.name, reply)
            if channel == None:
                send_messenger_message(sender_id, reply)
            frappe.cache().set_value(cache_key, 1, expires_in_sec=86400)
            return {"reply": reply, "status": "ok"}

        save_message_to_lead(lead_doc, message_text)

        if is_lead_complete(sender_id):
            reply = ask_ai(message_text) or (
                "Lo siento, no pude generar una respuesta en este momento."
            )
        else:
            reply = get_next_question(sender_id, lead_doc)

        save_bot_response(lead_doc.name, reply)
        if channel == None:
            send_messenger_message(sender_id, reply)
        frappe.cache().set_value(cache_key, 1, expires_in_sec=86400)

        return {"reply": reply, "status": "ok"}

    except Exception:
        frappe.log_error(
            title="Messenger Event Error",
            message=frappe.get_traceback(),
        )
        reply = (
            "Ocurrió un error al procesar tu mensaje. "
            "Por favor intenta nuevamente más tarde."
        )
        if channel == None:
            send_messenger_message(sender_id, reply)
        return {"reply": reply, "status": "error"}