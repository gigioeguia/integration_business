import re

""" obtiene el imail de una conversacion """
def get_email_from_message(message):
    if not isinstance(message, str):
        return None

    pattern = r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+'
    match = re.search(pattern, message)

    return match.group(0) if match else None

""" obtiene el numero de movil de una conversacion """
def get_phone_from_message(message):
    if not isinstance(message, str):
        return None

    pattern = r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
    match = re.search(pattern, message)

    return match.group(0) if match else None
