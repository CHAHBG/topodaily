import streamlit as st
from datetime import datetime
import os

# OPTIMISATIONS PRINCIPALES

def initialize_session_state():
    """Initialise l'état de session si nécessaire"""
    defaults = {
        "form_key": 0,
        "cached_form_data": {
            "region": "",
            "commune": "",
            "village": "",
            "appareil": "",
            "type_leve": 0,
            "quantite": 1,
            "topographe": ""
        },
        "form_submitted": False,
        "show_success_message": False,
        "app_state": {
            "authenticated": False,
            "username": "",
            "user": {},
            "show_login": False,
            "current_page": "Saisie"
        }
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def show_saisie_page(
    add_leve,
    load_villages_data,
    get_index_or_default,
    get_topographes_list,
    can_enter_surveys,
    clear_leves_cache=None
):
    st.title("Saisie des Levés Topographiques")
    initialize_session_state()

    # Authentification
    if not st.session_state.app_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour accéder à cette page.")
        st.session_state.app_state["show_login"] = True
        st.rerun()
        return

    user = st.session_state.app_state.get("user", {})
    user_role = user.get("role", "")
    current_username = st.session_state.app_state.get("username", "")

    if not can_enter_surveys(user_role):
        st.error("Accès non autorisé. Seuls les superviseurs et administrateurs peuvent saisir des levés.")
        return

    # CHARGEMENT DONNÉES VILLAGES
    villages_data = load_villages_data()
    if not villages_data or not isinstance(villages_data, dict) or not villages_data:
        st.error("Impossible de charger les données de villages. Veuillez vérifier le fichier source.")
        show_diagnostic_options()
        return

    # CHARGEMENT LISTE TOPOGRAPHES (optimisé)
    try:
        topographes_list = get_topographes_list() if callable(get_topographes_list) else []
        if not topographes_list or not isinstance(topographes_list, list):
            raise ValueError
    except Exception:
        topographes_list = [
            "", "Mouhamed Lamine THIOUB", "Mamadou GUEYE", "Djibril BODIAN", "Arona FALL", "Moussa DIOL",
            "Mbaye GAYE", "Ousseynou THIAM", "Ousmane BA", "Djibril Gueye", "Yakhaya Toure", "Seydina Aliou Sow",
            "Ndeye Yandé Diop", "Mohamed Ahmed Sylla", "Souleymane Niang", "Cheikh Diawara", "Mignane Gning",
            "Serigne Saliou Sow", "Gora Dieng"
        ]

    # Message succès persistant
    if st.session_state.get("show_success_message", False):
        st.success("✅ Levé enregistré avec succès!")
        if st.button("✖️ Fermer"):
            st.session_state.show_success_message = False
            st.rerun()

    # Navigation rapide
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🆕 Nouveau levé", key="new_leve_btn"):
            reset_form_state()
    with col2:
        if st.button("📊 Voir les levés", key="view_leves_btn"):
            st.session_state.app_state["current_page"] = "Suivi"
            st.rerun()
    with col3:
        if st.button("🔄 Actualiser données", key="refresh_data_btn"):
            st.cache_data.clear()
            st.rerun()

    # Données cachées pour formulaire
    cached_data = st.session_state.cached_form_data
    region_options = [""] + sorted(list(villages_data.keys()))
    region = st.selectbox(
        "Région", region_options,
        index=get_index_or_default(region_options, cached_data.get("region", "")), key="region_select"
    )

    commune_options = [""]
    if region and region in villages_data:
        commune_options += sorted(list(villages_data[region].keys()))
    commune = st.selectbox(
        "Commune", commune_options,
        index=get_index_or_default(commune_options, cached_data.get("commune", "")), key="commune_select"
    )

    village_options = [""]
    if region and commune and region in villages_data and commune in villages_data[region]:
        village_options += sorted(villages_data[region][commune])
    village = st.selectbox(
        "Village", village_options,
        index=get_index_or_default(village_options, cached_data.get("village", "")), key="village_select"
    )

    # Saisie du reste du formulaire
    date = st.date_input("Date du levé", datetime.now(), key="date_input")
    appareil_options = ["", "LT60H", "TRIMBLE", "AUTRE"]
    appareil = st.selectbox(
        "Appareil utilisé", appareil_options,
        index=get_index_or_default(appareil_options, cached_data.get("appareil", "")), key="appareil_select"
    )
    if appareil == "AUTRE":
        appareil = st.text_input("Précisez l'appareil", value=cached_data.get("appareil", ""), key="appareil_autre")

    type_options = ["Bâtiments", "Champs", "Édifice public", "Autre"]
    type_leve = st.selectbox(
        "Type de levé", type_options,
        index=cached_data.get("type_leve", 0), key="type_select"
    )

    quantite = st.number_input("Nombre d'éléments levés", min_value=1, value=cached_data.get("quantite", 1), key="quantite_input")

    topographe = st.selectbox(
        "Topographe responsable", topographes_list,
        index=get_index_or_default(topographes_list, cached_data.get("topographe", current_username)), key="topographe_select"
    )

    # Résumé avant soumission
    if all([region, commune, village, topographe]):
        st.info(
            f"**Résumé:** {quantite} {type_leve.lower()} à {village} ({commune}, {region}) "
            f"levé(s) par {topographe} avec {appareil} le {date.strftime('%d/%m/%Y')}"
        )

    with st.form(key=f"leve_form_{st.session_state.form_key}"):
        submit = st.form_submit_button("💾 Enregistrer le levé")
        if submit:
            errors = validate_form_data(date, village, region, commune, type_leve, quantite, appareil, topographe)
            if errors:
                for error in errors:
                    st.error(f"• {error}")
            else:
                # Mise à jour cache du formulaire
                st.session_state.cached_form_data.update({
                    "region": region,
                    "commune": commune,
                    "village": village,
                    "appareil": appareil,
                    "type_leve": type_options.index(type_leve) if type_leve in type_options else 0,
                    "quantite": quantite,
                    "topographe": topographe
                })
                with st.spinner("Enregistrement en cours..."):
                    success = add_leve(
                        date.strftime("%Y-%m-%d"), village, region, commune,
                        type_leve, quantite, appareil, topographe, current_username
                    )
                if success:
                    if clear_leves_cache and callable(clear_leves_cache):
                        clear_leves_cache()
                    st.cache_data.clear()
                    st.session_state.show_success_message = True
                    reset_form_state()
                else:
                    st.error("Erreur lors de l'enregistrement du levé. Veuillez réessayer.")

    # Option de reset manuel
    if st.button("Réinitialiser le formulaire"):
        reset_form_state()

def validate_form_data(date, village, region, commune, type_leve, quantite, appareil, topographe):
    """Validation complète des données du formulaire"""
    errors = []
    if not village: errors.append("Le village doit être sélectionné")
    if not region: errors.append("La région doit être sélectionnée")
    if not commune: errors.append("La commune doit être sélectionnée")
    if not topographe: errors.append("Le topographe doit être sélectionné")
    if not appareil: errors.append("L'appareil doit être spécifié")
    if not type_leve: errors.append("Le type de levé doit être sélectionné")
    if quantite <= 0: errors.append("La quantité doit être supérieure à 0")
    if date > datetime.now().date():
        errors.append("La date ne peut pas être dans le futur")
    return errors

def reset_form_state():
    """Réinitialise l'état du formulaire"""
    st.session_state.cached_form_data = {
        "region": "",
        "commune": "",
        "village": "",
        "appareil": "",
        "type_leve": 0,
        "quantite": 1,
        "topographe": ""
    }
    st.session_state.form_key += 1
    st.rerun()

def show_diagnostic_options():
    """Affiche les options de diagnostic pour le fichier villages"""
    if st.button("🔍 Diagnostiquer le fichier Villages.xlsx"):
        diagnosis = diagnose_villages_file()
        st.code(diagnosis)

def diagnose_villages_file():
    """Diagnostic du fichier Villages.xlsx"""
    try:
        excel_file = "Villages.xlsx"
        if not os.path.exists(excel_file):
            return f"❌ Fichier {excel_file} introuvable dans {os.getcwd()}"
        df = __import__("pandas").read_excel(excel_file)
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
        return f"❌ Erreur lors du diagnostic: {e}"

# Fonctions pour compatibilité éventuelle avec d'autres modules
def get_current_form_data():
    return st.session_state.get("cached_form_data", {})

def set_form_data(data):
    if isinstance(data, dict):
        st.session_state.cached_form_data.update(data)
