import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V12.5", layout="wide", page_icon="🏠")

COLOR_AZZURRO = (46, 117, 182)

class PDF(FPDF):
    def header(self):
        self.set_fill_color(*COLOR_AZZURRO)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        # Regola: Proprietà con à accentata
        testo = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

def safe_clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    # Forziamo le colonne a testo per evitare il blocco numerico
    text_cols = ['Oggetto', 'Articolo', 'Link', 'Note', 'Link Fattura', 'Acquista S/N', 'S/N']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace(['None', 'nan', '104807'], '')

    cols_num = ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']
    for c in cols_num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    return df

if "password_correct" not in st.session_state:
    st.title("🔒 Accesso Riservato")
    u = st.text_input("Utente")
    p = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Credenziali errate")
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: st.info("Logo non caricato")
        st.markdown("---")
        can_edit_structure = st.toggle("Modifica Struttura", value=False)
        selezione = st.selectbox("Menu:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

    # --- 1. RIEPILOGO GENERALE ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")

        try:
            # Lettura Budget: proviamo a leggere la colonna 'Valore' direttamente
            df_imp = conn.read(worksheet="Impostazioni", ttl=0)
            budget_iniziale = float(df_imp['Valore'].iloc[0])
        except:
            budget_iniziale = 15000.0 # Valore di emergenza se Sheets fallisce

        all_rows = []
        for s in stanze_reali:
            try:
                df_s = safe_clean_df(conn.read(worksheet=s, ttl=0))
                if not df_s.empty:
                    # Tenta di trovare la colonna S/N corretta
                    c_sn = 'Acquista S/N' if 'Acquista S/N' in df_s.columns else 'S/N'
                    # Filtra solo quelli con "S"
                    df_c = df_s[df_s[c_sn].str.upper().str.strip() == 'S'].copy()
                    if not df_c.empty:
                        df_c['Ambiente'] = s.capitalize()
                        all_rows.append(df_c)
            except: continue

        if all_rows:
            df_final = pd.concat(all_rows)
            tot_conf = df_final['Importo Totale'].sum()
            tot_versato = df_final['Versato'].sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("BUDGET", f"{budget_iniziale:,.2f} €")
            c2.metric("CONFERMATO", f"{tot_conf:,.2f} €", delta=f"{budget_iniziale-tot_conf:,.2f} residuo")
            c3.metric("PAGATO", f"{tot_versato:,.2f} €")

            st.divider()
            st.subheader("Dettaglio Oggetti Acquistati")
            st.dataframe(df_final[['Ambiente', 'Oggetto', 'Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

            if st.button("📄 Genera Report PDF"):
                pdf = PDF(); pdf.add_page(); pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(*COLOR_AZZURRO); pdf.set_text_color(255,255,255)
                pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True); pdf.cell(90, 10, 'Articolo', 1, 0, 'C', True); pdf.cell(35, 10, 'Totale', 1, 0, 'C', True); pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)
                pdf.set_font('Arial', '', 9); pdf.set_text_color(0,0,0)
                for _, row in df_final.iterrows():
                    x_s, y_s = pdf.get_x(), pdf.get_y()
                    pdf.cell(30, 10, str(row['Ambiente']), 1)
                    pdf.multi_cell(90, 5, str(row['Oggetto']).encode('latin-1', 'replace').decode('latin-1'), 1)
                    y_e = pdf.get_y(); pdf.set_xy(x_s + 120, y_s); h = max(10, y_e - y_s)
                    pdf.cell(35, h, f"{row['Importo Totale']:,.2f}", 1, 0, 'R'); pdf.cell(35, h, f"{row['Versato']:,.2f}", 1, 1, 'R')

                st.download_button("📥 Scarica Report PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="Report_Jacopo.pdf", mime="application/pdf")
        else: st.warning("Nessun oggetto risulta acquistato (metti 'S' nella colonna Acquista S/N).")

    # --- 2. STANZE ---
    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=selezione, ttl=0))
        c_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        c_stato = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'

        with st.form(f"form_{selezione}"):
            config = {
                c_sn: st.column_config.SelectboxColumn(c_sn, options=["S", "N"]),
                c_stato: st.column_config.SelectboxColumn(c_stato, options=["", "Acconto", "Saldato", "Ordinato", "Preventivo"]),
                "Link": st.column_config.LinkColumn("Link Fattura", help="Clicca per aprire, scrivi per modificare"),
                "Note": st.column_config.TextColumn("Note")
            }
            df_edit = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config, num_rows="dynamic" if can_edit_structure else "fixed")

            if st.form_submit_button("💾 SALVA"):
                conn.update(worksheet=selezione, data=df_edit)
                st.success("Sincronizzazione completata!"); st.balloons(); time.sleep(1); st.rerun()

    # --- 3. WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
        w_config = {"Foto": st.column_config.ImageColumn("Anteprima"), "Link": st.column_config.LinkColumn("Link Prodotto")}
        df_ed_w = st.data_editor(df_w, use_container_width=True, hide_index=True, column_config=w_config, num_rows="dynamic" if can_edit_structure else "fixed")
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w); st.balloons(); st.rerun()
