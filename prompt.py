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
}

Rules:
- Choose a CREATE intent ONLY if the user clearly asks to create or add something
- Queries, single words, listings, or vague references MUST be classified as "chat"
- Examples:
  - "categories" → chat
  - "show categories" → chat
  - "add category work" → create_category
  - "create category" → create_category
  - "buy milk" -> create_task
  - "apply for a job" -> create task
  - "remove / delete" -> mark_as_done 
  - "task" → chat
- Output JSON only
    """

    return prompt_ai(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        context={}
    )


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

def create_category_prompt(user_prompt,user_id):
    system_prompt = """
You are a category creation assistant.

You MUST respond with a single valid JSON object.
Do NOT include explanations outside JSON.

Schema:
{
  "category_name": string | null,
  "already_exists": true | false,
}

Rules:
- Extract the intended category name from the user message
- If the user did not clearly specify a category name, set category_name to null
- If a similar category already exists in the provided context:
  - Set already_exists = true
  - Use the existing category name
- Do NOT invent categories
- Do NOT modify existing categories
- Examples:
    - "Add category Project" -> "category_name": "Project"
    """

    categories = format_categories_text(get_categories(user_id))

    context = {
        "categories": categories,
        "has_categories": len(categories) > 0,
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

You MUST respond with a single valid JSON object.
Do NOT include explanations outside JSON.

Schema:
{
  "message": string
}

Rules:
- "message" MUST contain HTML-styled text.
- Only use these HTML tags: <b>, <i>. Use "\\n" as break line
- You are NOT allowed to create, remove, modify, or complete tasks or categories
- NEVER say or imply that a task was created, removed, deleted, updated, or marked as done
- If the user requests an action (e.g. remove, delete, mark, complete):
  - You MUST explain to the user that you cannot perform actions.
  - Inform the user about the supported actions

Supported actions are:
1. Create task with a category
2. Mark task as done
3. Create category
4. Chat about tasks

If there are no tasks, reply exactly:
"There are no tasks created yet."

Task listing rules:
- By default, include tasks with the nearest deadlines
"""

    categories = get_categories(user_id)
    categories_by_id = {c["id"]: c["name"] for c in categories}

    tasks = format_tasks_text(get_pending_tasks(user_id), categories_by_id)

    context = {
        "current_date": current_date,
        "current_tasks": tasks,
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








