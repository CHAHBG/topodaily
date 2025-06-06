import pandas as pd
import logging
from datetime import datetime, date
from db import get_connection, get_engine

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_leve(date, village, region, commune, type_leve, quantite, appareil, topographe, superviseur):
    """Ajoute un nouveau levé dans la base de données"""
    conn = get_connection()
    if not conn:
        logger.error("Impossible de se connecter à la base de données")
        return False
    
    c = conn.cursor()
    try:
        quantite = int(quantite) if quantite else 0
        c.execute('''
        INSERT INTO leves (date, village, region, commune, type, quantite, appareil, topographe, superviseur)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (date, village, region, commune, type_leve, quantite, appareil, topographe, superviseur))
        conn.commit()
        logger.info(f"Levé ajouté avec succès: {village} - {type_leve}")
        success = True
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de l'ajout du levé: {str(e)}")
        success = False
    finally:
        conn.close()
    return success

def get_all_leves():
    """Récupère tous les levés de la base de données"""
    engine = get_engine()
    if not engine:
        logger.error("Impossible de se connecter à la base de données")
        return pd.DataFrame()
    
    query = "SELECT * FROM leves ORDER BY date DESC"
    try:
        leves = pd.read_sql_query(query, engine)
        logger.info(f"Récupération de {len(leves)} levés")
        return leves
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des levés: {str(e)}")
        return pd.DataFrame()

def get_filtered_leves(start_date=None, end_date=None, village=None, region=None, commune=None, type_leve=None, appareil=None, topographe=None, superviseur=None):
    """Récupère les levés filtrés selon les critères spécifiés"""
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
    """Récupère tous les levés d'un topographe spécifique"""
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
    """Récupère toutes les levées saisies par un superviseur"""
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
    """Supprime un levé (fonction administrative)"""
    conn = get_connection()
    if not conn:
        return False
    
    c = conn.cursor()
    try:
        c.execute("DELETE FROM leves WHERE id=%s", (leve_id,))
        conn.commit()
        logger.info(f"Levé {leve_id} supprimé")
        success = True
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de la suppression du levé {leve_id}: {str(e)}")
        success = False
    finally:
        conn.close()
    return success

def is_leve_owner(leve_id, username, user_role):
    """Vérifie si l'utilisateur peut modifier/supprimer cette levée"""
    conn = get_connection()
    if not conn:
        return False
    
    c = conn.cursor()
    try:
        c.execute("SELECT superviseur FROM leves WHERE id=%s", (leve_id,))
        result = c.fetchone()
        
        if not result:
            return False
        
        # L'administrateur peut tout modifier
        if user_role in ["administrateur", "admin"]:
            return True
        
        # Le superviseur peut modifier ses propres levées
        if user_role == "superviseur" and result[0] == username:
            return True
        
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du propriétaire du levé {leve_id}: {str(e)}")
        return False
    finally:
        conn.close()

def delete_user_leve(leve_id, username, user_role):
    """Supprime un levé avec vérification des droits utilisateur"""
    if not is_leve_owner(leve_id, username, user_role):
        return False, "Vous n'êtes pas autorisé à supprimer ce levé."
    
    conn = get_connection()
    if not conn:
        return False, "Erreur de connexion à la base de données"
    
    c = conn.cursor()
    try:
        if user_role in ["administrateur", "admin"]:
            # L'admin peut supprimer n'importe quelle levée
            c.execute("DELETE FROM leves WHERE id=%s", (leve_id,))
        else:
            # Le superviseur ne peut supprimer que ses propres levées
            c.execute("DELETE FROM leves WHERE id=%s AND superviseur=%s", (leve_id, username))
        
        if c.rowcount == 0:
            return False, "Levé non trouvé ou vous n'êtes pas autorisé à le supprimer."
        
        conn.commit()
        logger.info(f"Levé {leve_id} supprimé par {username}")
        return True, "Levé supprimé avec succès!"
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de la suppression du levé {leve_id}: {str(e)}")
        return False, f"Erreur lors de la suppression du levé: {str(e)}"
    finally:
        conn.close()

def update_leve(leve_id, date, village, region, commune, type_leve, quantite, appareil, topographe, username, user_role):
    """Met à jour une levée existante"""
    if not is_leve_owner(leve_id, username, user_role):
        return False, "Vous n'êtes pas autorisé à modifier ce levé."
    
    conn = get_connection()
    if not conn:
        return False, "Erreur de connexion à la base de données"
    
    c = conn.cursor()
    try:
        quantite = int(quantite) if quantite else 0
        
        if user_role in ["administrateur", "admin"]:
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
            return False, "Levé non trouvé ou vous n'êtes pas autorisé à le modifier."
        
        conn.commit()
        logger.info(f"Levé {leve_id} modifié par {username}")
        return True, "Levé modifié avec succès!"
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de la modification du levé {leve_id}: {str(e)}")
        return False, f"Erreur lors de la modification du levé: {str(e)}"
    finally:
        conn.close()

def get_leve_by_id(leve_id):
    """Récupère une levée par son ID"""
    conn = get_connection()
    if not conn:
        return None
    
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM leves WHERE id=%s", (leve_id,))
        result = c.fetchone()
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du levé {leve_id}: {str(e)}")
        return None
    finally:
        conn.close()

def get_filter_options():
    """Récupère toutes les options disponibles pour les filtres"""
    engine = get_engine()
    if not engine:
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": [], "superviseurs": []}
    
    try:
        villages = pd.read_sql_query("SELECT DISTINCT village FROM leves WHERE village IS NOT NULL ORDER BY village", engine)
        regions = pd.read_sql_query("SELECT DISTINCT region FROM leves WHERE region IS NOT NULL ORDER BY region", engine)
        communes = pd.read_sql_query("SELECT DISTINCT commune FROM leves WHERE commune IS NOT NULL ORDER BY commune", engine)
        types = pd.read_sql_query("SELECT DISTINCT type FROM leves WHERE type IS NOT NULL ORDER BY type", engine)
        appareils = pd.read_sql_query("SELECT DISTINCT appareil FROM leves WHERE appareil IS NOT NULL ORDER BY appareil", engine)
        topographes = pd.read_sql_query("SELECT DISTINCT topographe FROM leves WHERE topographe IS NOT NULL ORDER BY topographe", engine)
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
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des options de filtre: {str(e)}")
        return {"villages": [], "regions": [], "communes": [], "types": [], "appareils": [], "topographes": [], "superviseurs": []}

# Fonctions helper supplémentaires

def get_topographes_list():
    """Récupère la liste de tous les topographes disponibles"""
    return [
        "",  # Option vide
        # Topographes de BAKEL
        "Mouhamed Lamine THIOUB",
        "Mamadou GUEYE", 
        "Djibril BODIAN",
        "Arona FALL",
        "Moussa DIOL",
        "Mbaye GAYE",
        "Ousseynou THIAM",
        "Ousmane BA",
        # Topographes de Kédougou
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

def get_types_leve_list():
    """Récupère la liste des types de levés disponibles"""
    return [
        "",
        "Levé de détail",
        "Levé topographique",
        "Levé cadastral",
        "Levé planimétrique",
        "Levé altimétrique",
        "Levé GPS",
        "Levé de bornage",
        "Levé de raccordement"
    ]

def get_appareils_list():
    """Récupère la liste des appareils disponibles"""
    return [
        "",
        "GPS Garmin",
        "GPS Trimble",
        "Théodolite",
        "Tachéomètre",
        "Niveau",
        "Station totale",
        "DGPS",
        "RTK GPS"
    ]

def can_enter_surveys(user_role):
    """Vérifie si l'utilisateur peut saisir des levées"""
    return user_role in ["superviseur", "administrateur", "admin"]

def can_edit_leve(current_username, user_role, leve_superviseur):
    """Vérifie si l'utilisateur peut modifier un levé spécifique"""
    if user_role in ["administrateur", "admin"]:
        return True
    return current_username == leve_superviseur

def get_leves_statistics():
    """Récupère les statistiques sur les levés"""
    engine = get_engine()
    if not engine:
        return {}
    
    try:
        stats = {}
        
        # Total des levés
        total_query = "SELECT COUNT(*) as total FROM leves"
        total_result = pd.read_sql_query(total_query, engine)
        stats['total_leves'] = total_result['total'].iloc[0] if not total_result.empty else 0
        
        # Levés par type
        type_query = "SELECT type, COUNT(*) as count FROM leves GROUP BY type ORDER BY count DESC"
        type_result = pd.read_sql_query(type_query, engine)
        stats['leves_par_type'] = type_result.to_dict('records') if not type_result.empty else []
        
        # Levés par région
        region_query = "SELECT region, COUNT(*) as count FROM leves WHERE region IS NOT NULL GROUP BY region ORDER BY count DESC"
        region_result = pd.read_sql_query(region_query, engine)
        stats['leves_par_region'] = region_result.to_dict('records') if not region_result.empty else []
        
        # Levés par topographe
        topo_query = "SELECT topographe, COUNT(*) as count FROM leves GROUP BY topographe ORDER BY count DESC LIMIT 10"
        topo_result = pd.read_sql_query(topo_query, engine)
        stats['top_topographes'] = topo_result.to_dict('records') if not topo_result.empty else []
        
        # Levés par mois (derniers 12 mois)
        monthly_query = """
        SELECT 
            DATE_FORMAT(date, '%Y-%m') as mois,
            COUNT(*) as count 
        FROM leves 
        WHERE date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(date, '%Y-%m')
        ORDER BY mois DESC
        """
        monthly_result = pd.read_sql_query(monthly_query, engine)
        stats['leves_par_mois'] = monthly_result.to_dict('records') if not monthly_result.empty else []
        
        return stats
    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques: {str(e)}")
        return {}

def export_leves_to_csv(leves_df, filename=None):
    """Exporte les levés vers un fichier CSV"""
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
    """Valide les données d'un levé avant insertion/modification"""
    errors = []
    
    # Validation de la date
    if not date:
        errors.append("La date est obligatoire")
    else:
        try:
            if isinstance(date, str):
                datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            errors.append("Format de date invalide (YYYY-MM-DD attendu)")
    
    # Validation du village
    if not village or village.strip() == "":
        errors.append("Le village est obligatoire")
    
    # Validation du type de levé
    if not type_leve or type_leve.strip() == "":
        errors.append("Le type de levé est obligatoire")
    
    # Validation de la quantité
    if quantite:
        try:
            q = int(quantite)
            if q < 0:
                errors.append("La quantité ne peut pas être négative")
        except ValueError:
            errors.append("La quantité doit être un nombre entier")
    
    return errors

def search_leves(search_term):
    """Recherche les levés par terme de recherche"""
    engine = get_engine()
    if not engine:
        return pd.DataFrame()
    
    query = """
    SELECT * FROM leves 
    WHERE village LIKE %s 
    OR region LIKE %s 
    OR commune LIKE %s 
    OR topographe LIKE %s
    OR superviseur LIKE %s
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
    """Récupère les levés les plus récents"""
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
    """Compte les levés dans une période donnée"""
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
