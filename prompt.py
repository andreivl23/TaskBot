import requests
import json
import datetime
from database import get_pending_tasks, get_categories
from preprocessing import fix_json, format_categories, format_tasks
import os
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("TASKBOT_PROMPT_ENDPOINT")

current_date = datetime.date.today().strftime("%A %d-%m-%Y")

def prompt_ai(user_prompt, system_prompt, context = None, model="qwen3:latest"):

    system_message = system_prompt

    if context is not None:
        system_message += (
            "\n\nContext (JSON):\n"
            + json.dumps(
                context if context else {"note": "No additional context provided"},
                indent=2
            )
        )

    print(system_message)  # final system message

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_message
            },
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "think": False
    }

    res = requests.post(
        endpoint,
        json=payload,
        timeout=60
    )

    res.raise_for_status()
    raw = res.json()["message"]["content"]
    print(raw) # for debugging
    llm_json = fix_json(raw) # Fixing json in a Markdown code block quotes
    return llm_json


def decision_prompt(user_prompt):
    system_prompt = """
    You are an intent classifier.

    Return a single JSON object with this schema:

    {
      "type": "create_task" | "mark_as_done" | "create_category" | "chat",
      "message": "string"
    }

    Rules:
    - Classify the user's intent only
    - In the message field include type and confidence
    - Do NOT extract task data
    - Do NOT explain
    - Output JSON only
    """

    return prompt_ai(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        context={}
    )


def create_task_prompt(user_prompt,user_id):
    system_prompt = """Your job is to prepare a JSON for creating a task.

    You MUST respond with a single valid JSON object.
    Do NOT use Markdown, code blocks, or explanations.

    The response schema is:

    {
      "title": string,
      "category_id": int | null,
      "due_at": string | null,
    }

    Rules:

    - Required: title
    - Optional: category_id, due_at
    - category_id MUST be one of the existing category IDs from context
    - If no existing category matches, use null
    - Do NOT invent categories

    Date rules:
    - Format: dd-mm-yyyy
    - Assume future dates
    - If a date would be in the past, move it to the nearest future occurrence
    - Convert relative dates using today's date from context

    General rules:
    - Do NOT recreate existing tasks

    Output ONLY the JSON object.
    """

    tasks = format_tasks(get_pending_tasks(user_id))
    categories = format_categories(get_categories(user_id))
    context = {
        "date": current_date,
        "current_tasks": tasks,
        "categories": categories,
    }

    llm_json = prompt_ai(user_prompt,system_prompt,context)

    return llm_json

def mark_as_done_prompt(user_prompt,user_id):
    return "mark as done: " + user_prompt

def create_category_prompt(user_prompt,user_id):
    return "create category: " + user_prompt

def chat_prompt(user_prompt, user_id):
    system_prompt = """
You are a task advisor.

You MUST respond with a single valid JSON object.
Do NOT include explanations outside JSON.

Schema:
{
  "message": string
}

Rules:
- "message" MUST contain Markdown-formatted text
- Use the context to guide the user
- If there are no tasks and no categories, reply exactly:
  "There are no tasks or categories created yet."
- By default, include ONLY 3 tasks that have a deadline soon. 
- If user wants to see many tasks, use table format
"""

    tasks = format_tasks(get_pending_tasks(user_id))
    categories = format_categories(get_categories(user_id))

    context = {
        "date": current_date,
        "current_tasks": tasks,
        "has_tasks": len(tasks) > 0,
        "categories": categories,
        "has_categories": len(categories) > 0,
    }

    data = prompt_ai(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        context=context
    )

    return data["message"]








