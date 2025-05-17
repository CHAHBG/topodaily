# app.py (version PostgreSQL)
import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import re
from datetime import datetime, timedelta
import time
import psycopg2
from sqlalchemy import create_engine
from urllib.parse import quote_plus

# Configuration de la page
st.set_page_config(
    page_title="Gestion des Levés Topographiques",
    page_icon="📏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration de la base de données PostgreSQL
# Ces valeurs devraient être définies comme variables d'environnement pour la sécurité
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'topodb')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'password')


# Fonction pour se connecter à PostgreSQL
def get_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données: {str(e)}")
        return None


# Fonction pour obtenir un moteur SQLAlchemy pour pandas
@st.cache_resource
def get_engine():
    try:
        # Encoder le mot de passe pour gérer les caractères spéciaux
        password = quote_plus(DB_PASSWORD)
        engine = create_engine(f'postgresql://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
        return engine
    except Exception as e:
        st.error(f"Erreur lors de la création du moteur SQLAlchemy: {str(e)}")
        return None


# Fonction pour initialiser la base de données
# Fonction pour initialiser la base de données
@st.cache_resource
def init_db():
    conn = get_connection()
    if not conn:
        return

    c = conn.cursor()

    # Création de la table utilisateurs si elle n'existe pas
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE,
        phone VARCHAR(20),
        role VARCHAR(20) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Création de la table des levés topographiques avec les nouveaux champs
    c.execute('''
    CREATE TABLE IF NOT EXISTS leves (
        id SERIAL PRIMARY KEY,
        date DATE NOT NULL,
        village VARCHAR(100) NOT NULL,
        region VARCHAR(100),
        commune VARCHAR(100),
        type VARCHAR(50) NOT NULL,
        quantite INTEGER NOT NULL,
        appareil VARCHAR(100),
        topographe VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Vérification si l'utilisateur admin existe déjà
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        # Création de l'utilisateur admin par défaut
        admin_password = hashlib.sha256("admin".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                  ("admin", admin_password, "administrateur"))

    conn.commit()
    conn.close()


# Fonction pour hacher un mot de passe
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Fonction pour vérifier si un utilisateur existe et si le mot de passe est correct
def verify_user(username, password):
    conn = get_connection()
    if not conn:
        return None

    c = conn.cursor()

    hashed_password = hash_password(password)
    c.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, hashed_password))
    user = c.fetchone()

    conn.close()

    if user:
        return {"id": user[0], "username": user[1], "role": user[5]}
    return None


# Fonction pour obtenir le rôle d'un utilisateur
def get_user_role(username):
    conn = get_connection()
    if not conn:
        return None

    c = conn.cursor()

    c.execute("SELECT role FROM users WHERE username=%s", (username,))
    role = c.fetchone()

    conn.close()

    if role:
        return role[0]
    return None


# Fonction pour ajouter un nouvel utilisateur
def add_user(username, password, email, phone, role="topographe"):
    conn = get_connection()
    if not conn:
        return False, "Erreur de connexion à la base de données"

    c = conn.cursor()

    try:
        hashed_password = hash_password(password)
        c.execute("INSERT INTO users (username, password, email, phone, role) VALUES (%s, %s, %s, %s, %s)",
                  (username, hashed_password, email, phone, role))
        conn.commit()
        success = True
        message = "Compte créé avec succès!"
    except psycopg2.IntegrityError:
        conn.rollback()
        success = False
        message = "Erreur: Nom d'utilisateur ou email déjà utilisé."
    except Exception as e:
        conn.rollback()
        success = False
        message = f"Erreur: {str(e)}"

    conn.close()
    return success, message


# Fonction pour supprimer un utilisateur
def delete_user(user_id):
    conn = get_connection()
    if not conn:
        return False, "Erreur de connexion à la base de données"

    c = conn.cursor()

    try:
        # Vérifier si l'utilisateur existe
        c.execute("SELECT username FROM users WHERE id=%s", (user_id,))
        user_data = c.fetchone()

        if not user_data:
            conn.close()
            return False, "Utilisateur non trouvé."

        username = user_data[0]

        # Vérifier si l'utilisateur est l'administrateur principal
        if username == "admin":
            conn.close()
            return False, "Impossible de supprimer l'administrateur principal."

        # Supprimer l'utilisateur
        c.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
        success = True
        message = f"Utilisateur {username} supprimé avec succès!"
    except Exception as e:
        conn.rollback()
        success = False
        message = f"Erreur lors de la suppression de l'utilisateur: {str(e)}"

    conn.close()
    return success, message


# Fonction pour modifier le mot de passe d'un utilisateur
def change_password(username, new_password):
    conn = get_connection()
    if not conn:
        return False

    c = conn.cursor()

    try:
        hashed_password = hash_password(new_password)
        c.execute("UPDATE users SET password=%s WHERE username=%s", (hashed_password, username))
        conn.commit()
        success = True
    except Exception as e:
        conn.rollback()
        success = False

    conn.close()
    return success


# Fonction pour obtenir la liste des utilisateurs
def get_users():
    engine = get_engine()
    if not engine:
        return pd.DataFrame()

    query = "SELECT id, username, email, phone, role, created_at FROM users"
    try:
        users = pd.read_sql_query(query, engine)
        return users
    except Exception as e:
        st.error(f"Erreur lors de la récupération des utilisateurs: {str(e)}")
        return pd.DataFrame()


# Fonction pour ajouter un levé topographique
# Fonction pour ajouter un levé topographique
def add_leve(date, village, region, commune, type_leve, quantite, appareil, topographe):
    conn = get_connection()
    if not conn:
        return False

    c = conn.cursor()

    try:
        # Assurez-vous que quantite est un entier
        quantite = int(quantite)

        c.execute('''
        INSERT INTO leves (date, village, region, commune, type, quantite, appareil, topographe)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (date, village, region, commune, type_leve, quantite, appareil, topographe))

        conn.commit()
        success = True
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de l'ajout du levé: {str(e)}")
        success = False

    conn.close()
    return success


# Fonction pour obtenir tous les levés
@st.cache_data(ttl=60)  # Cache valide pendant 1 minute
def get_all_leves():
    engine = get_engine()
    if not engine:
        return pd.DataFrame()

    query = "SELECT * FROM leves ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine)
        return leves
    except Exception as e:
        st.error(f"Erreur lors de la récupération des levés: {str(e)}")
        return pd.DataFrame()


# Fonction pour obtenir les levés filtrés
# Fonction pour obtenir les levés filtrés
def get_filtered_leves(start_date=None, end_date=None, village=None, region=None, commune=None, type_leve=None,
                       appareil=None, topographe=None):
    engine = get_engine()
    if not engine:
        return pd.DataFrame()

    # Construire la requête SQL avec les filtres
    query = "SELECT * FROM leves WHERE 1=1"
    params = {}

    if start_date:
        query += " AND date >= %(start_date)s"
        params['start_date'] = start_date

    if end_date:
        query += " AND date <= %(end_date)s"
        params['end_date'] = end_date

    if village:
        query += " AND village = %(village)s"
        params['village'] = village

    if region:
        query += " AND region = %(region)s"
        params['region'] = region

    if commune:
        query += " AND commune = %(commune)s"
        params['commune'] = commune

    if type_leve:
        query += " AND type = %(type_leve)s"
        params['type_leve'] = type_leve

    if appareil:
        query += " AND appareil = %(appareil)s"
        params['appareil'] = appareil

    if topographe:
        query += " AND topographe = %(topographe)s"
        params['topographe'] = topographe

    query += " ORDER BY date DESC"

    try:
        leves = pd.read_sql_query(query, engine, params=params)
        return leves
    except Exception as e:
        st.error(f"Erreur lors de la récupération des levés filtrés: {str(e)}")
        return pd.DataFrame()


# Fonction pour obtenir les levés d'un topographe spécifique
def get_leves_by_topographe(topographe):
    engine = get_engine()
    if not engine:
        return pd.DataFrame()

    query = "SELECT * FROM leves WHERE topographe=%s ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine, params=(topographe,))
        return leves
    except Exception as e:
        st.error(f"Erreur lors de la récupération des levés: {str(e)}")
        return pd.DataFrame()


# Fonction pour obtenir les données uniques pour les filtres
@st.cache_data(ttl=300)
def get_filter_options():
    engine = get_engine()
    if not engine:
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": []}

    try:
        # Obtenir les villages uniques
        villages = pd.read_sql_query("SELECT DISTINCT village FROM leves ORDER BY village", engine)

        # Obtenir les régions uniques
        regions = pd.read_sql_query("SELECT DISTINCT region FROM leves WHERE region IS NOT NULL ORDER BY region",
                                    engine)

        # Obtenir les communes uniques
        communes = pd.read_sql_query("SELECT DISTINCT commune FROM leves WHERE commune IS NOT NULL ORDER BY commune",
                                     engine)

        # Obtenir les types de levés uniques
        types = pd.read_sql_query("SELECT DISTINCT type FROM leves ORDER BY type", engine)

        # Obtenir les appareils uniques
        appareils = pd.read_sql_query(
            "SELECT DISTINCT appareil FROM leves WHERE appareil IS NOT NULL ORDER BY appareil", engine)

        # Obtenir les topographes uniques
        topographes = pd.read_sql_query("SELECT DISTINCT topographe FROM leves ORDER BY topographe", engine)

        return {
            "villages": villages["village"].tolist() if not villages.empty else [],
            "regions": regions["region"].tolist() if not regions.empty else [],
            "communes": communes["commune"].tolist() if not communes.empty else [],
            "types": types["type"].tolist() if not types.empty else [],
            "appareils": appareils["appareil"].tolist() if not appareils.empty else [],
            "topographes": topographes["topographe"].tolist() if not topographes.empty else []
        }
    except Exception as e:
        st.error(f"Erreur lors de la récupération des options de filtre: {str(e)}")
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": []}


# Fonction pour supprimer un levé
def delete_leve(leve_id):
    conn = get_connection()
    if not conn:
        return False

    c = conn.cursor()

    try:
        c.execute("DELETE FROM leves WHERE id=%s", (leve_id,))
        conn.commit()
        success = True
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de la suppression du levé: {str(e)}")
        success = False

    conn.close()
    return success


# Fonction pour vérifier si un utilisateur est propriétaire d'un levé
def is_leve_owner(leve_id, username):
    conn = get_connection()
    if not conn:
        return False

    c = conn.cursor()
    c.execute("SELECT topographe FROM leves WHERE id=%s", (leve_id,))
    result = c.fetchone()
    conn.close()

    if result and result[0] == username:
        return True
    return False


# Fonction pour supprimer un levé avec vérification du propriétaire
def delete_user_leve(leve_id, username):
    # Vérifier si l'utilisateur est le propriétaire du levé
    if not is_leve_owner(leve_id, username):
        return False, "Vous n'êtes pas autorisé à supprimer ce levé."

    conn = get_connection()
    if not conn:
        return False, "Erreur de connexion à la base de données"

    c = conn.cursor()

    try:
        c.execute("DELETE FROM leves WHERE id=%s AND topographe=%s", (leve_id, username))
        if c.rowcount == 0:
            conn.close()
            return False, "Levé non trouvé ou vous n'êtes pas autorisé à le supprimer."

        conn.commit()
        success = True
        message = "Levé supprimé avec succès!"
    except Exception as e:
        conn.rollback()
        success = False
        message = f"Erreur lors de la suppression du levé: {str(e)}"

    conn.close()
    return success, message


# Fonction pour valider le format de l'email
def validate_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


# Fonction pour valider le format du numéro de téléphone
def validate_phone(phone):
    # Accepte les formats communs: +33612345678, 0612345678, etc.
    pattern = r"^(\+\d{1,3}[- ]?)?\d{9,15}$"
    return re.match(pattern, phone) is not None


# Fonction pour afficher la page de connexion
def show_login_page():
    st.title("Connexion Gestion des Levés Topographiques")

    with st.form("login_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")

        if submit:
            user = verify_user(username, password)
            if user:
                # Met à jour app_state
                st.session_state.app_state["user"] = user
                st.session_state.app_state["username"] = username
                st.session_state.app_state["authenticated"] = True
                st.session_state.app_state["show_login"] = False
                st.session_state.app_state["current_page"] = "Mon Compte"

                # Met à jour les clés globales aussi
                st.session_state.user = user
                st.session_state.authenticated = True

                st.success(f"Connexion réussie! Bienvenue {username}!")
                st.rerun()
            else:
                st.error("Nom d'utilisateur ou mot de passe incorrect.")

    st.markdown("---")
    st.markdown("Pas encore de compte? [Créer un compte](#creer-un-compte)")

    if st.button("Créer un compte"):
        st.session_state.app_state["show_login"] = False
        st.session_state.app_state["show_registration"] = True
        st.rerun()


# Fonction pour afficher la page d'inscription
def show_registration_page():
    st.title("Création de compte")

    with st.form("registration_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        confirm_password = st.text_input("Confirmer le mot de passe", type="password")
        email = st.text_input("Email")
        phone = st.text_input("Numéro de téléphone")

        submit = st.form_submit_button("S'inscrire")

        if submit:
            if not username or not password:
                st.error("Le nom d'utilisateur et le mot de passe sont obligatoires.")
            elif password != confirm_password:
                st.error("Les mots de passe ne correspondent pas.")
            elif email and not validate_email(email):
                st.error("Format d'email invalide.")
            elif phone and not validate_phone(phone):
                st.error("Format de numéro de téléphone invalide.")
            else:
                success, message = add_user(username, password, email, phone)
                if success:
                    st.success(message)
                    st.session_state.show_registration = False
                    st.rerun()
                else:
                    st.error(message)

    if st.button("Retour à la connexion"):
        st.session_state.show_registration = False
        st.rerun()


# Fonction pour afficher la sidebar de navigation
def show_navigation_sidebar():
    st.sidebar.title("Navigation")

    # Si l'utilisateur est connecté
    app_state = st.session_state.app_state

    if app_state["authenticated"]:
        user_role = app_state["user"]["role"]
        username = app_state["username"]

        st.sidebar.write(f"Connecté en tant que: **{username}**")
        st.sidebar.write(f"Rôle: **{user_role}**")

        # Conserver le choix de page courant
        current_idx = ["Dashboard", "Saisie des Levés", "Suivi", "Mon Compte"].index(app_state["current_page"]) if \
        app_state["current_page"] in ["Dashboard", "Saisie des Levés", "Suivi", "Mon Compte"] else 0

        # Pages accessibles à tous les utilisateurs connectés
        page = st.sidebar.radio(
            "Pages",
            ["Dashboard", "Saisie des Levés", "Suivi", "Mon Compte"],
            index=current_idx
        )

        # Menu d'administration pour l'admin
        if user_role == "administrateur":
            admin_page = st.sidebar.radio(
                "Administration",
                ["Aucune", "Gestion des Utilisateurs", "Gestion des Données"],
                index=0
            )
            if admin_page == "Gestion des Utilisateurs":
                page = "Admin Users"
            elif admin_page == "Gestion des Données":
                page = "Admin Data"

        # Bouton déconnexion
        if st.sidebar.button("Déconnexion"):
            st.session_state.app_state = {
                "authenticated": False,
                "username": None,
                "user": None,
                "current_page": "Dashboard",
                "show_login": False,
                "show_registration": False
            }
            st.rerun()

    else:
        # Utilisateur non connecté
        page = st.sidebar.radio(
            "Pages",
            ["Dashboard"],
            index=0
        )

        st.sidebar.markdown("---")
        st.sidebar.info("Connectez-vous pour accéder à toutes les fonctionnalités.")

        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Se connecter"):
                st.session_state.app_state["show_login"] = True
                st.session_state.app_state["show_registration"] = False
                st.rerun()
        with col2:
            if st.sidebar.button("S'inscrire"):
                st.session_state.app_state["show_login"] = False
                st.session_state.app_state["show_registration"] = True
                st.rerun()

    # Vérifier si la page a changé et déclencher un rechargement
    if app_state["current_page"] != page:
        app_state["current_page"] = page
        st.rerun()  # Ajout d'un st.rerun() ici pour actualiser immédiatement

    return page


# Fonction pour afficher le dashboard
def show_dashboard():
    st.title("Dashboard des Levés Topographiques")

    @st.cache_data(ttl=600)
    def get_cached_leves():
        return get_all_leves()

    leves_df = get_cached_leves()

    if not leves_df.empty:
        leves_df['date'] = pd.to_datetime(leves_df['date'])

        with st.expander("Filtres", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Date de début", datetime.now() - timedelta(days=30))
            with col2:
                end_date = st.date_input("Date de fin", datetime.now())

            mask_date = (leves_df['date'] >= pd.Timestamp(start_date)) & (leves_df['date'] <= pd.Timestamp(end_date))
            leves_filtered = leves_df[mask_date]

            col1, col2, col3 = st.columns(3)

            with col1:
                filter_options = get_filter_options()
                region_options = ["Toutes"] + filter_options["regions"]
                region_filter = st.selectbox("Région", options=region_options, index=0)
                if region_filter != "Toutes" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['region'] == region_filter]

            with col2:
                commune_options = ["Toutes"] + filter_options["communes"]
                commune_filter = st.selectbox("Commune", options=commune_options, index=0)
                if commune_filter != "Toutes" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['commune'] == commune_filter]

            with col3:
                type_options = ["Tous"] + filter_options["types"]
                type_filter = st.selectbox("Type de levé", options=type_options, index=0)
                if type_filter != "Tous" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['type'] == type_filter]

            col1, col2 = st.columns(2)

            with col1:
                appareil_options = ["Tous"] + filter_options["appareils"]
                appareil_filter = st.selectbox("Appareil", options=appareil_options, index=0)
                if appareil_filter != "Tous" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['appareil'] == appareil_filter]

            with col2:
                village_options = ["Tous"] + filter_options["villages"]
                village_filter = st.selectbox("Village", options=village_options, index=0)
                if village_filter != "Tous" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['village'] == village_filter]

        if leves_filtered.empty:
            st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
            leves_filtered = leves_df

        tabs = st.tabs(["Statistiques Générales", "Répartition Géographique", "Évolution Temporelle", "Performance"])

        with tabs[0]:
            st.subheader("Aperçu des statistiques globales")
            col1, col2, col3 = st.columns(3)
            total_quantite = leves_filtered['quantite'].sum()
            moyenne_quantite = leves_filtered['quantite'].mean()

            with col1:
                st.metric("Nombre Total de Levés", len(leves_filtered))
            with col2:
                st.metric("Quantité Totale", f"{total_quantite:,.0f}")
            with col3:
                st.metric("Moyenne par Levé", f"{moyenne_quantite:.2f}")

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Levés par Type (Quantité Totale)")
                if not leves_filtered.empty:
                    type_counts = leves_filtered.groupby('type')['quantite'].sum().reset_index()
                    type_counts.columns = ['Type', 'Quantité']

                    fig = px.pie(type_counts, values='Quantité', names='Type',
                                 title='Répartition des types de levés (quantité)', hole=0.3)
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True, height=300)
                else:
                    st.info("Aucune donnée disponible pour ce filtre.")

            with col2:
                st.subheader("Top des Topographes")
                if not leves_filtered.empty:
                    topo_quantites = leves_filtered.groupby('topographe')['quantite'].sum().reset_index().sort_values(
                        'quantite', ascending=False).head(10)
                    topo_quantites.columns = ['Topographe', 'Quantité Totale']

                    fig = px.bar(topo_quantites, x='Topographe', y='Quantité Totale',
                                 title='Top 10 des topographes par quantité totale', color='Quantité Totale',
                                 color_continuous_scale='Viridis')
                    fig.update_layout(xaxis={'categoryorder': 'total descending'}, height=350,
                                      margin=dict(l=40, r=40, t=60, b=80))
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucune donnée disponible pour ce filtre.")

        with tabs[1]:
            st.subheader("Répartition géographique des levés")

            col1, col2 = st.columns(2)

            with col1:
                if not leves_filtered.empty and 'region' in leves_filtered.columns and leves_filtered[
                    'region'].notna().any():
                    st.subheader("Levés par Région")
                    region_counts = leves_filtered.groupby('region')['quantite'].sum().reset_index().sort_values(
                        'quantite', ascending=False)
                    region_counts.columns = ['Région', 'Quantité']

                    fig = px.pie(region_counts, values='Quantité', names='Région',
                                 title='Répartition des levés par région (quantité totale)', hole=0.3)
                    fig.update_traces(textposition='inside', textinfo='percent')
                    st.plotly_chart(fig, use_container_width=True, height=300)
                else:
                    st.info("Aucune donnée de région disponible.")

            with col2:
                st.subheader("Levés par Village")
                if not leves_filtered.empty:
                    village_counts = leves_filtered.groupby('village')['quantite'].sum().reset_index().sort_values(
                        'quantite', ascending=False).head(10)
                    village_counts.columns = ['Village', 'Quantité']

                    fig = px.bar(village_counts, x='Village', y='Quantité',
                                 title='Top 10 des villages (quantité totale)', color='Quantité',
                                 color_continuous_scale='Viridis')
                    fig.update_layout(xaxis={'categoryorder': 'total descending'}, height=350,
                                      margin=dict(l=40, r=40, t=60, b=80))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucune donnée disponible pour ce filtre.")

            if 'commune' in leves_filtered.columns and leves_filtered['commune'].notna().any():
                st.subheader("Répartition par Commune")
                commune_counts = leves_filtered.groupby('commune')['quantite'].sum().reset_index().sort_values(
                    'quantite', ascending=False)
                commune_counts.columns = ['Commune', 'Quantité']

                fig = px.bar(commune_counts.head(15), x='Commune', y='Quantité',
                             title='Top 15 des communes (quantité totale)', color='Quantité',
                             color_continuous_scale='Viridis')
                fig.update_layout(xaxis={'categoryorder': 'total descending'}, height=350,
                                  margin=dict(l=40, r=40, t=60, b=80))
                if len(commune_counts) > 10:
                    fig.update_layout(
                        xaxis=dict(tickmode='array', tickvals=list(range(0, len(commune_counts.head(15)), 2))))
                st.plotly_chart(fig, use_container_width=True)

        with tabs[2]:
            st.subheader("Analyse temporelle des levés")
            if not leves_filtered.empty:
                st.subheader("Évolution des Levés dans le Temps")
                time_series = leves_filtered.groupby(pd.Grouper(key='date', freq='D'))['quantite'].sum().reset_index()
                time_series.columns = ['Date', 'Quantité']

                fig = px.line(time_series, x='Date', y='Quantité',
                              title='Évolution quotidienne des levés (quantité totale)', markers=True)
                fig.update_layout(xaxis_title='Date', yaxis_title='Quantité levée', height=350,
                                  margin=dict(l=40, r=40, t=60, b=40))
                fig.update_xaxes(tickangle=45, nticks=10, tickformat="%d %b")
                st.plotly_chart(fig, use_container_width=True)

                monthly_series = leves_filtered.groupby(pd.Grouper(key='date', freq='M'))[
                    'quantite'].sum().reset_index()
                monthly_series.columns = ['Mois', 'Quantité']
                monthly_series['Mois'] = monthly_series['Mois'].dt.strftime('%b %Y')

                fig = px.bar(monthly_series, x='Mois', y='Quantité',
                             title='Évolution mensuelle des levés (quantité totale)', color='Quantité',
                             color_continuous_scale='Viridis')
                fig.update_layout(height=350, margin=dict(l=40, r=40, t=60, b=80))
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour analyser l'évolution temporelle.")

        with tabs[3]:
            st.subheader("Performance et efficacité")

            col1, col2 = st.columns(2)

            with col1:
                if 'appareil' in leves_filtered.columns and leves_filtered['appareil'].notna().any():
                    st.subheader("Levés par Appareil")
                    appareil_counts = leves_filtered.groupby('appareil')['quantite'].sum().reset_index().sort_values(
                        'quantite', ascending=False)
                    appareil_counts.columns = ['Appareil', 'Quantité']

                    fig = px.bar(appareil_counts, x='Appareil', y='Quantité',
                                 title='Répartition des levés par appareil (quantité totale)', color='Quantité',
                                 color_continuous_scale='Viridis')
                    fig.update_layout(xaxis={'categoryorder': 'total descending'}, height=350,
                                      margin=dict(l=40, r=40, t=60, b=80))
                    if len(appareil_counts) > 8:
                        fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucune donnée d'appareil disponible.")

            with col2:
                if not leves_filtered.empty:
                    st.subheader("Efficacité par Topographe")
                    topo_perf = leves_filtered.groupby('topographe')['quantite'].agg(['mean', 'count']).reset_index()
                    topo_perf.columns = ['Topographe', 'Moyenne', 'Nombre de levés']
                    topo_perf = topo_perf[topo_perf['Nombre de levés'] >= 5].sort_values('Moyenne',
                                                                                         ascending=False).head(10)

                    fig = px.bar(topo_perf, x='Topographe', y='Moyenne',
                                 title='Top 10 des topographes par quantité moyenne par levé', color='Nombre de levés',
                                 color_continuous_scale='Viridis')
                    fig.update_layout(xaxis={'categoryorder': 'total descending'}, height=350,
                                      margin=dict(l=40, r=40, t=60, b=80))
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucune donnée disponible pour ce filtre.")

        # Bouton central pour saisir des levés
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Saisir un nouveau levé", use_container_width=True):
                if st.session_state.get("authenticated", False):
                    st.session_state.current_page = "Saisie des Levés"
                    st.rerun()
                else:
                    st.session_state.app_state["show_login"] = True
                    st.session_state.app_state["show_registration"] = False
                    st.warning("Veuillez vous connecter pour saisir des levés.")
                    st.rerun()
    else:
        st.info("Aucun levé n'a encore été enregistré. Commencez par saisir des données.")

        # Bouton central pour saisir des levés
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Saisir un nouveau levé", use_container_width=True):
                if st.session_state.get("authenticated", False):
                    st.session_state.current_page = "Saisie des Levés"
                    st.rerun()
                else:
                    st.session_state.app_state["show_login"] = True
                    st.session_state.app_state["show_registration"] = False
                    st.warning("Veuillez vous connecter pour saisir des levés.")
                    st.rerun()


