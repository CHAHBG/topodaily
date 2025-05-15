# app.py (version optimisée pour Supabase/PostgreSQL)
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
import re
from datetime import datetime, timedelta
import time
import psycopg2
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from cachetools import cached, TTLCache
import functools

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

# Cache pour les connexions
connection_cache = TTLCache(maxsize=10, ttl=60)  # Expire après 60 secondes

# Cache pour les requêtes fréquentes (10 entrées, expire après 5 minutes)
data_cache = TTLCache(maxsize=100, ttl=300)

# Fonction pour obtenir une connexion de pool
@cached(cache=connection_cache)
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
@cached(cache=connection_cache)
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

    # Création d'index pour accélérer les requêtes fréquentes
    c.execute("CREATE INDEX IF NOT EXISTS idx_leves_date ON leves(date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_leves_village ON leves(village)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_leves_topographe ON leves(topographe)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_leves_type ON leves(type)")

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
        # Invalider le cache des utilisateurs
        if 'get_users' in data_cache:
            del data_cache['get_users']
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
        # Invalider le cache des utilisateurs
        if 'get_users' in data_cache:
            del data_cache['get_users']
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
@st.cache_data(ttl=300)  # Cache de 5 minutes
def get_users():
    # Utiliser une clé de cache pour cette fonction
    cache_key = 'get_users'
    if cache_key in data_cache:
        return data_cache[cache_key]

    engine = get_engine()
    if not engine:
        return pd.DataFrame()

    query = "SELECT id, username, email, phone, role, created_at FROM users"
    try:
        users = pd.read_sql_query(query, engine)
        # Stocker dans le cache
        data_cache[cache_key] = users
        return users
    except Exception as e:
        st.error(f"Erreur lors de la récupération des utilisateurs: {str(e)}")
        return pd.DataFrame()

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
        
        # Invalider les caches concernant les levés
        cache_keys_to_invalidate = [k for k in data_cache.keys() if 'leves' in str(k)]
        for key in cache_keys_to_invalidate:
            if key in data_cache:
                del data_cache[key]
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de l'ajout du levé: {str(e)}")
        success = False

    conn.close()
    return success

# Fonction pour obtenir tous les levés avec cache
@st.cache_data(ttl=300)  # Cache de 5 minutes
def get_all_leves():
    # Utiliser une clé de cache pour cette fonction
    cache_key = 'get_all_leves'
    if cache_key in data_cache:
        return data_cache[cache_key]
    
    engine = get_engine()
    if not engine:
        return pd.DataFrame()

    query = "SELECT * FROM leves ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine)
        # Stocker dans le cache
        data_cache[cache_key] = leves
        return leves
    except Exception as e:
        st.error(f"Erreur lors de la récupération des levés: {str(e)}")
        return pd.DataFrame()

# Fonction optimisée pour obtenir les levés filtrés
@st.cache_data(ttl=300)  # Cache de 5 minutes
def get_filtered_leves(start_date=None, end_date=None, village=None, region=None, commune=None, type_leve=None,
                      appareil=None, topographe=None):
    # Créer une clé de cache basée sur les paramètres
    cache_key = f'filtered_leves_{start_date}_{end_date}_{village}_{region}_{commune}_{type_leve}_{appareil}_{topographe}'
    if cache_key in data_cache:
        return data_cache[cache_key]

    engine = get_engine()
    if not engine:
        return pd.DataFrame()

    # Construction de requête optimisée
    conditions = []
    params = {}
    
    if start_date:
        conditions.append("date >= %(start_date)s")
        params['start_date'] = start_date
    
    if end_date:
        conditions.append("date <= %(end_date)s")
        params['end_date'] = end_date
    
    if village:
        conditions.append("village = %(village)s")
        params['village'] = village
    
    if region:
        conditions.append("region = %(region)s")
        params['region'] = region
    
    if commune:
        conditions.append("commune = %(commune)s")
        params['commune'] = commune
    
    if type_leve:
        conditions.append("type = %(type_leve)s")
        params['type_leve'] = type_leve
    
    if appareil:
        conditions.append("appareil = %(appareil)s")
        params['appareil'] = appareil
    
    if topographe:
        conditions.append("topographe = %(topographe)s")
        params['topographe'] = topographe
    
    # Construire la requête SQL
    query = "SELECT * FROM leves"
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY date DESC"
    
    try:
        leves = pd.read_sql_query(query, engine, params=params)
        # Stocker dans le cache
        data_cache[cache_key] = leves
        return leves
    except Exception as e:
        st.error(f"Erreur lors de la récupération des levés filtrés: {str(e)}")
        return pd.DataFrame()

