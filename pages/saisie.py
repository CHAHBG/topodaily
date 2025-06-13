import streamlit as st
from datetime import datetime

# ========== OPTIMISATIONS PRINCIPALES ==========

@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_cached_villages_data(load_villages_data_func):
    """Cache les données des villages pour éviter les rechargements"""
    return load_villages_data_func()

@st.cache_data(ttl=60)  # Cache pendant 1 minute
def get_cached_user_leves(get_user_leves_func, username):
    """Cache les levés de l'utilisateur"""
    return get_user_leves_func(username)

@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_cached_topographes_list(get_topographes_func):
    """Cache la liste des topographes"""
    if callable(get_topographes_func):
        return get_topographes_func()
    else:
        return [
            "",  # Option vide
            "Mouhamed Lamine THIOUB",
            "Mamadou GUEYE", 
            "Djibril BODIAN",
            "Arona FALL",
            "Moussa DIOL",
            "Mbaye GAYE",
            "Ousseynou THIAM",
            "Ousmane BA",
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

def initialize_session_state():
    """Initialise tous les états de session une seule fois"""
    defaults = {
        "form_key": 0,
        "cached_form_data": {
            "region": "", "commune": "", "village": "", "appareil": "",
            "type_leve": 0, "quantite": 1, "topographe": ""
        },
        "form_submitted": False,
        "edit_mode": False,
        "edit_leve_id": None,
        "show_edit_selection": False,
        "app_state": {
            "authenticated": False,
            "username": "",
            "show_login": False,
            "current_page": "Saisie"
        }
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_filtered_options(villages_data, region, commune):
    """Génère les options filtrées pour les selectbox sans rerun"""
    region_options = [""] + sorted(list(villages_data.keys()))
    
    commune_options = [""]
    if region and region in villages_data:
        commune_options += sorted(list(villages_data[region].keys()))
    
    village_options = [""]
    if region and commune and region in villages_data and commune in villages_data[region]:
        village_options += villages_data[region][commune]
    
    return region_options, commune_options, village_options

def show_saisie_page(
    add_leve,
    load_villages_data,
    get_index_or_default,
    get_topographes_list,
    can_enter_surveys,
    get_leve_by_id,
    update_leve,
    can_edit_leve,
    get_user_leves,
    clear_leves_cache=None  # Paramètre optionnel pour la compatibilité
):
    st.title("Saisie des Levés Topographiques")

    # Initialisation optimisée
    initialize_session_state()

    # Vérification d'authentification
    if not st.session_state.app_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour accéder à cette page.")
        st.session_state.app_state["show_login"] = True
        st.rerun()
        return

    user_role = st.session_state.app_state.get("user", {}).get("role", "")
    current_username = st.session_state.app_state["username"]
    
    # Contrôle d'accès
    if user_role not in ["superviseur", "admin"]:
        st.error("Accès non autorisé. Seuls les superviseurs et administrateurs peuvent saisir des levées.")
        return

    st.info(f"Connecté en tant que: {current_username} ({user_role})")

    # Chargement optimisé des données avec cache
    try:
        villages_data = get_cached_villages_data(load_villages_data)
        if not villages_data:
            st.error("Impossible de charger les données des villages.")
            return
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
        return

    # Cache des topographes
    topographes_list = get_cached_topographes_list(get_topographes_list)

    # Messages de succès (éviter les reruns inutiles)
    if st.session_state.get("form_submitted", False):
        if st.session_state.get("edit_mode", False):
            st.success("Levé modifié avec succès!")
        else:
            st.success("Levé enregistré avec succès!")
        st.session_state.form_submitted = False

    # Boutons de navigation
    render_navigation_buttons()

    # Interface de modification
    if st.session_state.get("show_edit_selection", False):
        render_edit_selection(get_user_leves, current_username, user_role, 
                            get_leve_by_id, can_edit_leve)

    # Titre du formulaire
    if st.session_state.get("edit_mode", False):
        st.subheader(f"Modification du levé #{st.session_state.edit_leve_id}")
    else:
        st.subheader("Sélection de la localisation")

    # Formulaire principal optimisé
    render_main_form(villages_data, topographes_list, current_username, 
                    get_index_or_default, add_leve, update_leve, clear_leves_cache)

    # Bouton annulation en mode édition
    if st.session_state.get("edit_mode", False):
        if st.button("Annuler la modification", key="cancel_edit_btn"):
            reset_form_state()

def render_navigation_buttons():
    """Affiche les boutons de navigation sans reruns inutiles"""
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("Nouveau levé", key="new_leve_btn"):
            reset_form_state()
    
    with col2:
        if st.button("Voir les levés", key="view_leves_btn"):
            st.session_state.app_state["current_page"] = "Suivi"
            st.rerun()

    with col3:
        if st.button("Modifier un levé", key="edit_mode_btn"):
            st.session_state.show_edit_selection = not st.session_state.get("show_edit_selection", False)
            st.rerun()

def render_edit_selection(get_user_leves, current_username, user_role, 
                         get_leve_by_id, can_edit_leve):
    """Interface de sélection pour modification - optimisée"""
    st.subheader("Sélectionner un levé à modifier")
    
    try:
        # Utilisation du cache pour les levés utilisateur
        user_leves = get_cached_user_leves(get_user_leves, current_username)
        
        # Filtrage robuste et optimisé
        user_leves_valides = [
            leve for leve in user_leves 
            if isinstance(leve, dict) and 
               'id' in leve and 
               leve['id'] is not None and 
               str(leve['id']).strip()
        ]
        
        if not user_leves_valides:
            st.info("Aucun levé valide à modifier.")
            return

        # Création optimisée des options
        options = []
        id_map = {}
        
        for leve in user_leves_valides:
            try:
                leve_id = leve.get('id', 'N/A')
                village = leve.get('village', 'N/A')
                date = leve.get('date', 'N/A')
                option = f"#{leve_id} - {village} ({date})"
                options.append(option)
                id_map[option] = leve['id']
            except Exception as e:
                st.warning(f"Erreur lors de la création de l'option: {e}")
                continue
        
        if not options:
            st.error("Aucune option valide disponible.")
            return
        
        selected = st.selectbox("Choisissez un levé", options, key="edit_leve_selectbox")
        
        if selected in id_map:
            render_edit_actions(selected, id_map, get_leve_by_id, 
                              can_edit_leve, current_username, user_role)
                    
    except Exception as e:
        st.error(f"Erreur lors du chargement des levés: {e}")

def render_edit_actions(selected, id_map, get_leve_by_id, can_edit_leve, 
                       current_username, user_role):
    """Affiche les actions pour l'édition"""
    leve_id = id_map[selected]
    
    col_edit1, col_edit2 = st.columns(2)
    with col_edit1:
        if st.button("Charger pour modification", key="load_edit_btn"):
            leve_data = get_leve_by_id(leve_id)
            if leve_data:
                if can_edit_leve(current_username, user_role, leve_data.get("superviseur", "")):
                    load_edit_data(leve_id, leve_data)
                else:
                    st.error("Vous ne pouvez modifier que vos propres levés.")
            else:
                st.error("Levé non trouvé.")
    
    with col_edit2:
        if st.button("Annuler", key="cancel_edit_selection_btn"):
            st.session_state.show_edit_selection = False
            st.rerun()

def load_edit_data(leve_id, leve_data):
    """Charge les données pour l'édition sans rerun complet"""
    st.session_state.edit_mode = True
    st.session_state.edit_leve_id = leve_id
    st.session_state.show_edit_selection = False
    st.session_state.cached_form_data = {
        "region": leve_data.get("region", ""),
        "commune": leve_data.get("commune", ""),
        "village": leve_data.get("village", ""),
        "appareil": leve_data.get("appareil", ""),
        "type_leve": leve_data.get("type_leve", 0),
        "quantite": leve_data.get("quantite", 1),
        "topographe": leve_data.get("topographe", ""),
        "date": leve_data.get("date", "")
    }
    st.session_state.form_key += 1
    st.rerun()

def render_main_form(villages_data, topographes_list, current_username, 
                    get_index_or_default, add_leve, update_leve, clear_leves_cache=None):
    """Formulaire principal optimisé"""
    
    # Données en cache pour éviter les recalculs
    cached_data = st.session_state.cached_form_data
    current_region = cached_data.get("region", "")
    current_commune = cached_data.get("commune", "")
    
    # Génération optimisée des options
    region_options, commune_options, village_options = get_filtered_options(
        villages_data, current_region, current_commune
    )

    # Sélecteurs avec callbacks optimisés
    region = st.selectbox(
        "Région",
        options=region_options,
        index=get_index_or_default(region_options, current_region),
        key="region_select"
    )

    commune = st.selectbox(
        "Commune",
        options=commune_options,
        index=get_index_or_default(commune_options, current_commune),
        key="commune_select"
    )

    # Mise à jour optimisée du cache
    if region != current_region:
        st.session_state.cached_form_data["region"] = region
        st.session_state.cached_form_data["commune"] = ""
        st.session_state.cached_form_data["village"] = ""
        st.rerun()
    
    if commune != current_commune:
        st.session_state.cached_form_data["commune"] = commune
        st.session_state.cached_form_data["village"] = ""
        st.rerun()

    # Formulaire principal
    with st.form(key=f"leve_form_{st.session_state.form_key}"):
        render_form_fields(village_options, topographes_list, current_username,
                          get_index_or_default, add_leve, update_leve, clear_leves_cache)

def render_form_fields(village_options, topographes_list, current_username,
                      get_index_or_default, add_leve, update_leve, clear_leves_cache=None):
    """Champs du formulaire"""
    form_title = "Modification du levé topographique" if st.session_state.get("edit_mode", False) else "Nouveau levé topographique"
    st.subheader(form_title)

    cached_data = st.session_state.cached_form_data

    # Date du levé
    default_date = datetime.now()
    if st.session_state.get("edit_mode", False) and cached_data.get("date"):
        try:
            default_date = datetime.strptime(cached_data["date"], "%Y-%m-%d")
        except:
            default_date = datetime.now()
    
    date = st.date_input("Date du levé", default_date)
    
    # Topographe
    cached_topographe = cached_data.get("topographe", "")
    topographe_index = 0
    if cached_topographe in topographes_list:
        topographe_index = topographes_list.index(cached_topographe)
    
    topographe = st.selectbox(
        "Topographe",
        options=topographes_list,
        index=topographe_index,
        key="topographe_select",
        help="Sélectionnez le topographe qui a effectué le levé"
    )
    
    # Superviseur
    superviseur = current_username
    st.write(f"Superviseur: **{superviseur}**")

    # Village
    village = st.selectbox(
        "Village",
        options=village_options,
        index=get_index_or_default(village_options, cached_data.get("village", "")),
        key="village_select"
    )

    # Appareil et type
    col1, col2 = st.columns(2)
    with col1:
        appareil_options = ["LT60H", "TRIMBLE", "AUTRE"]
        cached_appareil = cached_data.get("appareil", "")
        appareil_index = 0
        
        if cached_appareil in appareil_options:
            appareil_index = appareil_options.index(cached_appareil)
        elif cached_appareil:
            appareil_options.append(cached_appareil)
            appareil_index = len(appareil_options) - 1

        appareil = st.selectbox("Appareil utilisé", options=appareil_options, 
                              index=appareil_index, key="appareil_select")
        
        if appareil == "AUTRE":
            appareil_autre = st.text_input("Précisez l'appareil", 
                                         value="" if cached_appareil in appareil_options[:3] else cached_appareil, 
                                         key="appareil_autre")
            if appareil_autre:
                appareil = appareil_autre

    with col2:
        type_options = ["Batîments", "Champs", "Edifice publique", "Autre"]
        type_index = cached_data.get("type_leve", 0)
        type_leve = st.selectbox("Type de levé", options=type_options, index=type_index)

    # Quantité
    quantite = st.number_input("Quantité", min_value=1, 
                              value=cached_data.get("quantite", 1), step=1)
    
    # Soumission du formulaire
    submit_text = "Modifier le levé" if st.session_state.get("edit_mode", False) else "Enregistrer le levé"
    submit = st.form_submit_button(submit_text)

    if submit:
        handle_form_submission(date, village, cached_data["region"], 
                             cached_data["commune"], type_leve, quantite, 
                             appareil, topographe, superviseur, type_options,
                             add_leve, update_leve, clear_leves_cache)

def handle_form_submission(date, village, region, commune, type_leve, quantite, 
                          appareil, topographe, superviseur, type_options,
                          add_leve, update_leve, clear_leves_cache=None):
    """Gestion optimisée de la soumission"""
    
    # Validation
    if not all([village, region, commune, topographe]):
        missing = []
        if not village: missing.append("village")
        if not region: missing.append("région")
        if not commune: missing.append("commune")
        if not topographe: missing.append("topographe")
        st.error(f"Veuillez sélectionner: {', '.join(missing)}")
        return

    # Mise à jour du cache
    st.session_state.cached_form_data.update({
        "region": region, "commune": commune, "village": village,
        "appareil": appareil, "type_leve": type_options.index(type_leve),
        "quantite": quantite, "topographe": topographe
    })

    date_str = date.strftime("%Y-%m-%d")
    
    # Soumission
    if st.session_state.get("edit_mode", False):
        success = update_leve(
            st.session_state.edit_leve_id,
            date_str, village, region, commune, 
            type_leve, quantite, appareil, topographe, superviseur
        )
        if success:
            handle_successful_submission(True, clear_leves_cache)
        else:
            st.error("Erreur lors de la modification du levé.")
    else:
        success = add_leve(date_str, village, region, commune, type_leve, 
                          quantite, appareil, topographe, superviseur)
        if success:
            handle_successful_submission(False, clear_leves_cache)
        else:
            st.error("Erreur lors de l'enregistrement du levé.")

def handle_successful_submission(is_edit=False, clear_leves_cache=None):
    """Gestion après soumission réussie"""
    # Invalider les caches pertinents
    get_cached_user_leves.clear()
    st.cache_data.clear()
    
    # Si une fonction externe de nettoyage de cache est fournie
    if clear_leves_cache and callable(clear_leves_cache):
        try:
            clear_leves_cache()
        except Exception as e:
            st.warning(f"Erreur lors du nettoyage du cache externe: {e}")
    
    # Réinitialiser l'état
    st.session_state.form_submitted = True
    if is_edit:
        st.session_state.edit_mode = False
        st.session_state.edit_leve_id = None
    
    reset_form_state()

def reset_form_state():
    """Réinitialise l'état du formulaire"""
    st.session_state.cached_form_data = {
        "region": "", "commune": "", "village": "", "appareil": "",
        "type_leve": 0, "quantite": 1, "topographe": ""
    }
    st.session_state.form_key += 1
    st.rerun()
