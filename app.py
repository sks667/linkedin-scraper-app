import streamlit as st
import requests
from datetime import datetime, timedelta
from openai import OpenAI
import os

# -------- CONFIG --------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
DATASET_URL = "https://api.apify.com/v2/actor-tasks/purple_neck~linkedin-company-posts-batch-scraper-no-cookies-task/runs/last/dataset/items?format=json&clean=true&token=apify_api_ioAvdVWOS4CFKd3LQAsYrTtSKlgCyW2vCc4v"
WINDOW_HOURS = 200
APP_PASSWORD = os.getenv("APP_PASSWORD")
client = OpenAI(api_key=OPENAI_KEY)


# -------- SECURITÉ : MOT DE PASSE --------

def check_password():

    def password_entered():
        if st.session_state["password"] == APP_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" in st.session_state:
        return st.session_state["password_correct"]

    st.title("🔐 Accès protégé")
    st.write("Veuillez entrer le mot de passe pour accéder au tableau de bord.")

    st.text_input("Mot de passe :", type="password", key="password", on_change=password_entered)

    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("⛔ Mot de passe incorrect")

    return False


if not check_password():
    st.stop()


# --------- FONCTIONS ---------

def smart_title_and_summary(text):
    prompt = f"""
Voici un texte provenant d'un post LinkedIn :

{text}

Ta mission :
1) Générer un titre clair et court (6 à 12 mots).
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
    summary = ""

    for line in res.split("\n"):
        if line.startswith("TITRE:"):
            title = line.replace("TITRE:", "").strip()
        if line.startswith("RESUME:"):
            summary = line.replace("RESUME:", "").strip()

    return title, summary


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
            "id": p.get("full_urn"),
            "company": p.get("author", {}).get("name", "Entreprise inconnue"),
            "text": p.get("text") or "",
            "image": p.get("media", {}).get("items", [{}])[0].get("thumbnail"),
            "link": p.get("post_url"),
        })

    return posts


# -------- INTERFACE STREAMLIT --------

st.set_page_config(page_title="Scraper LinkedIn", layout="wide")

st.title("🚀 Tableau de bord LinkedIn")

if "active_posts" not in st.session_state:
    st.session_state["active_posts"] = {}


tab1, tab2 = st.tabs(["📌 Scraper & Résumés", "📰 Newsletter"])


# -------- TAB 1 : SCRAPER & POSTS --------
with tab1:

    st.header("📌 Posts LinkedIn (filtrés sur 24h – 200h)")
    if st.button("🔄 Récupérer les posts"):
        with st.spinner("Récupération des posts..."):
            posts = fetch_posts()

        if not posts:
            st.error("Aucun post trouvé.")
        else:
            st.success(f"{len(posts)} posts trouvés ✔️")

            companies = {}
            for p in posts:
                companies.setdefault(p["company"], []).append(p)

            # Mémoriser les posts
            st.session_state["active_posts"] = {p["id"]: True for p in posts}
            st.session_state["posts_data"] = posts

    if "posts_data" not in st.session_state:
        st.info("Clique sur le bouton pour afficher les posts.")
    else:
        posts = st.session_state["posts_data"]

        companies = {}
        for p in posts:
            companies.setdefault(p["company"], []).append(p)

        for company, items in companies.items():
            st.subheader(f"🏢 {company}")

            for item in items:
                include_key = f"include_{item['id']}"

                if include_key not in st.session_state:
                    st.session_state[include_key] = True  # Par défaut : inclus

                with st.container(border=True):
                    st.checkbox("Inclure ce post", key=include_key)

                    title, summary = smart_title_and_summary(item["text"])

                    st.markdown(f"### {title}")
                    st.write(summary)

                    if item["image"]:
                        st.image(item["image"], use_column_width=True)

                    st.markdown(f"[🔗 Voir le post]({item['link']})")
                    st.write("---")


# -------- TAB 2 : NEWSLETTER --------
with tab2:
    st.header("📰 Génération de newsletter")

    if st.button(" Générer la newsletter"):
        if "posts_data" not in st.session_state:
            st.error("Aucun post disponible.")
            st.stop()

        posts = [p for p in st.session_state["posts_data"]
                 if st.session_state.get(f"include_{p['id']}", True)]

        if not posts:
            st.error("Aucun post sélectionné !")
            st.stop()

        companies = {}
        for p in posts:
            companies.setdefault(p["company"], []).append(p)

        context = ""
        for company, items in companies.items():
            context += f"\n\n### {company}\n"
            for item in items:
                title, summary = smart_title_and_summary(item["text"])
                context += f"- **{title}** : {summary}\n"

        prompt = f"""
Tu es un analyste stratégique spécialisé dans le secteur spatial européen.
Génère une newsletter professionnelle basée uniquement sur ces posts :

{context}

Format :
# <Titre>
## Synthèse stratégique
...
"""

        newsletter = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        ).choices[0].message.content

        st.markdown(newsletter)

        st.download_button(
            "📥 Télécharger la newsletter",
            newsletter,
            "newsletter.txt",
            "text/plain"
        )