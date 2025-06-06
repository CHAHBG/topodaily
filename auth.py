import hashlib
import re
from db import get_connection, get_engine
import psycopg2
import pandas as pd

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def validate_phone(phone):
    """Validate phone number format (basic validation)"""
    # Remove spaces and common separators
    phone_clean = re.sub(r'[\s\-\(\)]+', '', phone)
    # Check if it contains only digits and has reasonable length
    return phone_clean.isdigit() and 8 <= len(phone_clean) <= 15

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

def delete_user(user_id):
    conn = get_connection()
    if not conn:
        return False, "Erreur de connexion à la base de données"
    c = conn.cursor()
    try:
        c.execute("SELECT username FROM users WHERE id=%s", (user_id,))
        user_data = c.fetchone()
        if not user_data:
            conn.close()
            return False, "Utilisateur non trouvé."
        username = user_data[0]
        if username == "admin":
            conn.close()
            return False, "Impossible de supprimer l'administrateur principal."
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
    except Exception:
        conn.rollback()
        success = False
    conn.close()
    return success

def get_users():
    engine = get_engine()
    if not engine:
        return pd.DataFrame()
    query = "SELECT id, username, email, phone, role, created_at FROM users"
    try:
        users = pd.read_sql_query(query, engine)
        return users
    except Exception:
        return pd.DataFrame()

def get_topographes_list():
    """Retourne la liste prédéfinie des topographes de BAKEL"""
    return [
        "Mouhamed Lamine THIOUB",
        "Mamadou GUEYE", 
        "Djibril BODIAN",
        "Arona FALL",
        "Moussa DIOL",
        "Mbaye GAYE",
        "Ousseynou THIAM",
        "Ousmane BA",
        "Djibril Gueye",
        "Yakhaya Toure",
        "Seydina Aliou Sow",
        "Ndeye Yandé Diop",
        "Mohamed Ahmed Sylla",
        "Souleymane Niang",
        "Cheikh Diawara",
        "Mignane Gning",
        "Serigne Saliou Sow",
        "Gora Dieng"
    ]

def can_create_accounts(user_role):
    """Vérifie si l'utilisateur peut créer des comptes"""
    return user_role == "administrateur"

def can_enter_surveys(user_role):
    """Vérifie si l'utilisateur peut saisir des levées"""
    return user_role in ["superviseur", "administrateur"]

def can_modify_survey(user_role, survey_creator, current_user):
    """Vérifie si l'utilisateur peut modifier une levée"""
    if user_role == "administrateur":
        return True
    if user_role == "superviseur" and survey_creator == current_user:
        return True
    return False
