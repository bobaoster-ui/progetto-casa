import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time
import requests
import io  # <--- AGGIUNGI SOLO QUESTO

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V22.10.11", layout="wide", page_icon="🚀")

# --- CONNESSIONE SUPABASE ---
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

sb = get_supabase()

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

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass

        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)

        # 1. MENU DI NAVIGAZIONE
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze] + ["📖 Manuale"])

        # 2. MODIFICA STRUTTURA
        edit_struct = st.toggle("⚙️ Modifica Struttura", False)

        st.markdown("<br>---<br>✨ **Roberto & Gemini**<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)

# 3. IL PARACADUTE (BACKUP)

# --- LOGICA GENERAZIONE BACKUP ---
        if st.sidebar.button("📊 GENERA BACKUP TOTALE"):
            try:
                # 1. Recupero dati da Supabase
                res_arredo = sb.table("arredamento").select("*").execute()
                res_docs = sb.table("documenti_arredo").select("*").execute()

                df_arredo = pd.DataFrame(res_arredo.data)
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

    if sel == "🏠 Riepilogo":
        st.markdown('<div class="main-header"><h1>Command Center</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        bud = 15000.0
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
                    p.cell(30,10,'Stanza',1,0,'C',1); p.cell(90,10,'Articolo',1,0,'C',1); p.cell(35,10,'Totale',1,0,'C',1); p.cell(35,10,'Versato',1,1,'C',1)
                    p.set_font('Arial','',9); p.set_text_color(0,0,0)
                    for _, r in df_r.iterrows():
                        y=p.get_y(); p.set_xy(40,y); p.multi_cell(90,10,str(r['DV']).encode('latin-1','replace').decode('latin-1'),1); h=max(p.get_y()-y,10)
                        p.set_xy(10,y); p.cell(30,h,str(r['stanza']),1); p.set_xy(130,y); p.cell(35,h,f"{r['Importo Totale']:,.2f}",1); p.cell(35,h,f"{r['Versato']:,.2f}",1,1)

                    # --- AGGIUNTA TOTALI (INSERISCI DA QUI) ---
                    p.ln(2); p.set_font('Arial','B',10); p.set_fill_color(220,220,220)
                    t_i = df_r['Importo Totale'].sum(); t_v = df_r['Versato'].sum()
                    p.cell(120,10,'TOTALE GENERALE PROPRIETÀ',1,0,'R',1)
                    p.cell(35,10,f"{t_i:,.2f}",1,0,'C',1)
                    p.cell(35,10,f"{t_v:,.2f}",1,1,'C',1)
                    # --- FINE AGGIUNTA ---

                    st.download_button("📥 Scarica PDF", bytes(p.output(dest='S')), "Report.pdf")


            c_t.dataframe(df_r[['stanza','DV','Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

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

    elif "📦" in sel or "✨" in sel:
        is_wish = "✨" in sel
        sn = "Wishlist" if is_wish else sel.replace("📦 ", "").capitalize()
        st.title(f"{sel}")

        # 1. RECUPERO DATI GLOBALI (Per la Dashboard di tutta la casa)
        res_tutto = sb.table("arredamento").select("*").execute()
        df_tutto = pd.DataFrame(res_tutto.data)

        # --- DASHBOARD GLOBALE ---
        st.write("### 📊 Riepilogo Totale Proprietà")
        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric("Totale Arredi", f"{len(df_tutto)} pz")

        with c2:
            # Usiamo 'Costo' visto che ora sappiamo che si chiama così!
            if 'Costo' in df_tutto.columns:
                prezzi = pd.to_numeric(df_tutto['Costo'], errors='coerce').fillna(0)
                st.metric("Valore Totale", f"€ {prezzi.sum():,.2f}")
            else:
                st.metric("Valore Totale", "N/A (Verifica colonna)")

        with c3:
            # Conteggio documenti totale
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

        res = sb.table("arredamento").select("*").eq("stanza", sn).execute()
        df = clean_df(pd.DataFrame(res.data))
        
        
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
                            if st.button("🗑️ Canc", key=f"del_{d['id']}", help="Elimina documento"):
                                try:
                                    sb.table("documenti_arredo").delete().eq("id", d['id']).execute()
                                    path_to_remove = d['link_file'].split('/')[-1]
                                    full_path = f"{id_parent}/{path_to_remove}"
                                    sb.storage.from_("documenti_proprieta").remove([full_path])
                                    st.toast("Rimosso!")
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


                if st.form_submit_button("💾 SALVA TUTTO"):
                    try:
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

                        df_db = df_e.rename(columns=inv_map)
                        df_db['stanza'] = sn

                        # Formattazione date (PULITA PER SUPABASE)
                        if 'data_scadenza' in df_db.columns:
                            df_db['data_scadenza'] = df_db['data_scadenza'].apply(
                                lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) and hasattr(x, 'strftime') else None
                            )

                        # --- TRASFORMAZIONE CON PULIZIA NaT/NaN ---
                        # Questa riga risolve l'errore "NaTType is not JSON serializable"
                        dati_finali = df_db.where(pd.notnull(df_db), None).to_dict(orient='records')

                        # Eseguiamo l'UPSERT
                        sb.table("arredamento").upsert(dati_finali, on_conflict="id").execute()

                        st.balloons()
                        st.success(f"**Proprietà** Jacopo aggiornata con successo! ✅")
                        time.sleep(1)
                        st.rerun()

                    except Exception as e:
                        st.error(f"Errore durante il salvataggio Platinum: {e}")
