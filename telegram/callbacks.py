from datetime import date

import requests
from dateutil.utils import today

from preprocessing import resolve_time_expression, normalize_due_date
from prompt import chat_prompt, create_task_prompt, assign_category_prompt, date_prompt
from telegram.keyboards import *
from database import get_or_create_user, mark_task_done, get_pending_tasks, set_user_state, get_user_state, \
    clear_user_state

from telegram.text_actions import TEXT_ACTIONS

import os

TELEGRAM_API = f"https://api.telegram.org/bot{os.getenv('TASKBOT_TELEGRAM_TOKEN')}/sendMessage"
WELCOME_TEXT = "Hello!\nThis is early testing. V2"


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(TELEGRAM_API, json=payload, timeout=10)


def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    tg_user_id = message["from"]["id"]

    user_id = get_or_create_user(tg_user_id)

    state = get_user_state(user_id)

    if text.lower() == "cancel":
        clear_user_state(user_id)
        send_message(chat_id, "Cancelled.")
        return "ok", 200

    if state:
        return handle_stateful_input(
            user_id,
            chat_id,
            text,
            state
        )

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
            set_user_state(
                user_id,
                state="creating_task",
                draft={}
            )
            send_message(chat_id, "Send me the task description.")
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


def handle_stateful_input(user_id, chat_id, text, state):
    match state["state"]:
        case "creating_task":
            return handle_task_creation_text(
                user_id, chat_id, text, state["draft"]
            )
        case "creating_category":
            return handle_category_creation_text(
                user_id, chat_id, text
            )
    return "ok", 200


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

        case ("category", "select"):
            state = get_user_state(user_id)
            if not state or state["state"] != "creating_task":
                send_message(chat_id, "No active task creation.")
                return "ok", 200

            draft = state["draft"]
            from database import add_task
            add_task(
                user_id=user_id,
                title=draft["title"],
                due_at=draft.get("due"),
                category_id=draft.get("category_id")
            )

            clear_user_state(user_id)
            send_message(chat_id, "Task created ✅", reply_markup=main_menu_keyboard())
        case ("category", "create"):
            set_user_state(
                user_id,
                state="creating_category",
                draft={}
            )
            send_message(chat_id, "Send the category name:")

    return "ok", 200


def handle_task_creation_text(user_id, chat_id, text, draft):
    task = create_task_prompt(text)

    if not task.get("title"):
        send_message(chat_id, "I couldn't detect a task title. Please try again.")
        return "ok", 200

    draft["title"] = task["title"]

    due = task.get("due")
    if due:
        if due["type"] == "relative":
            time_expr = date_prompt(due["value"])["time_expression"]
            due_date = resolve_time_expression(time_expr, date.today())
            draft["due"] = due_date.isoformat() if due_date else None
        elif due["type"] == "absolute":
            draft["due"] = normalize_due_date(due["value"])
        else:
            draft["due"] = None
    else:
        draft["due"] = None

    category = assign_category_prompt(task["title"], user_id)

    # ✅ Auto-category succeeded → finalize immediately
    if category.get("category_id"):
        draft["category_id"] = category["category_id"]

        from database import add_task
        add_task(
            user_id=user_id,
            title=draft["title"],
            due_at=draft.get("due"),
            category_id=draft["category_id"]
        )

        clear_user_state(user_id)
        send_message(chat_id, "Task created ✅", reply_markup=main_menu_keyboard())
        return "ok", 200

    # ⏸ Auto-category failed → pause and wait for callback
    set_user_state(user_id, "creating_task", draft)

    send_message(
        chat_id,
        "I couldn’t confidently choose a category. Please select one:",
        reply_markup=category_selection_keyboard(user_id)
    )

    return "ok", 200

def handle_category_creation_text(user_id, chat_id, text):
    from database import create_category

    name = text.strip()
    if not name:
        send_message(chat_id, "Category name cannot be empty.")
        return "ok", 200

    create_category(user_id, name)


    clear_user_state(user_id) # clears state even in task creation process

    send_message(
        chat_id,
        f"Category “{name}” created ✅"
        #reply_markup=category_menu_keyboard() # no need to display category menu
    )

    return "ok", 200



