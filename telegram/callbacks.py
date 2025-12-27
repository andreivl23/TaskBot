import requests

from prompt import chat_prompt
from telegram.keyboards import *
from database import get_or_create_user, mark_task_done, get_pending_tasks

import os

TELEGRAM_API = f"https://api.telegram.org/bot{os.getenv('TASKBOT_TELEGRAM_TOKEN')}/sendMessage"
WELCOME_TEXT = "Hello!\nThis is early testing"

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(TELEGRAM_API, json=payload, timeout=10)



from telegram.text_actions import TEXT_ACTIONS

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    tg_user_id = message["from"]["id"]

    user_id = get_or_create_user(tg_user_id)

    if text == "/start":
        send_message(chat_id, WELCOME_TEXT, reply_markup=main_menu_keyboard())
        return "ok", 200

    # 1️⃣ Check if text matches a menu button
    if text in TEXT_ACTIONS:
        handle_text_action(TEXT_ACTIONS[text], chat_id, user_id)
        return "ok", 200

    # 2️⃣ Otherwise → chat only
    reply = chat_prompt(text, user_id)
    send_message(chat_id, reply)
    return "ok", 200


def handle_text_action(action, chat_id, user_id):
    match action:
        case "task:create":
            send_message(chat_id, "Send me the task title.")
        case "task:mark_menu":
            tasks = get_pending_tasks(user_id)
            if not tasks:
                send_message(chat_id, "No tasks to mark as done.")
            else:
                send_message(
                    chat_id,
                    "Select a task to mark as done:",
                    reply_markup=task_list_keyboard(tasks)
                )
        case "category:menu":
            send_message(
                chat_id,
                "Manage categories:",
                reply_markup=category_menu_keyboard()
            )
        case "task:list":
            reply = chat_prompt("show tasks", user_id)
            send_message(chat_id, reply)
        case _:
            send_message(chat_id,"Error, non existent action: " + action )


def handle_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    data = cb["data"]
    tg_user_id = cb["from"]["id"]
    user_id = get_or_create_user(tg_user_id)

    parts = data.split(":")
    domain = parts[0]
    action = parts[1]
    arg = parts[2] if len(parts) > 2 else None

    match (domain, action):
        case ("task", "done"):
            mark_task_done(user_id, int(arg))
            send_message(chat_id, "Task marked as done.")
        case ("category", "menu"):
            send_message(
                chat_id,
                "Manage categories:",
                reply_markup=category_menu_keyboard()
            )
        case ("menu", "main"):
            send_message(chat_id, "Main menu", reply_markup=main_menu_keyboard())
    return "ok", 200
