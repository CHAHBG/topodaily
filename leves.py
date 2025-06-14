import pandas as pd
import logging
import streamlit as st
from datetime import datetime
from db import get_connection, get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@st.cache_data(ttl=3600)
def get_topographes_list():
    return [
        "", "Mouhamed Lamine THIOUB", "Mamadou GUEYE", "Djibril BODIAN", "Arona FALL", "Moussa DIOL",
        "Mbaye GAYE", "Ousseynou THIAM", "Ousmane BA",
        "Djibril Gueye", "Yakhaya Toure", "Seydina Aliou Sow", "Ndeye Yandé Diop",
        "Mohamed Ahmed Sylla", "Souleymane Niang", "Cheikh Diawara", "Mignane Gning",
        "Serigne Saliou Sow", "Gora Dieng"
    ]

@st.cache_data(ttl=3600)
def get_types_leve_list():
    return [
        "",
        "Levé de détail", "Levé topographique", "Levé cadastral", "Levé planimétrique",
        "Levé altimétrique", "Levé GPS", "Levé de bornage", "Levé de raccordement"
    ]

@st.cache_data(ttl=3600)
def get_appareils_list():
    return [
        "",
        "GPS Garmin", "GPS Trimble", "Théodolite", "Tachéomètre", "Niveau",
        "Station totale", "DGPS", "RTK GPS"
    ]

