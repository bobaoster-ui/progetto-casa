import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# --- 1. SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

# --- 2. CONFIGURAZIONE PAGINA ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
st.set_page_config(page_title="Monitoraggio Arredamento V20.6", layout="wide", page_icon="🚀")

bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
grad = "linear-gradient(90deg, #0f2027, #203a43, #2c5364)" if st.session_state.dark_mode else "linear-gradient(90deg, #2e5a88, #4a90e2)"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bc}; color: {tc}; }}
    .main-header {{ background: {grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }}
    .metric-card {{ background-color: {cc}; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-bottom: 5px solid #2e5a88; text-align: center; color: {tc}; }}
    .metric-value {{ font-size: 1.8em; font-weight: 800; color: #2e5a88; }}
    </style>
    """, unsafe_allow_html=True)

COLOR_AZZURRO = (46, 117, 182)

class PDF(FPDF):
    def header(self):
        self.set_fill_color(*COLOR_AZZURRO)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        testo = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128, 128, 128)
        firma = "Prodotto di Proprietà: Roberto & Gemini"
        self.cell(0, 10, firma.encode('latin-1', 'replace').decode('latin-1'), 0, 0, 'C')

def safe_clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    if 'Articolo' in df.columns: df['DV'] = df['Articolo']
    elif 'Oggetto' in df.columns: df['DV'] = df['Oggetto']
    for c in ['Note', 'Acquista S/N', 'S/N', 'Stato Pagamento', 'Stato', 'Link Fattura', 'Link', 'Foto']:
        if c in df.columns: df[c] = df[col].astype(str).replace(['None', 'nan', '<NA>', 'null'], '') if 'col' in locals() else df[c].astype(str).replace(['None', 'nan', '<NA>', 'null'], '')
    nums = ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']
    for c in nums:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    if 'Data Scadenza' in df.columns:
        df['Data Scadenza'] = pd.to_datetime(df['Data Scadenza'], errors='coerce')
    return df

if "password_correct" not in st.session_state:
    st.title("🔒 Accesso Riservato")
    u, p = st.text_input("Utente"), st.text_input("Password", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True; st.rerun()
        else: st.error("Credenziali errate")
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.session_state.dark_mode = st.toggle("🌙 Notte", value=st.session_state.dark_mode)
        selezione = st.selectbox("MENU", ["🏠 Riepilogo Generale", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze_reali])
        st.markdown("---")
        can_edit_structure = st.toggle("⚙️ Struttura", False)
        st.markdown("<br><br><br>---<br>✨ **Roberto & Gemini**", unsafe_allow_html=True)
        st.markdown("<small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    if "Riepilogo" in selezione:
        st.markdown(f'<div class="main-header"><h1>Command Center</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        try:
            df_imp = conn.read(worksheet="Impostazioni", ttl="5m")
            budget_totale = pd.to_numeric(df_imp.iloc[0, 1], errors='coerce')
        except: budget_totale = 15000.0

        all_rows = []
        for s in stanze_reali:
            df_s = safe_clean_df(conn.read(worksheet=s, ttl="1m"))
            if not df_s.empty:
                c_sn = 'Acquista S/N' if 'Acquista S/N' in df_s.columns else 'S/N'
                df_c = df_s[df_s[c_sn].str.upper().str.strip() == 'S'].copy()
                df_c['Stanza'] = s.capitalize(); all_rows.append(df_c)

        if all_rows:
            df_final = pd.concat(all_rows)
            tot_conf, tot_versato = df_final['Importo Totale'].sum(), df_final['Versato'].sum()

            m1, m2, m3, m4 = st.columns(4)
            with m1: st.markdown(f'<div class="metric-card">BUDGET<div class="metric-value">{budget_totale:,.0f}€</div></div>', unsafe_allow_html=True)
            with m2: st.markdown(f'<div class="metric-card">CONFERMATO<div class="metric-value">{tot_conf:,.0f}€</div></div>', unsafe_allow_html=True)
            with m3: st.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{tot_versato:,.0f}€</div></div>', unsafe_allow_html=True)
            with m4: st.markdown(f'<div class="metric-card">DISPONIBILE<div class="metric-value">{budget_totale - tot_conf:,.0f}€</div></div>', unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("🗓️ Scadenzario Pagamenti")
            df_scad = df_final[(df_final['Data Scadenza'].notna()) & (df_final['Versato'] < df_final['Importo Totale'])].copy()
            if not df_scad.empty:
                df_scad['gg'] = (df_scad['Data Scadenza'] - pd.Timestamp(datetime.now().date())).dt.days
                df_scad['Stato Scadenza'] = df_scad['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 IN TEMPO"))

                # RIPRISTINO BOTTONI COLORATI
                st.dataframe(
                    df_scad.sort_values(by='gg')[['Stanza', 'DV', 'Data Scadenza', 'Stato Scadenza']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Stato Scadenza": st.column_config.SelectboxColumn(
                            "Stato Scadenza",
                            options=["🔴 SCADUTO", "🟠 IMMINENTE", "🟢 IN TEMPO"]
                        ),
                        "Data Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY")
                    }
                )

            col_pie, col_tab = st.columns([1, 1.2])
            with col_pie:
                st.plotly_chart(px.pie(df_final, values='Importo Totale', names='Stanza', hole=0.5), use_container_width=True)
                if st.button("📄 Genera Report PDF"):
                    pdf = PDF(); pdf.add_page(); pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(*COLOR_AZZURRO); pdf.set_text_color(255, 255, 255)
                    pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True); pdf.cell(90, 10, 'Articolo', 1, 0, 'C', True); pdf.cell(35, 10, 'Totale', 1, 0, 'C', True); pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)
                    pdf.set_font('Arial', '', 9); pdf.set_text_color(0, 0, 0)
                    for _, row in df_final.iterrows():
                        txt = str(row['DV']).encode('latin-1', 'replace').decode('latin-1')
                        y = pdf.get_y(); pdf.set_xy(40, y); pdf.multi_cell(90, 10, txt, border=1); h = max(pdf.get_y() - y, 10)
                        pdf.set_xy(10, y); pdf.cell(30, h, str(row['Stanza']), 1); pdf.set_xy(130, y); pdf.cell(35, h, f"{row['Importo Totale']:,.2f}", 1, 0, 'R'); pdf.cell(35, h, f"{row['Versato']:,.2f}", 1, 1, 'R')
                    pdf.set_font('Arial', 'B', 10); pdf.cell(120, 10, 'TOTALI GENERALI', 1, 0, 'R'); pdf.cell(35, 10, f"{tot_conf:,.2f}", 1, 0, 'R'); pdf.cell(35, 10, f"{tot_versato:,.2f}", 1, 1, 'R')
                    st.download_button("📥 Scarica PDF", data=bytes(pdf.output(dest='S')), file_name="Report_Arredamento.pdf")
            with col_tab: st.dataframe(df_final[['Stanza', 'DV', 'Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

    elif "📦" in selezione:
        stanza_nome = selezione.replace("📦 ", "").lower()
        st.title(f"🏠 {stanza_nome.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=stanza_nome, ttl="0"))
        c_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        c_st = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'

        with st.expander("📝 EDITOR NOTE AVANZATO"):
            scelta = st.selectbox("Seleziona Articolo:", df['DV'].tolist())
            idx = df[df['DV'] == scelta].index[0]
            nota_nuova = st.text_area("Nota dettagliata:", value=df.at[idx, 'Note'], height=150)
            if st.button("Aggiorna Nota"):
                df.at[idx, 'Note'] = nota_nuova
                st.session_state[f"temp_df_{stanza_nome}"] = df
                st.success("Nota aggiornata! Salva tutto sotto.")

        with st.form(f"form_{stanza_nome}"):
            conf_cols = {
                c_sn: st.column_config.SelectboxColumn(c_sn, options=["S", "N"]),
                c_st: st.column_config.SelectboxColumn(c_st, options=["", "Acconto", "Saldato", "Preventivo"]),
                "Data Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"),
                "Link Fattura": st.column_config.LinkColumn("📂 Doc", display_text="Apri")
            }
            df_to_show = st.session_state.get(f"temp_df_{stanza_nome}", df)
            df_edit = st.data_editor(df_to_show.drop(columns=['DV']), use_container_width=True, hide_index=True, num_rows="dynamic" if can_edit_structure else "fixed", column_config=conf_cols)

            if st.form_submit_button("💾 SALVA TUTTO"):
                for i in range(len(df_edit)):
                    r = df_edit.iloc[i]; p, s, q = float(r.get('Prezzo Pieno',0)), float(r.get('Sconto %',0)), float(r.get('Acquistato',1))
                    costo = p * (1-(s/100)) if p>0 else float(r.get('Costo',0))
                    df_edit.at[df_edit.index[i],'Costo'] = costo; df_edit.at[df_edit.index[i],'Importo Totale'] = costo*q
                    if "Saldato" in str(r.get(c_st,'')): df_edit.at[df_edit.index[i],'Versato'] = costo*q
                conn.update(worksheet=stanza_nome, data=df_edit.fillna(''))
                st.cache_data.clear(); st.success("Dati salvati!"); st.balloons(); time.sleep(1); st.rerun()

    elif "✨" in selezione:
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl="0"))
        w_conf = {"Link": st.column_config.LinkColumn("🔗 Web", display_text="Apri Sito"), "Foto": st.column_config.LinkColumn("📸 Foto", display_text="Vedi Foto")}
        df_ed_w = st.data_editor(df_w.drop(columns=['DV']), use_container_width=True, hide_index=True, column_config=w_conf, num_rows="dynamic" if can_edit_structure else "fixed")
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w.fillna('')); st.cache_data.clear(); st.balloons(); st.rerun()
