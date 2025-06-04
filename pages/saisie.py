import streamlit as st
from datetime import datetime

def show_saisie_page(
    add_leve,
    load_villages_data,
    get_index_or_default
):
    st.title("Saisie des Levés Topographiques")

    if "form_key" not in st.session_state:
        st.session_state.form_key = 0

    if "cached_form_data" not in st.session_state:
        st.session_state.cached_form_data = {
            "region": "", "commune": "", "village": "", "appareil": "",
            "type_leve": 0, "quantite": 1
        }

    if "form_submitted" not in st.session_state:
        st.session_state.form_submitted = False

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

    st.info(f"Connecté en tant que: {st.session_state.app_state['username']}")

    if st.session_state.get("form_submitted", False):
        st.success("Levé enregistré avec succès!")
        st.session_state.form_submitted = False

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Nouveau levé", key="new_leve_btn"):
            st.session_state.form_key += 1
            st.session_state.cached_form_data = {
                "region": "", "commune": "", "village": "", "appareil": "",
                "type_leve": 0, "quantite": 1
            }
            st.rerun()
    with col2:
        if st.button("Voir mes levés", key="view_leves_btn"):
            st.session_state.app_state["current_page"] = "Suivi"
            st.rerun()

    st.subheader("Sélection de la localisation")

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

    region_options = [""] + sorted(list(st.session_state.villages_data.keys()))
    region = st.selectbox(
        "Région",
        options=region_options,
        index=get_index_or_default(region_options, st.session_state.cached_form_data.get("region", "")),
        key="region_select",
        on_change=on_region_change
    )

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

    with st.form(key=f"leve_form_{st.session_state.form_key}"):
        st.subheader("Nouveau levé topographique")

        date = st.date_input("Date du levé", datetime.now())
        topographe = st.session_state.app_state["username"]
        st.write(f"Topographe: **{topographe}**")

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

        quantite = st.number_input("Quantité", min_value=1, value=st.session_state.cached_form_data.get("quantite", 1), step=1)
        submit = st.form_submit_button("Enregistrer le levé")

        if submit:
            st.session_state.cached_form_data = {
                "region": current_region, "commune": current_commune, "village": village,
                "appareil": appareil, "type_leve": type_options.index(type_leve),
                "quantite": quantite
            }

            if not village:
                st.error("Veuillez sélectionner un village.")
            elif not current_region:
                st.error("Veuillez sélectionner une région.")
            elif not current_commune:
                st.error("Veuillez sélectionner une commune.")
            else:
                date_str = date.strftime("%Y-%m-%d")
                success = add_leve(date_str, village, current_region, current_commune, type_leve, quantite, appareil, topographe)
                if success:
                    st.cache_data.clear()
                    st.session_state.form_submitted = True
                    st.session_state.cached_form_data = {
                        "region": "", "commune": "", "village": "", "appareil": "",
                        "type_leve": 0, "quantite": 1
                    }
                    st.session_state.form_key += 1
                    st.rerun()
                else:
                    st.error("Erreur lors de l'enregistrement du levé.")