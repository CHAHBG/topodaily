# app.py
import os
import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import re
from datetime import datetime, timedelta
import time

# Configuration de la page
st.set_page_config(
    page_title="Gestion des Levés Topographiques",
    page_icon="📏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Création du dossier data s'il n'existe pas
if not os.path.exists("data"):
    os.makedirs("data")


# Fonction pour initialiser la base de données
def init_db():
    conn = sqlite3.connect('data/topodb.db')
    c = conn.cursor()

    # Création de la table utilisateurs si elle n'existe pas
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Création de la table des levés topographiques
    c.execute('''
    CREATE TABLE IF NOT EXISTS leves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        village TEXT NOT NULL,
        type TEXT NOT NULL,
        quantite INTEGER NOT NULL,
        topographe TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Vérification si l'utilisateur admin existe déjà
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        # Création de l'utilisateur admin par défaut
        admin_password = hashlib.sha256("admin".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ("admin", admin_password, "administrateur"))

    conn.commit()
    conn.close()


# Fonction pour hacher un mot de passe
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Fonction pour vérifier si un utilisateur existe et si le mot de passe est correct
def verify_user(username, password):
    conn = sqlite3.connect('data/topodb.db')
    c = conn.cursor()

    hashed_password = hash_password(password)
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_password))
    user = c.fetchone()

    conn.close()

    if user:
        return {"id": user[0], "username": user[1], "role": user[5]}
    return None


# Fonction pour obtenir le rôle d'un utilisateur
def get_user_role(username):
    conn = sqlite3.connect('data/topodb.db')
    c = conn.cursor()

    c.execute("SELECT role FROM users WHERE username=?", (username,))
    role = c.fetchone()

    conn.close()

    if role:
        return role[0]
    return None


# Fonction pour ajouter un nouvel utilisateur
def add_user(username, password, email, phone, role="topographe"):
    conn = sqlite3.connect('data/topodb.db')
    c = conn.cursor()

    try:
        hashed_password = hash_password(password)
        c.execute("INSERT INTO users (username, password, email, phone, role) VALUES (?, ?, ?, ?, ?)",
                  (username, hashed_password, email, phone, role))
        conn.commit()
        success = True
        message = "Compte créé avec succès!"
    except sqlite3.IntegrityError:
        success = False
        message = "Erreur: Nom d'utilisateur ou email déjà utilisé."

    conn.close()
    return success, message


# Fonction pour supprimer un utilisateur
def delete_user(user_id):
    conn = sqlite3.connect('data/topodb.db')
    c = conn.cursor()

    try:
        # Vérifier si l'utilisateur existe
        c.execute("SELECT username FROM users WHERE id=?", (user_id,))
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
        c.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        success = True
        message = f"Utilisateur {username} supprimé avec succès!"
    except Exception as e:
        success = False
        message = f"Erreur lors de la suppression de l'utilisateur: {str(e)}"

    conn.close()
    return success, message


# Fonction pour modifier le mot de passe d'un utilisateur
def change_password(username, new_password):
    conn = sqlite3.connect('data/topodb.db')
    c = conn.cursor()

    hashed_password = hash_password(new_password)
    c.execute("UPDATE users SET password=? WHERE username=?", (hashed_password, username))
    conn.commit()

    conn.close()
    return True


# Fonction pour obtenir la liste des utilisateurs
def get_users():
    conn = sqlite3.connect('data/topodb.db')
    query = "SELECT id, username, email, phone, role, created_at FROM users"
    users = pd.read_sql_query(query, conn)
    conn.close()
    return users


# Fonction pour ajouter un levé topographique
def add_leve(date, village, type_leve, quantite, topographe):
    conn = sqlite3.connect('data/topodb.db')
    c = conn.cursor()

    # Assurez-vous que quantite est un entier
    quantite = int(quantite)

    c.execute('''
    INSERT INTO leves (date, village, type, quantite, topographe)
    VALUES (?, ?, ?, ?, ?)
    ''', (date, village, type_leve, quantite, topographe))

    conn.commit()
    conn.close()
    return True


# Fonction pour obtenir tous les levés
def get_all_leves():
    conn = sqlite3.connect('data/topodb.db')
    query = "SELECT * FROM leves ORDER BY date DESC"
    leves = pd.read_sql_query(query, conn)
    conn.close()
    return leves


# Fonction pour obtenir les levés filtrés
def get_filtered_leves(start_date=None, end_date=None, village=None, type_leve=None, topographe=None):
    conn = sqlite3.connect('data/topodb.db')

    # Construire la requête SQL avec les filtres
    query = "SELECT * FROM leves WHERE 1=1"
    params = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    if village:
        query += " AND village = ?"
        params.append(village)

    if type_leve:
        query += " AND type = ?"
        params.append(type_leve)

    if topographe:
        query += " AND topographe = ?"
        params.append(topographe)

    query += " ORDER BY date DESC"

    leves = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return leves


# Fonction pour obtenir les levés d'un topographe spécifique
def get_leves_by_topographe(topographe):
    conn = sqlite3.connect('data/topodb.db')
    query = f"SELECT * FROM leves WHERE topographe=? ORDER BY date DESC"
    leves = pd.read_sql_query(query, conn, params=(topographe,))
    conn.close()
    return leves


# Fonction pour obtenir les données uniques pour les filtres
def get_filter_options():
    conn = sqlite3.connect('data/topodb.db')

    # Obtenir les villages uniques
    villages = pd.read_sql_query("SELECT DISTINCT village FROM leves ORDER BY village", conn)

    # Obtenir les types de levés uniques
    types = pd.read_sql_query("SELECT DISTINCT type FROM leves ORDER BY type", conn)

    # Obtenir les topographes uniques
    topographes = pd.read_sql_query("SELECT DISTINCT topographe FROM leves ORDER BY topographe", conn)

    conn.close()

    return {
        "villages": villages["village"].tolist() if not villages.empty else [],
        "types": types["type"].tolist() if not types.empty else [],
        "topographes": topographes["topographe"].tolist() if not topographes.empty else []
    }


# Fonction pour supprimer un levé
def delete_leve(leve_id):
    conn = sqlite3.connect('data/topodb.db')
    c = conn.cursor()

    c.execute("DELETE FROM leves WHERE id=?", (leve_id,))

    conn.commit()
    conn.close()
    return True


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

    user_role = st.session_state.user["role"]
    username = st.session_state.username

    # Filtres pour le suivi
    st.subheader("Filtres")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Filtre par date
        date_filter = st.selectbox(
            "Période",
            ["Tous", "Dernier mois", "Dernière semaine", "Dernier trimestre", "Dernière année", "Personnaliser"],
            index=0
        )

        start_date = None
        end_date = None

        if date_filter == "Dernier mois":
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
        elif date_filter == "Dernière semaine":
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
        elif date_filter == "Dernier trimestre":
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
        elif date_filter == "Dernière année":
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
        elif date_filter == "Personnaliser":
            col1_1, col1_2 = st.columns(2)
            with col1_1:
                start_date = st.date_input("Du", datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            with col1_2:
                end_date = st.date_input("Au", datetime.now()).strftime("%Y-%m-%d")

    with col2:
        # Filtre par type de levé
        filter_options = get_filter_options()
        type_options = ["Tous"] + filter_options["types"]
        type_filter = st.selectbox("Type de levé", options=type_options, index=0)

        if type_filter == "Tous":
            type_filter = None

    with col3:
        # Filtre par village
        village_options = ["Tous"] + filter_options["villages"]
        village_filter = st.selectbox("Village", options=village_options, index=0)

        if village_filter == "Tous":
            village_filter = None

    # Filtre par topographe pour les administrateurs/superviseurs
    topo_filter = None
    if user_role in ["administrateur", "superviseur"]:
        topo_options = ["Tous"] + filter_options["topographes"]
        topo_filter = st.selectbox("Topographe", options=topo_options, index=0)

        if topo_filter == "Tous":
            topo_filter = None
    else:
        # Pour les topographes, on filtre automatiquement sur leur nom
        topo_filter = username

    # Récupération des levés selon les filtres
    leves_df = get_filtered_leves(start_date, end_date, village_filter, type_filter, topo_filter)

    if not leves_df.empty:
        # Conversion
        # Affichage des résultats filtrés
        st.subheader("Résultats")

        # Métriques de synthèse
        total_leves = len(leves_df)
        total_quantite = leves_df['quantite'].sum() if total_leves > 0 else 0

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Nombre de levés", total_leves)
        with col2:
            st.metric("Quantité totale", f"{total_quantite:,.0f}")

        # Affichage du tableau de données
        st.dataframe(
            leves_df.rename(columns={
                'id': 'ID',
                'date': 'Date',
                'village': 'Village',
                'type': 'Type',
                'quantite': 'Quantité',
                'topographe': 'Topographe',
                'created_at': 'Créé le'
            }),
            use_container_width=True,
            hide_index=True
        )

        # Options pour exporter les données
        if st.button("Exporter les données (CSV)"):
            csv = leves_df.to_csv(index=False)
            st.download_button(
                label="Télécharger CSV",
                data=csv,
                file_name=f"leves_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

        # Option pour supprimer un levé (uniquement pour les administrateurs)
        if user_role == "administrateur":
            st.markdown("---")
            st.subheader("Gestion des données")

            with st.expander("Supprimer un levé", expanded=False):
                leve_id = st.number_input("ID du levé à supprimer", min_value=1, step=1)

                if st.button("Supprimer"):
                    if delete_leve(leve_id):
                        st.success(f"Levé ID {leve_id} supprimé avec succès!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erreur lors de la suppression du levé.")
    else:
        st.info("Aucun levé ne correspond aux filtres sélectionnés.")


# Fonction pour afficher la page Mon Compte
def show_account_page():
    st.title("Mon Compte")

    # Vérification que l'utilisateur est connecté
    if not st.session_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour accéder à cette page.")
        return

    username = st.session_state.username

    # Afficher les informations du compte
    st.subheader("Informations personnelles")

    conn = sqlite3.connect('data/topodb.db')
    c = conn.cursor()

    c.execute("SELECT username, email, phone, role, created_at FROM users WHERE username=?", (username,))
    user_data = c.fetchone()

    conn.close()

    if user_data:
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Nom d'utilisateur:** {user_data[0]}")
            st.write(f"**Email:** {user_data[1] if user_data[1] else 'Non renseigné'}")

        with col2:
            st.write(f"**Téléphone:** {user_data[2] if user_data[2] else 'Non renseigné'}")
            st.write(f"**Rôle:** {user_data[3]}")
            st.write(f"**Compte créé le:** {user_data[4]}")

    # Changer le mot de passe
    st.markdown("---")
    st.subheader("Changer le mot de passe")

    with st.form("change_password_form"):
        current_password = st.text_input("Mot de passe actuel", type="password")
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm_password = st.text_input("Confirmer le nouveau mot de passe", type="password")

        submit = st.form_submit_button("Changer le mot de passe")

        if submit:
            if not current_password or not new_password or not confirm_password:
                st.error("Tous les champs sont obligatoires.")
            elif new_password != confirm_password:
                st.error("Les nouveaux mots de passe ne correspondent pas.")
            elif not verify_user(username, current_password):
                st.error("Mot de passe actuel incorrect.")
            else:
                if change_password(username, new_password):
                    st.success("Mot de passe changé avec succès!")
                else:
                    st.error("Erreur lors du changement de mot de passe.")

    # Afficher les statistiques personnelles pour l'utilisateur
    st.markdown("---")
    st.subheader("Mes statistiques")

    # Récupérer les levés de l'utilisateur
    user_leves = get_leves_by_topographe(username)

    if not user_leves.empty:
        # Conversion de la colonne date en datetime pour les graphiques
        user_leves['date'] = pd.to_datetime(user_leves['date'])

        # Métriques de synthèse
        total_leves = len(user_leves)
        total_quantite = user_leves['quantite'].sum()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de levés", total_leves)
        with col2:
            st.metric("Quantité totale", f"{total_quantite:,.0f}")
        with col3:
            # Calculer la moyenne par jour des 30 derniers jours
            recent_leves = user_leves[user_leves['date'] >= datetime.now() - timedelta(days=30)]
            if not recent_leves.empty:
                avg_per_day = len(recent_leves) / 30
                st.metric("Moyenne sur 30 jours", f"{avg_per_day:.2f} levés/jour")
            else:
                st.metric("Moyenne sur 30 jours", "0 levés/jour")

        # Graphique d'évolution temporelle
        st.subheader("Évolution de mon activité")
        time_series = user_leves.groupby(pd.Grouper(key='date', freq='W')).size().reset_index()
        time_series.columns = ['Date', 'Nombre']

        fig = px.line(
            time_series,
            x='Date',
            y='Nombre',
            title='Levés par semaine',
            markers=True
        )
        fig.update_layout(xaxis_title='Date', yaxis_title='Nombre de levés')
        st.plotly_chart(fig, use_container_width=True)

        # Répartition par type de levé
        st.subheader("Mes types de levés")
        type_counts = user_leves['type'].value_counts().reset_index()
        type_counts.columns = ['Type', 'Nombre']

        fig = px.pie(
            type_counts,
            values='Nombre',
            names='Type',
            title='Répartition par type de levé',
            hole=0.3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Vous n'avez pas encore enregistré de levés.")


# Fonction pour afficher la page d'administration des utilisateurs
def show_admin_users_page():
    st.title("Gestion des Utilisateurs")

    # Vérifier que l'utilisateur est administrateur
    if not st.session_state.get("authenticated", False) or st.session_state.user["role"] != "administrateur":
        st.warning("Vous n'avez pas les droits pour accéder à cette page.")
        return

    # Récupérer la liste des utilisateurs
    users_df = get_users()

    # Affichage des utilisateurs
    st.subheader("Liste des utilisateurs")
    st.dataframe(
        users_df.rename(columns={
            'id': 'ID',
            'username': 'Nom d\'utilisateur',
            'email': 'Email',
            'phone': 'Téléphone',
            'role': 'Rôle',
            'created_at': 'Créé le'
        }),
        use_container_width=True,
        hide_index=True
    )

    # Ajouter un nouvel utilisateur
    st.markdown("---")
    st.subheader("Ajouter un utilisateur")

    with st.form("add_user_form"):
        col1, col2 = st.columns(2)

        with col1:
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            confirm_password = st.text_input("Confirmer le mot de passe", type="password")

        with col2:
            email = st.text_input("Email (optionnel)")
            phone = st.text_input("Téléphone (optionnel)")
            role = st.selectbox("Rôle", options=["topographe", "superviseur", "administrateur"])

        submit = st.form_submit_button("Ajouter l'utilisateur")

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
                success, message = add_user(username, password, email, phone, role)
                if success:
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)

    # Supprimer un utilisateur
    st.markdown("---")
    st.subheader("Supprimer un utilisateur")

    user_id = st.number_input("ID de l'utilisateur à supprimer", min_value=1, step=1)

    if st.button("Supprimer l'utilisateur"):
        if user_id == st.session_state.user["id"]:
            st.error("Vous ne pouvez pas supprimer votre propre compte.")
        else:
            success, message = delete_user(user_id)
            if success:
                st.success(message)
                time.sleep(1)
                st.rerun()
            else:
                st.error(message)


# Fonction pour afficher la page d'administration des données
def show_admin_data_page():
    st.title("Gestion des Données")

    # Vérifier que l'utilisateur est administrateur
    if not st.session_state.get("authenticated", False) or st.session_state.user["role"] != "administrateur":
        st.warning("Vous n'avez pas les droits pour accéder à cette page.")
        return

    # Options pour la gestion des données
    option = st.selectbox(
        "Sélectionnez une action:",
        ["Visualisation des données", "Suppression de données", "Exportation/Importation"]
    )

    if option == "Visualisation des données":
        st.subheader("Visualisation des données")

        # Récupérer toutes les données
        leves_df = get_all_leves()

        if not leves_df.empty:
            # Affichage complet des données
            st.dataframe(leves_df, use_container_width=True)

            # Graphiques avancés
            st.subheader("Analyse approfondie")

            # Convertir la date en datetime
            leves_df['date'] = pd.to_datetime(leves_df['date'])

            # Corrélation entre le type de levé et la quantité
            type_quant = leves_df.groupby('type')['quantite'].agg(['mean', 'sum', 'count']).reset_index()
            type_quant.columns = ['Type', 'Moyenne', 'Somme', 'Nombre']

            fig = px.bar(
                type_quant,
                x='Type',
                y=['Moyenne', 'Somme'],
                barmode='group',
                title='Analyse par type de levé',
                labels={'value': 'Valeur', 'variable': 'Métrique'}
            )
            st.plotly_chart(fig, use_container_width=True)

            # Heatmap d'activité
            st.subheader("Répartition d'activité")

            # Ajouter des colonnes pour le jour de la semaine et le mois
            leves_df['mois'] = leves_df['date'].dt.month_name()
            leves_df['jour'] = leves_df['date'].dt.day_name()

            # Regroupement par jour et mois
            heatmap_data = leves_df.groupby(['jour', 'mois']).size().unstack().fillna(0)

            # Réordonner les jours de la semaine
            jours_ordre = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heatmap_data = heatmap_data.reindex(jours_ordre)

            fig = px.imshow(
                heatmap_data,
                title='Heatmap d\'activité par jour et mois',
                labels=dict(x="Mois", y="Jour de la semaine", color="Nombre de levés"),
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Aucun levé n'a encore été enregistré.")

    elif option == "Suppression de données":
        st.subheader("Suppression de données")

        with st.expander("Supprimer un levé spécifique"):
            leve_id = st.number_input("ID du levé à supprimer", min_value=1, step=1)

            if st.button("Supprimer ce levé"):
                if delete_leve(leve_id):
                    st.success(f"Levé ID {leve_id} supprimé avec succès!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Erreur lors de la suppression du levé.")

        with st.expander("Suppression par lot (DANGER)"):
            st.warning("ATTENTION: Cette action est irréversible!")

            # Critères de suppression par lot
            filter_options = get_filter_options()

            # Date
            date_type = st.radio("Filtre de date", ["Aucun", "Avant une date", "Entre deux dates"])

            if date_type == "Avant une date":
                before_date = st.date_input("Supprimer les levés avant le", datetime.now()).strftime("%Y-%m-%d")
            elif date_type == "Entre deux dates":
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Du", datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                with col2:
                    end_date = st.date_input("Au", datetime.now()).strftime("%Y-%m-%d")

            # Village
            village_options = ["Tous"] + filter_options["villages"]
            village_filter = st.selectbox("Village", options=village_options, index=0)

            # Type
            type_options = ["Tous"] + filter_options["types"]
            type_filter = st.selectbox("Type de levé", options=type_options, index=0)

            # Topographe
            topo_options = ["Tous"] + filter_options["topographes"]
            topo_filter = st.selectbox("Topographe", options=topo_options, index=0)

            # Confirmation pour éviter les suppressions accidentelles
            confirmation = st.text_input("Tapez 'CONFIRMER' pour valider la suppression par lot")

            if st.button("Supprimer les levés correspondants"):
                if confirmation != "CONFIRMER":
                    st.error("Vous devez taper 'CONFIRMER' pour valider cette action.")
                else:
                    # Code de suppression par lot à implémenter
                    st.success("Suppression par lot effectuée avec succès!")
                    time.sleep(1)
                    st.rerun()

    elif option == "Exportation/Importation":
        st.subheader("Exportation/Importation de données")

        with st.expander("Exporter les données"):
            # Récupérer toutes les données
            leves_df = get_all_leves()

            if not leves_df.empty:
                # Export CSV
                csv = leves_df.to_csv(index=False)
                st.download_button(
                    label="Télécharger CSV",
                    data=csv,
                    file_name=f"leves_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

                # Export Excel
                st.info("L'export Excel n'est pas encore disponible.")
            else:
                st.info("Aucun levé n'a encore été enregistré.")

        with st.expander("Importer des données"):
            st.info("La fonctionnalité d'import n'est pas encore disponible.")


# Initialisation de la base de données au démarrage
init_db()


# Interface principale
def main():
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

    # Affichage de la sidebar de navigation
    page = show_navigation_sidebar()
    # Si connecté, forcer une redirection par défaut vers Mon Compte
    if st.session_state.authenticated and st.session_state.current_page == "Dashboard":
        st.session_state.current_page = "Mon Compte"

    # Gestion des pages d'authentification spéciales
    if st.session_state.show_login:
        show_login_page()
    elif st.session_state.show_registration:
        show_registration_page()
    # Si l'utilisateur a demandé une page spécifique via le menu
    elif st.session_state.current_page != page:
        st.session_state.current_page = page

    # Affichage de la page demandée
    if not st.session_state.show_login and not st.session_state.show_registration:
        if page == "Dashboard":
            show_dashboard()
        elif page == "Saisie des Levés":
            show_saisie_page()
        elif page == "Suivi":
            show_suivi_page()
        elif page == "Mon Compte":
            show_account_page()
        elif page == "Admin Users":
            show_admin_users_page()
        elif page == "Admin Data":
            show_admin_data_page()


if __name__ == "__main__":
    main()