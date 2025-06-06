import pandas as pd
from db import get_connection, get_engine

def add_leve(date, village, region, commune, type_leve, quantite, appareil, topographe, superviseur):
    conn = get_connection()
    if not conn:
        return False
    c = conn.cursor()
    try:
        quantite = int(quantite)
        c.execute('''
        INSERT INTO leves (date, village, region, commune, type, quantite, appareil, topographe, superviseur)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (date, village, region, commune, type_leve, quantite, appareil, topographe, superviseur))
        conn.commit()
        success = True
    except Exception:
        conn.rollback()
        success = False
    conn.close()
    return success

def get_all_leves():
    engine = get_engine()
    if not engine:
        return pd.DataFrame()
    query = "SELECT * FROM leves ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine)
        return leves
    except Exception:
        return pd.DataFrame()

def get_filtered_leves(start_date=None, end_date=None, village=None, region=None, commune=None, type_leve=None, appareil=None, topographe=None, superviseur=None):
    engine = get_engine()
    if not engine:
        return pd.DataFrame()
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
    if superviseur:
        query += " AND superviseur = %(superviseur)s"
        params['superviseur'] = superviseur
    query += " ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine, params=params)
        return leves
    except Exception:
        return pd.DataFrame()

def get_leves_by_topographe(topographe):
    engine = get_engine()
    if not engine:
        return pd.DataFrame()
    query = "SELECT * FROM leves WHERE topographe=%s ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine, params=(topographe,))
        return leves
    except Exception:
        return pd.DataFrame()

def get_leves_by_superviseur(superviseur):
    """Récupère toutes les levées saisies par un superviseur"""
    engine = get_engine()
    if not engine:
        return pd.DataFrame()
    query = "SELECT * FROM leves WHERE superviseur=%s ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine, params=(superviseur,))
        return leves
    except Exception:
        return pd.DataFrame()

def delete_leve(leve_id):
    conn = get_connection()
    if not conn:
        return False
    c = conn.cursor()
    try:
        c.execute("DELETE FROM leves WHERE id=%s", (leve_id,))
        conn.commit()
        success = True
    except Exception:
        conn.rollback()
        success = False
    conn.close()
    return success

def is_leve_owner(leve_id, username, user_role):
    """Vérifie si l'utilisateur peut modifier/supprimer cette levée"""
    conn = get_connection()
    if not conn:
        return False
    c = conn.cursor()
    c.execute("SELECT superviseur FROM leves WHERE id=%s", (leve_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return False
    
    # L'administrateur peut tout modifier
    if user_role == "administrateur":
        return True
    
    # Le superviseur peut modifier ses propres levées
    if user_role == "superviseur" and result[0] == username:
        return True
    
    return False

def delete_user_leve(leve_id, username, user_role):
    if not is_leve_owner(leve_id, username, user_role):
        return False, "Vous n'êtes pas autorisé à supprimer ce levé."
    
    conn = get_connection()
    if not conn:
        return False, "Erreur de connexion à la base de données"
    c = conn.cursor()
    try:
        if user_role == "administrateur":
            # L'admin peut supprimer n'importe quelle levée
            c.execute("DELETE FROM leves WHERE id=%s", (leve_id,))
        else:
            # Le superviseur ne peut supprimer que ses propres levées
            c.execute("DELETE FROM leves WHERE id=%s AND superviseur=%s", (leve_id, username))
        
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

def update_leve(leve_id, date, village, region, commune, type_leve, quantite, appareil, topographe, username, user_role):
    """Met à jour une levée existante"""
    if not is_leve_owner(leve_id, username, user_role):
        return False, "Vous n'êtes pas autorisé à modifier ce levé."
    
    conn = get_connection()
    if not conn:
        return False, "Erreur de connexion à la base de données"
    c = conn.cursor()
    try:
        quantite = int(quantite)
        if user_role == "administrateur":
            # L'admin peut modifier n'importe quelle levée
            c.execute('''
            UPDATE leves SET date=%s, village=%s, region=%s, commune=%s, type=%s, quantite=%s, appareil=%s, topographe=%s
            WHERE id=%s
            ''', (date, village, region, commune, type_leve, quantite, appareil, topographe, leve_id))
        else:
            # Le superviseur ne peut modifier que ses propres levées
            c.execute('''
            UPDATE leves SET date=%s, village=%s, region=%s, commune=%s, type=%s, quantite=%s, appareil=%s, topographe=%s
            WHERE id=%s AND superviseur=%s
            ''', (date, village, region, commune, type_leve, quantite, appareil, topographe, leve_id, username))
        
        if c.rowcount == 0:
            conn.close()
            return False, "Levé non trouvé ou vous n'êtes pas autorisé à le modifier."
        
        conn.commit()
        success = True
        message = "Levé modifié avec succès!"
    except Exception as e:
        conn.rollback()
        success = False
        message = f"Erreur lors de la modification du levé: {str(e)}"
    conn.close()
    return success, message

def get_leve_by_id(leve_id):
    """Récupère une levée par son ID"""
    conn = get_connection()
    if not conn:
        return None
    c = conn.cursor()
    c.execute("SELECT * FROM leves WHERE id=%s", (leve_id,))
    result = c.fetchone()
    conn.close()
    return result

def get_filter_options():
    engine = get_engine()
    if not engine:
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": [], "superviseurs": []}
    try:
        villages = pd.read_sql_query("SELECT DISTINCT village FROM leves ORDER BY village", engine)
        regions = pd.read_sql_query("SELECT DISTINCT region FROM leves WHERE region IS NOT NULL ORDER BY region", engine)
        communes = pd.read_sql_query("SELECT DISTINCT commune FROM leves WHERE commune IS NOT NULL ORDER BY commune", engine)
        types = pd.read_sql_query("SELECT DISTINCT type FROM leves ORDER BY type", engine)
        appareils = pd.read_sql_query("SELECT DISTINCT appareil FROM leves WHERE appareil IS NOT NULL ORDER BY appareil", engine)
        topographes = pd.read_sql_query("SELECT DISTINCT topographe FROM leves ORDER BY topographe", engine)
        superviseurs = pd.read_sql_query("SELECT DISTINCT superviseur FROM leves WHERE superviseur IS NOT NULL ORDER BY superviseur", engine)
        return {
            "villages": villages["village"].tolist() if not villages.empty else [],
            "regions": regions["region"].tolist() if not regions.empty else [],
            "communes": communes["commune"].tolist() if not communes.empty else [],
            "types": types["type"].tolist() if not types.empty else [],
            "appareils": appareils["appareil"].tolist() if not appareils.empty else [],
            "topographes": topographes["topographe"].tolist() if not topographes.empty else [],
            "superviseurs": superviseurs["superviseur"].tolist() if not superviseurs.empty else []
        }
    except Exception:
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": [], "superviseurs": []}
