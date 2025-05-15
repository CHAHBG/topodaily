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
from contextlib import contextmanager

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


# Gestionnaire de contexte pour la connexion PostgreSQL
@contextmanager
def get_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        yield conn
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données: {str(e)}")
        yield None
    finally:
        if conn is not None:
            conn.close()


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
    with get_connection() as conn:
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


# Fonction pour hacher un mot de passe
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Fonction pour vérifier si un utilisateur existe et si le mot de passe est correct
def verify_user(username, password):
    with get_connection() as conn:
        if not conn:
            return None

        c = conn.cursor()

        hashed_password = hash_password(password)
        c.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, hashed_password))
        user = c.fetchone()

        if user:
            return {"id": user[0], "username": user[1], "role": user[5]}
        return None


# Fonction pour obtenir le rôle d'un utilisateur
def get_user_role(username):
    with get_connection() as conn:
        if not conn:
            return None

        c = conn.cursor()

        c.execute("SELECT role FROM users WHERE username=%s", (username,))
        role = c.fetchone()

        if role:
            return role[0]
        return None


# Fonction pour ajouter un nouvel utilisateur
def add_user(username, password, email, phone, role="topographe"):
    with get_connection() as conn:
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

        return success, message


# Fonction pour supprimer un utilisateur
def delete_user(user_id):
    with get_connection() as conn:
        if not conn:
            return False, "Erreur de connexion à la base de données"

        c = conn.cursor()

        try:
            # Vérifier si l'utilisateur existe
            c.execute("SELECT username FROM users WHERE id=%s", (user_id,))
            user_data = c.fetchone()

            if not user_data:
                return False, "Utilisateur non trouvé."

            username = user_data[0]

            # Vérifier si l'utilisateur est l'administrateur principal
            if username == "admin":
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

        return success, message


# Fonction pour modifier le mot de passe d'un utilisateur
def change_password(username, new_password):
    with get_connection() as conn:
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
def add_leve(date, village, region, commune, type_leve, quantite, appareil, topographe):
    with get_connection() as conn:
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
        with engine.connect() as connection:
            leves = pd.read_sql_query(query, connection, params=params)
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
        with engine.connect() as connection:
            leves = pd.read_sql_query(query, connection, params=(topographe,))
        return leves
    except Exception as e:
        st.error(f"Erreur lors de la récupération des levés: {str(e)}")
        return pd.DataFrame()


# Fonction pour obtenir les données uniques pour les filtres
def get_filter_options():
    engine = get_engine()
    if not engine:
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": []}

    try:
        with engine.connect() as connection:
            # Obtenir les villages uniques
            villages = pd.read_sql_query("SELECT DISTINCT village FROM leves ORDER BY village", connection)

            # Obtenir les régions uniques
            regions = pd.read_sql_query("SELECT DISTINCT region FROM leves WHERE region IS NOT NULL ORDER BY region",
                                      connection)

            # Obtenir les communes uniques
            communes = pd.read_sql_query("SELECT DISTINCT commune FROM leves WHERE commune IS NOT NULL ORDER BY commune",
                                       connection)

            # Obtenir les types de levés uniques
            types = pd.read_sql_query("SELECT DISTINCT type FROM leves ORDER BY type", connection)

            # Obtenir les appareils uniques
            appareils = pd.read_sql_query(
                "SELECT DISTINCT appareil FROM leves WHERE appareil IS NOT NULL ORDER BY appareil", connection)

            # Obtenir les topographes uniques
            topographes = pd.read_sql_query("SELECT DISTINCT topographe FROM leves ORDER BY topographe", connection)

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
    with get_connection() as conn:
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

        return success


# Fonction pour vérifier si un utilisateur est propriétaire d'un levé
def is_leve_owner(leve_id, username):
    with get_connection() as conn:
        if not conn:
            return False

        c = conn.cursor()
        c.execute("SELECT topographe FROM leves WHERE id=%s", (leve_id,))
        result = c.fetchone()

        if result and result[0] == username:
            return True
        return False


