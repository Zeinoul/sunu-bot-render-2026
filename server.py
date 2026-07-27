import os
import json
import threading
import time
import re
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)
CORS(app, origins=["https://sunu.com", "https://www.sunu.com", "*"])
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

def extraire_infos_commande(message):
    tel_match = re.search(r'7[06758]\d{7}', message)
    tel = tel_match.group() if tel_match else ""
    nom_match = re.search(r'nom\s*(?:est|:)?\s*([a-zA-Z\s]+)', message)
    nom = nom_match.group(1).strip().title() if nom_match else ""
    adresse_match = re.search(r'adresse\s*(?:est|:)?\s*(.+)', message)
    adresse = adresse_match.group(1).strip().title() if adresse_match else ""
    return nom, tel, adresse

def sauvegarder_commande(data_commande):
    try:
        ref = db.reference('/commandes')
        ref.push(data_commande)
        return True
    except:
        return False

def trouver_produit(message, produits):
    """Cherche dans nom + categorie + mots clés"""
    message = message.lower()
    for p in produits:
        nom = p['nom'].lower()
        cat = p.get('categorie','').lower()
        if nom in message or cat in message or message in nom or message in cat:
            return p
    return None

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').lower()
    produits = data.get('produits', [])
    numero = data.get('numero', '')

    reponse = "Je n'ai pas compris. Tape 'aide' pour voir ce que je peux faire."

    # 1. BONJOUR
    if "bonjour" in message or "salut" in message:
        reponse = "Salut! 👋 Bienvenue sur SUNU.COM 🇸🇳\nLivraison gratuite Dakar > 20.000 FCFA. Tu cherches quoi?"

    # 2. ENREGISTRER NUMERO
    elif re.match(r'7[06758]\d{7}', message):
        reponse = f"✅ Numéro {message} enregistré. Que puis-je faire pour toi?"

    # 3. AIDE
    elif "aide" in message:
        reponse = "Je peux t'aider pour:\n💰 Prix des produits\n🚚 Livraison\n🛒 Passer commande\nDis moi le nom du produit"

    # 4. PRIX - INTELLIGENT
    elif "prix" in message or "coute" in message:
        produit = trouver_produit(message, produits)
        if produit:
            stock = "🔥 Il reste peu en stock!" if int(produit.get('stock', 10)) < 5 else "✅ En stock"
            reponse = f"{produit['nom']} coûte {int(produit['prix']):,} FCFA. {stock}\nTu veux commander?"
        else:
            reponse = "Donne moi le nom exact du produit. Ex: 'prix ordinateur' ou 'prix iPhone 14'"

    # 5. LIVRAISON
    elif "livraison" in message:
        reponse = "🚚 Livraison 24H Dakar. 48H régions. Frais dès 1500 FCFA.\n💰 Paiement à la livraison."

    # 6. COMMANDE
    elif any(mot in message for mot in ["commander", "commande", "je veux", "nom", "adresse"]):
        nom, tel, adresse = extraire_infos_commande(message)
        if nom and tel and adresse:
            commande = {
                "nom": nom, "telephone": tel, "adresse": adresse,
                "numero_client": numero, "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "statut": "Nouvelle", "source": "Chatbot"
            }
            if sauvegarder_commande(commande):
                reponse = f"✅ Commande confirmée {nom}!\nOn t'appelle au {tel} dans 5min.\nLivraison: {adresse} 🙏"
            else:
                reponse = "Erreur. Je te rappelle dans 2min."
        else:
            reponse = "Pour commander donne moi:\nNom + Téléphone + Adresse\nEx: mon nom est Zeinoul, téléphone 77 907 54 32, adresse Pikine"

    return jsonify({"reponse": reponse})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
