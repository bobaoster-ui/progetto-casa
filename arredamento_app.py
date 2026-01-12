import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time
import requests
import io  # <--- AGGIUNGI SOLO QUESTO
import os

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V22.10.11", layout="wide", page_icon="🚀")

# --- CONNESSIONE SUPABASE ---
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

sb = get_supabase()

# --- FUNZIONE DI ARCHIVIAZIONE REALE ---
def upload_documento(file, articolo_id, descrizione):
    try:
        # 1. Percorso file nel Bucket (senza prefisso 'art_', solo l'ID come i vecchi)
        file_path = f"{articolo_id}/{file.name}"
        file_content = file.getvalue()

        # 2. Caricamento nel Bucket "documenti_proprieta"
        sb.storage.from_("documenti_proprieta").upload(
            file_path, 
            file_content, 
            {"content-type": file.type, "upsert": "true"}
        )

        # 3. URL pubblico del file
        file_url = sb.storage.from_("documenti_proprieta").get_public_url(file_path)

        # 4. Registrazione nel DB (mappata sul tuo schema SQL reale)
        nuovo_doc = {
            "parent_id": articolo_id,      # Era arredo_id
            "nome_documento": file.name,   # Era nome_file
            "link_file": file_url,         # Era url
            "nota": descrizione            # Era descrizione
        }
        sb.table("documenti_arredo").insert(nuovo_doc).execute()
        return True
    except Exception as e:
        st.error(f"Errore tecnico durante l'upload: {e}")
        return False
# --- STILE (riga 25 originale diventa riga 50 circa) ---


def genera_pdf_riepilogo(nome_ordine, df_f, tot, pagato, residuo):
    pdf = FPDF()
    pdf.add_page()

# --- LOGO TESTUALE STILIZZATO (Il nostro "Logo senza bug") ---
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(41, 128, 185) # Blu professionale
    pdf.cell(0, 10, "PROPRIETÀ", ln=True, align='L')
    
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(100, 100, 100) # Grigio sobrio
    pdf.cell(0, 5, "Accounting Intelligence & Document-Flow", ln=True, align='L')
    
    # Linea sottile di separazione (molto elegante)
    pdf.set_draw_color(41, 128, 185)
    pdf.line(10, 27, 200, 27)
    pdf.ln(10)

    # Titolo
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"RIEPILOGO MOVIMENTI: {ordine_selezionato}", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)

    # Box Sintesi Economica
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 10, "Totale Impegnato", 1, 0, "C", True)
    pdf.cell(60, 10, "Totale Pagato", 1, 0, "C", True)
    pdf.cell(70, 10, "Residuo da Saldare", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(60, 10, f"Euro {tot:,.2f}", 1, 0, "C")
    pdf.cell(60, 10, f"Euro {pagato:,.2f}", 1, 0, "C")
    pdf.set_text_color(200, 0, 0) if residuo > 0 else pdf.set_text_color(0, 150, 0)
    pdf.cell(70, 10, f"Euro {residuo:,.2f}", 1, 1, "C")
    
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 10, "Dettaglio Movimenti:", ln=True)

    # Tabella Movimenti
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Data", 1, 0, "C", True)
    pdf.cell(30, 8, "Tipo", 1, 0, "C", True)
    pdf.cell(90, 8, "Descrizione", 1, 0, "C", True)
    pdf.cell(40, 8, "Importo", 1, 1, "C", True)

    pdf.set_font("Arial", "", 9)
    for _, row in df_f.iterrows():
        imp = row['dare'] if row['tipo'] == 'Ordine' else row['avere']
# 2. Formatti la data in formato italiano gg/mm/aaaa
        # Usiamo un controllo per sicurezza: se è già una data, la formattiamo, altrimenti la scriviamo così com'è
        dt_obj = pd.to_datetime(row['data_movimento'])
        data_ita = dt_obj.strftime("%d/%m/%Y")
        pdf.cell(30, 8, data_ita, 1, 0, "C") # <-- Usiamo data_ita qui
#        pdf.cell(30, 8, str(row['data_movimento']), 1, 0, "C")
        pdf.cell(30, 8, row['tipo'], 1, 0, "C")
        pdf.cell(90, 8, str(row['descrizione'])[:50], 1, 0, "L")
        pdf.cell(40, 8, f"Euro {imp:,.2f}", 1, 1, "R")
    
    return pdf.output()

# --- STILE ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
grad = "linear-gradient(90deg, #0f2027, #203a43, #2c5364)" if st.session_state.dark_mode else "linear-gradient(90deg, #2e5a88, #4a90e2)"
st.markdown(f"""<style>
    .stApp {{background-color: {bc}; color: {tc};}}
    .main-header {{background: {grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px;}}
    .metric-card {{background-color: {cc}; padding: 15px; border-radius: 10px; border-bottom: 4px solid #2e5a88; text-align: center; color: {tc}; margin-bottom: 10px;}}
    .metric-value {{font-size: 1.8em; font-weight: 800; color: #2e5a88;}}
    .gold-seal {{background: linear-gradient(145deg, #ffdf00, #d4af37); padding: 20px; border-radius: 15px; text-align: center; color: black; font-weight: bold; border: 2px solid #b8860b; margin-bottom: 20px; box-shadow: 0px 4px 15px rgba(212, 175, 55, 0.4);}}
    .manual-container {{background-color: {cc}; padding: 30px; border-radius: 15px; border: 1px solid #e0e0e0; line-height: 1.6;}}
</style>""", unsafe_allow_html=True)

class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10); t = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t.encode('latin-1','replace').decode('latin-1'), ln=True, align='C'); self.ln(15)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128, 128, 128)
        self.cell(0, 10, "Prodotto di Proprietà: Roberto & Gemini".encode('latin-1','replace').decode('latin-1'), 0, 0, 'C')

def clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    # Aggiunto 'id': 'id' nel mapping per non perderlo
    mapping = {'id': 'id', 'articolo': 'Articolo', 'acquistato': 'Acquistato', 'costo': 'Costo', 'importo_totale': 'Importo Totale', 'acquista_sn': 'Acquista S/N', 'note': 'Note', 'versato': 'Versato', 'prezzo_pieno': 'Prezzo Pieno', 'sconto_perc': 'Sconto %', 'stato_pagamento': 'Stato Pagamento', 'link_fattura': 'Link Fattura', 'link': 'Link', 'foto': 'Foto', 'data_scadenza': 'Data Scadenza', 'stanza_chiusa': 'Stanza Chiusa'}
    df = df.rename(columns=mapping)
    df['Stanza Chiusa'] = df['Stanza Chiusa'].apply(lambda x: str(x).upper().strip() in ['TRUE', '1', 'T'])
    df['DV'] = df['Articolo']
    for c in ['Note', 'Acquista S/N', 'Stato Pagamento', 'Link Fattura', 'Link', 'Foto']:
        if c in df.columns: df[c] = df[c].astype(str).replace(['None', 'nan', '<NA>', 'null', ''], '')
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    if 'Data Scadenza' in df.columns: df['Data Scadenza'] = pd.to_datetime(df['Data Scadenza'], errors='coerce')
    return df

