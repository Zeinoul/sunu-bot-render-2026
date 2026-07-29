import os
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# ========== CONFIG ==========
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ADMIN_WHATSAPP = "221779075432"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Init Firebase - avec try pour ne pas crasher
try:
    cred = credentials.Certificate(json.loads(os.getenv("FIREBASE_CREDENTIALS")))
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase connecté")
except Exception as e:
    db = None
    print("⚠️ Firebase erreur:", e)

# Init Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ========== FONCTIONS WHATSAPP ==========
def envoyer_whatsapp(numero, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": f"221{numero}" if not numero.startswith("221") else numero,
        "type": "text",
        "text": {"body": message}
    }
    try:
        r = requests.post(url, headers=headers, json=data, timeout=10)
        print("WhatsApp envoyé:", r.status_code)
    except Exception as e:
        print("Erreur WhatsApp:", e)

# ========== LOGIQUE CORE ==========
def traiter_message(numero, message_user, produits=[]):
    """Cette fonction remplace /chat pour éviter l'appel localhost"""
    prompt = f"""
    Tu es l'assistante de SUNU.COM au Sénégal. Tu vends ça: {produits}
    Client: {numero} a dit: "{message_user}"

    Règles:
    1. Sois chaleureuse et courte. En Wolof/Français.
    2. Si le client veut commander, demande: Nom + Téléphone + Adresse.
    3. Quand tu as Nom + Tel + Adresse, réponds UNIQUEMENT avec ce JSON:
    {{"action": "creer_commande", "nom": "...", "whatsapp": "...", "adresse": "...", "total":..., "produits":...}}
    4. Sinon réponds normalement pour vendre.
    """
    try:
        response = model.generate_content(prompt)
        texte = response.text.strip()

        if texte.startswith("{"):
            commande = json.loads(texte)
            if commande.get("action") == "creer_commande":
                gestion_direct(commande)
                return "Parfait! Votre commande est enregistrée. Vous allez recevoir un WhatsApp de confirmation."
        return texte
    except Exception as e:
        print("Erreur Gemini:", e)
        return "Désolée, petite erreur. Pouvez-vous répéter?"

def gestion_direct(data):
    print("Commande reçue direct:", data)
    try:
        nom = data["nom"]; whatsapp = data["whatsapp"]; adresse = data["adresse"]; total = data["total"]; produits = data["produits"]

        if db:
            db.collection("commandes").add({
                "nom": nom, "whatsapp": whatsapp, "adresse": adresse,
                "total": total, "produits": produits, "statut": "nouvelle"
            })

        message_client = f"Salut {nom} 😊\nMerci pour ta commande SUNU COM!\n\nTotal: {total} FCFA\nAdresse: {adresse}\nLivraison 24H\nPaiement à la livraison."
        envoyer_whatsapp(whatsapp, message_client)

        message_admin = f"🚨 NOUVELLE COMMANDE\nNom: {nom}\nTel: {whatsapp}\nTotal: {total} FCFA\nAdresse: {adresse}"
        envoyer_whatsapp(ADMIN_WHATSAPP, message_admin)

        return {"status": "ok"}
    except Exception as e:
        print("Erreur gestion:", e)
        return {"status": "erreur", "details": str(e)}

# ========== ROUTES ==========
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    reponse = traiter_message(data.get("numero"), data.get("message"), data.get("produits", []))
    return jsonify({"reponse": reponse})

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return request.args.get("hub.challenge")

    data = request.json
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = message["from"]
        texte = message["text"]["body"]

        # CORRECTION ICI : Appel direct au lieu de requests.post
        reponse = traiter_message(numero, texte)
        envoyer_whatsapp(numero, reponse)

    except Exception as e:
        print("Erreur webhook:", e)
    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "✅ Bot Gestionnaire Sunu connecté + Firestore", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port) je parle de ça c'est le server ou gestionnaire ?
