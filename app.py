import streamlit as st
from supabase import create_client
import pandas as pd
import time
import urllib.parse
import os

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Hub Salute - Proprietà", page_icon="🏥", layout="wide")

@st.cache_resource
def init_connection():
    url = st.secrets["connections"]["supabase"]["url"]
    key = st.secrets["connections"]["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()
# Trova il percorso della cartella dove si trova il file app.py
current_dir = os.path.dirname(__file__)
# USIAMO LA "L" MAIUSCOLA COME SU GITHUB
logo_path = os.path.join(current_dir, "Logo.png")

# Carica il logo
st.sidebar.image(logo_path, use_container_width=True)# --- MENU LATERALE ---

with st.sidebar:
    st.title("🏥 Hub Salute")
    st.subheader("La mia Proprietà")
    menu = st.radio(
        "Navigazione",
        ["🏠 Home Dashboard", "💊 Gestione Farmaci", "🩸 Pressione e Salute", "📁 Documenti & Medici", "📅 Agenda Appuntamenti"]
    )
    st.divider()
    st.caption("Accesso autorizzato per: Socio")

# --- 🏠 PAGINA 1: HOME DASHBOARD ---
if menu == "🏠 Home Dashboard":
    st.header("🏠 Centro di Controllo")
    
    # --- 1. SEZIONE URGENZE ---
    try:
        res_f = supabase.table("farmaci").select("nome_farmaco, quantita_attuale").execute()
        critici = [f for f in res_f.data if (f.get('quantita_attuale') is not None and f['quantita_attuale'] <= 5)]
        
        if critici:
            with st.container():
                st.subheader("🚨 Attenzione: Scorte in esaurimento")
                for f in critici:
                    nome = f['nome_farmaco']
                    q = f['quantita_attuale']
                    if q <= 0:
                        st.error(f"❌ **{nome}**: Esaurito! Caricare nuova confezione.")
                    else:
                        st.warning(f"⚠️ **{nome}**: Solo {q} rimasti.")
                st.divider()
    except Exception as e:
        st.error(f"Errore controllo scorte: {e}")

# --- 2. GRAFICO ANDAMENTO PRESSIONE ---
    st.subheader("📈 Andamento Pressione (Ultimi 7 Giorni)")
    try:
        # Recuperiamo i dati usando 'data_ora' invece di 'created_at'
        res_p = supabase.table("pressione_arteriosa").select("data_ora, sistolica, diastolica").order("data_ora", desc=True).limit(20).execute()
        
        if res_p.data:
            import pandas as pd
            df = pd.DataFrame(res_p.data)
            
            # Usiamo 'data_ora' per la conversione temporale
            df['data_ora'] = pd.to_datetime(df['data_ora']).dt.date
            df = df.sort_values('data_ora')
            
            # Impostiamo l'indice per il grafico
            chart_data = df.set_index('data_ora')[['sistolica', 'diastolica']]
            
            # Mostriamo il grafico
            st.line_chart(chart_data)
            
            # Calcolo media per consiglio rapido
            media_s = df['sistolica'].mean()
            if media_s > 140:
                st.warning(f"💡 Nota: La media sistolica è alta ({media_s:.0f}). Parlane con il medico.")
        else:
            st.info("Registra qualche valore di pressione per vedere il grafico!")
    except Exception as e:
        st.error(f"Errore nella generazione del grafico: {e}")
    st.divider()

    # --- 3. COLONNE DETTAGLIO ---
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Stato Scorte")
        res = supabase.table("farmaci").select("nome_farmaco, quantita_attuale").lte("quantita_attuale", 5).execute()
        if res.data:
            for f in res.data:
                st.warning(f"⚠️ **{f['nome_farmaco']}** ({f['quantita_attuale']} rimasti)")
        else:
            st.success("✅ Tutte le scorte sono ok!")

    with col2:
        st.subheader("📅 Prossima Visita")
        res_app = supabase.table("appuntamenti").select("*").order("data_ora").limit(1).execute()
        if res_app.data:
            app = res_app.data[0]
            st.info(f"Prossimo impegno: **{app['specialista']}**\n\n🗓️ {app['data_ora']}")
        else:
            st.write("Nessun appuntamento imminente.")
# --- 💊 PAGINA 2: GESTIONE FARMACI ---
elif menu == "💊 Gestione Farmaci":
    st.header("💊 Diario Assunzioni (Oggi)")

    try:
        # Recuperiamo i farmaci
        res_f_db = supabase.table("farmaci").select("*").order("nome_farmaco").execute()
        lista_f = res_f_db.data if res_f_db.data else []

        # Filtriamo solo quelli che hanno scorte
        opzioni_f = {
            f"{f['nome_farmaco']} ({f.get('dosaggio', '')}) - Rimasti: {f.get('quantita_attuale', 0)}": f 
            for f in lista_f if (f.get('quantita_attuale') is not None and f['quantita_attuale'] > 0)
        }

        if opzioni_f:
            with st.form("form_registro_assunzione", clear_on_submit=True):
                scelta_f = st.selectbox("Quale farmaco hai preso?", list(opzioni_f.keys()))
                nota_a = st.text_input("Note (es. a stomaco vuoto)")
                
                # Il bottone è SEMPRE dentro il form ora
                if st.form_submit_button("REGISTRA ASSUNZIONE 💊"):
                    f_scelto = opzioni_f[scelta_f]
                    nome_f = f_scelto['nome_farmaco']
                    
                    # 1. Registra assunzione nel database
                    supabase.table("somministrazioni").insert({
                        "farmaco_id": f_scelto['id'],
                        "note": nota_a,
                        "utente_id": "1efb545e-5b47-475c-ae13-01a1e806c60e"
                    }).execute()
                    
                    # 2. Scala la dose dall'armadietto
                    nuova_q = max(0, int(f_scelto['quantita_attuale']) - 1)
                    supabase.table("farmaci").update({"quantita_attuale": nuova_q}).eq("id", f_scelto['id']).execute()
                    
                    # --- MESSAGGIO DI CONFERMA ---
                    # Usiamo un'icona simpatica e il nome del farmaco per essere chiari
                    st.balloons() # Un tocco di festa per la salute!
                    st.success(f"✅ Assunzione registrata: hai preso {nome_f}. Scorte aggiornate!")
                    
                    # Aspettiamo un secondo così hai il tempo di leggere prima del refresh
                    import time
                    time.sleep(1.5)
                    st.rerun()
        else:
            st.warning("⚠️ Nessun farmaco disponibile nell'armadietto o scorte esaurite. Carica le confezioni nell'Armadietto in fondo.")

    except Exception as e:
        st.error(f"Errore nel Diario: {e}")
        # 2. Visualizziamo le ultime 5 assunzioni fatte
        st.write("🕒 **Ultime assunzioni registrate:**")
        res_recenti = supabase.table("somministrazioni").select("data_ora, note, farmaci(nome_farmaco)").order("data_ora", desc=True).limit(5).execute()
        
        if res_recenti.data:
            for r in res_recenti.data:
                # Gestione sicura del nome farmaco legato tramite join
                nome_f_storico = r.get('farmaci', {}).get('nome_farmaco', 'Farmaco rimosso')
                ora_f = pd.to_datetime(r['data_ora']).strftime('%H:%M del %d/%m')
                st.caption(f"✅ {nome_f_storico} preso alle {ora_f} - {r['note'] if r['note'] else ''}")
                
    except Exception as e:
        st.error(f"Errore nel Diario Farmaci: {e}")
    # --- FINE MODULO DIARIO FARMACI ---

    with st.expander("💊 Gestione Schema Terapeutico"):
        with st.form("form_farmaci", clear_on_submit=True):
            col_f0, col_f1, col_f2 = st.columns([2, 1, 1])
            with col_f0:
                f_nome = st.text_input("Nome Farmaco (es. Metformina)")
            with col_f1:
                f_poso = st.text_input("Posologia (es. 750mg)")
            with col_f2:
                f_dosa = st.text_input("Dosaggio (es. 1 o 1/2)")
            
            col_f3, col_f4 = st.columns(2)
            with col_f3:
                periodo = st.selectbox("Quando", ["Mattino", "Pomeriggio", "Sera", "Notte", "Al bisogno"])
            with col_f4:
                pasti = st.selectbox("Rispetto ai pasti", ["Lontano dai pasti", "Prima dei pasti", "Durante i pasti", "Dopo i pasti"])
            
            f_note = st.text_input("Note aggiuntive (es. solo lunedì)")
            f_submit = st.form_submit_button("Aggiungi alla Cura")

            if f_submit and f_nome:
                nuovo_farmaco = {
                    "nome_farmaco": f_nome,
                    "posologia": f_poso,
                    "dosaggio": f_dosa,
                    "periodo_giorno": periodo,
                    "relazione_pasti": pasti,
                    "note": f_note,
                    "utente_id": "1efb545e-5b47-475c-ae13-01a1e806c60e"
                }
                try:
                    supabase.table("farmaci").insert(nuovo_farmaco).execute()
                    st.success(f"✅ {f_nome} aggiunto allo schema!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    # Visualizzazione Schema Terapeutico
    st.subheader("📋 La mia Cura Quotidiana")
    try:
        # Ordiniamo per periodo del giorno per avere un senso logico (Mattino -> Notte)
        res_f = supabase.table("farmaci").select("*").execute()
        if res_f.data:
            for f in res_f.data:
                with st.container():
                    # Testo principale in grassetto con posologia e dosaggio ben chiari
                    # Sostituisci il blocco markdown della visualizzazione cura con questo:
                    st.markdown(f"""
                    ### {f['nome_farmaco']} {f.get('posologia') if f.get('posologia') else ''}
                    **Dosaggio:** {f.get('dosaggio') if f.get('dosaggio') else '1'} unità  
                    🕒 {f.get('periodo_giorno') if f.get('periodo_giorno') else 'Da definire'} | 🍽️ {f.get('relazione_pasti') if f.get('relazione_pasti') else '-'}  
                    *{f.get('note') if f.get('note') else ''}*
                    """)
                    st.divider()
            # 2. SOLO ORA, fuori dal ciclo, mettiamo UN UNICO expander per eliminare
            st.write("---")
            with st.expander("🗑️ Rimuovi un farmaco dallo schema"):
                # Creiamo un dizionario che associa una descrizione leggibile all'ID del database
                # Esempio: "Metformina (Mattino)" -> "id-123-abc"
                dict_farmaci = {
                    f"{f['nome_farmaco']} ({f['periodo_giorno']})": f['id'] 
                    for f in res_f.data
                }
                
                scelta_label = st.selectbox("Quale vuoi eliminare?", list(dict_farmaci.keys()), key="del_f")
                
                if st.button("Conferma Eliminazione", type="primary", key="btn_del_f"):
                    try:
                        # Recuperiamo l'ID corrispondente alla scelta
                        id_da_eliminare = dict_farmaci[scelta_label]
                        
                        # Cancelliamo usando l'ID (impossibile sbagliare!)
                        supabase.table("farmaci").delete().eq("id", id_da_eliminare).execute()
                        
                        st.success(f"Cancellato: {scelta_label}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore nella cancellazione: {e}")
        else:
            st.info("Nessun farmaco nello schema terapeutico.")
    except:
        pass
        
        # Qui inserisci il blocco del Diario Assunzioni (quello con i palloncini)
        # Seguito dallo Schema Terapeutico
        # Seguito dall'Armadietto (Magazzino)
    st.header("💊 Armadietto dei Medicinali")

    # --- FORM INSERIMENTO NUOVO FARMACO ---
    with st.expander("➕ Aggiungi Farmaco alla Scorta"):
        with st.form("form_farmaco", clear_on_submit=True):
            nome_f = st.text_input("Nome del Farmaco")
            col1, col2 = st.columns(2)
            with col1:
                dosaggio = st.text_input("Dosaggio (es: 500mg)")
                quantita_tot = st.number_input("Pillole totali nella confezione", min_value=1, value=30)
            with col2:
                frequenza = st.text_input("Frequenza (es: 2 volte al giorno)")
                scadenza = st.date_input("Data di Scadenza")
            
            note_f = st.text_area("Note (es: a stomaco pieno)")
            
            if st.form_submit_button("Registra Farmaco"):
                if nome_f:
                    try:
                        nuovo_f = {
                            "nome_farmaco": nome_f,
                            "dosaggio": dosaggio,
                            "frequenza": frequenza,
                            "quantita_iniziale": quantita_tot,
                            "quantita_attuale": quantita_tot,
                            "scadenza": str(scadenza),
                            "note": note_f,
                            "utente_id": "1efb545e-5b47-475c-ae13-01a1e806c60e"
                        }
                        supabase.table("farmaci").insert(nuovo_f).execute()
                        st.success(f"{nome_f} aggiunto all'armadietto!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")

    # --- VISUALIZZAZIONE SCORTE E ASSUNZIONE ---
    try:
        res_f = supabase.table("farmaci").select("*").order("nome_farmaco").execute()
        
        if res_f.data:
            for f in res_f.data:
                with st.container():
                    c1, c2, c3 = st.columns([3, 2, 1])
                    
                    with c1:
                        st.subheader(f.get('nome_farmaco'))
                        st.caption(f"Dosaggio: {f.get('dosaggio')} | {f.get('frequenza')}")
                        if f.get('note'): st.info(f"💡 {f.get('note')}")
                    with c2:
                        # Recuperiamo il valore e assicuriamoci che sia un numero
                        valore_rimanenti = f.get('quantita_attuale')
                        rimanenti = int(valore_rimanenti) if valore_rimanenti is not None else 0
                        
                        if rimanenti <= 5:
                            st.error(f"⚠️ Scorte basse: {rimanenti} rimasti")
                        else:
                            st.success(f"📦 Disponibili: {rimanenti}")
                        st.caption(f"Scadenza: {f.get('scadenza')}")                
                    
                    with c3:
                        # Tasto "Preso" che scala la dose
                        if st.button("💊 Preso", key=f"preso_{f['id']}"):
                            nuova_qty = max(0, rimanenti - 1)
                            supabase.table("farmaci").update({"quantita_attuale": nuova_qty}).eq("id", f['id']).execute()
                            if nuova_qty == 0:
                                st.warning("Farmaco terminato!")
                            st.rerun()
                        
                        # Tasto elimina
                        if st.button("🗑️", key=f"del_f_{f['id']}"):
                            supabase.table("farmaci").delete().eq("id", f['id']).execute()
                            st.rerun()
                    st.divider()
        else:
            st.info("L'armadietto è vuoto. Registra il tuo primo farmaco sopra!")

    except Exception as e:
                st.error(f"Errore caricamento farmaci: {e}")
                st.info("Qui trovi il Diario, lo Schema e l'Armadietto.")
            # [Inserisci qui il blocco di codice farmaci che abbiamo perfezionato prima]
# --- 🩸 PAGINA 3: PARAMETRI VITALI ---
elif menu == "🩸 Pressione e Salute":
    st.header("🩸 Monitoraggio Pressione")
    # Qui inserisci il form della pressione e il GRAFICO che avevamo fatto
    # [Inserisci qui il blocco pressione con st.line_chart]
    st.divider() # Una linea per separare dai medici
    with st.expander("🩸 Inserisci Misurazione Pressione"):
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
                nuova_misurazione = {
                    "sistolica": sis,
                    "diastolica": dia,
                    "pulsazioni": puls,
                    "note": note_pressione,
                    "utente_id": "1efb545e-5b47-475c-ae13-01a1e806c60e"
                }
                try:
                    supabase.table("pressione_arteriosa").insert(nuova_misurazione).execute()
                    st.success(f"✅ Misurazione registrata: {sis}/{dia} mmHg")
                except Exception as e:
                    st.error(f"Errore nel salvataggio pressione: {e}")         

    # --- QUI FINISCE IL FORM E INIZIA LA VISUALIZZAZIONE ---

    st.divider() # <--- IL TUO TOCCO DI CLASSE!

    st.subheader("📊 Cronologia Pressioni")
    try:
        # Recuperiamo i dati
        res_pressione = supabase.table("pressione_arteriosa") \
            .select("data_ora, sistolica, diastolica, pulsazioni, note") \
            .order("data_ora", desc=True) \
            .limit(10) \
            .execute()

        if res_pressione.data:
            import pandas as pd
            df = pd.DataFrame(res_pressione.data)
            
            # Formattiamo la data per renderla umana
            df['data_ora'] = pd.to_datetime(df['data_ora']).dt.strftime('%d/%m/%Y %H:%M')
            
            # Rinominiamo le colonne
            df.columns = ['Data e Ora', 'Massima', 'Minima', 'Pulsazioni', 'Note']
            
            # Visualizziamo la tabella
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # --- IL TUO NUOVO GRAFICO ---
            st.write("📈 **Andamento Temporale**")
            
            # Prepariamo i dati: usiamo la data come base e mostriamo Massima e Minima
            chart_data = df.set_index('Data e Ora')[['Massima', 'Minima']]
            
            # Disegniamo il grafico
            st.line_chart(chart_data)
            # ----------------------------        
        else:
            st.info("Ancora nessuna misurazione in archivio.")
    except Exception as e:
        st.error(f"Errore nel recupero dati: {e}")

    # Sotto il menu della Salute, puoi aggiungere:
    with st.expander("🩸 Registra Glicemia"):
        with st.form("form_glicemia"):
            val_glic = st.number_input("Valore (mg/dL)", min_value=30, max_value=500, value=100)
            momento = st.selectbox("Momento della misurazione", ["Digiuno", "Prima di pranzo", "Dopo pranzo", "Prima di cena", "Dopo cena", "Prima di dormire"])
            note_g = st.text_input("Note (es: dopo dolce)")
            
            if st.form_submit_button("Salva Glicemia"):
                dati_g = {
                    "valore": val_glic,
                    "momento": momento,
                    "note": note_g,
                    "utente_id": "1efb545e-5b47-475c-ae13-01a1e806c60e"
                }
                supabase.table("glicemia").insert(dati_g).execute()
                st.success("Glicemia registrata!")
                st.rerun()

# --- NUOVO: VISUALIZZAZIONE E GESTIONE GLICEMIA ---
    st.markdown("### 📊 Storico Misurazioni")

    try:
        # Recuperiamo le ultime 10 misurazioni dalla tua Proprietà
        res_g = supabase.table("glicemia").select("*").order("created_at", desc=True).limit(10).execute()
        
        if res_g.data:
            for g in res_g.data:
                with st.container():
                    # Creiamo 3 colonne: Valore, Dettagli, Azione
                    c_val, c_info, c_del = st.columns([1, 2, 1])
                    
                    with c_val:
                        # Colore dinamico: verde se buono, rosso se alto
                        colore = "🟢" if g['valore'] < 110 else "🟡" if g['valore'] < 140 else "🔴"
                        st.subheader(f"{colore} {g['valore']}")
                        st.caption("mg/dL")
                    
                    with c_info:
                        data_g = pd.to_datetime(g['created_at']).strftime('%d/%m/%y %H:%M')
                        st.write(f"**{g['momento']}**")
                        st.caption(f"📅 {data_g}")
                    
                    with c_del:
                        # Il tasto magico per eliminare i doppioni!
                        if st.button("🗑️", key=f"del_g_{g['id']}"):
                            supabase.table("glicemia").delete().eq("id", g['id']).execute()
                            st.success("Cancellato!")
                            st.rerun()
                    st.divider()
        else:
            st.info("Nessun dato trovato. Comincia a registrare sopra!")
            
    except Exception as e:
        st.error(f"Errore nel caricamento: {e}")

# --- 📁 PAGINA 4: DOCUMENTI & MEDICI ---
elif menu == "📁 Documenti & Medici":
    st.header("📁 Archivio e Contatti")
    tab1, tab2 = st.tabs(["📄 Documenti", "👨‍⚕️ Medici"])
    
    with tab1:
        st.subheader("I tuoi referti")
        # Codice per caricamento e visualizzazione documenti
        st.subheader("📄 Archivio Documenti e Referti")
        with st.expander("📤 Carica Nuovo Documento"):
            tipo_doc = st.selectbox("Tipo di documento", ["Referto Medico", "Ricetta", "Esami del Sangue", "Altro"])
            # NUOVO: Campo data
            data_doc = st.date_input("Data del documento", value=None, format="DD/MM/YYYY")
            uploaded_file = st.file_uploader("Scegli un file (PDF, JPG, PNG)", type=['pdf', 'jpg', 'jpeg', 'png'])
            
            if st.button("Salva Documento nell'Archivio"):
                if uploaded_file and data_doc:
                    try:
                        id_utente = "1efb545e-5b47-475c-ae13-01a1e806c60e"
                        file_path = f"{id_utente}/{uploaded_file.name}"
                        
                        # 1. Carichiamo il file
                        supabase.storage.from_("documenti_salute").upload(
                            path=file_path,
                            file=uploaded_file.read(),
                            file_options={"content-type": uploaded_file.type}
                        )
                        
                        # 2. Salviamo nel database con la DATA
                        nuovo_doc = {
                            "nome_file": uploaded_file.name,
                            "tipo_documento": tipo_doc,
                            "url_file": supabase.storage.from_("documenti_salute").get_public_url(file_path),
                            "data_documento": data_doc.isoformat(), # Salviamo la data scelta
                            "utente_id": id_utente
                        }
                        supabase.table("allegati_salute").insert(nuovo_doc).execute()
                        
                        st.success(f"✅ Documento del {data_doc.strftime('%d/%m/%Y')} salvato!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore tecnico: {e}")
                else:
                    st.warning("Compila tutti i campi (inclusa la data) e seleziona un file!")

        # --- VISUALIZZAZIONE DOCUMENTI ---
        try:
            res_docs = supabase.table("allegati_salute").select("*").order("data_documento", desc=True).execute()
            
            if res_docs.data:
                for doc in res_docs.data:
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        # Controllo data
                        if doc.get('data_documento'):
                            data_f = pd.to_datetime(doc['data_documento']).strftime('%d/%m/%Y')
                        else:
                            data_f = "Data N.D."
                        
                        st.write(f"📁 **{doc['tipo_documento']}** del {data_f}")
                        st.caption(f"File: {doc['nome_file']}")
                    
                    with col_b:
                        id_utente = "1efb545e-5b47-475c-ae13-01a1e806c60e"
                        nome_f = doc['nome_file']
                        
                        # Costruiamo l'URL pulito (senza spazi che rompono i link)
                        import urllib.parse
                        nome_f_safe = urllib.parse.quote(nome_f)
                        
                        url_finale = f"https://rubocoglxttoguufytfy.supabase.co/storage/v1/object/public/documenti_salute/{id_utente}/{nome_f_safe}"
                        
                        st.link_button("Apri", url_finale)
                    st.divider()

        # --- SEZIONE ELIMINAZIONE ---
                st.write("### ⚙️ Gestione Archivio")
                with st.expander("🗑️ Elimina Documenti"):
                    opzioni_del = {
                        f"{d['data_documento']} - {d['tipo_documento']} ({d['nome_file']})": d 
                        for d in res_docs.data
                    }
                    
                    if opzioni_del:
                        scelta = st.selectbox("Seleziona cosa rimuovere:", list(opzioni_del.keys()), key="select_delete_final")
                        
                        if st.button("CONFERMA ELIMINAZIONE DEFINITIVA", type="primary", use_container_width=True):
                            doc_t = opzioni_del[scelta]
                            id_db = doc_t['id']
                            nome_f = doc_t['nome_file']
                            path_st = f"1efb545e-5b47-475c-ae13-01a1e806c60e/{nome_f}"
                            
                            with st.spinner("Pulizia in corso..."):
                                try:
                                    # 1. TENTATIVO CANCELLAZIONE DATABASE
                                    res_db = supabase.table("allegati_salute").delete().eq("id", id_db).execute()
                                    
                                    # 2. TENTATIVO CANCELLAZIONE STORAGE
                                    res_st = supabase.storage.from_("documenti_salute").remove([path_st])
                                    
                                    # Verifichiamo se il DB ha effettivamente rimosso la riga
                                    if len(res_db.data) > 0:
                                        st.success(f"✅ '{nome_f}' rimosso da Database e Storage!")
                                        st.rerun()
                                    else:
                                        st.error("Errore: Il database non ha rimosso la riga. Controlla le Policy RLS.")
                                        
                                except Exception as e:
                                    st.error(f"Errore durante l'eliminazione: {e}")
                    else:
                        st.info("Nulla da eliminare.")
        except Exception as e:
            st.error(f"Errore generale: {e}")
        
    with tab2:
        st.subheader("Anagrafica Medici")
        # Codice per aggiungere medici
        if 'espanso' not in st.session_state:
            st.session_state.espanso = False

        with st.expander("➕ Aggiungi un nuovo Medico", expanded=st.session_state.espanso):
            # 1. Recupero dati
            try:
                res = supabase.table("contatti_medici").select("specializzazione").execute()
                lista_db = sorted(list(set([r['specializzazione'] for r in res.data if r['specializzazione']])))
            except Exception as e:
                lista_db = []

            # 2. Selezione Specializzazione
            scelta = st.selectbox("Specializzazione", options=lista_db + ["Altro..."], key="sel_spec")
            
            spec_per_db = ""
            if scelta == "Altro...":
                # Se l'utente clicca Altro, diciamo all'expander di restare aperto al prossimo refresh
                st.session_state.espanso = True
                spec_per_db = st.text_input("Specifica nuova specialità", key="txt_spec_nuova")
            else:
                spec_per_db = scelta

            with st.form("form_medico", clear_on_submit=True):
                nome = st.text_input("Nome del Medico")
                clinica = st.text_input("Clinica/Ospedale")
                tel = st.text_input("Telefono")
                email = st.text_input("Email")

                submit = st.form_submit_button("Salva Medico")

                if submit:
                    if nome and spec_per_db:
                        nuovo_medico = {
                            "nome_dottore": nome,
                            "specializzazione": spec_per_db,
                            "clinica_ospedale": clinica,
                            "telefono": tel,
                            "email": email,
                            "utente_id": "1efb545e-5b47-475c-ae13-01a1e806c60e"
                        }
                        try:
                            supabase.table("contatti_medici").insert(nuovo_medico).execute()
                            # Messaggio di successo FISSO (senza rerun immediato)
                            st.success(f"✅ Dott. {nome} salvato con successo!")
                            # Resettiamo lo stato dell'expander per la prossima volta
                            st.session_state.espanso = False 
                        except Exception as e:
                            st.error(f"Errore: {e}")
                    else:
                        st.warning("Mancano Nome o Specializzazione!")
    st.divider()
    st.subheader("👨‍⚕️ I tuoi Contatti Medici")
    try:
        res_m = supabase.table("contatti_medici").select("*").order("nome_dottore").execute()
        
        if res_m.data:
            for m in res_m.data:
                with st.container():
                    c1, c2 = st.columns([2, 1])
                    
                    with c1:
                        st.write(f"### Dott. {m['nome_dottore']}")
                        st.write(f"🧬 **{m['specializzazione']}**")
                        if m.get('clinica_ospedale'):
                            st.caption(f"🏥 {m['clinica_ospedale']}")
                    
                    with c2:
                        tel = m.get('telefono', '').replace(" ", "")
                        if tel:
                            # Tasto Chiamata (Protocollo tel:)
                            st.link_button("📞 Chiama", f"tel:{tel}", use_container_width=True)
                            
                            # Tasto WhatsApp (Protocollo wa.me)
                            messaggio = f"Buongiorno Dottore, sono un suo paziente della Proprietà."
                            import urllib.parse
                            msg_safe = urllib.parse.quote(messaggio)
                            st.link_button("💬 WhatsApp", f"https://wa.me/{tel}?text={msg_safe}", use_container_width=True)
                    
                    st.divider()
        else:
            st.info("Non hai ancora salvato nessun medico.")
    except Exception as e:
        st.error(f"Errore caricamento medici: {e}")
        st.divider() # Una linea per separare dai medici

# --- 📅 PAGINA 5: AGENDA ---
elif menu == "📅 Agenda Appuntamenti":
    # Codice per gestire gli appuntamenti
    st.header("📅 Agenda Appuntamenti Medici")

    # Inizializziamo una chiave per il reset se non esiste
    if "form_reset" not in st.session_state:
        st.session_state.form_reset = 0

    with st.expander("➕ Segna Nuovo Appuntamento"):
        # Usiamo la chiave dinamica per forzare il reset del form
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
                        "motivo": motivo,
                        "utente_id": "1efb545e-5b47-475c-ae13-01a1e806c60e"
                    }
                    supabase.table("appuntamenti").insert(nuovo_app).execute()
                    st.success("Appuntamento salvato!")
                    
                    # Piccola magia: forziamo il refresh totale per pulire i campi
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    # --- VISUALIZZAZIONE PROSSIMI APPUNTAMENTI ---
    try:
        # Prendiamo solo quelli futuri o tutti ordinati per data
        res_app = supabase.table("appuntamenti").select("*").order("data_ora", desc=False).execute()
        
        if res_app.data:
            st.subheader("I tuoi prossimi impegni")
            for app in res_app.data:
                # Formattiamo la data per leggerla bene
                dt = pd.to_datetime(app['data_ora'])
                data_readable = dt.strftime('%d/%m/%Y alle %H:%M')
                
                with st.container():
                    col_info, col_del = st.columns([4, 1])
                    with col_info:
                        st.markdown(f"### {app['specialista']}")
                        st.write(f"🗓️ **{data_readable}**")
                        if app['luogo']: st.caption(f"📍 {app['luogo']}")
                        if app['motivo']: st.info(f"📝 {app['motivo']}")
                    
                    with col_del:
                        if st.button("🗑️", key=f"del_app_{app['id']}"):
                            supabase.table("appuntamenti").delete().eq("id", app['id']).execute()
                            st.rerun()
                    st.divider()
        else:
            st.info("Non hai appuntamenti segnati. Usa il tasto '+' sopra per aggiungerne uno!")

    except Exception as e:
        st.error(f"Errore nel caricamento agenda: {e}")    
