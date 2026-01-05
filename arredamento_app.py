import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# --- [BLINDATO: SICUREZZA E CONFIGURAZIONE] ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V22.7.1", layout="wide", page_icon="🏆")

# --- [BLINDATO: STILE E CSS] ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
grad = "linear-gradient(90deg, #0f2027, #203a43, #2c5364)" if st.session_state.dark_mode else "linear-gradient(90deg, #2e5a88, #4a90e2)"

st.markdown(f"""<style>
    .stApp {{background-color: {bc}; color: {tc};}}
    .main-header {{background: {grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px;}}
    .metric-card {{background-color: {cc}; padding: 20px; border-radius: 12px; border-bottom: 5px solid #2e5a88; text-align: center; color: {tc};}}
    .metric-value {{font-size: 1.8em; font-weight: 800; color: #2e5a88;}}
    .metric-value-mini {{font-size: 1.4em; font-weight: 700; color: #d4af37;}}
    .gold-seal {{background: linear-gradient(145deg, #ffdf00, #d4af37); padding: 20px; border-radius: 15px; text-align: center; color: black; font-weight: bold; border: 2px solid #b8860b; margin: 20px 0; box-shadow: 0px 4px 15px rgba(212, 175, 55, 0.4);}}
</style>""", unsafe_allow_html=True)

# --- [BLINDATO: FUNZIONI CORE] ---
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
    df.columns = [str(c).strip() for c in df.columns]
    df['DV'] = df['Articolo'] if 'Articolo' in df.columns else df.get('Oggetto', 'N/A')
    for c in ['Note', 'Acquista S/N', 'S/N', 'Stato Pagamento', 'Stato', 'Link Fattura', 'Link', 'Foto', 'Stanza Chiusa']:
        if c in df.columns: df[c] = df[c].astype(str).replace(['None', 'nan', '<NA>', 'null', ''], '')
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    if 'Data Scadenza' in df.columns: df['Data Scadenza'] = pd.to_datetime(df['Data Scadenza'], errors='coerce')
    return df