# Fonction pour afficher la page de saisie des levés
def show_saisie_page():
    st.title("Saisie des Levés Topographiques")

    # Initialisation des variables de session si nécessaire
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0
    if "form_submitted" not in st.session_state:
        st.session_state.form_submitted = False
    if "villages_data" not in st.session_state:
        # Chargement du fichier Excel des villages
        load_villages_data()

    # Vérification que l'utilisateur est connecté
    if not st.session_state.app_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour accéder à cette page.")
        st.session_state.app_state["show_login"] = True
        st.rerun()
        return

    # Gestion des messages de succès après soumission
    if st.session_state.get("form_submitted", False):
        st.success("Levé enregistré avec succès!")
        st.session_state.form_submitted = False

    # Bandeau d'information utilisateur
    st.info(f"Connecté en tant que: {st.session_state.app_state['username']}")

    # Boutons d'action
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Nouveau levé", key="new_leve_btn"):
            # Réinitialiser le formulaire
            st.session_state.form_key += 1
            st.session_state.cached_form_data = {
                "region": "", "commune": "", "village": "", "appareil": "",
                "type_leve": 0, "quantite": 1
            }
            st.rerun()
    with col2:
        if st.button("Voir mes levés", key="view_leves_btn"):
            st.session_state.app_state["current_page"] = "Suivi"
            st.rerun()

    # Initialisation du cache si nécessaire
    if "cached_form_data" not in st.session_state:
        st.session_state.cached_form_data = {
            "region": "", "commune": "", "village": "", "appareil": "",
            "type_leve": 0, "quantite": 1
        }

    # Création de callbacks pour les changements de sélection
    def on_region_change():
        selected_region = st.session_state.region_select
        if selected_region != st.session_state.cached_form_data.get("region", ""):
            st.session_state.cached_form_data["region"] = selected_region
            st.session_state.cached_form_data["commune"] = ""
            st.session_state.cached_form_data["village"] = ""
            st.rerun()

    def on_commune_change():
        selected_commune = st.session_state.commune_select
        if selected_commune != st.session_state.cached_form_data.get("commune", ""):
            st.session_state.cached_form_data["commune"] = selected_commune
            st.session_state.cached_form_data["village"] = ""
            st.rerun()

    # Affichage du formulaire des levés topographiques
    with st.form(key=f"leve_form_{st.session_state.form_key}"):
        st.subheader("Nouveau levé topographique")
        # La date du jour est préremplie
        date = st.date_input("Date du levé", datetime.now())

        # Nom du topographe prérempli avec le nom de l'utilisateur connecté
        topographe = st.session_state.app_state["username"]
        st.write(f"Topographe: **{topographe}**")

        # Initialisation du cache si nécessaire
        if "cached_form_data" not in st.session_state:
            st.session_state.cached_form_data = {
                "region": "", "commune": "", "village": "", "appareil": "",
                "type_leve": 0, "quantite": 1
            }

        # Disposition en colonnes pour la localisation
        col1, col2 = st.columns(2)
        
        with col1:
            # Sélection de la région (liste déroulante avec recherche)
            region_options = [""] + sorted(list(st.session_state.villages_data.keys()))
            region = st.selectbox(
                "Région",
                options=region_options,
                index=get_index_or_default(region_options, st.session_state.cached_form_data.get("region", "")),
                key="region_select",
                on_change=on_region_change
            )
            
            # Sélection du village (liste déroulante avec recherche)
            village_options = [""]
            current_region = st.session_state.cached_form_data.get("region", "")
            current_commune = st.session_state.cached_form_data.get("commune", "")
            
            if current_region and current_commune:
                if current_commune in st.session_state.villages_data.get(current_region, {}):
                    village_options += sorted(st.session_state.villages_data[current_region][current_commune])
            
            village = st.selectbox(
                "Village",
                options=village_options,
                index=get_index_or_default(village_options, st.session_state.cached_form_data.get("village", "")),
                key="village_select"
            )
            
        with col2:
            # Sélection de la commune (liste déroulante avec recherche)
            commune_options = [""]
            current_region = st.session_state.cached_form_data.get("region", "")
            
            if current_region:
                commune_options += sorted(list(st.session_state.villages_data.get(current_region, {}).keys()))
            
            commune = st.selectbox(
                "Commune",
                options=commune_options,
                index=get_index_or_default(commune_options, st.session_state.cached_form_data.get("commune", "")),
                key="commune_select",
                on_change=on_commune_change
            )

        # Disposition en colonnes pour les autres champs
        col1, col2 = st.columns(2)
        
        with col1:
            # Liste déroulante pour les appareils avec options prédéfinies
            appareil_options = ["LT60H", "TRIMBLE", "AUTRE"]
            
            # Gérer la valeur de l'appareil dans le cache
            cached_appareil = st.session_state.cached_form_data.get("appareil", "")
            
            # Déterminer l'index initial pour la liste déroulante
            if cached_appareil in appareil_options:
                appareil_index = appareil_options.index(cached_appareil)
            elif cached_appareil:  # Si une valeur personnalisée est présente
                appareil_options.append(cached_appareil)  # Ajouter la valeur personnalisée temporairement
                appareil_index = len(appareil_options) - 1
            else:
                appareil_index = 0
            
            appareil = st.selectbox(
                "Appareil utilisé",
                options=appareil_options,
                index=appareil_index,
                key="appareil_select"
            )
            
            # Champ de texte pour "AUTRE" appareil
            if appareil == "AUTRE":
                appareil_autre = st.text_input(
                    "Précisez l'appareil",
                    value=cached_appareil if cached_appareil not in ["LT60H", "TRIMBLE", "AUTRE"] else "",
                    placeholder="Nom de l'appareil",
                    key="appareil_autre"
                )
                if appareil_autre:
                    appareil = appareil_autre
        
        with col2:
            # Types de levés prédéfinis avec valeur par défaut
            type_options = ["Batîments", "Champs", "Edifice publique", "Autre"]
            type_index = st.session_state.cached_form_data.get("type_leve", 0)
            type_leve = st.selectbox(
                "Type de levé",
                options=type_options,
                index=min(type_index, len(type_options) - 1)  # Éviter l'index out of range
            )

        # Quantité avec valeur minimale et par défaut
        quantite = st.number_input(
            "Quantité",
            min_value=1,
            value=st.session_state.cached_form_data.get("quantite", 1),
            step=1
        )

        # Bouton de soumission
        submit = st.form_submit_button("Enregistrer le levé")

        if submit:
            # Mise en cache des données en cas d'échec
            st.session_state.cached_form_data = {
                "region": region, "commune": commune, "village": village,
                "appareil": appareil, "type_leve": type_options.index(type_leve),
                "quantite": quantite
            }

            # Validation
            if not village:
                st.error("Veuillez sélectionner un village.")
            elif not region:
                st.error("Veuillez sélectionner une région.")
            elif not commune:
                st.error("Veuillez sélectionner une commune.")
            else:
                # Conversion de la date au format string
                date_str = date.strftime("%Y-%m-%d")

                # Enregistrement du levé
                success = add_leve(date_str, village, region, commune, type_leve, quantite, appareil, topographe)
                if success:
                    # Marquer comme soumis pour afficher le message de succès
                    st.session_state.form_submitted = True
                    # Réinitialiser le cache
                    st.session_state.cached_form_data = {
                        "region": "", "commune": "", "village": "", "appareil": "",
                        "type_leve": 0, "quantite": 1
                    }
                    # Incrémenter la clé pour réinitialiser le formulaire
                    st.session_state.form_key += 1
                    st.rerun()
                else:
                    st.error("Erreur lors de l'enregistrement du levé.")


