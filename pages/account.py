import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

def show_account_page(get_leves_by_topographe, verify_user, change_password):
    st.title("Mon Compte")
    if not st.session_state.app_state.get("authenticated", False):
        st.warning("Vous devez être connecté pour accéder à votre compte.")
        st.session_state.app_state["show_login"] = True
        st.experimental_rerun()
        return
    username = st.session_state.app_state["username"]
    role = st.session_state.app_state["user"]["role"]
    st.write(f"**Nom d'utilisateur:** {username}")
    st.write(f"**Rôle:** {role}")

    st.subheader("Changer de mot de passe")
    with st.form("change_password_form"):
        old_password = st.text_input("Ancien mot de passe", type="password")
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm_password = st.text_input("Confirmer le nouveau mot de passe", type="password")
        submit = st.form_submit_button("Changer le mot de passe")
        if submit:
            if not old_password or not new_password or not confirm_password:
                st.error("Tous les champs sont obligatoires.")
            elif new_password != confirm_password:
                st.error("Les nouveaux mots de passe ne correspondent pas.")
            else:
                user = verify_user(username, old_password)
                if not user:
                    st.error("Ancien mot de passe incorrect.")
                else:
                    if change_password(username, new_password):
                        st.success("Mot de passe changé avec succès!")
                    else:
                        st.error("Erreur lors du changement de mot de passe.")

    st.subheader("Mes Statistiques")
    # OPTI: récupération efficace des données utilisateur
    leves = get_leves_by_topographe(username)
    if isinstance(leves, pd.DataFrame):
        leves_df = leves
    else:
        leves_df = pd.DataFrame(leves)

    if not leves_df.empty:
        # OPTI: utiliser date seulement si elle existe
        if 'date' in leves_df.columns:
            leves_df['date'] = pd.to_datetime(leves_df['date'], errors='coerce')
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre Total de Levés", len(leves_df))
        with col2:
            st.metric("Quantité Totale", f"{leves_df['quantite'].sum():,.0f}" if 'quantite' in leves_df else "N/A")
        with col3:
            st.metric("Moyenne par Levé", f"{leves_df['quantite'].mean():.2f}" if 'quantite' in leves_df else "N/A")

        if 'date' in leves_df.columns and not leves_df['date'].isnull().all():
            st.subheader("Évolution de mes levés")
            time_series = leves_df.groupby(pd.Grouper(key='date', freq='D')).size().reset_index()
            time_series.columns = ['Date', 'Nombre']
            fig = px.line(
                time_series,
                x='Date',
                y='Nombre',
                title='Évolution quotidienne de mes levés',
                markers=True
            )
            fig.update_layout(xaxis_title='Date', yaxis_title='Nombre de levés')
            st.plotly_chart(fig, use_container_width=True)

        if 'type' in leves_df.columns and not leves_df['type'].isnull().all():
            st.subheader("Répartition par type de levé")
            type_counts = leves_df['type'].value_counts().reset_index()
            type_counts.columns = ['Type', 'Nombre']
            fig = px.pie(
                type_counts,
                values='Nombre',
                names='Type',
                title='Répartition des types de levés',
                hole=0.3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Vous n'avez pas encore enregistré de levés.")
