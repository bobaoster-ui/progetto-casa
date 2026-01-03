import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V9.2", layout="wide", page_icon="🏠")

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
        # Regola fissa: Proprietà con à
        testo = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

# --- FUNZIONE PULIZIA DATI ---
def safe_clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]

    if 'Articolo' in df.columns and 'Oggetto' not in df.columns:
        df['Oggetto'] = df['Articolo']

    cols_num = ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']
    for c in cols_num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    return df

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
        try: st.image("logo.png", use_container_width=True)
        except: st.info("Carica logo.png")
        st.markdown("---")
        can_edit_structure = st.toggle("Modifica Struttura", value=False)
        selezione = st.selectbox("Menu:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

    # --- RIEPILOGO ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")
        all_rows = []
        for s in stanze_reali:
            try:
                df_s = safe_clean_df(conn.read(worksheet=s, ttl=0))
                if not df_s.empty:
                    col_sn = 'Acquista S/N' if 'Acquista S/N' in df_s.columns else 'S/N'
                    df_c = df_s[df_s[col_sn].astype(str).str.upper() == 'S'].copy()
                    if not df_c.empty:
                        df_c['Ambiente'] = s.capitalize()
                        all_rows.append(df_c)
            except: continue

        if all_rows:
            df_final = pd.concat(all_rows)
            tot_conf, tot_versato = df_final['Importo Totale'].sum(), df_final['Versato'].sum()
            m1, m2, m3 = st.columns(3); m1.metric("CONFERMATO", f"{tot_conf:,.2f} €"); m2.metric("PAGATO", f"{tot_versato:,.2f} €"); m3.metric("DA SALDARE", f"{(tot_conf - tot_versato):,.2f} €")

            st.divider()
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.pie(df_final.groupby('Ambiente')['Importo Totale'].sum().reset_index(), values='Importo Totale', names='Ambiente', title="Budget per Stanza", hole=0.4), use_container_width=True)
            with g2: st.plotly_chart(px.bar(pd.DataFrame({"Stato": ["Pagato", "Residuo"], "Euro": [tot_versato, max(0, tot_conf - tot_versato)]}), x="Stato", y="Euro", color="Stato", color_discrete_map={"Pagato":"#2ECC71","Residuo":"#E74C3C"}), use_container_width=True)

            st.dataframe(df_final[['Ambiente', 'Oggetto', 'Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

            if st.button("📄 Report PDF"):
                pdf = PDF(); pdf.add_page(); pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(*COLOR_AZZURRO); pdf.set_text_color(255,255,255)
                pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True); pdf.cell(90, 10, 'Articolo', 1, 0, 'C', True); pdf.cell(35, 10, 'Totale', 1, 0, 'C', True); pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)
                pdf.set_font('Arial', '', 9); pdf.set_text_color(0,0,0)
                for _, row in df_final.iterrows():
                    pdf.cell(30, 8, str(row['Ambiente']), 1); pdf.cell(90, 8, str(row['Oggetto'])[:45].encode('latin-1', 'replace').decode('latin-1'), 1); pdf.cell(35, 8, f"{row['Importo Totale']:,.2f}", 1, 0, 'R'); pdf.cell(35, 8, f"{row['Versato']:,.2f}", 1, 1, 'R')
                st.download_button("📥 Scarica Report PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="Report_Jacopo.pdf", mime="application/pdf")

    # --- STANZE ---
    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=selezione, ttl=0))
        c_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        c_stato = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'

        # Uso del form per stabilità
        with st.form(f"form_{selezione}"):
            config = {
                c_sn: st.column_config.SelectboxColumn(c_sn, options=["S", "N"]),
                c_stato: st.column_config.SelectboxColumn(c_stato, options=["", "Acconto", "Saldato", "Ordinato", "Preventivo"])
            }
            df_edit = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config, num_rows="dynamic" if can_edit_structure else "fixed")

            if st.form_submit_button("💾 SALVA"):
                # Calcolo riga per riga come nelle versioni stabili
                for i in range(len(df_edit)):
                    try:
                        p, s, q = float(df_edit.iloc[i]['Prezzo Pieno']), float(df_edit.iloc[i]['Sconto %']), float(df_edit.iloc[i]['Acquistato'])
                        costo = p * (1 - (s/100)) if p > 0 else float(df_edit.iloc[i]['Costo'])
                        totale = costo * q
                        df_edit.at[df_edit.index[i], 'Costo'] = costo
                        df_edit.at[df_edit.index[i], 'Importo Totale'] = totale

                        # LOGICA SALDATO (Semplice e diretta)
                        if str(df_edit.iloc[i][c_stato]) == "Saldato":
                            df_edit.at[df_edit.index[i], 'Versato'] = totale
                    except: continue

                conn.update(worksheet=selezione, data=df_edit)
                st.success("Salvato!")
                st.balloons()
                time.sleep(1)
                st.rerun()

    # --- WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
        df_ed_w = st.data_editor(df_w, use_container_width=True, hide_index=True)
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w)
            st.balloons(); st.rerun()
