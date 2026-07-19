# ============================================================
# EasyGestion Pro – Version Ultime (avec toutes les fonctionnalités)
# ============================================================
import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
import plotly.express as px
import bcrypt
from fpdf import FPDF
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import openpyxl  # pour Excel

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Time, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import IntegrityError

# Chargement des variables d'environnement
load_dotenv()

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

# ---------- Modèles (ajout du champ role pour Utilisateur) ----------
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
    role = Column(String, default="employe")  # "admin" ou "employe"
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
    client_nom = Column(String, nullable=False)
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
    statut = Column(String, default="En attente")
    date_emission = Column(DateTime, default=datetime.now)
    date_echeance = Column(Date)
    entreprise = relationship("Entreprise", back_populates="factures")

Base.metadata.create_all(engine)

# ---------- Fonctions utilitaires ----------
def get_session():
    return SessionLocal()

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())

# ---------- Fonction d'envoi d'email ----------
def send_email(to_email, subject, body):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not smtp_user:
        st.warning("Configuration email manquante. Veuillez définir les variables d'environnement.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erreur d'envoi : {e}")
        return False

# ---------- Initialisation démo (avec admin par défaut) ----------
def init_demo_company():
    session = get_session()
    if session.query(Entreprise).count() == 0:
        entreprise = Entreprise(nom="EasyGestion Demo")
        session.add(entreprise)
        session.flush()
        admin = Utilisateur(
            entreprise_id=entreprise.id,
            nom="Administrateur",
            email="admin@demo.com",
            mot_de_passe_hash=hash_password("admin123"),
            role="admin"
        )
        session.add(admin)
        # Ajouter un employé de démo
        employe = Utilisateur(
            entreprise_id=entreprise.id,
            nom="Employé",
            email="employe@demo.com",
            mot_de_passe_hash=hash_password("employe123"),
            role="employe"
        )
        session.add(employe)
        session.commit()
    session.close()

init_demo_company()

# ---------- Gestion de session ----------
if "connecte" not in st.session_state:
    st.session_state.connecte = False
if "entreprise_id" not in st.session_state:
    st.session_state.entreprise_id = None
if "user_nom" not in st.session_state:
    st.session_state.user_nom = ""
if "user_role" not in st.session_state:
    st.session_state.user_role = ""
if "theme" not in st.session_state:
    st.session_state.theme = "clair"

# ---------- Fonction pour basculer le thème ----------
def toggle_theme():
    if st.session_state.theme == "clair":
        st.session_state.theme = "sombre"
    else:
        st.session_state.theme = "clair"
    st.rerun()

# ---------- CSS pour mode sombre personnalisé ----------
def apply_theme():
    if st.session_state.theme == "sombre":
        st.markdown("""
            <style>
                .stApp {
                    background-color: #1E1E2E;
                    color: #CDD6F4;
                }
                .stSidebar {
                    background-color: #313244;
                }
                .css-1d391kg, .css-1d391kg * {
                    color: #CDD6F4 !important;
                }
                .stButton button {
                    background-color: #45475A !important;
                    color: #CDD6F4 !important;
                }
                .stTextInput, .stSelectbox, .stDateInput, .stNumberInput {
                    background-color: #313244 !important;
                    color: #CDD6F4 !important;
                }
                .metric-card {
                    background: #313244 !important;
                    color: #CDD6F4 !important;
                }
                .user-info {
                    background: #45475A !important;
                }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
                .stApp {
                    background-color: #F5F7FA;
                    color: #1E293B;
                }
                .stSidebar {
                    background-color: #FFFFFF;
                }
                .metric-card {
                    background: white !important;
                }
                .user-info {
                    background: #F1F5F9 !important;
                }
            </style>
        """, unsafe_allow_html=True)

