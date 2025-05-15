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

    # Création de la table des levés topographiques
    c.execute('''
    CREATE TABLE IF NOT EXISTS leves (
        id SERIAL PRIMARY KEY,
        date DATE NOT NULL,
        village VARCHAR(100) NOT NULL,
        type VARCHAR(50) NOT NULL,
        quantite INTEGER NOT NULL,
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
def add_leve(date, village, type_leve, quantite, topographe):
    conn = get_connection()
    if not conn:
        return False

    c = conn.cursor()

    try:
        # Assurez-vous que quantite est un entier
        quantite = int(quantite)

        c.execute('''
        INSERT INTO leves (date, village, type, quantite, topographe)
        VALUES (%s, %s, %s, %s, %s)
        ''', (date, village, type_leve, quantite, topographe))

        conn.commit()
        success = True
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de l'ajout du levé: {str(e)}")
        success = False

    conn.close()
    return success


# Fonction pour obtenir tous les levés
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
def get_filtered_leves(start_date=None, end_date=None, village=None, type_leve=None, topographe=None):
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

    if type_leve:
        query += " AND type = %(type_leve)s"
        params['type_leve'] = type_leve

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
def get_filter_options():
    engine = get_engine()
    if not engine:
        return {"villages": [], "types": [], "topographes": []}

    try:
        # Obtenir les villages uniques
        villages = pd.read_sql_query("SELECT DISTINCT village FROM leves ORDER BY village", engine)

        # Obtenir les types de levés uniques
        types = pd.read_sql_query("SELECT DISTINCT type FROM leves ORDER BY type", engine)

        # Obtenir les topographes uniques
        topographes = pd.read_sql_query("SELECT DISTINCT topographe FROM leves ORDER BY topographe", engine)

        return {
            "villages": villages["village"].tolist() if not villages.empty else [],
            "types": types["type"].tolist() if not types.empty else [],
            "topographes": topographes["topographe"].tolist() if not topographes.empty else []
        }
    except Exception as e:
        st.error(f"Erreur lors de la récupération des options de filtre: {str(e)}")
        return {"villages": [], "types": [], "topographes": []}


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
                st.session_state.user = user
                st.session_state.username = username
                st.session_state.authenticated = True
                st.session_state.show_login = False  # Masquer page login
                st.session_state.show_registration = False  # Masquer page inscription
                st.session_state.current_page = "Mon Compte"  # Redirection vers page compte ou autre
                st.success(f"Connexion réussie! Bienvenue {username}!")
                st.rerun()
            else:
                st.error("Nom d'utilisateur ou mot de passe incorrect.")

    st.markdown("---")
    st.markdown("Pas encore de compte? [Créer un compte](#creer-un-compte)")

    if st.button("Créer un compte"):
        st.session_state.show_login = False
        st.session_state.show_registration = True
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
                    time.sleep(1)
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
    if st.session_state.get("authenticated", False):
        user_role = st.session_state.user["role"]
        username = st.session_state.username

        st.sidebar.write(f"Connecté en tant que: **{username}**")
        st.sidebar.write(f"Rôle: **{user_role}**")

        # Pages accessibles à tous les utilisateurs connectés
        page = st.sidebar.radio(
            "Pages",
            ["Dashboard", "Saisie des Levés", "Suivi", "Mon Compte"],
            index=0
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
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.user = None
            st.session_state.current_page = "Dashboard"
            st.session_state.show_login = False
            st.session_state.show_registration = False
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
                st.session_state.show_login = True
                st.session_state.show_registration = False
                st.rerun()
        with col2:
            if st.button("S'inscrire"):
                st.session_state.show_login = False
                st.session_state.show_registration = True
                st.rerun()

    return page


# Fonction pour afficher le dashboard
def show_dashboard():
    st.title("Dashboard des Levés Topographiques")

    # On récupère tous les levés pour les statistiques globales
    leves_df = get_all_leves()

    if not leves_df.empty:
        # Convertir la colonne date en datetime pour les graphiques
        leves_df['date'] = pd.to_datetime(leves_df['date'])

        # Filtres interactifs pour le dashboard
        with st.expander("Filtres", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                # Filtre par période
                periode = st.selectbox(
                    "Période",
                    ["Tous", "Dernier mois", "Dernière semaine", "Dernier trimestre", "Dernière année"],
                    index=0
                )

                if periode == "Dernier mois":
                    date_min = datetime.now() - timedelta(days=30)
                    leves_df = leves_df[leves_df['date'] >= date_min]
                elif periode == "Dernière semaine":
                    date_min = datetime.now() - timedelta(days=7)
                    leves_df = leves_df[leves_df['date'] >= date_min]
                elif periode == "Dernier trimestre":
                    date_min = datetime.now() - timedelta(days=90)
                    leves_df = leves_df[leves_df['date'] >= date_min]
                elif periode == "Dernière année":
                    date_min = datetime.now() - timedelta(days=365)
                    leves_df = leves_df[leves_df['date'] >= date_min]

            with col2:
                # Filtre par type de levé
                filter_options = get_filter_options()
                type_options = ["Tous"] + filter_options["types"]
                type_filter = st.selectbox("Type de levé", options=type_options, index=0)

                if type_filter != "Tous":
                    leves_df = leves_df[leves_df['type'] == type_filter]

            with col3:
                # Filtre par village
                village_options = ["Tous"] + filter_options["villages"]
                village_filter = st.selectbox("Village", options=village_options, index=0)

                if village_filter != "Tous":
                    leves_df = leves_df[leves_df['village'] == village_filter]

        st.subheader("Aperçu des statistiques globales")

        col1, col2 = st.columns(2)

        with col1:
            # Statistiques par type de levé avec Plotly
            st.subheader("Levés par Type")
            if not leves_df.empty:
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
                st.info("Aucune donnée disponible pour ce filtre.")

        with col2:
            # Statistiques par village avec Plotly
            st.subheader("Levés par Village")
            if not leves_df.empty:
                village_counts = leves_df['village'].value_counts().reset_index().head(10)
                village_counts.columns = ['Village', 'Nombre']

                fig = px.bar(
                    village_counts,
                    x='Village',
                    y='Nombre',
                    title='Top 10 des villages',
                    color='Nombre',
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(xaxis={'categoryorder': 'total descending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour ce filtre.")

        col1, col2 = st.columns(2)

        with col1:
            # Évolution temporelle des levés avec Plotly
            st.subheader("Évolution des Levés dans le Temps")
            if not leves_df.empty:
                time_series = leves_df.groupby(pd.Grouper(key='date', freq='D')).size().reset_index()
                time_series.columns = ['Date', 'Nombre']

                fig = px.line(
                    time_series,
                    x='Date',
                    y='Nombre',
                    title='Évolution quotidienne des levés',
                    markers=True
                )
                fig.update_layout(xaxis_title='Date', yaxis_title='Nombre de levés')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour ce filtre.")

        with col2:
            # Top des topographes avec Plotly
            st.subheader("Top des Topographes")
            if not leves_df.empty:
                topo_counts = leves_df['topographe'].value_counts().reset_index().head(10)
                topo_counts.columns = ['Topographe', 'Nombre']

                fig = px.bar(
                    topo_counts,
                    x='Topographe',
                    y='Nombre',
                    title='Top 10 des topographes',
                    color='Nombre',
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(xaxis={'categoryorder': 'total descending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour ce filtre.")

        # Afficher la somme totale des quantités
        st.subheader("Statistiques Globales")
        total_quantite = leves_df['quantite'].sum()
        moyenne_quantite = leves_df['quantite'].mean()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre Total de Levés", len(leves_df))
        with col2:
            st.metric("Quantité Totale", f"{total_quantite:,.0f}")
        with col3:
            st.metric("Moyenne par Levé", f"{moyenne_quantite:.2f}")

        # Bouton central pour saisir des levés
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Saisir un nouveau levé", use_container_width=True):
                if st.session_state.get("authenticated", False):
                    st.session_state.current_page = "Saisie des Levés"
                    st.rerun()
                else:
                    st.session_state.show_login = True
                    st.session_state.show_registration = False
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
                    st.session_state.show_login = True
                    st.session_state.show_registration = False
                    st.warning("Veuillez vous connecter pour saisir des levés.")
                    st.rerun()


# Fonction pour afficher la page de saisie des levés
def show_saisie_page():
    st.title("Saisie des Levés Topographiques")

    # Vérification que l'utilisateur est connecté
    if not st.session_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour saisir des levés.")

        # Afficher le formulaire de connexion directement sur cette page
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
        return

    with st.form("leve_form"):
        # La date du jour est préremplie
        date = st.date_input("Date du levé", datetime.now())

        # Nom du topographe prérempli avec le nom de l'utilisateur connecté
        topographe = st.session_state.username
        st.write(f"Topographe: **{topographe}**")

        # Autres champs du formulaire
        village = st.text_input("Village", placeholder="Nom du village")

        # Types de levés prédéfinis
        type_options = ["Batîments", "Champs", "Edifice publique", "Autre"]
        type_leve = st.selectbox("Type de levé", options=type_options)

        quantite = st.number_input("Quantité", min_value=0, step=1, format="%d")

        submit = st.form_submit_button("Enregistrer le levé")

        if submit:
            if not village:
                st.error("Veuillez entrer le nom du village.")
            elif quantite <= 0:
                st.error("La quantité doit être supérieure à zéro.")
            else:
                # Conversion de la date au format string
                date_str = date.strftime("%Y-%m-%d")

                # Enregistrement du levé
                if add_leve(date_str, village, type_leve, quantite, topographe):
                    st.success("Levé enregistré avec succès!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Erreur lors de l'enregistrement du levé.")


# Fonction pour afficher la page de suivi
def show_suivi_page():
    st.title("Suivi des Levés Topographiques")

    # Vérification que l'utilisateur est connecté
    if not st.session_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour accéder au suivi.")

        # Afficher le formulaire de connexion directement sur cette page
        with st.form("login_form_embed_suivi"):
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
        return

    # Récupération des options de filtre
    filter_options = get_filter_options()

    # Colonne pour les filtres
    with st.expander("Filtres", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Date de début", datetime.now() - timedelta(days=30))
            end_date = st.date_input("Date de fin", datetime.now())

        col1, col2, col3 = st.columns(3)
        with col1:
            village_options = ["Tous"] + filter_options["villages"]
            village = st.selectbox("Village", options=village_options)
            village = None if village == "Tous" else village

        with col2:
            type_options = ["Tous"] + filter_options["types"]
            type_leve = st.selectbox("Type de levé", options=type_options)
            type_leve = None if type_leve == "Tous" else type_leve

        with col3:
            # Pour les administrateurs, afficher tous les topographes
            # Pour les autres, voir uniquement ses propres levés
            if st.session_state.user["role"] == "administrateur":
                topo_options = ["Tous"] + filter_options["topographes"]
                topographe = st.selectbox("Topographe", options=topo_options)
                topographe = None if topographe == "Tous" else topographe
            else:
                topographe = st.session_state.username
                st.write(f"Topographe: **{topographe}**")

    # Récupération des levés filtrés
    leves_df = get_filtered_leves(start_date, end_date, village, type_leve, topographe)

    # Affichage des données
    if not leves_df.empty:
        # Renommage des colonnes pour un affichage plus convivial
        leves_df = leves_df.rename(columns={
            'id': 'ID',
            'date': 'Date',
            'village': 'Village',
            'type': 'Type',
            'quantite': 'Quantité',
            'topographe': 'Topographe',
            'created_at': 'Date de création'
        })

        # Formatage des dates
        leves_df['Date'] = pd.to_datetime(leves_df['Date']).dt.strftime('%d/%m/%Y')

        # Affichage des données avec une mise en forme améliorée
        st.dataframe(
            leves_df[['ID', 'Date', 'Village', 'Type', 'Quantité', 'Topographe']],
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

        # Pour les administrateurs, possibilité de supprimer des levés
        if st.session_state.user["role"] == "administrateur":
            st.subheader("Gestion des Levés")

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
    if not st.session_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour accéder à votre compte.")
        return

    username = st.session_state.username
    role = st.session_state.user["role"]

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
                    time.sleep(1)
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
                    time.sleep(1)
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
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "username" not in st.session_state:
        st.session_state.username = None

    if "user" not in st.session_state:
        st.session_state.user = None

    if "show_login" not in st.session_state:
        st.session_state.show_login = False

    if "show_registration" not in st.session_state:
        st.session_state.show_registration = False

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"

    # Affichage de la page de connexion si demandé
    if st.session_state.show_login:
        show_login_page()
        return

    # Affichage de la page d'inscription si demandé
    if st.session_state.show_registration:
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
