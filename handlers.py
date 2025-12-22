from database import *
from datetime import date
from preprocessing import resolve_time_expression, normalize_due_date
from prompt import (
    decision_prompt,
    create_task_prompt,
    create_category_prompt,
    mark_as_done_prompt,
    chat_prompt,
    date_prompt
)

def handle_user_input(text: str, user_id: int) -> str:
    decision = decision_prompt(text)

    match decision["type"]:
        case "create_task":
            data = create_task_prompt(text, user_id)
            due = data.get("due")
            if not data.get("title"):
                return "I couldn't determine the task title."

            if task_exists(user_id, title=data["title"]):
                return "That task already exists."

            if due["type"] == "relative":
                time_expr = date_prompt(due["value"])["time_expression"]
                due_date = resolve_time_expression(time_expr, date.today())
                due_at = due_date.isoformat() if due_date else None
            elif due["type"] == "absolute":
                due_at = normalize_due_date(due["value"])
            else:
                due_at = None

            add_task(
                user_id=user_id,
                title=data["title"].strip(),
                due_at=due_at,
                category_id=data.get("category_id"),
            )

            return f"Task '{data['title']}' saved."

        case "mark_as_done":
            data = mark_as_done_prompt(text, user_id)

            if data["task_id"] is None:
                return data.get("message") or "I couldn't determine which task you meant."

            if not task_exists(user_id, task_id=data["task_id"]):
                return "That task does not exist."

            mark_task_done(user_id, data["task_id"])
            return f"Task {data['task_id']} marked as done."

        case "create_category":
            data = create_category_prompt(text, user_id)

            if data["category_name"] is None:
                return "Please specify a category name."

            name = data["category_name"].strip().lower()

            if category_exists(user_id, name):
                return f"Category '{name}' already exists."

            create_category(user_id, name)
            return f"Category '{name}' created."

        case _:
            return chat_prompt(text, user_id)
