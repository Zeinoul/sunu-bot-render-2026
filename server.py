import os
import json
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)
CORS(app)
VERIFY_TOKEN = "sunu2026"

print("🔄 Connexion Firebase...")
database_url = os.environ.get('FIREBASE_URL')
cred_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')

if not database_url or not cred_json:
    print("❌ ERREUR: FIREBASE_URL ou GOOGLE_CREDENTIALS_JSON manquant")
else:
    cred_dict = json.loads(cred_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        'databaseURL': database_url
    })
    print("✅ Bot Gestionnaire Sunu connecté")
    print("🤖 En écoute: Commandes, Stock, Factures, Livraisons...")

def gerer_nouvelle_commande(event):
    if event.data:
        print(f"📦 Nouvelle commande reçue: {event.data}")

def lancer_ecoute_firebase():
    ref = db.reference('/commandes')
    ref.listen(gerer_nouvelle_commande)
    while True:
        time.sleep(10)

# Lancer l'écoute Firebase en arrière-plan
threading.Thread(target=lancer_ecoute_firebase, daemon=True).start()

@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    else:
        return "Erreur de vérification", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    return "ok", 200

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').lower()
    produits = data.get('produits', [])
    
    reponse = "Je n'ai pas compris. Tape 'aide' pour voir ce que je peux faire."
    
    if "bonjour" in message or "salut" in message:
        reponse = "Salut ! Bienvenue sur SUNU.COM 🇸🇳 Comment je peux t'aider aujourd'hui ?"
    
    elif "prix" in message:
        reponse = "Donne moi le nom du produit et je te donne le prix"
        for p in produits:
            if p['nom'].lower() in message:
                reponse = f"{p['nom']} coûte {int(p['prix']):,} FCFA. Tu veux commander ?"
                break
    
    elif "livraison" in message:
        reponse = "Livraison 24H à Dakar. 48H pour les régions. Frais à partir de 1500 FCFA"
    
    elif "commander" in message:
        reponse = "Parfait ! Donne moi ton nom, adresse et numéro pour valider ta commande."
    
    elif "aide" in message:
        reponse = "Je peux t'aider pour: prix des produits, livraison, passer commande. Que veux-tu ?"
    
    return jsonify({"reponse": reponse})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
