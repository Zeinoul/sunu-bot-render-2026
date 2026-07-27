import os
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Important: autorise ton site à appeler le bot

VERIFY_TOKEN = "sunu2026"
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")

# 1. WEBHOOK WHATSAPP - déjà existant
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Erreur de vérification", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Message WhatsApp reçu:", data) # pour voir dans les logs Render
    return "ok", 200

# 2. NOUVELLE ROUTE POUR LE SITE - C'EST ÇA QU'ON AJOUTE
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').lower()
    numero = data.get('numero', '')
    produits = data.get('produits', [])

    print(f"Message du site: {message} de {numero}")

    # LOGIQUE DU BOT SUNU.COM
    reponse = "Désolé je n'ai pas compris. Tape 'aide'"

    if "bonjour" in message or "salut" in message:
        reponse = "Salut ! Bienvenue sur SUNU.COM 🇸🇳 Comment je peux t'aider ?"
    
    elif "prix" in message or "coute" in message:
        # Cherche le produit dans la liste
        for p in produits:
            if p['nom'].lower() in message:
                reponse = f"{p['nom']} coûte {int(p['prix']):,} FCFA"
                break
        else:
            reponse = f"On a {len(produits)} produits. Donne moi le nom du produit."

    elif "livraison" in message:
        reponse = "Livraison 24H à Dakar. 48H régions. Paiement à la livraison."
    
    elif "aide" in message:
        reponse = "Je peux t'aider avec: prix, livraison, commande. Donne moi le nom d'un produit."
    
    else:
        # Réponse par défaut avec 3 produits
        noms = [p['nom'] for p in produits[:3]]
        reponse = f"Voici quelques produits: {', '.join(noms)}. Tape le nom pour avoir le prix."

    return jsonify({"reponse": reponse})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
