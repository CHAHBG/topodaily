import streamlit as st
from datetime import datetime

def show_saisie_page(
    add_leve,
    load_villages_data,
    get_index_or_default,
    get_topographes_list,
    can_enter_surveys,
    get_leve_by_id,
    update_leve,
    can_edit_leve,
    get_user_leves  # Ajoute ce paramètre !
):
    st.title("Saisie des Levés Topographiques")

    # Initialisations d'état
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0

    if "cached_form_data" not in st.session_state:
        st.session_state.cached_form_data = {
            "region": "", "commune": "", "village": "", "appareil": "",
            "type_leve": 0, "quantite": 1, "topographe": ""
        }

    if "form_submitted" not in st.session_state:
        st.session_state.form_submitted = False

    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False
        
    if "edit_leve_id" not in st.session_state:
        st.session_state.edit_leve_id = None

    if "show_edit_selection" not in st.session_state:
        st.session_state.show_edit_selection = False

    if "app_state" not in st.session_state:
        st.session_state.app_state = {
            "authenticated": False,
            "username": "",
            "show_login": False,
            "current_page": "Saisie"
        }

    if "villages_data" not in st.session_state:
        success = load_villages_data()
        if not success:
            st.error("Impossible de charger les données des villages.")
            return

    if not st.session_state.app_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour accéder à cette page.")
        st.session_state.app_state["show_login"] = True
        st.rerun()
        return

    user_role = st.session_state.app_state.get("user", {}).get("role", "")
    current_username = st.session_state.app_state["username"]
    
    # Seuls les superviseurs et administrateurs peuvent saisir des levées
    if user_role not in ["superviseur", "admin"]:
        st.error("Accès non autorisé. Seuls les superviseurs et administrateurs peuvent saisir des levées.")
        return

    st.info(f"Connecté en tant que: {current_username} ({user_role})")

    # Messages de succès
    if st.session_state.get("form_submitted", False):
        if st.session_state.get("edit_mode", False):
            st.success("Levé modifié avec succès!")
        else:
            st.success("Levé enregistré avec succès!")
        st.session_state.form_submitted = False

    # Boutons de navigation
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Nouveau levé", key="new_leve_btn"):
            st.session_state.form_key += 1
            st.session_state.edit_mode = False
            st.session_state.edit_leve_id = None
            st.session_state.cached_form_data = {
                "region": "", "commune": "", "village": "", "appareil": "",
                "type_leve": 0, "quantite": 1, "topographe": ""
            }
            st.rerun()
    
    with col2:
        if st.button("Voir les levés", key="view_leves_btn"):
            st.session_state.app_state["current_page"] = "Suivi"
            st.rerun()

    # Mode édition - Sélection du levé à modifier
    if user_role in ["superviseur", "admin"]:
        with col3:
            if st.button("Modifier un levé", key="edit_mode_btn"):
                st.session_state.show_edit_selection = not st.session_state.get("show_edit_selection", False)
                st.rerun()

    # Interface de sélection pour modification
    if st.session_state.get("show_edit_selection", False):
        st.subheader("Sélectionner un levé à modifier")
        
        # Affiche les levés de l'utilisateur sous forme de selectbox
        user_leves = get_user_leves(current_username)
        if not user_leves:
            st.info("Aucun levé à modifier.")
        else:
            options = [f"#{lev['id']} - {lev.get('village', 'N/A')} ({lev.get('date', 'N/A')})" for lev in user_leves]
            id_map = {opt: lev['id'] for opt, lev in zip(options, user_leves)}
            selected = st.selectbox("Choisissez un levé", options, key="edit_leve_selectbox")
            leve_id = id_map[selected]

            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                if st.button("Charger pour modification", key="load_edit_btn"):
                    leve_data = get_leve_by_id(leve_id)
                    if leve_data:
                        if can_edit_leve(current_username, user_role, leve_data.get("superviseur", "")):
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
                        else:
                            st.error("Vous ne pouvez modifier que vos propres levés.")
                    else:
                        st.error("Levé non trouvé.")
            
            with col_edit2:
                if st.button("Annuler", key="cancel_edit_selection_btn"):
                    st.session_state.show_edit_selection = False
                    st.rerun()

    # Titre du formulaire selon le mode
    if st.session_state.get("edit_mode", False):
        st.subheader(f"Modification du levé #{st.session_state.edit_leve_id}")
    else:
        st.subheader("Sélection de la localisation")

    # Gestion des changements de région/commune
    if st.session_state.get("_should_rerun", False):
        st.session_state._should_rerun = False
        st.rerun()

    def on_region_change():
        selected_region = st.session_state.region_select
        if selected_region != st.session_state.cached_form_data.get("region", ""):
            st.session_state.cached_form_data["region"] = selected_region
            st.session_state.cached_form_data["commune"] = ""
            st.session_state.cached_form_data["village"] = ""
            st.session_state._should_rerun = True

    def on_commune_change():
        selected_commune = st.session_state.commune_select
        if selected_commune != st.session_state.cached_form_data.get("commune", ""):
            st.session_state.cached_form_data["commune"] = selected_commune
            st.session_state.cached_form_data["village"] = ""
            st.session_state._should_rerun = True

    # Sélection région
    region_options = [""] + sorted(list(st.session_state.villages_data.keys()))
    region = st.selectbox(
        "Région",
        options=region_options,
        index=get_index_or_default(region_options, st.session_state.cached_form_data.get("region", "")),
        key="region_select",
        on_change=on_region_change
    )

    # Sélection commune
    commune_options = [""]
    current_region = st.session_state.cached_form_data.get("region", "")
    if current_region:
        commune_options += sorted(list(st.session_state.villages_data.get(current_region, {}).keys()))

    commune = st.selectbox(
        "Commune",
        options=commune_options,
        index=get_index_or_default(commune_options, st.session_state.cached_form_data.get("commune", "")),
        key="commune_select",
        on_change=on_commune_change
    )

    # Formulaire principal
    with st.form(key=f"leve_form_{st.session_state.form_key}"):
        form_title = "Modification du levé topographique" if st.session_state.get("edit_mode", False) else "Nouveau levé topographique"
        st.subheader(form_title)

        # Date du levé
        default_date = datetime.now()
        if st.session_state.get("edit_mode", False) and st.session_state.cached_form_data.get("date"):
            try:
                default_date = datetime.strptime(st.session_state.cached_form_data["date"], "%Y-%m-%d")
            except:
                default_date = datetime.now()
        
        date = st.date_input("Date du levé", default_date)
        
        # Liste complète des topographes
        topographes_list = get_topographes_list() if callable(get_topographes_list) else [
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
        
        cached_topographe = st.session_state.cached_form_data.get("topographe", "")
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
        
        # Affichage du superviseur (utilisateur connecté)
        superviseur = current_username
        st.write(f"Superviseur: **{superviseur}**")

        # Sélection du village
        village_options = [""]
        current_commune = st.session_state.cached_form_data.get("commune", "")
        if current_region and current_commune:
            village_options += st.session_state.villages_data[current_region][current_commune]

        village = st.selectbox(
            "Village",
            options=village_options,
            index=get_index_or_default(village_options, st.session_state.cached_form_data.get("village", "")),
            key="village_select"
        )

        # Appareil et type de levé
        col1, col2 = st.columns(2)
        with col1:
            appareil_options = ["LT60H", "TRIMBLE", "AUTRE"]
            cached_appareil = st.session_state.cached_form_data.get("appareil", "")
            if cached_appareil in appareil_options:
                appareil_index = appareil_options.index(cached_appareil)
            elif cached_appareil:
                appareil_options.append(cached_appareil)
                appareil_index = len(appareil_options) - 1
            else:
                appareil_index = 0

            appareil = st.selectbox("Appareil utilisé", options=appareil_options, index=appareil_index, key="appareil_select")
            if appareil == "AUTRE":
                appareil_autre = st.text_input("Précisez l'appareil", value="" if cached_appareil in appareil_options else cached_appareil, key="appareil_autre")
                if appareil_autre:
                    appareil = appareil_autre

        with col2:
            type_options = ["Batîments", "Champs", "Edifice publique", "Autre"]
            type_index = st.session_state.cached_form_data.get("type_leve", 0)
            type_leve = st.selectbox("Type de levé", options=type_options, index=type_index)

        # Quantité
        quantite = st.number_input("Quantité", min_value=1, value=st.session_state.cached_form_data.get("quantite", 1), step=1)
        
        # Bouton de soumission
        submit_text = "Modifier le levé" if st.session_state.get("edit_mode", False) else "Enregistrer le levé"
        submit = st.form_submit_button(submit_text)

        if submit:
            # Mise à jour des données en cache
            st.session_state.cached_form_data = {
                "region": current_region, "commune": current_commune, "village": village,
                "appareil": appareil, "type_leve": type_options.index(type_leve),
                "quantite": quantite, "topographe": topographe
            }

            # Validation
            if not village:
                st.error("Veuillez sélectionner un village.")
            elif not current_region:
                st.error("Veuillez sélectionner une région.")
            elif not current_commune:
                st.error("Veuillez sélectionner une commune.")
            elif not topographe:
                st.error("Veuillez sélectionner un topographe.")
            else:
                date_str = date.strftime("%Y-%m-%d")
                
                # Mode modification ou création
                if st.session_state.get("edit_mode", False):
                    success = update_leve(
                        st.session_state.edit_leve_id,
                        date_str, village, current_region, current_commune, 
                        type_leve, quantite, appareil, topographe, superviseur
                    )
                    if success:
                        st.cache_data.clear()
                        st.session_state.form_submitted = True
                        st.session_state.edit_mode = False
                        st.session_state.edit_leve_id = None
                        st.session_state.cached_form_data = {
                            "region": "", "commune": "", "village": "", "appareil": "",
                            "type_leve": 0, "quantite": 1, "topographe": ""
                        }
                        st.session_state.form_key += 1
                        st.rerun()
                    else:
                        st.error("Erreur lors de la modification du levé.")
                else:
                    success = add_leve(date_str, village, current_region, current_commune, type_leve, quantite, appareil, topographe, superviseur)
                    if success:
                        st.cache_data.clear()
                        st.session_state.form_submitted = True
                        st.session_state.cached_form_data = {
                            "region": "", "commune": "", "village": "", "appareil": "",
                            "type_leve": 0, "quantite": 1, "topographe": ""
                        }
                        st.session_state.form_key += 1
                        st.rerun()
                    else:
                        st.error("Erreur lors de l'enregistrement du levé.")

    # Annuler la modification
    if st.session_state.get("edit_mode", False):
        if st.button("Annuler la modification", key="cancel_edit_btn"):
            st.session_state.edit_mode = False
            st.session_state.edit_leve_id = None
            st.session_state.cached_form_data = {
                "region": "", "commune": "", "village": "", "appareil": "",
                "type_leve": 0, "quantite": 1, "topographe": ""
            }
            st.session_state.form_key += 1
            st.rerun()
