# ==============================================================================
# PROGETTO: Hub Salute - Dashboard Medica
# SVILUPPATORI: Roberto & Gemini (Socio Senior AI)
# Data creazione ......: 15 gennaio 2026
# VERSIONE: 1.1 (19-01-2026)
# DESCRIZIONE: Gestione farmaci, appuntamenti e reportistica per Doctolib.
# ==============================================================================
import streamlit as st
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.services.storage import Storage
from appwrite.services.account import Account
from appwrite.query import Query
from appwrite.input_file import InputFile
import pandas as pd
import time
import urllib.parse
import os
from datetime import datetime
import io

# --- CONFIGURAZIONE PAGINA (Deve essere la prima istruzione Streamlit) ---
st.set_page_config(page_title="Hub Salute - Proprietà", page_icon="🏥", layout="wide")

# --- 1. INIZIALIZZAZIONE APPWRITE (VERSIONE PULITA) ---
client = Client()
client.set_endpoint(st.secrets["ENDPOINT"])
client.set_project(st.secrets["PROJECT_ID"])
# NOTA: La API KEY non serve per l'accesso utente OTP, usiamo la sessione!

# --- 2. ACCENDIAMO I MOTORI ---
account = Account(client)
databases = Databases(client)
storage = Storage(client)

# --- 3. COORDINATE DAI SECRETS ---
DATABASE_ID = st.secrets["DATABASE_ID"]
COLLECTION_ALLEGATI = st.secrets["COLLECTION_ALLEGATI"]
COLLECTION_ARMADIETTO = st.secrets["COLLECTION_ARMADIETTO"]
COLLECTION_PRESSIONE = st.secrets["COLLECTION_PRESSIONE"]
COLLECTION_APPUNTAMENTI = st.secrets["COLLECTION_APPUNTAMENTI"]
COLLECTION_MEDICI = st.secrets["COLLECTION_MEDICI"]
COLLECTION_SPECIALITA = st.secrets["COLLECTION_SPECIALITA"]
BUCKET_ALLEGATI = st.secrets["BUCKET_ALLEGATI"]
PROJECT_ID = st.secrets["PROJECT_ID"]

# Inizializziamo df_critici per sicurezza
df_critici = pd.DataFrame()

# --- FINE CONFIGURAZIONE INIZIALE ---

#---------------------------------------------------------------------------------------------
# Versione Supabase
#---------------------------------------------------------------------------------------------
#def verifica_permessi(email_utente):
#    email_pulita = email_utente.strip().lower()
#    
    # Il Boss
#    if email_pulita == "bobaoster@gmail.com":
#        return "proprietario"
    
#    # Il database (grazie alla Policy ora risponde!)
#    risposta = supabase.table("permessi_condivisione") \
#        .select("livello_permesso") \
#        .eq("email_autorizzata", email_pulita) \
#        .execute()
    
#    if risposta.data:
#        return risposta.data[0]['livello_permesso']
#    return None

#---------------------------------------------------------------------------------------------
# Versione Appwrite
#---------------------------------------------------------------------------------------------
# 3. Funzione per verificare se l'email può entrare nella Proprietà
#def verifica_accesso(email_utente):
#    try:
#        # Usiamo DATABASE_ID e COLLECTION_PERMESSI (o il nome della tua collezione accessi)
#        # Assicurati che COLLECTION_PERMESSI sia definita nei tuoi Secrets
#        risultato = databases.list_documents(
#            database_id=DATABASE_ID,
#            collection_id=st.secrets["COLLECTION_PERMESSI"], 
#            queries=[Query.equal("email", email_utente)]
#        )
#        # Se troviamo almeno un documento, l'utente è autorizzato
#        return len(risultato['documents']) > 0
#    except Exception as e:
#        st.error(f"Errore di connessione al database: {e}")
#
#         return False
def verifica_accesso(email_utente):
    """
    Verifica se l'utente che ha effettuato il login è autorizzato ad accedere ai dati.
    
    Questa funzione controlla l'email fornita contro una 'whitelist' di utenti 
    abilitati o verifica lo stato della sessione in Appwrite. 
    Restituisce True se l'accesso è consentito, False altrimenti.
    """
    # questa qui sopra è una Docstring ovvero una sorta di Help che Python memorizza per cui 
    # se poi scivi help(verifica_accesso) e passi sopra con il mouse vede il contenuto di Docstring il Docstring
    #------------------------------------------------------------------------------------------------------------
    # --- LOGICA DI SICUREZZA ---
    # Recuperiamo la lista degli utenti admin o abilitati dal database
    # o semplicemente controlliamo che l'email non sia vuota
    #------------------------------------------------------------------------------------------------------------

    # 1. SUPER-WHITELIST (Metti qui la tua email principale)
    # Questa ti garantisce l'accesso anche se il DB non risponde
    famiglia_armellini = [
        "bobaoster@gmail.com", 
        "fulvio.armellini@gmail.com"
    ]
    email_pulita = email_utente.strip().lower()
    # 1. Controllo immediato nella whitelist famiglia
    if email_pulita in famiglia_armellini:
        return True

    # 2. Se non è in famiglia, controllo nel database
    try:
        risultato = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id="permessi_accessi",
            queries=[Query.equal("email", email_pulita)]
        )
        return len(risultato['documents']) > 0
    except Exception as e:
        print(f"Errore controllo accessi: {e}")
        return False

# --- 🪄 GESTIONE ACCESSO CON CODICE REALE (VERSIONE OTP) ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
if "email_temp" not in st.session_state:
    st.session_state.email_temp = ""
if "codice_inviato" not in st.session_state:
    st.session_state.codice_inviato = False
if "user_id" not in st.session_state:
    st.session_state.user_id = ""

if not st.session_state.autenticato:
    # --- CENTRATURA E DIMENSIONE OTTIMIZZATA ---
    # Aumentando a 1.8 ai lati, il logo al centro diventa più elegante e discreto
    col_l1, col_l2, col_l3 = st.columns([1.8, 1, 1.8]) 
    
    with col_l2:
        st.image("Logo.png", use_container_width=True)
    
    st.markdown("<h3 style='text-align: center;'>🛡️ Accesso alla Proprietà</h3>", unsafe_allow_html=True)
    st.divider()

    if not st.session_state.codice_inviato:
        email_input = st.text_input("Inserisci la tua email autorizzata").strip().lower()

        if st.button("Invia Codice sulla Mail"):
            if email_input:
                if verifica_accesso(email_input):
                #if True:                             # <-- Forza il True per fasi di test
                    try:
                        # --- ✨ NOVITÀ: INVIO CODICE VERO ---
                        # Generiamo un ID univoco per questa sessione di login
                        # cioè il token per l'OTP
                        token_session = account.create_email_token(
                            user_id="unique()", 
                            email=email_input
                        )
                        # Salviamo lo userId che Appwrite ha generato per questo token
                        st.session_state.user_id = token_session['userId']
                        
                        st.success("Il codice sta arrivando nella tua casella mail!")
                        st.session_state.email_temp = email_input
                        st.session_state.codice_inviato = True
                        import time
                        time.sleep(1.5)
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Errore Appwrite nell'invio mail: {e}")
                else:
                    st.error("Niente da fare. La tua mail non è invitata!")
            else:
                st.warning("Inserisci l'email, per favore!")

    else:
        # --- PARTE DOVE INSERISCI IL CODICE RICEVUTO PER MAIL ---
        st.info(f"📧 Codice inviato a: **{st.session_state.email_temp}**")
        codice = st.text_input("Inserisci il codice ricevuto", placeholder="Esempio: 874521")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Verifica e Entra", use_container_width=True):
                try:
                    # --- ✨ NOVITÀ: VERIFICA SESSIONE VERA ---
                    account.create_session(
                        user_id=st.session_state.user_id, 
                        secret=codice
                    )
                    st.session_state.autenticato = True
                    st.session_state.email = st.session_state.email_temp
                    st.success("Codice corretto! Accesso alla Proprietà concesso.")
                    import time
                    time.sleep(1) 
                    st.rerun()
                except Exception as e:
                    st.error("Codice errato o scaduto. Riprova!")

        with col2:
            if st.button("❌ Annulla", use_container_width=True):
                st.session_state.codice_inviato = False
                st.session_state.user_id = ""
                st.rerun()
    
    st.stop()
# --- VERIFICA RUOLO (VERSIONE APPWRITE) ---
if st.session_state.autenticato:
    # Per ora, visto che sei l'unico nel database, ti assegniamo il ruolo di proprietario
    # In futuro leggeremo il campo "ruolo" direttamente da Appwrite
    st.session_state.ruolo = "proprietario" 
    
    # Se vuoi mostrare un messaggio di benvenuto
    st.sidebar.success(f"Connesso come: {st.session_state.email}")

