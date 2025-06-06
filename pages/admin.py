import streamlit as st
import pandas as pd

def show_admin_users_page(get_users, delete_user, add_user, validate_email, validate_phone):
    st.title("Administration - Gestion des Utilisateurs")

    # Fixed: Access app_state properly from session_state
    app_state = st.session_state.get("app_state", {})
    
    # Check authentication and role
    if not app_state.get("authenticated", False):
        st.error("Vous devez être connecté pour accéder à cette page.")
        return
    
    user_data = app_state.get("user", {})
    user_role = user_data.get("role", "")
    
    if user_role != "administrateur":
        st.error("Accès non autorisé. Cette page est réservée aux administrateurs.")
        return

    # Get users data
    users_df = get_users()

    if not users_df.empty:
        # Rename columns for better display
        users_df = users_df.rename(columns={
            'id': 'ID',
            'username': 'Nom d\'utilisateur',
            'email': 'Email',
            'phone': 'Téléphone',
            'role': 'Rôle',
            'created_at': 'Date de création'
        })

        # Format date column if it exists
        if 'Date de création' in users_df.columns:
            users_df['Date de création'] = pd.to_datetime(users_df['Date de création']).dt.strftime('%d/%m/%Y %H:%M')

        st.subheader("Liste des Utilisateurs")
        st.dataframe(users_df, use_container_width=True)

        # Delete user section
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

    # Add new user section
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

    # Fixed: Access app_state properly from session_state
    app_state = st.session_state.get("app_state", {})
    
    # Check authentication and role
    if not app_state.get("authenticated", False):
        st.error("Vous devez être connecté pour accéder à cette page.")
        return
    
    user_data = app_state.get("user", {})
    user_role = user_data.get("role", "")
    
    if user_role != "administrateur":
        st.error("Accès non autorisé. Cette page est réservée aux administrateurs.")
        return

    st.subheader("Maintenance de la Base de Données")

    col1, col2 = st.columns(2)

    with col1:
        st.info("Pour PostgreSQL, la sauvegarde se fait via pg_dump. Consultez la documentation PostgreSQL.")

    with col2:
        st.info("La restauration de PostgreSQL se fait via pg_restore ou psql. Consultez la documentation PostgreSQL.")

    st.subheader("Statistiques Globales")

    # Get data
    leves_df = get_all_leves()
    users_df = get_users()

    if not leves_df.empty and not users_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Nombre d'utilisateurs", len(users_df))
        with col2:
            st.metric("Nombre de levés", len(leves_df))
        with col3:
            # Check if 'quantite' column exists
            if 'quantite' in leves_df.columns:
                st.metric("Quantité totale", f"{leves_df['quantite'].sum():,.0f}")
            else:
                st.metric("Quantité totale", "N/A")
        with col4:
            # Check if 'village' column exists
            if 'village' in leves_df.columns:
                nb_villages = leves_df['village'].nunique()
                st.metric("Nombre de villages", nb_villages)
            else:
                st.metric("Nombre de villages", "N/A")
    else:
        st.info("Pas assez de données pour afficher les statistiques.")
