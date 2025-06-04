import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def show_suivi_page(get_filter_options, get_filtered_leves, delete_user_leve, delete_leve):
    st.title("Suivi des Levés Topographiques")

    if not st.session_state.app_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour accéder au suivi.")
        st.session_state.app_state["show_login"] = True
        st.rerun()
        return

    filter_options = get_filter_options()

    with st.expander("Filtres", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Date de début", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Date de fin", datetime.now())

        col1, col2, col3 = st.columns(3)
        with col1:
            village_options = ["Tous"] + filter_options["villages"]
            village = st.selectbox("Village", options=village_options)
            village = None if village == "Tous" else village

            region_options = ["Toutes"] + filter_options["regions"]
            region = st.selectbox("Région", options=region_options)
            region = None if region == "Toutes" else region

        with col2:
            commune_options = ["Toutes"] + filter_options["communes"]
            commune = st.selectbox("Commune", options=commune_options)
            commune = None if commune == "Toutes" else commune

            type_options = ["Tous"] + filter_options["types"]
            type_leve = st.selectbox("Type de levé", options=type_options)
            type_leve = None if type_leve == "Tous" else type_leve

        with col3:
            appareil_options = ["Tous"] + filter_options["appareils"]
            appareil = st.selectbox("Appareil", options=appareil_options)
            appareil = None if appareil == "Tous" else appareil

            if st.session_state.app_state["user"]["role"] == "administrateur":
                topo_options = ["Tous"] + filter_options["topographes"]
                topographe = st.selectbox("Topographe", options=topo_options)
                topographe = None if topographe == "Tous" else topographe
            else:
                topographe = st.session_state.app_state["username"]
                st.write(f"Topographe: **{topographe}**")

    leves_df = get_filtered_leves(start_date, end_date, village, region, commune, type_leve, appareil, topographe)

    if not leves_df.empty:
        leves_df = leves_df.rename(columns={
            'id': 'ID',
            'date': 'Date',
            'village': 'Village',
            'region': 'Région',
            'commune': 'Commune',
            'type': 'Type',
            'quantite': 'Quantité',
            'appareil': 'Appareil',
            'topographe': 'Topographe',
            'created_at': 'Date de création'
        })

        leves_df['Date'] = pd.to_datetime(leves_df['Date']).dt.strftime('%d/%m/%Y')

        st.dataframe(
            leves_df[['ID', 'Date', 'Village', 'Région', 'Commune', 'Type', 'Quantité', 'Appareil', 'Topographe']],
            use_container_width=True,
            height=400
        )

        st.subheader("Statistiques")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre Total de Levés", len(leves_df))
        with col2:
            st.metric("Quantité Totale", f"{leves_df['Quantité'].sum():,.0f}")
        with col3:
            st.metric("Moyenne par Levé", f"{leves_df['Quantité'].mean():.2f}")

        if st.download_button(
                label="Télécharger les données en CSV",
                data=leves_df.to_csv(index=False).encode('utf-8'),
                file_name=f"leves_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv'
        ):
            st.success("Export réussi!")

        if st.session_state.app_state["user"]["role"] != "administrateur":
            st.subheader("Gestion de mes levés")
            with st.form("delete_own_leve_form"):
                leve_id = st.number_input("ID du levé à supprimer", min_value=1, step=1)
                delete_submit = st.form_submit_button("Supprimer mon levé")
                if delete_submit:
                    success, message = delete_user_leve(leve_id, st.session_state.app_state["username"])
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

        if st.session_state.app_state["user"]["role"] == "administrateur":
            st.subheader("Gestion des Levés (Admin)")
            with st.form("delete_leve_form"):
                leve_id = st.number_input("ID du levé à supprimer", min_value=1, step=1)
                delete_submit = st.form_submit_button("Supprimer le levé")
                if delete_submit:
                    if delete_leve(leve_id):
                        st.success(f"Levé {leve_id} supprimé avec succès!")
                        import time
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erreur lors de la suppression du levé. Vérifiez l'ID.")
    else:
        st.info("Aucun levé ne correspond aux critères de recherche sélectionnés.")