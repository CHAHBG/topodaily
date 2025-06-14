import streamlit as st
from db import init_db
from auth import (
    verify_user, get_user_role, add_user, delete_user, change_password, get_users,
    validate_email, validate_phone
)
from leves import (
    add_leve, get_all_leves, get_filtered_leves, get_leves_by_topographe,
    delete_leve, delete_user_leve, get_filter_options
)
from villages import load_villages_data, get_index_or_default

from pages.dashboard import show_dashboard
from pages.saisie import show_saisie_page
from pages.suivi import show_suivi_page
from pages.account import show_account_page
from pages.admin import show_admin_users_page, show_admin_data_page

# ================================
# CACHE OPTIMISÉ
# ================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_villages_data():
    return load_villages_data()

@st.cache_data(ttl=1800, show_spinner=False)
def get_cached_topographes_list():
    return [
        "",
        "Mouhamed Lamine THIOUB", "Mamadou GUEYE", "Djibril BODIAN", "Arona FALL", "Moussa DIOL",
        "Mbaye GAYE", "Ousseynou THIAM", "Ousmane BA",
        "Djibril Gueye", "Yakhaya Toure", "Seydina Aliou Sow", "Ndeye Yandé Diop",
        "Mohamed Ahmed Sylla", "Souleymane Niang", "Cheikh Diawara", "Mignane Gning",
        "Serigne Saliou Sow", "Gora Dieng"
    ]

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_user_leves(username):
    return get_leves_by_topographe(username)

@st.cache_data(ttl=600, show_spinner=False)
def get_cached_all_leves():
    return get_all_leves()

@st.cache_data(ttl=600, show_spinner=False)
def get_cached_filter_options():
    return get_filter_options()

def clear_leves_cache():
    get_cached_user_leves.clear()
    get_cached_all_leves.clear()
    get_cached_filter_options.clear()

# ================================
# STYLES CSS - NOUVELLE PALETTE
# ================================

def apply_custom_styles():
    st.markdown("""
    <style>
    /* Variables CSS pour la nouvelle palette */
    :root {
        --primary-orange: #e67e22;
        --primary-blue: #2c3e50;
        --secondary-blue: #34495e;
        --light-orange: #f39c12;
        --gradient-primary: linear-gradient(135deg, #e67e22 0%, #2c3e50 100%);
        --gradient-secondary: linear-gradient(135deg, #f39c12 0%, #34495e 100%);
    }
    
    /* Styles pour les boutons principaux */
    .stButton > button {
        background: var(--gradient-primary) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 24px !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 8px rgba(230, 126, 34, 0.3) !important;
    }
    
    .stButton > button:hover {
        background: var(--gradient-secondary) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(230, 126, 34, 0.4) !important;
    }
    
    /* Bouton de connexion centré et agrandi */
    .login-button {
        display: flex !important;
        justify-content: center !important;
        margin: 20px 0 !important;
    }
    
    .login-button .stButton > button {
        width: 200px !important;
        height: 50px !important;
        font-size: 18px !important;
        background: var(--gradient-primary) !important;
    }
    
    /* Styles pour la sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%) !important;
    }
    
    /* Styles pour les formulaires */
    .stTextInput > div > div > input {
        border: 2px solid var(--primary-orange) !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--light-orange) !important;
        box-shadow: 0 0 0 2px rgba(230, 126, 34, 0.2) !important;
    }
    
    /* Styles pour les titres */
    h1 {
        color: var(--primary-blue) !important;
        text-align: center !important;
        margin-bottom: 30px !important;
        font-weight: bold !important;
    }
    
    h2, h3 {
        color: var(--secondary-blue) !important;
    }
    
    /* Styles pour les métriques */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(230, 126, 34, 0.1) 0%, rgba(44, 62, 80, 0.1) 100%) !important;
        border: 1px solid var(--primary-orange) !important;
        border-radius: 10px !important;
        padding: 15px !important;
    }
    
    /* Styles pour les success/error messages */
    .stAlert > div {
        border-radius: 8px !important;
    }
    
    /* Style pour le radio button de navigation */
    .stRadio > div {
        background: rgba(230, 126, 34, 0.1) !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }
    
    /* Cacher les éléments Streamlit par défaut */
    #root > div:nth-child(1) > div > div > div > div > section > div {
        padding-top: 0rem;
    }
    .css-1d391kg {display: none}
    .stDeployButton {display: none}
    footer {visibility: hidden;}
    .stDecoration {display: none;}
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none;}
    section[data-testid="stSidebar"] nav {display: none;}
    </style>
    """, unsafe_allow_html=True)

