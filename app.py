from flask import Flask, request, render_template_string
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return render_template_string("<h1>Hello from Coach Daniel!</h1><p>The app is running.</p>")
