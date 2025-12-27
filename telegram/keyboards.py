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
            [{"text": "🗑 Hide category", "callback_data": "category:hide"}],
            [{"text": "⬅️ Back", "callback_data": "menu:main"}],
        ]
    }
