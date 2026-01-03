import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V8.4", layout="wide", page_icon="🏠")

# Palette Colori
COLOR_AZZURRO = (46, 117, 182)

# --- CLASSE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(*COLOR_AZZURRO)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        # Regola fissa: Proprietà con à accentata
        testo = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

# --- FUNZIONE PULIZIA DATI ---
def safe_clean_df(df):
    if df is None or df.empty: return pd.DataFrame(), 'Acquista S/N', 'Stato Pagamento'
    df.columns = [str(c).strip() for c in df.columns]

    if 'Oggetto' not in df.columns and 'Articolo' in df.columns:
        df['Oggetto'] = df['Articolo']

    col_sn = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df.columns), 'Acquista S/N')
    col_stato = next((c for c in ['Stato Pagamento', 'Stato', 'Pagamento'] if c in df.columns), 'Stato Pagamento')

    if col_sn not in df.columns: df[col_sn] = 'N'
    if col_stato not in df.columns: df[col_stato] = ''

    # Assicuriamoci che le colonne numeriche esistano
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        if c not in df.columns: df[c] = 0.0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

    return df, col_sn, col_stato

# --- LOGIN ---
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
        # LOGO
        try: st.image("logo.png", use_container_width=True)
        except: st.info("Carica 'logo.png' per vederlo qui.")

        st.markdown("---")
        can_edit_structure = st.toggle("Modifica Struttura", value=False)
        selezione = st.selectbox("Menu Principale:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

    # --- 1. RIEPILOGO GENERALE ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")
        all_rows = []
        for s in stanze_reali:
            try:
                df_s, col_sn, _ = safe_clean_df(conn.read(worksheet=s, ttl=0))
                if not df_s.empty:
                    df_c = df_s[df_s[col_sn].astype(str).str.upper() == 'S'].copy()
                    if not df_c.empty:
                        df_c['Ambiente'] = s.capitalize()
                        all_rows.append(df_c)
            except: continue

        if all_rows:
            df_final = pd.concat(all_rows)
            tot_conf, tot_versato = df_final['Importo Totale'].sum(), df_final['Versato'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("CONFERMATO", f"{tot_conf:,.2f} €")
            m2.metric("PAGATO", f"{tot_versato:,.2f} €")
            m3.metric("DA SALDARE", f"{(tot_conf - tot_versato):,.2f} €")

            st.divider()
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.pie(df_final.groupby('Ambiente')['Importo Totale'].sum().reset_index(), values='Importo Totale', names='Ambiente', title="Budget per Stanza", hole=0.4), use_container_width=True)
            with g2: st.plotly_chart(px.bar(pd.DataFrame({"Stato": ["Pagato", "Residuo"], "Euro": [tot_versato, max(0, tot_conf - tot_versato)]}), x="Stato", y="Euro", color="Stato", color_discrete_map={"Pagato":"#2ECC71","Residuo":"#E74C3C"}), use_container_width=True)

            st.dataframe(df_final[['Ambiente', 'Oggetto', 'Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

            if st.button("📄 Genera Report PDF"):
                try:
                    pdf = PDF(); pdf.add_page(); pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(*COLOR_AZZURRO); pdf.set_text_color(255,255,255)
                    pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True); pdf.cell(90, 10, 'Articolo', 1, 0, 'C', True); pdf.cell(35, 10, 'Totale', 1, 0, 'C', True); pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)
                    pdf.set_font('Arial', '', 9); pdf.set_text_color(0,0,0)
                    for _, row in df_final.iterrows():
                        pdf.cell(30, 8, str(row['Ambiente']), 1); pdf.cell(90, 8, str(row['Oggetto'])[:45].encode('latin-1', 'replace').decode('latin-1'), 1); pdf.cell(35, 8, f"{row['Importo Totale']:,.2f}", 1, 0, 'R'); pdf.cell(35, 8, f"{row['Versato']:,.2f}", 1, 1, 'R')
                    pdf_out = pdf.output(dest='S')
                    if not isinstance(pdf_out, bytes): pdf_out = bytes(pdf_out, 'latin-1') if isinstance(pdf_out, str) else bytes(pdf_out)
                    st.download_button("📥 Scarica Report PDF", data=pdf_out, file_name="Report_Jacopo.pdf", mime="application/pdf")
                except Exception as e: st.error(f"Errore PDF: {e}")
        else: st.warning("Nessun dato confermato trovato.")

    # --- 2. STANZE ---
    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")
        df, col_sn, col_stato = safe_clean_df(conn.read(worksheet=selezione, ttl=0))

        with st.form(f"form_{selezione}"):
            config = {
                col_sn: st.column_config.SelectboxColumn(col_sn, options=["S", "N"], required=True),
                col_stato: st.column_config.SelectboxColumn(col_stato, options=["", "Acconto", "Saldato", "Ordinato", "Preventivo"])
            }
            df_edit = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config, num_rows="dynamic" if can_edit_structure else "fixed")

            if st.form_submit_button("💾 SALVA"):
                # Applichiamo i calcoli riga per riga sul dataframe modificato
                for i in range(len(df_edit)):
                    try:
                        p = float(df_edit.iloc[i]['Prezzo Pieno'])
                        s = float(df_edit.iloc[i]['Sconto %'])
                        q = float(df_edit.iloc[i]['Acquistato'])

                        # Calcolo Costo Unitario
                        costo = p * (1 - (s/100)) if p > 0 else float(df_edit.iloc[i]['Costo'])
                        df_edit.at[df_edit.index[i], 'Costo'] = costo

                        # Calcolo Importo Totale
                        totale_riga = costo * q
                        df_edit.at[df_edit.index[i], 'Importo Totale'] = totale_riga

                        # LOGICA SALDATO (Controllo stringa pulita)
                        stato_val = str(df_edit.iloc[i][col_stato]).strip()
                        if stato_val == "Saldato":
                            df_edit.at[df_edit.index[i], 'Versato'] = totale_riga
                    except:
                        continue

                conn.update(worksheet=selezione, data=df_edit)
                st.balloons()
                st.success("Dati aggiornati correttamente!")
                time.sleep(1.5)
                st.rerun()

    # --- 3. WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        df_w, _, _ = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
        df_ed_w = st.data_editor(df_w, use_container_width=True, hide_index=True)
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w)
            st.balloons(); st.rerun()