def load_villages_data():
    """Charge les données des villages depuis le fichier Excel"""
    import pandas as pd
    import io
    import logging

    try:
        # Lire le fichier Excel
        excel_file = "Villages.xlsx"
        df = pd.read_excel(excel_file)
        
        # Afficher les informations sur le fichier Excel (pour débogage)
        logging.info(f"Fichier Excel chargé: {excel_file}")
        logging.info(f"Colonnes trouvées: {df.columns.tolist()}")
        logging.info(f"Nombre de lignes: {len(df)}")
        
        # Nettoyer les noms de colonnes (convertir en minuscules)
        df.columns = [col.lower() for col in df.columns]
        
        # Vérifier que les colonnes nécessaires existent
        required_columns = ['village', 'commune', 'region']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Le fichier Excel ne contient pas la colonne requise: {col}")
                st.session_state.villages_data = {}
                return False
        
        # Structurer les données en hiérarchie: région -> commune -> villages
        villages_data = {}
        
        for _, row in df.iterrows():
            region = row['region']
            commune = row['commune']
            village = row['village']
            
            # Ignorer les lignes avec des valeurs manquantes
            if pd.isna(region) or pd.isna(commune) or pd.isna(village):
                continue
                
            # Convertir en string pour éviter les problèmes
            region = str(region).strip()
            commune = str(commune).strip()
            village = str(village).strip()
            
            # Initialiser la région si elle n'existe pas encore
            if region not in villages_data:
                villages_data[region] = {}
            
            # Initialiser la commune si elle n'existe pas encore
            if commune not in villages_data[region]:
                villages_data[region][commune] = []
            
            # Ajouter le village à la commune s'il n'existe pas déjà
            if village not in villages_data[region][commune]:
                villages_data[region][commune].append(village)
        
        # Trier les listes de villages par ordre alphabétique
        for region in villages_data:
            for commune in villages_data[region]:
                villages_data[region][commune].sort()
        
        # Stocker les données dans la session
        st.session_state.villages_data = villages_data
        logging.info(f"Données chargées: {len(villages_data)} régions")
        return True
    
    except Exception as e:
        # En cas d'erreur, créer une structure vide
        st.session_state.villages_data = {}
        st.error(f"Erreur lors du chargement des villages: {str(e)}")
        return False


