import frappe
import requests

from frappe.utils import validate_email_address

from .utils import get_email_from_message, get_phone_from_message

GRAPH_API_VERSION = "v26.0"

""" 
Obtener el token de pagina de acceso de facebook 
"""
def get_page_access_token():
    return frappe.conf.get("page_access_token")

"""
crea un registro de tipo Communication
"""
def save_message_to_lead(lead_name, message_content):
    try:
        communication = frappe.get_doc({
            "doctype": "Communication",
            "communication_type": "Communication",
            "subject": "Mensaje recibido vía Messenger",
            "content": message_content,
            "reference_doctype": "Lead",
            "reference_name": lead_name,
            "status": "Linked",
            "sent_or_received": "Received"
        })

        communication.insert(ignore_permissions=True)
        frappe.db.commit()

        return communication.name

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Error guardando mensaje en Lead"
        )
        return None

"""
obtener información básica de un usuario que interactuó con tu página mediante Messenger
PSID (Page Scoped ID)
"""    
def get_user_profile(psid):
    access_token = get_page_access_token()
    response = requests.get(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{psid}",
        params={
            "fields": "first_name,last_name",
            "access_token": access_token
        },
        timeout=10
    )
    response.raise_for_status()
    return response.json()

"""
verifica si un Lead asociado a un usuario de Messenger ya tiene toda la información mínima requerida
"""
def is_lead_complete(sender_id):

    lead_name = frappe.db.get_value(
        "Lead",
        {"custom_messenger_id": sender_id},
        "name"
    )

    if not lead_name:
        return False

    step = frappe.db.get_value(
        "Lead",
        lead_name,
        "custom_capture_step"
    )

    return step == "completed"

"""
generar un Lead mínimo y después comenzar el flujo de preguntas
"""    
def create_initial_lead(sender_id):

    lead = frappe.get_doc({
        "doctype": "Lead",
        "first_name": "Prospecto Messenger",
        "custom_messenger_id": sender_id,
        "status": "Lead",
        "custom_capture_step": "first_name"
    })

    lead.insert(ignore_permissions=True)

    return lead.name

"""
actualizar los datos de un Lead existente cuando recibe un nuevo mensaje desde Messenger
"""
def update_lead_data(sender_id, message_text):
    lead_name = frappe.db.get_value(
        "Lead",
        {"custom_messenger_id": sender_id},
        "name",
    )
    if not lead_name:
        return False

    lead = frappe.get_doc("Lead", lead_name)
    value = (message_text or "").strip()

    if not value:
        return False

    step = lead.custom_capture_step

    if step == "email":
        try:
            value = get_email_from_message(value)
            if value != None:
                validate_email_address(value, throw=True)
        except frappe.exceptions.InvalidEmailAddressError:
            return False

        lead.email_id = value
        lead.custom_capture_step = "phone"

    elif step == "first_name":
        lead.first_name = value
        lead.custom_capture_step = "last_name"

    elif step == "last_name":
        lead.last_name = value
        lead.custom_capture_step = "email"

    elif step == "phone":
        lead.phone = value
        lead.custom_capture_step = None

    else:
        return False

    frappe.logger().info(
        f"Messenger capture: lead={lead.name}, "
        f"step={lead.custom_capture_step}, "
        f"email_id={lead.email_id!r}, input={value!r}"
    )
    
    frappe.logger().error(
        f"Antes de guardar Lead {lead.name}: "
        f"step={step!r}, email_id={lead.email_id!r}, input={value!r}"
    )

    lead.save(ignore_permissions=True)
    return True




"""
filtro de validación para decidir si ya existe suficiente información para crear un Lead
"""
def should_create_lead(sender_id, message_text):
    email = get_email_from_message(message_text)
    phone = get_phone_from_message(message_text)
    if not email or not phone:
        return False
    return True

"""
Guarda una respuesta enviada por el chatbot en el historial del Lead.
"""
def save_bot_response(lead_name, response_text):

    communication = frappe.get_doc({
        "doctype": "Communication",
        "communication_type": "Automated Message",
        "subject": "Respuesta automática IA",
        "content": response_text,
        "reference_doctype": "Lead",
        "reference_name": lead_name,
        "status": "Linked",
        "sender_full_name": "Chatbot IA",
        "sent_or_received": "Sent"
    })

    communication.insert(
        ignore_permissions=True
    )

"""
ennviar un mensaje desde tu Página de Facebook hacia un usuario de Messenger utilizando la Facebook Messenger Send API
"""
def send_messenger_message(recipient_id, text):

    response = requests.post(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/messages",
        params={
            "access_token": get_page_access_token()
        },
        json={
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "text": text
            }
        },
        timeout=10
    )

    response.raise_for_status()

    return response.json()

"""
revisar qué campos obligatorios faltan y devolver la siguiente pregunta correspondiente
"""
def get_next_question(sender_id):

    lead_name = frappe.db.get_value(
        "Lead",
        {"custom_messenger_id": sender_id},
        "name"
    )

    if not lead_name:
        return "¿Cuál es tu nombre?"

    lead = frappe.get_doc("Lead", lead_name)

    questions = {
        "first_name": "¿Cuál es tu nombre?",
        "last_name": "¿Cuáles son tus apellidos?",
        "email": "¿Cuál es tu correo electrónico?",
        "phone": "¿Cuál es tu número de teléfono?",
        "completed": "¿En qué puedo ayudarte?"
    }

    return questions.get(
        lead.custom_capture_step,
        "¿En qué puedo ayudarte?"
    )