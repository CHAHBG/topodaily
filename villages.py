import pandas as pd
import streamlit as st

def load_villages_data():
    try:
        excel_file = "Villages.xlsx"
        df = pd.read_excel(excel_file)
        df.columns = [col.lower() for col in df.columns]
        required_columns = ['village', 'commune', 'region']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Le fichier Excel ne contient pas la colonne requise: {col}")
                st.session_state.villages_data = {}
                return False
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
        for region in villages_data:
            for commune in villages_data[region]:
                villages_data[region][commune].sort()
        st.session_state.villages_data = villages_data
        return True
    except Exception as e:
        st.session_state.villages_data = {}
        st.error(f"Erreur lors du chargement des villages: {str(e)}")
        return False

def get_index_or_default(options_list, value, default=0):
    try:
        return options_list.index(value)
    except ValueError:
        return default