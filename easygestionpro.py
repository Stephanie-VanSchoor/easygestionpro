# =======================================================
# easygestionpro.py  –  Version améliorée
# =======================================================

import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
import plotly.express as px
import bcrypt

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Time, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, joinedload
from sqlalchemy.exc import IntegrityError

# ---------- Configuration de la page ----------
st.set_page_config(
    page_title="EasyGestion Pro",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Base de données ----------
DB_NAME = "easygestionpro.db"
engine = create_engine(f"sqlite:///{DB_NAME}", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ---------- Modèles ----------
class Entreprise(Base):
    __tablename__ = "entreprises"
    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    date_creation = Column(DateTime, default=datetime.now)

    utilisateurs = relationship("Utilisateur", back_populates="entreprise")
    clients = relationship("Client", back_populates="entreprise")
    rendezvous = relationship("RendezVous", back_populates="entreprise")
    factures = relationship("Facture", back_populates="entreprise")

class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id = Column(Integer, primary_key=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    nom = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    mot_de_passe_hash = Column(String, nullable=False)
    date_creation = Column(DateTime, default=datetime.now)

    entreprise = relationship("Entreprise", back_populates="utilisateurs")

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    nom = Column(String, nullable=False)
    telephone = Column(String)
    email = Column(String)
    date_creation = Column(DateTime, default=datetime.now)

    entreprise = relationship("Entreprise", back_populates="clients")

class RendezVous(Base):
    __tablename__ = "rendezvous"
    id = Column(Integer, primary_key=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    client_nom = Column(String, nullable=False)   # On stocke le nom pour simplifier
    date = Column(Date, nullable=False)
    heure = Column(Time, nullable=False)
    date_creation = Column(DateTime, default=datetime.now)

    entreprise = relationship("Entreprise", back_populates="rendezvous")

class Facture(Base):
    __tablename__ = "factures"
    id = Column(Integer, primary_key=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    client_nom = Column(String, nullable=False)
    montant = Column(Float, nullable=False)
    statut = Column(String, default="En attente")  # En attente, Payée, Annulée
    date_emission = Column(DateTime, default=datetime.now)
    date_echeance = Column(Date)   # Optionnel

    entreprise = relationship("Entreprise", back_populates="factures")

# ---------- Création des tables ----------
Base.metadata.create_all(engine)

# ---------- Fonctions utilitaires ----------
def get_session():
    return SessionLocal()

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())

# ---------- Initialisation : création d'un compte admin par défaut si vide ----------
def init_demo_company():
    session = get_session()
    if session.query(Entreprise).count() == 0:
        # Créer une entreprise de démonstration
        entreprise = Entreprise(nom="EasyGestion Demo")
        session.add(entreprise)
        session.flush()  # pour avoir l'id
        admin = Utilisateur(
            entreprise_id=entreprise.id,
            nom="Administrateur",
            email="admin@demo.com",
            mot_de_passe_hash=hash_password("admin123")
        )
        session.add(admin)
        session.commit()
    session.close()

init_demo_company()

# ---------- Gestion de session Streamlit ----------
if "connecte" not in st.session_state:
    st.session_state.connecte = False
if "entreprise_id" not in st.session_state:
    st.session_state.entreprise_id = None
if "user_nom" not in st.session_state:
    st.session_state.user_nom = ""

# =======================================================
# AUTHENTIFICATION
# =======================================================
def page_connexion():
    st.title("🔐 EasyGestion Pro – Connexion")
    choix = st.radio("Choisir", ["Connexion", "Créer mon entreprise"])

    if choix == "Connexion":
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter", type="primary"):
            session = get_session()
            utilisateur = session.query(Utilisateur).filter_by(email=email).first()
            session.close()
            if utilisateur and verify_password(password, utilisateur.mot_de_passe_hash):
                st.session_state.connecte = True
                st.session_state.entreprise_id = utilisateur.entreprise_id
                st.session_state.user_nom = utilisateur.nom
                st.rerun()
            else:
                st.error("Identifiants incorrects")

    else:  # Création
        with st.form("create_company"):
            entreprise = st.text_input("Nom de l'entreprise")
            nom = st.text_input("Votre nom")
            email = st.text_input("Email")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Créer mon entreprise")
            if submitted:
                if not (entreprise and nom and email and password):
                    st.error("Tous les champs sont obligatoires")
                else:
                    session = get_session()
                    # Vérifier si l'email existe déjà
                    if session.query(Utilisateur).filter_by(email=email).first():
                        st.error("Cet email est déjà utilisé.")
                    else:
                        new_entreprise = Entreprise(nom=entreprise)
                        session.add(new_entreprise)
                        session.flush()
                        new_user = Utilisateur(
                            entreprise_id=new_entreprise.id,
                            nom=nom,
                            email=email,
                            mot_de_passe_hash=hash_password(password)
                        )
                        session.add(new_user)
                        session.commit()
                        st.success("Entreprise créée ! Connectez-vous.")
                        st.rerun()
                    session.close()

# =======================================================
# PAGES PRINCIPALES
# =======================================================
def dashboard():
    st.title("📊 Tableau de bord")
    ent_id = st.session_state.entreprise_id
    session = get_session()

    # Compteurs
    nb_clients = session.query(Client).filter_by(entreprise_id=ent_id).count()
    nb_rdv = session.query(RendezVous).filter_by(entreprise_id=ent_id).count()
    factures = session.query(Facture).filter_by(entreprise_id=ent_id).all()
    ca = sum(f.montant for f in factures if f.statut == "Payée")

    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Clients", nb_clients)
    col2.metric("📅 Rendez-vous", nb_rdv)
    col3.metric("💰 Chiffre d'affaires (payé)", f"{ca:.2f} €")

    # Graphiques
    if nb_rdv > 0:
        rdvs = session.query(RendezVous).filter_by(entreprise_id=ent_id).all()
        df_rdv = pd.DataFrame([(r.date, 1) for r in rdvs], columns=["date", "count"])
        df_rdv["mois"] = pd.to_datetime(df_rdv["date"]).dt.to_period("M").astype(str)
        df_rdv = df_rdv.groupby("mois").sum().reset_index()
        if not df_rdv.empty:
            fig1 = px.bar(df_rdv, x="mois", y="count", title="Rendez-vous par mois")
            st.plotly_chart(fig1, use_container_width=True)

    if ca > 0:
        # CA par mois
        df_ca = pd.DataFrame([(f.date_emission, f.montant) for f in factures if f.statut == "Payée"],
                             columns=["date", "montant"])
        if not df_ca.empty:
            df_ca["mois"] = pd.to_datetime(df_ca["date"]).dt.to_period("M").astype(str)
            df_ca = df_ca.groupby("mois").sum().reset_index()
            fig2 = px.line(df_ca, x="mois", y="montant", title="CA mensuel (€)")
            st.plotly_chart(fig2, use_container_width=True)

    session.close()

def gestion_clients():
    st.title("👥 Clients")
    ent_id = st.session_state.entreprise_id
    session = get_session()

    # Formulaire d'ajout
    with st.expander("➕ Ajouter un client", expanded=False):
        with st.form("add_client"):
            nom = st.text_input("Nom *")
            tel = st.text_input("Téléphone")
            email = st.text_input("Email")
            submitted = st.form_submit_button("Ajouter")
            if submitted:
                if not nom:
                    st.error("Le nom est obligatoire")
                else:
                    client = Client(entreprise_id=ent_id, nom=nom, telephone=tel, email=email)
                    session.add(client)
                    session.commit()
                    st.toast("Client ajouté ✅", icon="✅")
                    st.rerun()

    # Recherche
    search = st.text_input("🔍 Rechercher un client", placeholder="Nom ou email")
    query = session.query(Client).filter_by(entreprise_id=ent_id)
    if search:
        query = query.filter(Client.nom.contains(search) | Client.email.contains(search))
    clients = query.all()

    if not clients:
        st.info("Aucun client")
    else:
        # Affichage avec data_editor pour modification inline
        data = [{"ID": c.id, "Nom": c.nom, "Téléphone": c.telephone, "Email": c.email} for c in clients]
        df = pd.DataFrame(data)
        edited = st.data_editor(df, key="clients_editor", use_container_width=True, num_rows="dynamic")
        # Détecter les modifications
        # Pour simplifier, on ajoute des boutons de suppression
        for c in clients:
            col1, col2 = st.columns([10, 1])
            with col1:
                st.write(f"{c.nom}  |  {c.telephone}  |  {c.email}")
            with col2:
                if st.button("🗑️", key=f"del_client_{c.id}"):
                    session.delete(c)
                    session.commit()
                    st.toast(f"Client {c.nom} supprimé", icon="🗑️")
                    st.rerun()

        # Mise à jour en masse (si l'utilisateur modifie via l'éditeur, on peut enregistrer)
        # Ici on ne gère pas pour éviter la complexité, mais on pourrait.
    session.close()

def gestion_rendezvous():
    st.title("📅 Rendez-vous")
    ent_id = st.session_state.entreprise_id
    session = get_session()

    with st.expander("➕ Ajouter un rendez-vous", expanded=False):
        with st.form("add_rdv"):
            client_nom = st.text_input("Nom du client *")
            date_rdv = st.date_input("Date", value=date.today())
            heure_rdv = st.time_input("Heure", value=datetime.now().time())
            submitted = st.form_submit_button("Ajouter")
            if submitted:
                if not client_nom:
                    st.error("Le nom est obligatoire")
                else:
                    rdv = RendezVous(entreprise_id=ent_id, client_nom=client_nom, date=date_rdv, heure=heure_rdv)
                    session.add(rdv)
                    session.commit()
                    st.toast("Rendez-vous ajouté ✅", icon="✅")
                    st.rerun()

    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        date_filter = st.date_input("Filtrer par date", value=None)
    with col2:
        search_rdv = st.text_input("Rechercher un client", placeholder="Nom")

    query = session.query(RendezVous).filter_by(entreprise_id=ent_id)
    if date_filter:
        query = query.filter(RendezVous.date == date_filter)
    if search_rdv:
        query = query.filter(RendezVous.client_nom.contains(search_rdv))
    rdvs = query.all()

    if not rdvs:
        st.info("Aucun rendez-vous")
    else:
        for rdv in rdvs:
            col1, col2, col3, col4 = st.columns([3,2,2,1])
            with col1:
                st.write(f"👤 {rdv.client_nom}")
            with col2:
                st.write(f"📅 {rdv.date.strftime('%d/%m/%Y')}")
            with col3:
                st.write(f"⏰ {rdv.heure.strftime('%H:%M')}")
            with col4:
                if st.button("🗑️", key=f"del_rdv_{rdv.id}"):
                    session.delete(rdv)
                    session.commit()
                    st.toast(f"Rendez-vous de {rdv.client_nom} supprimé", icon="🗑️")
                    st.rerun()
    session.close()

def gestion_factures():
    st.title("🧾 Factures")
    ent_id = st.session_state.entreprise_id
    session = get_session()

    with st.expander("➕ Créer une facture", expanded=False):
        with st.form("add_facture"):
            client_nom = st.text_input("Client *")
            montant = st.number_input("Montant (€) *", min_value=0.0, step=0.01)
            statut = st.selectbox("Statut", ["En attente", "Payée", "Annulée"])
            echeance = st.date_input("Date d'échéance", value=date.today() + timedelta(days=30))
            submitted = st.form_submit_button("Créer")
            if submitted:
                if not client_nom or montant <= 0:
                    st.error("Client et montant valide requis")
                else:
                    facture = Facture(
                        entreprise_id=ent_id,
                        client_nom=client_nom,
                        montant=montant,
                        statut=statut,
                        date_echeance=echeance
                    )
                    session.add(facture)
                    session.commit()
                    st.toast("Facture créée ✅", icon="✅")
                    st.rerun()

    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        statut_filter = st.selectbox("Statut", ["Tous", "En attente", "Payée", "Annulée"])
    with col2:
        search_fact = st.text_input("Rechercher un client")

    query = session.query(Facture).filter_by(entreprise_id=ent_id)
    if statut_filter != "Tous":
        query = query.filter(Facture.statut == statut_filter)
    if search_fact:
        query = query.filter(Facture.client_nom.contains(search_fact))
    factures = query.all()

    if not factures:
        st.info("Aucune facture")
    else:
        for f in factures:
            col1, col2, col3, col4, col5, col6 = st.columns([2,1.5,1,1,1,0.8])
            with col1:
                st.write(f"👤 {f.client_nom}")
            with col2:
                st.write(f"{f.montant:.2f} €")
            with col3:
                st.write(f"{f.statut}")
            with col4:
                st.write(f"{f.date_emission.strftime('%d/%m/%Y')}")
            with col5:
                if f.date_echeance:
                    st.write(f"Échéance: {f.date_echeance.strftime('%d/%m/%Y')}")
            with col6:
                if st.button("🗑️", key=f"del_fact_{f.id}"):
                    session.delete(f)
                    session.commit()
                    st.toast(f"Facture de {f.client_nom} supprimée", icon="🗑️")
                    st.rerun()
    session.close()

# =======================================================
# APP PRINCIPALE
# =======================================================
def main():
    if not st.session_state.connecte:
        page_connexion()
        return

    # Barre latérale
    st.sidebar.title("📋 EasyGestion Pro")
    st.sidebar.write(f"👋 Bienvenue, {st.session_state.user_nom}")
    if st.sidebar.button("Déconnexion", use_container_width=True):
        st.session_state.connecte = False
        st.session_state.entreprise_id = None
        st.session_state.user_nom = ""
        st.rerun()

    menu = st.sidebar.radio(
        "Navigation",
        ["🏠 Tableau de bord", "👥 Clients", "📅 Rendez-vous", "🧾 Factures"],
        index=0
    )

    # Pages
    if menu == "🏠 Tableau de bord":
        dashboard()
    elif menu == "👥 Clients":
        gestion_clients()
    elif menu == "📅 Rendez-vous":
        gestion_rendezvous()
    elif menu == "🧾 Factures":
        gestion_factures()

if __name__ == "__main__":
    main()
