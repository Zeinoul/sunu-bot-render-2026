import os, json, threading, time
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)
CORS(app)

VERIFY_TOKEN = "sunu2026"
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")

# 1. CONNEXION FIREBASE POUR ECOUTER COMMANDES
print("🔄 Connexion Firebase...")
database_url = os.environ.get('FIREBASE_URL')
cred_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
cred_dict = json.loads(cred_json)

cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred, {'databaseURL': database_url})
print("✅ Bot Gestionnaire Sunu connecté")

def gerer_nouvelle_commande(event):
    if event.data:
        print(f"📦 Nouvelle commande reçue: {event.data}")
        # ICI TU PEUX ENVOYER UN WHATSAPP AU CLIENT

def lancer_ecoute_firebase():
    ref = db.reference('/commandes')
    ref.listen(gerer_nouvelle_commande)
    while True: time.sleep(10)

# Lance l'écoute Firebase dans un thread séparé
threading.Thread(target=lancer_ecoute_firebase, daemon=True).start()

# 2. WEBHOOK WHATSAPP
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Erreur de vérification", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Message WhatsApp reçu:", data)
    return "ok", 200

# 3. ROUTE POUR LE SITE SUNU.COM
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').lower()
    numero = data.get('numero', '')
    produits = data.get('produits', [])

    print(f"Message du site: {message} de {numero}")
    reponse = "Désolé je n'ai pas compris. Tape 'aide'"

    if "bonjour" in message or "salut" in message:
        reponse = "Salut ! Bienvenue sur SUNU.COM 🇸🇳 Comment je peux t'aider ?"
    
    elif "prix" in message:
        for p in produits:
            if p['nom'].lower() in message:
                reponse = f"{p['nom']} coûte {int(p['prix']):,} FCFA. Tu veux commander ?"
                break
        else:
            reponse = f"On a {len(produits)} produits. Donne moi le nom."

    elif "livraison" in message:
        reponse = "Livraison 24H à Dakar. 48H régions. Paiement à la livraison."
    
    elif "commander" in message:
        reponse = f"Super ! Donne moi l'adresse de livraison et je passe ta commande."

    return jsonify({"reponse": reponse})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
