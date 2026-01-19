from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
# APP functions
from database import init_db

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


@app.route("/telegram/webhook", methods=["POST"])
def telegram_route():
    return telegram_webhook()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8002)