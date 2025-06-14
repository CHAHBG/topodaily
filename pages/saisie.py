import streamlit as st
from datetime import datetime
import os

# ========== OPTIMISATIONS PRINCIPALES ==========

@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_cached_topographes_list(_get_topographes_func):
    """Cache la liste des topographes"""
    if callable(_get_topographes_func):
        try:
            return _get_topographes_func()
        except Exception as e:
            st.warning(f"Erreur lors du chargement des topographes depuis la base: {e}")
            # Fallback vers la liste par défaut
            pass
    
    # Liste par défaut des topographes
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
            "show_login": False,
            "current_page": "Saisie"
        }
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_filtered_options(villages_data, region, commune):
    """Génère les options filtrées pour les selectbox sans rerun"""
    # Vérification de la validité des données
    if not villages_data or not isinstance(villages_data, dict):
        return [""], [""], [""]
    
    try:
        region_options = [""] + sorted(list(villages_data.keys()))
    except (AttributeError, TypeError):
        region_options = [""]
    
    commune_options = [""]
    if region and region in villages_data and isinstance(villages_data[region], dict):
        try:
            commune_options += sorted(list(villages_data[region].keys()))
        except (AttributeError, TypeError):
            pass
    
    village_options = [""]
    if (region and commune and 
        region in villages_data and 
        isinstance(villages_data[region], dict) and
        commune in villages_data[region] and
        isinstance(villages_data[region][commune], list)):
        village_options += villages_data[region][commune]
    
    return region_options, commune_options, village_options

def show_saisie_page(
    add_leve,
    load_villages_data,
    get_index_or_default,
    get_topographes_list,
    can_enter_surveys,
    clear_leves_cache=None
):
    """Page principale de saisie des levés topographiques - Version optimisée"""
    
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

    # ===== CHARGEMENT OPTIMISÉ DES DONNÉES =====
    villages_data = load_and_validate_villages_data(load_villages_data)
    if not villages_data:
        return  # Arrêt si pas de données valides

    # Cache des topographes avec gestion d'erreur
    try:
        topographes_list = get_cached_topographes_list(get_topographes_list)
    except Exception as e:
        st.warning(f"Erreur lors du chargement des topographes: {e}")
        topographes_list = get_cached_topographes_list(None)  # Utilise la liste par défaut

    # Message de succès persistant
    display_success_message()

    # Boutons de navigation
    render_navigation_buttons()

    # Titre du formulaire
    st.subheader("Sélection de la localisation")

    # Formulaire principal optimisé
    render_main_form(
        villages_data, 
        topographes_list, 
        current_username, 
        get_index_or_default, 
        add_leve, 
        clear_leves_cache
    )

def load_and_validate_villages_data(load_villages_data):
    """Charge et valide les données des villages avec diagnostic intégré"""
    
    try:
        # Chargement des données
        villages_data = load_villages_data()
        
        # Vérification robuste du type et du contenu
        if not villages_data:
            st.error("❌ Aucune donnée de village n'a pu être chargée.")
            show_diagnostic_options()
            return None
            
        elif not isinstance(villages_data, dict):
            st.error(f"❌ Format de données invalide. Type reçu: {type(villages_data)}")
            st.info("Les données doivent être un dictionnaire de la forme: {région: {commune: [villages]}}")
            show_diagnostic_options()
            return None
            
        elif len(villages_data) == 0:
            st.warning("⚠️ Le fichier a été chargé mais ne contient aucune donnée valide.")
            show_diagnostic_options()
            return None
            
        else:
            # Afficher les statistiques de chargement
            display_loading_stats(villages_data)
            return villages_data
            
    except Exception as e:
        st.error(f"❌ Erreur critique lors du chargement des données: {e}")
        st.code(f"Type d'erreur: {type(e).__name__}\nMessage: {str(e)}")
        show_recovery_options()
        return None

def display_loading_stats(villages_data):
    """Affiche les statistiques de chargement des données"""
    regions_count = len(villages_data)
    communes_count = sum(len(communes) for communes in villages_data.values())
    villages_count = sum(len(villages) for region in villages_data.values() for villages in region.values())
    
    st.success(f"✅ Données chargées: {regions_count} régions, {communes_count} communes, {villages_count} villages")

def show_diagnostic_options():
    """Affiche les options de diagnostic"""
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Diagnostiquer le problème"):
            diagnosis = diagnose_villages_file()
            st.code(diagnosis)
    
    with col2:
        if st.button("📝 Créer un fichier de test"):
            if create_sample_villages_file():
                st.rerun()

def show_recovery_options():
    """Affiche les options de récupération d'erreur"""
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Vider le cache et réessayer"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if st.button("📝 Créer fichier de test"):
            if create_sample_villages_file():
                st.rerun()

