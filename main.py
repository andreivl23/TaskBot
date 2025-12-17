from flask import Flask, request, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
# APP functions
from database import init_db, get_or_create_user, add_task, mark_task_done, create_category, get_pending_tasks
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
            save_task_to_db(user_id, data)
            return f"Task '{data['title']}' saved."

        case "mark_as_done":
            data = mark_as_done_prompt(user_prompt, user_id)
            mark_task_done(user_id, data["task_id"])
            return f"Task {data['task_id']} marked as done."

        case "create_category":
            data = create_category_prompt(user_prompt, user_id)
            create_category(user_id, data["title"])
            return f"Category '{data['title']}' created."

        case _:
            response = chat_prompt(user_prompt,user_id)

            return response




def save_task_to_db(user_id, data):
    if not data.get("title"):
        raise ValueError("Task title is required")

    due_at = normalize_due_date(data.get("due_at"))
    due_at = enforce_future_date(due_at)

    add_task(
        user_id=user_id,
        title=data["title"].strip(),
        due_at=due_at,
        category_id=data.get("category_id"),
    )

    return


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8002)