import os
from dotenv import load_dotenv
load_dotenv()

import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ADMIN_WHATSAPP = os.getenv("ADMIN_WHATSAPP", "221779075432")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

clients = {}

# Init Firebase
db = None
firebase_creds = os.getenv("FIREBASE_CREDENTIALS")
if firebase_creds:
    try:
        cred_dict = json.loads(firebase_creds)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase connecté")
    except Exception as e:
        print("⚠️ Firebase erreur:", e)

# Init Gemini
model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Gemini connecté")
    except Exception as e:
        print("⚠️ Gemini erreur:", e)

def envoyer_whatsapp(numero, message):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID: return
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": message}}
    try: requests.post(url, headers=headers, json=data, timeout=10)
    except Exception as e: print("Erreur WhatsApp:", e)

def gestion_direct(data):
    try:
        if db: db.collection("commandes").add({**data, "statut": "nouvelle", "date": firestore.SERVER_TIMESTAMP})
        message_client = f"Salut {data['nom']} 😊\nMerci pour ta commande SUNU COM!\nAdresse: {data['adresse']}\nLivraison 24H\nPaiement à la livraison."
        envoyer_whatsapp(data['whatsapp'], message_client)
        message_admin = f"🚨 NOUVELLE COMMANDE\nNom: {data['nom']}\nTel: {data['whatsapp']}\nAdresse: {data['adresse']}"
        envoyer_whatsapp(ADMIN_WHATSAPP, message_admin)
    except Exception as e: print("Erreur gestion:", e)

def traiter_message(numero, message_user, produits=[]):
    if numero not in clients: clients[numero] = {"etape": "accueil", "historique": []}
    clients[numero]["historique"].append(f"Client: {message_user}")
    if not model: return "Le bot est en maintenance."

    if clients[numero]["etape"] == "commande" and len(message_user.split()) >= 3:
        clients[numero]["etape"] = "accueil"
        commande = {"nom": message_user.split(" à ")[0].split(" mon adresse ")[0], "adresse": message_user.split(" à ")[-1].split(" mon adresse ")[-1], "whatsapp": numero, "total": 0, "produits": "panier"}
        gestion_direct(commande)
        return "Parfait! Votre commande est enregistrée ✅\nLivraison 24H. Paiement à la livraison."

    produits_liste = ", ".join([f"{p['nom']} - {int(p['prix']):,} FCFA" for p in produits[:20]]) if produits else "Catalogue SUNU COM"

    prompt = f"""Tu es SUNU ASSISTANT, vendeur officiel de SUNU COM au Sénégal.
    RÈGLE 1: CONSEILLER D'ABORD. Propose produits si client cherche.
    RÈGLE 2: Si client dit "je prends" → Réponds: COMMANDE_OK
    STYLE: Chaleureux, français simple, max 5 phrases. Emojis 😊
    PRODUITS: {produits_liste}
    HISTORIQUE: {clients[numero]["historique"][-4:]}
    MESSAGE CLIENT: {message_user}"""
    try:
        response = model.generate_content(prompt)
        texte = response.text.strip()
        if "COMMANDE_OK" in texte:
            clients[numero]["etape"] = "commande"
            return "Super choix! 😊 Pour finaliser, donne moi ton Nom complet et ton Adresse de livraison"
        clients[numero]["historique"].append(f"Bot: {texte}")
        return texte
    except Exception as e:
        print("Erreur Gemini:", e)
        return "Désolé petite erreur. Que puis-je faire pour vous?"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    reponse = traiter_message(data.get("numero"), data.get("message"), data.get("produits", []))
    return jsonify({"reponse": reponse})

@app.route("/", methods=["GET"])
def home():
    return "✅ Bot SUNU.COM connecté sur INTERNET", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
