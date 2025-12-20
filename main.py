from flask import Flask, request, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
# APP functions
from database import *
from preprocessing import normalize_due_date, enforce_future_date, clean_chat_message
# Prompts
from prompt import decision_prompt, create_task_prompt, create_category_prompt, mark_as_done_prompt, chat_prompt

load_dotenv()

flask_key = os.getenv("TASKBOT_FLASK_SECRET_KEY")

# FLASK
app = Flask(__name__)
app.config['SECRET_KEY'] = flask_key
CORS(app)

# CREATE DATABASE ON FIRST RUN
init_db()


@app.route('/')
def index():
    return render_template("index.html")  # Load the dashboard page


@app.route('/prompt', methods=['GET'])
def prompt():
    user_prompt = request.args.get("text", "")
    user_id = get_or_create_user(
        telegram_user_id=123456,
        username="demo",
        first_name="Demo"
    )

    decision = decision_prompt(user_prompt)

    match decision["type"]:
        case "create_task":
            data = create_task_prompt(user_prompt, user_id)
            error = save_task_to_db(user_id, data)
            if error:
                return f"Task '{data['title']}' was not saved. {error}"
            return f"Task '{data['title']}' saved."

        case "mark_as_done":
            data = mark_as_done_prompt(user_prompt, user_id)

            if data["task_id"] is None:
                return data.get("message") or "I couldn't determine which task you meant."

            if not task_exists(user_id, task_id=data["task_id"]):
                return "That task does not exist."

            mark_task_done(user_id, data["task_id"])
            return f"Task {data['task_id']} marked as done."

        case "create_category":
            data = create_category_prompt(user_prompt, user_id)

            # 1. Validate extraction
            if data["category_name"] is None:
                return "Please specify a category name."

            # 2. Normalize
            name = data["category_name"].strip().lower()

            # 3. Authoritative DB check
            if category_exists(user_id, name):
                return f"Category '{name}' already exists."

            # 4. Create
            create_category(user_id, name)
            return f"Category '{name}' created."

        case _:
            response = chat_prompt(user_prompt,user_id)

            return response




def save_task_to_db(user_id, data):
    if not data.get("title"):
        raise ValueError("Task title is required")

    if task_exists(user_id, title=data["title"]):
        return "Already exists!"

    due_at = normalize_due_date(data.get("due_at"))
    due_at = enforce_future_date(due_at)

    add_task(
        user_id=user_id,
        title=data["title"].strip(),
        due_at=due_at,
        category_id=data.get("category_id"),
    )

def save_category_to_db(user_id, data):
    if not data.get("title"):
        raise ValueError("Task title is required")

    if task_exists(user_id, data["title"]):
        return "Already exists!"

    due_at = normalize_due_date(data.get("due_at"))
    due_at = enforce_future_date(due_at)

    add_task(
        user_id=user_id,
        title=data["title"].strip(),
        due_at=due_at,
        category_id=data.get("category_id"),
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8002)