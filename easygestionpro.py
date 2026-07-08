# cd "C:\Users\leurq\Desktop\easygestionprofessionnelle"
# py -m streamlit run easygestionpro.py


import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

from auth import *


st.set_page_config(
    page_title="EasyGestion Pro",
    page_icon="📋",
    layout="wide"
)


DB = "easygestionpro.db"


# ==========================
# BASE APPLICATION
# ==========================

def connexion_db():
    return sqlite3.connect(DB)



def init_database():

    con = connexion_db()
    cur = con.cursor()


    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entreprise_id INTEGER,
        nom TEXT,
        telephone TEXT,
        email TEXT,
        date_creation TEXT
    )
    """)


    cur.execute("""
    CREATE TABLE IF NOT EXISTS rendezvous(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entreprise_id INTEGER,
        client TEXT,
        date TEXT,
        heure TEXT
    )
    """)


    cur.execute("""
    CREATE TABLE IF NOT EXISTS factures(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entreprise_id INTEGER,
        client TEXT,
        montant REAL,
        statut TEXT,
        date TEXT
    )
    """)


    con.commit()
    con.close()



def lire(sql, params=()):

    con = connexion_db()

    df = pd.read_sql_query(
        sql,
        con,
        params=params
    )

    con.close()

    return df



def execute(sql, params=()):

    con = connexion_db()
    cur = con.cursor()

    cur.execute(
        sql,
        params
    )

    con.commit()
    con.close()



init_database()
init_auth()



# ==========================
# CONNEXION
# ==========================

if "connecte" not in st.session_state:
    st.session_state.connecte = False



if not st.session_state.connecte:


    st.title("🔐 EasyGestion Pro")


    choix = st.radio(
        "Choisir",
        [
            "Connexion",
            "Créer mon entreprise"
        ]
    )



    if choix == "Connexion":


        email = st.text_input("Email")

        password = st.text_input(
            "Mot de passe",
            type="password"
        )


        if st.button("Se connecter"):


            user = connexion_utilisateur(
                email,
                password
            )


            if user:

                st.session_state.connecte = True

                st.session_state.entreprise_id = user[1]

                st.rerun()


            else:

                st.error(
                    "Identifiants incorrects"
                )



    else:


        entreprise = st.text_input(
            "Entreprise"
        )

        nom = st.text_input(
            "Votre nom"
        )

        email = st.text_input(
            "Email"
        )

        password = st.text_input(
            "Mot de passe",
            type="password"
        )


        if st.button(
            "Créer mon entreprise"
        ):


            ok = creer_entreprise(
                entreprise,
                nom,
                email,
                password
            )


            if ok:

                st.success(
                    "Entreprise créée ! Connectez-vous."
                )

            else:

                st.error(
                    "Email déjà utilisé."
                )


    st.stop()



# ==========================
# APPLICATION CONNECTEE
# ==========================


ENTREPRISE = st.session_state.entreprise_id



st.sidebar.title(
    "📋 EasyGestion Pro"
)


if st.sidebar.button(
    "Déconnexion"
):

    st.session_state.connecte = False
    st.rerun()



menu = st.sidebar.radio(
    "Menu",
    [
        "🏠 Tableau de bord",
        "👥 Clients",
        "📅 Rendez-vous",
        "🧾 Factures"
    ]
)



# ==========================
# TABLEAU DE BORD
# ==========================

if menu == "🏠 Tableau de bord":


    st.title(
        "📊 Tableau de bord"
    )


    clients = lire(
        "SELECT * FROM clients WHERE entreprise_id=?",
        (ENTREPRISE,)
    )


    factures = lire(
        "SELECT * FROM factures WHERE entreprise_id=?",
        (ENTREPRISE,)
    )


    rdv = lire(
        "SELECT * FROM rendezvous WHERE entreprise_id=?",
        (ENTREPRISE,)
    )


    chiffre = 0

    if not factures.empty:

        chiffre = factures["montant"].sum()



    c1,c2,c3 = st.columns(3)


    c1.metric(
        "Clients",
        len(clients)
    )

    c2.metric(
        "Rendez-vous",
        len(rdv)
    )

    c3.metric(
        "Chiffre d'affaires",
        f"{chiffre:.2f} €"
    )



# ==========================
# CLIENTS
# ==========================

elif menu == "👥 Clients":


    st.title(
        "👥 Clients"
    )


    nom = st.text_input(
        "Nom client"
    )

    tel = st.text_input(
        "Téléphone"
    )

    email = st.text_input(
        "Email"
    )


    if st.button(
        "Ajouter client"
    ):


        execute(
            """
            INSERT INTO clients
            VALUES(NULL,?,?,?,?,?)
            """,
            (
                ENTREPRISE,
                nom,
                tel,
                email,
                str(datetime.now())
            )
        )

        st.success(
            "Client ajouté"
        )


    clients = lire(
        "SELECT * FROM clients WHERE entreprise_id=?",
        (ENTREPRISE,)
    )


    st.dataframe(
        clients
    )



# ==========================
# RENDEZ-VOUS
# ==========================

elif menu == "📅 Rendez-vous":


    st.title(
        "📅 Rendez-vous"
    )


    client = st.text_input(
        "Client"
    )

    d = st.date_input(
        "Date"
    )

    h = st.time_input(
        "Heure"
    )


    if st.button(
        "Ajouter rendez-vous"
    ):


        execute(
            """
            INSERT INTO rendezvous
            VALUES(NULL,?,?,?,?)
            """,
            (
                ENTREPRISE,
                client,
                str(d),
                str(h)
            )
        )


        st.success(
            "Rendez-vous ajouté"
        )



    st.dataframe(
        lire(
            "SELECT * FROM rendezvous WHERE entreprise_id=?",
            (ENTREPRISE,)
        )
    )



# ==========================
# FACTURES
# ==========================

elif menu == "🧾 Factures":


    st.title(
        "🧾 Factures"
    )


    client = st.text_input(
        "Client"
    )

    montant = st.number_input(
        "Montant €"
    )

    statut = st.selectbox(
        "Statut",
        [
            "En attente",
            "Payée"
        ]
    )



    if st.button(
        "Créer facture"
    ):


        execute(
            """
            INSERT INTO factures
            VALUES(NULL,?,?,?,?,?)
            """,
            (
                ENTREPRISE,
                client,
                montant,
                statut,
                str(datetime.now())
            )
        )


        st.success(
            "Facture créée"
        )


    st.dataframe(
        lire(
            "SELECT * FROM factures WHERE entreprise_id=?",
            (ENTREPRISE,)
        )
    )