def get_index_or_default(options_list, value, default=0):
    """Récupère l'index d'une valeur dans une liste, ou renvoie la valeur par défaut"""
    try:
        return options_list.index(value)
    except ValueError:
        return default

def show_login_form():
    """Fonction séparée pour afficher le formulaire de connexion"""
    st.warning("Vous devez être connecté pour saisir des levés.")

    # Afficher le formulaire de connexion
    with st.form("login_form_embed"):
        st.subheader("Connexion")
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")

        if submit:
            user = verify_user(username, password)
            if user:
                st.session_state.user = user
                st.session_state.username = username
                st.session_state.authenticated = True
                st.success(f"Connexion réussie! Bienvenue {username}!")
                st.rerun()
            else:
                st.error("Nom d'utilisateur ou mot de passe incorrect.")

    st.markdown("---")
    st.markdown("Pas encore de compte? Cliquez sur 'S'inscrire' dans le menu latéral.")


# Fonction pour afficher la page de suivi
# Fonction pour afficher la page de suivi
def show_suivi_page():
    st.title("Suivi des Levés Topographiques")

    # Vérification que l'utilisateur est connecté
    if not st.session_state.app_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour accéder au suivi.")
        st.session_state.app_state["show_login"] = True
        st.rerun()
        return

    # Récupération des options de filtre
    filter_options = get_filter_options()

    # Colonne pour les filtres
    with st.expander("Filtres", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Date de début", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Date de fin", datetime.now())

        col1, col2, col3 = st.columns(3)
        with col1:
            village_options = ["Tous"] + filter_options["villages"]
            village = st.selectbox("Village", options=village_options)
            village = None if village == "Tous" else village

            region_options = ["Toutes"] + filter_options["regions"]
            region = st.selectbox("Région", options=region_options)
            region = None if region == "Toutes" else region

        with col2:
            commune_options = ["Toutes"] + filter_options["communes"]
            commune = st.selectbox("Commune", options=commune_options)
            commune = None if commune == "Toutes" else commune

            type_options = ["Tous"] + filter_options["types"]
            type_leve = st.selectbox("Type de levé", options=type_options)
            type_leve = None if type_leve == "Tous" else type_leve

        with col3:
            appareil_options = ["Tous"] + filter_options["appareils"]
            appareil = st.selectbox("Appareil", options=appareil_options)
            appareil = None if appareil == "Tous" else appareil

            # Pour les administrateurs, afficher tous les topographes
            # Pour les autres, voir uniquement ses propres levés
            if st.session_state.app_state["user"]["role"] == "administrateur":
                topo_options = ["Tous"] + filter_options["topographes"]
                topographe = st.selectbox("Topographe", options=topo_options)
                topographe = None if topographe == "Tous" else topographe
            else:
                topographe = st.session_state.app_state["username"]
                st.write(f"Topographe: **{topographe}**")

    # Récupération des levés filtrés
    leves_df = get_filtered_leves(start_date, end_date, village, region, commune, type_leve, appareil, topographe)

    # Affichage des données
    if not leves_df.empty:
        # Renommage des colonnes pour un affichage plus convivial
        leves_df = leves_df.rename(columns={
            'id': 'ID',
            'date': 'Date',
            'village': 'Village',
            'region': 'Région',
            'commune': 'Commune',
            'type': 'Type',
            'quantite': 'Quantité',
            'appareil': 'Appareil',
            'topographe': 'Topographe',
            'created_at': 'Date de création'
        })

        # Formatage des dates
        leves_df['Date'] = pd.to_datetime(leves_df['Date']).dt.strftime('%d/%m/%Y')

        # Affichage des données avec une mise en forme améliorée
        st.dataframe(
            leves_df[['ID', 'Date', 'Village', 'Région', 'Commune', 'Type', 'Quantité', 'Appareil', 'Topographe']],
            use_container_width=True,
            height=400
        )

        # Statistiques sur les données filtrées
        st.subheader("Statistiques")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre Total de Levés", len(leves_df))
        with col2:
            st.metric("Quantité Totale", f"{leves_df['Quantité'].sum():,.0f}")
        with col3:
            st.metric("Moyenne par Levé", f"{leves_df['Quantité'].mean():.2f}")

        # Option d'export
        if st.download_button(
                label="Télécharger les données en CSV",
                data=leves_df.to_csv(index=False).encode('utf-8'),
                file_name=f"leves_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv'
        ):
            st.success("Export réussi!")

        # Pour les utilisateurs normaux, possibilité de supprimer ses propres levés
        if st.session_state.app_state["user"]["role"] != "administrateur":
            st.subheader("Gestion de mes levés")

            with st.form("delete_own_leve_form"):
                leve_id = st.number_input("ID du levé à supprimer", min_value=1, step=1)
                delete_submit = st.form_submit_button("Supprimer mon levé")

                if delete_submit:
                    success, message = delete_user_leve(leve_id, st.session_state.app_state["username"])
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

        # Pour les administrateurs, possibilité de supprimer des levés
        if st.session_state.app_state["user"]["role"] == "administrateur":
            st.subheader("Gestion des Levés (Admin)")

            with st.form("delete_leve_form"):
                leve_id = st.number_input("ID du levé à supprimer", min_value=1, step=1)
                delete_submit = st.form_submit_button("Supprimer le levé")

                if delete_submit:
                    if delete_leve(leve_id):
                        st.success(f"Levé {leve_id} supprimé avec succès!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erreur lors de la suppression du levé. Vérifiez l'ID.")
    else:
        st.info("Aucun levé ne correspond aux critères de recherche sélectionnés.")


