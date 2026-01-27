#Interfaccia: streamlit, streamlit_authenticator

#Dati: pandas, json, yaml

#Database & Cloud: appwrite (Client, Databases, ID, Query, Storage, InputFile)

#Grafica: plotly.express

#Tempo: time, datetime, date

import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import streamlit as st
import pandas as pd
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.id import ID
from appwrite.query import Query
import time
from appwrite.services.storage import Storage # <--- Aggiungi questa importazione
from appwrite.input_file import InputFile     # <--- E questa
import plotly.express as px
import json
import os
from datetime import datetime, date, timedelta
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import calendar
import subprocess # Serve per lanciare i programmi di sistema


# --- LOGICA DI ACCESSO ---
if 'autenticato' not in st.session_state:
    st.session_state.autenticato = False

def login():
    st.title("🔐 Accesso Family Hub")
    user = st.text_input("Username").lower() # Portiamo tutto in minuscolo per evitare errori
    password = st.text_input("Password", type="password")
    
    if st.button("Entra"):
        # Recuperiamo il dizionario degli utenti dai secrets
        utenti = st.secrets["utenti"]
        
        # Controlliamo se l'utente esiste e se la password è corretta
        if user in utenti and password == utenti[user]:
            st.session_state.autenticato = True
            st.session_state.user_nome = user # Salviamo chi è entrato
#------------------------------------------------------------------------------
# togliamo perde solo tempo e resta fantasma dopo il login
#            st.success(f"Benvenuto {user.capitalize()}!")
#            time.sleep(1)
#------------------------------------------------------------------------------
            st.rerun()
        else:
            st.error("Credenziali non valide")

if not st.session_state.autenticato:
    login()
    st.stop() # FERMA TUTTO QUI SE NON SEI LOGGATO

# --- DA QUI IN POI PARTE IL TUO CODICE ATTUALE ---
# (Tutto quello che avevi già: sidebar, logo, calcoli, ecc.)

st.set_page_config(page_title="Family Hub", layout="wide", page_icon="🏠")

# 3. RECUPERO NOME (Mettilo qui!)
# Cerchiamo il nome nel session_state, se non c'è usiamo "Socio"
nome_utente = st.session_state.get("name", "Socio")
nome_fresco = nome_utente.split()[0] # Prende solo il primo nome

# 2. Connessione ad Appwrite
client = Client()
client.set_endpoint(st.secrets["appwrite"]["endpoint"])
client.set_project(st.secrets["appwrite"]["project_id"])
client.set_key(st.secrets["appwrite"]["api_key"])

db = Databases(client)
storage = Storage(client)

BUCKET_ID = st.secrets["appwrite"]["bucket_id"]
DB_ID = st.secrets["appwrite"]["db_id"]
COL_PROP = st.secrets["appwrite"]["col_proprieta_id"]
COL_SPESE = st.secrets["appwrite"]["col_spese_id"]
PROJECT_ID = st.secrets["appwrite"]["project_id"]
COL_ALLEGATI=st.secrets["appwrite"]["col_allegati_spese_id"]
COL_RIPARTIZIONI_ID = st.secrets["appwrite"]["col_ripartizioni_id"]
COL_MANUT_ID = st.secrets["appwrite"]["col_manutenzione_id"]
COL_MANUT_REG_ID = st.secrets["appwrite"]["col_manutenzione_regole_id"]
COL_DOCUMENTI_REG_ID = st.secrets["appwrite"]["col_documenti_registro_id"]
COL_RUBRICA_ID = st.secrets["appwrite"]["col_rubrica_id"]

def mostra_riepilogo_tasks(service):
    st.write("### 📝 Promemoria Attivi")
    
    try:
        # 1. Recuperiamo la lista "Family Hub: Da Fare"
        lists = service.tasklists().list().execute()
        list_id = next((l['id'] for l in lists['items'] if l['title'] == 'Family Hub: Da Fare'), None)
        
        if list_id:
            # 2. Leggiamo i task non completati
            tasks = service.tasks().list(tasklist=list_id, showCompleted=False).execute()
            items = tasks.get('items', [])
            
            if not items:
                st.info(f"✅ {nome_fresco}, tutto pulito! Goditi il caffè. ☕")
            else:
                for t in items:
                    # --- LOGICA DATA (Formato gg/mm/aaaa) ---
                    due_date_str = ""
                    if 'due' in t:
                        # Convertiamo il formato Google in oggetto datetime e poi in stringa ITA
                        d = datetime.strptime(t['due'], '%Y-%m-%dT%H:%M:%S.%fZ')
                        due_date_str = f" 📅 *({d.strftime('%d/%m/%Y')})*"
                    
                    # --- VISUALIZZAZIONE CON ICONE E BOTTONI ---
                    col_testo, col_bottone = st.columns([0.8, 0.2])
                    
                    with col_testo:
                        # Se il titolo contiene "MANUTENZIONE", lo coloriamo e mettiamo l'alert
                        if "MANUTENZIONE" in t['title']:
                            st.markdown(f"⚠️ **:red[{t['title']}]** {due_date_str}")
                        else:
                            # Altrimenti icona standard 📌
                            st.write(f"📌 {t['title']} {due_date_str}")
                        
                        # Se ci sono note, le mostriamo piccole sotto
                        if t.get('notes'):
                            st.caption(f"ℹ️ {t['notes']}")

                    with col_bottone:
                        # Il bottone magico per completare il task
                        # Usiamo l'ID del task come chiave unica
                        if st.button("Fatto! ✅", key=f"btn_home_{t['id']}"):
                            service.tasks().patch(tasklist=list_id, task=t['id'], body={'status': 'completed'}).execute()
                            st.toast(f"Ottimo lavoro per la Proprietà!")
                            st.rerun()
                    
                    st.divider()
        else:
            st.warning("Lista 'Family Hub' non trovata su Google.")
            
    except Exception as e:
        st.error(f"Errore nel recupero Task: {e}")

# DEFINIAMO LA FUNZIONE CHE MANCAVA
def get_tasks_service():
    creds = None
    # Cerca il file token.pickle che hai appena caricato
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Usa il file credentials.json che hai appena caricato
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', ['https://www.googleapis.com/auth/tasks'])
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('tasks', 'v1', credentials=creds)

def inizializza_google_tasks():
    service = get_tasks_service() # La funzione che abbiamo testato prima
    
    # 1. Cerchiamo se esiste già la nostra lista
    results = service.tasklists().list().execute()
    liste = results.get('items', [])
    
    id_lista_family = None
    for lista in liste:
        if lista['title'] == "Family Hub: Da Fare":
            id_lista_family = lista['id']
            break
            
    # 2. Se non esiste, la creiamo noi!
    if not id_lista_family:
        nuova_lista = {'title': 'Family Hub: Da Fare'}
        creata = service.tasklists().insert(body=nuova_lista).execute()
        id_lista_family = creata['id']
        print(f"✨ Nuova lista creata con ID: {id_lista_family}")
    
    return service, id_lista_family

def aggiungi_task_family(titolo, scadenza=None):
    # 1. Inizializziamo il servizio e la lista
    service, list_id = inizializza_google_tasks()
    
    # 2. LOGICA SCADENZA: Se 'scadenza' è fornita, usa quella. Altrimenti calcola fine mese.
    if scadenza:
        data_scadenza = scadenza
    else:
        # Questo è il tuo calcolo originale per la fine del mese
        oggi = datetime.now()
        ultimo_giorno = calendar.monthrange(oggi.year, oggi.month)[1]
        data_scadenza = f"{oggi.year}-{oggi.month:02d}-{ultimo_giorno:02d}T09:00:00Z"
    
    # 3. Creiamo il corpo del task (Attenzione: usa 'titolo' che è il parametro della funzione)
    task_corpo = {
        'title': titolo,
        'due': data_scadenza
    }
    
    # 4. Invio a Google
    service.tasks().insert(tasklist=list_id, body=task_corpo).execute()
    
    return f"✅ Task '{titolo}' aggiunto alla Proprietà!"


def ottieni_lista_task():
    service, list_id = inizializza_google_tasks()
    
    # Chiediamo a Google i task di quella lista specifica
    results = service.tasks().list(tasklist=list_id, showCompleted=False).execute()
    tasks = results.get('items', [])
    
    return tasks


def completa_task_family(task_id):
    service, list_id = inizializza_google_tasks()
    # Per Google, 'completare' significa aggiornare lo stato in 'completed'
    task = service.tasks().get(tasklist=list_id, task=task_id).execute()
    task['status'] = 'completed'
    service.tasks().update(tasklist=list_id, task=task_id, body=task).execute()