# ================================
# UTILITAIRES
# ================================

def can_enter_surveys(user_role):
    return user_role in ["superviseur", "administrateur", "admin"]

def initialize_session_state():
    if "app_state" not in st.session_state:
        st.session_state.app_state = {
            "authenticated": False,
            "username": None,
            "user": None,
            "current_page": "Dashboard",
            "show_login": False,
            "show_registration": False
        }
    if "villages_data_loaded" not in st.session_state:
        villages_data = get_cached_villages_data()
        if villages_data is not None:
            st.session_state.villages_data = villages_data
            st.session_state.villages_data_loaded = True
        else:
            st.error("Impossible de charger les données des villages.")
            st.session_state.villages_data_loaded = False

def show_login_page():
    st.title("🔐 Connexion Gestion des Levés Topographiques")
    
    # Conteneur centré pour le formulaire
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("👤 Nom d'utilisateur")
            password = st.text_input("🔒 Mot de passe", type="password")
            
            # Bouton de connexion centré et agrandi
            st.markdown('<div class="login-button">', unsafe_allow_html=True)
            submit = st.form_submit_button("🚀 Se connecter")
            st.markdown('</div>', unsafe_allow_html=True)
            
        if submit:
            user = verify_user(username, password)
            if user:
                st.session_state.app_state["user"] = user
                st.session_state.app_state["username"] = username
                st.session_state.app_state["authenticated"] = True
                st.session_state.app_state["show_login"] = False
                st.session_state.app_state["current_page"] = "Mon Compte"
                st.success(f"✅ Connexion réussie! Bienvenue {username}!")
                st.rerun()
            else:
                st.error("❌ Nom d'utilisateur ou mot de passe incorrect.")
        
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #34495e; margin: 20px 0;'>
            <p>Pas encore de compte ? Contactez l'administrateur pour créer votre compte.</p>
        </div>
        """, unsafe_allow_html=True)

def show_registration_page():
    st.title("📝 Création de compte")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("registration_form"):
            username = st.text_input("👤 Nom d'utilisateur")
            password = st.text_input("🔒 Mot de passe", type="password")
            confirm_password = st.text_input("🔒 Confirmer le mot de passe", type="password")
            email = st.text_input("📧 Email")
            phone = st.text_input("📱 Numéro de téléphone")
            
            submit = st.form_submit_button("✨ S'inscrire")
            
        if submit:
            if not username or not password:
                st.error("❌ Le nom d'utilisateur et le mot de passe sont obligatoires.")
            elif password != confirm_password:
                st.error("❌ Les mots de passe ne correspondent pas.")
            elif email and not validate_email(email):
                st.error("❌ Format d'email invalide.")
            elif phone and not validate_phone(phone):
                st.error("❌ Format de numéro de téléphone invalide.")
            else:
                success, message = add_user(username, password, email, phone)
                if success:
                    st.success(f"✅ {message}")
                    st.session_state.app_state["show_login"] = True
                    st.session_state.app_state["show_registration"] = False
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        if st.button("🔙 Retour à la connexion"):
            st.session_state.app_state["show_login"] = True
            st.session_state.app_state["show_registration"] = False
            st.rerun()

def show_navigation_sidebar():
    st.sidebar.title("🧭 Navigation")
    app_state = st.session_state.app_state
    
    if app_state["authenticated"]:
        user_role = app_state["user"]["role"]
        username = app_state["username"]
        
        # Informations utilisateur avec style
        st.sidebar.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba(230, 126, 34, 0.1) 0%, rgba(44, 62, 80, 0.1) 100%); 
                    padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #e67e22;'>
            <p style='margin: 0; color: #2c3e50;'><strong>👤 Utilisateur:</strong> {username}</p>
            <p style='margin: 0; color: #34495e;'><strong>🎭 Rôle:</strong> {user_role}</p>
        </div>
        """, unsafe_allow_html=True)
        
        pages = ["📊 Dashboard", "📝 Saisie des Levés", "📋 Suivi", "👤 Mon Compte"]
        current_idx = 0
        for i, page in enumerate(pages):
            if app_state["current_page"] in page:
                current_idx = i
                break
        
        page = st.sidebar.radio("📑 Pages", pages, index=current_idx, key="main_nav")
        
        if user_role == "administrateur":
            st.sidebar.markdown("---")
            admin_page = st.sidebar.radio(
                "⚙️ Administration",
                ["Aucune", "👥 Gestion des Utilisateurs", "📊 Gestion des Données"],
                index=0,
                key="admin_nav"
            )
            if admin_page == "👥 Gestion des Utilisateurs":
                page = "Admin Users"
            elif admin_page == "📊 Gestion des Données":
                page = "Admin Data"
        
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Déconnexion", key="logout_btn"):
            get_cached_user_leves.clear()
            st.session_state.clear()
            initialize_session_state()
            st.rerun()
    else:
        page = st.sidebar.radio("📑 Pages", ["📊 Dashboard"], index=0, key="guest_nav")
        st.sidebar.markdown("---")
        
        st.sidebar.markdown("""
        <div style='background: linear-gradient(135deg, rgba(230, 126, 34, 0.1) 0%, rgba(44, 62, 80, 0.1) 100%); 
                    padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #e67e22;'>
            <p style='margin: 0; color: #2c3e50; text-align: center;'>
                🔐 Connectez-vous pour accéder à toutes les fonctionnalités
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Bouton de connexion centré et agrandi dans la sidebar
        st.sidebar.markdown('<div class="login-button">', unsafe_allow_html=True)
        if st.sidebar.button("🔑 Se connecter", key="login_btn"):
            st.session_state.app_state["show_login"] = True
            st.session_state.app_state["show_registration"] = False
            st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # Nettoyage des emojis pour la logique interne
    page_mapping = {
        "📊 Dashboard": "Dashboard",
        "📝 Saisie des Levés": "Saisie des Levés",
        "📋 Suivi": "Suivi",
        "👤 Mon Compte": "Mon Compte"
    }
    
    clean_page = page_mapping.get(page, page)
    
    # Changement de page seulement si nécessaire
    if app_state["current_page"] != clean_page:
        app_state["current_page"] = clean_page
        st.rerun()
    
    return clean_page

def main():
    st.set_page_config(
        page_title="Gestion des Levés Topographiques",
        page_icon="📏",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Application des styles personnalisés
    apply_custom_styles()
    
    init_db()
    initialize_session_state()
    
    app_state = st.session_state.app_state
    
    if app_state["show_login"]:
        show_login_page()
        return
    
    if app_state["show_registration"]:
        show_registration_page()
        return
    
    current_page = show_navigation_sidebar()
    
    # OPTI: passage de fonctions avec cache pour éviter les recalculs
    if current_page == "Dashboard":
        show_dashboard(get_cached_all_leves, get_cached_filter_options)
    elif current_page == "Saisie des Levés":
        show_saisie_page(
            add_leve,
            get_cached_villages_data,
            get_index_or_default,
            get_cached_topographes_list,
            can_enter_surveys,
            clear_leves_cache=clear_leves_cache
        )
    elif current_page == "Suivi":
        show_suivi_page(get_cached_filter_options, get_filtered_leves, delete_user_leve, delete_leve)
    elif current_page == "Mon Compte":
        show_account_page(get_cached_user_leves, verify_user, change_password)
    elif current_page == "Admin Users":
        show_admin_users_page(get_users, delete_user, add_user, validate_email, validate_phone)
    elif current_page == "Admin Data":
        show_admin_data_page(get_cached_all_leves, get_users)
    else:
        show_dashboard(get_cached_all_leves, get_cached_filter_options)

if __name__ == "__main__":
    main()
