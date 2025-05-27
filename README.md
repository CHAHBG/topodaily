Topodaily
Topodaily est une application web développée avec Streamlit pour la gestion, le suivi et l’analyse des levés topographiques sur le terrain. Elle permet aux équipes de topographes et aux administrateurs de centraliser, visualiser et exporter les données de rendement quotidien, tout en assurant la sécurité et la gestion des utilisateurs.

Fonctionnalités principales
Authentification et gestion des utilisateurs :
Création de comptes avec rôles (topographe ou administrateur)
Connexion sécurisée, changement de mot de passe
Suppression et gestion des comptes (admin)
Saisie des levés topographiques :
Formulaire intuitif avec sélection dynamique de la région, commune et village (import depuis un fichier Excel)
Saisie des informations : date, localisation, type de levé, quantité, appareil utilisé, etc.
Visualisation et analyse :
Tableau de bord interactif avec statistiques globales et filtres avancés
Graphiques (histogrammes, camemberts, séries temporelles) sur la quantité, la répartition géographique, la performance par topographe, etc.
Suivi personnalisé pour chaque utilisateur
Exportation des données :
Téléchargement des levés filtrés au format CSV
Administration :
Gestion des utilisateurs (ajout, suppression, modification)
Statistiques avancées sur tous les utilisateurs et les levés
Maintenance de la base PostgreSQL (sauvegarde/restauration via outils PostgreSQL externes)
Prérequis
Python 3.8+
Streamlit
PostgreSQL
Bibliothèques Python : pandas, matplotlib, seaborn, plotly, psycopg2, sqlalchemy, etc.
Installation
Cloner le dépôt :

bash
git clone https://github.com/CHAHBG/topodaily.git
cd topodaily
Installer les dépendances :

bash
pip install -r requirements.txt
Configurer la base de données PostgreSQL :

Créez une base de données PostgreSQL (par défaut nommée topodb)
Définissez les variables d’environnement pour la connexion :
DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
Préparer le fichier de villages :

Ajoutez un fichier Villages.xlsx à la racine du projet contenant les colonnes : region, commune, village.
Lancement de l’application
bash
streamlit run topodaily.py
Utilisation
Connectez-vous ou créez un compte depuis la page d’accueil.
Naviguez via la barre latérale :
Dashboard : vue d’ensemble et statistiques.
Saisie des Levés : ajout de nouveaux levés topographiques.
Suivi : filtre, visualisation et export de vos levés.
Mon Compte : modification du mot de passe et statistiques personnelles.
Administration : gestion avancée (pour les administrateurs).
Sécurité
Les mots de passe sont stockés sous forme de hash SHA256.
Les droits d’accès sont gérés selon le rôle de l’utilisateur.
L’administrateur principal ne peut pas être supprimé.
Auteurs
Projet développé par CHAHBG
Licence
Ce projet est distribué sous licence MIT.
