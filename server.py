import os
import json
import re
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import google.generativeai as genai
import requests

app = Flask(__name__)
CORS(app)

# ===== CONFIG =====
# 1. FIREBASE
cred_json = os.environ.get("FIREBASE_CRED")
cred_dict = json.loads(cred_json)
cred = credentials.Certificate(cred_dict)
database_url = os.environ.get("FIREBASE_DB_URL")
firebase_admin.initialize_app(cred, {'databaseURL': database_url})
print("✅ Bot Sunu + Firebase connecté")

# 2. GEMINI GRATUIT
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. API META WHATSAPP
META_TOKEN = os.environ.get("META_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
META_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

VERIFY_TOKEN = "sunu123"
clients = {} # pour garder le contexte

# ===== FONCTIONS =====
def envoyer_whatsapp(numero, texte):
    """Envoie un message via API Meta"""
    headers = {"Authorization": f"Bearer {META_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": "221" + numero, # 221 = code Sénégal
        "type": "text",
        "text": {"body": texte}
    }
    try:
        requests.post(META_URL, headers=headers, json=data)
    except Exception as e:
        print("Erreur envoi Meta:", e)

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
        print(f"✅ Commande sauvegardée: {data_commande['nom']}")
        return True
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")
        return False

# ===== ROUTES =====
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    else:
        return "Erreur de vérification", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    """Pour recevoir les messages depuis WhatsApp Meta"""
    data = request.get_json()
    # Ici Meta va t'envoyer les messages si quelqu'un écrit sur 70 513 91 64
    return "ok", 200

@app.route('/chat', methods=['POST'])
def chat():
    """C'est cette route que ton site appelle"""
    data = request.get_json()
    message = data.get('message', '').lower()
    numero = data.get('numero')
    produits = data.get('produits', [])

    if numero not in clients:
        clients[numero] = {"etape": "accueil"}

    reponse = "Je n'ai pas compris. Tape 'aide' pour voir ce que je peux faire."

    # 1. BONJOUR
    if "bonjour" in message or "salut" in message:
        reponse = "Salut! 👋 Bienvenue sur SUNU.COM 🇸🇳\nLivraison gratuite Dakar > 20.000 FCFA. Tu cherches quoi?"

    # 2. ENREGISTRER NUMERO
    elif re.match(r'7[06758]\d{7}', message):
        reponse = f"✅ Numéro {message} enregistré. Que puis-je faire pour toi?"

    # 3. AFFICHER PRODUITS AVEC PHOTOS
    elif 'produit' in message or 'catalogue' in message or 'voir' in message or 'ménager' in message:
        if len(produits) == 0:
            reponse = "Aucun produit chargé pour le moment."
        else:
            reponse = "Voici nos produits du moment 👇\n\n"
            for i, p in enumerate(produits[:8]):
                reponse += f"{i+1}. *{p['nom']}* - {int(p['prix']):,} FCFA\n"
                reponse += f"{p['image']}\n\n" # Le lien image s'affiche
            reponse += "Tape le numéro pour commander. Ex: 1"

    # 4. CHOIX PRODUIT PAR NUMERO
    elif message.isdigit() and 1 <= int(message) <= 8:
        index = int(message) - 1
        produit = produits[index]
        clients[numero]['produit_choisi'] = produit
        reponse = f"✅ Tu as choisi: *{produit['nom']}* à {int(produit['prix']):,} FCFA\n\n"
        reponse += "Pour valider donne moi:\nNom + Téléphone + Adresse\nEx: mon nom est Zeinoul, téléphone 77 907 54 32, adresse Pikine"

    # 5. PRIX
    elif "prix" in message:
        for p in produits:
            if p['nom'].lower() in message:
                stock = "🔥 Il reste peu en stock!" if int(p.get('stock', 10)) < 5 else "✅ En stock"
                reponse = f"{p['nom']} coûte {int(p['prix']):,} FCFA. {stock}\nTu veux commander?"
                break
        else:
            reponse = "Donne moi le nom du produit. Ex: 'prix javel'"

    # 6. COMMANDE
    elif any(mot in message for mot in ["commander", "commande", "nom", "adresse"]):
        nom, tel, adresse = extraire_infos_commande(message)
        if nom and tel and adresse:
            produit = clients[numero].get('produit_choisi', {'nom': 'Produit demandé'})
            commande = {
                "nom": nom, "telephone": tel, "adresse": adresse,
                "numero_client": numero, "produit": produit['nom'],
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "statut": "Nouvelle", "source": "Chatbot Site"
            }
            if sauvegarder_commande(commande):
                reponse = f"✅ Commande confirmée {nom}!\nOn t'appelle au {tel} dans 5min.\nLivraison: {adresse} 🙏"
                # Optionnel: envoyer aussi sur ton WhatsApp perso
                # envoyer_whatsapp("775139164", f"Nouvelle commande: {nom} - {produit['nom']}")
            else:
                reponse = "Erreur. Je te rappelle dans 2min."
        else:
            reponse = "Pour commander donne moi:\nNom + Téléphone + Adresse\nEx: mon nom est Zeinoul, téléphone 77 907 54 32, adresse Pikine"

    # 7. SINON GEMINI REPOND
    else:
        try:
            prompt = f"""Tu es l'assistant commercial de SUNU.COM au Sénégal.
            Sois court, sympa, en Français/Wolof. Client: "{message}".
            Produits dispo: {', '.join([p['nom'] for p in produits[:10]])}.
            Si il demande un produit, dis lui de taper 'produits'."""
            response = model.generate_content(prompt)
            reponse = response.text
        except:
            reponse = "Désolé je n'ai pas compris. Tape 'produits' pour voir le catalogue"

    return jsonify({"reponse": reponse})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))iron.get("PORT", 5000)))
