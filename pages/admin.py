import streamlit as st
import pandas as pd

def show_admin_users_page(get_users, delete_user, add_user, validate_email, validate_phone):
    st.title("Administration - Gestion des Utilisateurs")

    if not st.session_state.get("authenticated", False) or st.session_state.user["role"] != "administrateur":
        st.error("Accès non autorisé. Cette page est réservée aux administrateurs.")
        return

    users_df = get_users()

    if not users_df.empty:
        users_df = users_df.rename(columns={
            'id': 'ID',
            'username': 'Nom d\'utilisateur',
            'email': 'Email',
            'phone': 'Téléphone',
            'role': 'Rôle',
            'created_at': 'Date de création'
        })

        if 'Date de création' in users_df.columns:
            users_df['Date de création'] = pd.to_datetime(users_df['Date de création']).dt.strftime('%d/%m/%Y %H:%M')

        st.dataframe(users_df, use_container_width=True)

        st.subheader("Supprimer un utilisateur")
        with st.form("delete_user_form"):
            user_id = st.number_input("ID de l'utilisateur à supprimer", min_value=1, step=1)
            delete_submit = st.form_submit_button("Supprimer l'utilisateur")

            if delete_submit:
                success, message = delete_user(user_id)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    else:
        st.info("Aucun utilisateur n'a été trouvé.")

    st.subheader("Ajouter un nouvel utilisateur")
    with st.form("add_user_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        email = st.text_input("Email (optionnel)")
        phone = st.text_input("Téléphone (optionnel)")
        role = st.selectbox("Rôle", options=["topographe", "administrateur"])

        submit = st.form_submit_button("Ajouter l'utilisateur")

        if submit:
            if not username or not password:
                st.error("Le nom d'utilisateur et le mot de passe sont obligatoires.")
            elif email and not validate_email(email):
                st.error("Format d'email invalide.")
            elif phone and not validate_phone(phone):
                st.error("Format de numéro de téléphone invalide.")
            else:
                success, message = add_user(username, password, email, phone, role)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

def show_admin_data_page(get_all_leves, get_users):
    st.title("Administration - Gestion des Données")

    if not st.session_state.get("authenticated", False) or st.session_state.user["role"] != "administrateur":
        st.error("Accès non autorisé. Cette page est réservée aux administrateurs.")
        return

    st.subheader("Maintenance de la Base de Données")

    col1, col2 = st.columns(2)

    with col1:
        st.info("Pour PostgreSQL, la sauvegarde se fait via pg_dump. Consultez la documentation PostgreSQL.")

    with col2:
        st.info("La restauration de PostgreSQL se fait via pg_restore ou psql. Consultez la documentation PostgreSQL.")

    st.subheader("Statistiques Globales")

    leves_df = get_all_leves()
    users_df = get_users()

    if not leves_df.empty and not users_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Nombre d'utilisateurs", len(users_df))
        with col2:
            st.metric("Nombre de levés", len(leves_df))
        with col3:
            st.metric("Quantité totale", f"{leves_df['quantite'].sum():,.0f}")
        with col4:
            nb_villages = leves_df['village'].nunique()
            st.metric("Nombre de villages", nb_villages)
    else:
        st.info("Pas assez de données pour afficher les statistiques.")