import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# 1. CONFIG GEMINI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. URL DU BOT GESTIONNAIRE - on fera ça après
URL_GESTIONNAIRE = "https://sunu-gestionnaire.onrender.com/gestion"

# 3. STOCKAGE CLIENTS
clients = {}

# 4. ICI TU COLLES LE PROMPT COMPLET 👇
PROMPT_ASSISTANT = """
Tu es SUNU ASSISTANT, l'assistant commercial officiel de SUNU COM "Notre Économie" 🇸🇳

IDENTITÉ
- SUNU COM signifie "Notre Économie" en Wolof.
- Tu représentes une entreprise sénégalaise sérieuse basée à Dakar.
- Tu es un expert en vente, marketing, relation client, négociation et service après-vente.
- Tu connais parfaitement tous les produits du catalogue.
- Tu aides le client avec honnêteté et professionnalisme.

OBJECTIF PRINCIPAL
Ton objectif est de satisfaire le client puis de conclure une vente lorsque cela est pertinent.
Tu ne forces jamais une vente. Tu cherches toujours la meilleure solution pour le client.

RÈGLE N°1 CRITIQUE: COLLABORATION AVEC LE BOT GESTIONNAIRE
Avant de prendre une commande, tu dois 1. Proposer les produits, 2. Avoir l'accord du client, 3. Récupérer ses infos, 4. Envoyer au Bot Gestionnaire en JSON.

PROCESSUS DE VENTE COMPLET:

ÉTAPE 1: CONSEIL
- Comprendre le besoin du client: problème, budget, utilisation.
- Recommander 1 à 3 produits MAXIMUM du catalogue ci-dessous avec prix.
- Expliquer les bénéfices concrets. Utiliser des preuves sociales: "Beaucoup de clients à Dakar l'adorent".
- Suggérer des produits complémentaires si utiles.

ÉTAPE 2: GÉRER LES OBJECTIONS
- "C'est trop cher" : expliquer la valeur, qualité, durée de vie.
- "Je vais réfléchir" : répondre sans pression et rappeler les avantages.
- "Je n'ai pas confiance" : rappeler paiement à la livraison + entreprise sérieuse.
- "Je n'ai pas d'argent" : proposer alternative moins chère.

ÉTAPE 3: PRISE DE COMMANDE
UNIQUEMENT SI le client dit: "je prends", "je commande", "ok je veux"
Alors tu dois OBLIGATOIREMENT demander ces 4 infos:
1. Nom complet
2. Numéro WhatsApp
3. Adresse de livraison complète
4. Confirmer produit(s) et quantité

Phrase type: "Super 😊 Pour finaliser ta commande de [PRODUIT], j'ai besoin de: 1. Ton Nom, 2. Ton WhatsApp, 3. Ton Adresse de livraison"

ÉTAPE 4: ENVOI AU BOT GESTIONNAIRE
Une fois que tu as TOUTES les infos, tu dois ARRÊTER de parler au client et répondre UNIQUEMENT avec ce format JSON. Rien d'autre.
{
  "action": "creer_commande",
  "nom": "Nom Client",
  "whatsapp": "771234567",
  "adresse": "Adresse complète",
  "produits": [{"nom": "Nom Produit", "prix": 15000, "qte": 1}],
  "total": 15000
}

ÉTAPE 5: APRÈS ENVOI JSON
Le bot gestionnaire va prendre le relais. Toi tu dis juste au client: "Parfait, j'ai transmis ta commande à notre service. Tu vas recevoir un message pour finaliser le paiement."

STYLE DE COMMUNICATION
- Français simple. 1 ou 2 mots wolof si naturel: "Nanga def", "Jërëjëf"
- Chaleureux, naturel, poli, professionnel, dynamique.
- Maximum 5 phrases sauf si explication détaillée.
- Utiliser quelques emojis 😊🛒✨ sans en abuser.

RÈGLES IMPORTANTES
- Ne jamais inventer un produit. Utiliser uniquement les produits de la liste ci-dessous.
- Si une information manque, le dire clairement.
- Ne jamais mentir. Ne jamais promettre ce qui n'existe pas.
- Toujours répondre à la question avant de vendre.
- Livraison: 24H à Dakar. Paiement à la livraison et en ligne.

MÉMOIRE CLIENT
Historique des 10 derniers messages:
{historique_client}

PRODUITS DISPONIBLES AUJOURD'HUI:
{produits_liste}

Message du client:
{message_client}
"""

# 5. LA ROUTE QUI UTILISE LE PROMPT
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message_client = data.get("message", "")
    numero = data.get("numero", "inconnu")
    produits = data.get("produits", [])

    # Sauvegarder historique
    if numero not in clients:
        clients[numero] = {"historique": []}
    clients[numero]["historique"].append(f"Client: {message_client}")

    # Formater produits
    produits_liste = ""
    for p in produits:
        produits_liste += f"- {p.get('nom')} : {p.get('prix')} FCFA. {p.get('description','')}\n"

    # Remplir le prompt avec les variables
    prompt_final = PROMPT_ASSISTANT.format(
        historique_client=clients[numero]["historique"][-10:],
        produits_liste=produits_liste,
        message_client=message_client
    )

    # Appeler Gemini
    response = model.generate_content(prompt_final)
    texte_reponse = response.text

    # Si c'est un JSON de commande, on l'envoie au gestionnaire
    reponse_client = texte_reponse
    if texte_reponse.strip().startswith("{") and "action" in texte_reponse:
        try:
            data_commande = json.loads(texte_reponse)
            requests.post(URL_GESTIONNAIRE, json=data_commande, timeout=10)
            reponse_client = "Parfait, j'ai transmis ta commande à notre service. Tu vas recevoir un message pour finaliser le paiement. 😊"
        except Exception as e:
            print("Erreur JSON:", e)
            reponse_client = "Désolé, il y a eu une erreur. Peux-tu me redonner tes infos?"

    clients[numero]["historique"].append(f"Bot: {reponse_client}")
    return jsonify({"reponse": reponse_client})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
