from datetime import datetime

import re
import json

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

def resolve_time_expression(expr: str | None, today: date) -> date | None:
    if not expr:
        return None

    if expr == "today":
        return today

    if expr == "tomorrow":
        return today + timedelta(days=1)

    if expr == "next_week":
        return today + timedelta(weeks=1)

    if expr == "next_month":
        return today + relativedelta(months=1)

    if expr == "next_year":
        return today + relativedelta(years=1)

    if expr.startswith("in_"):
        parts = expr.split("_")
        if len(parts) != 3:
            return None

        n = int(parts[1])
        unit = parts[2]

        if unit == "days":
            return today + timedelta(days=n)
        if unit == "weeks":
            return today + timedelta(weeks=n)
        if unit == "months":
            return today + relativedelta(months=n)

    if expr == "start_of_next_week":
        return today + relativedelta(weeks=1, weekday=0)

    if expr == "end_of_next_week":
        start = today + relativedelta(weeks=1, weekday=0)
        return start + timedelta(days=6)

    if expr == "start_of_month":
        return today.replace(day=1)

    if expr == "end_of_month":
        start = today.replace(day=1)
        return start + relativedelta(months=1) - timedelta(days=1)

    return None


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


def serialize_date(d: date | None) -> str | None:
    return d.isoformat() if d else None


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