# ============================================================
# AUTHENTIFICATION (ajout du rôle lors de la création)
# ============================================================
def page_connexion():
    st.markdown("""
        <style>
        .big-title { font-size: 48px; font-weight: 700; color: #1E88E5; text-align: center; }
        .sub-title { font-size: 20px; text-align: center; color: #64748B; margin-bottom: 30px; }
        .login-box { background: white; padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); max-width: 500px; margin: auto; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="big-title">📋 EasyGestion Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">La solution de gestion pour les pros</div>', unsafe_allow_html=True)

    choix = st.radio("Choisir", ["Connexion", "Créer mon entreprise"], horizontal=True)

    with st.container():
        if choix == "Connexion":
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="votre@email.com")
                password = st.text_input("Mot de passe", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Se connecter", use_container_width=True, type="primary")
                if submitted:
                    session = get_session()
                    user = session.query(Utilisateur).filter_by(email=email).first()
                    session.close()
                    if user and verify_password(password, user.mot_de_passe_hash):
                        st.session_state.connecte = True
                        st.session_state.entreprise_id = user.entreprise_id
                        st.session_state.user_nom = user.nom
                        st.session_state.user_role = user.role
                        st.toast("Bienvenue ! 🎉", icon="👋")
                        st.rerun()
                    else:
                        st.error("❌ Identifiants incorrects")
        else:
            with st.form("create_form"):
                entreprise = st.text_input("Nom de l'entreprise")
                nom = st.text_input("Votre nom")
                email = st.text_input("Email")
                password = st.text_input("Mot de passe", type="password")
                # L'utilisateur qui crée l'entreprise est automatiquement admin
                submitted = st.form_submit_button("Créer mon entreprise", use_container_width=True)
                if submitted:
                    if not (entreprise and nom and email and password):
                        st.error("Tous les champs sont obligatoires.")
                    else:
                        session = get_session()
                        if session.query(Utilisateur).filter_by(email=email).first():
                            st.error("Cet email est déjà utilisé.")
                        else:
                            new_ent = Entreprise(nom=entreprise)
                            session.add(new_ent)
                            session.flush()
                            new_user = Utilisateur(
                                entreprise_id=new_ent.id,
                                nom=nom,
                                email=email,
                                mot_de_passe_hash=hash_password(password),
                                role="admin"
                            )
                            session.add(new_user)
                            session.commit()
                            st.success("✅ Entreprise créée ! Vous pouvez vous connecter.")
                            st.balloons()
                        session.close()

# ============================================================
# PAGES PRINCIPALES (avec gestion des rôles)
# ============================================================

def est_admin():
    return st.session_state.user_role == "admin"

def dashboard():
    apply_theme()
    st.title("📊 Tableau de bord")
    ent_id = st.session_state.entreprise_id
    session = get_session()

    nb_clients = session.query(Client).filter_by(entreprise_id=ent_id).count()
    nb_rdv = session.query(RendezVous).filter_by(entreprise_id=ent_id).count()
    factures = session.query(Facture).filter_by(entreprise_id=ent_id).all()
    ca = sum(f.montant for f in factures if f.statut == "Payée")
    ca_attente = sum(f.montant for f in factures if f.statut == "En attente")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
            <div class="metric-card" style="border-left-color: #3B82F6; padding:20px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05); text-align:center;">
                <div style="font-size:32px; font-weight:700;">{nb_clients}</div>
                <div style="font-size:14px; color:#64748B;">👥 Clients</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="metric-card" style="border-left-color: #8B5CF6; padding:20px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05); text-align:center;">
                <div style="font-size:32px; font-weight:700;">{nb_rdv}</div>
                <div style="font-size:14px; color:#64748B;">📅 Rendez-vous</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div class="metric-card" style="border-left-color: #10B981; padding:20px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05); text-align:center;">
                <div style="font-size:32px; font-weight:700;">{ca:.2f} €</div>
                <div style="font-size:14px; color:#64748B;">💰 Chiffre d'affaires (payé)</div>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
            <div class="metric-card" style="border-left-color: #F59E0B; padding:20px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05); text-align:center;">
                <div style="font-size:32px; font-weight:700;">{ca_attente:.2f} €</div>
                <div style="font-size:14px; color:#64748B;">⏳ En attente de paiement</div>
            </div>
        """, unsafe_allow_html=True)

    # Graphiques (inchangés)
    if nb_rdv > 0:
        rdvs = session.query(RendezVous).filter_by(entreprise_id=ent_id).all()
        df_rdv = pd.DataFrame([(r.date, 1) for r in rdvs], columns=["date", "count"])
        df_rdv["mois"] = pd.to_datetime(df_rdv["date"]).dt.to_period("M").astype(str)
        df_rdv = df_rdv.groupby("mois").sum().reset_index()
        if not df_rdv.empty:
            fig1 = px.bar(df_rdv, x="mois", y="count", title="Rendez-vous par mois", color_discrete_sequence=["#3B82F6"])
            fig1.update_layout(plot_bgcolor="white" if st.session_state.theme=="clair" else "#1E1E2E",
                               paper_bgcolor="white" if st.session_state.theme=="clair" else "#1E1E2E",
                               font_color="#1E293B" if st.session_state.theme=="clair" else "#CDD6F4")
            st.plotly_chart(fig1, use_container_width=True)

    if ca > 0 or ca_attente > 0:
        df_ca = pd.DataFrame([(f.date_emission, f.montant, f.statut) for f in factures],
                             columns=["date", "montant", "statut"])
        if not df_ca.empty:
            df_ca["mois"] = pd.to_datetime(df_ca["date"]).dt.to_period("M").astype(str)
            df_ca_group = df_ca.groupby(["mois", "statut"]).sum().reset_index()
            fig2 = px.bar(df_ca_group, x="mois", y="montant", color="statut", title="CA par mois et statut",
                          color_discrete_map={"Payée": "#10B981", "En attente": "#F59E0B", "Annulée": "#EF4444"})
            fig2.update_layout(plot_bgcolor="white" if st.session_state.theme=="clair" else "#1E1E2E",
                               paper_bgcolor="white" if st.session_state.theme=="clair" else "#1E1E2E",
                               font_color="#1E293B" if st.session_state.theme=="clair" else "#CDD6F4")
            st.plotly_chart(fig2, use_container_width=True)

    session.close()

