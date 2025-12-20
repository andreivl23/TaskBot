from datetime import date, datetime
import re
import json

# Keeping the dates consistent
def normalize_due_date(due_at: str | None) -> str | None:
    if not due_at:
        return None

    # Accept dd-mm-yyyy
    try:
        dt = datetime.strptime(due_at, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass

    # Accept yyyy-mm-dd (already normalized)
    try:
        dt = datetime.strptime(due_at, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass

    raise ValueError(f"Invalid due_at format: {due_at}")

def enforce_future_date(due_at_iso: str | None) -> str | None:
    if not due_at_iso:
        return None

    due_date = datetime.strptime(due_at_iso, "%Y-%m-%d").date()
    today = date.today()

    # If date is in the past, assume next year
    if due_date < today:
        try:
            due_date = due_date.replace(year=due_date.year + 1)
        except ValueError:
            # Handles Feb 29 edge case
            due_date = due_date.replace(month=3, day=1, year=due_date.year + 1)

    return due_date.strftime("%Y-%m-%d")

# Remove Markdown mention
def clean_chat_message(text: str) -> str:
    text = text.strip()

    # Remove leading "Markdown" heading variants
    text = re.sub(
        r"^(#{1,6}\s*)?markdown\s*\n+",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text

def fix_json(raw):
    # Remove ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"```(?:json)?\n(.*?)```", r"\1", raw, flags=re.DOTALL)
    data = json.loads(cleaned)
    return data

# Saving on tokens for unused/less useful data
def format_tasks(tasks, categories_by_id=None):
    if categories_by_id:
        return [
            {
                "task_id": t["id"],
                "title": t["title"],
                "category": (
                    {
                        "cat_id": t["category_id"],
                        "name": categories_by_id.get(t["category_id"])
                    }
                    if t["category_id"] is not None
                    else None
                ),
                "due_at": t["due_at"]
            }
            for t in tasks
        ]
    else:
        return [
            {
                "task_id": t["id"],
                "title": t["title"],
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


def format_tasks_text(tasks, categories_by_id=None):
    if not tasks:
        return "No tasks."

    lines = []
    for t in tasks:
        parts = [f"Task {t['id']}: {t['title']}"]

        if categories_by_id and t['category_id']:
            cat_name = categories_by_id.get(t['category_id'])
            parts.append(f"category: {cat_name}")

        if t['due_at']:
            parts.append(f"due: {t['due_at']}")
        else: parts.append(f"This is a note.")

        lines.append(", ".join(parts))

    return " \n ".join(lines)


def format_categories_text(categories):
    if not categories:
        return "No categories."

    return " \n ".join([f"Category {c['id']}: {c['name']}" for c in categories])
