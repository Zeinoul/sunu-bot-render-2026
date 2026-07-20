from flask import Flask, request
import os
import requests

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID") # On va l'ajouter après

# 1. VERIFICATION DU WEBHOOK POUR META
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Erreur de vérification", 403

# 2. RECEPTION DES MESSAGES
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Message reçu:", data)
    return "ok", 200

# 3. PAGE D'ACCUEIL POUR TEST
@app.route('/')
def home():
    return "Bot Sunu est en ligne ✅", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
