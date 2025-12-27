from flask import Flask, request, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import os
# APP functions
from database import init_db, get_or_create_user
# Managing input
from handlers.chat import chat_prompt

# Telegram
from telegram.webhook import telegram_webhook

# ENV VARIABLES
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TASKBOT_TELEGRAM_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
FLASK_KEY = os.getenv("TASKBOT_FLASK_SECRET_KEY")

# FLASK
app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_KEY
CORS(app)

# CREATE DATABASE ON FIRST RUN
init_db()


@app.route('/')
def index():
    return render_template("index.html")  # Load the dashboard page


@app.route("/telegram/webhook", methods=["POST"])
def telegram_route():
    return telegram_webhook()


@app.route('/prompt', methods=['GET'])
def prompt():

    text = request.args.get("text", "")
    user_id = get_or_create_user(
        telegram_user_id=123456,
        username="demo",
        first_name="Demo"
    )

    return chat_prompt(text, user_id)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8002)