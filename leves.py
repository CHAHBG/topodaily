import pandas as pd
from db import get_connection, get_engine

def add_leve(date, village, region, commune, type_leve, quantite, appareil, topographe):
    conn = get_connection()
    if not conn:
        return False
    c = conn.cursor()
    try:
        quantite = int(quantite)
        c.execute('''
        INSERT INTO leves (date, village, region, commune, type, quantite, appareil, topographe)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (date, village, region, commune, type_leve, quantite, appareil, topographe))
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

def get_filtered_leves(start_date=None, end_date=None, village=None, region=None, commune=None, type_leve=None, appareil=None, topographe=None):
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

def delete_user_leve(leve_id, username):
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

def get_filter_options():
    engine = get_engine()
    if not engine:
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": []}
    try:
        villages = pd.read_sql_query("SELECT DISTINCT village FROM leves ORDER BY village", engine)
        regions = pd.read_sql_query("SELECT DISTINCT region FROM leves WHERE region IS NOT NULL ORDER BY region", engine)
        communes = pd.read_sql_query("SELECT DISTINCT commune FROM leves WHERE commune IS NOT NULL ORDER BY commune", engine)
        types = pd.read_sql_query("SELECT DISTINCT type FROM leves ORDER BY type", engine)
        appareils = pd.read_sql_query("SELECT DISTINCT appareil FROM leves WHERE appareil IS NOT NULL ORDER BY appareil", engine)
        topographes = pd.read_sql_query("SELECT DISTINCT topographe FROM leves ORDER BY topographe", engine)
        return {
            "villages": villages["village"].tolist() if not villages.empty else [],
            "regions": regions["region"].tolist() if not regions.empty else [],
            "communes": communes["commune"].tolist() if not communes.empty else [],
            "types": types["type"].tolist() if not types.empty else [],
            "appareils": appareils["appareil"].tolist() if not appareils.empty else [],
            "topographes": topographes["topographe"].tolist() if not topographes.empty else []
        }
    except Exception:
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": []}