def display_success_message():
    """Affiche le message de succès de manière persistante"""
    if st.session_state.get("show_success_message", False):
        st.success("✅ Levé enregistré avec succès!")
        # Garder le message visible plus longtemps
        if st.button("✖️ Fermer"):
            st.session_state.show_success_message = False
            st.rerun()

def render_navigation_buttons():
    """Affiche les boutons de navigation sans reruns inutiles"""
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🆕 Nouveau levé", key="new_leve_btn", use_container_width=True):
            reset_form_state()
    
    with col2:
        if st.button("📊 Voir les levés", key="view_leves_btn", use_container_width=True):
            st.session_state.app_state["current_page"] = "Suivi"
            st.rerun()
    
    with col3:
        if st.button("🔄 Actualiser données", key="refresh_data_btn", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

def render_main_form(villages_data, topographes_list, current_username, 
                    get_index_or_default, add_leve, clear_leves_cache=None):
    """Formulaire principal optimisé - villages_data est garanti d'être valide"""
    
    # Données en cache pour éviter les recalculs
    cached_data = st.session_state.cached_form_data
    current_region = cached_data.get("region", "")
    current_commune = cached_data.get("commune", "")
    
    # Génération optimisée des options
    try:
        region_options, commune_options, village_options = get_filtered_options(
            villages_data, current_region, current_commune
        )
    except Exception as e:
        st.error(f"Erreur lors de la génération des options: {e}")
        region_options, commune_options, village_options = [""], [""], [""]

    # Sélecteurs avec callbacks optimisés
    render_location_selectors(
        region_options, commune_options, 
        current_region, current_commune, 
        get_index_or_default
    )

    # Vérifier les changements de sélection
    region = st.session_state.get("region_select", "")
    commune = st.session_state.get("commune_select", "")
    
    # Mise à jour optimisée du cache
    update_location_cache(region, commune, current_region, current_commune)

    # Formulaire principal
    with st.form(key=f"leve_form_{st.session_state.form_key}"):
        render_form_fields(
            village_options, topographes_list, current_username,
            get_index_or_default, add_leve, clear_leves_cache
        )

def render_location_selectors(region_options, commune_options, current_region, 
                            current_commune, get_index_or_default):
    """Affiche les sélecteurs de localisation"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            st.selectbox(
                "🌍 Région",
                options=region_options,
                index=get_index_or_default(region_options, current_region),
                key="region_select",
                help="Sélectionnez la région"
            )
        except Exception as e:
            st.error(f"Erreur région: {e}")
            return

    with col2:
        try:
            st.selectbox(
                "🏘️ Commune",
                options=commune_options,
                index=get_index_or_default(commune_options, current_commune),
                key="commune_select",
                help="Sélectionnez la commune"
            )
        except Exception as e:
            st.error(f"Erreur commune: {e}")
            return

def update_location_cache(region, commune, current_region, current_commune):
    """Met à jour le cache de localisation et gère les changements"""
    
    if region != current_region:
        st.session_state.cached_form_data["region"] = region
        st.session_state.cached_form_data["commune"] = ""
        st.session_state.cached_form_data["village"] = ""
        st.rerun()
    
    if commune != current_commune:
        st.session_state.cached_form_data["commune"] = commune
        st.session_state.cached_form_data["village"] = ""
        st.rerun()

def render_form_fields(village_options, topographes_list, current_username,
                      get_index_or_default, add_leve, clear_leves_cache=None):
    """Champs du formulaire avec mise en page améliorée"""
    
    st.subheader("📝 Nouveau levé topographique")

    cached_data = st.session_state.cached_form_data

    # === SECTION 1: INFORMATIONS GÉNÉRALES ===
    st.markdown("### 📅 Informations générales")
    
    col1, col2 = st.columns(2)
    
    with col1:
        date = st.date_input(
            "Date du levé", 
            datetime.now(),
            help="Date à laquelle le levé a été effectué"
        )
    
    with col2:
        # Superviseur (lecture seule)
        st.text_input(
            "Superviseur", 
            value=current_username,
            disabled=True,
            help="Superviseur connecté (automatique)"
        )

    # === SECTION 2: TOPOGRAPHE ===
    st.markdown("### 👷 Topographe")
    
    cached_topographe = cached_data.get("topographe", "")
    topographe_index = get_safe_topographe_index(topographes_list, cached_topographe)
    
    topographe = st.selectbox(
        "Sélectionner le topographe",
        options=topographes_list,
        index=topographe_index,
        key="topographe_select",
        help="Topographe qui a effectué le levé sur le terrain"
    )

    # === SECTION 3: LOCALISATION ===
    st.markdown("### 📍 Localisation précise")
    
    try:
        village = st.selectbox(
            "Village",
            options=village_options,
            index=get_index_or_default(village_options, cached_data.get("village", "")),
            key="village_select",
            help="Village où le levé a été effectué"
        )
    except Exception as e:
        st.error(f"Erreur lors de l'affichage des villages: {e}")
        village = ""

    # === SECTION 4: DÉTAILS TECHNIQUES ===
    st.markdown("### 🔧 Détails techniques")
    
    col1, col2 = st.columns(2)
    
    with col1:
        appareil = render_appareil_selector(cached_data)
    
    with col2:
        type_leve = render_type_selector(cached_data)

    # === SECTION 5: QUANTITÉ ===
    st.markdown("### 📊 Quantité")
    
    quantite = st.number_input(
        "Nombre d'éléments levés", 
        min_value=1, 
        value=max(1, cached_data.get("quantite", 1)), 
        step=1,
        help="Nombre d'éléments (bâtiments, parcelles, etc.) levés"
    )

    # === SECTION 6: VALIDATION ===
    st.markdown("### ✅ Validation")
    
    # Résumé avant soumission
    render_submission_summary(
        date, village, cached_data["region"], cached_data["commune"],
        type_leve, quantite, appareil, topographe, current_username
    )
    
    # Bouton de soumission
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        submit = st.form_submit_button(
            "💾 Enregistrer le levé", 
            use_container_width=True,
            type="primary"
        )

    if submit:
        handle_form_submission(
            date, village, cached_data["region"], cached_data["commune"],
            type_leve, quantite, appareil, topographe, current_username,
            add_leve, clear_leves_cache
        )

def get_safe_topographe_index(topographes_list, cached_topographe):
    """Obtient l'index du topographe de manière sécurisée"""
    topographe_index = 0
    try:
        if cached_topographe and cached_topographe in topographes_list:
            topographe_index = topographes_list.index(cached_topographe)
    except (ValueError, TypeError):
        topographe_index = 0
    return topographe_index

def render_appareil_selector(cached_data):
    """Sélecteur d'appareil avec option personnalisée"""
    appareil_options = ["LT60H", "TRIMBLE", "AUTRE"]
    cached_appareil = cached_data.get("appareil", "")
    appareil_index = 0
    
    if cached_appareil in appareil_options:
        appareil_index = appareil_options.index(cached_appareil)
    elif cached_appareil:
        appareil_options.append(cached_appareil)
        appareil_index = len(appareil_options) - 1

    appareil = st.selectbox(
        "Appareil utilisé", 
        options=appareil_options, 
        index=appareil_index, 
        key="appareil_select",
        help="Type d'appareil topographique utilisé"
    )
    
    if appareil == "AUTRE":
        appareil_autre = st.text_input(
            "Précisez l'appareil", 
            value="" if cached_appareil in appareil_options[:3] else cached_appareil, 
            key="appareil_autre",
            placeholder="Ex: LEICA, SOKKIA..."
        )
        if appareil_autre:
            appareil = appareil_autre

    return appareil

def render_type_selector(cached_data):
    """Sélecteur de type de levé"""
    type_options = ["Bâtiments", "Champs", "Édifice public", "Autre"]
    type_index = cached_data.get("type_leve", 0)
    
    # Validation de l'index
    if type_index >= len(type_options):
        type_index = 0
        
    type_leve = st.selectbox(
        "Type de levé", 
        options=type_options, 
        index=type_index,
        help="Type d'éléments levés sur le terrain"
    )
    
    return type_leve

def render_submission_summary(date, village, region, commune, type_leve, 
                            quantite, appareil, topographe, superviseur):
    """Affiche un résumé avant soumission"""
    
    if all([village, region, commune, topographe]):
        st.info(
            f"**Résumé:** {quantite} {type_leve.lower()} à {village} ({commune}, {region}) "
            f"levé(s) par {topographe} avec {appareil} le {date.strftime('%d/%m/%Y')}"
        )
    else:
        missing_fields = []
        if not village: missing_fields.append("village")
        if not region: missing_fields.append("région")
        if not commune: missing_fields.append("commune")
        if not topographe: missing_fields.append("topographe")
        
        st.warning(f"⚠️ Champs manquants: {', '.join(missing_fields)}")

def handle_form_submission(date, village, region, commune, type_leve, quantite, 
                          appareil, topographe, superviseur, add_leve, clear_leves_cache=None):
    """Gestion optimisée de la soumission avec validation complète"""
    
    # Validation complète
    validation_errors = validate_form_data(
        date, village, region, commune, type_leve, quantite, appareil, topographe
    )
    
    if validation_errors:
        st.error("❌ Erreurs de validation:")
        for error in validation_errors:
            st.error(f"• {error}")
        return

    # Mise à jour du cache
    update_form_cache(region, commune, village, appareil, type_leve, quantite, topographe)

    # Préparation des données
    date_str = date.strftime("%Y-%m-%d")
    
    # Soumission avec gestion d'erreur complète
    try:
        with st.spinner("Enregistrement en cours..."):
            success = add_leve(
                date_str, village, region, commune, type_leve, 
                quantite, appareil, topographe, superviseur
            )
            
        if success:
            handle_successful_submission(clear_leves_cache)
        else:
            st.error("❌ Erreur lors de l'enregistrement du levé.")
            st.info("Veuillez vérifier les données et réessayer.")
            
    except Exception as e:
        st.error(f"❌ Erreur lors de la soumission: {e}")
        st.info("Si le problème persiste, contactez l'administrateur.")

def validate_form_data(date, village, region, commune, type_leve, quantite, appareil, topographe):
    """Validation complète des données du formulaire"""
    errors = []
    
    # Champs obligatoires
    if not village: errors.append("Le village doit être sélectionné")
    if not region: errors.append("La région doit être sélectionnée")
    if not commune: errors.append("La commune doit être sélectionnée")
    if not topographe: errors.append("Le topographe doit être sélectionné")
    if not appareil: errors.append("L'appareil doit être spécifié")
    if not type_leve: errors.append("Le type de levé doit être sélectionné")
    
    # Validation de la quantité
    if quantite <= 0: errors.append("La quantité doit être supérieure à 0")
    
    # Validation de la date
    if date > datetime.now().date():
        errors.append("La date ne peut pas être dans le futur")
    
    return errors

def update_form_cache(region, commune, village, appareil, type_leve, quantite, topographe):
    """Met à jour le cache du formulaire"""
    type_options = ["Bâtiments", "Champs", "Édifice public", "Autre"]
    
    try:
        type_index = type_options.index(type_leve) if type_leve in type_options else 0
    except (ValueError, AttributeError):
        type_index = 0
        
    st.session_state.cached_form_data.update({
        "region": region, 
        "commune": commune, 
        "village": village,
        "appareil": appareil, 
        "type_leve": type_index,
        "quantite": quantite, 
        "topographe": topographe
    })

def handle_successful_submission(clear_leves_cache=None):
    """Gestion après soumission réussie avec feedback utilisateur"""
    
    # Invalider les caches pertinents
    try:
        st.cache_data.clear()
    except Exception as e:
        st.warning(f"Avertissement lors du nettoyage du cache: {e}")
    
    # Cache externe
    if clear_leves_cache and callable(clear_leves_cache):
        try:
            clear_leves_cache()
        except Exception as e:
            st.warning(f"Avertissement lors du nettoyage du cache externe: {e}")
    
    # Marquer le succès
    st.session_state.show_success_message = True
    st.session_state.form_submitted = True
    
    # Réinitialiser le formulaire
    reset_form_state()

def reset_form_state():
    """Réinitialise l'état du formulaire de manière propre"""
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

# ========== FONCTIONS UTILITAIRES DE DIAGNOSTIC ==========

def diagnose_villages_file():
    """Fonction de diagnostic pour vérifier le fichier Villages.xlsx"""
    try:
        import pandas as pd
        excel_file = "Villages.xlsx"
        
        if not os.path.exists(excel_file):
            return f"❌ Fichier {excel_file} introuvable dans {os.getcwd()}"
        
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
        return f"❌ Erreur lors du diagnostic: {e}"

def create_sample_villages_file():
    """Crée un fichier Villages.xlsx de test"""
    try:
        import pandas as pd
        
        data = {
            'Region': ['Dakar', 'Dakar', 'Dakar', 'Thiès', 'Thiès', 'Thiès'],
            'Commune': ['Dakar', 'Dakar', 'Guédiawaye', 'Thiès', 'Thiès', 'Mbour'],
            'Village': ['Plateau', 'Médina', 'Sam Notaire', 'Randoulène', 'Mbour 1', 'Mbour 2']
        }
        
        df = pd.DataFrame(data)
        df.to_excel('Villages.xlsx', index=False)
        st.success("📝 Fichier Villages.xlsx de test créé avec succès!")
        return True
        
    except Exception as e:
        st.error(f"Erreur lors de la création du fichier test: {e}")
        return False

# ========== FONCTION DE DEBUG ==========

def debug_session_state():
    """Fonction de debug pour examiner l'état de session"""
    if st.sidebar.button("🔍 Debug Session State"):
        st.sidebar.write("**Session State:**")
        for key, value in st.session_state.items():
            if isinstance(value, dict):
                st.sidebar.write(f"- {key}: {len(value)} items")
            else:
                st.sidebar.write(f"- {key}: {type(value).__name__}")

# ========== FONCTIONS D'EXPORT POUR COMPATIBILITÉ ==========

def get_current_form_data():
    """Retourne les données actuelles du formulaire"""
    return st.session_state.get("cached_form_data", {})

def set_form_data(data):
    """Définit les données du formulaire"""
    if isinstance(data, dict):
        st.session_state.cached_form_data.update(data)