# Fonction pour supprimer un levé avec vérification du propriétaire
def delete_user_leve(leve_id, username):
    # Vérifier si l'utilisateur est le propriétaire du levé
    if not is_leve_owner(leve_id, username):
        return False, "Vous n'êtes pas autorisé à supprimer ce levé."

    with get_connection() as conn:
        if not conn:
            return False, "Erreur de connexion à la base de données"

        c = conn.cursor()

        try:
            c.execute("DELETE FROM leves WHERE id=%s AND topographe=%s", (leve_id, username))
            if c.rowcount == 0:
                return False, "Levé non trouvé ou vous n'êtes pas autorisé à le supprimer."

            conn.commit()
            success = True
            message = "Levé supprimé avec succès!"
        except Exception as e:
            conn.rollback()
            success = False
            message = f"Erreur lors de la suppression du levé: {str(e)}"

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
            # Filtres de dates
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Date de début", datetime.now() - timedelta(days=30))
            with col2:
                end_date = st.date_input("Date de fin", datetime.now())

            # Appliquer filtre de date
            mask_date = (leves_df['date'] >= pd.Timestamp(start_date)) & (leves_df['date'] <= pd.Timestamp(end_date))
            leves_filtered = leves_df[mask_date]

            col1, col2, col3 = st.columns(3)

            with col1:
                # Filtre par région
                filter_options = get_filter_options()
                region_options = ["Toutes"] + filter_options["regions"]
                region_filter = st.selectbox("Région", options=region_options, index=0)

                if region_filter != "Toutes" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['region'] == region_filter]

            with col2:
                # Filtre par commune
                commune_options = ["Toutes"] + filter_options["communes"]
                commune_filter = st.selectbox("Commune", options=commune_options, index=0)

                if commune_filter != "Toutes" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['commune'] == commune_filter]

            with col3:
                # Filtre par type de levé
                type_options = ["Tous"] + filter_options["types"]
                type_filter = st.selectbox("Type de levé", options=type_options, index=0)

                if type_filter != "Tous" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['type'] == type_filter]

            col1, col2 = st.columns(2)

            with col1:
                # Filtre par appareil
                appareil_options = ["Tous"] + filter_options["appareils"]
                appareil_filter = st.selectbox("Appareil", options=appareil_options, index=0)

                if appareil_filter != "Tous" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['appareil'] == appareil_filter]

            with col2:
                # Filtre par village
                village_options = ["Tous"] + filter_options["villages"]
                village_filter = st.selectbox("Village", options=village_options, index=0)

                if village_filter != "Tous" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['village'] == village_filter]

        st.subheader("Aperçu des statistiques globales")

        if leves_filtered.empty:
            st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
            leves_filtered = leves_df  # Réinitialiser pour afficher toutes les données

        col1, col2 = st.columns(2)

        with col1:
            # Statistiques par type de levé avec Plotly
            st.subheader("Levés par Type")
            if not leves_filtered.empty:
                type_counts = leves_filtered['type'].value_counts().reset_index()
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
            if not leves_filtered.empty:
                village_counts = leves_filtered['village'].value_counts().reset_index().head(10)
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
            if not leves_filtered.empty:
                time_series = leves_filtered.groupby(pd.Grouper(key='date', freq='D')).size().reset_index()
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
            if not leves_filtered.empty:
                topo_counts = leves_filtered['topographe'].value_counts().reset_index().head(10)
                topo_counts.columns = ['Topographe', 'Nombre']

                fig = px.bar(
                    topo_counts,
                    x='Topographe',
                    y='Nombre',
                    title='Top 10 des topographes par nombre de levés',
                    color='Nombre',
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(xaxis={'categoryorder': 'total descending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour ce filtre.")

        # Graphiques supplémentaires
        if not leves_filtered.empty and 'region' in leves_filtered.columns and leves_filtered['region'].notna().any():
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Levés par Région")
                region_counts = leves_filtered['region'].value_counts().reset_index()
                region_counts.columns = ['Région', 'Nombre']

                fig = px.pie(
                    region_counts,
                    values='Nombre',
                    names='Région',
                    title='Répartition des levés par région',
                    hole=0.3
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                if 'appareil' in leves_filtered.columns and leves_filtered['appareil'].notna().any():
                    st.subheader("Levés par Appareil")
                    appareil_counts = leves_filtered['appareil'].value_counts().reset_index()
                    appareil_counts.columns = ['Appareil', 'Nombre']

                    fig = px.bar(
                        appareil_counts,
                        x='Appareil',
                        y='Nombre',
                        title='Répartition des levés par appareil',
                        color='Nombre',
                        color_continuous_scale='Viridis'
                    )
                    fig.update_layout(xaxis={'categoryorder': 'total descending'})
                    st.plotly_chart(fig, use_container_width=True)

        # Tableau récapitulatif des données
        st.subheader("Tableau récapitulatif des données")
        
        # Affichage des données avec formatage de date pour meilleure lisibilité
        if not leves_filtered.empty:
            display_df = leves_filtered.copy()
            display_df['date'] = display_df['date'].dt.strftime('%d-%m-%Y')
            st.dataframe(display_df, height=300, use_container_width=True)
        else:
            st.info("Aucune donnée disponible pour ce filtre.")
    else:
        st.info("Aucune donnée de levé n'a encore été enregistrée dans le système.")


# Fonction pour afficher la page de saisie des levés
def show_leve_form():
    st.title("Saisie d'un nouveau levé topographique")

    if not st.session_state.get("authenticated", False):
        st.warning("Veuillez vous connecter pour ajouter un levé.")
        return

    # Récupérer les options pour les filtres
    filter_options = get_filter_options()

    with st.form("leve_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            date = st.date_input("Date du levé", datetime.now())
            
            # Champ village avec suggestions ou nouveau village
            existing_villages = filter_options["villages"]
            village_option = st.radio("Village", 
                                     ["Choisir dans la liste", "Ajouter un nouveau village"],
                                     horizontal=True)
            
            if village_option == "Choisir dans la liste" and existing_villages:
                village = st.selectbox("Sélectionner un village", options=existing_villages)
            else:
                village = st.text_input("Nom du village")
            
            # Type de levé
            existing_types = filter_options["types"] if filter_options["types"] else ["Parcellaire", "Foncier", "Routier", "Autre"]
            type_option = st.radio("Type de levé", 
                                  ["Choisir dans la liste", "Autre type"],
                                  horizontal=True)
            
            if type_option == "Choisir dans la liste":
                type_leve = st.selectbox("Sélectionner un type", options=existing_types)
            else:
                type_leve = st.text_input("Préciser le type de levé")
            
            # Appareil utilisé
            existing_appareils = filter_options["appareils"] if filter_options["appareils"] else ["GPS", "Station totale", "Drone", "Autre"]
            appareil_option = st.radio("Appareil utilisé", 
                                      ["Choisir dans la liste", "Autre appareil"],
                                      horizontal=True)
            
            if appareil_option == "Choisir dans la liste":
                appareil = st.selectbox("Sélectionner un appareil", options=existing_appareils)
            else:
                appareil = st.text_input("Préciser l'appareil utilisé")
        
        with col2:
            # Région avec suggestions
            existing_regions = filter_options["regions"]
            region_option = st.radio("Région", 
                                    ["Choisir dans la liste", "Ajouter une nouvelle région"],
                                    horizontal=True)
            
            if region_option == "Choisir dans la liste" and existing_regions:
                region = st.selectbox("Sélectionner une région", options=existing_regions)
            else:
                region = st.text_input("Nom de la région")
            
            # Commune avec suggestions
            existing_communes = filter_options["communes"]
            commune_option = st.radio("Commune", 
                                     ["Choisir dans la liste", "Ajouter une nouvelle commune"],
                                     horizontal=True)
            
            if commune_option == "Choisir dans la liste" and existing_communes:
                commune = st.selectbox("Sélectionner une commune", options=existing_communes)
            else:
                commune = st.text_input("Nom de la commune")
            
            # Quantité (nombre d'hectares, de parcelles, etc.)
            quantite = st.number_input("Quantité (en hectares, parcelles, etc.)", min_value=1, value=1)
            
        # Le topographe est automatiquement l'utilisateur connecté
        topographe = st.session_state.username
        
        submit = st.form_submit_button("Enregistrer")
        
        if submit:
            if not village or not type_leve:
                st.error("Le village et le type de levé sont obligatoires.")
            else:
                # Correction: utiliser un gestionnaire de contexte pour la connexion
                success = add_leve(date, village, region, commune, type_leve, quantite, appareil, topographe)
                if success:
                    st.success("Levé enregistré avec succès!")
                    # Vider les champs ou les réinitialiser
                    # On peut ajouter des commandes pour réinitialiser les champs après la soumission
                else:
                    st.error("Erreur lors de l'enregistrement du levé. Veuillez réessayer.")


# Fonction pour afficher la page de suivi des levés
def show_leve_tracking():
    st.title("Suivi des Levés Topographiques")

    if not st.session_state.get("authenticated", False):
        st.warning("Veuillez vous connecter pour voir le suivi des levés.")
        return

    user_role = st.session_state.user["role"]
    username = st.session_state.username

    # Récupérer les options pour les filtres
    filter_options = get_filter_options()
    
    # Interface de recherche et filtrage
    with st.expander("Filtres de recherche", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date = st.date_input("Date de début", datetime.now() - timedelta(days=30))
        
        with col2:
            end_date = st.date_input("Date de fin", datetime.now())
        
        with col3:
            if user_role == "administrateur":
                topographe_options = ["Tous"] + filter_options["topographes"]
                topographe_filter = st.selectbox("Topographe", options=topographe_options, index=0)
            else:
                topographe_filter = username  # L'utilisateur ne peut voir que ses propres levés
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Type de levé
            type_options = ["Tous"] + filter_options["types"]
            type_filter = st.selectbox("Type de levé", options=type_options, index=0)
        
        with col2:
            # Village
            village_options = ["Tous"] + filter_options["villages"]
            village_filter = st.selectbox("Village", options=village_options, index=0)
        
        search_button = st.button("Rechercher")
    
    # Affichage des résultats
    if search_button or 'first_load' not in st.session_state:
        st.session_state.first_load = False  # Pour éviter de recharger automatiquement à chaque changement
        
        # Récupération des levés filtrés
        # Correction: Utilisation de la connexion SQLAlchemy via get_engine pour éviter les problèmes de connexion fermée
        if user_role == "administrateur" and topographe_filter == "Tous":
            leves_df = get_filtered_leves(
                start_date=start_date,
                end_date=end_date,
                village=None if village_filter == "Tous" else village_filter,
                type_leve=None if type_filter == "Tous" else type_filter
            )
        else:
            # Pour un utilisateur normal ou un admin qui a choisi un topographe spécifique
            selected_topographe = username if user_role != "administrateur" else (
                None if topographe_filter == "Tous" else topographe_filter
            )
            
            leves_df = get_filtered_leves(
                start_date=start_date,
                end_date=end_date,
                village=None if village_filter == "Tous" else village_filter,
                type_leve=None if type_filter == "Tous" else type_filter,
                topographe=selected_topographe
            )
        
        if not leves_df.empty:
            # Conversion de la date pour l'affichage
            leves_df['date'] = pd.to_datetime(leves_df['date']).dt.strftime('%d-%m-%Y')
            
            # Ajout de boutons d'action
            if user_role == "administrateur":
                # Les administrateurs peuvent supprimer n'importe quel levé
                st.subheader(f"Résultats: {len(leves_df)} levés trouvés")
                
                # On crée un dataframe pour l'affichage sans les boutons
                display_df = leves_df.copy()
                st.dataframe(display_df, height=400, use_container_width=True)
                
                # Permettre la suppression de levés sélectionnés
                if not display_df.empty:
                    st.subheader("Actions")
                    leve_to_delete = st.selectbox("Sélectionner un levé à supprimer:", 
                                               options=display_df['id'].tolist(),
                                               format_func=lambda x: f"ID: {x} - {display_df[display_df['id'] == x]['village'].values[0]} ({display_df[display_df['id'] == x]['date'].values[0]})")
                    
                    if st.button("Supprimer ce levé"):
                        # Confirmation de suppression
                        if st.session_state.get('confirm_delete', False):
                            success = delete_leve(leve_to_delete)
                            if success:
                                st.success(f"Levé ID:{leve_to_delete} supprimé avec succès!")
                                st.session_state.confirm_delete = False
                                st.rerun()  # Recharger pour mettre à jour la liste
                            else:
                                st.error("Erreur lors de la suppression.")
                            st.session_state.confirm_delete = False
                        else:
                            st.warning("Êtes-vous sûr de vouloir supprimer ce levé? Cette action est irréversible.")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Oui, supprimer"):
                                    st.session_state.confirm_delete = True
                                    st.rerun()
                            with col2:
                                if st.button("Annuler"):
                                    st.session_state.confirm_delete = False
            else:
                # Les utilisateurs standards ne peuvent supprimer que leurs propres levés
                st.subheader(f"Vos levés: {len(leves_df)} levés trouvés")
                
                # Affichage du tableau sans boutons
                display_df = leves_df.copy()
                st.dataframe(display_df, height=400, use_container_width=True)
                
                # Permettre la suppression de ses propres levés
                if not display_df.empty:
                    st.subheader("Actions")
                    leve_to_delete = st.selectbox("Sélectionner un levé à supprimer:", 
                                               options=display_df['id'].tolist(),
                                               format_func=lambda x: f"ID: {x} - {display_df[display_df['id'] == x]['village'].values[0]} ({display_df[display_df['id'] == x]['date'].values[0]})")
                    
                    if st.button("Supprimer ce levé"):
                        # Vérification que c'est bien son propre levé
                        if st.session_state.get('confirm_delete', False):
                            success, message = delete_user_leve(leve_to_delete, username)
                            if success:
                                st.success(message)
                                st.session_state.confirm_delete = False
                                st.rerun()  # Recharger pour mettre à jour la liste
                            else:
                                st.error(message)
                            st.session_state.confirm_delete = False
                        else:
                            st.warning("Êtes-vous sûr de vouloir supprimer ce levé? Cette action est irréversible.")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Oui, supprimer"):
                                    st.session_state.confirm_delete = True
                                    st.rerun()
                            with col2:
                                if st.button("Annuler"):
                                    st.session_state.confirm_delete = False
        else:
            st.info("Aucun levé ne correspond aux critères de recherche.")


# Fonction pour afficher la page Mon Compte
def show_account_page():
    st.title("Mon Compte")

    if not st.session_state.get("authenticated", False):
        st.warning("Veuillez vous connecter pour accéder à votre compte.")
        return

    username = st.session_state.username
    user_role = st.session_state.user["role"]

    st.write(f"**Nom d'utilisateur:** {username}")
    st.write(f"**Rôle:** {user_role}")

    # Section pour changer le mot de passe
    st.subheader("Changer mon mot de passe")
    
    with st.form("change_password_form"):
        current_password = st.text_input("Mot de passe actuel", type="password")
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm_password = st.text_input("Confirmer nouveau mot de passe", type="password")
        
        submit = st.form_submit_button("Changer le mot de passe")
        
        if submit:
            if not current_password or not new_password or not confirm_password:
                st.error("Tous les champs sont obligatoires.")
            elif new_password != confirm_password:
                st.error("Les nouveaux mots de passe ne correspondent pas.")
            else:
                # Vérifier le mot de passe actuel
                user = verify_user(username, current_password)
                if user:
                    # Mot de passe correct, on peut le changer
                    success = change_password(username, new_password)
                    if success:
                        st.success("Mot de passe changé avec succès!")
                    else:
                        st.error("Erreur lors du changement de mot de passe. Veuillez réessayer.")
                else:
                    st.error("Mot de passe actuel incorrect.")

    # Afficher les statistiques de l'utilisateur
    st.subheader("Mes statistiques")
    
    # Récupération des levés de l'utilisateur
    user_leves = get_leves_by_topographe(username)
    
    if not user_leves.empty:
        # Afficher quelques statistiques générales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Nombre total de levés", len(user_leves))
        
        with col2:
            if 'quantite' in user_leves.columns:
                st.metric("Total quantité", user_leves['quantite'].sum())
        
        with col3:
            if 'date' in user_leves.columns:
                most_recent = pd.to_datetime(user_leves['date']).max().strftime('%d-%m-%Y')
                st.metric("Dernier levé", most_recent)
        
        # Répartition des types de levés
        if not user_leves.empty and 'type' in user_leves.columns:
            st.subheader("Mes types de levés")
            
            type_counts = user_leves['type'].value_counts().reset_index()
            type_counts.columns = ['Type', 'Nombre']
            
            fig = px.pie(
                type_counts,
                values='Nombre',
                names='Type',
                title='Répartition de mes types de levés',
                hole=0.3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        
        # Évolution des levés dans le temps
        if not user_leves.empty and 'date' in user_leves.columns:
            st.subheader("Mon activité dans le temps")
            
            user_leves['date'] = pd.to_datetime(user_leves['date'])
            time_series = user_leves.groupby(pd.Grouper(key='date', freq='M')).size().reset_index()
            time_series.columns = ['Date', 'Nombre']
            
            fig = px.line(
                time_series,
                x='Date',
                y='Nombre',
                title='Évolution mensuelle de mes levés',
                markers=True
            )
            fig.update_layout(xaxis_title='Date', yaxis_title='Nombre de levés')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Vous n'avez pas encore enregistré de levés.")


# Fonction pour afficher la page d'administration des utilisateurs
def show_admin_users_page():
    st.title("Gestion des Utilisateurs")

    if not st.session_state.get("authenticated", False) or st.session_state.user["role"] != "administrateur":
        st.warning("Accès non autorisé. Cette page nécessite des droits d'administrateur.")
        return

    # Récupérer tous les utilisateurs
    users = get_users()

    if users.empty:
        st.warning("Aucun utilisateur trouvé.")
        return

    # Afficher la liste des utilisateurs
    st.subheader("Liste des utilisateurs")
    st.dataframe(users, height=300, use_container_width=True)

    # Section pour ajouter un nouvel utilisateur
    st.subheader("Ajouter un nouvel utilisateur")
    
    with st.form("add_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Nom d'utilisateur")
            new_password = st.text_input("Mot de passe", type="password")
            new_email = st.text_input("Email")
        
        with col2:
            new_phone = st.text_input("Téléphone")
            new_role = st.selectbox("Rôle", ["topographe", "administrateur"])
        
        submit = st.form_submit_button("Ajouter l'utilisateur")
        
        if submit:
            if not new_username or not new_password:
                st.error("Le nom d'utilisateur et le mot de passe sont obligatoires.")
            elif new_email and not validate_email(new_email):
                st.error("Format d'email invalide.")
            elif new_phone and not validate_phone(new_phone):
                st.error("Format de numéro de téléphone invalide.")
            else:
                success, message = add_user(new_username, new_password, new_email, new_phone, new_role)
                if success:
                    st.success(message)
                    st.rerun()  # Rafraîchir pour voir le nouvel utilisateur
                else:
                    st.error(message)

    # Section pour supprimer un utilisateur
    st.subheader("Supprimer un utilisateur")
    
    user_to_delete = st.selectbox(
        "Sélectionner un utilisateur à supprimer:",
        options=users['id'].tolist(),
        format_func=lambda x: f"{users[users['id'] == x]['username'].values[0]} ({users[users['id'] == x]['role'].values[0]})"
    )
    
    if st.button("Supprimer l'utilisateur"):
        if user_to_delete and st.session_state.username != users[users['id'] == user_to_delete]['username'].values[0]:
            if st.session_state.get('confirm_user_delete', False):
                success, message = delete_user(user_to_delete)
                if success:
                    st.success(message)
                    st.session_state.confirm_user_delete = False
                    st.rerun()  # Rafraîchir pour voir les changements
                else:
                    st.error(message)
                st.session_state.confirm_user_delete = False
            else:
                st.warning("Êtes-vous sûr de vouloir supprimer cet utilisateur? Cette action est irréversible.")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Oui, supprimer", key="confirm_user_delete_yes"):
                        st.session_state.confirm_user_delete = True
                        st.rerun()
                with col2:
                    if st.button("Annuler", key="confirm_user_delete_no"):
                        st.session_state.confirm_user_delete = False
        elif user_to_delete and st.session_state.username == users[users['id'] == user_to_delete]['username'].values[0]:
            st.error("Vous ne pouvez pas supprimer votre propre compte!")


# Fonction pour afficher la page d'administration des données
def show_admin_data_page():
    st.title("Gestion des Données")

    if not st.session_state.get("authenticated", False) or st.session_state.user["role"] != "administrateur":
        st.warning("Accès non autorisé. Cette page nécessite des droits d'administrateur.")
        return

    # Section pour exporter les données
    st.subheader("Exporter les données")
    
    export_type = st.radio("Type d'export", ["Levés", "Utilisateurs"], horizontal=True)
    
    if export_type == "Levés":
        # Récupérer tous les levés
        leves_df = get_all_leves()
        
        if not leves_df.empty:
            # Formater la date pour l'export
            leves_df['date'] = pd.to_datetime(leves_df['date']).dt.strftime('%d-%m-%Y')
            
            # Options d'export
            export_format = st.radio("Format d'export", ["CSV", "Excel", "JSON"], horizontal=True)
            
            if st.button("Exporter les données"):
                if export_format == "CSV":
                    csv_data = leves_df.to_csv(index=False)
                    st.download_button(
                        label="Télécharger CSV",
                        data=csv_data,
                        file_name=f"leves_export_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                elif export_format == "Excel":
                    # Pour Excel, nous devons utiliser un buffer
                    import io
                    buffer = io.BytesIO()
                    leves_df.to_excel(buffer, index=False)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="Télécharger Excel",
                        data=buffer,
                        file_name=f"leves_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
                elif export_format == "JSON":
                    json_data = leves_df.to_json(orient="records")
                    st.download_button(
                        label="Télécharger JSON",
                        data=json_data,
                        file_name=f"leves_export_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
        else:
            st.info("Aucune donnée de levé disponible pour l'export.")
    
    elif export_type == "Utilisateurs":
        # Récupérer tous les utilisateurs sans le mot de passe pour la sécurité
        users_df = get_users()
        
        if not users_df.empty:
            # Exclure le mot de passe de l'export
            if 'password' in users_df.columns:
                users_df = users_df.drop(columns=['password'])
            
            # Options d'export
            export_format = st.radio("Format d'export", ["CSV", "Excel", "JSON"], horizontal=True)
            
            if st.button("Exporter les données"):
                if export_format == "CSV":
                    csv_data = users_df.to_csv(index=False)
                    st.download_button(
                        label="Télécharger CSV",
                        data=csv_data,
                        file_name=f"utilisateurs_export_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                elif export_format == "Excel":
                    # Pour Excel, nous devons utiliser un buffer
                    import io
                    buffer = io.BytesIO()
                    users_df.to_excel(buffer, index=False)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="Télécharger Excel",
                        data=buffer,
                        file_name=f"utilisateurs_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
                elif export_format == "JSON":
                    json_data = users_df.to_json(orient="records")
                    st.download_button(
                        label="Télécharger JSON",
                        data=json_data,
                        file_name=f"utilisateurs_export_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
        else:
            st.info("Aucune donnée utilisateur disponible pour l'export.")

    # Section pour nettoyer la base de données (fonctionnalité avancée)
    st.subheader("Maintenance de la base de données")
    
    if st.button("Optimiser la base de données"):
        with get_connection() as conn:
            if conn:
                try:
                    c = conn.cursor()
                    # Exécuter VACUUM pour récupérer l'espace disque
                    c.execute("VACUUM")
                    # Exécuter ANALYZE pour mettre à jour les statistiques
                    c.execute("ANALYZE")
                    conn.commit()
                    st.success("Base de données optimisée avec succès!")
                except Exception as e:
                    st.error(f"Erreur lors de l'optimisation: {str(e)}")
    
    # Bouton dangereux - avec confirmation
    st.subheader("Zone Dangereuse", help="Ces actions sont irréversibles!")
    
    danger_action = st.selectbox(
        "Action dangereuse",
        ["Sélectionner une action", "Supprimer tous les levés", "Réinitialiser la base de données"]
    )
    
    if danger_action != "Sélectionner une action":
        st.warning(f"⚠️ Vous êtes sur le point de {danger_action.lower()}. Cette action est irréversible!")
        
        # Demander une confirmation avec un code spécifique
        confirmation_code = "CONFIRMER"
        user_confirmation = st.text_input(f"Pour {danger_action.lower()}, tapez '{confirmation_code}'")
        
        if st.button("Exécuter l'action dangereuse") and user_confirmation == confirmation_code:
            with get_connection() as conn:
                if conn:
                    try:
                        c = conn.cursor()
                        
                        if danger_action == "Supprimer tous les levés":
                            c.execute("DELETE FROM leves")
                            conn.commit()
                            st.success("Tous les levés ont été supprimés.")
                        
                        elif danger_action == "Réinitialiser la base de données":
                            # Supprimer les tables
                            c.execute("DROP TABLE IF EXISTS leves")
                            # Ne pas supprimer la table users pour garder les comptes
                            conn.commit()
                            # Recréer les tables
                            init_db()
                            st.success("La base de données a été réinitialisée.")
                        
                    except Exception as e:
                        st.error(f"Erreur lors de l'exécution de l'action: {str(e)}")
def main():
    # Initialiser la base de données
    init_db()
    
    # Initialiser les variables de session si elles n'existent pas
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if "username" not in st.session_state:
        st.session_state.username = None
        
    if "show_login" not in st.session_state:
        st.session_state.show_login = False
        
    if "show_registration" not in st.session_state:
        st.session_state.show_registration = False
        
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"
    
    # Afficher la page de connexion si l'utilisateur n'est pas authentifié
    if not st.session_state.authenticated:
        # Titre de l'application
        st.title("Système de Gestion des Levés Topographiques")
        
        # Message de bienvenue
        st.write("""
        Bienvenue dans le système de gestion des levés topographiques. 
        Veuillez vous connecter pour accéder à toutes les fonctionnalités.
        """)
        
        # Boutons pour afficher le formulaire de connexion ou d'inscription
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Se connecter"):
                st.session_state.show_login = True
                st.session_state.show_registration = False
        with col2:
            if st.button("S'inscrire"):
                st.session_state.show_registration = True
                st.session_state.show_login = False
        
        # Afficher le formulaire de connexion si le bouton est cliqué
        if st.session_state.show_login:
            show_login_form()
        
        # Afficher le formulaire d'inscription si le bouton est cliqué
        if st.session_state.show_registration:
            show_registration_form()
        
        # Afficher un aperçu limité du tableau de bord
        st.subheader("Aperçu du tableau de bord")
        st.write("Connectez-vous pour voir toutes les statistiques et fonctionnalités disponibles.")
        
        # Afficher quelques statistiques générales si disponibles
        with st.spinner("Chargement des statistiques..."):
            # Utilisation de get_connection() avec gestionnaire de contexte pour éviter les erreurs de connexion fermée
            try:
                with get_connection() as conn:
                    if conn:
                        # Récupérer le nombre total de levés
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) FROM leves")
                        total_leves = c.fetchone()[0]
                        
                        # Récupérer le nombre de villages différents
                        c.execute("SELECT COUNT(DISTINCT village) FROM leves")
                        total_villages = c.fetchone()[0]
                        
                        # Afficher les statistiques
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Nombre total de levés", total_leves)
                        with col2:
                            st.metric("Nombre de villages", total_villages)
                    else:
                        st.error("Impossible de se connecter à la base de données.")
            except Exception as e:
                st.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
    else:
        # L'utilisateur est connecté, afficher l'interface complète
        
        # Barre latérale avec menu de navigation
        with st.sidebar:
            st.title("Navigation")
            
            # Menu pour tous les utilisateurs
            st.subheader("Général")
            if st.button("Tableau de bord"):
                st.session_state.current_page = "Dashboard"
            if st.button("Saisie d'un nouveau levé"):
                st.session_state.current_page = "Form"
            if st.button("Suivi des levés"):
                st.session_state.current_page = "Tracking"
            if st.button("Mon compte"):
                st.session_state.current_page = "Account"
            
            # Menu supplémentaire pour les administrateurs
            if st.session_state.get("user", {}).get("role") == "administrateur":
                st.subheader("Administration")
                if st.button("Gestion des utilisateurs"):
                    st.session_state.current_page = "AdminUsers"
                if st.button("Gestion des données"):
                    st.session_state.current_page = "AdminData"
            
            # Bouton de déconnexion
            st.subheader("Session")
            if st.button("Se déconnecter"):
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.user = None
                st.session_state.current_page = "Dashboard"
                st.rerun()
            
            # Afficher l'utilisateur connecté
            st.write(f"Connecté en tant que: **{st.session_state.username}**")
        
        # Afficher la page correspondante selon le choix de l'utilisateur
        if st.session_state.current_page == "Dashboard":
            show_dashboard()
        elif st.session_state.current_page == "Form":
            show_leve_form()
        elif st.session_state.current_page == "Tracking":
            show_leve_tracking()
        elif st.session_state.current_page == "Account":
            show_account_page()
        elif st.session_state.current_page == "AdminUsers" and st.session_state.user["role"] == "administrateur":
            show_admin_users_page()
        elif st.session_state.current_page == "AdminData" and st.session_state.user["role"] == "administrateur":
            show_admin_data_page()
        else:
            # Par défaut, afficher le tableau de bord
            show_dashboard()

# Point d'entrée principal
if __name__ == "__main__":
    main()
