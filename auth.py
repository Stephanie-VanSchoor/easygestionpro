import sqlite3
import hashlib
from datetime import datetime


DB = "easygestionpro.db"


def connexion():
    return sqlite3.connect(DB)



def init_auth():

    con = connexion()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS entreprises(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        email TEXT,
        date_creation TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS utilisateurs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entreprise_id INTEGER,
        nom TEXT,
        email TEXT UNIQUE,
        mot_de_passe TEXT,
        role TEXT
    )
    """)

    con.commit()
    con.close()



def crypter_mot_de_passe(password):

    return hashlib.sha256(
        password.encode()
    ).hexdigest()



def creer_entreprise(
        entreprise,
        nom,
        email,
        password
):

    con = connexion()
    cur = con.cursor()

    try:

        cur.execute(
            """
            INSERT INTO entreprises
            VALUES(NULL,?,?,?)
            """,
            (
                entreprise,
                email,
                str(datetime.now())
            )
        )

        entreprise_id = cur.lastrowid


        cur.execute(
            """
            INSERT INTO utilisateurs
            VALUES(NULL,?,?,?,?,?)
            """,
            (
                entreprise_id,
                nom,
                email,
                crypter_mot_de_passe(password),
                "Administrateur"
            )
        )


        con.commit()

        return True


    except sqlite3.IntegrityError:

        return False


    finally:

        con.close()



def connexion_utilisateur(
        email,
        password
):

    con = connexion()
    cur = con.cursor()


    cur.execute(
        """
        SELECT *
        FROM utilisateurs
        WHERE email=?
        AND mot_de_passe=?
        """,
        (
            email,
            crypter_mot_de_passe(password)
        )
    )


    user = cur.fetchone()

    con.close()

    return user