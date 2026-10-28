import re
import requests
import frappe

from openai import OpenAI
from werkzeug.wrappers import Response
from .processMensagger import process_messenger_event 


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