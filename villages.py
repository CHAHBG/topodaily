import pandas as pd
import streamlit as st
import os

@st.cache_data(ttl=3600)
def load_villages_structure():
    """
    Charge et structure toutes les données nécessaires en une seule passe :
    - Dictionnaire villages_data[region][commune] = [villages...]
    - Liste des régions, des communes par région, des villages par (région, commune)
    """
    excel_file = "Villages.xlsx"
    if not os.path.exists(excel_file):
        st.error(f"Le fichier {excel_file} n'existe pas dans le répertoire courant ({os.getcwd()})")
        return {}, [], {}, {}
    try:
        df = pd.read_excel(excel_file)
        if df.empty:
            st.error("Le fichier Excel est vide.")
            return {}, [], {}, {}
        df.columns = [col.lower().strip() for col in df.columns]
        required = ['village', 'commune', 'region']
        if any(col not in df.columns for col in required):
            st.error(f"Le fichier Excel doit contenir les colonnes : {required}")
            return {}, [], {}, {}
        df_clean = df.dropna(subset=required).copy()
        villages_data = {}
        region_list = set()
        communes_dict = {}   # region -> list of communes
        villages_dict = {}   # (region, commune) -> list of villages

        for _, row in df_clean.iterrows():
            region = str(row['region']).strip()
            commune = str(row['commune']).strip()
            village = str(row['village']).strip()
            if not region or not commune or not village or region == 'nan' or commune == 'nan' or village == 'nan':
                continue
            region_list.add(region)
            communes_dict.setdefault(region, set()).add(commune)
            villages_dict.setdefault((region, commune), set()).add(village)
            # Pour compatibilité ancienne structure
            villages_data.setdefault(region, {}).setdefault(commune, []).append(village)

        # Nettoyage et tri final
        region_list = sorted(region_list)
        for region in communes_dict:
            communes_dict[region] = sorted(list(communes_dict[region]))
        for key in villages_dict:
            villages_dict[key] = sorted(list(villages_dict[key]))
        # Deduplicate villages in villages_data
        for region in villages_data:
            for commune in villages_data[region]:
                villages_data[region][commune] = sorted(list(set(villages_data[region][commune])))

        return villages_data, region_list, communes_dict, villages_dict
    except Exception as e:
        st.error(f"Erreur lors du chargement des villages : {str(e)}")
        return {}, [], {}, {}

def load_villages_data():
    """
    Pour compatibilité ascendante. Retourne la structure ancienne.
    """
    villages_data, _, _, _ = load_villages_structure()
    st.session_state.villages_data = villages_data
    return villages_data

def get_regions_list():
    """Retourne la liste triée des régions"""
    _, region_list, _, _ = load_villages_structure()
    return [""] + region_list

def get_communes_list(region):
    """Retourne la liste triée des communes pour une région donnée"""
    if not region:
        return [""]
    _, _, communes_dict, _ = load_villages_structure()
    return [""] + communes_dict.get(region, [])

def get_villages_list(region, commune):
    """Retourne la liste triée des villages pour une région/commune donnée"""
    if not region or not commune:
        return [""]
    _, _, _, villages_dict = load_villages_structure()
    return [""] + villages_dict.get((region, commune), [])

def get_index_or_default(options_list, value, default=0):
    if not options_list or not value:
        return default
    try:
        if isinstance(options_list, list) and value in options_list:
            return options_list.index(value)
        return default
    except (ValueError, TypeError, AttributeError):
        return default

# Diagnostic et création fichier test restent inchangés
def diagnose_villages_file():
    try:
        excel_file = "Villages.xlsx"
        if not os.path.exists(excel_file):
            return f"❌ Fichier {excel_file} introuvable"
        df = pd.read_excel(excel_file)
        if df.empty:
            return "❌ Fichier vide"
        result = f"✅ Fichier trouvé: {len(df)} lignes\n"
        result += f"📋 Colonnes: {list(df.columns)}\n"
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

def create_sample_villages_file():
    data = {
        'Region': ['Dakar', 'Dakar', 'Dakar', 'Thiès', 'Thiès', 'Thiès'],
        'Commune': ['Dakar', 'Dakar', 'Guédiawaye', 'Thiès', 'Thiès', 'Mbour'],
        'Village': ['Plateau', 'Médina', 'Sam Notaire', 'Randoulène', 'Mbour 1', 'Mbour 2']
    }
    df = pd.DataFrame(data)
    df.to_excel('Villages.xlsx', index=False)
    st.success("Fichier Villages.xlsx de test créé avec succès!")
    return True
