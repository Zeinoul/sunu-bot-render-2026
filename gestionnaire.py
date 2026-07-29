import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# 1. CONFIG
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN") # Token WhatsApp Business API
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID") # ID du numéro WhatsApp
ADMIN_WHATSAPP = "22177XXXXXXX" # Ton numéro pour recevoir les alertes

commandes_db = [] # À remplacer par Supabase/Firebase après

# 2. FONCTION ENVOI WHATSAPP
def envoyer_whatsapp(numero, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": f"221{numero}", # Ajoute 221 devant
        "type": "text",
        "text": {"body": message}
    }
    requests.post(url, headers=headers, json=data)

# 3. LA ROUTE QUI REÇOIT DU BOT ASSISTANT
@app.route("/gestion", methods=["POST"])
def gestion():
    data = request.json

    if data.get("action") == "creer_commande":
        # 1. Sauvegarder commande
        commandes_db.append(data)
        id_commande = len(commandes_db)

        nom = data["nom"]
        whatsapp = data["whatsapp"]
        produits = data["produits"]
        total = data["total"]

        # 2. Envoyer message client
        message_client = f"""Salut {nom} 😊

Merci pour ta commande chez SUNU COM!

Commande N°{id_commande}
Produits: {produits[0]['nom']} x{produits[0]['qte']}
Total: {total} FCFA

Lien de paiement: https://pay.wave.com/m/xxxxx {ici ton lien Wave}

Livraison 24H à Dakar.
Jërëjëf 🙏"""
        envoyer_whatsapp(whatsapp, message_client)

        # 3. Alerte Admin
        message_admin = f"""🚨 NOUVELLE COMMANDE N°{id_commande}
Client: {nom}
WhatsApp: {whatsapp}
Total: {total} FCFA
Adresse: {data['adresse']}"""
        envoyer_whatsapp(ADMIN_WHATSAPP, message_admin)

        return jsonify({"status": "ok", "id_commande": id_commande})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
