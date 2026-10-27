import re
import requests
import frappe

from openai import OpenAI
from werkzeug.wrappers import Response

from .services import update_lead_data, should_create_lead, save_bot_response, create_initial_lead, \
    send_messenger_message, is_lead_complete, save_message_to_lead, get_next_question, get_user_profile

""" Obtener el token verificacion de meta-facebook """
def get_verify_token():
    return frappe.conf.get("meta_verify_token")

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

""" 2do step:
    procesa los eventos enviados desde messenger
    Evitar loops generados por Messenger
    Evitaa duplicidad de mensajes
    si envian Imágenes, stickers, audio, archivos, etc.
    ejecuta send_messenger_message
    
    si existing_lead es true
        ejecuta update_lead_data
    si proces should_create_lead
        ejecuta create_or_update_lead
    
    si todo ok 
        ejecuta ask_ai
        
    si si responde ok la ia
        ejecuta save_bot_response
        
    si respode ok save_boot_respnse
        ejecuta send_messenger_message con el resultado        
"""
def process_messenger_event(messaging_event):
    sender_id = messaging_event.get("sender", {}).get("id")
    if not sender_id:
        return

    message = messaging_event.get("message", {})

    # Evitar loops de Messenger
    if message.get("is_echo"):
        return

    message_id = message.get("mid")
    if not message_id:
        frappe.logger().warning("Messenger message without mid")
        return

    # Deduplicación
    cache_key = f"messenger_message:{message_id}"
    if frappe.cache().get_value(cache_key):
        frappe.logger().info(
            f"Duplicate Messenger message ignored: {message_id}"
        )
        return

    message_text = message.get("text")

    # Solo texto
    if not message_text:
        frappe.logger().info({
            "event": "messenger_non_text_message",
            "sender_id": sender_id,
            "message_id": message_id,
        })
        send_messenger_message(
            sender_id,
            "Por el momento solo puedo procesar mensajes de texto."
        )
        frappe.cache().set_value(cache_key, 1, expires_in_sec=86400)
        return

    try:
        existing_lead = frappe.db.exists(
            "Lead",
            {"custom_messenger_id": sender_id},
        )
        if not existing_lead:
            existing_lead = get_user_profile(sender_id)

        if existing_lead:
            lead_name = existing_lead
            updated = update_lead_data(sender_id, message_text)

            if not updated:
                step = frappe.db.get_value(
                    "Lead",
                    {"custom_messenger_id": sender_id},
                    "custom_capture_step",
                )

                if step == "email":
                    reply = "Ese correo no parece válido. Por favor, escríbelo nuevamente."
                elif step == "phone":
                    reply = "No pude registrar ese teléfono. Por favor, escríbelo nuevamente."
                else:
                    reply = get_next_question(sender_id)

                save_bot_response(lead_name, reply)
                send_messenger_message(sender_id, reply)
                frappe.cache().set_value(cache_key, 1, expires_in_sec=86400)
                return
        else:
            lead_name = create_initial_lead(sender_id)

        # Guardar mensaje recibido
        save_message_to_lead(lead_name, message_text)

        # Decidir respuesta
        if is_lead_complete(sender_id):
            reply = ask_ai(message_text)
            if not reply:
                reply = (
                    "Lo siento, no pude generar una respuesta "
                    "en este momento."
                )
        else:
            reply = get_next_question(sender_id)

        # Guardar y enviar respuesta
        save_bot_response(lead_name, reply)
        send_messenger_message(sender_id, reply)

        # Marcar como procesado después de completar el flujo
        frappe.cache().set_value(cache_key, 1, expires_in_sec=86400)

    except Exception:
        frappe.log_error(
            title="Messenger Event Error",
            message=frappe.get_traceback(),
        )

        send_messenger_message(
            sender_id,
            (
                "Ocurrió un error al procesar tu mensaje. "
                "Por favor intenta nuevamente más tarde."
            ),
        )


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