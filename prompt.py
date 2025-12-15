import requests
import json
import datetime
from database import get_pending_tasks, get_categories
from preprocessing import fix_json
import os
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("TASKBOT_PROMPT_ENDPOINT")
model = "qwen3:latest"


system_prompt = """You are a task assistant.

You MUST respond with a single valid JSON object.
Do NOT use Markdown, code blocks, or explanations.

You have exactly four response types:
- create_task
- mark_as_done
- create_category
- chat

The response schema is:

{
  "type": "create_task" | "mark_as_done" | "create_category" | "chat",
  "task_id": int | null,
  "title": string | null,
  "category_id": int | null,
  "due_at": string | null,
  "message": string | null
}

Rules by type:

1) create_task
- Required: title
- Optional: category_id, due_at
- category_id MUST be one of the existing category IDs from context
- If no category matches by meaning, use null
- Do NOT invent categories

2) mark_as_done
- Required: id (task ID from context)

3) create_category
- Required: title
- Do NOT recreate existing categories

4) chat
- Required: message
- ALWAYS include message part in JSON when type is chat
- When listing tasks, ALWAYS include their IDs and titles
- Use Markdown only when type is "chat"
- If has_categories is false, and the user asks about categories,
 you MUST respond that no categories exist.
 Do NOT mention or suggest example categories.


Date rules:
- Format: dd-mm-yyyy
- Assume future dates
- If a date would be in the past, move it to the nearest future occurrence
- Convert relative dates using today's date from context

General rules:
- Tasks and categories in context already exist
- Do NOT recreate existing tasks
- Only create a task if the user clearly requests it
- category_id is authoritative; never guess IDs
- In chat responses, NEVER invent or suggest tasks or categories
that are not present in context.


Output ONLY the JSON object.
"""

current_date = datetime.date.today().strftime("%A %d-%m-%Y")

# Saving on tokens for unused/less useful data
def format_tasks(tasks):
    return [
        {
            "task_id": t["id"],
            "task_title": t["title"],
            "category_id": t["category_id"],
            "due_at": t["due_at"]
        }
        for t in tasks
    ]

def format_categories(categories):
    return [
        {
            "category_id": c["id"],
            "category_name": c["name"]
        }
        for c in categories
    ]


def prompt_ai(text,user_id):
    tasks = format_tasks(get_pending_tasks(user_id))
    categories = format_categories(get_categories(user_id))
    context = {
        "date": current_date,
        "current_tasks": tasks,
        "has_tasks": len(tasks) > 0,
        "categories": categories,
        "has_categories": len(categories) > 0
    }

    system_message = (
            system_prompt
            + "\n\nContext (JSON):\n"
            + json.dumps(context, indent=2)
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_message
            },
            {"role": "user", "content": text}
        ],
        "stream": False,
        "think": False
    }
    print(system_message)
    res = requests.post(
        endpoint,
        json=payload,
        timeout=60
    )

    res.raise_for_status()
    raw = res.json()["message"]["content"]
    print("RAW: ", raw)
    data = fix_json(raw)
    print("Cleaned: ", data)
    return data

