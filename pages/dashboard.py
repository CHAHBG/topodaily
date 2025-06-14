import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

def show_dashboard(get_all_leves, get_filter_options):
    st.title("Dashboard des Levés Topographiques")

    leves_df = get_all_leves()
    if leves_df is None or leves_df.empty:
        st.info("Aucun levé n'a encore été enregistré.")
        if st.button("Saisir un nouveau levé"):
            if st.session_state.get("authenticated", False):
                st.session_state.current_page = "Saisie des Levés"
                st.rerun()
            else:
                st.session_state.app_state["show_login"] = True
                st.session_state.app_state["show_registration"] = False
                st.warning("Veuillez vous connecter pour saisir des levés.")
                st.rerun()
        return

    # Normalisation de la colonne date
    if 'date' in leves_df.columns:
        leves_df['date'] = pd.to_datetime(leves_df['date'], errors='coerce')

    filter_options = get_filter_options() if callable(get_filter_options) else {}

    # Filtres dynamiques
    with st.expander("Filtres", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Date de début", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Date de fin", datetime.now())
        mask_date = pd.Series([True] * len(leves_df))
        if 'date' in leves_df.columns:
            mask_date = (leves_df['date'] >= pd.Timestamp(start_date)) & (leves_df['date'] <= pd.Timestamp(end_date))
        leves_filtered = leves_df[mask_date].copy()

        # Sélecteurs de filtres (sécurité sur les clés)
        region_options = ["Toutes"] + filter_options.get("regions", [])
        region_filter = st.selectbox("Région", options=region_options, index=0)
        if region_filter != "Toutes" and not leves_filtered.empty and 'region' in leves_filtered.columns:
            leves_filtered = leves_filtered[leves_filtered['region'] == region_filter]

        commune_options = ["Toutes"] + filter_options.get("communes", [])
        commune_filter = st.selectbox("Commune", options=commune_options, index=0)
        if commune_filter != "Toutes" and not leves_filtered.empty and 'commune' in leves_filtered.columns:
            leves_filtered = leves_filtered[leves_filtered['commune'] == commune_filter]

        type_options = ["Tous"] + filter_options.get("types", [])
        type_filter = st.selectbox("Type de levé", options=type_options, index=0)
        if type_filter != "Tous" and not leves_filtered.empty and 'type' in leves_filtered.columns:
            leves_filtered = leves_filtered[leves_filtered['type'] == type_filter]

        appareil_options = ["Tous"] + filter_options.get("appareils", [])
        appareil_filter = st.selectbox("Appareil", options=appareil_options, index=0)
        if appareil_filter != "Tous" and not leves_filtered.empty and 'appareil' in leves_filtered.columns:
            leves_filtered = leves_filtered[leves_filtered['appareil'] == appareil_filter]

        village_options = ["Tous"] + filter_options.get("villages", [])
        village_filter = st.selectbox("Village", options=village_options, index=0)
        if village_filter != "Tous" and not leves_filtered.empty and 'village' in leves_filtered.columns:
            leves_filtered = leves_filtered[leves_filtered['village'] == village_filter]

    if leves_filtered.empty:
        st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
        leves_filtered = leves_df

    # Tabs d'analyse
    tabs = st.tabs(["Statistiques Générales", "Répartition Géographique", "Évolution Temporelle", "Performance"])

    with tabs[0]:
        st.subheader("Aperçu des statistiques globales")
        col1, col2, col3 = st.columns(3)
        quantite = leves_filtered['quantite'] if 'quantite' in leves_filtered.columns else pd.Series([0]*len(leves_filtered))
        with col1:
            st.metric("Nombre d'enregistrements", len(leves_filtered))
        with col2:
            st.metric("Quantité Totale", f"{quantite.sum():,.0f}")
        with col3:
            st.metric("Moyenne par Levé", f"{quantite.mean():.2f}" if len(leves_filtered) else "0")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Levés par Type (Quantité Totale)")
            if not leves_filtered.empty and 'type' in leves_filtered.columns and 'quantite' in leves_filtered.columns:
                type_counts = leves_filtered.groupby('type')['quantite'].sum().reset_index()
                type_counts.columns = ['Type', 'Quantité']
                fig = px.pie(type_counts, values='Quantité', names='Type',
                             title='Répartition des types de levés (quantité)', hole=0.3)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour ce filtre.")

        with col2:
            st.subheader("Top des Topographes")
            if not leves_filtered.empty and 'topographe' in leves_filtered.columns and 'quantite' in leves_filtered.columns:
                topo_quantites = leves_filtered.groupby('topographe')['quantite'].sum().reset_index().sort_values(
                    'quantite', ascending=False).head(10)
                topo_quantites.columns = ['Topographe', 'Quantité Totale']
                fig = px.bar(topo_quantites, x='Topographe', y='Quantité Totale',
                             title='Top 10 des topographes par quantité totale', color='Quantité Totale',
                             color_continuous_scale='Viridis')
                fig.update_layout(xaxis={'categoryorder': 'total descending'})
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour ce filtre.")

    with tabs[1]:
        st.subheader("Répartition géographique des levés")
        col1, col2 = st.columns(2)
        with col1:
            if not leves_filtered.empty and 'region' in leves_filtered.columns and 'quantite' in leves_filtered.columns:
                region_counts = leves_filtered.groupby('region')['quantite'].sum().reset_index().sort_values(
                    'quantite', ascending=False)
                region_counts.columns = ['Région', 'Quantité']
                fig = px.pie(region_counts, values='Quantité', names='Région',
                             title='Répartition des levés par région (quantité totale)', hole=0.3)
                fig.update_traces(textposition='inside', textinfo='percent')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée de région disponible.")

        with col2:
            if not leves_filtered.empty and 'village' in leves_filtered.columns and 'quantite' in leves_filtered.columns:
                village_counts = leves_filtered.groupby('village')['quantite'].sum().reset_index().sort_values(
                    'quantite', ascending=False).head(10)
                village_counts.columns = ['Village', 'Quantité']
                fig = px.bar(village_counts, x='Village', y='Quantité',
                             title='Top 10 des villages (quantité totale)', color='Quantité',
                             color_continuous_scale='Viridis')
                fig.update_layout(xaxis={'categoryorder': 'total descending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour ce filtre.")

        if not leves_filtered.empty and 'commune' in leves_filtered.columns and 'quantite' in leves_filtered.columns:
            st.subheader("Répartition par Commune")
            commune_counts = leves_filtered.groupby('commune')['quantite'].sum().reset_index().sort_values(
                'quantite', ascending=False)
            commune_counts.columns = ['Commune', 'Quantité']
            fig = px.bar(commune_counts.head(15), x='Commune', y='Quantité',
                         title='Top 15 des communes (quantité totale)', color='Quantité',
                         color_continuous_scale='Viridis')
            fig.update_layout(xaxis={'categoryorder': 'total descending'})
            st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        st.subheader("Analyse temporelle des levés")
        if not leves_filtered.empty and 'date' in leves_filtered.columns and 'quantite' in leves_filtered.columns:
            time_series = leves_filtered.groupby(pd.Grouper(key='date', freq='D'))['quantite'].sum().reset_index()
            time_series.columns = ['Date', 'Quantité']
            fig = px.line(time_series, x='Date', y='Quantité',
                          title='Évolution quotidienne des levés (quantité totale)', markers=True)
            fig.update_layout(xaxis_title='Date', yaxis_title='Quantité levée')
            st.plotly_chart(fig, use_container_width=True)

            monthly_series = leves_filtered.groupby(pd.Grouper(key='date', freq='M'))['quantite'].sum().reset_index()
            monthly_series.columns = ['Mois', 'Quantité']
            monthly_series['Mois'] = monthly_series['Mois'].dt.strftime('%b %Y')
            fig2 = px.bar(monthly_series, x='Mois', y='Quantité',
                          title='Évolution mensuelle des levés (quantité totale)', color='Quantité',
                          color_continuous_scale='Viridis')
            fig2.update_xaxes(tickangle=45)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Aucune donnée disponible pour analyser l'évolution temporelle.")

    with tabs[3]:
        st.subheader("Performance et efficacité")
        col1, col2 = st.columns(2)
        with col1:
            if not leves_filtered.empty and 'appareil' in leves_filtered.columns and 'quantite' in leves_filtered.columns:
                appareil_counts = leves_filtered.groupby('appareil')['quantite'].sum().reset_index().sort_values(
                    'quantite', ascending=False)
                appareil_counts.columns = ['Appareil', 'Quantité']
                fig = px.bar(appareil_counts, x='Appareil', y='Quantité',
                             title='Répartition des levés par appareil (quantité totale)', color='Quantité',
                             color_continuous_scale='Viridis')
                fig.update_layout(xaxis={'categoryorder': 'total descending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée d'appareil disponible.")

        with col2:
            if not leves_filtered.empty and 'topographe' in leves_filtered.columns and 'quantite' in leves_filtered.columns:
                topo_perf = leves_filtered.groupby('topographe')['quantite'].agg(['mean', 'count']).reset_index()
                topo_perf.columns = ['Topographe', 'Moyenne', 'Nombre de levés']
                topo_perf = topo_perf[topo_perf['Nombre de levés'] >= 5].sort_values('Moyenne', ascending=False).head(10)
                fig = px.bar(topo_perf, x='Topographe', y='Moyenne',
                             title='Top 10 des topographes par quantité moyenne par levé', color='Nombre de levés',
                             color_continuous_scale='Viridis')
                fig.update_layout(xaxis={'categoryorder': 'total descending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour ce filtre.")

    # Pagination sur la table principale (20 lignes par page)
    st.markdown("---")
    st.subheader("Aperçu des levés (table paginée)")
    page_size = 20
    total_rows = len(leves_filtered)
    if total_rows > page_size:
        page = st.number_input("Page", min_value=1, max_value=(total_rows // page_size) + 1, value=1)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        st.dataframe(leves_filtered.iloc[start_idx:end_idx], use_container_width=True)
    else:
        st.dataframe(leves_filtered, use_container_width=True)

    # Bouton central pour saisir des levés
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Saisir un nouveau levé"):
            if st.session_state.get("authenticated", False):
                st.session_state.current_page = "Saisie des Levés"
                st.rerun()
            else:
                st.session_state.app_state["show_login"] = True
                st.session_state.app_state["show_registration"] = False
                st.warning("Veuillez vous connecter pour saisir des levés.")
                st.rerun()
