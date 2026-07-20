import os
from flask import Flask, request
import requests

app = Flask(__name__)

VERIFY_TOKEN = "sunu2026"
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")

@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Erreur de vérification", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print(data) # pour voir dans les logs Render
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))