@st.cache_data(ttl=300)
def get_all_leves_cached():
    engine = get_engine()
    if not engine:
        logger.error("Impossible de se connecter à la base de données")
        return pd.DataFrame()
    query = "SELECT * FROM leves ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine)
        return leves
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des levés: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_user_leves_cached(username):
    engine = get_engine()
    if not engine:
        return pd.DataFrame()
    query = "SELECT * FROM leves WHERE superviseur=%s ORDER BY date DESC"
    try:
        leves_df = pd.read_sql_query(query, engine, params=(username,))
        return leves_df
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des levés utilisateur: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_filter_options_cached():
    engine = get_engine()
    if not engine:
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": [], "superviseurs": []}
    try:
        return {
            "villages": pd.read_sql_query("SELECT DISTINCT village FROM leves WHERE village IS NOT NULL ORDER BY village", engine)["village"].tolist(),
            "regions": pd.read_sql_query("SELECT DISTINCT region FROM leves WHERE region IS NOT NULL ORDER BY region", engine)["region"].tolist(),
            "communes": pd.read_sql_query("SELECT DISTINCT commune FROM leves WHERE commune IS NOT NULL ORDER BY commune", engine)["commune"].tolist(),
            "types": pd.read_sql_query("SELECT DISTINCT type FROM leves WHERE type IS NOT NULL ORDER BY type", engine)["type"].tolist(),
            "appareils": pd.read_sql_query("SELECT DISTINCT appareil FROM leves WHERE appareil IS NOT NULL ORDER BY appareil", engine)["appareil"].tolist(),
            "topographes": pd.read_sql_query("SELECT DISTINCT topographe FROM leves WHERE topographe IS NOT NULL ORDER BY topographe", engine)["topographe"].tolist(),
            "superviseurs": pd.read_sql_query("SELECT DISTINCT superviseur FROM leves WHERE superviseur IS NOT NULL ORDER BY superviseur", engine)["superviseur"].tolist(),
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des options de filtre: {str(e)}")
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": [], "superviseurs": []}

def clear_leves_cache():
    get_all_leves_cached.clear()
    get_filter_options_cached.clear()
    get_user_leves_cached.clear()

def add_leve(date, village, region, commune, type_leve, quantite, appareil, topographe, superviseur):
    conn = get_connection()
    if not conn:
        logger.error("Impossible de se connecter à la base de données")
        return False
    try:
        c = conn.cursor()
        quantite = int(quantite) if quantite else 0
        c.execute('''
            INSERT INTO leves (date, village, region, commune, type, quantite, appareil, topographe, superviseur)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (date, village, region, commune, type_leve, quantite, appareil, topographe, superviseur))
        conn.commit()
        clear_leves_cache()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de l'ajout du levé: {str(e)}")
        return False
    finally:
        conn.close()

def get_all_leves():
    return get_all_leves_cached()

def get_user_leves(username):
    return get_user_leves_cached(username)

def get_filter_options():
    return get_filter_options_cached()

def get_filtered_leves(
    start_date=None, end_date=None, village=None, region=None, commune=None, type_leve=None,
    appareil=None, topographe=None, superviseur=None
):
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
    except Exception as e:
        logger.error(f"Erreur lors du filtrage des levés: {str(e)}")
        return pd.DataFrame()

def get_leves_by_topographe(topographe):
    engine = get_engine()
    if not engine:
        return pd.DataFrame()
    query = "SELECT * FROM leves WHERE topographe=%s ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine, params=(topographe,))
        return leves
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des levés du topographe {topographe}: {str(e)}")
        return pd.DataFrame()

def get_leves_by_superviseur(superviseur):
    engine = get_engine()
    if not engine:
        return pd.DataFrame()
    query = "SELECT * FROM leves WHERE superviseur=%s ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine, params=(superviseur,))
        return leves
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des levés du superviseur {superviseur}: {str(e)}")
        return pd.DataFrame()

def delete_leve(leve_id):
    conn = get_connection()
    if not conn:
        return False
    try:
        c = conn.cursor()
        c.execute("DELETE FROM leves WHERE id=%s", (leve_id,))
        conn.commit()
        clear_leves_cache()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de la suppression du levé {leve_id}: {str(e)}")
        return False
    finally:
        conn.close()

def is_leve_owner(leve_id, username, user_role):
    conn = get_connection()
    if not conn:
        return False
    try:
        c = conn.cursor()
        c.execute("SELECT superviseur FROM leves WHERE id=%s", (leve_id,))
        result = c.fetchone()
        if not result:
            return False
        if user_role in ["administrateur", "admin"]:
            return True
        if user_role == "superviseur" and result[0] == username:
            return True
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du propriétaire du levé {leve_id}: {str(e)}")
        return False
    finally:
        conn.close()

def delete_user_leve(leve_id, username, user_role):
    if not is_leve_owner(leve_id, username, user_role):
        return False, "Vous n'êtes pas autorisé à supprimer ce levé."
    conn = get_connection()
    if not conn:
        return False, "Erreur de connexion à la base de données"
    try:
        c = conn.cursor()
        if user_role in ["administrateur", "admin"]:
            c.execute("DELETE FROM leves WHERE id=%s", (leve_id,))
        else:
            c.execute("DELETE FROM leves WHERE id=%s AND superviseur=%s", (leve_id, username))
        if c.rowcount == 0:
            return False, "Levé non trouvé ou vous n'êtes pas autorisé à le supprimer."
        conn.commit()
        clear_leves_cache()
        return True, "Levé supprimé avec succès!"
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de la suppression du levé {leve_id}: {str(e)}")
        return False, f"Erreur lors de la suppression du levé: {str(e)}"
    finally:
        conn.close()

def update_leve(leve_id, date, village, region, commune, type_leve, quantite, appareil, topographe, username, user_role):
    if not is_leve_owner(leve_id, username, user_role):
        return False, "Vous n'êtes pas autorisé à modifier ce levé."
    conn = get_connection()
    if not conn:
        return False, "Erreur de connexion à la base de données"
    try:
        c = conn.cursor()
        quantite = int(quantite) if quantite else 0
        if user_role in ["administrateur", "admin"]:
            c.execute('''
                UPDATE leves SET date=%s, village=%s, region=%s, commune=%s, type=%s, quantite=%s, appareil=%s, topographe=%s
                WHERE id=%s
            ''', (date, village, region, commune, type_leve, quantite, appareil, topographe, leve_id))
        else:
            c.execute('''
                UPDATE leves SET date=%s, village=%s, region=%s, commune=%s, type=%s, quantite=%s, appareil=%s, topographe=%s
                WHERE id=%s AND superviseur=%s
            ''', (date, village, region, commune, type_leve, quantite, appareil, topographe, leve_id, username))
        if c.rowcount == 0:
            return False, "Levé non trouvé ou vous n'êtes pas autorisé à le modifier."
        conn.commit()
        clear_leves_cache()
        return True, "Levé modifié avec succès!"
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de la modification du levé {leve_id}: {str(e)}")
        return False, f"Erreur lors de la modification du levé: {str(e)}"
    finally:
        conn.close()

def get_leve_by_id(leve_id):
    conn = get_connection()
    if not conn:
        return None
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM leves WHERE id=%s", (leve_id,))
        result = c.fetchone()
        if result:
            columns = [desc[0] for desc in c.description]
            return dict(zip(columns, result))
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du levé {leve_id}: {str(e)}")
        return None
    finally:
        conn.close()

def can_enter_surveys(user_role):
    return user_role in ["superviseur", "administrateur", "admin"]

def can_edit_leve(current_username, user_role, leve_superviseur):
    if user_role in ["administrateur", "admin"]:
        return True
    return current_username == leve_superviseur

def get_leves_statistics():
    engine = get_engine()
    if not engine:
        return {}
    try:
        stats = {}
        total_query = "SELECT COUNT(*) as total FROM leves"
        total_result = pd.read_sql_query(total_query, engine)
        stats['total_leves'] = total_result['total'].iloc[0] if not total_result.empty else 0
        type_query = "SELECT type, COUNT(*) as count FROM leves GROUP BY type ORDER BY count DESC"
        type_result = pd.read_sql_query(type_query, engine)
        stats['leves_par_type'] = type_result.to_dict('records') if not type_result.empty else []
        region_query = "SELECT region, COUNT(*) as count FROM leves WHERE region IS NOT NULL GROUP BY region ORDER BY count DESC"
        region_result = pd.read_sql_query(region_query, engine)
        stats['leves_par_region'] = region_result.to_dict('records') if not region_result.empty else []
        topo_query = "SELECT topographe, COUNT(*) as count FROM leves GROUP BY topographe ORDER BY count DESC LIMIT 10"
        topo_result = pd.read_sql_query(topo_query, engine)
        stats['top_topographes'] = topo_result.to_dict('records') if not topo_result.empty else []
        monthly_query = """
        SELECT 
            DATE_TRUNC('month', date) as mois,
            COUNT(*) as count 
        FROM leves 
        WHERE date >= NOW() - INTERVAL '12 MONTH'
        GROUP BY mois
        ORDER BY mois DESC
        """
        monthly_result = pd.read_sql_query(monthly_query, engine)
        stats['leves_par_mois'] = monthly_result.to_dict('records') if not monthly_result.empty else []
        return stats
    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques: {str(e)}")
        return {}

def export_leves_to_csv(leves_df, filename=None):
    if filename is None:
        filename = f"leves_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    try:
        leves_df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"Export CSV réussi: {filename}")
        return True, filename
    except Exception as e:
        logger.error(f"Erreur lors de l'export CSV: {str(e)}")
        return False, str(e)

def validate_leve_data(date, village, type_leve, quantite):
    errors = []
    if not date:
        errors.append("La date est obligatoire")
    else:
        try:
            if isinstance(date, str):
                datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            errors.append("Format de date invalide (YYYY-MM-DD attendu)")
    if not village or village.strip() == "":
        errors.append("Le village est obligatoire")
    if not type_leve or type_leve.strip() == "":
        errors.append("Le type de levé est obligatoire")
    if quantite:
        try:
            q = int(quantite)
            if q < 0:
                errors.append("La quantité ne peut pas être négative")
        except ValueError:
            errors.append("La quantité doit être un nombre entier")
    return errors

def search_leves(search_term):
    engine = get_engine()
    if not engine:
        return pd.DataFrame()
    query = """
    SELECT * FROM leves 
    WHERE village ILIKE %s 
    OR region ILIKE %s 
    OR commune ILIKE %s 
    OR topographe ILIKE %s
    OR superviseur ILIKE %s
    ORDER BY date DESC
    """
    search_pattern = f"%{search_term}%"
    params = (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern)
    try:
        leves = pd.read_sql_query(query, engine, params=params)
        return leves
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {str(e)}")
        return pd.DataFrame()

def get_recent_leves(limit=10):
    engine = get_engine()
    if not engine:
        return pd.DataFrame()
    query = f"SELECT * FROM leves ORDER BY date DESC, id DESC LIMIT {limit}"
    try:
        leves = pd.read_sql_query(query, engine)
        return leves
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des levés récents: {str(e)}")
        return pd.DataFrame()

def get_leves_count_by_period(start_date, end_date):
    engine = get_engine()
    if not engine:
        return 0
    query = "SELECT COUNT(*) as count FROM leves WHERE date BETWEEN %s AND %s"
    try:
        result = pd.read_sql_query(query, engine, params=(start_date, end_date))
        return result['count'].iloc[0] if not result.empty else 0
    except Exception as e:
        logger.error(f"Erreur lors du comptage des levés: {str(e)}")
        return 0