# --- [ACCESSO] ---
if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]: st.session_state.password_correct = True; st.rerun()
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze])
        edit_struct = st.toggle("⚙️ Modifica Struttura", False)
        st.markdown("<br>---<br>✨ **Roberto & Gemini**<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    if "Riepilogo" in sel:
        st.markdown('<div class="main-header"><h1>Command Center 🏆</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        try: bud = pd.to_numeric(conn.read(worksheet="Impostazioni", ttl="5m").iloc[0,1], errors='coerce')
        except: bud = 15000.0
        all_d = []
        for s in stanze:
            try:
                d = clean_df(conn.read(worksheet=s, ttl="1m"))
                if not d.empty:
                    cs = 'Acquista S/N' if 'Acquista S/N' in d.columns else 'S/N'
                    dc = d[d[cs].str.upper().str.strip() == 'S'].copy(); dc['Stanza'] = s.capitalize(); all_d.append(dc)
            except: continue
        if all_d:
            df_r = pd.concat(all_d); conf, pag = df_r['Importo Totale'].sum(), df_r['Versato'].sum()
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card">BUDGET<div class="metric-value">{bud:,.0f}€</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card">CONFERMATO<div class="metric-value">{conf:,.0f}€</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{pag:,.0f}€</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="metric-card">DISPONIBILE<div class="metric-value">{bud-conf:,.0f}€</div></div>', unsafe_allow_html=True)

            sc = df_r[df_r['Data Scadenza'].notna() & (df_r['Versato'] < df_r['Importo Totale'])].copy()
            if not sc.empty:
                st.subheader("🗓️ Scadenzario")
                sc['gg'] = (sc['Data Scadenza'] - pd.Timestamp(datetime.now().date())).dt.days
                sc['Stato'] = sc['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                st.dataframe(sc.sort_values('gg')[['Stanza','DV','Data Scadenza','Stato']], use_container_width=True, hide_index=True)

            c_p, c_t = st.columns([1, 1.2])
            with c_p:
                st.plotly_chart(px.pie(df_r, values='Importo Totale', names='Stanza', hole=0.5), use_container_width=True)
                if st.button("📄 PDF"):
                    p = PDF(); p.add_page(); p.set_font('Arial', 'B', 10)
                    st.download_button("📥 Scarica PDF", bytes(p.output(dest='S')), "Report.pdf")
            c_t.dataframe(df_r[['Stanza','DV','Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

    elif "📦" in sel:
        sn = sel.replace("📦 ", "").lower(); st.title(f"🏠 {sn.capitalize()}")
        try:
            df = clean_df(conn.read(worksheet=sn, ttl="0"))

            if 'Stanza Chiusa' not in df.columns: df['Stanza Chiusa'] = "FALSE"
            is_closed = str(df.at[0, 'Stanza Chiusa']).upper() == "TRUE"

            head1, head2 = st.columns([3, 1])
            with head2:
                new_status = st.toggle("🔒 Chiudi Stanza", value=is_closed, key=f"tog_{sn}")
                if new_status != is_closed:
                    df['Stanza Chiusa'] = "TRUE" if new_status else "FALSE"
                    conn.update(worksheet=sn, data=df.fillna('')); st.rerun()

            if new_status:
                st.markdown(f'<div class="gold-seal">🏆 COMPLIMENTI! La stanza {sn.capitalize()} è stata ufficialmente completata!</div>', unsafe_allow_html=True)

            t_imp, t_ver = df['Importo Totale'].sum(), df['Versato'].sum()
            col_t1, col_t2 = st.columns(2)
            col_t1.markdown(f'<div class="metric-card">TOTALE STANZA<div class="metric-value-mini">{t_imp:,.2f}€</div></div>', unsafe_allow_html=True)
            col_t2.markdown(f'<div class="metric-card">PAGATO STANZA<div class="metric-value-mini">{t_ver:,.2f}€</div></div>', unsafe_allow_html=True)

            c_st, c_sn = ('Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'), ('Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N')

            with st.form(f"f_{sn}"):
                # Mostriamo Stanza Chiusa nell'editor come richiesto
                cols_to_show = [c for c in df.columns if c not in ['DV']]
                cfg = {
                    c_sn: st.column_config.SelectboxColumn(c_sn, options=["S", "N"]),
                    c_st: st.column_config.SelectboxColumn(c_st, options=["", "Acconto", "Saldato", "Preventivo"]),
                    "Stanza Chiusa": st.column_config.SelectboxColumn("Stanza Chiusa", options=["TRUE", "FALSE"]),
                    "Data Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"),
                    "Link Fattura": st.column_config.LinkColumn("📂 Doc Drive", display_text="Apri")
                }
                df_e = st.data_editor(df[cols_to_show], use_container_width=True, hide_index=True, num_rows="dynamic" if edit_struct else "fixed", column_config=cfg)

                if st.form_submit_button("💾 SALVA TUTTO"):
                    for i in range(len(df_e)):
                        try:
                            r = df_e.iloc[i]; p, s, q = float(r.get('Prezzo Pieno',0)), float(r.get('Sconto %',0)), float(r.get('Acquistato',1))
                            c = p * (1-(s/100)) if p>0 else float(r.get('Costo',0))
                            df_e.at[df_e.index[i],'Costo'], df_e.at[df_e.index[i],'Importo Totale'] = c, c*q
                            stato = str(r.get(c_st,'')).strip()
                            if stato == "Saldato":
                                df_e.at[df_e.index[i],'Versato'], df_e.at[df_e.index[i],'Data Scadenza'] = c*q, pd.NaT
                            elif (not stato or stato == "") and df_e.at[df_e.index[i],'Versato'] == df_e.at[df_e.index[i],'Importo Totale']:
                                df_e.at[df_e.index[i],'Versato'] = 0.0
                        except: continue
                    conn.update(worksheet=sn, data=df_e.fillna('')); st.cache_data.clear()
                    st.success(f"Dati {sn.capitalize()} salvati!"); st.balloons(); time.sleep(1); st.rerun()

            st.markdown("---")
            st.subheader("🏁 Checklist Fine Lavori")
            try:
                df_c = conn.read(worksheet="collaudi", ttl="5m")
                if sn not in df_c['Stanza'].values:
                    df_c = pd.concat([df_c, pd.DataFrame([{'Stanza': sn, 'Montaggio': False, 'Integrita': False, 'Pulizia': False}])], ignore_index=True)
                idx_c = df_c[df_c['Stanza'] == sn].index[0]
                ch1, ch2, ch3 = st.columns(3)
                v1, v2, v3 = ch1.checkbox("Montaggio OK", value=bool(df_c.at[idx_c, 'Montaggio']), key=f"c1_{sn}"), ch2.checkbox("Integrità", value=bool(df_c.at[idx_c, 'Integrita']), key=f"c2_{sn}"), ch3.checkbox("Pulizia", value=bool(df_c.at[idx_c, 'Pulizia']), key=f"c3_{sn}")
                if st.button(f"Aggiorna Checklist {sn.capitalize()}"):
                    df_c.at[idx_c, 'Montaggio'], df_c.at[idx_c, 'Integrita'], df_c.at[idx_c, 'Pulizia'] = v1, v2, v3
                    conn.update(worksheet="collaudi", data=df_c); st.success("Checklist salvata!"); st.balloons(); time.sleep(1); st.rerun()
            except: st.warning("Foglio 'collaudi' non trovato.")
        except Exception as e: st.error(f"Errore: {e}")

    elif "✨" in sel:
        st.title("✨ Wishlist")
        try:
            df_w = clean_df(conn.read(worksheet="desideri", ttl="0"))
            w_cfg = {"Link": st.column_config.LinkColumn("🔗 Web", display_text="Apri Sito"), "Foto": st.column_config.LinkColumn("📸 Foto", display_text="Vedi Foto")}
            df_ew = st.data_editor(df_w.drop(columns=['DV']), use_container_width=True, hide_index=True, column_config=w_cfg, num_rows="dynamic" if edit_struct else "fixed")
            if st.button("Salva Wishlist"):
                conn.update(worksheet="desideri", data=df_ew.fillna('')); st.cache_data.clear()
                st.success("✨ Wishlist aggiornata!"); st.balloons(); time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Errore: {e}")