if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]: st.session_state.password_correct = True; st.rerun()
else:
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    try:
        res_settings = sb.table("impostazioni").select("*").execute()
        conf = {r['chiave']: r for r in res_settings.data}
        bud = float(conf.get('budget_totale', {}).get('valore_num', 15000.0))
        path_scansioni = conf.get('path_scansioni', {}).get('valore_txt', '/home/roberto/Documenti/ScansioniApp')
        # Recuperiamo il nome del proprietario (default 'Jacopo' se non trovato)
        nome_prop = conf.get('Proprietà', {}).get('valore_txt', 'Jacopo')        
    except Exception as e:
        bud = 15000.0
        path_scansioni = "/home/roberto/Documenti/ScansioniApp"
    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass

        # 3. TITOLO DINAMICO (Qui va la riga!)
        st.title(f"Gestione Arredamento - {nome_prop}")

        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)

    # --- 1. MENU DI NAVIGAZIONE (AGGIORNATO ALLA V1.2) ---
    sel = st.sidebar.selectbox("MENU", 
        ["🏠 Riepilogo", "✨ Wishlist", "📥 Carico Rapido", "📈 Contabilità"] + 
        [f"📦 {s.capitalize()}" for s in stanze] + 
        ["📖 Manuale"]
    )
    
    edit_struct = st.sidebar.toggle("⚙️ Modifica Struttura", False)
    st.sidebar.markdown(f"<br>---<br>✨ **Roberto & Gemini**<br><small>Proprietà: {nome_prop}</small>", unsafe_allow_html=True)
    st.sidebar.write(f"📁 Path: {path_scansioni}")        
    # 3. IL PARACADUTE (BACKUP)
    # --- LOGICA GENERAZIONE BACKUP ---
    
    if st.sidebar.button("📊 GENERA BACKUP TOTALE"):
        try:
            # 1. Recupero dati da Supabase
            # Questa è la "legge" per la Proprietà Jacopo: ordine assoluto per ID
            res_arredo = sb.table("arredamento").select("*").order("id").execute()
            res_docs = sb.table("documenti_arredo").select("*").execute()
            df_arredo = pd.DataFrame(res_arredo.data)
            # Forza l'ordinamento numerico per ID nel DataFrame di Python
            df_arredo = df_arredo.sort_values(by="id", ascending=True).reset_index(drop=True)
            df_docs = pd.DataFrame(res_docs.data)
            # 2. Creazione file Excel in memoria
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_arredo.to_excel(writer, sheet_name='Inventario Arredo', index=False)
                df_docs.to_excel(writer, sheet_name='Lista Documenti', index=False)
            # 3. Tasto per il download effettivo
            st.sidebar.download_button(
                label="💾 Scarica Excel Proprietà",
                data=output.getvalue(),
                file_name=f"Backup_Proprieta_Jacopo_{datetime.now().strftime('%d_%m_%Y_%H_%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.sidebar.success("Excel generato! Clicca sopra per scaricare.")
        except Exception as e:
            st.sidebar.error(f"Errore backup: {e}")
    st.markdown("---")

    if st.sidebar.button("Logout 🚪"): # Ho aggiunto .sidebar qui così il tasto resta a sinistra!
        st.session_state.clear()
        st.rerun()

    # --- LOGICA DELLE PAGINE ---

# --- AGGIUNGI QUESTO QUI! ---
    if sel == "📈 Contabilità":
        st.markdown(f'<div class="main-header"><h1>Amministrazione e Flussi</h1><p>Proprietà {nome_prop}</p></div>', unsafe_allow_html=True)
        
        # Recupero dati dal nuovo tavolo Contabilità
        res_cont = sb.table("contabilita").select("*").order("data_movimento", desc=True).execute()
        df_cont = pd.DataFrame(res_cont.data)

        # Metriche
        if not df_cont.empty:
            m1, m2, m3 = st.columns(3)
            tot_dare = df_cont['dare'].sum()
            tot_avere = df_cont['avere'].sum()
            residuo = tot_dare - tot_avere
            m1.metric("Totale Ordini (DARE)", f"€ {tot_dare:,.2f}")
            m2.metric("Totale Pagato (AVERE)", f"€ {tot_avere:,.2f}")
            m3.metric("Residuo da Saldare", f"€ {residuo:,.2f}")

        # Maschera di inserimento (il form che abbiamo scritto prima)
        # 1. Recuperiamo gli ordini (FUORI dal form per evitare errori)
        ordini_esistenti = []
        if not df_cont.empty:
            # Prendiamo solo i nomi unici degli oggetti coinvolti
            ordini_esistenti = sorted(df_cont['oggetti_coinvolti'].unique().tolist())

        # 1. Scelta fuori dal form per "svegliare" Streamlit
        t_mov = st.selectbox("Tipo Movimento", ["Ordine", "Pagamento"])
        with st.expander("➕ Registra Nuovo Ordine o Pagamento", expanded=False):
            with st.form("form_contabilita_v3", clear_on_submit=True):
                c1, c2, c3 = st.columns([1, 1, 1])
                
                with c1:
                    # DATA (Abbiamo tolto t_mov da qui!)
                    d_mov = st.date_input("Data", datetime.now(), format="DD/MM/YYYY") # Qui l'utente la vede bene
                    data_per_pdf = d_mov.strftime("%d/%m/%Y") # Qui la trasformi in testo per il PDF o il DB
                    importo = st.number_input("Importo (€)", min_value=0.0, step=10.0)
                with c2:
                    # LOGICA DINAMICA (Ora t_mov è quello fuori e Streamlit lo sente subito!)
                    if t_mov == "Ordine":
                        scelta = st.radio("L'ordine è:", ["Nuovo", "Esistente"], horizontal=True, key="r_ord")
                        if scelta == "Nuovo":
                            ogg = st.text_input("Nome Nuovo Ordine", placeholder="es. Cucina Lube", key="t_nuo")
                        else:
                            ogg = st.selectbox("Seleziona Ordine", ordini_esistenti if ordini_esistenti else ["Nessun ordine"], key="s_ord")
                    else:
                        st.write("**Riferito all'ordine:**")
                        ogg = st.selectbox("Scegli:", ordini_esistenti if ordini_esistenti else ["Nessun ordine"], label_visibility="collapsed", key="s_pag")
                with c3:
                    # NOTA E FILE
                    descr = st.text_input("Nota", placeholder="es. Acconto 30%")
                    f_doc = st.file_uploader("Documento PDF/IMG", type=['pdf', 'jpg', 'png'])

                submit = st.form_submit_button("🚀 Memorizza Movimento")                
                if submit:
                    if not ogg or ogg == "Nessun ordine trovato":
                        st.warning("⚠️ Per favore, specifica a quale oggetto o ordine si riferisce il movimento!")
                    else:                    
                        url_f = None 
                        if f_doc:
                            f_name = f"cont_{int(time.time())}_{f_doc.name}"
                            sb.storage.from_("contabilita_documenti").upload(
                                f_name, 
                                f_doc.getvalue(), 
                                {"content-type": f_doc.type}
                            )
                            url_f = sb.storage.from_("contabilita_documenti").get_public_url(f_name)
                        
                        nuovo_rec = {
                            "data_movimento": str(d_mov),
                            "tipo": t_mov,
                            "descrizione": descr,
                            "oggetti_coinvolti": ogg,
                            "dare": importo if t_mov == "Ordine" else 0,
                            "avere": importo if t_mov == "Pagamento" else 0,
                            "url_documento": url_f
                        }
                        
                        try:
                            sb.table("contabilita").insert(nuovo_rec).execute()
                            st.success(f"✅ {t_mov} registrato per {ogg}!")
                            st.rerun() 
                        except Exception as e:
                            st.error(f"Errore nel salvataggio: {e}")

        # --- VISUALIZZAZIONE ESTRATTO CONTO (Torna a livello dell'expander) ---
        # --- VISUALIZZAZIONE ESTRATTO CONTO AGGIORNATA ---
# --- 1. SEZIONE FILTRI E RICERCA (Mettila subito sotto la fine del form/expander) ---
        st.write("---")
        st.subheader("📊 Analisi e Ricerca")
        
        # Lista ordini per il filtro (prendiamo i nomi unici dalla tabella)
        ordini_per_filtro = []
        if not df_cont.empty:
            ordini_per_filtro = sorted(df_cont['oggetti_coinvolti'].unique().tolist())
        
        # Questa selectbox crea il filtro
        ordine_selezionato = st.selectbox("Filtra per Ordine/Oggetto:", ["Tutti"] + ordini_per_filtro, key="filtro_ordini")

        # Prepariamo i dati filtrati: se è "Tutti" copia tutto, altrimenti filtra
        if ordine_selezionato == "Tutti":
            df_visualizza = df_cont.copy()
        else:
            df_visualizza = df_cont[df_cont['oggetti_coinvolti'] == ordine_selezionato].copy()

        # --- 2. LA SCHEDA PRO (Appare solo se selezioni un ordine specifico) ---
        if ordine_selezionato != "Tutti" and not df_visualizza.empty:
            tot_ordine = df_visualizza[df_visualizza['tipo'] == 'Ordine']['dare'].sum()
            tot_pagato = df_visualizza[df_visualizza['tipo'] == 'Pagamento']['avere'].sum()
            residuo_singolo = tot_ordine - tot_pagato
            
            with st.container(border=True):
                st.markdown(f"### 📑 Riepilogo: {ordine_selezionato}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Costo Totale", f"€ {tot_ordine:,.2f}")
                
                # Calcolo percentuale di avanzamento
                percentuale = (tot_pagato / tot_ordine * 100) if tot_ordine > 0 else 0
                c2.metric("Pagato", f"€ {tot_pagato:,.2f}", delta=f"{percentuale:.1f}% del totale")
                
                # Box per il residuo
                color_res = "green" if residuo_singolo <= 0 else "#D32F2F"
                c3.markdown(f"""
                    <div style="text-align: center; background-color: rgba(0,0,0,0.05); padding: 10px; border-radius: 10px; border-left: 5px solid {color_res};">
                        <p style="margin:0; font-size: 0.9em; color: gray;">Residuo da versare</p>
                        <h2 style="margin:0; color: {color_res};">€ {residuo_singolo:,.2f}</h2>
                    </div>
                """, unsafe_allow_html=True)
                # --- QUI AGGIUNGI IL GENERATORE E IL TASTO ---
                try:
                    pdf_output = genera_pdf_riepilogo(
                        ordine_selezionato, 
                        df_visualizza, 
                        tot_ordine, 
                        tot_pagato, 
                        residuo_singolo
                    )
                    
                    st.download_button(
                        label="📄 Scarica Riepilogo PDF",
                        data=bytes(pdf_output),
                        file_name=f"Riepilogo_{ordine_selezionato}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Errore generazione PDF: {e}")

        # --- 3. VISUALIZZAZIONE LISTA (Usa df_visualizza invece di df_cont) ---
        st.write(f"### 📜 Elenco Movimenti: {ordine_selezionato}")            
        
        if not df_visualizza.empty:
            for i, row in df_visualizza.iterrows():
                with st.container():
                    col_data, col_info, col_soldi, col_file, col_azioni = st.columns([1, 2.5, 2, 1, 0.5])
                    
                    with col_data:
                        st.caption(f"📅 {row['data_movimento']}")
                        st.write(f"**{row['tipo']}**")
                    
                    with col_info:
                        st.write(f"🔍 {row['oggetti_coinvolti']}")
                        st.caption(f"📝 {row['descrizione']}")
                    
                    with col_soldi:
                        if row['dare'] > 0: st.error(f"Dare: € {row['dare']:,.2f}")
                        if row['avere'] > 0: st.success(f"Avere: € {row['avere']:,.2f}")
                    
                    with col_file:
                        if row['url_documento']:
                            st.markdown(f'<a href="{row["url_documento"]}" target="_blank" style="text-decoration: none; border: 1px solid #2e5a88; padding: 5px 10px; border-radius: 5px; font-size: 12px;">📄 Doc</a>', unsafe_allow_html=True)
                    
                    with col_azioni:
                        if st.button("🗑️", key=f"del_{row['id']}"):
                            try:
                                if row['url_documento']:
                                    file_name = row['url_documento'].split('/')[-1]
                                    try:
                                        sb.storage.from_("contabilita_documenti").remove([file_name])
                                    except: pass
                                sb.table("contabilita").delete().eq("id", row['id']).execute()
                                st.success("Eliminato!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Errore: {e}")                    
                st.divider()
        else:
            st.info(f"Nessun movimento trovato per {ordine_selezionato}.")

    elif sel == "🏠 Riepilogo":

        st.markdown('<div class="main-header"><h1>Command Center</h1><p>Proprietà Jacopo</p></div>', unsafe_allow_html=True)
        # 1. RECUPERO DATI GLOBALI
        res_tutto = sb.table("arredamento").select("*").execute()
        df_tutto = pd.DataFrame(res_tutto.data)

        # --- DASHBOARD GLOBALE ---
        st.write("### 📊 Riepilogo Totale Proprietà")
        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric("Totale Arredi", f"{len(df_tutto)} pz")

        with c2:
            # Troviamo la colonna costo (Costo o costo)
            col_costo = next((c for c in df_tutto.columns if c.lower() == 'costo'), None)
            
            if col_costo:
                # .fillna(0) è la magia: trasforma i valori vuoti (NaN) in 0
                # Così l'errore "JSON compliant: nan" sparisce!
                prezzi = pd.to_numeric(df_tutto[col_costo], errors='coerce').fillna(0)
                st.metric("Valore Totale", f"€ {prezzi.sum():,.2f}")
            else:
                st.metric("Valore Totale", "Colonna non trovata")

        with c3:
            try:
                res_docs = sb.table("documenti_arredo").select("id", count="exact").execute()
                st.metric("Documenti", f"{res_docs.count if res_docs.count else 0} file")
            except:
                st.metric("Documenti", "0")

        st.divider()

        # --- RICERCA RAPIDA DOCUMENTI ---
        with st.expander("🔍 Cerca un documento in tutta la Proprietà"):
            cerca_doc = st.text_input("Inserisci il nome del file (es: fattura, progetto...):", key="search_global")
            
            if cerca_doc:
                # Cerchiamo nel DB in modo "fuzzy" (ilike trova anche parti del nome)
                risultati = sb.table("documenti_arredo").select("*").ilike("nome_documento", f"%{cerca_doc}%").execute()
                
                if risultati.data:
                    st.write(f"Trovati {len(risultati.data)} documenti:")
                    for r in risultati.data:
                        col_info, col_btn = st.columns([4, 1])
                        with col_info:
                            st.markdown(f"📄 **{r['nome_documento']}**")
                        with col_btn:
                            st.link_button("👁️ Apri", r['link_file'], use_container_width=True)
                else:
                    st.info("Nessun documento trovato con questo nome.")

        
        st.divider()        #un po' di spazio in fondo (evviva)



        res = sb.table("arredamento").select("*").execute()
        df_all = clean_df(pd.DataFrame(res.data))
        if not df_all.empty:
            df_r = df_all[df_all['Acquista S/N'].str.upper().str.strip() == 'S'].copy()
            conf, pag = df_r['Importo Totale'].sum(), df_r['Versato'].sum()
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card">BUDGET<div class="metric-value">{bud:,.0f}€</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card">CONFERMATO<div class="metric-value">{conf:,.0f}€</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{pag:,.0f}€</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="metric-card">DISPONIBILE<div class="metric-value">{bud-conf:,.0f}€</div></div>', unsafe_allow_html=True)
            st.subheader("🗓️ Scadenzario")
            sc = df_r[df_r['Data Scadenza'].notna()].copy()
            sc = sc[sc['Versato'] < sc['Importo Totale']]
            if not sc.empty:
                oggi = pd.Timestamp(datetime.now().date())
                sc['gg'] = (sc['Data Scadenza'] - oggi).dt.days
                sc['Stato'] = sc['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                sc_display = sc.sort_values('gg').copy()
                sc_display['Data Scadenza'] = sc_display['Data Scadenza'].dt.strftime('%d/%m/%Y')
                st.dataframe(sc_display[['stanza','DV','Data Scadenza','Stato']], use_container_width=True, hide_index=True)



            else: st.info("Nessuna scadenza imminente trovata.")
            c_p, c_t = st.columns([1, 1.2])
            with c_p:
                st.plotly_chart(px.pie(df_r, values='Importo Totale', names='stanza', hole=0.5), use_container_width=True)

                if st.button("📄 PDF"):
                    p = PDF(); p.add_page(); p.set_font('Arial','B',10); p.set_fill_color(46,117,182); p.set_text_color(255,255,255)
                    # --- INTESTAZIONE (Allineamento al centro per i titoli) ---
                    p.cell(30,10,'Stanza',1,0,'C',1)
                    p.cell(75,10,'Articolo',1,0,'C',1)
                    p.cell(15,10,'OMG',1,0,'C',1)
                    p.cell(35,10,'Totale',1,0,'C',1)
                    p.cell(35,10,'Versato',1,1,'C',1)
                    
                    p.set_font('Arial','',9); p.set_text_color(0,0,0)
                    for _, r in df_r.iterrows():
                        reg_val = "S" if r.get('Sconto %', 0) == 100 else ""
                        
                        y=p.get_y()
                        # Articolo
                        p.set_xy(40,y)
                        p.multi_cell(75,10,str(r['DV']).encode('latin-1','replace').decode('latin-1'),1)
                        h=max(p.get_y()-y,10)
                        
                        # Stanza
                        p.set_xy(10,y)
                        p.cell(30,h,str(r['stanza']),1,0,'C')
                        
                        # OMG
                        p.set_xy(115,y)
                        p.cell(15,h,reg_val,1,0,'C')
                        
                        # --- IMPORTI ALLINEATI A DESTRA ('R') ---
                        p.set_xy(130,y)
                        p.cell(35,h,f"{r['Importo Totale']:,.2f} ",1,0,'R') # Spazio dopo il numero per distanziarlo dal bordo
                        p.set_xy(165,y)
                        p.cell(35,h,f"{r['Versato']:,.2f} ",1,1,'R')

                    # --- TOTALI (Anche questi a destra per coerenza) ---
                    p.ln(2); p.set_font('Arial','B',10); p.set_fill_color(220,220,220)
                    t_i = df_r['Importo Totale'].sum(); t_v = df_r['Versato'].sum()
                    # Nel calcolo dei totali in fondo al PDF
                    p.cell(120, 10, f'TOTALE GENERALE PROPRIETÀ {nome_prop.upper()}', 1, 0, 'R', 1)
                    p.cell(35,10,f"{t_i:,.2f} ",1,0,'R',1)
                    p.cell(35,10,f"{t_v:,.2f} ",1,1,'R',1)
                    st.download_button("📥 Scarica PDF", bytes(p.output(dest='S')), "Report.pdf")

            # --- 1. CREIAMO LA COLONNA OMAGGIO NEL DATAFRAME ---
            # Nota: usiamo 'Sconto %' perché è il nome tecnico nella tua tabella Supabase
            # 1. Creiamo la colonna Omaggio in modo sicuro
            # Usiamo axis=1 per controllare riga per riga
            # --- 1. CREIAMO LA COLONNA OMAGGIO NEL DATAFRAME ---
            # Usiamo 'Sconto %' perché è così che clean_df rinomina 'sconto_perc'
            df_r['Omaggio'] = df_r.apply(
                lambda row: "🎁 S" if row.get('Sconto %', 0) == 100 else "", 
                axis=1
            )
            # --- 2. AGGIUNGIAMO 'Omaggio' NELLA LISTA DELLE COLONNE DA MOSTRARE ---
            c_t.dataframe(
                df_r[['stanza', 'DV', 'Omaggio', 'Importo Totale', 'Versato']], 
                use_container_width=True, 
                hide_index=True
            )

#            c_t.dataframe(df_r[['stanza','DV','Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

    elif sel == "📖 Manuale":
        st.markdown('<div class="main-header"><h1>Manuale d\'Uso</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        try:
            # URL RAW del file su GitHub (Sostituisci col tuo link diretto se necessario)
            # Esempio: "https://raw.githubusercontent.com/TUO_UTENTE/TUO_REPO/main/manuale.md"
            url_manuale = f"https://raw.githubusercontent.com/{st.secrets['github']['user']}/{st.secrets['github']['repo']}/main/manuale.md"
            response = requests.get(url_manuale)
            if response.status_code == 200:
                st.markdown(f'<div class="manual-container">', unsafe_allow_html=True)
                st.markdown(response.text)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Non riesco a leggere il file manuale.md su GitHub. Controlla il link o che il file sia pubblico.")
        except:
            st.error("❌ Errore di connessione a GitHub per il Manuale.")

    elif sel == "📥 Carico Rapido":
            st.markdown(f'<div class="main-header"><h1>Carico Rapido Documenti</h1><p>Proprietà Jacopo</p></div>', unsafe_allow_html=True)
            
            # Questo comando crea l'area dove trascinare i file
            uploaded_files = st.file_uploader("Trascina qui i documenti o le foto dal tuo PC", accept_multiple_files=True)
            
            if not uploaded_files:
                st.info("👋 Socio, trascina qui i file (PDF o immagini) che vuoi archiviare!")
            else:
                st.write(f"Hai selezionato **{len(uploaded_files)}** file da elaborare:")
                
                for uploaded_file in uploaded_files:
                    # Usiamo il nome del file come chiave per non fare confusione
                    with st.expander(f"📄 {uploaded_file.name}", expanded=True):
                        col_view, col_actions = st.columns([1, 1])
                        
                        with col_view:
                            # Se è una foto, la vediamo subito
                            if uploaded_file.type.startswith('image/'):
                                st.image(uploaded_file, use_container_width=True)
                            else:
                                st.caption("📎 Documento PDF/Altro (Anteprima non disponibile)")
                        
                        with col_actions:
                            # Scegliamo la destinazione nella Proprietà
                            st_scelta = st.selectbox("In quale stanza?", ["Seleziona..."] + stanze, key=f"st_{uploaded_file.name}")
                            
                            if st_scelta != "Seleziona...":
                                sn_formattata = st_scelta.capitalize()
                                res_art = sb.table("arredamento").select("id, articolo").eq("stanza", sn_formattata).execute()
                                
                                if res_art.data:
                                    opzioni = {r['articolo']: r['id'] for r in res_art.data}
                                    art_scelto = st.selectbox("Associa all'articolo:", [""] + list(opzioni.keys()), key=f"art_{uploaded_file.name}")
                                    desc_doc = st.text_input("Descrizione (es: Fattura)", value=uploaded_file.name, key=f"desc_{uploaded_file.name}")
                                    
                                    if st.button("🚀 Archivia Documento", key=f"btn_{uploaded_file.name}"):
                                        if art_scelto:
                                            with st.spinner("Archiviazione nella Proprietà in corso..."):
                                                # Recuperiamo l'ID dell'articolo scelto dal dizionario opzioni
                                                id_articolo = opzioni[art_scelto]
                                                
                                                # Eseguiamo l'upload vero!
                                                successo = upload_documento(uploaded_file, id_articolo, desc_doc)
                                                
                                                if successo:
                                                    st.success(f"✅ '{uploaded_file.name}' archiviato con successo nella Proprietà Jacopo!")
                                                    st.balloons()
                                        else:
                                            st.warning("Socio, devi prima selezionare un articolo!")
                                else:
                                    st.warning("Non ci sono articoli in questa stanza.")

# ... poi continuano gli altri elif per le stanze o il manuale ...


    elif "📦" in sel or "✨" in sel:
        is_wish = "✨" in sel
        sn = "Wishlist" if is_wish else sel.replace("📦 ", "").capitalize()
        st.title(f"{sel}")



        res = sb.table("arredamento").select("*").eq("stanza", sn).execute()
        df = clean_df(pd.DataFrame(res.data))
        # --- AGGIUNGI QUESTE RIGHE QUI SOTTO ---
        if not df.empty:
            df = df.sort_values(by="id", ascending=True).reset_index(drop=True)
        # ---------------------------------------        
        
        if not df.empty:
            is_closed = any(df['Stanza Chiusa'] == True)
            if is_closed and not is_wish: st.markdown(f'<div class="gold-seal">🏆 COMPLIMENTI! La stanza {sn} è completata!</div>', unsafe_allow_html=True)
            t_imp, t_ver = df['Importo Totale'].sum(), df['Versato'].sum()
            c1, c2 = st.columns(2)
            c1.markdown(f'<div class="metric-card">TOTALE STANZA<div class="metric-value">{t_imp:,.2f}€</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card">PAGATO STANZA<div class="metric-value">{t_ver:,.2f}€</div></div>', unsafe_allow_html=True)

# --- 1. SEZIONE NOTE ---
            with st.expander("📝 NOTE"):
                # Selettore specifico per le note
                art_per_nota = st.selectbox("Seleziona Articolo per la nota:", df['DV'].tolist(), key=f"sel_nota_{sn}")
                idx_n = df[df['DV'] == art_per_nota].index[0]

                nt_key = f"note_val_{sn}_{idx_n}"
                if nt_key not in st.session_state:
                    st.session_state[nt_key] = str(df.at[idx_n, 'Note'])

                nt = st.text_area("Nota:", value=st.session_state[nt_key], height=100, key=f"area_note_{sn}")
                if st.button("Conferma Nota", key=f"btn_note_{sn}"):
                    st.session_state[nt_key] = nt
                    st.success("Nota pronta!")

            # --- 2. GESTIONE DOCUMENTI (PLATINUM EDITION) ---
            st.markdown("---")
            with st.expander("📂 GESTIONE DOCUMENTI (Fatture, Scontrini, Garanzie)"):
                # Creiamo la lista usando l'ID che abbiamo recuperato prima
                opzioni_art = df[['id', 'Articolo']].values.tolist()

                scelta = st.selectbox(
                    "Seleziona l'articolo a cui riferire il documento:",
                    opzioni_art,
                    format_func=lambda x: x[1],
                    key=f"sel_parent_doc_{sn}"
                )

                id_parent = scelta[0]

                st.write("---")
                st.subheader("📄 Documenti già presenti:")
                # --- AGGIUNTA: IL FRENO A MANO (Sotto il titolo) ---
                conferma_canc_doc = st.checkbox("🔓 Autorizzo la cancellazione definitiva dei file", key=f"check_del_doc_{sn}")
                # 1. Recupero dati
                docs = sb.table("documenti_arredo").select("*").eq("parent_id", id_parent).execute()

                if docs.data:
                    # --- CSS PULITO (senza sovrapposizioni) ---
                    st.markdown("""
                        <style>
                            /* Spazio tra le righe più naturale */
                            [data-testid="stVerticalBlock"] > div:has(div[data-testid="stColumn"]) {
                                gap: 0.2rem !important;
                                margin-bottom: 0px !important;
                            }
                            /* Testo piccolo per la tabella */
                            .small-text {
                                font-size: 14px !important;
                            }
                        </style>
                    """, unsafe_allow_html=True)

                    st.write("---")
                    # Intestazione
                    h1, h2, h3 = st.columns([6, 1, 1])
                    h1.caption("DESCRIZIONE")
                    h2.caption("VEDI")
                    h3.caption("ELIM")

                    for d in docs.data:
                        c1, c2, c3 = st.columns([6, 1, 1])

                        with c1:
                            st.markdown(f"<div class='small-text'>🔹 {d['nome_documento']}</div>", unsafe_allow_html=True)

                        with c2:
                            # Link testuale invece del bottone
                            st.markdown(f"[:eye: Apri]({d['link_file']})")

                        with c3:
                            # Bottone "invisibile" che sembra testo
                            # --- MODIFICA: LOGICA DI CONTROLLO ---
                            if st.button("🗑️ Canc", key=f"del_{d['id']}", help="Elimina documento"):
                                # CONTROLLO SICUREZZA
                                if not conferma_canc_doc:
                                    st.error("⚠️ Spunta la casella sopra per autorizzare!")
                                    st.stop() # Blocca e tiene il messaggio a video
                                else:
                                    try:
                                        # Eliminazione Database
                                        sb.table("documenti_arredo").delete().eq("id", d['id']).execute()
                                        
                                        # Eliminazione Storage (Ottimo che l'avevi già prevista!)
                                        path_to_remove = d['link_file'].split('/')[-1]
                                        full_path = f"{id_parent}/{path_to_remove}"
                                        sb.storage.from_("documenti_proprieta").remove([full_path])
                                        
                                        st.success("Rimosso!") # Successo invece di toast per visibilità
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Errore: {e}")
                    st.write("---")
                else:
                    st.info("Nessun documento caricato.")


                # 1. Inizializziamo il contatore per forzare il refresh
                if f"cnt_{sn}" not in st.session_state:
                    st.session_state[f"cnt_{sn}"] = 0

                # 2. La KEY del widget cambia ogni volta (grazie al contatore)
                nome_doc = st.text_input(
                    "Descrizione documento (es: Fattura Forno)",
                    value="",
                    key=f"input_doc_{sn}_{st.session_state[f'cnt_{sn}']}"
                )

                file_caricato = st.file_uploader(
                    "Carica PDF o Immagine",
                    type=['pdf', 'png', 'jpg', 'jpeg'],
                    key=f"up_doc_{sn}_{st.session_state[f'cnt_{sn}']}"
                )

                if st.button("🚀 Salva Documento", key=f"btn_save_doc_{sn}"):
                    if file_caricato and nome_doc:
                        try:
                            # --- TUTTO QUESTO DEVE ESSERE SOTTO IL TRY ---
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                            # Pulizia nome file per evitare Errore 400
                            nome_file_pulito = file_caricato.name.replace(" ", "_").replace("è", "e").replace("à", "a").replace("ò", "o")
                            file_path = f"{id_parent}/{timestamp}_{nome_file_pulito}"

                            # Upload nello Storage
                            sb.storage.from_("documenti_proprieta").upload(
                                file_path,
                                file_caricato.getvalue(),
                                {"content-type": file_caricato.type}
                            )

                            # URL Pubblico e inserimento nel Database
                            url_doc = sb.storage.from_("documenti_proprieta").get_public_url(file_path)
                            sb.table("documenti_arredo").insert({
                                "parent_id": id_parent,
                                "nome_documento": nome_doc,
                                "link_file": url_doc
                            }).execute()

                            # --- IL COLPO DI GRAZIA PER SBIANCARE ---
                            # Aumentiamo il contatore: al rerun la KEY cambierà e il campo sarà vuoto
                            st.session_state[f"cnt_{sn}"] += 1

                            st.success(f"Documento '{nome_doc}' salvato!")
                            time.sleep(1)
                            st.rerun()

                        except Exception as e:
                            st.error(f"Errore: {e}")
                    else:
                        st.warning("Compila descrizione e seleziona un file!")



            # --- 3. INIZIO FORM TABELLA ---
            with st.form(f"f_{sn}"):
                check_chiusura = st.checkbox("🔒 Chiudi Stanza (Attiva Sigillo Oro)", value=is_closed) if not is_wish else False
# --- VERSIONE AGGIORNATA DEL TUO CFG ---

# --- 1. FORZATURA DECIMALI (Senza questo non scriverai mai il punto) ---
                for col in ['Prezzo Pieno', 'Sconto %', 'Versato', 'Acquistato', 'Costo', 'Importo Totale']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).astype(float)

        # --- 2. CONFIGURAZIONE COLONNE (Aggiunto step per sbloccare il punto) ---
                cfg = {
                    "Prezzo Pieno": st.column_config.NumberColumn("Prezzo Pieno", format="%.2f", step=0.01),
                    "Sconto %": st.column_config.NumberColumn("Sconto %", format="%.2f", step=0.01),
                    "Versato": st.column_config.NumberColumn("Versato", format="%.2f", step=0.01),
                    "Acquistato": st.column_config.NumberColumn("Quantità", format="%.2f", step=0.1),
                    "Costo": st.column_config.NumberColumn("Costo Unit.", format="%.2f", step=0.01),
                    "Importo Totale": st.column_config.NumberColumn("Totale", format="%.2f", step=0.01),
                    "Acquista S/N": st.column_config.SelectboxColumn("Acquista S/N", options=["S", "N"]),
                    "Stato Pagamento": st.column_config.SelectboxColumn("Stato Pagamento", options=["", "Acconto", "Saldato", "Preventivo"]),
                    "Data Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"),
                    "Link Fattura": st.column_config.LinkColumn("📂 Doc", display_text="Apri"),
                    "Link": st.column_config.LinkColumn("🔗 Web", display_text="Apri"),
                    "Foto": st.column_config.LinkColumn("📸 Foto", display_text="Vedi")
                }

# --- 3. EDITOR ---
                df_per_editor = df.drop(columns=['DV', 'stanza'])

# Nascondiamo l'id dall'ordine delle colonne (Socio, questa è la chiave!)
                colonne_visibili = [c for c in df_per_editor.columns if c != 'id']

                df_e = st.data_editor(
                    df_per_editor,
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic" if edit_struct else "fixed",
                    column_config=cfg,
                    column_order=colonne_visibili, # L'id c'è nel DF ma non viene disegnato
                    key=f"editor_{sn}"
                )
# --- 1. IL "FRENO A MANO" DI SICUREZZA ---
                st.write("---")
                conferma_canc = st.checkbox("🔓 Autorizzo la cancellazione definitiva delle righe rimosse")
                if st.form_submit_button("💾 SALVA TUTTO"):
                    try:
                        stato_editor = st.session_state.get(f"editor_{sn}")
                        
                        if stato_editor and stato_editor.get("deleted_rows"):
                            # SE MANCA IL CHECK: Messaggio persistente e blocco ricaricamento
                            if not conferma_canc:
                                st.error("⚠️ ATTENZIONE: Hai rimosso delle righe ma NON hai autorizzato la cancellazione. Per sicurezza i dati NON sono stati toccati. Spunta la casella 'Autorizzo...' e premi Salva, oppure cambia stanza per annullare.")
                                st.info("💡 Suggerimento: Se volevi solo nasconderle, ricorda che la cancellazione è definitiva.")
                                st.stop()  # <--- QUESTO blocca tutto e tiene il messaggio a video!
                            
                            # SE IL CHECK C'È: Messaggio di avvertimento definitivo
                            else:
                                st.warning("❗ CANCELLAZIONE DEFINITIVA IN CORSO...")
                                # Qui il codice procede a cancellare...
                                for idx in stato_editor["deleted_rows"]:
                                    id_da_cancellare = df_per_editor.iloc[idx].get('id')
                                    if id_da_cancellare and id_da_cancellare != 0:
                                        sb.table("arredamento").delete().eq("id", id_da_cancellare).execute()
                                st.success("✅ Record eliminati definitivamente dalla Proprietà.")
                        # PuliAMO i dati: trasforma tutti i vuoti in 0 così i calcoli non falliscono
                        df_e = df_e.fillna(0) 
                        df_e['Acquista S/N'] = df_e['Acquista S/N'].replace(0, 'N')                        
                        # Prepariamo i dati aggiornando le logiche di calcolo
                        df_e['Stanza Chiusa'] = check_chiusura
                        for i in range(len(df_e)):
                            k = f"note_val_{sn}_{i}"
                            if k in st.session_state:
                                df_e.at[df_e.index[i], 'Note'] = st.session_state[k]

                            p = float(df_e.iloc[i].get('Prezzo Pieno', 0))
                            s = float(df_e.iloc[i].get('Sconto %', 0))
                            q = float(df_e.iloc[i].get('Acquistato', 1))

                            c = p * (1-(s/100)) if p > 0 else float(df_e.iloc[i].get('Costo', 0))
                            df_e.at[df_e.index[i], 'Costo'] = c
                            df_e.at[df_e.index[i], 'Importo Totale'] = c * q

                            if "Saldato" in str(df_e.iloc[i].get('Stato Pagamento', '')):
                                df_e.at[df_e.index[i], 'Versato'] = c * q
                                df_e.at[df_e.index[i], 'Data Scadenza'] = None

                        # --- LOGICA UPSERT (PLATINUM) ---
                        mappa_colonne = {
                            'id': 'id',
                            'articolo': 'Articolo', 'acquistato': 'Acquistato', 'costo': 'Costo',
                            'importo_totale': 'Importo Totale', 'acquista_sn': 'Acquista S/N',
                            'note': 'Note', 'versato': 'Versato', 'prezzo_pieno': 'Prezzo Pieno',
                            'sconto_perc': 'Sconto %', 'stato_pagamento': 'Stato Pagamento',
                            'link_fattura': 'Link Fattura', 'link': 'Link', 'foto': 'Foto',
                            'data_scadenza': 'Data Scadenza', 'stanza_chiusa': 'Stanza Chiusa'
                        }
                        inv_map = {v: k for k, v in mappa_colonne.items()}


                        # 1. Forza la colonna a essere di tipo data e trasforma errori (come lo 0) in NaT
                        df_e['Data Scadenza'] = pd.to_datetime(df_e['Data Scadenza'], errors='coerce')

                        # 2. Formattazione finale: se è una data valida, scrivi la stringa, altrimenti None
                        df_e['Data Scadenza'] = df_e['Data Scadenza'].apply(
                            lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) and hasattr(x, 'strftime') else None
                        )

                        # 3. Ora rinominiamo per il database
                        df_db = df_e.rename(columns=inv_map)
                        df_db['stanza'] = sn

                        # Qui forziamo il calcolo per il database

                        # 4. IL FILTRO LASER: Se dopo il rename qualche '0' è rimasto, lo polverizziamo
                        if 'data_scadenza' in df_db.columns:
                        # --- TRASFORMAZIONE CON PULIZIA TOTALE (PROTEGGIAMO L'ID) ---
                        # Creiamo una lista di colonne da pulire (TUTTE tranne l'id)
                            colonne_da_pulire = [c for c in df_db.columns if c != 'id']
                        
                        # Applichiamo la pulizia solo a quelle colonne
                        df_db[colonne_da_pulire] = df_db[colonne_da_pulire].replace(['0', 0, '0000-00-00', 'nan', 'NaN', 'None', 'NaT', '1970-01-01'], None)
                        
                        # Trasformiamo in dizionario finale assicurandoci che i null siano reali
                        dati_finali = df_db.where(pd.notnull(df_db), None).to_dict(orient='records')

                        # --- IL FILTRO DEFINITIVO ---
                        nuove_righe = []
                        righe_esistenti = []

                        for riga in dati_finali:
                            # 1. RECUPERO VALORI (Nomi esatti dallo schema SQL)
                            p_pieno = float(riga.get('prezzo_pieno') or 0)
                            s_percento = float(riga.get('sconto_perc') or 0) # Da schema: sconto_perc
                            qta = float(riga.get('acquistato') or 1)         # Da schema: acquistato
                            costo_u = float(riga.get('costo') or 0)          # Da schema: costo

                            # 2. LOGICA DI CALCOLO RIGOROSA
                            if s_percento >= 99.0:
                                riga['importo_totale'] = 0.0
                                riga['sconto_perc'] = 100.0
                            elif p_pieno > 0:
                                nuovo_costo = p_pieno * (1 - (s_percento / 100))
                                riga['costo'] = nuovo_costo
                                riga['importo_totale'] = nuovo_costo * qta
                            else:
                                riga['importo_totale'] = costo_u * qta

                            # 3. GESTIONE ID (Serial - Auto-incremento)
                            val_id = riga.get('id')
                            # Se l'ID è 0, None o NaN, la trattiamo come riga NUOVA
                            if val_id is None or pd.isna(val_id) or str(val_id) == '0' or val_id == 0:
                                riga.pop('id', None) # Fondamentale per attivare il 'serial' di Supabase
                                nuove_righe.append(riga)
                            else:
                                righe_esistenti.append(riga)

                        # --- ESECUZIONE SALVATAGGIO ---
                        if nuove_righe:
                            sb.table("arredamento").insert(nuove_righe).execute()
                        
                        if righe_esistenti:
                            sb.table("arredamento").upsert(righe_esistenti, on_conflict="id").execute()

                        st.balloons()
                        st.success(f"**Proprietà** Jacopo aggiornata con successo! ✅")
                        time.sleep(1)
                        st.rerun()

                    except Exception as e:
                        st.error(f"Errore durante il salvataggio Platinum: {e}")
