import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

def show_dashboard(get_all_leves, get_filter_options):
    st.title("Dashboard des Levés Topographiques")

    @st.cache_data(ttl=60)
    def get_cached_leves():
        return get_all_leves()

    leves_df = get_cached_leves()

    if not leves_df.empty:
        leves_df['date'] = pd.to_datetime(leves_df['date'])

        with st.expander("Filtres", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Date de début", datetime.now() - timedelta(days=30))
            with col2:
                end_date = st.date_input("Date de fin", datetime.now())

            mask_date = (leves_df['date'] >= pd.Timestamp(start_date)) & (leves_df['date'] <= pd.Timestamp(end_date))
            leves_filtered = leves_df[mask_date]

            col1, col2, col3 = st.columns(3)

            with col1:
                filter_options = get_filter_options()
                region_options = ["Toutes"] + filter_options["regions"]
                region_filter = st.selectbox("Région", options=region_options, index=0)
                if region_filter != "Toutes" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['region'] == region_filter]

            with col2:
                commune_options = ["Toutes"] + filter_options["communes"]
                commune_filter = st.selectbox("Commune", options=commune_options, index=0)
                if commune_filter != "Toutes" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['commune'] == commune_filter]

            with col3:
                type_options = ["Tous"] + filter_options["types"]
                type_filter = st.selectbox("Type de levé", options=type_options, index=0)
                if type_filter != "Tous" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['type'] == type_filter]

            col1, col2 = st.columns(2)

            with col1:
                appareil_options = ["Tous"] + filter_options["appareils"]
                appareil_filter = st.selectbox("Appareil", options=appareil_options, index=0)
                if appareil_filter != "Tous" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['appareil'] == appareil_filter]

            with col2:
                village_options = ["Tous"] + filter_options["villages"]
                village_filter = st.selectbox("Village", options=village_options, index=0)
                if village_filter != "Tous" and not leves_filtered.empty:
                    leves_filtered = leves_filtered[leves_filtered['village'] == village_filter]

        if leves_filtered.empty:
            st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
            leves_filtered = leves_df

        tabs = st.tabs(["Statistiques Générales", "Répartition Géographique", "Évolution Temporelle", "Performance"])

        with tabs[0]:
            st.subheader("Aperçu des statistiques globales")
            col1, col2, col3 = st.columns(3)
            total_quantite = leves_filtered['quantite'].sum()
            moyenne_quantite = leves_filtered['quantite'].mean()

            with col1:
                st.metric("Nombre Total de Levés", len(leves_filtered))
            with col2:
                st.metric("Quantité Totale", f"{total_quantite:,.0f}")
            with col3:
                st.metric("Moyenne par Levé", f"{moyenne_quantite:.2f}")

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Levés par Type (Quantité Totale)")
                if not leves_filtered.empty:
                    type_counts = leves_filtered.groupby('type')['quantite'].sum().reset_index()
                    type_counts.columns = ['Type', 'Quantité']

                    fig = px.pie(type_counts, values='Quantité', names='Type',
                                 title='Répartition des types de levés (quantité)', hole=0.3)
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True, height=300)
                else:
                    st.info("Aucune donnée disponible pour ce filtre.")

            with col2:
                st.subheader("Top des Topographes")
                if not leves_filtered.empty:
                    topo_quantites = leves_filtered.groupby('topographe')['quantite'].sum().reset_index().sort_values(
                        'quantite', ascending=False).head(10)
                    topo_quantites.columns = ['Topographe', 'Quantité Totale']

                    fig = px.bar(topo_quantites, x='Topographe', y='Quantité Totale',
                                 title='Top 10 des topographes par quantité totale', color='Quantité Totale',
                                 color_continuous_scale='Viridis')
                    fig.update_layout(xaxis={'categoryorder': 'total descending'}, height=350,
                                      margin=dict(l=40, r=40, t=60, b=80))
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucune donnée disponible pour ce filtre.")

        with tabs[1]:
            st.subheader("Répartition géographique des levés")

            col1, col2 = st.columns(2)

            with col1:
                if not leves_filtered.empty and 'region' in leves_filtered.columns and leves_filtered[
                    'region'].notna().any():
                    st.subheader("Levés par Région")
                    region_counts = leves_filtered.groupby('region')['quantite'].sum().reset_index().sort_values(
                        'quantite', ascending=False)
                    region_counts.columns = ['Région', 'Quantité']

                    fig = px.pie(region_counts, values='Quantité', names='Région',
                                 title='Répartition des levés par région (quantité totale)', hole=0.3)
                    fig.update_traces(textposition='inside', textinfo='percent')
                    st.plotly_chart(fig, use_container_width=True, height=300)
                else:
                    st.info("Aucune donnée de région disponible.")

            with col2:
                st.subheader("Levés par Village")
                if not leves_filtered.empty:
                    village_counts = leves_filtered.groupby('village')['quantite'].sum().reset_index().sort_values(
                        'quantite', ascending=False).head(10)
                    village_counts.columns = ['Village', 'Quantité']

                    fig = px.bar(village_counts, x='Village', y='Quantité',
                                 title='Top 10 des villages (quantité totale)', color='Quantité',
                                 color_continuous_scale='Viridis')
                    fig.update_layout(xaxis={'categoryorder': 'total descending'}, height=350,
                                      margin=dict(l=40, r=40, t=60, b=80))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucune donnée disponible pour ce filtre.")

            if 'commune' in leves_filtered.columns and leves_filtered['commune'].notna().any():
                st.subheader("Répartition par Commune")
                commune_counts = leves_filtered.groupby('commune')['quantite'].sum().reset_index().sort_values(
                    'quantite', ascending=False)
                commune_counts.columns = ['Commune', 'Quantité']

                fig = px.bar(commune_counts.head(15), x='Commune', y='Quantité',
                             title='Top 15 des communes (quantité totale)', color='Quantité',
                             color_continuous_scale='Viridis')
                fig.update_layout(xaxis={'categoryorder': 'total descending'}, height=350,
                                  margin=dict(l=40, r=40, t=60, b=80))
                if len(commune_counts) > 10:
                    fig.update_layout(
                        xaxis=dict(tickmode='array', tickvals=list(range(0, len(commune_counts.head(15)), 2))))
                st.plotly_chart(fig, use_container_width=True)

        with tabs[2]:
            st.subheader("Analyse temporelle des levés")
            if not leves_filtered.empty:
                st.subheader("Évolution des Levés dans le Temps")
                time_series = leves_filtered.groupby(pd.Grouper(key='date', freq='D'))['quantite'].sum().reset_index()
                time_series.columns = ['Date', 'Quantité']

                fig = px.line(time_series, x='Date', y='Quantité',
                              title='Évolution quotidienne des levés (quantité totale)', markers=True)
                fig.update_layout(xaxis_title='Date', yaxis_title='Quantité levée', height=350,
                                  margin=dict(l=40, r=40, t=60, b=40))
                fig.update_xaxes(tickangle=45, nticks=10, tickformat="%d %b")
                st.plotly_chart(fig, use_container_width=True)

                monthly_series = leves_filtered.groupby(pd.Grouper(key='date', freq='M'))[
                    'quantite'].sum().reset_index()
                monthly_series.columns = ['Mois', 'Quantité']
                monthly_series['Mois'] = monthly_series['Mois'].dt.strftime('%b %Y')

                fig = px.bar(monthly_series, x='Mois', y='Quantité',
                             title='Évolution mensuelle des levés (quantité totale)', color='Quantité',
                             color_continuous_scale='Viridis')
                fig.update_layout(height=350, margin=dict(l=40, r=40, t=60, b=80))
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour analyser l'évolution temporelle.")

        with tabs[3]:
            st.subheader("Performance et efficacité")

            col1, col2 = st.columns(2)

            with col1:
                if 'appareil' in leves_filtered.columns and leves_filtered['appareil'].notna().any():
                    st.subheader("Levés par Appareil")
                    appareil_counts = leves_filtered.groupby('appareil')['quantite'].sum().reset_index().sort_values(
                        'quantite', ascending=False)
                    appareil_counts.columns = ['Appareil', 'Quantité']

                    fig = px.bar(appareil_counts, x='Appareil', y='Quantité',
                                 title='Répartition des levés par appareil (quantité totale)', color='Quantité',
                                 color_continuous_scale='Viridis')
                    fig.update_layout(xaxis={'categoryorder': 'total descending'}, height=350,
                                      margin=dict(l=40, r=40, t=60, b=80))
                    if len(appareil_counts) > 8:
                        fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucune donnée d'appareil disponible.")

            with col2:
                if not leves_filtered.empty:
                    st.subheader("Efficacité par Topographe")
                    topo_perf = leves_filtered.groupby('topographe')['quantite'].agg(['mean', 'count']).reset_index()
                    topo_perf.columns = ['Topographe', 'Moyenne', 'Nombre de levés']
                    topo_perf = topo_perf[topo_perf['Nombre de levés'] >= 5].sort_values('Moyenne',
                                                                                         ascending=False).head(10)

                    fig = px.bar(topo_perf, x='Topographe', y='Moyenne',
                                 title='Top 10 des topographes par quantité moyenne par levé', color='Nombre de levés',
                                 color_continuous_scale='Viridis')
                    fig.update_layout(xaxis={'categoryorder': 'total descending'}, height=350,
                                      margin=dict(l=40, r=40, t=60, b=80))
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucune donnée disponible pour ce filtre.")

        # Bouton central pour saisir des levés
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Saisir un nouveau levé", use_container_width=True):
                if st.session_state.get("authenticated", False):
                    st.session_state.current_page = "Saisie des Levés"
                    st.rerun()
                else:
                    st.session_state.app_state["show_login"] = True
                    st.session_state.app_state["show_registration"] = False
                    st.warning("Veuillez vous connecter pour saisir des levés.")
                    st.rerun()
    else:
        st.info("Aucun levé n'a encore été enregistré. Commencez par saisir des données.")

        # Bouton central pour saisir des levés
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Saisir un nouveau levé", use_container_width=True):
                if st.session_state.get("authenticated", False):
                    st.session_state.current_page = "Saisie des Levés"
                    st.rerun()
                else:
                    st.session_state.app_state["show_login"] = True
                    st.session_state.app_state["show_registration"] = False
                    st.warning("Veuillez vous connecter pour saisir des levés.")
                    st.rerun()