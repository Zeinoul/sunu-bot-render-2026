import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()
app = Flask(__name__)
CORS(app) # <-- Pour que ton site puisse appeler l'API

# --- CONFIG ---
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VERIFY_TOKEN = "sunu123" # Le même que sur Meta

# --- INIT FIREBASE ---
db = None
try:
    firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS")
    if firebase_creds_json:
        cred = credentials.Certificate(json.loads(firebase_creds_json))
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase connecté")
    else:
        print("⚠️ FIREBASE_CREDENTIALS manquant")
except Exception as e:
    print(f"❌ Erreur Firebase: {e}")

# --- INIT GEMINI ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini connecté")
except Exception as e:
    print(f"❌ Erreur Gemini: {e}")

def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "text": {"body": text}}
    try:
        requests.post(url, headers=headers, json=data)
    except Exception as e:
        print(f"Erreur envoi WA: {e}")

def ask_gemini(prompt):
    try:
        system_prompt = "Tu es l'assistante de sunu.com, un site e-commerce au Sénégal. Sois amicale, courte et réponds en français/wolof. Propose toujours d'aider pour les commandes."
        response = model.generate_content(system_prompt + "\n\nClient: " + prompt)
        return response.text
    except Exception as e:
        return "Désolée, j'ai un petit souci technique. Réessaie stp 🙏"

def handle_message(user_phone, text):
    if not db:
        send_whatsapp_message(user_phone, "Le bot est en maintenance.")
        return

    user_ref = db.collection('users').document(user_phone)
    user_doc = user_ref.get()

    # Si nouveau et qu'il a mis 77... on ajoute +221
    if not user_doc.exists and not user_phone.startswith('+'):
        if user_phone.startswith('221'):
            user_phone = '+' + user_phone
        else:
            user_phone = '+221' + user_phone
        user_ref = db.collection('users').document(user_phone)
        user_doc = user_ref.get()

    if not user_doc.exists:
        user_ref.set({'phone': user_phone, 'state': 'awaiting_phone'})
        send_whatsapp_message(user_phone, "🧕 Assistant sunu.com\nSalut! Je suis l'assistante sunu.com. Donne moi ton numéro WhatsApp pour commencer ex: 77 123 45 67")
        return

    state = user_doc.to_dict().get('state')

    if state == 'awaiting_phone':
        clean_phone = ''.join(filter(str.isdigit, text))
        if len(clean_phone) >= 9:
            full_phone = '+221' + clean_phone[-9:]
            user_ref.update({'phone': full_phone, 'state': 'active'})
            send_whatsapp_message(user_phone, f"✅ Merci! Numéro enregistré: {full_phone}\n\nQue puis-je faire pour toi?")
        else:
            send_whatsapp_message(user_phone, "❌ Numéro invalide. Ex: 77 123 45 67")
        return

    # Si actif, on répond avec Gemini
    response = ask_gemini(text)
    send_whatsapp_message(user_phone, response)

@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data.get("object") == "whatsapp_business_account":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "messages":
                    messages = change.get("value", {}).get("messages", [])
                    if messages:
                        msg = messages[0]
                        user_phone = msg["from"]
                        text = msg["text"]["body"]
                        handle_message(user_phone, text)
    return "ok", 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "sunu-bot-api is live"}), 200

if __name__ == '__main__':
    app.run(debug=True)