def genera_task_manutenzione():
    # 1. Recupero dati
    # st.warning("⚠️ ATTENZIONE: Funzione avviata!") # Se non vedi questo, la funzione non parte proprio
    mese_corrente = datetime.now().month
    regole = carica_regole_manutenzione() 
    lista_esistente = ottieni_lista_task()
    nomi_task_esistenti = [t['title'] for t in lista_esistente]
    
    # --- SENSORI DI LIVELLO 1 ---
    #st.write(f"DEBUG: Regole scaricate: {len(regole)}") 
    #print(f"DEBUG LOG: Numero regole nella Proprietà: {len(regole)}")
    
    compiti_aggiunti = 0

    # 2. Ciclo di controllo
    for r in regole:
    #    st.write(f"Controllo regola: {r.get('compito')} - Mesi: '{r.get('mesi')}' - Attiva: {r.get('attiva')}")
        if not r.get('attiva', True): 
            continue 
        
        try:
            # Pulizia totale: togliamo spazi e trasformiamo in lista
            valore_mesi = str(r.get('mesi', ''))
            stringa_pulita = valore_mesi.replace(' ', '')
            
            # Creiamo la lista di numeri
            mesi_regola = [int(m) for m in stringa_pulita.split(',') if m.strip().isdigit()]
            
            # --- IL SENSORE DEFINITIVO ---
            # Questo ti mostrerà a video cosa sta succedendo riga per riga
            #st.info(f"Controllo '{r['compito']}': Cerco il mese {mese_corrente} in {mesi_regola}")
            
            if mese_corrente in mesi_regola:
                titolo_nuovo = f"MANUTENZIONE: {r['compito']} {r['icona']}"
                
                if titolo_nuovo not in nomi_task_esistenti:
                    aggiungi_task_family(titolo_nuovo)
                    compiti_aggiunti += 1
                    
        except Exception as e:
            st.error(f"Errore nella regola {r.get('compito')}: {e}")
            
    return compiti_aggiunti

@st.cache_data(ttl=300)  # Conserva i dati per 5 minuti (300 secondi)
def carica_regole_manutenzione():
    # Usiamo 'db' invece di 'databases'
    risposta = db.list_documents( 
        database_id=DB_ID, 
        collection_id=COL_MANUT_REG_ID
    )
    return risposta['documents']



#@st.cache_data(ttl=300)  # Conserva i dati per 5 minuti (300 secondi)
# --- FUNZIONE PER LEGGERE DA APPWRITE ---
# 🚨 COMMENTA O TOGLI LA CACHE PER ORA: @st.cache_data(ttl=300)
def carica_rubrica_appwrite():
    try:
        # Forziamo la pulizia della cache ad ogni chiamata per sicurezza
        st.cache_data.clear() 
        
        response = db.list_documents(
            database_id=DB_ID,
            collection_id=COL_RUBRICA_ID
        )
        
        # Se non ci sono documenti, DataFrame vuoto con colonne pulite
        if not response['documents']:
            return pd.DataFrame(columns=['nominativo', 'specializzazione', 'indirizzo', 'telefono'])
        
        df = pd.DataFrame(response['documents'])
        
        # ✅ Prendiamo le colonne che ci servono + l'$id (che ci serve internamente per le pulizie)
        # Se l'id non c'è ancora (perché il DB è vuoto), lo gestiamo
        cols_base = ['nominativo', 'specializzazione', 'indirizzo', 'telefono']
        available_cols = [c for c in cols_base if c in df.columns]
        
        # Se vogliamo essere super sicuri per il data_editor:
        df_pulito = df[available_cols].copy()
        
        # Aggiungiamo l'id solo se esiste, ma lo terremo "nascosto" o lo useremo solo per i calcoli
        if '$id' in df.columns:
            df_pulito['$id'] = df['$id']
            
        return df_pulito
        
    except Exception as e:
        return pd.DataFrame(columns=['nominativo', 'specializzazione', 'indirizzo', 'telefono'])

def gestione_rubrica_artigiani():
    st.header("📞 Rubrica Artigiani di Riferimento")
    
    # 1. Caricamento dati (Session State)
    if "df_rubrica" not in st.session_state:
        st.session_state.df_rubrica = carica_rubrica_appwrite()

    # --- PREPARAZIONE COLONNE LINK ---
    df_visualizzazione = st.session_state.df_rubrica.copy()
    
    def prepara_whatsapp(row):
        tel = row.get('telefono')
        nome = row.get('nominativo', 'Artigiano')
        if pd.isna(tel) or str(tel).strip() == "": return ""
        num = "".join(filter(str.isdigit, str(tel)))
        messaggio = f"Ciao {nome}, sono Roberto della Proprietà. Avrei bisogno di un intervento..."
        return f"https://wa.me/{num}?text={messaggio.replace(' ', '%20')}"

    # Creazione colonne virtuali
    df_visualizzazione['Chiama'] = df_visualizzazione['telefono'].apply(
        lambda x: f"tel:{str(x).replace(' ', '')}" if pd.notnull(x) and str(x).strip() != "" else ""
    )
    df_visualizzazione['WA'] = df_visualizzazione.apply(prepara_whatsapp, axis=1)

    # 2. IL FORM (Fondamentale: racchiude Editor e Bottone)
    with st.form("form_gestione_artigiani"):
        st.subheader("📝 Modifica e Contatta")
        
        df_editabile = st.data_editor(
            df_visualizzazione,
            column_config={
                "specializzazione": st.column_config.SelectboxColumn(
                    "Specializzazione", options=["Idraulico", "Elettricista", "Caldaista", "Muratore", "Piastrellista", "Altro"]
                ),
                "telefono": st.column_config.TextColumn("Telefono"),
                "Chiama": st.column_config.LinkColumn("📞", display_text="📞 Chiama"),
                "WA": st.column_config.LinkColumn("💬", display_text="💬 WA")
            },
            column_order=("nominativo", "specializzazione", "indirizzo", "telefono", "Chiama", "WA"),
            num_rows="dynamic",
            use_container_width=True,
            key="editor_rubrica_vfinal"
        )
        
        # Il bottone DEVE stare dentro il form
        submit = st.form_submit_button("💾 Salva modifiche nella Proprietà")

    # 3. LOGICA DI SALVATAGGIO (Fuori dal form, scatta dopo il submit)
    if submit:
        with st.spinner("Sincronizzazione della Proprietà..."):
            try:
                # A. CANCELLAZIONE TOTALE
                st.cache_data.clear()
                df_db_attuale = carica_rubrica_appwrite()
                if not df_db_attuale.empty:
                    for _, row in df_db_attuale.iterrows():
                        if '$id' in row:
                            db.delete_document(DB_ID, COL_RUBRICA_ID, row['$id'])

                # B. RE-INSERIMENTO PULITO
                for _, row in df_editabile.iterrows():
                    nome = str(row.get('nominativo', '')).strip()
                    if nome == "" or nome.lower() == "none": 
                        continue
                    
                    data_da_inviare = {
                        "nominativo": nome,
                        "specializzazione": str(row.get("specializzazione", "Altro")),
                        "indirizzo": str(row.get("indirizzo", "")),
                        "telefono": str(row.get("telefono", ""))
                    }
                    db.create_document(DB_ID, COL_RUBRICA_ID, 'unique()', data_da_inviare)
                
                # C. RESET E REFRESH
                if "df_rubrica" in st.session_state:
                    del st.session_state.df_rubrica
                
                st.cache_data.clear()
                st.success("Rubrica aggiornata correttamente! ✨")
                st.rerun()
                
            except Exception as e:
                st.error(f"Errore durante il salvataggio: {e}")

def aggiorna_regole_manutenzione(df_editato):
    for index, row in df_editato.iterrows():
        data = {
            "compito": row['compito'],
            "mesi": str(row['mesi']),
            "icona": row['icona'],
            "attiva": bool(row['attiva'])
        }
        
        document_id = row.get('$id')
        
        if pd.isna(document_id) or document_id is None:
            # Usiamo 'db' come nel resto dell'app
            db.create_document(
                database_id=DB_ID,
                collection_id=COL_MANUT_REG_ID,
                document_id="unique()",
                data=data
            )
            
        else:
            # Usiamo 'db' anche qui
            db.update_document(
                database_id=DB_ID,
                collection_id=COL_MANUT_REG_ID,
                document_id=document_id,
                data=data
            )
    # ✅ METTILA QUI: Una volta sola, dopo che il ciclo ha finito tutto il lavoro
    st.cache_data.clear()
    st.success("Regole della Proprietà aggiornate!")        


def data_ultimo_giorno_mese():
    oggi = datetime.now()
    # Trova l'ultimo giorno del mese corrente
    ultimo_giorno = calendar.monthrange(oggi.year, oggi.month)[1]
    # Formato richiesto da Google Tasks: 2026-01-31T23:59:59Z
    return f"{oggi.year}-{oggi.month:02d}-{ultimo_giorno:02d}T09:00:00Z"



# Recupero ID dai Secrets
COL_DOC_REGISTRO = st.secrets["appwrite"]["col_documenti_registro_id"]
BUCKET_ID = st.secrets["appwrite"]["bucket_id"]
PROJECT_ID = st.secrets["appwrite"]["project_id"]


