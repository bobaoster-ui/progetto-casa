import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V14.9", layout="wide", page_icon="🏠")

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
    text_cols = ['Oggetto', 'Articolo', 'Note', 'Acquista S/N', 'S/N', 'Stato Pagamento', 'Stato', 'Link Fattura', 'Link']
    for col in text_cols:
        if col in df.columns:
            # Sostituiamo nan e None con stringa vuota per evitare brutte scritte nel PDF
            df[col] = df[col].astype(str).replace(['None', 'nan', '104807', '<NA>'], '')

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
        can_edit_structure = st.toggle("Modifica Struttura", value=False)
        selezione = st.selectbox("Menu:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)

    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")
        try:
            df_imp = conn.read(worksheet="Impostazioni", ttl=0, header=None)
            budget_iniziale = float(df_imp.iloc[1, 1])
        except: budget_iniziale = 15000.0

        all_rows = []
        for s in stanze_reali:
            try:
                df_s = safe_clean_df(conn.read(worksheet=s, ttl=0))
                if not df_s.empty:
                    c_sn = 'Acquista S/N' if 'Acquista S/N' in df_s.columns else 'S/N'
                    df_c = df_s[df_s[c_sn].str.upper().str.strip() == 'S'].copy()
                    if not df_c.empty:
                        df_c['Ambiente'] = s.capitalize()
                        all_rows.append(df_c)
            except: continue

        if all_rows:
            df_final = pd.concat(all_rows)

            if st.button("📄 Genera Report PDF"):
                try:
                    pdf = PDF()
                    pdf.add_page()
                    pdf.set_font('Arial', 'B', 10)
                    pdf.set_fill_color(*COLOR_AZZURRO)
                    pdf.set_text_color(255, 255, 255)

                    # Intestazioni
                    pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True)
                    pdf.cell(90, 10, 'Articolo', 1, 0, 'C', True)
                    pdf.cell(35, 10, 'Totale', 1, 0, 'C', True)
                    pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)

                    pdf.set_font('Arial', '', 9)
                    pdf.set_text_color(0, 0, 0)

                    for _, row in df_final.iterrows():
                        # Prepariamo i testi
                        stanza = str(row['Ambiente'])
                        articolo = str(row['Oggetto']).encode('latin-1', 'replace').decode('latin-1')
                        totale = f"{row['Importo Totale']:,.2f}"
                        versato = f"{row['Versato']:,.2f}"

                        # 1. Calcoliamo quante linee servono per l'articolo
                        linee = pdf.multi_cell(90, 5, articolo, split_only=True)
                        h_riga = max(10, len(linee) * 5)

                        # 2. Otteniamo la posizione corrente
                        curr_x = pdf.get_x()
                        curr_y = pdf.get_y()

                        # 3. Disegniamo tutte le celle con la stessa altezza h_riga
                        pdf.cell(30, h_riga, stanza, 1, 0, 'L')

                        # multi_cell per l'articolo (bisogna resettare la X dopo)
                        pdf.multi_cell(90, 5, articolo, 1, 'L')

                        # Torniamo su per disegnare le ultime due colonne
                        pdf.set_xy(curr_x + 120, curr_y)
                        pdf.cell(35, h_riga, totale, 1, 0, 'R')
                        pdf.cell(35, h_riga, versato, 1, 1, 'R')

                    pdf_bytes = pdf.output(dest='S')
                    st.download_button("📥 Scarica Report PDF", data=bytes(pdf_bytes), file_name="Report_Arredi.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Errore: {e}")

            st.dataframe(df_final[['Ambiente', 'Oggetto', 'Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=selezione, ttl=0))
        col_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        col_stato = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'

        with st.form(f"form_{selezione}"):
            config = {
                col_sn: st.column_config.SelectboxColumn(col_sn, options=["S", "N"]),
                col_stato: st.column_config.SelectboxColumn(col_stato, options=["", "Acconto", "Saldato", "Ordinato", "Preventivo"]),
                "Link Fattura": st.column_config.LinkColumn("📂 Fattura", display_text="🌐 Apri Documento"),
                "Note": st.column_config.TextColumn("Note")
            }
            df_edit = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config, num_rows="dynamic" if can_edit_structure else "fixed")

            if st.form_submit_button("💾 SALVA"):
                for i in range(len(df_edit)):
                    try:
                        p, s, q = float(df_edit.iloc[i]['Prezzo Pieno']), float(df_edit.iloc[i]['Sconto %']), float(df_edit.iloc[i]['Acquistato'])
                        costo = p * (1 - (s/100)) if p > 0 else float(df_edit.iloc[i]['Costo'])
                        totale = costo * q
                        df_edit.at[df_edit.index[i], 'Costo'] = costo
                        df_edit.at[df_edit.index[i], 'Importo Totale'] = totale

                        stato_val = str(df_edit.iloc[i][col_stato]).strip()
                        if stato_val == "" or stato_val.lower() == "none":
                            df_edit.at[df_edit.index[i], 'Versato'] = 0.0
                        elif stato_val == "Saldato":
                            df_edit.at[df_edit.index[i], 'Versato'] = totale
                    except: continue
                conn.update(worksheet=selezione, data=df_edit)
                st.success("Dati salvati!"); st.balloons(); time.sleep(1); st.rerun()

    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
        w_config = {"Foto": st.column_config.ImageColumn("Anteprima"), "Link": st.column_config.LinkColumn("🔗 Web", display_text="🌐 Vai al sito")}
        df_ed_w = st.data_editor(df_w, use_container_width=True, hide_index=True, column_config=w_config, num_rows="dynamic" if can_edit_structure else "fixed")
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w); st.balloons(); st.rerun()