# Fonction pour obtenir les levés d'un topographe spécifique avec cache
@st.cache_data(ttl=300)  # Cache de 5 minutes
def get_leves_by_topographe(topographe):
    # Créer une clé de cache basée sur le topographe
    cache_key = f'leves_by_topographe_{topographe}'
    if cache_key in data_cache:
        return data_cache[cache_key]
    
    engine = get_engine()
    if not engine:
        return pd.DataFrame()

    query = "SELECT * FROM leves WHERE topographe=%s ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine, params=(topographe,))
        # Stocker dans le cache
        data_cache[cache_key] = leves
        return leves
    except Exception as e:
        st.error(f"Erreur lors de la récupération des levés: {str(e)}")
        return pd.DataFrame()

# Fonction pour obtenir les données uniques pour les filtres avec cache
@st.cache_data(ttl=600)  # Cache de 10 minutes
def get_filter_options():
    # Utiliser une clé de cache pour cette fonction
    cache_key = 'filter_options'
    if cache_key in data_cache:
        return data_cache[cache_key]
    
    engine = get_engine()
    if not engine:
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": []}

    try:
        # Requête optimisée pour récupérer toutes les options en une seule fois
        villages = pd.read_sql_query("SELECT DISTINCT village FROM leves ORDER BY village", engine)
        regions = pd.read_sql_query("SELECT DISTINCT region FROM leves WHERE region IS NOT NULL ORDER BY region", engine)
        communes = pd.read_sql_query("SELECT DISTINCT commune FROM leves WHERE commune IS NOT NULL ORDER BY commune", engine)
        types = pd.read_sql_query("SELECT DISTINCT type FROM leves ORDER BY type", engine)
        appareils = pd.read_sql_query("SELECT DISTINCT appareil FROM leves WHERE appareil IS NOT NULL ORDER BY appareil", engine)
        topographes = pd.read_sql_query("SELECT DISTINCT topographe FROM leves ORDER BY topographe", engine)

        filter_options = {
            "villages": villages["village"].tolist() if not villages.empty else [],
            "regions": regions["region"].tolist() if not regions.empty else [],
            "communes": communes["commune"].tolist() if not communes.empty else [],
            "types": types["type"].tolist() if not types.empty else [],
            "appareils": appareils["appareil"].tolist() if not appareils.empty else [],
            "topographes": topographes["topographe"].tolist() if not topographes.empty else []
        }
        
        # Stocker dans le cache
        data_cache[cache_key] = filter_options
        return filter_options
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
        
        # Invalider les caches concernant les levés
        cache_keys_to_invalidate = [k for k in data_cache.keys() if 'leves' in str(k)]
        for key in cache_keys_to_invalidate:
            if key in data_cache:
                del data_cache[key]
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
        
        # Invalider les caches concernant les levés
        cache_keys_to_invalidate = [k for k in data_cache.keys() if 'leves' in str(k)]
        for key in cache_keys_to_invalidate:
            if key in data_cache:
                del data_cache[key]
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
@st.cache_data(ttl=10)  # Cache de 10 secondes pour l'UI
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

            # Récupération des options de filtre (en cache)
            filter_options = get_filter_options()

            # Appliquer filtre de date avant les autres filtres pour réduire la charge
            mask_date = (leves_df['date'] >= pd.Timestamp(start_date)) & (leves_df['date'] <= pd.Timestamp(end_date))
            leves_filtered = leves_df[mask_date]

            col1, col2, col3 = st.columns(3)

            with col1:
                # Filtre par région
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

        # Simplifier les graphiques pour améliorer les performances
        col1, col2 = st.columns(2)

        with col1:
            # Statistiques par type de levé avec Plotly
            st.subheader("Levés par Type")
            if not leves_filtered.empty:
                type_counts = leves_filtered['type'].value_counts().reset_index()
                type_counts.columns = ['type', 'count']
                
                # Utilisation de Plotly pour le graphique interactif
                fig = px.bar(
                    type_counts, 
                    x='type', 
                    y='count',
                    title="Nombre de levés par type",
                    color='type',
                    labels={'count':'Nombre de levés', 'type':'Type de levé'},
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour ce graphique.")

        with col2:
            # Statistiques par topographe (limité aux 10 premiers pour l'efficacité)
            st.subheader("Levés par Topographe")
            if not leves_filtered.empty:
                topo_counts = leves_filtered['topographe'].value_counts().head(10).reset_index()
                topo_counts.columns = ['topographe', 'count']
                
                fig = px.bar(
                    topo_counts, 
                    x='topographe', 
                    y='count',
                    title="Top 10 des topographes par nombre de levés",
                    color='topographe',
                    labels={'count':'Nombre de levés', 'topographe':'Topographe'},
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour ce graphique.")

        # Carte des levés par mois (chronologique)
        st.subheader("Évolution des levés")
        if not leves_filtered.empty:
            # Agréger par mois pour réduire la quantité de données
            leves_filtered['year_month'] = leves_filtered['date'].dt.strftime('%Y-%m')
            monthly_counts = leves_filtered.groupby('year_month').size().reset_index(name='count')
            monthly_counts = monthly_counts.sort_values('year_month')
            
            fig = px.line(
                monthly_counts, 
                x='year_month', 
                y='count',
                title="Évolution mensuelle du nombre de levés",
                markers=True,
                labels={'count':'Nombre de levés', 'year_month':'Mois'},
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée disponible pour ce graphique.")

        # Tableau récapitulatif des données
        st.subheader("Tableau des levés récents")
        if not leves_filtered.empty:
            # Limiter à 100 entrées pour performance
            display_df = leves_filtered.head(100).copy()
            # Formater la date pour l'affichage
            display_df['date'] = display_df['date'].dt.strftime('%d/%m/%Y')
            
            # Afficher seulement les colonnes importantes
            display_cols = ['date', 'village', 'region', 'commune', 'type', 'quantite', 'topographe']
            st.dataframe(display_df[display_cols], use_container_width=True)
            
            # Afficher le nombre total d'entrées
            total_entries = len(leves_filtered)
            if total_entries > 100:
                st.info(f"Affichage des 100 entrées les plus récentes sur un total de {total_entries}.")
        else:
            st.info("Aucune donnée disponible pour ce tableau.")
    else:
        st.info("Aucune donnée n'est disponible. Commencez par ajouter des levés topographiques.")

# Fonction pour afficher la page de saisie des levés
def show_leve_entry_page():
    st.title("Saisie d'un nouveau levé topographique")

    # Formulaire pour la saisie d'un nouveau levé
    with st.form("leve_form"):
        col1, col2 = st.columns(2)

        with col1:
            date = st.date_input("Date du levé", datetime.now())
            village = st.text_input("Village", max_chars=100)
            region = st.text_input("Région", max_chars=100)
            commune = st.text_input("Commune", max_chars=100)

        with col2:
            type_options = ["Arpentage", "Bornage", "Nivellement", "Parcellaire", "Autre"]
            type_leve = st.selectbox("Type de levé", options=type_options)
            if type_leve == "Autre":
                type_leve = st.text_input("Préciser le type")

            quantite = st.number_input("Quantité", min_value=1, max_value=10000, value=1)
            appareil_options = ["GPS", "Station totale", "Drone", "Théodolite", "Autre"]
            appareil = st.selectbox("Appareil utilisé", options=appareil_options)
            if appareil == "Autre":
                appareil = st.text_input("Préciser l'appareil")

        # Pour les admins, permettre de choisir le topographe
        if st.session_state.user["role"] == "administrateur":
            # Récupérer la liste des topographes
            users_df = get_users()
            topographes = users_df[users_df['role'] == 'topographe']['username'].tolist()
            
            # Ajouter l'option "Autre" pour les cas spéciaux
            topographes.append("Autre")
            
            selected_topographe = st.selectbox("Topographe", options=topographes)
            if selected_topographe == "Autre":
                topographe = st.text_input("Préciser le topographe")
            else:
                topographe = selected_topographe
        else:
            # Pour les topographes, utiliser leur nom d'utilisateur
            topographe = st.session_state.username

        submit = st.form_submit_button("Enregistrer le levé")

        if submit:
            if not village or not type_leve:
                st.error("Le village et le type de levé sont obligatoires.")
            else:
                success = add_leve(date, village, region, commune, type_leve, quantite, appareil, topographe)
                if success:
                    st.success("Levé topographique enregistré avec succès!")
                    time.sleep(1)
                    st.rerun()  # Rafraîchir la page après l'ajout
                else:
                    st.error("Erreur lors de l'enregistrement du levé.")

# Fonction pour afficher la page de suivi des levés
def show_tracking_page():
    st.title("Suivi des levés topographiques")

    # Déterminer quels levés afficher en fonction du rôle
    role = st.session_state.user["role"]
    username = st.session_state.username

    if role == "administrateur":
        # Les administrateurs peuvent voir tous les levés
        leves_df = get_all_leves()
    else:
        # Les topographes ne voient que leurs propres levés
        leves_df = get_leves_by_topographe(username)

    # Filtres
    with st.expander("Filtres", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("Date de début", datetime.now() - timedelta(days=30))
        
        with col2:
            end_date = st.date_input("Date de fin", datetime.now())
        
        # Récupérer les options de filtre
        filter_options = get_filter_options()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filtre par village
            village_options = ["Tous"] + filter_options["villages"]
            selected_village = st.selectbox("Village", options=village_options, index=0)
            
        with col2:
            # Filtre par région
            region_options = ["Toutes"] + filter_options["regions"]
            selected_region = st.selectbox("Région", options=region_options, index=0)
            
        with col3:
            # Filtre par type de levé
            type_options = ["Tous"] + filter_options["types"]
            selected_type = st.selectbox("Type de levé", options=type_options, index=0)
        
        # Pour les administrateurs, ajouter un filtre par topographe
        if role == "administrateur":
            topo_options = ["Tous"] + filter_options["topographes"]
            selected_topo = st.selectbox("Topographe", options=topo_options, index=0)
        else:
            selected_topo = username

        # Bouton pour appliquer les filtres
        if st.button("Appliquer les filtres"):
            # Convertir les options "Tous"/"Toutes" en None pour la fonction
            village_filter = None if selected_village == "Tous" else selected_village
            region_filter = None if selected_region == "Toutes" else selected_region
            type_filter = None if selected_type == "Tous" else selected_type
            topo_filter = None if role == "administrateur" and selected_topo == "Tous" else selected_topo
            
            # Récupérer les levés filtrés
            leves_df = get_filtered_leves(
                start_date=start_date,
                end_date=end_date,
                village=village_filter,
                region=region_filter,
                type_leve=type_filter,
                topographe=topo_filter
            )

    # Affichage des levés
    if not leves_df.empty:
        # Conversion de la colonne date pour un meilleur affichage
        leves_df['date'] = pd.to_datetime(leves_df['date']).dt.strftime('%d/%m/%Y')
        
        # Afficher le nombre total de levés
        st.write(f"Total des levés : **{len(leves_df)}**")
        
        # Préparation du DataFrame pour l'affichage
        display_df = leves_df.copy()
        
        # Colonnes à afficher
        display_cols = ['id', 'date', 'village', 'region', 'commune', 'type', 'quantite', 'appareil', 'topographe']
        
        # Pagination pour améliorer les performances
        items_per_page = 20
        total_pages = len(display_df) // items_per_page + (1 if len(display_df) % items_per_page > 0 else 0)
        
        # Si plus d'une page est nécessaire, afficher la pagination
        if total_pages > 1:
            page_num = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
        else:
            page_num = 1
        
        # Calcul de l'index de début et de fin pour la pagination
        start_idx = (page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(display_df))
        
        # Afficher le sous-ensemble de données pour la page actuelle
        display_page = display_df.iloc[start_idx:end_idx]
        
        # Afficher le tableau avec les données paginées
        st.dataframe(display_page[display_cols], use_container_width=True)
        
        # Afficher la pagination
        if total_pages > 1:
            st.write(f"Page {page_num} sur {total_pages}")
            
            col1, col2 = st.columns(2)
            with col1:
                if page_num > 1:
                    if st.button("Page précédente"):
                        st.session_state.page_num = page_num - 1
                        st.rerun()
            with col2:
                if page_num < total_pages:
                    if st.button("Page suivante"):
                        st.session_state.page_num = page_num + 1
                        st.rerun()
        
        # Fonctionnalité de suppression de levé
        st.subheader("Supprimer un levé")
        with st.form("delete_leve_form"):
            leve_id = st.number_input("ID du levé à supprimer", min_value=1, step=1)
            delete_button = st.form_submit_button("Supprimer le levé")
            
            if delete_button:
                if role == "administrateur":
                    # Les administrateurs peuvent supprimer n'importe quel levé
                    success = delete_leve(leve_id)
                    if success:
                        st.success(f"Levé ID {leve_id} supprimé avec succès!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Erreur lors de la suppression du levé ID {leve_id}.")
                else:
                    # Les topographes ne peuvent supprimer que leurs propres levés
                    success, message = delete_user_leve(leve_id, username)
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info("Aucun levé topographique trouvé.")

# Fonction pour afficher la page Mon Compte
def show_account_page():
    st.title("Mon Compte")

    username = st.session_state.username
    user_role = st.session_state.user["role"]

    st.write(f"**Nom d'utilisateur:** {username}")
    st.write(f"**Rôle:** {user_role}")

    # Changer le mot de passe
    st.subheader("Changer mon mot de passe")
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
            else:
                # Vérifier le mot de passe actuel
                user = verify_user(username, current_password)
                if user:
                    # Changer le mot de passe
                    success = change_password(username, new_password)
                    if success:
                        st.success("Mot de passe changé avec succès!")
                    else:
                        st.error("Erreur lors du changement du mot de passe.")
                else:
                    st.error("Mot de passe actuel incorrect.")

# Fonction pour afficher la page d'administration des utilisateurs
def show_admin_users_page():
    st.title("Gestion des Utilisateurs")

    # Vérifier si l'utilisateur est administrateur
    if st.session_state.user["role"] != "administrateur":
        st.error("Accès non autorisé.")
        return

    # Onglets pour séparer les fonctionnalités d'administration
    tab1, tab2 = st.tabs(["Liste des utilisateurs", "Ajouter un utilisateur"])

    with tab1:
        st.subheader("Liste des utilisateurs")
        users_df = get_users()
        
        if not users_df.empty:
            # Afficher le tableau des utilisateurs
            st.dataframe(users_df[['id', 'username', 'email', 'phone', 'role', 'created_at']], use_container_width=True)
            
            # Formulaire pour supprimer un utilisateur
            with st.form("delete_user_form"):
                user_id = st.number_input("ID de l'utilisateur à supprimer", min_value=1, step=1)
                delete_button = st.form_submit_button("Supprimer l'utilisateur")
                
                if delete_button:
                    success, message = delete_user(user_id)
                    if success:
                        st.success(message)
                        st.session_state.refresh_users = True
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.info("Aucun utilisateur trouvé.")

    with tab2:
        st.subheader("Ajouter un nouvel utilisateur")
        with st.form("add_user_form"):
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            confirm_password = st.text_input("Confirmer le mot de passe", type="password")
            email = st.text_input("Email")
            phone = st.text_input("Numéro de téléphone")
            role = st.selectbox("Rôle", options=["topographe", "administrateur"])

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
                        st.session_state.refresh_users = True
                        st.rerun()
                    else:
                        st.error(message)

# Fonction pour afficher la page d'administration des données
def show_admin_data_page():
    st.title("Gestion des Données")

    # Vérifier si l'utilisateur est administrateur
    if st.session_state.user["role"] != "administrateur":
        st.error("Accès non autorisé.")
        return

    # Onglets pour séparer les fonctionnalités
    tab1, tab2 = st.tabs(["Statistiques", "Maintenance"])

    with tab1:
        st.subheader("Statistiques générales")
        
        # Récupérer les levés
        leves_df = get_all_leves()
        
        if not leves_df.empty:
            # Statistiques générales
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Nombre total de levés", len(leves_df))
            with col2:
                st.metric("Nombre de villages", leves_df['village'].nunique())
            with col3:
                st.metric("Nombre de topographes", leves_df['topographe'].nunique())
            
            # Graphique des levés par région
            st.subheader("Levés par région")
            if not leves_df['region'].isna().all():
                region_counts = leves_df['region'].value_counts().reset_index()
                region_counts.columns = ['region', 'count']
                
                fig = px.pie(
                    region_counts, 
                    values='count', 
                    names='region',
                    title="Répartition des levés par région",
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée régionale disponible.")
        else:
            st.info("Aucun levé topographique n'a été enregistré.")

    with tab2:
        st.subheader("Maintenance de la base de données")
        
        # Bouton pour rafraîchir les caches
        if st.button("Rafraîchir les caches"):
            # Vider tous les caches
            data_cache.clear()
            connection_cache.clear()
            st.success("Tous les caches ont été vidés avec succès!")
            time.sleep(1)
            st.rerun()

# Fonction principale
def main():
    # Initialisation de la base de données
    init_db()

    # Initialisation des variables de session
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "show_login" not in st.session_state:
        st.session_state.show_login = False
    if "show_registration" not in st.session_state:
        st.session_state.show_registration = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"
    if "page_num" not in st.session_state:
        st.session_state.page_num = 1

    # Affichage des pages selon l'état
    if st.session_state.show_login:
        show_login_page()
    elif st.session_state.show_registration:
        show_registration_page()
    else:
        # Affichage de la navigation
        current_page = show_navigation_sidebar()
        
        # Affichage des différentes pages
        if current_page == "Dashboard":
            show_dashboard()
        elif current_page == "Saisie des Levés":
            if st.session_state.authenticated:
                show_leve_entry_page()
            else:
                st.error("Veuillez vous connecter pour accéder à cette page.")
                st.session_state.show_login = True
                st.rerun()
        elif current_page == "Suivi":
            if st.session_state.authenticated:
                show_tracking_page()
            else:
                st.error("Veuillez vous connecter pour accéder à cette page.")
                st.session_state.show_login = True
                st.rerun()
        elif current_page == "Mon Compte":
            if st.session_state.authenticated:
                show_account_page()
            else:
                st.error("Veuillez vous connecter pour accéder à cette page.")
                st.session_state.show_login = True
                st.rerun()
        elif current_page == "Admin Users":
            if st.session_state.authenticated and st.session_state.user["role"] == "administrateur":
                show_admin_users_page()
            else:
                st.error("Accès non autorisé.")
                st.session_state.current_page = "Dashboard"
                st.rerun()
        elif current_page == "Admin Data":
            if st.session_state.authenticated and st.session_state.user["role"] == "administrateur":
                show_admin_data_page()
            else:
                st.error("Accès non autorisé.")
                st.session_state.current_page = "Dashboard"
                st.rerun()

# Lancement de l'application
if __name__ == "__main__":
    main()