def sezione_documenti_immobili():
    st.subheader("🏛️ Caveau Documenti della Proprietà")
    st.info("Una volta fatta la scansione, salva il PDF e trascinalo nel box qui sotto.")
    # --- PARTE 1: CARICAMENTO ---
    with st.expander("➕ Carica Nuovo Documento (Contratti, Planimetrie, etc.)"):
        c1, c2 = st.columns(2)
        nome_doc = c1.text_input("Nome Documento", placeholder="es. Contratto Affitto 2026")
        cat_doc = c2.selectbox("Categoria", ["Contratti", "Planimetrie", "Certificazioni", "Assicurazioni", "Altro"])
        desc_doc = st.text_area("Descrizione breve (opzionale)")
        
        up_file = st.file_uploader("Trascina qui il file", type=['pdf', 'jpg', 'png', 'jpeg', 'xlsx', 'docx'], key="up_doc_casa")
        
        if st.button("ARCHIVIA DOCUMENTO 📁"):
            if up_file and nome_doc:
                # A. Caricamento fisico nello Storage (Ricicliamo il Bucket Spese)
                new_f = storage.create_file(
                    bucket_id=BUCKET_ID,
                    file_id=ID.unique(),
                    file=InputFile.from_bytes(up_file.getvalue(), filename=up_file.name)
                )
                
                # B. Record nel Database (Tabella documenti_registro)
                # Usiamo il formato ISO per il campo datetime di Appwrite
                data_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
                
                db.create_document(DB_ID, COL_DOC_REGISTRO, ID.unique(), {
                    "nome": nome_doc,
                    "categoria": cat_doc,
                    "file_id": str(new_f["$id"]),
                    "descrizione": desc_doc,
                    "data_inserimento": data_iso
                })
                st.cache_data.clear()
                st.success(f"Documento '{nome_doc}' archiviato con successo!")
                time.sleep(1.5)
                st.rerun()
            else:
                st.warning("⚠️ Inserisci almeno il nome e seleziona un file.")

    st.divider()

    # --- PARTE 2: VISUALIZZAZIONE ---
    st.write("### 🔍 Documenti Archiviati")
    docs_res = db.list_documents(DB_ID, COL_DOC_REGISTRO, [Query.order_desc("data_inserimento")])
    elenco_docs = docs_res['documents']

    if not elenco_docs:
        st.info("Nessun documento presente nell'archivio della Proprietà.")
    else:
        for d in elenco_docs:
            with st.container():
                col_info, col_btn = st.columns([4, 1])
                
                # Prepariamo l'URL magico
                url_view = f"https://cloud.appwrite.io/v1/storage/buckets/{BUCKET_ID}/files/{d['file_id']}/view?project={PROJECT_ID}"
                
                with col_info:
                    st.markdown(f"**{d['nome']}** ({d['categoria']})")
                    if d.get('descrizione'):
                        st.caption(f"📝 {d['descrizione']}")
                    st.caption(f"📅 Caricato il: {d['data_inserimento'][:10]}")
                
                with col_btn:
                    # Bottone Visualizza (Stesso stile delle spese)
                    st.link_button("Apri 📄", url_view, use_container_width=True)
                    
                    # Tasto Cancella
                    if st.button("🗑️", key=f"del_doc_{d['$id']}"):
                        storage.delete_file(BUCKET_ID, d['file_id'])
                        db.delete_document(DB_ID, COL_DOC_REGISTRO, d['$id'])
                        st.warning("Rimosso.")
                        time.sleep(1)
                        st.rerun()
                st.divider()


