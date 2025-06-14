import pandas as pd
import streamlit as st
import os
from functools import lru_cache

@st.cache_data(ttl=3600)  # Cache pendant 1 heure
def load_villages_data_cached():
    """
    Charge les données des villages avec mise en cache et gestion d'erreurs améliorée
    TTL de 1 heure pour éviter de recharger trop souvent
    """
    try:
        excel_file = "Villages.xlsx"
        
        # Vérifier si le fichier existe
        if not os.path.exists(excel_file):
            st.error(f"Le fichier {excel_file} n'existe pas dans le répertoire courant.")
            st.info(f"Répertoire actuel: {os.getcwd()}")
            st.info("Assurez-vous que le fichier Villages.xlsx est dans le même répertoire que votre application.")
            return {}
        
        # Charger le fichier Excel
        df = pd.read_excel(excel_file)
        
        # Vérifier si le DataFrame est vide
        if df.empty:
            st.error("Le fichier Excel est vide.")
            return {}
        
        # Normaliser les noms de colonnes
        df.columns = [col.lower().strip() for col in df.columns]
        
        # Afficher les colonnes disponibles pour le debug
      
        
        # Vérifier les colonnes requises
        required_columns = ['village', 'commune', 'region']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Le fichier Excel ne contient pas les colonnes requises: {missing_columns}")
            st.info("Colonnes requises: village, commune, region")
            return {}
        
        # Nettoyer les données
        df_clean = df.dropna(subset=required_columns).copy()
        
        # Vérifier s'il reste des données après nettoyage
        if df_clean.empty:
            st.error("Aucune donnée valide trouvée après nettoyage.")
            return {}
        
        # Construire la structure de données
        villages_data = {}
        processed_count = 0
        
        for _, row in df_clean.iterrows():
            try:
                region = str(row['region']).strip()
                commune = str(row['commune']).strip() 
                village = str(row['village']).strip()
                
                # Vérifier que les valeurs ne sont pas vides
                if not region or not commune or not village or region == 'nan' or commune == 'nan' or village == 'nan':
                    continue
                
                # Initialiser la structure si nécessaire
                if region not in villages_data:
                    villages_data[region] = {}
                if commune not in villages_data[region]:
                    villages_data[region][commune] = []
                if village not in villages_data[region][commune]:
                    villages_data[region][commune].append(village)
                    processed_count += 1
                    
            except Exception as e:
                st.warning(f"Erreur lors du traitement de la ligne {row.name}: {e}")
                continue
        
        # Trier les données
        for region in villages_data:
            for commune in villages_data[region]:
                villages_data[region][commune].sort()
        
        # Afficher les statistiques
        if villages_data:
            regions_count = len(villages_data)
            communes_count = sum(len(communes) for communes in villages_data.values())
            villages_count = sum(len(villages) for region in villages_data.values() for villages in region.values())
            
            st.success(f"Données chargées avec succès: {regions_count} régions, {communes_count} communes, {villages_count} villages")
        else:
            st.error("Aucune donnée valide n'a pu être extraite du fichier.")
        
        return villages_data
        
    except FileNotFoundError:
        st.error(f"Le fichier {excel_file} n'a pas été trouvé.")
        return {}
    except pd.errors.EmptyDataError:
        st.error("Le fichier Excel est vide ou corrompu.")
        return {}
    except Exception as e:
        st.error(f"Erreur lors du chargement des villages: {str(e)}")
        st.info("Vérifiez que le fichier Villages.xlsx est correctement formaté avec les colonnes: village, commune, region")
        return {}

def load_villages_data():
    """
    Version améliorée qui garantit le retour d'un dictionnaire
    Maintient la compatibilité avec l'ancien code
    """
    try:
        villages_data = load_villages_data_cached()
        
        # S'assurer que le résultat est un dictionnaire
        if not isinstance(villages_data, dict):
            st.error("Les données chargées ne sont pas dans le format attendu (dictionnaire).")
            villages_data = {}
        
        # Stocker dans le session state
        st.session_state.villages_data = villages_data
        
        # Retourner les données directement (et non un booléen)
        return villages_data
        
    except Exception as e:
        st.error(f"Erreur critique lors du chargement des villages: {e}")
        st.session_state.villages_data = {}
        return {}

# Fonctions utilitaires améliorées
@st.cache_data
def get_regions_list():
    """Retourne la liste triée des régions"""
    villages_data = load_villages_data_cached()
    if villages_data and isinstance(villages_data, dict):
        return [""] + sorted(list(villages_data.keys()))
    return [""]

@st.cache_data
def get_communes_list(region):
    """Retourne la liste triée des communes pour une région donnée"""
    if not region:
        return [""]
    
    villages_data = load_villages_data_cached()
    if villages_data and isinstance(villages_data, dict) and region in villages_data:
        return [""] + sorted(list(villages_data[region].keys()))
    return [""]

@st.cache_data
def get_villages_list(region, commune):
    """Retourne la liste triée des villages pour une région/commune donnée"""
    if not region or not commune:
        return [""]
    
    villages_data = load_villages_data_cached()
    if (villages_data and isinstance(villages_data, dict) and 
        region in villages_data and commune in villages_data[region]):
        return [""] + villages_data[region][commune]
    return [""]

def get_index_or_default(options_list, value, default=0):
    """Version optimisée avec gestion d'erreur améliorée"""
    if not options_list or not value:
        return default
    try:
        if isinstance(options_list, list) and value in options_list:
            return options_list.index(value)
        return default
    except (ValueError, TypeError, AttributeError):
        return default

# Fonctions de diagnostic
def diagnose_villages_file():
    """Fonction de diagnostic pour vérifier le fichier Villages.xlsx"""
    try:
        excel_file = "Villages.xlsx"
        
        if not os.path.exists(excel_file):
            return f"❌ Fichier {excel_file} introuvable"
        
        df = pd.read_excel(excel_file)
        
        if df.empty:
            return "❌ Fichier vide"
        
        result = f"✅ Fichier trouvé: {len(df)} lignes\n"
        result += f"📋 Colonnes: {list(df.columns)}\n"
        
        # Vérifier les colonnes requises
        required_columns = ['village', 'commune', 'region']
        df.columns = [col.lower().strip() for col in df.columns]
        
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            result += f"❌ Colonnes manquantes: {missing}"
        else:
            result += "✅ Toutes les colonnes requises sont présentes"
        
        return result
        
    except Exception as e:
        return f"❌ Erreur: {e}"

# Fonction pour créer un fichier de test
def create_sample_villages_file():
    """Crée un fichier Villages.xlsx de test"""
    data = {
        'Region': ['Dakar', 'Dakar', 'Dakar', 'Thiès', 'Thiès', 'Thiès'],
        'Commune': ['Dakar', 'Dakar', 'Guédiawaye', 'Thiès', 'Thiès', 'Mbour'],
        'Village': ['Plateau', 'Médina', 'Sam Notaire', 'Randoulène', 'Mbour 1', 'Mbour 2']
    }
    
    df = pd.DataFrame(data)
    df.to_excel('Villages.xlsx', index=False)
    st.success("Fichier Villages.xlsx de test créé avec succès!")
    return True
