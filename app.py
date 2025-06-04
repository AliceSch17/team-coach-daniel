from flask import Flask, request, jsonify, render_template, session
import openai
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a real secret key in production

# Load API key and credentials from environment
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Google Sheets setup
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get('SERVICE_ACCOUNT_JSON'))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(os.environ.get("SHEET_ID")).sheet1

# Structured prompts and steps
steps = ["project", "goals", "roles", "norms", "wrap"]
prompts = {
    "intro": "Hi team! I’m Daniel, your friendly and wise team coach. I’m here to help you create your team charter — a tool that helps teams work better together. Let's start! What is your team name?",
    "project": "Great! Can you briefly describe your project?",
    "goals": "What are the specific assignment goals and team goals you'd like to achieve?",
    "roles": "Who will take on which task for this project? It’s OK if you’re not 100% sure yet.",
    "norms": "Let’s talk about team norms. How will you communicate? Treat one another? Track tasks?",
    "wrap": "Nice work! Here's your summary. You can revisit this charter later as your project evolves."
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    session.clear()
    session['step'] = 'intro'
    session['responses'] = {}
    return jsonify({"message": prompts["intro"]})

@app.route("/message", methods=["POST"])
def message():
    data = request.get_json()
    text = data.get("message", "").strip()

    if 'step' not in session:
        return jsonify({"message": prompts["intro"]})

    if session['step'] == 'intro':
        session['responses']['Team Name'] = text
        session['step'] = 'project'
        return jsonify({"message": prompts['project']})

    elif session['step'] == 'project':
        session['responses']['Project Description'] = text
        session['step'] = 'goals'
        return jsonify({"message": prompts['goals']})

    elif session['step'] == 'goals':
        session['responses']['Team Goals'] = text
        session['step'] = 'roles'
        return jsonify({"message": prompts['roles']})

    elif session['step'] == 'roles':
        session['responses']['Team Roles'] = text
        session['step'] = 'norms'
        return jsonify({"message": prompts['norms']})

    elif session['step'] == 'norms':
        session['responses']['Team Norms'] = text
        session['step'] = 'wrap'

        # Save to Google Sheet
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            now,
            session['responses'].get("Team Name", ""),
            session['responses'].get("Project Description", ""),
            session['responses'].get("Team Goals", ""),
            session['responses'].get("Team Roles", ""),
            session['responses'].get("Team Norms", "")
        ]
        sheet.append_row(row)
        return jsonify({
            "message": prompts['wrap'],
            "summary": session['responses']
        })

    else:
        return jsonify({"message": "Thanks! You’ve completed the team charter."})
