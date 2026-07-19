import json
import os
import time
import firebase_admin
from firebase_admin import credentials, db

print("🔄 Connexion Firebase...")

database_url = os.environ.get('FIREBASE_URL')
cred_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
cred_dict = json.loads(cred_json)

cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': database_url
})

print("✅ Bot Gestionnaire Sunu connecté")
print("🤖 En écoute: Commandes, Stock, Factures, Livraisons...")

def gerer_nouvelle_commande(event):
    print(f"📦 Nouvelle commande reçue: {event.data}")

ref = db.reference('/commandes')
ref.listen(gerer_nouvelle_commande)

while True:
    time.sleep(10)