import requests
import json
import datetime
from database import get_pending_tasks, get_categories
from preprocessing import *
import os
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("TASKBOT_PROMPT_ENDPOINT")

current_date = date.today().strftime("%A %d-%m-%Y")

def prompt_ai(user_prompt, system_prompt, context = None, model="gemma3:latest"):

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


def create_task_prompt(user_prompt):
    system_prompt = """You extract task information.

You MUST respond with a single valid JSON object.
Do NOT use Markdown, code blocks, or explanations.

Schema:
{
  "title": string,
  "due": null | {
    "type": "absolute" | "relative",
    "value": string
  }
}

Rules:
- title is REQUIRED
- Do NOT include category names in the title
- Do NOT include dates in the title
- Do NOT infer or invent information

Date rules:
- DO NOT calculate dates
- Relative dates: return exactly as mentioned
- Absolute dates: extract exactly
- If no date is mentioned, due must be null

Examples:
- "Buy milk"
  -> { "title": "Buy milk", "due": null }

- "Finish report next week"
  -> { "title": "Finish report", "due": { "type": "relative", "value": "next week" } }

Output ONLY the JSON object.
"""

    context = {
        "current_date": current_date
    }

    return prompt_ai(user_prompt, system_prompt, context)


def assign_category_prompt(title: str, user_id: int):
    system_prompt = """
You assign a category to a task.

You MUST respond with a single valid JSON object.
Do NOT include explanations outside JSON.

Schema:
{
  "category_id": number | null,
  "confidence": "high" | "medium" | "low"
}

Rules:
- Categories are provided in context
- Use category descriptions to infer meaning
- Choose the BEST matching category
- If no category clearly matches:
  - category_id MUST be null
  - confidence MUST be low
- Do NOT invent categories
- Do NOT guess when uncertain
"""

    categories = get_categories(user_id)

    context = {
        "task_title": title,
        "categories": [
            {
                "id": c["id"],
                "name": c["name"],
                "description": c.get("description")
            }
            for c in categories
        ]
    }

    return prompt_ai(title, system_prompt, context)


def mark_as_done_prompt(user_prompt,user_id):
    system_prompt = """
You are a task selector.

You MUST respond with a single valid JSON object.
Do NOT include explanations outside JSON.

Schema:
{
  "task_id": number | null,
  "message": string | null
}

Rules:
- Existing tasks are provided in the context
- If the user mentions a task ID explicitly, select that task
- Otherwise, match by task title (case-insensitive)
- If more than one task matches, task_id MUST be null
- If no task matches, task_id MUST be null
- Do NOT guess
- If task_id is null, include a short message explaining why

        """

    tasks = format_tasks_text(get_pending_tasks(user_id))

    context = {
        "current_date": current_date,
        "current_tasks": tasks,
        "has_tasks": len(tasks) > 0,
    }

    data = prompt_ai(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        context=context
    )

    return data


def chat_prompt(user_prompt, user_id):
    system_prompt = """
You are a task advisor. 
You provide insight to the user based on the tasks in the context and user's questions.

You MUST respond with a single valid JSON object.
Do NOT include explanations outside JSON.

Schema:
{
  "message": string
}

Rules:
- "message" MUST contain unstyled text.
- By default, include tasks with the nearest deadlines. Do no include task IDs. 
- If the user requests an action (e.g. remove, delete, mark, complete):
  - Inform the user that buttons are responsible for actions
  - you can only chat with user about his tasks


If there are no tasks in the context, reply exactly:
"There are no tasks created yet."

"""

    categories = get_categories(user_id)
    categories_by_id = {c["id"]: c["name"] for c in categories}
    tasks = get_pending_tasks(user_id)


    context = {
        "current_date": current_date,
        "current_tasks": format_tasks_text(tasks, categories_by_id),
        "has_tasks": len(tasks) > 0,
        "categories": format_categories_text(categories),
        "has_categories": len(categories) > 0,
    }

    data = prompt_ai(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        context=context
    )

    return data["message"]


def date_prompt(relative_date):
    system_prompt = """
    You are a time expression extractor.

Your job is to detect whether the user message contains a date or time reference.

You MUST respond with a single valid JSON object.
Do NOT include explanations or extra text.

Schema:
{
  "time_expression": string | null
}

Rules:
- Use ONLY the supported expressions listed below
- If no time reference is present, return null
- If the time reference is ambiguous or unsupported, return null
- Do NOT compute dates
- Do NOT invent new expressions

Supported expressions:
- today
- tomorrow
- next_week
- next_month
- next_year
- in_N_days
- in_N_weeks
- in_N_months
- start_of_next_week
- end_of_next_week
- start_of_month
- end_of_month

Examples:
- "buy milk tomorrow" → "tomorrow"
- "finish report in 3 days" → "in_3_days"
- "end of next week" → "end_of_next_week"
- "sometime later" → null
    """

    data = prompt_ai(
        user_prompt=relative_date,
        system_prompt=system_prompt,
        context=None
    )

    return data








