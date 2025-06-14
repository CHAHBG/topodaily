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

def apply_custom_styles():
    """Applique les styles CSS personnalisés"""
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #e67e22 0%, #2c3e50 100%);
        padding: 2rem 1rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        font-size: 1.2rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    .form-container {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.18);
        margin: 1rem 0;
    }
    
    .form-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 4px solid #e67e22;
    }
    
    .form-section h3 {
        color: #e67e22;
        margin-top: 0;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .nav-buttons {
        display: flex;
        gap: 1rem;
        margin: 2rem 0;
        flex-wrap: wrap;
    }
    
    .nav-button {
        flex: 1;
        min-width: 200px;
    }
    
    .success-alert {
        background: linear-gradient(135deg, #00b894 0%, #00a085 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: none;
        box-shadow: 0 4px 15px rgba(0,184,148,0.3);
    }
    
    .error-alert {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: none;
        box-shadow: 0 4px 15px rgba(231,76,60,0.3);
    }
    
    .warning-alert {
        background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: none;
        box-shadow: 0 4px 15px rgba(243,156,18,0.3);
    }
    
    .info-alert {
        background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: none;
        box-shadow: 0 4px 15px rgba(52,152,219,0.3);
    }
    
    .summary-card {
        background: linear-gradient(135deg, #e67e22 0%, #2c3e50 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(230,126,34,0.3);
    }
    
    .summary-card h4 {
        margin: 0 0 1rem 0;
        font-size: 1.3rem;
        font-weight: 600;
    }
    
    .summary-card p {
        margin: 0;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    
    .stSelectbox > div > div {
        border-radius: 10px;
        border: 2px solid #e1e8ed;
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #e67e22;
        box-shadow: 0 0 0 3px rgba(230,126,34,0.1);
    }
    
    .stNumberInput > div > div {
        border-radius: 10px;
        border: 2px solid #e1e8ed;
        transition: all 0.3s ease;
    }
    
    .stNumberInput > div > div:focus-within {
        border-color: #e67e22;
        box-shadow: 0 0 0 3px rgba(230,126,34,0.1);
    }
    
    .stDateInput > div > div {
        border-radius: 10px;
        border: 2px solid #e1e8ed;
        transition: all 0.3s ease;
    }
    
    .stDateInput > div > div:focus-within {
        border-color: #e67e22;
        box-shadow: 0 0 0 3px rgba(230,126,34,0.1);
    }
    
    .stTextInput > div > div {
        border-radius: 10px;
        border: 2px solid #e1e8ed;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div:focus-within {
        border-color: #e67e22;
        box-shadow: 0 0 0 3px rgba(230,126,34,0.1);
    }
    
    .stButton > button {
        border-radius: 10px;
        border: none;
        padding: 0.7rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #e67e22 0%, #2c3e50 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(230,126,34,0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(230,126,34,0.4);
    }
    
    .diagnostic-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 15px;
        border: 2px dashed #dee2e6;
        margin: 2rem 0;
        text-align: center;
    }
    
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin: 2rem 0;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 15px;
    }
    
    .step {
        flex: 1;
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        margin: 0 0.5rem;
        background: white;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .step.active {
        background: linear-gradient(135deg, #e67e22 0%, #34495e 100%);
        color: white;
        transform: scale(1.05);
    }
    
    .step h4 {
        margin: 0 0 0.5rem 0;
        font-size: 1rem;
        font-weight: 600;
        color: #2c3e50;
    }
    
    .step p {
        margin: 0;
        font-size: 0.9rem;
        opacity: 0.8;
        color: #34495e;
    }
    
    .step.active h4,
    .step.active p {
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

def show_saisie_page(
    add_leve,
    load_villages_data,
    get_index_or_default,
    get_topographes_list,
    can_enter_surveys,
    clear_leves_cache=None
):
    # Application des styles
    apply_custom_styles()
    
    # En-tête principal
    st.markdown("""
    <div class="main-header">
        <h1>📍 Saisie des Levés Topographiques</h1>
        <p>Système de gestion des relevés topographiques</p>
    </div>
    """, unsafe_allow_html=True)
    
    initialize_session_state()

    # Authentification
    if not st.session_state.app_state.get("authenticated", False):
        st.markdown("""
        <div class="warning-alert">
            <strong>🔐 Authentification requise</strong><br>
            Vous devez être connecté pour accéder à cette page.
        </div>
        """, unsafe_allow_html=True)
        st.session_state.app_state["show_login"] = True
        st.rerun()
        return

    user = st.session_state.app_state.get("user", {})
    user_role = user.get("role", "")
    current_username = st.session_state.app_state.get("username", "")

    if not can_enter_surveys(user_role):
        st.markdown("""
        <div class="error-alert">
            <strong>❌ Accès non autorisé</strong><br>
            Seuls les superviseurs et administrateurs peuvent saisir des levés.
        </div>
        """, unsafe_allow_html=True)
        return

    # CHARGEMENT DONNÉES VILLAGES
    villages_data = load_villages_data()
    if not villages_data or not isinstance(villages_data, dict) or not villages_data:
        st.markdown("""
        <div class="error-alert">
            <strong>❌ Erreur de chargement</strong><br>
            Impossible de charger les données de villages. Veuillez vérifier le fichier source.
        </div>
        """, unsafe_allow_html=True)
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
        st.markdown("""
        <div class="success-alert">
            <strong>✅ Succès!</strong><br>
            Levé enregistré avec succès dans la base de données.
        </div>
        """, unsafe_allow_html=True)
        if st.button("✖️ Fermer le message", key="close_success"):
            st.session_state.show_success_message = False
            st.rerun()

    # Navigation rapide avec style
    st.markdown('<div class="nav-buttons">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🆕 Nouveau levé", key="new_leve_btn", help="Réinitialiser le formulaire"):
            reset_form_state()
    
    with col2:
        if st.button("📊 Voir les levés", key="view_leves_btn", help="Accéder au tableau de bord"):
            st.session_state.app_state["current_page"] = "Suivi"
            st.rerun()
    
    with col3:
        if st.button("🔄 Actualiser", key="refresh_data_btn", help="Recharger les données"):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Indicateur d'étapes
    st.markdown("""
    <div class="step-indicator">
        <div class="step active">
            <h4>1. Localisation</h4>
            <p>Région, Commune, Village</p>
        </div>
        <div class="step">
            <h4>2. Détails</h4>
            <p>Date, Appareil, Type</p>
        </div>
        <div class="step">
            <h4>3. Responsable</h4>
            <p>Topographe, Quantité</p>
        </div>
        <div class="step">
            <h4>4. Validation</h4>
            <p>Vérification, Enregistrement</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Conteneur principal du formulaire
    st.markdown('<div class="form-container">', unsafe_allow_html=True)

    # Section 1: Localisation
    st.markdown("""
    <div class="form-section">
        <h3>🌍 Localisation du levé</h3>
    </div>
    """, unsafe_allow_html=True)

    # Données cachées pour formulaire
    cached_data = st.session_state.cached_form_data
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        region_options = [""] + sorted(list(villages_data.keys()))
        region = st.selectbox(
            "🏞️ Région", region_options,
            index=get_index_or_default(region_options, cached_data.get("region", "")), 
            key="region_select",
            help="Sélectionnez la région administrative"
        )

    with col2:
        commune_options = [""]
        if region and region in villages_data:
            commune_options += sorted(list(villages_data[region].keys()))
        commune = st.selectbox(
            "🏘️ Commune", commune_options,
            index=get_index_or_default(commune_options, cached_data.get("commune", "")), 
            key="commune_select",
            help="Sélectionnez la commune"
        )

    with col3:
        village_options = [""]
        if region and commune and region in villages_data and commune in villages_data[region]:
            village_options += sorted(villages_data[region][commune])
        village = st.selectbox(
            "🏠 Village", village_options,
            index=get_index_or_default(village_options, cached_data.get("village", "")), 
            key="village_select",
            help="Sélectionnez le village"
        )

    # Section 2: Détails du levé
    st.markdown("""
    <div class="form-section">
        <h3>📋 Détails du levé</h3>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    
    with col1:
        date = st.date_input(
            "📅 Date du levé", 
            datetime.now(), 
            key="date_input",
            help="Date de réalisation du levé topographique"
        )
        
        type_options = ["Bâtiments", "Champs", "Édifice public", "Autre"]
        type_leve = st.selectbox(
            "🏗️ Type de levé", type_options,
            index=cached_data.get("type_leve", 0), 
            key="type_select",
            help="Type d'éléments à lever"
        )

    with col2:
        appareil_options = ["", "LT60H", "TRIMBLE", "AUTRE"]
        appareil = st.selectbox(
            "🔧 Appareil utilisé", appareil_options,
            index=get_index_or_default(appareil_options, cached_data.get("appareil", "")), 
            key="appareil_select",
            help="Équipement topographique utilisé"
        )
        
        if appareil == "AUTRE":
            appareil = st.text_input(
                "Précisez l'appareil", 
                value=cached_data.get("appareil", ""), 
                key="appareil_autre",
                help="Nom de l'appareil utilisé"
            )

        quantite = st.number_input(
            "🔢 Nombre d'éléments", 
            min_value=1, 
            value=cached_data.get("quantite", 1), 
            key="quantite_input",
            help="Nombre d'éléments levés"
        )

    # Section 3: Responsable
    st.markdown("""
    <div class="form-section">
        <h3>👤 Responsable du levé</h3>
    </div>
    """, unsafe_allow_html=True)

    topographe = st.selectbox(
        "🎯 Topographe responsable", topographes_list,
        index=get_index_or_default(topographes_list, cached_data.get("topographe", current_username)), 
        key="topographe_select",
        help="Personne responsable du levé topographique"
    )

    # Section 4: Résumé et validation
    if all([region, commune, village, topographe]):
        st.markdown(f"""
        <div class="summary-card">
            <h4>📝 Résumé du levé</h4>
            <p><strong>{quantite}</strong> {type_leve.lower()} à <strong>{village}</strong> ({commune}, {region})<br>
            Levé(s) par <strong>{topographe}</strong> avec <strong>{appareil}</strong><br>
            Date: <strong>{date.strftime('%d/%m/%Y')}</strong></p>
        </div>
        """, unsafe_allow_html=True)

    # Formulaire de soumission
    with st.form(key=f"leve_form_{st.session_state.form_key}"):
        st.markdown("### 🔍 Validation finale")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info("Vérifiez toutes les informations avant de valider l'enregistrement.")
        
        with col2:
            submit = st.form_submit_button(
                "💾 Enregistrer le levé",
                help="Sauvegarder le levé dans la base de données"
            )
        
        if submit:
            errors = validate_form_data(date, village, region, commune, type_leve, quantite, appareil, topographe)
            if errors:
                for error in errors:
                    st.markdown(f"""
                    <div class="error-alert">
                        <strong>❌ Erreur de validation</strong><br>
                        {error}
                    </div>
                    """, unsafe_allow_html=True)
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
                
                with st.spinner("🔄 Enregistrement en cours..."):
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
                    st.markdown("""
                    <div class="error-alert">
                        <strong>❌ Erreur d'enregistrement</strong><br>
                        Une erreur s'est produite lors de l'enregistrement. Veuillez réessayer.
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # Fermeture form-container

    # Actions secondaires
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Réinitialiser le formulaire", help="Effacer tous les champs"):
            reset_form_state()
    
    with col2:
        if st.button("🔍 Diagnostiquer les données", help="Vérifier le fichier Villages.xlsx"):
            show_diagnostic_options()

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
    st.markdown("""
    <div class="diagnostic-section">
        <h3>🔍 Diagnostic du fichier Villages.xlsx</h3>
        <p>Vérifiez l'intégrité et la structure du fichier de données</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔍 Lancer le diagnostic", help="Analyser le fichier Villages.xlsx"):
        diagnosis = diagnose_villages_file()
        st.code(diagnosis, language="text")

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
