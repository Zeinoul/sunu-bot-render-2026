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
ADMIN_WHATSAPP = "221779075432" # Ton numéro admin
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Init Firebase - VERSION SÉCURISÉE
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
else:
    print("⚠️ FIREBASE_CREDENTIALS non trouvée dans Render")

# Init Gemini - VERSION SÉCURISÉE
model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Gemini connecté")
    except Exception as e:
        print("⚠️ Gemini erreur:", e)
else:
    print("⚠️ GEMINI_API_KEY non trouvée dans Render")

# ========== FONCTIONS WHATSAPP ==========
def envoyer_whatsapp(numero, message):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("Erreur: Token WhatsApp ou Phone ID manquant")
        return

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
        print("WhatsApp envoyé:", r.status_code, r.text[:100])
    except Exception as e:
        print("Erreur WhatsApp:", e)

# ========== LOGIQUE CORE ==========
Ok je te montre exactement 👇

Dans ton `server.py` sur Render, cherche la fonction `def traiter_message`

### *1. SUPPRIME ÇA ENTIER :*

De :
def traiter_message(numero, message_user, produits=[]):
    if not model:
        return "Le bot est en maintenance."

    prompt = f"""
    Tu es l'assistante de SUNU.COM...
    ...
    """

    response = model.generate_content(prompt)
    texte = response.text.strip()

    if texte.startswith("{") and "action" in texte:
        try:
            commande = json.loads(texte)
            if commande.get("action") == "creer_commande":
                gestion_direct(commande)
                return "Parfait! Votre commande est enregistrée."
        except:
            pass

    return texte
Jusqu'à :
return texte
### *2. COLLE ÇA À LA PLACE :*
def traiter_message(numero, message_user, produits=[]):
    if not model:
        return "Le bot est en maintenance. Réessayez dans 5min."

    prompt = f"""
    Tu es l'assistante de SUNU.COM au Sénégal. Tu vends: {produits}
    Client: {numero} a dit: "{message_user}"

    Règles:
    1. Sois chaleureuse et courte. Parle en Wolof/Français.
    2. Si le client donne son numéro, remercie et demande son Nom et Adresse.
    3. Si le client donne Nom + Téléphone + Adresse, réponds UNIQUEMENT avec ce JSON:
    {{"action": "creer_commande", "nom": "...", "whatsapp": "...", "adresse": "...", "total": 0, "produits": "panier"}}
    4. Sinon réponds normalement pour vendre et aider.
    """
    try:
        response = model.generate_content(prompt)
        texte = response.text.strip()

        # Si Gemini renvoie du JSON = c'est une commande
        if texte.startswith("{") and "action" in texte:
            try:
                commande = json.loads(texte)
                if commande.get("action") == "creer_commande":
                    gestion_direct(commande)
                    return "Parfait! Votre commande est enregistrée. Vous allez recevoir un WhatsApp de confirmation."
            except Exception as e:
                print("JSON cassé:", e)
                return "Merci. Pouvez-vous me redonner votre nom et adresse complète svp?"
        
        return texte
    except Exception as e:
        print("Erreur Gemini:", e)
        return "Navrée, petite erreur technique. Pouvez-vous répéter svp?"
### *3. APRES AVOIR COLLE*
1.  `git add .` `git commit -m "fix bot"` `git push`
2.  Va sur Render > Manual Deploy > Clear build cache & deploy
3.  Attends 2min que ça redémarre

### *4. TEST*
Toi: 77 907 54 32
Bot: Merci! Quel est votre nom et adresse de livraison?
Toi: Aicha Ndiaye Parcelles Assainies
Bot: Parfait! Votre commande est enregistrée...
Et dans Firebase tu verras la commande apparaître dans `commandes`

Fais ça et envoie-moi la réponse du bot après le déploiement
    except Exception as e:
        print("Erreur Gemini:", e)
        return "Désolée, petite erreur. Pouvez-vous répéter?"

def gestion_direct(data):
    print("Commande reçue direct:", data)
    try:
        nom = data["nom"]
        whatsapp = data["whatsapp"]
        adresse = data["adresse"]
        total = data["total"]
        produits = data["produits"]

        # Sauvegarde Firebase
        if db:
            db.collection("commandes").add({
                "nom": nom, "whatsapp": whatsapp, "adresse": adresse,
                "total": total, "produits": produits, "statut": "nouvelle",
                "date": firestore.SERVER_TIMESTAMP
            })
            print("✅ Sauvegardé dans Firebase")

        # Message Client
        message_client = f"Salut {nom} 😊\nMerci pour ta commande SUNU COM!\n\nTotal: {total} FCFA\nAdresse: {adresse}\nLivraison 24H\nPaiement à la livraison."
        envoyer_whatsapp(whatsapp, message_client)

        # Alerte Admin
        message_admin = f"🚨 NOUVELLE COMMANDE\nNom: {nom}\nTel: {whatsapp}\nTotal: {total} FCFA\nAdresse: {adresse}\nProduits: {produits}"
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

        reponse = traiter_message(numero, texte)
        envoyer_whatsapp(numero, reponse)

    except Exception as e:
        print("Erreur webhook:", e)
    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "✅ Bot Sunu connecté + Firestore + Gemini", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
