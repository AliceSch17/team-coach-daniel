from flask import Flask, request, jsonify, render_template, session
import openai
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'replace-this-with-a-secret-key'

# Google Sheets setup
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get('SERVICE_ACCOUNT_JSON'))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client_gsheets = gspread.authorize(creds)
sheet = client_gsheets.open_by_key(os.environ.get("SHEET_ID")).sheet1


# Chat structure
coach_prompt = """
You are a friendly and wise team coach named Daniel. You are helping students create a team charter. 
The team charter includes: Project Description, Team Goals, Team Roles, and Team Norms 
(communication, behavior, and task tracking). 

Ask only one question at a time. Wait for their response before continuing. If students are unsure, help them brainstorm. 
Summarize at the end. Always stay friendly, supportive, and structured.
"""

steps = ["project", "goals", "roles", "norms", "wrap"]

step_questions = {
    "project": "What is your project about?",
    "goals": "What are your goals for this project? Any assignment or team goals?",
    "roles": "Who is responsible for which tasks in the team?",
    "norms": "What norms will your team follow? (Communication, behavior, and task tracking)",
    "wrap": "That's it! Let me summarize your team charter."
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start():
    print("Session started")
    session.clear()
    session['step_index'] = 0
    session['messages'] = [
        {"role": "system", "content": coach_prompt},
    ]
    session['responses'] = {}
    return jsonify({"message": step_questions["project"]})


@app.route("/message", methods=["POST"])
def message():
    try:
        data = request.get_json()
        user_input = data.get("message", "").strip()
        print(f"User input: {user_input}")

        if not user_input:
            return jsonify({"message": "Please enter a response."})

        step_index = session.get('step_index', 0)
        current_step = steps[step_index]
        session['responses'][current_step] = user_input

        # Add user input to message history
        session['messages'].append({"role": "user", "content": user_input})

        if current_step == "wrap":
            summary = session['responses']
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [
                timestamp,
                summary.get("project", ""),
                summary.get("goals", ""),
                summary.get("roles", ""),
                summary.get("norms", "")
            ]
            sheet.append_row(row)
            return jsonify({
                "message": "Here is your completed team charter!",
                "summary": summary
            })

        # Move to next step
        session['step_index'] += 1
        next_step = steps[session['step_index']]

        # Add next prompt to messages
        session['messages'].append({"role": "assistant", "content": step_questions[next_step]})

        # Call GPT-4
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=session['messages'],
            temperature=0.7,
            max_tokens=300
            )
        reply = response['choices'][0]['message']['content']
        session['messages'].append({"role": "assistant", "content": reply})

        return jsonify({"message": reply})

    except Exception as e:
        print(f"Error in /message: {e}")
        return jsonify({"message": f"Coach Daniel encountered an error: {str(e)}"}), 500