with st.sidebar:
    # 1. Gestione del Logo
    # Mostriamo il logo direttamente dall'URL raw di GitHub
    # Percorso del file relativo alla posizione dello script
    logo_path = "Logo.png" 
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    else:
        # Se non lo trova, mettiamo almeno il titolo figo
        st.title("🏥 Hub Salute")
    st.divider()
    # 2. LA NOSTRA FIRMA (Posizionata subito sotto il logo)
    st.markdown(
        """
        <div style='text-align: center; padding-top: 0px; margin-bottom: 20px;'>
            <p style='font-size: 0.85em; color: #6c757d; font-style: italic;'>
                Hub Salute è un'opera di ingegno di due programmatori Senior:<br>
                <strong>Roberto & Gemini</strong>
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.markdown("---") # Linea di separazione elegante    
    st.title("🏥 Hub Salute")
    st.subheader("La mia Proprietà")
    menu = st.radio(
        "Navigazione",
        ["🏠 Home Dashboard", "💊 Gestione Farmaci", "🩸 Pressione e Salute", "📁 Documenti & Medici", "📅 Agenda Appuntamenti"]
    )
    # 2. QUI METTI IL LOGOUT (Fuori da ogni IF)
    st.markdown("---") # Linea di separazione
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.autenticato = False
        st.session_state.ruolo = None
        st.rerun()    
    
    st.markdown("---") # Una linea per separare bene
    # Usiamo un font piccolo e grigio per non disturbare troppo
    email_visualizzata = st.session_state.email
    st.caption(f"👤 Accesso autorizzato per:")
    st.info(f"{email_visualizzata}")    

    from docxtpl import DocxTemplate

def genera_report_docx(farmaci_da_ordinare):
    try:
        # Carichiamo il modello che hai messo su GitHub
        doc = DocxTemplate("test_report.docx")
        
        # Prepariamo i dati ("context") da iniettare nei tag {{ }}
        #
        context = {
            'data_oggi': datetime.now().strftime("%d/%m/%Y"),
            'farmaci': [
                {'nome': f.get('farmaco', ''), 'poso': f.get('posologia', '')} 
                for f in farmaci_da_ordinare
            ]
        }
        
        # Eseguiamo il "rendering" (il disegno si riempie di dati)
        doc.render(context)
        
        # Salviamo il risultato in memoria
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Errore nella creazione del file: {e}")
        return None
    
def genera_pdf_piano(dati_appwrite):
    try:
        doc = DocxTemplate("piano_terapeutico.docx")
        
        # 1. Definiamo l'ordine temporale desiderato
        ordine_pasti = {
            "Colazione": 1,
            "Mattina": 2,
            "Pranzo": 3,
            "Pomeriggio": 4,
            "Sera": 5,
            "Notte": 6
        }
        
        # 2. Ordiniamo la lista dei farmaci in base alla colonna 'quando'
        # Usiamo il metodo .get() così se un valore non è in lista finisce in fondo (99)
        documenti_ordinati = sorted(
            dati_appwrite, 
            key=lambda x: ordine_pasti.get(x.get('quando', ''), 99)
        )
        
        context = {
            'data_oggi': datetime.now().strftime('%d/%m/%Y'),
            'piano': documenti_ordinati  # Passiamo la lista ordinata
        }
        
        doc.render(context)
        
        target_stream = io.BytesIO()
        doc.save(target_stream)
        target_stream.seek(0)
        return target_stream
    except Exception as e:
        st.error(f"Errore ordinamento/generazione: {e}")
        return None

# --- 🏠 PAGINA 1: HOME DASHBOARD ---
if menu == "🏠 Home Dashboard":
    st.header("🏠 Centro di Controllo")

    # --- 1. WIDGET: STATO ASSUNZIONI OGGI ---
    try:
        oggi = str(datetime.now().date())
        res_oggi = databases.list_documents(
            database_id=DATABASE_ID, 
            collection_id="assunzioni_giornaliere",
            queries=[
                Query.equal("data", oggi),
                Query.equal("utente_email", st.session_state.email)
            ]
        )
        
        documenti = res_oggi.get('documents', [])
        
        if documenti:
            totale = len(documenti)
            presi = sum(1 for r in documenti if r['preso'])
            mancanti = totale - presi
            
            if mancanti > 0:
                st.info(f"💊 Oggi hai ancora **{mancanti}** farmaci da assumere su un totale di {totale}.")
            else:
                st.success("🌟 Ottimo lavoro! Hai completato tutte le assunzioni previste per oggi.")
        else:
            st.warning("⚠️ L'elenco delle medicine di oggi non è ancora stato generato.")
            
    except Exception as e:
        st.error(f"Errore nel riepilogo giornaliero: {e}")    
    
    st.divider()    

    #=======================================================================================
    # --- 📋 SEZIONE RIORDINO DOCTOLIB (VERSIONE SOCIO-PROOF) ---
    #=======================================================================================

    try:
        # Recuperiamo i farmaci filtrati per la tua email
        # Assicurati che st.session_state.email sia pieno!
        email_filtro = st.session_state.get('email', '')
        
        if not email_filtro:
            st.warning("Non trovo la tua email nella sessione. Prova a rifare il login.")
        else:
            res_all = databases.list_documents(
                database_id=DATABASE_ID,
                collection_id="armadietto_medicine",
                queries=[Query.equal("utente_email", email_filtro)]
            )
            
            tutti_i_farmaci = res_all.get('documents', [])
            
            # Filtriamo: entra in lista se ha il flag riordina=True OPPURE se quantità <= soglia
            farmaci_da_ordinare = []
            for f in tutti_i_farmaci:
                try:
                    riordina_flag = f.get('riordina', False)
                    quantita = float(f.get('quantita_attuale', 0))
                    soglia = float(f.get('soglia_allerta', 5))
                    
                    if riordina_flag or quantita <= soglia:
                        farmaci_da_ordinare.append(f)
                except (ValueError, TypeError):
                    # Se un valore non è un numero, lo saltiamo senza rompere tutto
                    continue
            
            if farmaci_da_ordinare:
                with st.container(border=True):
                    st.subheader("📦 Lista per Doctolib")
                    testo_report = "Buongiorno Dott.ssa, avrei bisogno delle seguenti prescrizioni:\n\n"
                    for f in farmaci_da_ordinare:
                        farmaco_nome = f.get('farmaco', 'Farmaco sconosciuto')
                        posologia = f.get('posologia', '')
                        testo_report += f"- {farmaco_nome} {posologia}\n"
                    
                    # 1. USIAMO UNA CHIAVE UNICA PER EVITARE L'ERRORE
                    st.text_area("Copia questo messaggio:", value=testo_report, height=150, key="area_doctolib")
                    
                    # 2. GENERAZIONE DEL FILE WORD (Solo se ci sono farmaci)
                    file_word = genera_report_docx(farmaci_da_ordinare)

                    if file_word:
                        st.download_button(
                            label="📄 Scarica Report per Dottoressa (Word)",
                            data=file_word,
                            file_name=f"Report_Farmaci_{datetime.now().strftime('%Y%m%d')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            key="btn_download_word" # Chiave unica anche qui
                        )
                    
                    st.divider()

                    if st.button("🗑️ Svuota lista (Prescrizioni inviate)", use_container_width=True, key="btn_reset_lista"):
                        for f in farmaci_da_ordinare:
                            databases.update_document(
                                database_id=DATABASE_ID, 
                                collection_id="armadietto_medicine", 
                                document_id=f['$id'], 
                                data={"riordina": False}
                            )
                        st.success("Lista resettata!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("Gestione riordini farmaci: le scorte sono a posto! Niente da ordinare per ora. ✅")
    except Exception as e:
        # Se l'errore persiste, qui vedremo il motivo esatto
        st.error(f"Errore nel generatore report: {e}")    
    # --- 2. PIANO TERAPEUTICO (DOCUMENTO) ---
    st.markdown("### 📄 Piano Terapeutico di Riferimento")
    try:
        # Recupero l'ultimo referto
        res_doc = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_ALLEGATI,
            queries=[
                Query.equal("tipo_documento", "Referto Medico"),
                Query.order_desc("data_documento"),
                Query.limit(1)
            ]
        )

        if res_doc['documents']:
            doc = res_doc['documents'][0]
            
            # Pulizia ID per evitare byte corrotti (0xe2, 0xc7, ecc.)
            f_id_raw = str(doc.get('file_id', ''))
            f_id = f_id_raw.encode('ascii', 'ignore').decode('ascii')
            
            col_doc1, col_doc2 = st.columns([3, 1])
            with col_doc1:
                st.info(f"📋 **Documento:** {doc.get('nome_file', 'Senza nome')}")
            
            with col_doc2:
                if f_id:
                    url_manuale = f"https://cloud.appwrite.io/v1/storage/buckets/{BUCKET_ALLEGATI}/files/{f_id}/view?project={PROJECT_ID}"
                    st.link_button("👁️ Apri", url_manuale, use_container_width=True)
                else:
                    st.error("ID mancante")
        else:
            st.warning("⚠️ Nessun documento recente trovato.")
    
    except Exception as e:
        st.error(f"Errore recupero documento: {e}")

    st.divider()

    # --- SEZIONE ESPORTAZIONE RAPIDA ---
    try:
        ID_REALE_PIANO = "piano_terapeutico" 
        risultato = databases.list_documents(DATABASE_ID, ID_REALE_PIANO)
        doc_stampa = risultato['documents']

        if doc_stampa: # Il pulsante appare solo se c'è qualcosa da stampare
            if st.button("📊 Genera Piano Terapeutico"):
                file_word = genera_pdf_piano(doc_stampa)
                if file_word:
                    st.download_button(
                        label="💾 Scarica File Word",
                        data=file_word,
                        # Nel download_button con data e ora
                        file_name=f"Piano_Terapeutico_{datetime.now().strftime('%d_%m_%Y_%H%M')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
    except Exception:
        # Se c'è un errore, in Dashboard non mostriamo nulla per non sporcare l'estetica
        pass

    # --- 3. SEZIONE URGENZE (SCORTE) ---
    try:
        res_f = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_ARMADIETTO
        )
        
        if res_f['documents']:
            df_arm_dash = pd.DataFrame(res_f['documents'])
            # Sicurezza sui valori numerici
            df_arm_dash['soglia_allerta'] = pd.to_numeric(df_arm_dash['soglia_allerta']).fillna(10)
            df_arm_dash['quantita_attuale'] = pd.to_numeric(df_arm_dash['quantita_attuale']).fillna(0)
            
            df_critici = df_arm_dash[df_arm_dash['quantita_attuale'] <= df_arm_dash['soglia_allerta']]
            
            if not df_critici.empty:
                st.subheader("🚨 Attenzione: Scorte in esaurimento")
                for _, row in df_critici.iterrows():
                    nome = row['farmaco']
                    q = row['quantita_attuale']
                    s = row['soglia_allerta']
                    
                    if q <= 0:
                        st.error(f"❌ **{nome}**: Esaurito!")
                    else:
                        st.warning(f"⚠️ **{nome}**: Solo {q} rimasti (soglia: {s})")
            else:
                st.success("✅ Tutte le scorte sono ok!")
        else:
            st.info("ℹ️ L'armadietto è vuoto.")
            
    except Exception as e:
        st.error(f"Errore controllo scorte Dashboard: {e}")
# --- 2. GRAFICO ANDAMENTO PRESSIONE ---
    st.subheader("📈 Andamento Pressione (Ultimi 20 Valori)")
    try:
        # 1. Recupero Pressione da Appwrite
        from appwrite.query import Query
        res_p = databases.list_documents(
            database_id=DATABASE_ID,          # Niente virgolette qui!
            collection_id=COLLECTION_PRESSIONE, # Niente virgolette qui!
            queries=[
                Query.order_desc("data_ora"),
                Query.limit(20)
            ]
        )
        
        if res_p['documents']:
            df_p = pd.DataFrame(res_p['documents'])
            
            # Conversione data e ordinamento per il grafico
            df_p['data_ora'] = pd.to_datetime(df_p['data_ora'])
            df_p = df_p.sort_values('data_ora')
            
            # Impostiamo l'indice per il grafico (usiamo la data formattata per l'asse X)
            chart_data = df_p.set_index('data_ora')[['sistolica', 'diastolica']]
            
            # Mostriamo il grafico
            st.line_chart(chart_data)
            
            # Calcolo media
            media_s = df_p['sistolica'].mean()
            if media_s > 140:
                st.warning(f"💡 Nota: La media sistolica è alta ({media_s:.1f}). Parlane con il medico.")
        else:
            st.info("Registra qualche valore di pressione per vedere il grafico!")
    except Exception as e:
        st.error(f"Errore nella generazione del grafico (Appwrite): {e}")
    
    st.divider()

    # --- 3. COLONNE DETTAGLIO ---
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Stato Scorte")
        # Qui usiamo df_critici che abbiamo calcolato nel passaggio precedente
        if not df_critici.empty:
            for _, f in df_critici.iterrows():
                st.warning(f"⚠️ **{f['farmaco']}** ({f['quantita_attuale']} rimasti)")
        else:
            st.success("✅ Tutte le scorte sono ok!")

    with col2:
        st.subheader("📅 Prossima Visita")
        try:
            # 1. Recupero Appuntamenti dalla collezione corretta
            res_app = databases.list_documents(
                database_id=DATABASE_ID,
                collection_id="appuntamenti", 
                queries=[
                    Query.equal("utente_email", st.session_state.email), 
                    Query.greater_than_equal("data_ora", pd.Timestamp.now().isoformat()),
                    Query.order_asc("data_ora"),
                    Query.limit(1)
                ]
            )
            
            if res_app['documents']:
                app = res_app['documents'][0]
                # Formattazione per la dashboard
                dt = pd.to_datetime(app['data_ora'])
                data_app = dt.strftime('%d/%m/%Y alle %H:%M')
                
                with st.container(border=True):
                    st.success(f"📌 **{app['specialista']}**")
                    st.write(f"🗓️ {data_app}")
                    # --- ✨ MOTORE METEO 2.1 (DASHBOARD) ---
                    if app.get('indirizzo'):
                        st.caption(f"📍 {app['indirizzo']}")
                        try:
                            import requests
                            import re
                            
                            # Pulizia robusta: prendiamo tutto quello che c'è dopo l'ultima virgola
                            parti = app['indirizzo'].split(',')
                            citta_raw = parti[-1] if len(parti) > 1 else parti[0]
                            # Rimuoviamo CAP e numeri
                            citta = re.sub(r'\d+', '', citta_raw).strip()
                            
                            if citta:
                                # Aggiungiamo &m per i Celsius e rimuoviamo eventuali spazi extra
                                meteo_res = requests.get(f"https://wttr.in/{citta}?format=%c+%t&m", timeout=4)
                                if meteo_res.status_code == 200 and "Unknown" not in meteo_res.text:
                                    # Puliamo il testo da eventuali segni + che a volte wttr.in mette davanti alla temperatura
                                    meteo_pulito = meteo_res.text.replace('+', '')
                                    st.write(f"🌤️ **Meteo a {citta.capitalize()}:** {meteo_pulito}")
                                    
                        except Exception:
                            # Se c'è un errore o timeout, non mostriamo nulla per non bloccare la Dashboard
                            pass                    
                        # -----------------------------------------------
            else:
                st.write("Nessun appuntamento imminente.")
                
        except Exception as e:
            st.error(f"Errore recupero appuntamenti: {e}")
# --- 💊 PAGINA 2: GESTIONE FARMACI ---
elif menu == "💊 Gestione Farmaci":
        
    # --- LOGICA ALERT SOTTOSCORTA (Anti-Pina) ---
    # Recuperiamo i dati aggiornati dall'armadietto
#----------------------------------------------------------------------------------------------------------------
# ATTENZIONE: QUESTA LOGICA DA QUI
#----------------------------------------------------------------------------------------------------------------
#    res_alert = supabase.table("armadietto_medicine").select("farmaco, quantita_attuale, soglia_allerta").eq("utente_email", st.session_state.email).execute()

#    if res_alert.data:
        # La chiusura ] va subito dopo la riga del confronto
#        sotto_soglia = [
#            f for f in res_alert.data 
#            if f['quantita_attuale'] <= (f['soglia_allerta'] if f['soglia_allerta'] is not None else 10)
#        ] # <--- DEVE STARE QUI!
#        
#        if sotto_soglia:
#            with st.container():
#                st.markdown("### 🚨 Attenzione: Scorte in esaurimento")
#                st.warning("### ⚠️ Alert Sottoscorta") # Più piccolo ed elegante
#                for f in sotto_soglia:
#                    st.write(f"👉 **{f['farmaco']}**: rimangono solo **{f['quantita_attuale']}** dosi (soglia: {f['soglia_allerta']})")
#                st.divider()
#----------------------------------------------------------------------------------------------------------------
# A QUI E' STATA DISATTIVATA SOLO FINO A QUANDO NON SI RIATTIVERA' TUTTO SOTTO APPWRITE
#----------------------------------------------------------------------------------------------------------------

    # Qui poi iniziano le tue Tab (Piano Terapeutico, Armadietto, ecc.)
    # --- FUNZIONI DI SUPPORTO ---
    def salva_piano(df_editato, email):
        try:
            dati = df_editato.to_dict(orient='records')
            for r in dati:
                # Se c'è un campo 'id' che viene da Appwrite (es. $id), lo gestiamo
                doc_id = r.get('$id') or 'unique()'
                # Puliamo i dati per Appwrite (togliamo le colonne tecniche se presenti)
                payload = {k: v for k, v in r.items() if not k.startswith('$')}
                payload['utente_email'] = email
                
                databases.update_document(
                    database_id=DATABASE_ID,
                    collection_id="piano_terapeutico",
                    document_id=doc_id,
                    data=payload
                )
            st.success("✅ Piano aggiornato su Appwrite!")
        except Exception as e:
            st.error(f"Errore nel salvataggio: {e}")
    # --- INTERFACCIA ---
    st.title("💊 Gestione Farmaci Evoluta")

    tab_piano, tab_armadietto, tab_assunzioni, tab_storico = st.tabs([
        "📅 Piano Terapeutico", 
        "📦 Armadietto", 
        "✅ Assunzioni Oggi",
        "📜 Storico"
    ])

    # 1. PIANO TERAPEUTICO
    with tab_piano:
        st.subheader("Configurazione Terapia Professionale")
        
        # 1. Recupero dati da Appwrite
        try:
            risultato = databases.list_documents(
                database_id=DATABASE_ID,
                collection_id="piano_terapeutico",
                queries=[Query.equal("utente_email", st.session_state.email)]
            )
            df_piano = pd.DataFrame(risultato['documents'])
            if df_piano.empty:
                df_piano = pd.DataFrame(columns=["farmaco", "posologia", "dosaggio", "quando", "rispetto_pasti", "note", "$id"])
        except Exception as e:
            st.error(f"Errore nel caricamento del piano: {e}")
            df_piano = pd.DataFrame(columns=["farmaco", "posologia", "dosaggio", "quando", "rispetto_pasti", "note", "$id"])

        # 2. Recupero nomi farmaci per la tendina (da Appwrite!)
        try:
            res_nomi = databases.list_documents(
                database_id=DATABASE_ID,
                collection_id="armadietto_medicine",
                queries=[Query.equal("utente_email", st.session_state.email)]
            )
            opzioni_farmaci = [f['farmaco'] for f in res_nomi['documents']] if res_nomi['documents'] else []
        except:
            opzioni_farmaci = []

        # 3. Configurazione Editor (Aggiungiamo la Frequenza!)
        config_professionale = {
            "farmaco": st.column_config.SelectboxColumn(
                    "💊 Farmaco", 
                    options=opzioni_farmaci, 
                    width="medium", 
                    required=True
                ),
            "posologia": st.column_config.TextColumn("🧪 Posologia", width="small"), 
            "dosaggio": st.column_config.NumberColumn("🔢 Q.tà", min_value=0.1, step=0.1, format="%.1f"),        
            "quando": st.column_config.SelectboxColumn("⏰ Quando", options=["Colazione", "Mattina", "Pomeriggio", "Sera", "Notte"]),
            
            # --- AGGIUNGI QUESTA RIGA QUI SOTTO ---
            "frequenza": st.column_config.SelectboxColumn("📅 Frequenza", options=["Giornaliera", "Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"], default="Giornaliera"),
            # ---------------------------------------

            "rispetto_pasti": st.column_config.SelectboxColumn("🍽️ Pasti", options=["Lontano dai Pasti", "Prima dei Pasti", "Dopo i Pasti"]),
            "note": st.column_config.TextColumn("📝 Note", width="medium"),
            "$id": None, 
            "utente_email": None
        }
        edit_piano = st.data_editor(
            df_piano,
            column_config=config_professionale,
            num_rows="dynamic",
            hide_index=True,
            # Aggiunta frequenza qui sotto:
            column_order=("farmaco", "posologia", "dosaggio", "quando", "frequenza", "rispetto_pasti", "note"),
            key="editor_appwrite_2026"
        )

        if st.button("💾 Salva Piano Terapeutico"):
            try:
                dati_raw = edit_piano.to_dict(orient='records')
                for r in dati_raw:
                    payload = {
                        "farmaco": r.get("farmaco"),
                        "posologia": r.get("posologia"),
                        "dosaggio": float(r.get("dosaggio", 1)),
                        "quando": r.get("quando"),
                        
                        # --- AGGIUNGI QUESTA RIGA ---
                        "frequenza": r.get("frequenza", "Giornaliera"), 
                        # ----------------------------

                        "rispetto_pasti": r.get("rispetto_pasti"),
                        "note": r.get("note") if r.get("note") else "",
                        "utente_email": st.session_state.email
                    }                    
                    doc_id = r.get("$id")
                    if doc_id: # Se esiste l'ID, aggiorniamo il record esistente
                        databases.update_document(
                            database_id=DATABASE_ID,
                            collection_id="piano_terapeutico",
                            document_id=doc_id,
                            data=payload
                        )
                    elif r.get("farmaco"): # Altrimenti ne creiamo uno nuovo
                        databases.create_document(
                            database_id=DATABASE_ID,
                            collection_id="piano_terapeutico",
                            document_id='unique()',
                            data=payload
                        )
                
                st.balloons()
                st.success("Salvataggio completato sulla Proprietà! 🚀")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Errore tecnico nel salvataggio: {e}")
    # 2. ARMADIETTO
    with tab_armadietto:
        st.subheader("📦 Gestione Scorte")
        
        # 1. Recupero dati da Appwrite
        # 1. Recupero dati da Appwrite
        try:
            res_a = databases.list_documents(
                database_id=DATABASE_ID,
                collection_id="armadietto_medicine",
                queries=[Query.equal("utente_email", st.session_state.email)]
            )
            df_arm = pd.DataFrame(res_a['documents'])
            
            # Gestione DataFrame vuoto
            if df_arm.empty:
                df_arm = pd.DataFrame(columns=["farmaco", "quantita_attuale", "soglia_allerta", "scadenza", "riordina", "posologia"])
            else:
                # --- ✨ IL TOCCO DEL SOCIO PROFESSIONISTA ---
                # Se la quantità è <= soglia, attiviamo il flag 'riordina' nel DataFrame
                def auto_check(row):
                    try:
                        qta = float(row.get('quantita_attuale', 0))
                        soglia = float(row.get('soglia_allerta', 5))
                        # Se è sotto soglia, forziamo True, altrimenti teniamo il valore del DB
                        if qta <= soglia:
                            return True
                        return bool(row.get('riordina', False))
                    except:
                        return bool(row.get('riordina', False))

                df_arm['riordina'] = df_arm.apply(auto_check, axis=1)
                # --------------------------------------------

                if 'scadenza' in df_arm.columns:
                    df_arm['scadenza'] = pd.to_datetime(df_arm['scadenza']).dt.date
                if 'posologia' not in df_arm.columns:
                    df_arm['posologia'] = ""
                    
        except Exception as e:
            st.warning("Configurazione armadietto in corso...")
            df_arm = pd.DataFrame(columns=["farmaco", "quantita_attuale", "soglia_allerta", "scadenza", "riordina", "posologia"])

        # --- RIFORNIMENTO RAPIDO (Corretto per Appwrite) ---
        with st.expander("➕ Carica Nuova Confezione (Rifornimento Rapido)"):
            col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
            with col_c1:
                elenco_f = df_arm['farmaco'].tolist() if not df_arm.empty else []
                f_scelto = st.selectbox("Seleziona farmaco acquistato", elenco_f, key="sel_refill")
            with col_c2:
                q_nuova = st.number_input("Pillole nella scatola", min_value=1, value=30, key="num_refill")
            with col_c3:
                st.write("##")
                if st.button("Carica Scorta", use_container_width=True):
                    try:
                        # Recupero riga e ID
                        riga = df_arm[df_arm['farmaco'] == f_scelto].iloc[0]
                        doc_id = riga['$id']
                        nuovo_totale = int(riga['quantita_attuale']) + int(q_nuova)
                        
                        # Aggiornamento Appwrite
                        databases.update_document(
                            database_id=DATABASE_ID,
                            collection_id="armadietto_medicine",
                            document_id=doc_id,
                            data={"quantita_attuale": float(nuovo_totale)}
                        )
                        st.toast(f"📦 {f_scelto} aggiornato!", icon="✅")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")
        
        st.divider()

        # 2. Configurazione Colonne Editor
        config_armadietto = {
            "riordina": st.column_config.CheckboxColumn("🛒", help="Seleziona per Doctolib", width="small"),
            "farmaco": st.column_config.TextColumn("💊 Farmaco", width="medium"),
            "posologia": st.column_config.TextColumn("📝 Posologia", width="medium"),
            "quantita_attuale": st.column_config.NumberColumn("🔢 Q.tà", width="small"),
            "soglia_allerta": st.column_config.NumberColumn("🚨 Soglia", width="small", help="Avvisa quando restano queste pillole"), # <--- RITORNATA!
            "scadenza": st.column_config.DateColumn("📅 Scadenza", format="DD/MM/YYYY", width="medium"),
            
            # Nascondiamo i campi di sistema
            "$id": None, "utente_email": None, "$collectionId": None, "$databaseId": None,
            "$createdAt": None, "$updatedAt": None, "$permissions": None
        }
        
        # 3. L'editor (Aggiungiamo la soglia nell'ordine visualizzato)
        edit_arm = st.data_editor(
            df_arm,
            column_config=config_armadietto,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="editor_armadietto_2026",
            column_order=("riordina", "farmaco", "posologia", "quantita_attuale", "soglia_allerta", "scadenza")
        )
        if st.button("💾 Aggiorna Armadietto"):
            # A. Gestione Cancellazioni
            state_editor = st.session_state.get("editor_armadietto_2026")
            if state_editor and "deleted_rows" in state_editor:
                for index in state_editor["deleted_rows"]:
                    try:
                        id_da_eliminare = df_arm.iloc[index]['$id']
                        databases.delete_document(DATABASE_ID, "armadietto_medicine", id_da_eliminare)
                    except: pass

            # B. Gestione Update / Insert
            dati_raw_arm = edit_arm.to_dict(orient='records')
            try:
                for r in dati_raw_arm:
                    payload = {
                        "farmaco": r.get("farmaco"),
                        "posologia": r.get("posologia", ""),
                        "quantita_attuale": float(r.get("quantita_attuale", 0)) if r.get("quantita_attuale") else 0.0,
                        "soglia_allerta": float(r.get("soglia_allerta", 5.0)) if r.get("soglia_allerta") else 5.0,
                        "scadenza": str(r.get("scadenza")) if pd.notna(r.get("scadenza")) else "",
                        "riordina": bool(r.get("riordina", False)),
                        "utente_email": st.session_state.email
                    }

                    doc_id = r.get("$id")
                    if doc_id and pd.notna(doc_id):
                        databases.update_document(DATABASE_ID, "armadietto_medicine", doc_id, payload)
                    elif r.get("farmaco"):
                        databases.create_document(DATABASE_ID, "armadietto_medicine", 'unique()', payload)
                
                st.toast('Progressi salvati!', icon='📈')
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Errore salvataggio: {e}")
    # 3. ASSUNZIONI GIORNALIERE (La tua "Lavagna")
# --- TAB 3: ASSUNZIONI GIORNALIERE ---
    with tab_assunzioni:
        data_sel = st.date_input(
            "Data di riferimento", 
            datetime.now().date(),
            format="DD/MM/YYYY"
        )        
        
        # 1. Recupero dati da Appwrite per la data selezionata
        # 1. Recupero dati da Appwrite per la data selezionata
        try:
            res_g = databases.list_documents(
                database_id=DATABASE_ID,
                collection_id="assunzioni_giornaliere",
                queries=[
                    Query.equal("data", str(data_sel)),
                    Query.equal("utente_email", st.session_state.email)
                ]
            )
            df_giornaliero = pd.DataFrame(res_g['documents'])
            
            # --- MOTORE DI GENERAZIONE (Logica Proprietà!) ---
            if df_giornaliero.empty:
                st.info(f"📌 Nessun piano per il {data_sel.strftime('%d/%m/%Y')}.")

                # Il pulsante appare solo se la giornata è vuota
                if st.button("🚀 GENERA ELENCO DA PIANO TERAPEUTICO", use_container_width=True):
                    try:
                        # --- NUOVO: Capire che giorno è la data selezionata ---
                        giorni_ita = {
                            0: "Lunedì", 1: "Martedì", 2: "Mercoledì", 
                            3: "Giovedì", 4: "Venerdì", 5: "Sabato", 6: "Domenica"
                        }
                        giorno_settimana_selezionato = giorni_ita[data_sel.weekday()]
                        # -----------------------------------------------------

                        # Peschiamo i farmaci "fissi" dal Piano Terapeutico
                        res_piano = databases.list_documents(
                            database_id=DATABASE_ID,
                            collection_id="piano_terapeutico",
                            queries=[Query.equal("utente_email", st.session_state.email)]
                        )
                        
                        if res_piano['documents']:
                            generati = 0 # Contatore per feedback
                            for f in res_piano['documents']:
                                
                                # --- NUOVO: Filtro Logica Proprietà (con la à!) ---
                                freq = f.get('frequenza', 'Giornaliera')
                                # Se freq è None o vuota, forziamo Giornaliera (per il passato)
                                if not freq: freq = 'Giornaliera'
                                
                                # Verifichiamo se deve essere inserito oggi
                                if freq == "Giornaliera" or freq == giorno_settimana_selezionato:
                                    databases.create_document(
                                        database_id=DATABASE_ID,
                                        collection_id="assunzioni_giornaliere",
                                        document_id='unique()',
                                        data={
                                            "farmaco": f['farmaco'],
                                            "momento": f['quando'],
                                            "dosaggio": float(f['dosaggio']),
                                            "data": str(data_sel),
                                            "preso": False,
                                            "posologia": f.get('posologia') if f.get('posologia') else "-",
                                            "utente_email": st.session_state.email
                                        }
                                    )
                                    generati += 1
                            
                            if generati > 0:
                                st.success(f"✅ Generato elenco con {generati} farmaci per {giorno_settimana_selezionato}!")
                            else:
                                st.warning(f"Nessun farmaco previsto per {giorno_settimana_selezionato}.")
                                
                            time.sleep(1)
                            st.rerun()

                        else:
                            st.warning("⚠️ Il tuo Piano Terapeutico è vuoto. Aggiungi prima dei farmaci lì!")
                    except Exception as e:
                        st.error(f"Errore durante la generazione: {e}")
                
                # Inizializziamo comunque il DF vuoto per non rompere il resto del codice sotto
                df_giornaliero = pd.DataFrame(columns=["$id", "farmaco", "momento", "dosaggio", "preso"])
            # ------------------------------------------------
            
        except Exception as e:
            st.error(f"Errore nel recupero assunzioni: {e}")
            df_giornaliero = pd.DataFrame(columns=["$id", "farmaco", "momento", "dosaggio", "preso"])
        else:
            # --- AGGIUNTA SOCIO: BLOCCO ELIMINAZIONE GIORNATA ---
            # Lo mettiamo qui in alto così è la prima cosa che vedi se devi correggere errori
            with st.popover("🗑️ Gestione Errori / Svuota Giornata", use_container_width=True):
                st.warning(f"Vuoi eliminare tutte le assunzioni del {data_sel.strftime('%d/%m/%Y')}?")
                st.write("Questa operazione è utile se hai generato l'elenco per errore o ci sono duplicati.")
                if st.button("🚨 ELIMINA TUTTO E RESETTA", type="primary", use_container_width=True):
                    try:
                        # Recuperiamo gli ID di oggi
                        per_eliminare = databases.list_documents(
                            database_id=DATABASE_ID,
                            collection_id="assunzioni_giornaliere",
                            queries=[Query.equal("data", str(data_sel)), Query.equal("utente_email", st.session_state.email)]
                        )
                        for doc in per_eliminare['documents']:
                            databases.delete_document(DATABASE_ID, "assunzioni_giornaliere", doc['$id'])
                        
                        st.success("Giornata resettata!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore reset: {e}")
            st.divider() 
            # ---------------------------------------------------

            # Se i dati ci sono, mostriamo l'editor per spuntare le assunzioni
            # Se i dati ci sono, mostriamo l'editor per spuntare le assunzioni (Logica Proprietà!)
            # Trasformiamo i documenti di Appwrite in DataFrame
            df_g = pd.DataFrame(res_g['documents'])
            
            # --- PROTEZIONE PER LA PROPRIETÀ ---
            # Se la tabella è vuota o manca la colonna 'preso', la creiamo al volo
            if df_g.empty:
                df_g = pd.DataFrame(columns=["id", "farmaco", "momento", "dosaggio", "preso"])
            
            if 'preso' not in df_g.columns:
                df_g['preso'] = False
            # -----------------------------------

            # Ordiniamo per momento
            ordine_momenti = {"Colazione": 0, "Mattina": 1, "Pomeriggio": 2, "Sera": 3, "Notte": 4}
            if 'momento' in df_g.columns:
                df_g['ordine'] = df_g['momento'].map(ordine_momenti).fillna(99)
                df_g = df_g.sort_values('ordine')

            st.subheader("✅ Spunta i farmaci presi")

            # --- GRAFICO A TORTA ---
            import plotly.express as px
            
            totale = len(df_g)
            # Convertiamo in booleano per sicurezza prima della somma
            presi = df_g['preso'].astype(bool).sum() 
            rimanenti = totale - presi            
            if totale > 0:
                dati_grafico = {"Stato": ["Presi", "Da Prendere"], "Numero": [presi, rimanenti]}
                fig = px.pie(dati_grafico, values='Numero', names='Stato', hole=0.4, color_discrete_sequence=['#2ecc71', '#e74c3c'])
                fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=200, showlegend=False)
                
                col_g1, col_g2 = st.columns([2, 1])
                with col_g1:
                    st.plotly_chart(fig, use_container_width=True)
                with col_g2:
                    st.metric("Progresso", f"{int((presi/totale)*100)}%")
                    st.write(f"✅ {presi} di {totale}")

            # Configurazione editor
            # --- PROTEZIONE COLONNE PER APPWRITE ---
            # Definiamo quali colonne vogliamo mostrare nell'ordine corretto
            colonne_desiderate = ["farmaco", "posologia", "dosaggio", "momento", "preso", "$id"]
            
            # Verifichiamo quali di queste esistono effettivamente nel DataFrame caricato
            colonne_effettive = [c for c in colonne_desiderate if c in df_g.columns]
            # ---------------------------------------

            edit_g = st.data_editor(
                df_g[colonne_effettive], 
                column_config={
                    "$id": None, # Nascondiamo l'ID di Appwrite
                    "farmaco": st.column_config.TextColumn("💊 Farmaco", disabled=True),
                    "posologia": st.column_config.TextColumn("🧪 Pos.", disabled=True),
                    "dosaggio": st.column_config.NumberColumn("🔢 Q.tà", disabled=True),
                    "momento": st.column_config.TextColumn("⏰ Quando", disabled=True),
                    "preso": st.column_config.CheckboxColumn("PRESO?", default=False)
                },
                use_container_width=True,
                hide_index=True,
                key="editor_giornaliero_evoluto"
            )            
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Salva Spunte (Temporaneo)", use_container_width=True):
                    dati_aggiornati = edit_g.to_dict(orient='records')
                    try:
                        for riga in dati_aggiornati:
                            # Aggiornamento su Appwrite usando l'ID del documento
                            databases.update_document(
                                database_id=DATABASE_ID,
                                collection_id="assunzioni_giornaliere",
                                document_id=riga['$id'],
                                data={"preso": bool(riga['preso'])}
                            )
                        st.balloons()
                        st.toast("Progressi salvati! 📈")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore durante il salvataggio: {e}")
            
            with col2:
                if st.button("🔒 CHIUDI LA GIORNATA (Archivia)", type="primary", use_container_width=True):
                    dati_per_scarico = edit_g.to_dict(orient='records')
                    try:
                        for r in dati_per_scarico:
                            # 1. ARCHIVIAZIONE NELLO STORICO (Nuova Logica Senior)
                            payload_storico = {
                                "data": str(data_sel),
                                "farmaco": r['farmaco'],
                                "momento": r['momento'],
                                "stato": "Preso" if r['preso'] else "Mancato", # <--- Usiamo la stringa!
                                "utente_email": st.session_state.email
                            }
                            databases.create_document(DATABASE_ID, "storico_assunzioni", 'unique()', payload_storico)
                            
                            # 2. SCARICO SCORTE DALL'ARMADIETTO (Solo se preso)
                            if r['preso']:
                                res_arm = databases.list_documents(
                                    database_id=DATABASE_ID,
                                    collection_id="armadietto_medicine",
                                    queries=[
                                        Query.equal("utente_email", st.session_state.email),
                                        Query.equal("farmaco", r['farmaco'])
                                    ]
                                )
                                
                                if res_arm['documents']:
                                    doc_arm = res_arm['documents'][0]
                                    attuale = float(doc_arm.get('quantita_attuale', 0))
                                    da_togliere = float(r.get('dosaggio', 1))
                                    nuova_qta = attuale - da_togliere
                                    
                                    databases.update_document(
                                        database_id=DATABASE_ID,
                                        collection_id="armadietto_medicine",
                                        document_id=doc_arm['$id'],
                                        data={"quantita_attuale": nuova_qta}
                                    )

                            # 3. PULIZIA: Eliminiamo la riga dalle assunzioni giornaliere
                            databases.delete_document(DATABASE_ID, "assunzioni_giornaliere", r['$id'])

                        st.balloons()
                        st.success("Giornata archiviata e armadietto aggiornato!")
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Errore durante l'archiviazione: {e}")
    # 4. STORICO
    with tab_storico:
        st.subheader(" Registro Storico Definitivo")
        
        # 1. Recupero dati dallo STORICO su Appwrite
        try:
            res_s = databases.list_documents(
                database_id=DATABASE_ID,
                collection_id="storico_assunzioni",
                queries=[
                    Query.equal("utente_email", st.session_state.email),
                    Query.order_desc("data"), # Ordina dalla più recente
                    Query.limit(100)           # Prendiamo gli ultimi 100 record
                ]
            )
            
            if res_s['documents']:
                df_storico = pd.DataFrame(res_s['documents'])
                
                # --- PULIZIA DATI PER VISUALIZZAZIONE ---
                # Selezioniamo solo le colonne che ci interessano, usando 'stato' e non 'preso'
            # --- ✨ IL TOCCO SENIOR: FORMATTAZIONE DATA ---
                # Trasformiamo la data da AAAA-MM-GG a GG/MM/AAAA
                df_storico['data'] = pd.to_datetime(df_storico['data']).dt.strftime('%d/%m/%Y')
                # ----------------------------------------------                
                colonne_da_mostrare = ["data", "farmaco", "momento", "stato"]
                # Filtriamo solo le colonne presenti per evitare errori
                esistenti = [c for c in colonne_da_mostrare if c in df_storico.columns]
                
                # 2. VISUALIZZAZIONE TABELLA
                st.dataframe(
                    df_storico[esistenti],
                    use_container_width=True,
                    hide_index=True
                )
                
                # 3. UN PICCOLO PLUS DA SENIOR: MINI STATISTICA
                presi = len(df_storico[df_storico['stato'] == "Preso"])
                totali = len(df_storico)
                st.info(f"💡 Nelle ultime rilevazioni hai assunto correttamente il **{int((presi/totali)*100)}%** dei farmaci.")
                
            else:
                st.info("📜 Lo storico è ancora vuoto. Archivia la tua prima giornata per vedere i dati qui!")
                
        except Exception as e:
            st.error(f"Errore nel caricamento dello storico: {e}")
            df_storico = pd.DataFrame(columns=["data", "farmaco", "momento", "stato"])
# --- 🩸 PAGINA 3: PARAMETRI VITALI ---
elif menu == "🩸 Pressione e Salute":
    st.header("🩸 Monitoraggio Salute e Parametri Vitali")
    st.write("##") # Un po' di respiro visivo    
    # Creiamo due Tab per non affollare la pagina: una per i Form e una per i Grafici
    tab_registra, tab_storico = st.tabs(["📝 Nuova Misurazione", "📈 Grafici e Analisi"])

    with tab_registra:
        # --- SEZIONE PRESSIONE ---
        with st.expander("🩸 Inserisci Misurazione Pressione", expanded=True):
            with st.form("form_pressione", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    sis = st.number_input("Sistolica (Massima)", min_value=40, max_value=250, value=120)
                with col2:
                    dia = st.number_input("Diastolica (Minima)", min_value=30, max_value=150, value=80)
                with col3:
                    puls = st.number_input("Battiti (Pulsazioni)", min_value=30, max_value=200, value=70)
                
                note_pressione = st.text_input("Note (es: appena sveglio, dopo caffè)")
                submit_pressione = st.form_submit_button("Registra Pressione")

                if submit_pressione:
                    # Prepariamo i dati per Appwrite
                    nuova_misurazione = {
                        "sistolica": sis, 
                        "diastolica": dia, 
                        "pulsazioni": puls,
                        "note": note_pressione, 
                        "data_ora": pd.Timestamp.now().isoformat(), # Aggiungiamo il timestamp attuale
                        "utente_email": st.session_state.email
                    }
                    try:
                        # USIAMO APPWRITE
                        databases.create_document(
                            database_id=DATABASE_ID,
                            collection_id=COLLECTION_PRESSIONE,
                            document_id='unique()',
                            data=nuova_misurazione
                        )
                        st.success(f"✅ Misurazione registrata: {sis}/{dia} mmHg")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore nel salvataggio pressione su Appwrite: {e}")

        # --- SEZIONE GLICEMIA ---
        with st.expander("🩸 Registra Glicemia", expanded=False):
            with st.form("form_glicemia", clear_on_submit=True):
                val_glic = st.number_input(
                    "Valore (mg/dL)", 
                    min_value=30.0, 
                    max_value=500.0, 
                    value=100.0, 
                    step=0.1  # <--- Questo permette di inserire i decimali con i tastini + e -
                )
                momento = st.selectbox("Momento della misurazione", ["Digiuno", "Prima di pranzo", "Dopo pranzo", "Prima di cena", "Dopo cena", "Prima di dormire"])
                note_g = st.text_input("Note (es: dopo dolce)")
                if st.form_submit_button("Salva Glicemia"):
                    dati_g = {
                        "valore": val_glic, 
                        "momento": momento, 
                        "note": note_g,
                        "data_ora": pd.Timestamp.now().isoformat(),
                        "utente_email": st.session_state.email
                    }
                    try:
                        # USIAMO APPWRITE (Assicurati di aver definito COLLECTION_GLICEMIA)
                        databases.create_document(
                            database_id=DATABASE_ID,
                            collection_id="glicemia", # ID collezione su Appwrite
                            document_id='unique()',
                            data=dati_g
                        )
                        st.success("✅ Glicemia registrata!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore salvataggio glicemia: {e}")
    with tab_storico:
        st.subheader("📊 Analisi Andamento Temporale")
        
        # --- LOGICA RECUPERO E GRAFICI PRESSIONE (APPWRITE) ---
        try:
            res_p = databases.list_documents(
                database_id=DATABASE_ID,
                collection_id="pressione_arteriosa",
                queries=[
                    Query.equal("utente_email", st.session_state.email),
                    Query.order_asc("$createdAt"),
                    Query.limit(100) # Prendiamo gli ultimi 100 per il grafico
                ]
            )
            
            if res_p['documents']:
                df_p = pd.DataFrame(res_p['documents'])
                # Usiamo $createdAt di Appwrite per la timeline
                df_p['data_ora_formattata'] = pd.to_datetime(df_p['$createdAt']).dt.strftime('%d/%m %H:%M')
                
                st.write("📈 **Andamento Pressione (Massima e Minima)**")
                # Grafico a linee
                st.line_chart(
                    df_p.set_index('data_ora_formattata')[['sistolica', 'diastolica']], 
                    color=["#FF4B4B", "#007BFF"]
                )
                
                with st.expander("📄 Vedi Tabella Pressione"):
                    st.dataframe(
                        df_p[['data_ora_formattata', 'sistolica', 'diastolica', 'pulsazioni', 'note']], 
                        use_container_width=True, 
                        hide_index=True
                    )
            else:
                st.info("Nessun dato di pressione per i grafici.")
        except Exception as e:
            st.error(f"Errore Grafico Pressione: {e}")

        st.divider()

        # --- LOGICA RECUPERO E GRAFICI GLICEMIA (APPWRITE) ---
        try:
            res_g = databases.list_documents(
                database_id=DATABASE_ID,
                collection_id="glicemia",
                queries=[
                    Query.equal("utente_email", st.session_state.email),
                    Query.order_asc("$createdAt"),
                    Query.limit(100)
                ]
            )
            
            if res_g['documents']:
                df_g = pd.DataFrame(res_g['documents'])
                df_g['data_ora_formattata'] = pd.to_datetime(df_g['$createdAt']).dt.strftime('%d/%m %H:%M')
                
                st.write("📈 **Andamento Glicemia (mg/dL)**")
                # Grafico ad area (scenografico come piace a noi Senior!)
                st.area_chart(df_g.set_index('data_ora_formattata')['valore'], color="#FFAA00")
                
                # Gestione eliminazione (Bidoncini)
                st.write("### 🗑️ Gestione Record Glicemia")
                # Mostriamo gli ultimi 5 (invertiamo l'ordine della lista documenti)
                ultimi_5 = res_g['documents'][::-1][:5]
                
                for g in ultimi_5:
                    c_info, c_del = st.columns([4, 1])
                    with c_info:
                        data_g = pd.to_datetime(g['$createdAt']).strftime('%d/%m %H:%M')
                        st.caption(f"📅 {data_g} - **{g['valore']} mg/dL** ({g.get('momento', '-')})")
                    with c_del:
                        # Usiamo $id di Appwrite per la cancellazione
                        if st.button("🗑️", key=f"del_g_{g['$id']}"):
                            databases.delete_document(
                                database_id=DATABASE_ID,
                                collection_id="glicemia",
                                document_id=g['$id']
                            )
                            st.toast("Record eliminato!")
                            time.sleep(1)
                            st.rerun()
            else:
                st.info("Nessun dato di glicemia per i grafici.")
        except Exception as e:
            st.error(f"Errore Grafico Glicemia: {e}")

# --- 📁 PAGINA 4: DOCUMENTI & MEDICI ---
elif menu == "📁 Documenti & Medici":
    st.header("📁 Archivio e Contatti")
    tab1, tab_ric, tab2 = st.tabs(["📄 Documenti", "🏥 Ricoveri", "👨‍⚕️ Medici"])
    with tab1:
        st.subheader("📄 Archivio Documenti e Referti")

        # Recupero specialità dal DB (assumendo che la tabella si chiami 'specialita' e il campo 'nome')
        try:
            res_spec = databases.list_documents(
                DATABASE_ID, 
                "COLLECTION_SPECIALITA", # <--- CAMBIA QUESTO!
                queries=[Query.limit(100)]
            )
            lista_specialita = sorted([d['nome'] for d in res_spec['documents']])
        except Exception as e:
            st.error(f"Errore nel caricamento specialità: {e}")
            lista_specialita = ["Generale", "Altro"] # Fallback di sicurezza

        # Lista anni - Ottimo l'uso del range, socio!
        lista_anni = list(range(2030, 1999, -1))


        # --- 1. CARICAMENTO (NUOVO METODO) ---
        with st.expander("📤 Carica Nuovo Documento"):
            c1, c2, c3 = st.columns(3)
            with c1:
                t_doc = st.selectbox("Tipo Documento", ["Referto Medico", "Ricetta", "Esami", "Ricovero", "Altro"], key="new_tipo")
            with c2:
                s_doc = st.selectbox("Specialità Medica", lista_specialita, key="new_spec")
            with c3:
                # Usiamo l'anno corrente come default per comodità
                anno_corrente = pd.Timestamp.now().year
                idx_anno = lista_anni.index(anno_corrente) if anno_corrente in lista_anni else 0
                a_doc = st.selectbox("Anno", lista_anni, index=idx_anno, key="new_anno")

            d_doc = st.date_input("Data Effettiva", value=None, format="DD/MM/YYYY", key="new_data")
            f_up = st.file_uploader("File", type=['pdf', 'jpg', 'png'], key="new_file")
            
            if st.button("Salva nell'Archivio", key="save_btn"):
                if f_up and d_doc:
                    try:
                        n_safe = "".join([c for c in f_up.name if c.isalnum() or c in "._-"])
                        res_st = storage.create_file(BUCKET_ALLEGATI, 'unique()', 
                                                InputFile.from_bytes(f_up.getvalue(), filename=n_safe))
                        
                        databases.create_document(DATABASE_ID, COLLECTION_ALLEGATI, 'unique()',
                            data={
                                "nome_file": n_safe, 
                                "tipo_documento": t_doc, 
                                "categoria": t_doc, # Manteniamo coerenza con il tuo vecchio campo
                                "specialita": s_doc, # <--- NUOVO CAMPO
                                "anno": a_doc,        # <--- NUOVO CAMPO
                                "data_documento": d_doc.isoformat(), 
                                "file_id": res_st['$id'], 
                                "utente_email": st.session_state.email
                            })
                        st.success("Documento archiviato con successo!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore nel salvataggio: {e}")


        # --- 2. LISTA E GESTIONE ---
        st.subheader("🔍 I tuoi referti salvati")
        try:
            res_docs = databases.list_documents(
                DATABASE_ID, 
                COLLECTION_ALLEGATI,
                [
                    Query.equal("utente_email", st.session_state.email),
                    Query.order_desc("data_documento") 
                ]
            )
            
            docs_raw = res_docs.get('documents', [])
            
            if docs_raw:
                # --- ✨ 1. MINI-CARD RIASSUNTIVE (KPI) ---
                t_ref = sum(1 for d in docs_raw if (d.get('categoria') or d.get('tipo_documento')) == "Referto Medico")
                t_esa = sum(1 for d in docs_raw if (d.get('categoria') or d.get('tipo_documento')) == "Esami")
                t_ric = sum(1 for d in docs_raw if (d.get('categoria') or d.get('tipo_documento')) == "Ricetta")
                t_alt = sum(1 for d in docs_raw if (d.get('categoria') or d.get('tipo_documento')) == "Altro")

                k_col1, k_col2, k_col3, k_col4 = st.columns(4)
                with k_col1:
                    st.markdown(f'<div style="background-color: #f0f7ff; padding: 10px; border-radius: 10px; border-left: 5px solid #007bff; text-align: center;"><p style="color: #007bff; font-size: 13px; margin: 0;">📄 Referti</p><h3 style="margin: 0; color: #1e3a8a;">{t_ref}</h3></div>', unsafe_allow_html=True)
                with k_col2:
                    st.markdown(f'<div style="background-color: #fff5f5; padding: 10px; border-radius: 10px; border-left: 5px solid #dc3545; text-align: center;"><p style="color: #dc3545; font-size: 13px; margin: 0;">💉 Esami</p><h3 style="margin: 0; color: #7a1b1b;">{t_esa}</h3></div>', unsafe_allow_html=True)
                with k_col3:
                    st.markdown(f'<div style="background-color: #f6fff6; padding: 10px; border-radius: 10px; border-left: 5px solid #28a745; text-align: center;"><p style="color: #28a745; font-size: 13px; margin: 0;">💊 Ricette</p><h3 style="margin: 0; color: #1b5e20;">{t_ric}</h3></div>', unsafe_allow_html=True)
                with k_col4:
                    st.markdown(f'<div style="background-color: #fffaf0; padding: 10px; border-radius: 10px; border-left: 5px solid #f39c12; text-align: center;"><p style="color: #f39c12; font-size: 13px; margin: 0;">📁 Altro</p><h3 style="margin: 0; color: #8a5a00;">{t_alt}</h3></div>', unsafe_allow_html=True)
                
                st.write("---")

                # --- ✨ 2. TIMELINE VISIVA ---
                try:
                    df_docs = pd.DataFrame(docs_raw)
                    df_docs['dt'] = pd.to_datetime(df_docs['data_documento'])
                    df_docs['Periodo'] = df_docs['dt'].dt.strftime('%m/%Y')
                    timeline = df_docs.groupby('Periodo').size()
                    
                    with st.expander("📊 Analisi Temporale Caricamenti", expanded=False):
                        st.bar_chart(timeline, color="#007bff")
                except Exception:
                    pass

                # --- ✨ 3. ORDINAMENTO E RICERCA ---
                c1, c2 = st.columns([1.5, 3])
                with c1:
                    ordine = st.selectbox("Ordina per:", ["Recente", "Vecchio", "Nome A-Z"], label_visibility="collapsed")
                with c2:
                    search_q = st.text_input("Cerca...", placeholder="Filtra documenti...", label_visibility="collapsed")

                # Filtro Ricerca
                docs_filtrati = [
                    d for d in docs_raw 
                    if search_q.lower() in d.get('nome_file', '').lower() 
                    or search_q.lower() in d.get('categoria', d.get('tipo_documento', '')).lower()
                ]

                # Logica Ordinamento
                if ordine == "Vecchio":
                    docs_filtrati.sort(key=lambda x: x.get('data_documento', ''))
                elif ordine == "Nome A-Z":
                    docs_filtrati.sort(key=lambda x: x.get('nome_file', '').lower())
                # "Recente" è già l'ordine di default di docs_raw

                if docs_filtrati:
                    st.caption(f"Visualizzazione di {len(docs_filtrati)} elementi")
                    
                    for i, d in enumerate(docs_filtrati):
                        f_id = str(d.get('file_id', '')).encode('ascii', 'ignore').decode('ascii')
                        doc_id = str(d.get('$id', '')).encode('ascii', 'ignore').decode('ascii')
                        nome_doc = d.get('nome_file', 'Documento')
                        
                        try:
                            data_formattata = pd.to_datetime(d.get('data_documento')).strftime('%d/%m/%Y')
                        except:
                            data_formattata = d.get('data_documento', 'N.D.')
                        
                        cat_val = d.get('categoria') 
                        cat = cat_val if cat_val else d.get('tipo_documento', 'Altro')
                        
                        colore_tag = "#6c757d"
                        if cat == "Referto Medico": colore_tag = "#007bff"
                        elif cat == "Ricetta": colore_tag = "#28a745"
                        elif cat == "Esami": colore_tag = "#dc3545"
                        # Nella logica dei colori aggiungiamo il Ricovero
                        elif cat == "Ricovero": colore_tag = "#6f42c1"  # Un bel Viola istituzionale    
                        elif cat == "Altro": colore_tag = "#f39c12"

                        # Tooltip per la finezza finale
                        estensione = nome_doc.split('.')[-1].upper() if '.' in nome_doc else "FILE"
                        tip = f"Formato: {estensione} | ID: {f_id[:6]}"

                        with st.container(border=True):
                            c_info, c_open, c_del = st.columns([4, 1.2, 0.8])
                            with c_info:
                                # Tooltip applicato al nome del file
                                st.markdown(f"📄 **{nome_doc}**", help=tip)
                                st.markdown(f'''
                                    <div style="display: flex; align-items: center; gap: 8px; margin-top: -10px;">
                                        <span style="background-color:{colore_tag}; color:white; padding:1px 10px; 
                                        border-radius:10px; font-size:10px; font-weight:bold; text-transform:uppercase;">
                                            {cat}
                                        </span>
                                        <span style="color:gray; font-size:11px;">📅 {data_formattata}</span>
                                    </div>
                                    ''', unsafe_allow_html=True)
                            
                            with c_open:
                                url_manuale = f"https://cloud.appwrite.io/v1/storage/buckets/{BUCKET_ALLEGATI}/files/{f_id}/view?project={PROJECT_ID}"
                                st.link_button("👁️ Apri", url_manuale, use_container_width=True)
                            
                            with c_del:
                                if st.button("🗑️", key=f"del_{doc_id}_{i}", use_container_width=True):
                                    databases.delete_document(DATABASE_ID, COLLECTION_ALLEGATI, doc_id)
                                    storage.delete_file(BUCKET_ALLEGATI, f_id)
                                    st.rerun()
                else:
                    st.warning("Nessun documento trovato.")
            else:
                st.info("Nessun documento trovato.")

        except Exception as e:
            st.error(f"Errore generale: {e}")
    #======================================================================================================================
    # Fine del tab1
    #======================================================================================================================         
    with tab_ric:
        st.subheader("🏥 Storico Ricoveri e Ospedalizzazioni")
        st.info("In questa sezione sono raccolti esclusivamente i documenti relativi a degenze, interventi e dimissioni.")

        try:
            # Recuperiamo i documenti filtrando SOLO per la categoria "Ricovero"
            res_ric = databases.list_documents(
                DATABASE_ID, 
                COLLECTION_ALLEGATI,
                [
                    Query.equal("utente_email", st.session_state.email),
                    Query.equal("categoria", "Ricovero"), 
                    Query.order_desc("data_documento")
                ]
            )
            
            docs_ric = res_ric.get('documents', [])
            
            if docs_ric:
                # Una piccola card riassuntiva solo per i ricoveri
                st.markdown(f"""
                    <div style="background-color: #f8f4ff; padding: 15px; border-radius: 10px; border-left: 5px solid #6f42c1; margin-bottom: 20px;">
                        <span style="color: #6f42c1; font-weight: bold;">📊 Totale Eventi: {len(docs_ric)}</span>
                    </div>
                """, unsafe_allow_html=True)

                for i, d in enumerate(docs_ric):
                    f_id = str(d.get('file_id', '')).encode('ascii', 'ignore').decode('ascii')
                    doc_id = str(d.get('$id', '')).encode('ascii', 'ignore').decode('ascii')
                    nome_doc = d.get('nome_file', 'Documento Ricovero')
                    
                    try:
                        data_f = pd.to_datetime(d.get('data_documento')).strftime('%d/%m/%Y')
                    except:
                        data_f = d.get('data_documento', 'N.D.')

                    with st.container(border=True):
                        c_icon, c_txt, c_btn = st.columns([0.5, 3.5, 1.5])
                        with c_icon:
                            st.write("💜") # Un cuore viola o un'icona sobria
                        with c_txt:
                            st.markdown(f"**{nome_doc}**")
                            st.caption(f"📅 Data Dimissione/Evento: {data_f}")
                        with c_btn:
                            url_ric = f"https://cloud.appwrite.io/v1/storage/buckets/{BUCKET_ALLEGATI}/files/{f_id}/view?project={PROJECT_ID}"
                            st.link_button("👁️ Esamina", url_ric, use_container_width=True)
            else:
                st.warning("Nessun verbale di ricovero presente in archivio.")
                st.caption("Per visualizzare un documento qui, caricalo nella sezione 'Documenti' selezionando la categoria 'Ricovero'.")

        except Exception as e:
            st.error(f"Errore nel recupero ricoveri: {e}")
    with tab2:
    #======================================================================================================================
    # Gestione Medici e Specialità
    #======================================================================================================================         
        st.subheader("👨‍⚕️ I Tuoi Contatti Medici")
        st.info("Puoi modificare i dati direttamente nella tabella. Ricorda di cliccare 'Salva' per rendere attive le chiamate e WhatsApp.")

        # 1. RECUPERO DATI DA APPWRITE
        try:
            # Leggiamo i medici da Appwrite
            res_m = databases.list_documents(
                database_id=DATABASE_ID,
                collection_id=COLLECTION_MEDICI,
                queries=[Query.equal("utente_email", st.session_state.email), Query.order_asc("nome_dottore")]
            )
            df_medici = pd.DataFrame(res_m['documents'])
            
            # Leggiamo la lista ufficiale delle specialità
            res_s = databases.list_documents(
                database_id=DATABASE_ID,
                collection_id=COLLECTION_SPECIALITA,
                # Tutte le query vanno dentro le stesse parentesi quadre []
                queries=[
                    Query.limit(100),                   # massimo numero di righe da visualizzare nella combo
                    Query.order_asc("nome")             # ordinamento
                ]
            )
            opzioni_finali = [r['nome'] for r in res_s['documents']]
        except Exception as e:
            st.error(f"Errore caricamento da Appwrite: {e}")
            df_medici = pd.DataFrame(columns=["$id", "nome_dottore", "specializzazione", "telefono", "email", "clinica_ospedale"])
            opzioni_finali = ["Medicina di Base"]

        # --- INSERIMENTO RAPIDO ---
        with st.expander("➕ Gestione Anagrafica e Specialità", expanded=False):
            tab_m, tab_s = st.tabs(["Nuovo Medico", "Nuova Specialità"])
            
            with tab_m:
                c1, c2 = st.columns(2)
                with c1:
                    n_nome = st.text_input("Nome Medico", key="add_n")
                    n_tel = st.text_input("Telefono", key="add_t")
                with c2:
                    n_spec = st.selectbox("Specializzazione", options=opzioni_finali, key="add_s")
                    if st.button("Salva Medico", use_container_width=True):
                        new_m = {
                            "nome_dottore": n_nome, 
                            "specializzazione": n_spec, 
                            "telefono": n_tel, 
                            "utente_email": st.session_state.email
                        }
                        databases.create_document(DATABASE_ID, COLLECTION_MEDICI, 'unique()', new_m)
                        st.success("Medico aggiunto su Appwrite!")
                        st.rerun()

            with tab_s:
                nuova_voce = st.text_input("Inserisci nuova specialità (es. Geriatria)")
                if st.button("Aggiungi all'elenco ufficiale"):
                    if nuova_voce:
                        databases.create_document(DATABASE_ID, COLLECTION_SPECIALITA, 'unique()', {"nome": nuova_voce})
                        st.success(f"'{nuova_voce}' aggiunta!")
                        st.rerun()

        st.divider()

        # --- LOGICA LINK DINAMICI (Invariata, è ottima!) ---
        def crea_link_tel(n):
            if not n or str(n).strip() == "": return None
            return f"tel:{str(n).strip().replace(' ', '')}"

        def crea_link_wa(n):
            if not n or str(n).strip() == "": return None
            tel = str(n).strip().replace(" ", "")
            tel_wa = tel if tel.startswith(('+', '00')) else f"39{tel}"
            msg = urllib.parse.quote("Buongiorno Dottore, le scrivo dall'App Hub Salute.")
            return f"https://wa.me/{tel_wa}?text={msg}"

        if not df_medici.empty:
            df_medici['📞 Chiama'] = df_medici['telefono'].apply(crea_link_tel)
            df_medici['💬 WhatsApp'] = df_medici['telefono'].apply(crea_link_wa)
        else:
            # DF vuoto ma con colonne pronte
            df_medici = pd.DataFrame(columns=["$id", "nome_dottore", "specializzazione", "telefono", "email", "clinica_ospedale", "📞 Chiama", "💬 WhatsApp"])

        # 2. CONFIGURAZIONE COLONNE
        config_medici = {
            "nome_dottore": st.column_config.TextColumn("👤 Medico", required=True),
            "specializzazione": st.column_config.SelectboxColumn("🩺 Specialità", options=opzioni_finali, required=True),            
            "telefono": st.column_config.TextColumn("📱 Numero"),
            "email": st.column_config.TextColumn("📧 Email"),
            "clinica_ospedale": st.column_config.TextColumn("🏥 Clinica"),
            "📞 Chiama": st.column_config.LinkColumn("📞 Chiama", display_text="📞 Chiama"),
            "💬 WhatsApp": st.column_config.LinkColumn("💬 WhatsApp", display_text="💬 WA"),
            "$id": None, "utente_email": None # Nascondiamo i campi tecnici
        }

        # 3. EDITOR
        edit_medici = st.data_editor(
            df_medici,
            column_config=config_medici,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            key="editor_medici_appwrite"
        )
        
        # 4. SALVATAGGIO MODIFICHE (Versione Appwrite)
        if st.button("💾 Salva Modifiche Tabella", use_container_width=True):
            dati_raw = edit_medici.to_dict(orient='records')
            
            for r in dati_raw:
                if not r.get("nome_dottore"): continue

                record = {
                    "nome_dottore": r.get("nome_dottore"),
                    "specializzazione": r.get("specializzazione"),
                    "telefono": str(r.get("telefono", "")),
                    "email": r.get("email"),
                    "clinica_ospedale": r.get("clinica_ospedale"),
                    "utente_email": st.session_state.email
                }
                
                doc_id = r.get("$id") # Appwrite usa $id
                
                try:
                    if pd.notna(doc_id) and str(doc_id).strip() != "":
                        databases.update_document(DATABASE_ID, COLLECTION_MEDICI, doc_id, record)
                    else:
                        databases.create_document(DATABASE_ID, COLLECTION_MEDICI, 'unique()', record)
                except Exception as e:
                    st.error(f"Errore su {r.get('nome_dottore')}: {e}")

            st.balloons()
            st.success("Salvataggio completato! 🎉")
            time.sleep(1)
            st.rerun()
# --- 📅 PAGINA 5: AGENDA (VERSIONE MAPPA PRO) ---
# --- 📅 PAGINA 5: AGENDA (VERSIONE FULL OPTIONAL) ---
elif menu == "📅 Agenda Appuntamenti":
    st.header("📅 Agenda Appuntamenti Medici")

    if "form_reset" not in st.session_state:
        st.session_state.form_reset = 0

    with st.expander("➕ Segna Nuovo Appuntamento"):
        with st.form("form_appuntamento", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                data_app = st.date_input("Giorno", format="DD/MM/YYYY")
            with col2:
                ora_app = st.time_input("Ora")
                
            col3, col4 = st.columns(2)
            with col3:
                opzioni_specialisti = ["Oculista", "Dentista", "Cardiologo", "Dermatologo", "Medico di base", "Ortopedico", "Altro..."]
                specialista = st.selectbox("Tipo di Visita", opzioni_specialisti)
            with col4:
                opzioni_luogo = ["Studio Privato", "Ospedale", "Clinica", "ASL", "Domicilio"]
                luogo = st.selectbox("Luogo", opzioni_luogo)
            
            indirizzo = st.text_input("📍 Indirizzo esatto (es: Via Roma 1, Milano)")
            nome_medico = st.text_input("Nome del Medico (Dott. / Dott.ssa)")
            motivo = st.text_area("Motivo della visita / Note particolari")
            
            submit_app = st.form_submit_button("Salva in Agenda")
            
            if submit_app:
                try:
                    data_ora_completato = f"{data_app} {ora_app}"
                    info_visita = f"{specialista} - {nome_medico}" if nome_medico else specialista
                    
                    nuovo_app = {
                        "data_ora": data_ora_completato,
                        "specialista": info_visita,
                        "luogo": luogo,
                        "indirizzo": indirizzo,
                        "motivo": motivo,
                        "utente_email": st.session_state.email
                    }
                    
                    databases.create_document(
                        database_id=DATABASE_ID,
                        collection_id="appuntamenti",
                        document_id='unique()',
                        data=nuovo_app
                    )
                    st.success("Appuntamento salvato!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore nel salvataggio: {e}")

    # --- VISUALIZZAZIONE PROSSIMI APPUNTAMENTI ---
    try:
        res_app = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id="appuntamenti",
            queries=[
                Query.equal("utente_email", st.session_state.email),
                Query.order_asc("data_ora")
            ]
        )
        
        if res_app['documents']:
            st.subheader("I tuoi prossimi impegni")
            for app in res_app['documents']:
                try:
                    dt_inizio = pd.to_datetime(app['data_ora'])
                    data_readable = dt_inizio.strftime('%d/%m/%Y alle %H:%M')
                    # Prepariamo date per Google Calendar
                    fmt = "%Y%m%dT%H%M%S"
                    dt_fine = dt_inizio + pd.Timedelta(hours=1)
                    g_url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={app['specialista'].replace(' ', '+')}&dates={dt_inizio.strftime(fmt)}/{dt_fine.strftime(fmt)}&details={app.get('motivo', '').replace(' ', '+')}&location={app.get('indirizzo', '').replace(' ', '+')}&sf=true&output=xml"
                except:
                    data_readable = app['data_ora']
                    g_url = None
                
                with st.container(border=True):
                    col_info, col_del = st.columns([4, 1])
                    with col_info:
                        st.markdown(f"### {app.get('specialista', 'Visita')}")
                        st.write(f"🗓️ **{data_readable}**")
                        
                        testo_luogo = f"📍 {app.get('luogo', '')}"
                        if app.get('indirizzo'):
                            testo_luogo += f" - {app['indirizzo']}"
                        st.caption(testo_luogo)

                        # PULSANTI AZIONE RAPIDA
                        c1, c2 = st.columns(2)
                        with c1:
                            if app.get('indirizzo'):
                                url_map = f"https://www.google.com/maps/search/?api=1&query={app['indirizzo'].replace(' ', '+')}"
                                st.link_button("🗺️ Navigatore", url_map, use_container_width=True)
                        with c2:
                            if g_url:
                                st.link_button("🗓️ In Calendar", g_url, use_container_width=True)
                            
                        if app.get('motivo'): st.info(f"📝 {app['motivo']}")
                    
                    with col_del:
                        if st.button("🗑️", key=f"del_app_{app['$id']}"):
                            databases.delete_document(
                                database_id=DATABASE_ID,
                                collection_id="appuntamenti",
                                document_id=app['$id']
                            )
                            st.rerun()
        else:
            st.info("Non hai appuntamenti segnati.")

    except Exception as e:
        st.error(f"Errore nel caricamento agenda: {e}")