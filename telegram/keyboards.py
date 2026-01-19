from database import get_categories


def main_menu_keyboard():
    return {
        "keyboard": [
            ["➕ Add task", "📂 Categories"],
            ["✅ Mark task done", "📋 Show tasks"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }


def task_list_keyboard(tasks):
    return {
        "inline_keyboard": [
            [
                {
                    "text": f"✅ {t['title']}",
                    "callback_data": f"task:done:{t['id']}"
                }
            ]
            for t in tasks
        ]
    }

def category_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "➕ Create category", "callback_data": "category:create"}],
            [{"text": "✏️ Rename category", "callback_data": "category:rename"}],
            [{"text": "🗑 Hide category", "callback_data": "category:hide"}]
        ]
    }

def category_selection_keyboard(user_id):
    categories = get_categories(user_id)

    keyboard = []

    row = []
    for c in categories:
        row.append({
            "text": c["name"],
            "callback_data": f"category:select:{c['id']}"
        })

        # 2 buttons per row
        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # Utility buttons
    keyboard.append([
        {"text": "➕ Create category", "callback_data": "category:create"}
    ])
    keyboard.append([
        {"text": "❌ No category", "callback_data": "category:select:none"}
    ])

    return {"inline_keyboard": keyboard}



