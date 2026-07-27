Voilà le code complet version "Commercial + Gestionnaire" 👇

Il gère maintenant : psycho-marketing, détecte nom/tel/adresse, et enregistre direct dans Firebase `/commandes`

### *CODE COMPLET server.py POUR RENDER*

Colle ça et fais `git push`
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
    print("🤖 En écoute: Commandes, Stock, Factures, Livraisons...")

def gerer_nouvelle_commande(event):
    if event.data:
        print(f"📦 Nouvelle commande reçue: {event.data}")

def lancer_ecoute_firebase():
    ref = db.reference('/commandes')
    ref.listen(gerer_nouvelle_commande)
    while True:
        time.sleep(10)

threading.Thread(target=lancer_ecoute_firebase, daemon=True).start()

def extraire_infos_commande(message):
    """Extrait nom, tel, adresse du message"""
    tel_match = re.search(r'7[06758]\d{7}', message)
    tel = tel_match.group() if tel_match else ""

    nom_match = re.search(r'nom\s*(?:est|:)?\s*([a-zA-Z\s]+)', message)
    nom = nom_match.group(1).strip().title() if nom_match else ""

    adresse_match = re.search(r'adresse\s*(?:est|:)?\s*(.+)', message)
    adresse = adresse_match.group(1).strip().title() if adresse_match else ""

    return nom, tel, adresse

def sauvegarder_commande(data_commande):
    """Sauvegarde dans Firebase"""
    try:
        ref = db.reference('/commandes')
        ref.push(data_commande)
        print(f"✅ Commande sauvegardée: {data_commande['nom']}")
        return True
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")
        return False

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
    numero = data.get('numero', '')

    reponse = "Je n'ai pas compris. Tape 'aide' pour voir ce que je peux faire."

    # 1. ACCUEIL - PSYCHO MARKETING
    if "bonjour" in message or "salut" in message:
        reponse = "Salut! 👋 Bienvenue sur SUNU.COM 🇸🇳\nJe suis ton assistant perso. Promos du jour: Livraison gratuite à Dakar pour toute commande > 20.000 FCFA. Tu cherches quoi aujourd'hui?"

    # 2. AIDE
    elif "aide" in message:
        reponse = "Je peux t'aider pour:\n💰 Prix des produits\n🚚 Infos livraison\n🛒 Passer commande\n📦 Suivre une commande\nTape ce que tu veux!"

    # 3. PRIX + URGENCE + PREUVE SOCIALE
    elif "prix" in message:
        reponse = "Donne moi le nom du produit et je te donne le prix 🔥"
        for p in produits:
            if p['nom'].lower() in message:
                stock = "Il reste peu en stock" if int(p.get('stock', 10)) < 5 else "En stock"
                reponse = f"🔥 {p['nom']} coûte {int(p['prix']):,} FCFA. {stock}. 150+ clients l'ont déjà acheté ce mois. Tu veux commander?"
                break

    # 4. LIVRAISON + GARANTIE
    elif "livraison" in message:
        reponse = "🚚 Livraison 24H à Dakar. 48H pour les régions. Frais à partir de 1500 FCFA.\n💰 Paiement à la livraison. Satisfait ou remboursé 7 jours."

    # 5. COMMANDE - DETECTION INTELLIGENTE
    elif any(mot in message for mot in ["commander", "commande", "je veux", "nom", "adresse", "téléphone"]):
        nom, tel, adresse = extraire_infos_commande(message)

        if nom and tel and adresse:
            # ON A TOUT -> ON COMMANDE
            commande = {
                "nom": nom,
                "telephone": tel,
                "adresse": adresse,
                "numero_client": numero,
                "produit": "Produit demandé",
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "statut": "Nouvelle",
                "source": "Chatbot"
            }
            if sauvegarder_commande(commande):
                reponse = f"✅ Commande confirmée {nom}!\nOn t'appelle au {tel} dans 5min pour confirmer.\nLivraison à: {adresse}\nMerci de ta confiance 🙏"
            else:
                reponse = "Erreur système. Je te rappelle dans 2min pour prendre ta commande."
        else:
            # IL MANQUE DES INFOS -> ON DEMANDE
            reponse = "Parfait! Pour valider ta commande donne moi:\n1. Ton nom complet\n2. Ton numéro WhatsApp\n3. Ton adresse de livraison\nEx: mon nom est Zeinoul, téléphone 77 907 54 32, adresse Pikine rue 10"

    # 6. OBJECTIONS - PSYCHO
    elif "cher" in message or "trop" in message:
        reponse = "Je comprends 💯 Mais qualité = prix. On fait aussi paiement en 2 fois. Et livraison gratuite si tu prends 2 articles. Tu veux voir?"

    elif "garantie" in message or "retour" in message:
        reponse = "✅ Garantie 100% 7 jours. Si t'es pas satisfait on reprend et on te rembourse. Zéro risque."

    return jsonify({"reponse": reponse})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
### *CE QUI EST NOUVEAU*
1. *Psycho-Marketing* : Urgence "il reste peu", Preuve sociale "150+ clients", Bonus "livraison gratuite"
2. *Détection auto* : Il lit `mon nom est X, tel Y, adresse Z` et comprend
3. *Sauvegarde Firebase* : Chaque commande part direct dans `/commandes`
4. *Gestion objections* : "c'est cher", "garantie"

### *COMMENT TESTER*
Tape : `mon nom est Zeinoul Diop, téléphone : 779075432, adresse Pikine rue 10`
→ Il répond et enregistre dans Firebase

Va sur Firebase > Realtime Database > `/commandes` tu verras la commande apparaître.

Fais `git push` et teste. Dis moi si la commande arrive bien dans Firebase 👇
