Ahhh j’ai compris l’erreur 😅

`SyntaxError: unterminated string literal (detected at line 1)`
Tu as copié-collé mon texte d’explication dans `server.py` au lieu du code seul.

Il faut seulement le code Python.

### *CORRECTION : VOICI LE VRAI server.py À COLLER*

Copie ça exactement et fais `git push` :
import os
import json
import re
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# ===== CONFIG =====
cred_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
cred_dict = json.loads(cred_json)
cred = credentials.Certificate(cred_dict)
database_url = os.environ.get("FIREBASE_URL")
firebase_admin.initialize_app(cred, {'databaseURL': database_url})

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

clients = {}

print("✅ Bot Gestionnaire Sunu connecté")

# ===== PAGE D'ACCUEIL =====
@app.route('/', methods=['GET'])
def accueil():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Bot SUNU.COM API</title>
        <style>
            body { font-family: Arial; background: #0B5FFF; color: white; text-align: center; padding-top: 100px; }
           .box { background: white; color: #333; padding: 40px; border-radius: 20px; width: 500px; margin: auto; }
            h1 { color: #0B5FFF; }
           .status { color: green; font-weight: bold; font-size: 20px; }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🤖 Bot SUNU.COM</h1>
            <p class="status">EN LIGNE ✅</p>
            <p>API pour le site sunu.com</p>
            <hr>
            <p><b>Route:</b> POST /chat</p>
            <p>Version 2.0 - Propulsé par Gemini + Firebase</p>
        </div>
    </body>
    </html>
    """, 200

# ===== FONCTIONS =====
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

# ===== ROUTE PRINCIPALE CHAT =====
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '').lower()
    numero = data.get('numero')
    produits = data.get('produits', [])

    if numero not in clients:
        clients[numero] = {}

    if 'produit' in message or 'catalogue' in message:
        reponse = "Voici nos produits 👇\n\n"
        for i, p in enumerate(produits[:8]):
            reponse += f"{i+1}. *{p['nom']}* - {int(p['prix']):,} FCFA\n{p['image']}\n\n"
        reponse += "Tape le numéro pour commander. Ex: 1"

    elif message.isdigit() and 1 <= int(message) <= len(produits):
        produit = produits[int(message)-1]
        clients[numero]['produit'] = produit
        reponse = f"✅ *{produit['nom']}* à {int(produit['prix']):,} FCFA\n\nDonne: Nom + Téléphone + Adresse"

    elif any(mot in message for mot in ["commander", "nom", "adresse"]):
        nom, tel, adresse = extraire_infos_commande(message)
        if nom and tel and adresse:
            produit = clients[numero].get('produit', {'nom': 'Produit'})
            commande = {"nom": nom, "telephone": tel, "adresse": adresse, "produit": produit['nom'], "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
            if sauvegarder_commande(commande):
                reponse = f"✅ Commande confirmée {nom}!\nOn t'appelle au {tel} dans 5min."
            else:
                reponse = "Erreur système."
        else:
            reponse = "Donne: Nom + Téléphone + Adresse"
    else:
        try:
            prompt = f"Tu es assistant SUNU.COM Dakar. Sois court et commercial. Client: '{message}'. Produits: {', '.join([p['nom'] for p in produits[:10]])}."
            reponse = model.generate_content(prompt).text
        except:
            reponse = "Tape 'produits' pour voir le catalogue"

    return jsonify({"reponse": reponse})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
### *COMMANDES GIT*
git add server.py
git commit -m "fix: ajout page accueil"
git push
Attends 1min que Render re-déploie.

Après tu vas sur `https://sunu-bot-render-2026-1-5oit.onrender.com` et tu dois voir la page bleue.

Dis moi si ça passe cette fois 👇
