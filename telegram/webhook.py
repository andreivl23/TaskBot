import requests
from flask import request
from telegram.callbacks import handle_message, handle_callback



def telegram_webhook():
    data = request.json
    print("DEBUG WEBHOOK DATA: ", data)
    if "callback_query" in data:
        return handle_callback(data["callback_query"])

    if "message" in data:
        return handle_message(data["message"])

    return "ok", 200
