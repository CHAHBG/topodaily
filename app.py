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

# Import des pages - assurez-vous que ces imports ne créent pas de pages Streamlit
from pages.dashboard import show_dashboard
from pages.saisie import show_saisie_page
from pages.suivi import show_suivi_page
from pages.account import show_account_page
from pages.admin import show_admin_users_page, show_admin_data_page

def show_login_page():
    st.title("Connexion Gestion des Levés Topographiques")
    with st.form("login_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")
        if submit:
            user = verify_user(username, password)
            if user:
                st.session_state.app_state["user"] = user
                st.session_state.app_state["username"] = username
                st.session_state.app_state["authenticated"] = True
                st.session_state.app_state["show_login"] = False
                st.session_state.app_state["current_page"] = "Mon Compte"
                st.success(f"Connexion réussie! Bienvenue {username}!")
                st.rerun()
            else:
                st.error("Nom d'utilisateur ou mot de passe incorrect.")
    st.markdown("---")
    st.markdown("Pas encore de compte ? 👇Cliquez sur le bouton Créer un compte👇")
    if st.button("Créer un compte"):
        st.session_state.app_state["show_login"] = False
        st.session_state.app_state["show_registration"] = True
        st.rerun()

def show_registration_page():
    st.title("Création de compte")
    with st.form("registration_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        confirm_password = st.text_input("Confirmer le mot de passe", type="password")
        email = st.text_input("Email")
        phone = st.text_input("Numéro de téléphone")
        submit = st.form_submit_button("S'inscrire")
        if submit:
            if not username or not password:
                st.error("Le nom d'utilisateur et le mot de passe sont obligatoires.")
            elif password != confirm_password:
                st.error("Les mots de passe ne correspondent pas.")
            elif email and not validate_email(email):
                st.error("Format d'email invalide.")
            elif phone and not validate_phone(phone):
                st.error("Format de numéro de téléphone invalide.")
            else:
                success, message = add_user(username, password, email, phone)
                if success:
                    st.success(message)
                    st.session_state.app_state["show_login"] = True
                    st.session_state.app_state["show_registration"] = False
                    st.rerun()
                else:
                    st.error(message)
    if st.button("Retour à la connexion"):
        st.session_state.app_state["show_login"] = True
        st.session_state.app_state["show_registration"] = False
        st.rerun()

def show_navigation_sidebar():
    # Masquer la navigation par défaut de Streamlit
    st.markdown("""
    <style>
    /* Masquer la navigation des pages générée automatiquement par Streamlit */
    section[data-testid="stSidebar"] nav {display: none;}
    /* Masquer le menu principal Streamlit en haut à gauche */
    #MainMenu {visibility: hidden;}
    /* Masquer le header Streamlit */
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
    
    st.sidebar.title("Navigation")
    app_state = st.session_state.app_state
    
    if app_state["authenticated"]:
        user_role = app_state["user"]["role"]
        username = app_state["username"]
        st.sidebar.write(f"Connecté en tant que: **{username}**")
        st.sidebar.write(f"Rôle: **{user_role}**")
        
        pages = ["Dashboard", "Saisie des Levés", "Suivi", "Mon Compte"]
        current_idx = pages.index(app_state["current_page"]) if app_state["current_page"] in pages else 0
        page = st.sidebar.radio("Pages", pages, index=current_idx)
        
        # Menu d'administration pour l'admin
        if user_role == "administrateur":
            st.sidebar.markdown("---")
            admin_page = st.sidebar.radio(
                "Administration",
                ["Aucune", "Gestion des Utilisateurs", "Gestion des Données"],
                index=0
            )
            if admin_page == "Gestion des Utilisateurs":
                page = "Admin Users"
            elif admin_page == "Gestion des Données":
                page = "Admin Data"
        
        st.sidebar.markdown("---")
        if st.sidebar.button("Déconnexion"):
            st.session_state.app_state = {
                "authenticated": False,
                "username": None,
                "user": None,
                "current_page": "Dashboard",
                "show_login": False,
                "show_registration": False
            }
            st.rerun()
    else:
        page = st.sidebar.radio("Pages", ["Dashboard"], index=0)
        st.sidebar.markdown("---")
        st.sidebar.info("Connectez-vous pour accéder à toutes les fonctionnalités.")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Se connecter"):
                st.session_state.app_state["show_login"] = True
                st.session_state.app_state["show_registration"] = False
                st.rerun()
        with col2:
            if st.sidebar.button("S'inscrire"):
                st.session_state.app_state["show_login"] = False
                st.session_state.app_state["show_registration"] = True
                st.rerun()
    
    if app_state["current_page"] != page:
        app_state["current_page"] = page
        st.rerun()
    
    return page

def main():
    # Configuration de la page - IMPORTANT: doit être la première commande Streamlit
    st.set_page_config(
        page_title="Gestion des Levés Topographiques",
        page_icon="📏",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Masquer les éléments indésirables de Streamlit
    hide_streamlit_style = """
    <style>
        #root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}
        .css-1d391kg {display: none}
        .stDeployButton {display: none}
        footer {visibility: hidden;}
        .stDecoration {display: none;}
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        .viewerBadge_container__1QSob {display: none;}
        .css-15zrgzn {display: none}
        .css-eczf16 {display: none}
        .css-jn99sy {display: none}
        .css-14xtw13.e8zbici0 {display: none}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    init_db()
    
    if "app_state" not in st.session_state:
        st.session_state.app_state = {
            "authenticated": False,
            "username": None,
            "user": None,
            "current_page": "Dashboard",
            "show_login": False,
            "show_registration": False
        }
    
    app_state = st.session_state.app_state
    
    if app_state["show_login"]:
        show_login_page()
        return
    
    if app_state["show_registration"]:
        show_registration_page()
        return
    
    # Affichage de la barre de navigation
    current_page = show_navigation_sidebar()
    
    # Affichage de la page correspondante
    if current_page == "Dashboard":
        show_dashboard(get_all_leves, get_filter_options)
    elif current_page == "Saisie des Levés":
        show_saisie_page(add_leve, load_villages_data, get_index_or_default)
    elif current_page == "Suivi":
        show_suivi_page(get_filter_options, get_filtered_leves, delete_user_leve, delete_leve)
    elif current_page == "Mon Compte":
        show_account_page(get_leves_by_topographe, verify_user, change_password)
    elif current_page == "Admin Users":
        show_admin_users_page(get_users, delete_user, add_user, validate_email, validate_phone)
    elif current_page == "Admin Data":
        show_admin_data_page(get_all_leves, get_users)
    else:
        show_dashboard(get_all_leves, get_filter_options)

if __name__ == "__main__":
    main()
