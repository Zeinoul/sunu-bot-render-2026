OUI C'EST MIEUX 🔥

Là ton bot envoie une liste de produits en dur. Si tu ajoutes un produit sur Firebase, le bot le verra pas.

On va le brancher direct à Firestore pour que le bot lise `collection: Produits` en temps réel.

### *CODE SERVER.PY MIS A JOUR AVEC FIREBASE LECTURE*

Remplace tout ton `server.py` par ça :
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
### *CODE WIDGET SITE MIS A JOUR*

Plus besoin de mettre les produits en dur. Le site envoie juste `produits: []` vide
<script>
const API_URL = "https://sunu-bot-render-2026-1-5oit.onrender.com/chat";
const CLIENT_NUM = "site_web_" + Date.now();

async function sendToBot() {
  const input = document.getElementById('sunu-user-input');
  const message = input.value;
  if (!message) return;

  addMessage(message, 'user');
  input.value = '';
  addMessage('...', 'bot');

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        message: message,
        numero: CLIENT_NUM,
        produits: [] // VIDE, le bot va chercher dans Firebase
      })
    });
    const data = await res.json();
    document.getElementById('sunu-bot-messages').lastChild.remove();
    addMessage(data.reponse.replace(/\n/g, '<br>'), 'bot');

  } catch(e) {
    document.getElementById('sunu-bot-messages').lastChild.remove();
    addMessage("Désolé, erreur de connexion au bot.", 'bot');
  }
}
</script>
### *IMPORTANT : CHAMPS FIREBASE*
Dans ta collection `Produits`, assure toi que chaque produit a:
1. `nom` : "Eau de Javel 5L"
2. `prix` : 3500
3. `image` : "https://..."

### *COMMANDES GIT*
git add server.py
git commit -m "lecture produits depuis Firestore"
git push
Attends 2min de déploiement.

Test: Tape "produits" sur le bot. Il doit afficher les 14 produits de ta capture d'écran.

Tu veux que je t’ajoute aussi la recherche par mot clé genre "je veux du javel"?