# ============================================================
# GESTION DES CLIENTS (UNIQUE VERSION AVEC UPLOAD)
# ============================================================
def gestion_clients():
    apply_theme()
    st.title("👥 Clients")
    
    ent_id = st.session_state.entreprise_id
    session = get_session()
    
    # ============================================================
    # 📥 TÉLÉCHARGER UN MODÈLE (CSV et Excel)
    # ============================================================
    with st.expander("📥 Télécharger un modèle de fichier", expanded=False):
        st.markdown("""
        **Téléchargez le modèle qui vous convient :**  
        - **CSV** : ouvrable avec n'importe quel éditeur ou tableur.  
        - **Excel** : format classique.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = "Nom,Téléphone,Email\nDupont Jean,0612345678,jean.dupont@email.com\nMartin Sophie,0623456789,sophie.martin@email.com\nBernard Pierre,0634567890,pierre.bernard@email.com"
            st.download_button(
                label="📥 Télécharger le modèle (CSV)",
                data=csv_data,
                file_name="clients_exemple.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            df_modele = pd.DataFrame({
                "Nom": ["Dupont Jean", "Martin Sophie", "Bernard Pierre"],
                "Téléphone": ["0612345678", "0623456789", "0634567890"],
                "Email": ["jean.dupont@email.com", "sophie.martin@email.com", "pierre.bernard@email.com"]
            })
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_modele.to_excel(writer, index=False, sheet_name="Clients")
            st.download_button(
                label="📥 Télécharger le modèle (Excel)",
                data=output.getvalue(),
                file_name="clients_exemple.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    # ============================================================
    # 📂 IMPORTER DES CLIENTS (TOUS LES FORMATS)
    # ============================================================
    uploaded_file = st.file_uploader(
        "Choisissez votre fichier",
        type=None,
        key="import_clients"
    )

    if uploaded_file is not None:
        df_import = None
        
        # ----- ESSAI 1 : LECTURE EXCEL (XLSX, XLS, ODS) -----
        for engine in ['openpyxl', 'xlrd', 'odf']:
            try:
                uploaded_file.seek(0)
                df_import = pd.read_excel(uploaded_file, engine=engine)
                st.info(f"✅ Fichier lu avec le moteur '{engine}'")
                break
            except Exception:
                continue
        
        # ----- ESSAI 2 : LECTURE CSV (si Excel a échoué) -----
        if df_import is None:
            try:
                uploaded_file.seek(0)
                raw = uploaded_file.read(1024).decode('utf-8', errors='ignore')
                uploaded_file.seek(0)
                sep = ';' if ';' in raw else ','
                df_import = pd.read_csv(uploaded_file, sep=sep, encoding='utf-8')
                st.info(f"✅ Fichier CSV lu avec séparateur '{sep}'")
            except Exception:
                try:
                    uploaded_file.seek(0)
                    df_import = pd.read_csv(uploaded_file, sep=None, engine='python')
                    st.info("✅ Fichier CSV lu (détection automatique)")
                except Exception as e:
                    st.error(f"❌ Impossible de lire le fichier. Détail : {e}")
                    df_import = None
        
        # ----- TRAITEMENT DES DONNÉES -----
        if df_import is not None and not df_import.empty:
            df_import.columns = df_import.columns.str.strip().str.lower()
            df_import.columns = df_import.columns.str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
            
            if 'nom' in df_import.columns:
                rename_dict = {}
                if 'nom' in df_import.columns:
                    rename_dict['nom'] = 'Nom'
                if 'telephone' in df_import.columns:
                    rename_dict['telephone'] = 'Téléphone'
                if 'email' in df_import.columns:
                    rename_dict['email'] = 'Email'
                df_import.rename(columns=rename_dict, inplace=True)
                
                st.write("**Aperçu des données :**")
                st.dataframe(df_import.head(10))
                
                if st.button("✅ Importer ces clients", use_container_width=True):
                    with st.spinner("Importation en cours..."):
                        count = 0
                        for _, row in df_import.iterrows():
                            nom = str(row.get("Nom", "")).strip()
                            if nom and nom != "nan":
                                tel = str(row.get("Téléphone", "")).strip()
                                email = str(row.get("Email", "")).strip()
                                
                                existant = session.query(Client).filter_by(
                                    entreprise_id=ent_id,
                                    nom=nom
                                ).first()
                                if not existant:
                                    client = Client(
                                        entreprise_id=ent_id,
                                        nom=nom,
                                        telephone=tel if tel and tel != "nan" else None,
                                        email=email if email and email != "nan" else None
                                    )
                                    session.add(client)
                                    count += 1
                        session.commit()
                        st.success(f"✅ {count} clients importés !")
                        st.rerun()
            else:
                st.error("❌ Colonne 'Nom' introuvable. Vérifie que ton fichier contient une colonne avec ce nom.")
        else:
            st.error("❌ Aucune donnée lue. Assure-toi que le fichier n'est pas vide.")
    
    # ============================================================
    # ➕ AJOUTER UN CLIENT (manuel)
    # ============================================================
    with st.expander("➕ Ajouter un client (manuel)", expanded=False):
        with st.form("add_client"):
            nom = st.text_input("Nom *")
            tel = st.text_input("Téléphone")
            email = st.text_input("Email")
            submitted = st.form_submit_button("Ajouter", use_container_width=True)
            if submitted:
                if not nom:
                    st.error("Le nom est requis.")
                else:
                    existant = session.query(Client).filter_by(
                        entreprise_id=ent_id,
                        nom=nom
                    ).first()
                    if existant:
                        st.warning("⚠️ Ce client existe déjà.")
                    else:
                        client = Client(entreprise_id=ent_id, nom=nom, telephone=tel, email=email)
                        session.add(client)
                        session.commit()
                        st.toast("✅ Client ajouté", icon="✅")
                        st.rerun()

    # ============================================================
    # 🔍 RECHERCHE ET AFFICHAGE
    # ============================================================
    st.divider()
    search = st.text_input("🔍 Rechercher un client", placeholder="Nom ou email")
    query = session.query(Client).filter_by(entreprise_id=ent_id)
    if search:
        query = query.filter(Client.nom.contains(search) | Client.email.contains(search))
    clients = query.all()

    st.write(f"**Total :** {len(clients)} client(s)")

    if not clients:
        st.info("Aucun client trouvé")
    else:
        for c in clients:
            col1, col2, col3, col4 = st.columns([3, 3, 3, 1])
            with col1:
                st.write(f"**{c.nom}**")
            with col2:
                st.write(c.telephone or "—")
            with col3:
                st.write(c.email or "—")
            with col4:
                if est_admin():
                    if st.button("🗑️", key=f"del_client_{c.id}"):
                        session.delete(c)
                        session.commit()
                        st.toast(f"Client {c.nom} supprimé", icon="🗑️")
                        st.rerun()

    # ============================================================
    # 📤 EXPORTER LES CLIENTS EN EXCEL ET CSV
    # ============================================================
    if clients:
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Exporter en Excel", use_container_width=True):
                data = [{"Nom": c.nom, "Téléphone": c.telephone or "", "Email": c.email or ""} for c in clients]
                df_export = pd.DataFrame(data)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_export.to_excel(writer, index=False, sheet_name="Clients")
                st.download_button(
                    label="Télécharger .xlsx",
                    data=output.getvalue(),
                    file_name=f"clients_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        with col2:
            if st.button("📤 Exporter en CSV", use_container_width=True):
                data = [{"Nom": c.nom, "Téléphone": c.telephone or "", "Email": c.email or ""} for c in clients]
                df_export = pd.DataFrame(data)
                csv = df_export.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    label="Télécharger .csv",
                    data=csv,
                    file_name=f"clients_{date.today()}.csv",
                    mime="text/csv"
                )

    session.close()

# ============================================================
# GESTION DES RENDEZ-VOUS
# ============================================================
def gestion_rendezvous():
    apply_theme()
    st.title("📅 Rendez-vous")
    ent_id = st.session_state.entreprise_id
    session = get_session()

    # --- Calendrier interactif avec streamlit-calendar ---
    try:
        from streamlit_calendar import calendar
        rdvs = session.query(RendezVous).filter_by(entreprise_id=ent_id).all()
        events = []
        for rdv in rdvs:
            events.append({
                "title": rdv.client_nom,
                "start": f"{rdv.date} {rdv.heure.strftime('%H:%M')}",
                "end": f"{rdv.date} {rdv.heure.strftime('%H:%M')}",
                "allDay": False,
            })
        if events:
            st.subheader("📆 Vue mensuelle")
            calendar(events=events, options={
                "initialView": "dayGridMonth",
                "headerToolbar": {
                    "left": "prev,next today",
                    "center": "title",
                    "right": "dayGridMonth,timeGridWeek,timeGridDay"
                },
                "editable": False,
                "selectable": False,
            })
    except ImportError:
        st.info("Installez 'streamlit-calendar' pour un calendrier interactif.")

    # --- Ajout rendez-vous ---
    with st.expander("➕ Ajouter un rendez-vous", expanded=False):
        with st.form("add_rdv"):
            client_nom = st.text_input("Nom du client *")
            date_rdv = st.date_input("Date", value=date.today())
            heure_rdv = st.time_input("Heure", value=datetime.now().time())
            send_email_rdv = st.checkbox("Envoyer un email de rappel au client (si email connu)")
            submitted = st.form_submit_button("Ajouter")
            if submitted:
                if not client_nom:
                    st.error("Nom requis.")
                else:
                    rdv = RendezVous(entreprise_id=ent_id, client_nom=client_nom, date=date_rdv, heure=heure_rdv)
                    session.add(rdv)
                    session.commit()
                    st.toast("✅ Rendez-vous ajouté", icon="✅")
                    if send_email_rdv:
                        client = session.query(Client).filter_by(entreprise_id=ent_id, nom=client_nom).first()
                        if client and client.email:
                            subject = f"Rappel de rendez-vous - {client_nom}"
                            body = f"Bonjour {client_nom},\n\nVotre rendez-vous est prévu le {date_rdv.strftime('%d/%m/%Y')} à {heure_rdv.strftime('%H:%M')}.\n\nCordialement,\nEasyGestion Pro"
                            if send_email(client.email, subject, body):
                                st.success("📧 Email de rappel envoyé !")
                            else:
                                st.warning("Échec de l'envoi de l'email.")
                        else:
                            st.warning("Aucun email trouvé pour ce client.")
                    st.rerun()

    # --- Filtres et liste ---
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
            col1, col2, col3, col4, col5 = st.columns([2,2,2,1,1])
            with col1:
                st.write(f"👤 **{rdv.client_nom}**")
            with col2:
                st.write(f"📅 {rdv.date.strftime('%d/%m/%Y')}")
            with col3:
                st.write(f"⏰ {rdv.heure.strftime('%H:%M')}")
            with col4:
                if st.button("📧", key=f"email_rdv_{rdv.id}"):
                    client = session.query(Client).filter_by(entreprise_id=ent_id, nom=rdv.client_nom).first()
                    if client and client.email:
                        subject = f"Rappel de rendez-vous - {rdv.client_nom}"
                        body = f"Bonjour {rdv.client_nom},\n\nVotre rendez-vous est prévu le {rdv.date.strftime('%d/%m/%Y')} à {rdv.heure.strftime('%H:%M')}.\n\nCordialement,\nEasyGestion Pro"
                        if send_email(client.email, subject, body):
                            st.success("📧 Email envoyé !")
                        else:
                            st.error("Erreur d'envoi.")
                    else:
                        st.warning("Aucun email trouvé.")
            with col5:
                if est_admin():
                    if st.button("🗑️", key=f"del_rdv_{rdv.id}"):
                        session.delete(rdv)
                        session.commit()
                        st.toast(f"Rendez-vous de {rdv.client_nom} supprimé", icon="🗑️")
                        st.rerun()
    session.close()

# ============================================================
# GESTION DES FACTURES (fonction vide pour éviter erreur)
# ============================================================
def gestion_factures():
    apply_theme()
    st.title("🧾 Factures")
    st.info("Module Factures en cours de développement...")
    # Vous pouvez implémenter ici la gestion des factures (création, affichage, etc.)

# ============================================================
# SIDEBAR (avec thème et rôle)
# ============================================================
def sidebar():
    with st.sidebar:
        st.markdown("""
            <style>
                .sidebar-title { font-size: 22px; font-weight: 700; color: #1E88E5; }
                .user-info { background: #F1F5F9; padding: 15px; border-radius: 12px; text-align: center; }
                .user-avatar { font-size: 48px; }
                .theme-toggle { margin-top: 20px; }
            </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sidebar-title">📋 EasyGestion Pro</div>', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="user-info">
                <div class="user-avatar">👤</div>
                <div style="font-weight:600;">{st.session_state.user_nom}</div>
                <div style="font-size:12px;color:#64748B;">Rôle : {st.session_state.user_role}</div>
                <div style="font-size:12px;color:#64748B;">Entreprise ID: {st.session_state.entreprise_id}</div>
            </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Déconnexion", use_container_width=True):
            st.session_state.connecte = False
            st.session_state.entreprise_id = None
            st.session_state.user_nom = ""
            st.session_state.user_role = ""
            st.rerun()

        st.divider()

        menu = st.radio(
            "Navigation",
            ["🏠 Tableau de bord", "👥 Clients", "📅 Rendez-vous", "🧾 Factures"],
            index=0,
            key="menu"
        )

        st.divider()

        st.markdown("### 🌙 Thème")
        if st.button("Changer de thème" if st.session_state.theme == "clair" else "Changer de thème (clair)", use_container_width=True):
            toggle_theme()

        return menu

# ============================================================
# MAIN
# ============================================================
def main():
    if not st.session_state.connecte:
        page_connexion()
        return

    apply_theme()
    menu = sidebar()

    if menu == "🏠 Tableau de bord":
        dashboard()
    elif menu == "👥 Clients":
        gestion_clients()
    elif menu == "📅 Rendez-vous":
        gestion_rendezvous()
    elif menu == "🧾 Factures":
        gestion_factures()

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #94A3B8; font-size: 12px;'>"
        "© 2025 EasyGestion Pro – Tous droits réservés"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
