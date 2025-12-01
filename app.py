import streamlit as st
import requests
from datetime import datetime, timedelta
from openai import OpenAI
import os   
# -------- CONFIG --------
OPENAI_KEY = os.getenv("OPENAI_API_KEY") 
DATASET_URL = "https://api.apify.com/v2/actor-tasks/purple_neck~linkedin-company-posts-batch-scraper-no-cookies-task/runs/last/dataset/items?token=apify_api_ioAvdVWOS4CFKd3LQAsYrTtSKlgCyW2vCc4v"
WINDOW_HOURS = 200
client = OpenAI(api_key=OPENAI_KEY)

# --------- FONCTIONS ---------

def smart_title_and_summary(text):
    prompt = f"""
Voici un texte provenant d'un post LinkedIn :

{text}

Ta mission :
1) Générer un titre clair et court (6 à 12 mots), style communiqué officiel.
2) Générer un résumé en UNE SEULE PHRASE.

Format EXACT :
TITRE: <titre>
RESUME: <résumé>
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    ).choices[0].message.content

    title = ""
    resume = ""
    for l in res.split("\n"):
        if l.startswith("TITRE:"):
            title = l.replace("TITRE:", "").strip()
        if l.startswith("RESUME:"):
            resume = l.replace("RESUME:", "").strip()

    return title, resume


def fetch_posts():
    data = requests.get(DATASET_URL).json()
    if not isinstance(data, list):
        return []

    cutoff = datetime.utcnow() - timedelta(hours=WINDOW_HOURS)
    posts = []

    for p in data:
        if "posted_at" not in p:
            continue

        dt = datetime.strptime(p["posted_at"]["date"], "%Y-%m-%d %H:%M:%S")
        if dt < cutoff:
            continue

        posts.append({
            "company": p.get("author", {}).get("name", "Entreprise inconnue"),
            "text": p.get("text") or "",
            "image": p.get("image_url") or None,
            "link": p.get("post_url"),
        })

    return posts


# -------- INTERFACE STREAMLIT --------

st.set_page_config(page_title="Scraper LinkedIn", layout="wide")

st.title("🚀 Tableau de bord LinkedIn")
st.write("Bienvenue mes Cannois!")

tab1, tab2 = st.tabs(["📌 Scraper & Résumés", "📰 Newsletter"])


# ----------- TAB 1 : SCRAPER & POSTS -----------
with tab1:
    st.header("📌 Récupérer les posts")

    if st.button("🔄 Lancer la collecte"):
        with st.spinner("Récupération des posts..."):
            posts = fetch_posts()

        if not posts:
            st.error("Aucun post trouvé.")
        else:
            st.success(f"{len(posts)} posts trouvés ✔️")

            # Affichage par entreprise
            companies = {}
            for p in posts:
                companies.setdefault(p["company"], []).append(p)

            for company, items in companies.items():
                st.subheader(f"🏢 {company}")

                for item in items:
                    title, summary = smart_title_and_summary(item['text'])

                    with st.container(border=True):
                        st.markdown(f"### {title}")
                        st.write(summary)

                        if item["image"]:
                            st.image(item["image"], use_column_width=True)

                        st.markdown(f"[🔗 Voir le post LinkedIn]({item['link']})")
                        st.write("---")

    st.info("Clique sur le bouton pour afficher les posts.")

    


# ----------- TAB 2 : NEWSLETTER -----------

with tab2:
    st.header("📰 Génération de newsletter")

    st.write("Cette section génère une analyse stratégique complète à partir des posts collectés.")

    if st.button("Générer la newsletter"):
        with st.spinner("Analyse des posts et génération de la newsletter..."):

            posts = fetch_posts()
            if not posts:
                st.error("Aucun post disponible pour créer la newsletter.")
            else:
                # Organiser les posts par entreprise
                companies = {}
                for p in posts:
                    companies.setdefault(p["company"], []).append(p)

                # Construire un contexte clair pour GPT
                context = ""
                for company, items in companies.items():
                    context += f"\n\n### {company}\n"
                    for item in items:
                        title, summary = smart_title_and_summary(item['text'])
                        context += f"- **{title}** : {summary}\n"

                # Prompt newsletter
                prompt = f"""
Tu es un analyste stratégique spécialisé dans le secteur spatial européen.
Génère une **newsletter professionnelle**, concise mais percutante, basée sur ces posts LinkedIn des dernières heures :

{context}

Ton travail :
1. Créer un titre général impactant pour la newsletter.
2. Faire une synthèse stratégique globale (400–600 mots).
3. Identifier :
   - les signaux faibles,
   - les tendances majeures,
   - les messages politiques ou institutionnels,
   - les implications marché & concurrents.
4. Proposer une section "À surveiller prochainement".
5. Faire une conclusion éditoriale courte.

Format EXACT :
# <Titre>
## Synthèse stratégique
<texte>
## Signaux faibles
- ...
## Tendances
- ...
## Messages institutionnels
- ...
## Implications marché & concurrence
- ...
## À surveiller
- ...
## Conclusion
<texte>
"""

                # Appel GPT
                newsletter = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                ).choices[0].message.content

                st.success("Newsletter générée ✔️")
                st.markdown(newsletter)

                # Téléchargement
                st.download_button(
                    label="📥 Télécharger en .txt",
                    data=newsletter,
                    file_name="newsletter.txt",
                    mime="text/plain"
                )