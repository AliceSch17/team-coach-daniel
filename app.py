from flask import Flask, request, jsonify, render_template, session
import openai
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'

openai.api_key = os.environ.get("OPENAI_API_KEY")

# Google Sheets setup
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get('SERVICE_ACCOUNT_JSON'))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(os.environ.get("SHEET_ID")).sheet1

# Ordered steps
steps = ["project", "goals", "roles", "norms", "wrap"]

# Core prompt for Coach Daniel (system-level)
coach_prompt = """
You are a friendly and wise team coach named Daniel. You are helping students set up a team charter. 
The team charter includes: 
- Project Description
- Team Goals
- Team Roles
- Team Norms (communication, behavior, task tracking)

Ask only one question at a time. After each answer, wait for the student reply before moving on. 
Your goal is to guide the team to complete their charter with thoughtful discussion. 
If they’re unsure about something (like goals or roles), help them brainstorm options.
End by summarizing their responses and encouraging them to revisit their charter during the project.
"""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    session.clear()
    session['step_index'] = 0
    session['responses'] = {}
    session['messages'] = [{"role": "system", "content": coach_prompt}]
    return jsonify({"message": "Hi team! I’m Daniel, your team coach. Let’s create your team charter. First — what is your project about?"})

@app.route("/message", methods=["POST"])
def message():
    data = request.get_json()
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"message": "Please enter a response to continue."})

    # Store response to current step
    step_index = session.get("step_index", 0)
    current_step = steps[step_index] if step_index < len(steps) else "wrap"
    session['responses'][current_step] = user_input

    # Append user input to chat history
    session['messages'].append({"role": "user", "content": user_input})

    # If we’re at the last step, generate a wrap-up message and summary
    if current_step == "wrap":
        summary = session['responses']
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            now,
            summary.get("project", ""),
            summary.get("goals", ""),
            summary.get("roles", ""),
            summary.get("norms", "")
        ]
        sheet.append_row(row)
        return jsonify({
            "message": "Nice work! Here’s your team charter summary:",
            "summary": summary
        })

    # Advance to next step
    session['step_index'] += 1
    next_step = steps[session['step_index']] if session['step_index'] < len(steps) else "wrap"

    step_to_question = {
        "goals": "What are your goals for this project? Any team goals or assignment outcomes?",
        "roles": "Who is doing what in the team? Assign any known roles or responsibilities.",
        "norms": "What team norms do you want to follow? (How will you communicate, treat one another, keep track of work?)",
        "wrap": "That’s everything! Let me wrap this up."
    }

    next_question = step_to_question.get(next_step, "What’s next for your team?")

    # Add coach message via GPT-4
    session['messages'].append({"role": "assistant", "content": next_question})

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=session['messages'],
        temperature=0.7,
        max_tokens=300
    )

    reply = response['choices'][0]['message']['content']
    session['messages'].append({"role": "assistant", "content": reply})

    return jsonify({"message": reply})
