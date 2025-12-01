import streamlit as st
import requests
from datetime import datetime, timedelta
from openai import OpenAI
import os

# -------- CONFIG --------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
APP_PASSWORD = os.getenv("APP_PASSWORD")
DATASET_URL = "https://api.apify.com/v2/actor-tasks/purple_neck~linkedin-company-posts-batch-scraper-no-cookies-task/runs/last/dataset/items?format=json&clean=true"
WINDOW_HOURS = 200
client = OpenAI(api_key=OPENAI_KEY)


# -------- CUSTOM CSS DESIGN --------
CUSTOM_CSS = """
<style>

html, body, [class*="css"]  {
    font-family: "SF Pro Display", sans-serif;
}

body {
    background: radial-gradient(circle at 20% 20%, #0d1b2a 0%, #000814 70%);
    color: #e6e6e6;
}

section.main > div {
    padding-top: 2rem;
}

h1, h2, h3 {
    font-weight: 600;
    color: #e6f1ff;
}

.stButton>button {
    background: linear-gradient(90deg, #003f88, #0077b6);
    border-radius: 12px;
    padding: 0.6rem 1.2rem;
    color: white;
    border: none;
    transition: 0.2s;
    font-size: 1rem;
}
.stButton>button:hover {
    background: linear-gradient(90deg, #0077b6, #0096c7);
    transform: scale(1.02);
}

.block-container {
    background: rgba(255,255,255,0.03);
    padding: 2rem;
    border-radius: 18px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.05);
}

.post-card {
    background: rgba(255,255,255,0.06);
    padding: 1rem 1.4rem;
    border-radius: 14px;
    margin-bottom: 1.2rem;
    border-left: 4px solid #00a8e8;
}

.company-title {
    font-size: 1.7rem;
    font-weight: 600;
    margin-top: 2rem;
    color: #caf0f8;
}

</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


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

    st.title("🔐 Accès sécurisé")
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

st.set_page_config(page_title="TAS LinkedIn Monitor", layout="wide")

st.title("🚀 **Thales Alenia Space – LinkedIn Monitor**")
st.caption("Interface moderne – Données LinkedIn mises à jour automatiquement via Apify.")

tab1, tab2 = st.tabs(["📌 Scraper & Résumés", "📰 Newsletter"])


# -------- TAB 1 --------
with tab1:
    st.header("📡 Derniers posts (24–200h)")

    if st.button("🔄 Actualiser les posts"):
        with st.spinner("Récupération des posts…"):
            posts = fetch_posts()

        if not posts:
            st.error("Aucun post trouvé.")
        else:
            st.success(f"{len(posts)} posts trouvés ✔️")

            companies = {}
            for p in posts:
                companies.setdefault(p["company"], []).append(p)

            for company, items in companies.items():
                st.markdown(f"<div class='company-title'>🏢 {company}</div>", unsafe_allow_html=True)

                for item in items:
                    title, summary = smart_title_and_summary(item["text"])

                    st.markdown("<div class='post-card'>", unsafe_allow_html=True)
                    st.markdown(f"### {title}")
                    st.write(summary)

                    if item["image"]:
                        st.image(item["image"], use_column_width=True)

                    st.markdown(f"[🔗 Accéder au post LinkedIn]({item['link']})")
                    st.markdown("</div>", unsafe_allow_html=True)

    st.info("Clique sur le bouton pour afficher les posts.")


# -------- TAB 2 : NEWSLETTER --------

with tab2:
    st.header("📰 Générateur de newsletter professionnelle")

    if st.button("📝 Générer la newsletter"):
        with st.spinner("Analyse des posts…"):
            posts = fetch_posts()

            if not posts:
                st.error("Aucun post disponible.")
            else:
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
Tu es un analyste stratégique spécialisé dans le spatial européen.
Produis une newsletter professionnelle basée sur ces posts :

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

                st.success("Newsletter générée")
                st.markdown(newsletter)

                st.download_button(
                    label="📥 Télécharger en .txt",
                    data=newsletter,
                    file_name="newsletter.txt",
                    mime="text/plain",
                )