# --- MENU LATERALE ---
def genera_riepilogo_pdf(periodo, prop_nome, dati_tabella, totale_bolletta):
    # 1. Inizio Template (Parte fissa superiore)
    html_template = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #eee; max-width: 800px; margin: auto;">
        <h1 style="color: #2E7D32; border-bottom: 2px solid #2E7D32; padding-bottom: 10px;">💧 Riepilogo Ripartizione Acqua</h1>
        <div style="margin-bottom: 20px;">
            <p><strong>Immobile:</strong> {prop_nome}</p>
            <p><strong>Periodo:</strong> {periodo}</p>
        </div>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background-color: #f2f2f2;">
                    <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Inquilino</th>
                    <th style="padding: 12px; border: 1px solid #ddd; text-align: right;">Consumo (mc)</th>
                    <th style="padding: 12px; border: 1px solid #ddd; text-align: right;">Quota (€)</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Inizializziamo il contatore per il controllo incrociato
    totale_mc_calcolato = 0.0
    
    # 2. Ciclo per aggiungere SOLO le righe degli inquilini
    for _, row in dati_tabella.iterrows():
        mc = float(row['totale_mc']) 
        quota = float(row['euro'])
        totale_mc_calcolato += mc
        
        html_template += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">{row['Inquilino']}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">{mc:.2f}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">{quota:.2f} €</td>
                </tr>
        """
    
    # 3. Parte finale (Fuori dal ciclo): Riga Totali, Chiusura Tabella e Footer
    html_template += f"""
                <tr style="background-color: #f9f9f9; font-weight: bold; border-top: 2px solid #2E7D32;">
                    <td style="padding: 12px; border: 1px solid #ddd; text-align: left;">TOTALE GENERALE</td>
                    <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">{totale_mc_calcolato:.2f} mc</td>
                    <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">{totale_bolletta:.2f} €</td>
                </tr>
            </tbody>
        </table>

        <p style="margin-top: 20px; font-size: 0.9em; color: #555; font-style: italic; text-align: center;">
            Nota: I valori includono il bilanciamento delle eccedenze per allineamento alla bolletta condominiale.
        </p>
        
        <footer style="margin-top: 30px; font-size: 0.8em; color: #777; text-align: center; border-top: 1px solid #eee; padding-top: 10px;">
            Generato automaticamente dal Sistema Gestionale **Hub Family** - {datetime.now().strftime('%d/%m/%Y')}
        </footer>
    </div>
    """
    return html_template


def pagina_ripartizione_acqua():
    st.title("💧 Ripartizione Spese Acqua")

    tab1, tab2 = st.tabs(["📝 Nuova Ripartizione", "📜 Storico e Ristampa"])

    with tab1:
        # --- 1. SELEZIONE PROPRIETÀ (Logica identica a Gestione Spese) ---
        st.info("Configura una nuova ripartizione per la tua **Proprietà**.")
        try:
            # Recuperiamo i documenti
            lista_prop = db.list_documents(database_id=DB_ID, collection_id=COL_PROP)
            import pandas as pd
            df_p = pd.DataFrame(lista_prop['documents'])
            
            if df_p.empty:
                st.warning("Nessuna **Proprietà** trovata nel database.")
                return

            # USIAMO I TUOI CAMPI: 'nome' e 'indirizzo_completo'
            df_p["label"] = df_p["nome"] + " - " + df_p["indirizzo_completo"]
            
            # Creiamo la mappa ETICHETTA -> ID
            mappa_id = dict(zip(df_p["label"], df_p["$id"]))
            
            # IL SELETTORE (usiamo la variabile 'prop_selezionata' per evitare NameError)
            prop_selezionata = st.selectbox(
                "A quale Immobile si riferisce la bolletta?", 
                options=df_p["label"].tolist()
            )
            
            # Recuperiamo l'ID reale
            prop_id_scelta = mappa_id[prop_selezionata]
            
            # Messaggio di conferma corretto
            st.info(f"Configurato per: **{prop_selezionata}**")
                
        except Exception as e:
            st.error(f"Errore nel recupero degli Immobili : {e}")
            return
        

        # --- 2. RESTO DEL CODICE (Senza riga fantasma!) ---
        # (Qui prosegui con il container della bolletta e i consumi...)
        # --- 2. RESTO DEL CODICE ---
        
        # ❌ CANCELLA QUESTA RIGA QUI SOTTO (è quella che dà l'errore):
        # st.info(f"Calcolo per: **{prop_scelta_nome}**. La tua quota sarà registrata automaticamente.")

        # 2. Inserimento Dati Bolletta
        with st.container(border=True):
            st.subheader("📄 Dati Bolletta Generale")
            # ... (restante codice dei widget) ...
            col1, col2, col3 = st.columns(3)
            periodo = col1.text_input("Periodo", placeholder="es. Gen-Mar 2026")
            importo_tot = col2.number_input("Totale Bolletta (€)", min_value=0.0, step=0.01)
            mc_tot = col3.number_input("Metri Cubi Totali", min_value=0.1, step=0.1)
            costo_mc = importo_tot / mc_tot if mc_tot > 0 else 0
            st.write(f"Costo unitario: **{costo_mc:.4f} €/m³**")

        # ... (parte dei consumi inquilini) ...
        st.subheader("👥 Consumi Inquilini")
        df_input = pd.DataFrame({
            "Inquilino": ["Armellini Roberto", "Iovine Francesco", "Ciarpaglini Giacomo"], 
            "Metri Cubi": [0.0, 0.0, 0.0]
        })
        # 1. Creiamo la lista nomi (fondamentale!)
        # 1. Prepariamo i dati con la colonna Eccedenza
        inquilini_nomi = ["Armellini Roberto", "Iovine Francesco", "Ciarpaglini Giacomo"]
        df_input = pd.DataFrame({
            "Inquilino": ["Armellini Roberto", "Iovine Francesco", "Ciarpaglini Giacomo"], 
            "Lettura MC": [0.0, 0.0, 0.0],  # <--- Cambiato nome
            "Eccedenza MC": [0.0, 0.0, 0.0] # <--- Aggiunta colonna
        })

        # 2. Key NUOVA per resettare la memoria di Streamlit
        edit_consumi = st.data_editor(df_input, use_container_width=True, hide_index=True, key="editor_acqua_con_eccedenza")

        # 3. Calcolo finale degli Euro (ora che i mc sono quadrati)
        
        # Visualizziamo la tabella finale riassuntiva
        # --- IL BILANCIATORE CON MEMORIA ---
        # --- IL BILANCIATORE DEL SOCIO (Con protezione dai crash) ---
        
        # 1. Calcoliamo i mc inseriti nell'editor
        totale_mc_inseriti = edit_consumi["Lettura MC"].sum()
        
        # 2. CALCOLIAMO SOLO SE mc_tot ESISTE ED È MAGGIORE DI ZERO
        # mc_tot è il valore che scrivi nel box "Metri Cubi Totali"
        if mc_tot > 0: 
            differenza_mc = round(mc_tot - totale_mc_inseriti, 2)
            
            if abs(differenza_mc) > 0.01:
                st.warning(f"⚖️ **Squadratura rilevata:** Mancano **{differenza_mc} mc**.")
                
                # Assicurati che 'inquilini_nomi' sia definita qui sopra!
                assegna_a = st.selectbox(
                    "A quale inquilino vuoi assegnare l'eccedenza?", 
                    options=["Armellini Roberto", "Iovine Francesco", "Ciarpaglini Giacomo"],
                    key="selettore_eccedenza_unico"
                )
                
                # Applichiamo la correzione
                edit_consumi.loc[edit_consumi["Inquilino"] == assegna_a, "Eccedenza MC"] = differenza_mc
                st.success(f"✅ Eccedenza assegnata a {assegna_a}")
        else:
            # Se la bolletta è a zero, l'eccedenza deve essere zero
            edit_consumi["Eccedenza MC"] = 0.0
            
        # 3. Calcolo Totale e Euro
        # Il totale MC è la somma di lettura + eccedenza
        edit_consumi["Totale MC"] = edit_consumi["Lettura MC"] + edit_consumi["Eccedenza MC"]
        edit_consumi["Quota €"] = (edit_consumi["Totale MC"] * costo_mc).round(2)
        
        # 4. Visualizzazione Finale
        st.write("### 📊 Riepilogo Ripartizione")
        st.table(edit_consumi)
        # --- CONTROLLI DI COERENZA (Warning) ---
        # --- CONTROLLI DI COERENZA (Aggiornato per la tua Proprietà) ---
        # 1. Sommiamo le due nuove colonne invece della vecchia "Metri Cubi"
        totale_mc_inseriti = edit_consumi["Lettura MC"].sum() + edit_consumi["Eccedenza MC"].sum()

        # 2. Il resto rimane uguale, ma usiamo la variabile corretta
        totale_euro_calcolati = edit_consumi["Quota €"].sum()
        # Arrotondiamo per evitare falsi allarmi dovuti ai decimali di Python
        diff_mc = abs(totale_mc_inseriti - mc_tot)
        diff_euro = abs(totale_euro_calcolati - importo_tot)

        col_warn1, col_warn2 = st.columns(2)

        with col_warn1:
            if diff_mc > 0.01:
                st.warning(f"⚠️ I metri cubi totali ({totale_mc_inseriti:.2f}) non corrispondono alla bolletta ({mc_tot:.2f})")
            else:
                st.success("✅ Metri cubi coerenti")

        with col_warn2:
            if diff_euro > 0.05: # Tolleranza di 5 centesimi per arrotondamenti
                st.warning(f"⚠️ Il totale quote ({totale_euro_calcolati:.2f}€) differisce dalla bolletta ({importo_tot:.2f}€)")
            else:
                st.success("✅ Totale euro coerente")
        # 4. Salvataggio
        if st.button("SALVA E REGISTRA 🚀", use_container_width=True):
            try:
                # 1. Prepariamo il dizionario con la memoria dell'eccedenza

                # 1. Usiamo nomi chiavi più brevi per stare sicuri con lo spazio
                riepilogo_completo = {
                    row["Inquilino"]: {
                        "mcr": float(row["Lettura MC"]),      # mcr = mc reali
                        "ecc": float(row["Eccedenza MC"]),    # ecc = eccedenza
                        "tot": float(row["Lettura MC"] + row["Eccedenza MC"]),
                        "eur": float(row["Quota €"])
                    } for _, row in edit_consumi.iterrows()
                }

                ora_attuale = datetime.now().isoformat()
                # 2. Trasformiamo tutto in testo per il database
                dati_stringa = json.dumps(riepilogo_completo) 

                # A. Storico - QUI salviamo i dettagli completi
                db.create_document(
                    database_id=DB_ID, 
                    collection_id=COL_RIPARTIZIONI_ID, 
                    document_id=ID.unique(),
                    data={
                        "data_ripartizione": ora_attuale,
                        "periodo_riferimento": periodo,
                        "bolletta_totale_euro": float(importo_tot),
                        "mc_totali_bolletta": float(mc_tot),
                        "costo_mc": float(costo_mc),
                        "dati_ripartizione": dati_stringa # <--- USA LA STRINGA JSON
                    }
                )
                # B. Spese - Qui salviamo solo la tua parte (Armellini)
                quota_socio = float(edit_consumi.loc[edit_consumi["Inquilino"] == "Armellini Roberto", "Quota €"].values[0])
                db.create_document(
                    database_id=DB_ID, 
                    collection_id=COL_SPESE, 
                    document_id=ID.unique(),
                    data={
                        "descrizione": f"Acqua - Quota Personale ({periodo})",
                        "importo": quota_socio,
                        "data_scadenza": ora_attuale,
                        "categoria": "Acqua",
                        "proprieta_id": prop_id_scelta,
                        "fornitore": "Gestore Idrico",
                        "numero_fattura": periodo,
                        "data_fattura": ora_attuale,
                        "metodo_pagamento": "Addebito Diretto"
                    }
                )
                
                st.cache_data.clear()
                st.balloons()
                st.success(f"Tutto salvato per **{prop_selezionata}**! Controlla la tua lista spese.")
                
            except Exception as e:
                st.error(f"Errore durante il salvataggio: {e}")
    with tab2:
        st.subheader("🕵️ Storico Ripartizioni")
        try:
            # Recuperiamo i dati dallo storico
            storico = db.list_documents(database_id=DB_ID, collection_id=COL_RIPARTIZIONI_ID)
            if storico['documents']:
                df_storico = pd.DataFrame(storico['documents'])
                
                # Puliamo il DataFrame per la visualizzazione
                mostra_storico = df_storico[["periodo_riferimento", "bolletta_totale_euro", "data_ripartizione"]].copy()
                
                # Visualizziamo la lista
                scelta_storico = st.selectbox("Seleziona una ripartizione passata per vedere i dettagli:", 
                                            options=range(len(mostra_storico)),
                                            format_func=lambda x: f"{mostra_storico.iloc[x]['periodo_riferimento']} (del {mostra_storico.iloc[x]['data_ripartizione'][:10]})")
                
                # Quando l'utente seleziona, ricostruiamo la tabella dai dati JSON

                # 1. Quando l'utente seleziona, ricostruiamo la tabella dai dati JSON
                dati_salvati = json.loads(df_storico.iloc[scelta_storico]["dati_ripartizione"])
                
                st.write(f"### Dettaglio Periodo: {df_storico.iloc[scelta_storico]['periodo_riferimento']}")
                
                # 2. Ricostruiamo il dataframe con le NUOVE COLONNE
                df_dettaglio = pd.DataFrame.from_dict(dati_salvati, orient='index').reset_index()
                
                # Rinominiamo le colonne per farle combaciare con i dati salvati
                # Nota: l'ordine dipende da come lo hai salvato nel dizionario
                df_dettaglio.columns = ["Inquilino", "mc_reali", "eccedenza", "totale_mc", "euro"]
                
                # Visualizziamo una tabella pulita per l'utente
                st.table(df_dettaglio[["Inquilino", "totale_mc", "euro"]].rename(columns={
                    "totale_mc": "Metri Cubi Totali",
                    "euro": "Quota €"
                }))
                
                st.divider()
                st.subheader("📥 Opzioni di Esportazione")

                # --- 1. DATI COMUNI ---
                periodo_storico = df_storico.iloc[scelta_storico]['periodo_riferimento']
                totale_bolletta_storica = float(df_storico.iloc[scelta_storico]['bolletta_totale_euro'])

                # --- 2. DOWNLOAD COMPLESSIVO (Riepilogo Totale) ---
                col_globale1, col_globale2 = st.columns(2)
                
                html_completo = genera_riepilogo_pdf(
                    periodo_storico, 
                    prop_selezionata, 
                    df_dettaglio, 
                    totale_bolletta_storica
                )

                with col_globale1:
                    st.download_button(
                        label="📄 Scarica Riepilogo Globale (HTML)",
                        data=html_completo,
                        file_name=f"Riepilogo_Globale_{periodo_storico}.html",
                        mime="text/html",
                        use_container_width=True
                    )
                with col_globale2:
                    csv = df_dettaglio.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Scarica Riepilogo (CSV)",
                        data=csv,
                        file_name=f"Ripartizione_{periodo_storico}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                # --- 3. DOWNLOAD SINGOLO (Ricevuta per inquilino) ---
                st.write("---")
                st.write("🔍 **Genera Ricevuta Singola**")
                col_sel, col_btn = st.columns([2, 1])
                
                with col_sel:
                    inquilino_scelto = st.selectbox(
                        "Scegli inquilino:", 
                        options=df_dettaglio["Inquilino"].tolist(),
                        key="sel_singolo"
                    )
                    # --- 3. DOWNLOAD SINGOLO (Ricevuta per inquilino) ---
                    # Qui le chiavi ora combaceranno perfettamente con l'HTML
                with col_btn:
                    dati_singolo = df_dettaglio[df_dettaglio["Inquilino"] == inquilino_scelto].iloc[0]
                    
                    riga_storico = df_storico.iloc[scelta_storico]
                    importo_gen = float(riga_storico['bolletta_totale_euro'])
                    mc_gen = float(riga_storico['mc_totali_bolletta'])
                    
                    # L'HTML che hai postato ora funzionerà perché dati_singolo
                    # contiene le chiavi: mc_reali, eccedenza, totale_mc, euro
                    html_singolo = f"""                    
                    <div style="font-family: Arial, sans-serif; padding: 30px; border: 2px solid #2E7D32; border-radius: 15px; max-width: 450px; margin: auto; background-color: #fff;">
                        <div style="text-align: center; margin-bottom: 20px;">
                            <h2 style="color: #2E7D32; margin: 0;">RICEVUTA ACQUA</h2>
                            <p style="color: #666; font-size: 0.9em;">Documento ad uso interno</p>
                        </div>
                        
                        <div style="border-top: 1px solid #eee; border-bottom: 1px solid #eee; padding: 15px 0; margin-bottom: 20px;">
                            <p><strong>Immobile:</strong> {prop_selezionata}</p>
                            <p><strong>Periodo:</strong> {periodo_storico}</p>
                            <p><strong>Inquilino:</strong> {inquilino_scelto}</p>
                        </div>

                        <div style="background-color: #f1f8e9; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                            <p style="margin: 0; color: #555;">Dettaglio Consumi</p>
                            <p style="margin: 5px 0; color: #666; font-size: 0.9em;">
                                Contatore: <b>{dati_singolo['mc_reali']:.2f} mc</b> | 
                                Eccedenza: <b>{dati_singolo['eccedenza']:.2f} mc</b>
                            </p>
                            <h3 style="margin: 10px 0; color: #333;">Totale: {dati_singolo['totale_mc']:.2f} mc</h3>
                            <p style="margin: 15px 0 5px 0; color: #555;">Tua quota da versare</p>
                            <h2 style="margin: 0; color: #2E7D32; font-size: 2.2em;">{dati_singolo['euro']:.2f} €</h2>
                        </div>
                        <div style="border: 1px dashed #ccc; padding: 10px; border-radius: 5px; background-color: #fafafa; font-size: 0.85em; color: #555;">
                            <p style="margin: 0 0 5px 0; font-weight: bold; border-bottom: 1px solid #eee;">Dati Bolletta Condominiale di Riferimento:</p>
                            <p style="margin: 2px 0;">Bolletta Periodo: <strong>{periodo_storico}</strong></p>
                            <p style="margin: 2px 0;">Importo Totale: <strong>{importo_gen:.2f} €</strong></p>
                            <p style="margin: 2px 0;">Consumo Totale: <strong>{mc_gen:.2f} mc</strong></p>
                        </div>

                        <p style="font-size: 0.75em; color: #999; text-align: center; margin-top: 25px;">
                            Generato dal Sistema Gestionale **Hub Family** il {datetime.now().strftime('%d/%m/%Y')}
                        </p>
                    </div>
                    """
                    
                    # 🚀 MANCAVA IL BOTTONE DI DOWNLOAD EFFETTIVO!
                    st.download_button(
                        label=f"💾 Scarica Ricevuta",
                        data=html_singolo,
                        file_name=f"Ricevuta_{inquilino_scelto}_{periodo_storico}.html",
                        mime="text/html",
                        use_container_width=True
                    )
                # Tasto per "Ristampa" (per ora facciamo scaricare un CSV, poi se vuoi passiamo al PDF)
            else:
                st.write("Nessuno storico presente.")
        except Exception as e:
            st.error(f"Errore nel recupero dello storico: {e}")
                        
#st.sidebar.title("🎮 Navigazione")
#scelta_pagina = st.sidebar.radio("Vai a:", [
#    "💰 Dashboard Spese", 
#    "🏠 Gestione Immobili", 
#    "💧 Ripartizione Acqua"  # <--- Aggiungiamo questa!
#])

with st.sidebar:
    # 1. Visualizzazione del Logo
    try:
        st.image("LogoHubFamily.png", use_container_width=True)
    except Exception:
        st.write("🏠 **Family Hub**") # Fallback se l'immagine non viene caricata

    # Recuperiamo il nome dell'utente loggato (usiamo .capitalize() per l'iniziale maiuscola)
    nome_utente = st.session_state.get("user_nome", "Ospite").capitalize()

    # Scriviamo il saluto dinamico
    st.write(f"Utente: **{nome_utente}**")

    st.sidebar.write(f"Versione Streamlit: {st.__version__}")    
    # 2. Pulsante Logout (con il nostro nuovo st.stop!)
    if st.button("Esci in Sicurezza 🚪", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Sessione conclusa con successo!")
        st.rerun() # Ti riporta alla schermata di login        
    st.divider()

    st.subheader("🌐 Link Rapidi Utenze")
        
        # Un contenitore per rendere i tasti più compatti
    with st.expander("Gestione Utenze", expanded=True):
        st.link_button("💧 Portale Acqua", "https://www.publiacqua.it", use_container_width=True)
        st.link_button("⚡ Portale Luce", "https://www.sorgenia.it", use_container_width=True)
        st.link_button("🔥 Portale Gas", "https://www.sorgenia.it", use_container_width=True)
        st.link_button("🗑️ Portale Rifiuti (TARI)", "https://www.aliaserviziambientali.it/it-it", use_container_width=True)
        
        # Se vuoi aggiungere link a cartelle o documenti specifici della Proprietà
#    with st.expander("📂 Documenti", expanded=False):
#        st.link_button("📋 Regolamento", "https://link-al-tuo-regolamento.it", use_container_width=True)
#        st.link_button("📑 Tabelle Millesimali", "https://link-tabelle.it", use_container_width=True)

    st.divider()

# 2. Sostituiamo il radio button con i Tab nella pagina principale
tab_compiti, tab_immobili, tab_doc_imm, tab_spese, tab_acqua, tab_manutenzioni, tab_proprieta, tab_setup, tab_rubrica = st.tabs([
    "✅ Compiti",
    "🏠 Immobili", 
    "📂 Documenti Casa",
    "💰 Spese", 
    "💧 Acqua", 
    "🛠️ Manutenzioni",
    "📝 Task Proprietà",
    "⚙️ Setup Regole",
    "📞 Rubrica Artigiani"
])

with tab_compiti:
    # Mostriamo il saluto personalizzato
    nome_utente = st.session_state.get("user_nome", "Socio").capitalize()
    st.header(f"Ciao {nome_utente}, ecco l'agenda:")
    # 🛠️ LA MODIFICA È QUI: 
    # Se 'service' non esiste, lo creiamo al volo usando la tua funzione
    try:
        service_google = get_tasks_service() 
        mostra_riepilogo_tasks(service_google)
    except Exception as e:
        st.error(f"Socio, non riesco a collegarmi a Google Tasks: {e}")
    

with tab_immobili:
# --- PAGINA: GESTIONE PROPRIETÀ ---
    st.title("🏠 Anagrafica Immobili")
    st.info("Qui puoi aggiungere, modificare o eliminare le tue case.")
    
    try:
        res = db.list_documents(DB_ID, COL_PROP)
        df_p_raw = pd.DataFrame(res['documents'])
        cols_p = ["nome", "indirizzo_completo", "tipo_contratto", "proprietario_id"]
        
        df_p_display = df_p_raw[cols_p] if not df_p_raw.empty else pd.DataFrame(columns=cols_p)

        edit_p = st.data_editor(df_p_display, num_rows="dynamic", use_container_width=True, key="ed_p",
                               column_config={"tipo_contratto": st.column_config.SelectboxColumn("Tipo", options=["Proprietà", "Affitto", "Altro"])})

        if st.button("Salva modifiche Immobile"):
            state = st.session_state.ed_p
            for row in state.get("added_rows", []):
                db.create_document(DB_ID, COL_PROP, ID.unique(), row)
            for index, changes in state.get("edited_rows", {}).items():
                db.update_document(DB_ID, COL_PROP, df_p_raw.iloc[index]["$id"], changes)
            for index in state.get("deleted_rows", []):
                db.delete_document(DB_ID, COL_PROP, df_p_raw.iloc[index]["$id"])
            st.cache_data.clear()    
            st.balloons()
            time.sleep(2)
            st.rerun()
    except Exception as e:
        st.error(f"Errore: {e}")

with tab_doc_imm:
    # Richiamiamo la nuova funzione del Caveau
    sezione_documenti_immobili()

# --- PAGINA: DASHBOARD SPESE (Sostituisci tutto il blocco else) ---
with tab_spese: 
    st.title("💰 Gestione Spese e Bollette")
# ==> in caso di situazioni anomale; serve per vedere se stiamo caricando il programma
# ==> aggiornato    st.title("🚀 TEST DI SALVATAGGIO 🚀")    
    try:
        # Recupero tutte le proprietà per la selectbox
        res_p = db.list_documents(DB_ID, COL_PROP)
        df_p = pd.DataFrame(res_p['documents'])
        
        if df_p.empty:
            st.warning("Vai prima nella sezione 'Gestione Immobili' e aggiungi una casa!")
        else:
            # 1. Creiamo l'etichetta leggibile "Nome - Indirizzo"
            df_p["label"] = df_p["nome"] + " - " + df_p["indirizzo_completo"]
            
            # 2. Mappa che collega l'ETICHETTA all'ID UNIVOCO ($id) della casa
            mappa_id = dict(zip(df_p["label"], df_p["$id"]))
            
            scelta_label = st.selectbox("Seleziona l' Immobile:", df_p["label"].tolist())
            
            # 3. Recuperiamo l'ID reale della casa scelta per il filtro
            id_casa_scelta = mappa_id[scelta_label]
            
            st.divider()

            # 4. Recupero spese filtrate per ID UNIVOCO della casa
            # 4. Recupero spese filtrate per ID UNIVOCO della casa
            res_s = db.list_documents(DB_ID, COL_SPESE, [Query.equal("proprieta_id", id_casa_scelta)])
            df_s_raw = pd.DataFrame(res_s['documents'])

            # --- ORDINAMENTO DECRESCENTE ---
            if not df_s_raw.empty and 'data_scadenza' in df_s_raw.columns:
                # Convertiamo la colonna in formato data per essere sicuri che l'ordine sia corretto
                df_s_raw['data_scadenza'] = pd.to_datetime(df_s_raw['data_scadenza'])
                # Ordiniamo: ascending=False mette la data più recente (es. 2026) in alto
                df_s_raw = df_s_raw.sort_values(by='data_scadenza', ascending=False)
                # Riportiamo il formato a stringa gg/mm/aaaa per la visualizzazione nella Proprietà
                df_s_raw['data_scadenza'] = df_s_raw['data_scadenza'].dt.strftime('%d/%m/%Y')

            # Calcolo del totale in tempo reale
            if not df_s_raw.empty and 'importo' in df_s_raw.columns:
                totale_spese = df_s_raw['importo'].sum()
            else:
                totale_spese = 0.0

            # Visualizzazione Totale
            st.metric(
                label=f"Totale Spese per {scelta_label}", 
                value=f"€ {totale_spese:,.2f}",
                delta_color="normal"
            )
            st.write("") 

            # Aggiorna la lista delle colonne da mostrare
            # --- MODIFICA 1: Aggiungi $id alle colonne da mostrare (anche se resterà nascosto)
            cols_s = ["$id", "descrizione", "importo", "data_scadenza", "categoria", "metodo_pagamento", "fornitore", "numero_fattura", "data_fattura"]
            df_s_display = df_s_raw[cols_s] if not df_s_raw.empty else pd.DataFrame(columns=cols_s)

            # Formattazione date per l'editor
            if not df_s_display.empty:
                df_s_display["data_fattura"] = pd.to_datetime(df_s_display["data_fattura"]).dt.date
                df_s_display["data_scadenza"] = pd.to_datetime(df_s_display["data_scadenza"]).dt.date

            # --- MODIFICA SENIOR: Configurazione decimale sbloccata ---
            # --- MODIFICA SENIOR: Aggiunta Metodo di Pagamento nell'Editor ---
            edit_s = st.data_editor(
                df_s_display, 
                num_rows="dynamic", 
                use_container_width=True, 
                key="ed_s",
                column_config={
                    "$id": None, # 👈 AGGIUNGI QUESTA RIGA: Nasconde l'ID ma lo tiene nel codice
                    "importo": st.column_config.NumberColumn(
                        "Importo (€)", 
                        format="%.2f", 
                        required=True,
                        min_value=0.0,
                        step=0.01
                    ),
                    "categoria": st.column_config.SelectboxColumn(
                        "Categoria", 
                        options=["Luce", "Gas", "Acqua", "Manutenzione", "Tasse", "Affitto","Tari", "Assicurazione", "Altro"], 
                        required=True
                    ),
                    # --- NUOVA COLONNA METODO DI PAGAMENTO ---
                    "metodo_pagamento": st.column_config.SelectboxColumn(
                        "Pagamento",
                        options=[
                            "🏦 Bonifico Bancario", 
                            "💳 Carta/Bancomat", 
                            "📉 Addebito Diretto (SDD)", 
                            "💵 Contanti", 
                            "🏛️ CBILL / PagoPA", 
                            "🔄 Altro"
                        ],
                        required=True
                    ),
                    "data_fattura": st.column_config.DateColumn("Data Fattura", format="DD/MM/YYYY"),
                    "data_scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY")
                }
            )
            # --- SEZIONE ALLEGATI ---
            st.subheader("📎 Documenti e Allegati")
            
            # --- AGGIUNTA MANUALE D'ORO: GHOST COMPRESSOR PRO ---
            with st.expander("🗜️ Utility: Ottimizzatore PDF (Ghostscript)"):
                st.info("Genera il comando completo con i percorsi delle cartelle della tua **Proprietà**.")
                
                # Inserimento del percorso (es. C:\Bollette\2026\ o /Users/roberto/Documents/)
                path_cartella = st.text_input("📁 Percorso della cartella (Path):", "C:/Documenti/Bollette/", key="gs_path")
                
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    file_input = st.text_input("📄 File originale:", "bolletta_pesante.pdf", key="gs_in")
                with col_f2:
                    file_output = st.text_input("📄 Nuovo file:", "bolletta_light.pdf", key="gs_out")
                
                # Costruiamo i percorsi completi (gestendo lo slash finale se manca)
                if not path_cartella.endswith('/') and not path_cartella.endswith('\\'):
                    path_cartella += '/'
                
                full_in = f"{path_cartella}{file_input}"
                full_out = f"{path_cartella}{file_output}"
                
                # Il comando "Magico" con i percorsi completi tra virgolette (per gestire eventuali spazi nei nomi)
                gs_command = f'gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/screen -dNOPAUSE -dQUIET -dBATCH -sOutputFile="{full_out}" "{full_in}"'
                
                st.code(gs_command, language="bash")
                st.warning("⚠️ Nota: Copia il comando, apri il terminale e incollalo. Il file compresso apparirà nella stessa cartella.")

            st.write("") # Un po' di spazio prima della gestione allegati
            # --- FINE UTILITY ---
            #             
            if not df_s_raw.empty:
                scelta_spesa = st.selectbox(
                    "Seleziona una spesa per gestire l'allegato:", 
                    df_s_raw["descrizione"].tolist(),
                    key="sel_spesa_allegato"
                )
                
                spesa_sel = df_s_raw[df_s_raw["descrizione"] == scelta_spesa].iloc[0]
                doc_id_spesa = spesa_sel["$id"]
                file_id_esistente = spesa_sel.get("file_id")

                # 1. Recupero ALLEGATI dal DB filtrando per spesa_id
                res_all = db.list_documents(DB_ID, COL_ALLEGATI, [Query.equal("spesa_id", doc_id_spesa)])
                allegati_presenti = res_all['documents']

                col1, col2 = st.columns(2)

                with col1:
                    if allegati_presenti:
                        st.write(f"📂 **{len(allegati_presenti)} documenti trovati:**")
                        for doc in allegati_presenti:
                            f_id = doc["file_id"]
                            nome = doc.get("nome_file", "Documento")
                            
                            PROJECT_ID = st.secrets["appwrite"]["project_id"]
                            url_doc = f"https://cloud.appwrite.io/v1/storage/buckets/{BUCKET_ID}/files/{f_id}/view?project={PROJECT_ID}"
                            
                            c1, c2 = st.columns([4, 1])
                            c1.link_button(f"{nome} 📄", url_doc, use_container_width=True)
                            
                            # Tasto Cancella Chirurgico
                            if c2.button("🗑️", key=f"del_{doc['$id']}"):
                                storage.delete_file(BUCKET_ID, f_id) # Via il file fisico
                                db.delete_document(DB_ID, COL_ALLEGATI, doc['$id']) # Via il record dal DB
                                st.warning("Allegato rimosso.")
                                time.sleep(1)
                                st.rerun()
                    else:
                        st.info("ℹ️ Nessun documento per questa spesa.")

                with col2:
                    uploaded_file = st.file_uploader("Carica nuovo documento", type=['pdf', 'jpg', 'png'], key="uploader")
                    if uploaded_file and st.button("SALVA ALLEGATO 💾"):
                        # A. Caricamento fisico
                        new_file = storage.create_file(
                            bucket_id=BUCKET_ID,
                            file_id=ID.unique(),
                            file=InputFile.from_bytes(uploaded_file.getvalue(), filename=uploaded_file.name)
                        )
                        
                        # B. Creazione record nella nuova tabella ALLEGATI
                        db.create_document(DB_ID, COL_ALLEGATI, ID.unique(), {
                            "spesa_id": doc_id_spesa,
                            "file_id": str(new_file["$id"]),
                            "nome_file": uploaded_file.name
                        })
                        st.cache_data.clear()
                        st.success("Allegato salvato correttamente!")
                        st.balloons()
                        time.sleep(1)
                        st.cache_data.clear()
                        st.rerun()
            st.divider()
            
            # --- SEZIONE SALVATAGGIO ---
            if "salvataggio_completato" in st.session_state and st.session_state.salvataggio_completato:
                st.session_state["check_conferma"] = False
                st.session_state.salvataggio_completato = False 

            col_check, col_btn = st.columns([2, 1])
            with col_check:
                conferma = st.checkbox("Confermo le modifiche (incluse eventuali cancellazioni) ✅", key="check_conferma")

            with col_btn:
                if st.button("Salva Spese 🚀", disabled=not conferma, use_container_width=True):
                    # 1. Recupero lo stato dell'editor
                    if "ed_s" not in st.session_state:
                        st.error("Nessuna modifica rilevata da salvare.")
                        st.stop()
                    
                    state = st.session_state.ed_s
                    try:
                        # --- PARTE A: NUOVE RIGHE (Usa added_rows per evitare raddoppi) ---
                        for row in state.get("added_rows", []):
                            # Salto la riga se non c'è almeno la descrizione
                            if not row.get("descrizione"):
                                continue
                                
                            nuovo_doc = {
                                "proprieta_id": id_casa_scelta,
                                "descrizione": str(row.get("descrizione")),
                                "categoria": row.get("categoria") or row.get("Categoria", "Altro"),
                                "metodo_pagamento": row.get("metodo_pagamento") or row.get("Pagamento", "Bonifico"),
                                "fornitore": row.get("fornitore", ""),
                                "numero_fattura": row.get("numero_fattura", ""),
                            }

                            # Gestione Importo (conversione virgola/punto)
                            val_imp = str(row.get("importo", "0")).replace(',', '.')
                            nuovo_doc["importo"] = float(val_imp) if val_imp else 0.0

                            # Gestione Date (Mappatura nomi visuali/tecnici)
                            scad_raw = row.get("data_scadenza") or row.get("Scadenza")
                            nuovo_doc["data_scadenza"] = str(scad_raw) if scad_raw else None
                            
                            fatt_raw = row.get("data_fattura") or row.get("Data Fattura")
                            nuovo_doc["data_fattura"] = str(fatt_raw) if fatt_raw else None

                            # Scrittura su Appwrite
                            db.create_document(DB_ID, COL_SPESE, ID.unique(), nuovo_doc)

                        # --- PARTE B: RIGHE MODIFICATE ---
                        for index, changes in state.get("edited_rows", {}).items():
                            # Usiamo df_s_raw per beccare l'ID corretto tramite l'indice
                            doc_id = df_s_raw.iloc[int(index)]["$id"]
                            
                            # Traduzione chiavi per modifiche date/pagamento
                            if "Scadenza" in changes: changes["data_scadenza"] = str(changes.pop("Scadenza"))
                            if "Pagamento" in changes: changes["metodo_pagamento"] = str(changes.pop("Pagamento"))
                            
                            if "importo" in changes:
                                val_imp = str(changes.get("importo", "0")).replace(',', '.')
                                changes["importo"] = float(val_imp) if val_imp else 0.0
                            
                            db.update_document(DB_ID, COL_SPESE, doc_id, changes)
                        
                        # --- PARTE C: RIGHE ELIMINATE ---
                        for index in state.get("deleted_rows", []):
                            doc_da_eliminare = df_s_raw.iloc[int(index)]
                            db.delete_document(DB_ID, COL_SPESE, doc_da_eliminare["$id"])

                        # --- PARTE D: RESET TOTALE E PULIZIA ---
                        st.cache_data.clear() # Svuota la cache di lettura
                        if "ed_s" in st.session_state:
                            del st.session_state["ed_s"] # Svuota il buffer dell'editor
                        
                        st.balloons()
                        st.success("Dati della **Proprietà** sincronizzati con successo!")
                        time.sleep(1.5)
                        st.rerun()

                    except Exception as e:
                        if "cannot be modified" in str(e): 
                            st.rerun()
                        else: 
                            st.error(f"Errore tecnico nel salvataggio: {str(e)}")
                            
        # --- OCCHIO DI FALCO: COMINCIA QUI ---
            # Nota: è allineato alla stessa altezza di "with col_check" e "with col_btn"
            if not df_s_raw.empty:
                st.write("---")
                st.subheader(f"📊 Analisi Strategica: {scelta_label}")
                
                # Prepariamo i dati
                df_grafico = df_s_raw.copy()
                df_grafico['importo'] = pd.to_numeric(df_grafico['importo'], errors='coerce').fillna(0)
                df_grafico['data_fattura'] = pd.to_datetime(df_grafico['data_fattura'], errors='coerce')
                
                g1, g2 = st.columns(2)
                with g1:
                    st.markdown("##### 🍕 Spese per Categoria")
                    fig_pie = px.pie(df_grafico, values='importo', names='categoria', hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                with g2:
                    st.markdown("##### 📅 Trend Mensile")
                    df_trend = df_grafico.set_index('data_fattura').resample('ME')['importo'].sum().reset_index()
                    fig_trend = px.line(df_trend, x='data_fattura', y='importo', markers=True)
                    st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("ℹ️ Carica i dati per attivare l'Analisi Occhio di Falco.")

    except Exception as e:
        st.error(f"Errore di caricamento: {e}")

with tab_acqua:
    # Mettiamo l'acqua nel suo elif dedicato
    pagina_ripartizione_acqua()


with tab_manutenzioni:
    st.title("🛠️ Scadenziario Manutenzioni")
    
    try:
        documenti = db.list_documents(DB_ID, COL_MANUT_ID)
        df_m = pd.DataFrame(documenti['documents'])
        if not df_m.empty:
            df_m = df_m[["intervento", "data_scadenza", "preavviso_giorni", "periodico"]]
            # Forza la conversione in data per far apparire il calendario nell'editor
            df_m['data_scadenza'] = pd.to_datetime(df_m['data_scadenza']).dt.date
        else:
            df_m = pd.DataFrame(columns=["intervento", "data_scadenza", "preavviso_giorni", "periodico"])
    except Exception:
        df_m = pd.DataFrame(columns=["intervento", "data_scadenza", "preavviso_giorni", "periodico"])

    # --- INIZIO SEMAFORO CON CALENDAR (CON LOGICA OBLIO) ---
    if not df_m.empty:
        st.subheader("🔔 Avvisi Scadenze Hub Family")
        oggi = date.today()
        GIORNI_OBLIO = 10 # <--- Socio, qui decidi dopo quanti giorni far sparire il "rosso"
        
        with st.expander("Controlla scadenze imminenti", expanded=True):
            for index, row in df_m.iterrows():
                data_scad = row['data_scadenza']
                if isinstance(data_scad, str):
                    data_scad = pd.to_datetime(data_scad).date()
                
                giorni_mancanti = (data_scad - oggi).days
                preavviso = int(row['preavviso_giorni'] or 0)
                intervento = row['intervento']

                # --- NUOVA LOGICA OBLIO ---
                # Se è scaduta (giorni_mancanti < 0) e il ritardo è oltre i GIORNI_OBLIO, saltiamo la riga
                if giorni_mancanti < 0 and abs(giorni_mancanti) > GIORNI_OBLIO:
                    continue # Passa alla prossima scadenza senza mostrare nulla

                # Logica Avvisi + Bottone Calendar
                if giorni_mancanti <= preavviso:
                    # Creiamo due colonne: una per l'avviso e una piccola per il bottone
                    col_testo, col_btn = st.columns([0.75, 0.25])
                    
                    with col_testo:
                        if giorni_mancanti <= 0:
                            # Mostriamo il ritardo esatto per dare un senso di urgenza (ma solo entro i 10gg)
                            ritardo = abs(giorni_mancanti)
                            giorni_str = "oggi" if ritardo == 0 else f"{ritardo} giorni fa"
                            st.error(f"🔴 **SCADUTO!** {intervento} (scadenza: {data_scad.strftime('%d/%m/%Y')} - {giorni_str})")
                        else:
                            st.warning(f"🟡 **ATTENZIONE:** {intervento} tra {giorni_mancanti} giorni")
                    
                    with col_btn:
                        # 1. ID del tuo nuovo calendario Scadenze
                        id_cal_scadenze = "a06886a5459784a0d431f16d42c22f185fa2e06cec4d882e331cb5b64ea16b30@group.calendar.google.com"
                        
                        # 2. Preparazione link Google Calendar
                        titolo_cal = f"Manutenzione: {intervento}".replace(" ", "+")
                        data_stringa = data_scad.strftime("%Y%m%d")
                        
                        link_google = (
                            f"https://www.google.com/calendar/render?action=TEMPLATE"
                            f"&text={titolo_cal}"
                            f"&dates={data_stringa}/{data_stringa}"
                            f"&details=Promemoria+automatico+Hub+Family"
                            f"&src={id_cal_scadenze}"
                        )
                        
                        st.link_button("🗓️ Calendar", link_google, use_container_width=True)                    
    # --- FINE SEMAFORO ---

    st.info("Gestisci le scadenze. Clicca sulla colonna 'Scadenza' per il calendario. Usa il tasto **+** per aggiungere.")

    # --- LOGICA VISUALE PER L'OBLIO ---
    df_m_visual = df_m.copy()
    GIORNI_OBLIO = 10
    oggi = date.today()

    def calcola_stato(row):
        data_scad = row['data_scadenza']
        if isinstance(data_scad, str):
            data_scad = pd.to_datetime(data_scad).date()
        
        ritardo = (oggi - data_scad).days
        if ritardo > GIORNI_OBLIO:
            return "🚨 OBLIO"  # La sirena per le cose dimenticate
        elif ritardo > 0:
            return "🔴 SCADUTO"
        else:
            return "✅ OK"

    # Aggiungiamo la colonna di stato solo per la visualizzazione
    if not df_m_visual.empty:
        df_m_visual.insert(0, "Stato", df_m_visual.apply(calcola_stato, axis=1))

    # EDITOR CONFIGURATO CON COLONNA STATO
    edited_df = st.data_editor(
        df_m_visual, 
        num_rows="dynamic", 
        use_container_width=True, 
        key="edit_manut_v2",
        column_config={
            "Stato": st.column_config.TextColumn("Stato", width="small", help="🚨 indica una scadenza oltre i 10 giorni di oblio"),
            "intervento": st.column_config.TextColumn("Descrizione Intervento", width="large"),
            "data_scadenza": st.column_config.DateColumn("Scadenza", width="small", format="DD/MM/YYYY"),
            "preavviso_giorni": st.column_config.NumberColumn("Preavviso gg", width="small"),
            "periodico": st.column_config.CheckboxColumn("Annuale", width="small")
        }
    )

    if st.button("Aggiorna Scadenziario 💾", use_container_width=True):
        try:
            # Rimuoviamo la colonna "Stato" prima di salvare (perché il DB non la vuole!)
            if "Stato" in edited_df.columns:
                df_to_save = edited_df.drop(columns=["Stato"])
            else:
                df_to_save = edited_df

            # Svuota vecchi record
            vecchi = db.list_documents(DB_ID, COL_MANUT_ID)
            for doc in vecchi['documents']:
                db.delete_document(DB_ID, COL_MANUT_ID, doc['$id'])
            
            # Salva nuovi record
            for index, row in df_to_save.iterrows():
                data_val = row['data_scadenza']
                if pd.isnull(data_val) or data_val == "":
                    continue
                
                if isinstance(data_val, str):
                    data_val = pd.to_datetime(data_val).date()
                
                data_iso = data_val.strftime("%Y-%m-%dT00:00:00.000+00:00")
                
                db.create_document(DB_ID, COL_MANUT_ID, "unique()", {
                    "intervento": row['intervento'],
                    "data_scadenza": data_iso,
                    "preavviso_giorni": int(row['preavviso_giorni'] or 0),
                    "periodico": bool(row['periodico'])
                })
            st.cache_data.clear()    
            st.success("Dati della **Proprietà** salvati correttamente!")
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")

with tab_proprieta:
    st.header("Gestione Impegni Hub Family")
    
    # 1. Sezione Inserimento (Con Calendario)
    st.subheader("📝 Nuovo Impegno")
    c1, c2, c3 = st.columns([1.5, 3, 1])
    
    with c1:
        # Il calendario per scegliere la scadenza (default: oggi)
        # Aggiungiamo format="DD/MM/YYYY" per vedere la data all'italiana
        data_scadenza = st.date_input(
            "Scadenza", 
            key="data_impegno", 
            format="DD/MM/YYYY"
        )
    
    with c2:
        nuovo = st.text_input("Cosa c'è da fare?", key="input_task", placeholder="es. Comprare Gatto")
    
    with c3:
        st.write(" ") # Spazio estetico per allineare il bottone
        invio = st.button("🚀 Invia", use_container_width=True)
        
    if invio:
        if nuovo:
            # 🚨 ATTENZIONE: Passiamo sia il testo che la data!
            # Trasformiamo la data in stringa formato ISO che Google Tasks gradisce
            data_iso = data_scadenza.strftime('%Y-%m-%dT00:00:00Z')
            aggiungi_task_family(nuovo, data_iso) 
            st.success(f"Impegno per il {data_scadenza.strftime('%d/%m')} aggiunto!")
            st.rerun()

    st.divider()

    # --- IL RESTO DELLA FUNZIONE (Visualizzazione e Manutenzione) ---
    st.subheader("Cose da fare:")
    elenco_tasks = ottieni_lista_task()

    if not elenco_tasks:
        st.info(f"{nome_fresco}, tutto pulito! Goditi il caffè. ☕")
    else:
        for t in elenco_tasks:
            col_testo, col_bottone = st.columns([0.8, 0.2])
            with col_testo:
                # Recuperiamo la data di scadenza se presente nel task di Google
                due_date = ""
                if 'due' in t:
                    d = datetime.strptime(t['due'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    due_date = f" 📅 *({d.strftime('%d/%m')})*"
                
                if "MANUTENZIONE" in t['title']:
                    st.markdown(f"⚠️ **:red[{t['title']}]** {due_date}")
                else:
                    st.write(f"📌 {t['title']} {due_date}")               

            with col_bottone:
                if st.button("Fatto! ✅", key=t['id']):
                    completa_task_family(t['id'])
                    st.toast(f"Ottimo lavoro per la Proprietà!")
                    st.rerun()

    st.divider()
    st.subheader("🛠️ Manutenzione Programmata")
    if st.button("Esegui Check-Up Stagionale"):
        nuovi = genera_task_manutenzione()
        if nuovi > 0:
            st.success(f"Ottimo lavoro per la Proprietà, {nome_fresco}!")
            st.rerun()
        else:
            st.info(f"{nome_fresco}, per questo mese siamo a posto con la manutenzione! Goditi il caffè. ☕")

with tab_setup:
    st.header("⚙️ Configurazione Regole")
    st.write("Qui imposti i lavori ricorrenti. L'app li creerà su Google Tasks nei mesi giusti.")
    
    # 1. RECUPERO: Leggiamo cosa c'è attualmente nel database
    regole_raw = carica_regole_manutenzione()
    
    # 2. TRASFORMAZIONE: Prepariamo i dati per Streamlit
    if regole_raw:
        df = pd.DataFrame(regole_raw)
        # Teniamo solo le colonne che ci servono, incluso l'ID nascosto
        df_visualizzato = df[['compito', 'mesi', 'icona', 'attiva', '$id']]
    else:
        # Se il database è vuoto, creiamo una tabella di partenza vuota
        df_visualizzato = pd.DataFrame(columns=['compito', 'mesi', 'icona', 'attiva'])

    # 3. EDITING: La tabella magica dove puoi scrivere e aggiungere righe (+)
    df_editato = st.data_editor(
        df_visualizzato, 
        num_rows="dynamic", 
        key="editor_regole", 
        hide_index=True,
        use_container_width=True
    )
    
    # 4. SALVATAGGIO: Quando premi il tasto, inviamo tutto al database
    if st.button("💾 Salva"):
        with st.spinner("Aggiornamento regole..."):
            aggiorna_regole_manutenzione(df_editato)
            st.success("Configurazione aggiornata! 🚂")
            st.rerun()

with tab_rubrica:
    gestione_rubrica_artigiani()            