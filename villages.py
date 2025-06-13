import pandas as pd
import streamlit as st
from functools import lru_cache

@st.cache_data(ttl=3600)  # Cache pendant 1 heure
def load_villages_data_cached():
    """
    Charge les données des villages avec mise en cache
    TTL de 1 heure pour éviter de recharger trop souvent
    """
    try:
        excel_file = "Villages.xlsx"
        df = pd.read_excel(excel_file)
        df.columns = [col.lower() for col in df.columns]
        
        required_columns = ['village', 'commune', 'region']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Le fichier Excel ne contient pas la colonne requise: {col}")
                return None
        
        # Nettoyer les données
        df = df.dropna(subset=required_columns)  # Supprimer les lignes avec des valeurs manquantes
        
        villages_data = {}
        for _, row in df.iterrows():
            region = str(row['region']).strip()
            commune = str(row['commune']).strip() 
            village = str(row['village']).strip()
            
            if not region or not commune or not village:
                continue
                
            if region not in villages_data:
                villages_data[region] = {}
            if commune not in villages_data[region]:
                villages_data[region][commune] = []
            if village not in villages_data[region][commune]:
                villages_data[region][commune].append(village)
        
        # Trier une seule fois
        for region in villages_data:
            for commune in villages_data[region]:
                villages_data[region][commune].sort()
        
        return villages_data
        
    except Exception as e:
        st.error(f"Erreur lors du chargement des villages: {str(e)}")
        return None

@st.cache_data
def get_regions_list():
    """Retourne la liste triée des régions"""
    villages_data = load_villages_data_cached()
    if villages_data:
        return [""] + sorted(list(villages_data.keys()))
    return [""]

@st.cache_data
def get_communes_list(region):
    """Retourne la liste triée des communes pour une région donnée"""
    if not region:
        return [""]
    
    villages_data = load_villages_data_cached()
    if villages_data and region in villages_data:
        return [""] + sorted(list(villages_data[region].keys()))
    return [""]

@st.cache_data
def get_villages_list(region, commune):
    """Retourne la liste triée des villages pour une région/commune donnée"""
    if not region or not commune:
        return [""]
    
    villages_data = load_villages_data_cached()
    if villages_data and region in villages_data and commune in villages_data[region]:
        return [""] + villages_data[region][commune]
    return [""]

def load_villages_data():
    """
    Version simplifiée qui utilise le cache
    Maintient la compatibilité avec l'ancien code
    """
    villages_data = load_villages_data_cached()
    if villages_data is not None:
        st.session_state.villages_data = villages_data
        return True
    else:
        st.session_state.villages_data = {}
        return False

def get_index_or_default(options_list, value, default=0):
    """Version optimisée avec gestion d'erreur améliorée"""
    if not options_list or not value:
        return default
    try:
        return options_list.index(value)
    except (ValueError, TypeError):
        return default

# Fonctions utilitaires pour éviter les accès répétés au session_state
def get_cached_form_data(key, default=""):
    """Récupère une valeur du cache avec une valeur par défaut"""
    return st.session_state.get("cached_form_data", {}).get(key, default)

def update_cached_form_data(key, value):
    """Met à jour une valeur dans le cache"""
    if "cached_form_data" not in st.session_state:
        st.session_state.cached_form_data = {}
    st.session_state.cached_form_data[key] = value
