from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", current_year=datetime.now().year)

@app.route("/about")
def about():
    return render_template("about.html", current_year=datetime.now().year)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

# Old command: gunicorn your_application.wsgi