# Fonction pour afficher la page de mon compte
def show_account_page():
    st.title("Mon Compte")

    # Vérification que l'utilisateur est connecté
    if not st.session_state.app_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour accéder à votre compte.")
        st.session_state.app_state["show_login"] = True
        st.rerun()
        return

    username = st.session_state.app_state["username"]
    role = st.session_state.app_state["user"]["role"]

    st.write(f"**Nom d'utilisateur:** {username}")
    st.write(f"**Rôle:** {role}")

    # Formulaire de changement de mot de passe
    st.subheader("Changer de mot de passe")
    with st.form("change_password_form"):
        old_password = st.text_input("Ancien mot de passe", type="password")
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm_password = st.text_input("Confirmer le nouveau mot de passe", type="password")
        submit = st.form_submit_button("Changer le mot de passe")

        if submit:
            if not old_password or not new_password or not confirm_password:
                st.error("Tous les champs sont obligatoires.")
            elif new_password != confirm_password:
                st.error("Les nouveaux mots de passe ne correspondent pas.")
            else:
                # Vérifier que l'ancien mot de passe est correct
                user = verify_user(username, old_password)
                if not user:
                    st.error("Ancien mot de passe incorrect.")
                else:
                    # Mettre à jour le mot de passe
                    if change_password(username, new_password):
                        st.success("Mot de passe changé avec succès!")
                    else:
                        st.error("Erreur lors du changement de mot de passe.")

    # Statistiques personnelles pour le topographe
    st.subheader("Mes Statistiques")

    # Récupérer les levés de l'utilisateur
    leves_df = get_leves_by_topographe(username)

    if not leves_df.empty:
        # Convertir la colonne date en datetime pour les analyses
        leves_df['date'] = pd.to_datetime(leves_df['date'])

        # Métriques principales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre Total de Levés", len(leves_df))
        with col2:
            st.metric("Quantité Totale", f"{leves_df['quantite'].sum():,.0f}")
        with col3:
            st.metric("Moyenne par Levé", f"{leves_df['quantite'].mean():.2f}")

        # Graphique d'évolution des levés dans le temps
        st.subheader("Évolution de mes levés")
        time_series = leves_df.groupby(pd.Grouper(key='date', freq='D')).size().reset_index()
        time_series.columns = ['Date', 'Nombre']

        fig = px.line(
            time_series,
            x='Date',
            y='Nombre',
            title='Évolution quotidienne de mes levés',
            markers=True
        )
        fig.update_layout(xaxis_title='Date', yaxis_title='Nombre de levés')
        st.plotly_chart(fig, use_container_width=True)

        # Répartition par type de levé
        st.subheader("Répartition par type de levé")
        type_counts = leves_df['type'].value_counts().reset_index()
        type_counts.columns = ['Type', 'Nombre']

        fig = px.pie(
            type_counts,
            values='Nombre',
            names='Type',
            title='Répartition des types de levés',
            hole=0.3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Vous n'avez pas encore enregistré de levés.")


# Fonction pour afficher la page d'administration des utilisateurs
def show_admin_users_page():
    st.title("Administration - Gestion des Utilisateurs")

    # Vérification que l'utilisateur est connecté et est admin
    if not st.session_state.get("authenticated", False) or st.session_state.user["role"] != "administrateur":
        st.error("Accès non autorisé. Cette page est réservée aux administrateurs.")
        return

    # Récupération de la liste des utilisateurs
    users_df = get_users()

    if not users_df.empty:
        # Renommage des colonnes pour un affichage plus convivial
        users_df = users_df.rename(columns={
            'id': 'ID',
            'username': 'Nom d\'utilisateur',
            'email': 'Email',
            'phone': 'Téléphone',
            'role': 'Rôle',
            'created_at': 'Date de création'
        })

        # Formatage des dates
        if 'Date de création' in users_df.columns:
            users_df['Date de création'] = pd.to_datetime(users_df['Date de création']).dt.strftime('%d/%m/%Y %H:%M')

        # Affichage des utilisateurs
        st.dataframe(users_df, use_container_width=True)

        # Formulaire pour la suppression d'un utilisateur
        st.subheader("Supprimer un utilisateur")
        with st.form("delete_user_form"):
            user_id = st.number_input("ID de l'utilisateur à supprimer", min_value=1, step=1)
            delete_submit = st.form_submit_button("Supprimer l'utilisateur")

            if delete_submit:
                success, message = delete_user(user_id)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    else:
        st.info("Aucun utilisateur n'a été trouvé.")

    # Formulaire pour l'ajout d'un nouvel utilisateur
    st.subheader("Ajouter un nouvel utilisateur")
    with st.form("add_user_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        email = st.text_input("Email (optionnel)")
        phone = st.text_input("Téléphone (optionnel)")
        role = st.selectbox("Rôle", options=["topographe", "administrateur"])

        submit = st.form_submit_button("Ajouter l'utilisateur")

        if submit:
            if not username or not password:
                st.error("Le nom d'utilisateur et le mot de passe sont obligatoires.")
            elif email and not validate_email(email):
                st.error("Format d'email invalide.")
            elif phone and not validate_phone(phone):
                st.error("Format de numéro de téléphone invalide.")
            else:
                success, message = add_user(username, password, email, phone, role)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


# Fonction pour afficher la page d'administration des données
def show_admin_data_page():
    st.title("Administration - Gestion des Données")

    # Vérification que l'utilisateur est connecté et est admin
    if not st.session_state.get("authenticated", False) or st.session_state.user["role"] != "administrateur":
        st.error("Accès non autorisé. Cette page est réservée aux administrateurs.")
        return

    # Fonctionnalité de sauvegarde et restauration (à implanter avec PostgreSQL)
    st.subheader("Maintenance de la Base de Données")

    col1, col2 = st.columns(2)

    with col1:
        st.info("Pour PostgreSQL, la sauvegarde se fait via pg_dump. Consultez la documentation PostgreSQL.")

    with col2:
        st.info("La restauration de PostgreSQL se fait via pg_restore ou psql. Consultez la documentation PostgreSQL.")

    # Afficher les statistiques globales
    st.subheader("Statistiques Globales")

    # Récupération des données
    leves_df = get_all_leves()
    users_df = get_users()

    if not leves_df.empty and not users_df.empty:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Nombre d'utilisateurs", len(users_df))

        with col2:
            st.metric("Nombre de levés", len(leves_df))

        with col3:
            st.metric("Quantité totale", f"{leves_df['quantite'].sum():,.0f}")

        with col4:
            # Calculer le nombre de villages uniques
            nb_villages = leves_df['village'].nunique()
            st.metric("Nombre de villages", nb_villages)
    else:
        st.info("Pas assez de données pour afficher les statistiques.")


# Programme principal
def main():
    # Initialisation de la base de données
    init_db()

    # Initialisation des variables de session si elles n'existent pas
    if "app_state" not in st.session_state:
        st.session_state.app_state = {
            "authenticated": False,
            "username": None,
            "user": None,
            "current_page": "Dashboard",
            "show_login": False,
            "show_registration": False
        }

    app_state = st.session_state.app_state

    # Affichage de la page de connexion si demandé
    if st.session_state.app_state["show_login"]:
        show_login_page()
        return

    # Affichage de la page d'inscription si demandé
    if st.session_state.app_state["show_registration"]:
        show_registration_page()
        return

    # Affichage de la barre de navigation
    current_page = show_navigation_sidebar()

    # Affichage de la page correspondante
    if current_page == "Dashboard":
        show_dashboard()
    elif current_page == "Saisie des Levés":
        show_saisie_page()
    elif current_page == "Suivi":
        show_suivi_page()
    elif current_page == "Mon Compte":
        show_account_page()
    elif current_page == "Admin Users":
        show_admin_users_page()
    elif current_page == "Admin Data":
        show_admin_data_page()
    else:
        show_dashboard()  # Page par défaut


if __name__ == "__main__":
    main()
