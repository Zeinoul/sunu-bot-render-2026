import os
import json
import re
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db, firestore
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# ===== CONFIG =====
cred_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
cred_dict = json.loads(cred_json)
cred = credentials.Certificate(cred_dict)
database_url = os.environ.get("FIREBASE_URL")
firebase_admin.initialize_app(cred, {'databaseURL': database_url})

firestore_db = firestore.client() # POUR LIRE FIRESTORE

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

clients = {}

print("✅ Bot Gestionnaire Sunu connecté + Firestore")

@app.route('/', methods=['GET'])
def accueil():
    return "<h1>Bot SUNU.COM EN LIGNE ✅</h1>", 200

def get_produits_firebase():
    """Lit directement la collection 'Produits' de Firestore"""
    produits = []
    try:
        docs = firestore_db.collection('Produits').stream()
        for doc in docs:
            data = doc.to_dict()
            produits.append({
                "id": doc.id,
                "nom": data.get('nom', 'Sans nom'),
                "prix": data.get('prix', 0),
                "image": data.get('image', '')
            })
    except Exception as e:
        print("Erreur lecture produits:", e)
    return produits

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

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '').lower()
    numero = data.get('numero')

    produits = get_produits_firebase() # ON LIT FIREBASE A CHAQUE FOIS

    if numero not in clients:
        clients[numero] = {}

    if 'produit' in message or 'catalogue' in message:
        reponse = "Voici nos produits SUNU 👇\n\n"
        for i, p in enumerate(produits[:10]):
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
            commande = {"nom": nom, "telephone": tel, "adresse": adresse, "produit": produit['nom'], "prix": produit['prix'], "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
            if sauvegarder_commande(commande):
                reponse = f"✅ Commande confirmée {nom}!\nProduit: {produit['nom']}\nOn t'appelle au {tel} dans 5min."
            else:
                reponse = "Erreur système."
        else:
            reponse = "Donne: Nom + Téléphone + Adresse"
    else:
        try:
            noms_produits = ', '.join([p['nom'] for p in produits[:10]])
            prompt = f"Tu es assistant SUNU.COM Dakar. Sois court et commercial. Client: '{message}'. Produits dispo: {noms_produits}."
            reponse = model.generate_content(prompt).text
        except:
            reponse = "Tape 'produits' pour voir le catalogue"

    return jsonify({"reponse": reponse})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
