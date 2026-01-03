import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V15.3", layout="wide", page_icon="🏠")

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
            df[col] = df[col].astype(str).replace(['None', 'nan', '104807', '<NA>', 'undefined', 'nan'], '')
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
        except: pass
        st.markdown("---")
        can_edit_structure = st.toggle("Modifica Struttura", value=False)
        selezione = st.selectbox("Menu:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

    # --- RIEPILOGO GENERALE ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")

        # Lettura Budget potenziata
        try:
            df_imp = conn.read(worksheet="Impostazioni", ttl=0)
            # Cerchiamo il valore numerico nella prima colonna o nella seconda
            budget_iniziale = pd.to_numeric(df_imp.iloc[0, 1], errors='coerce')
            if pd.isna(budget_iniziale): budget_iniziale = 15000.0
        except:
            budget_iniziale = 15000.0

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
            tot_conf = df_final['Importo Totale'].sum()
            tot_versato = df_final['Versato'].sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("BUDGET", f"{budget_iniziale:,.2f} €")
            c2.metric("CONFERMATO", f"{tot_conf:,.2f} €", delta=f"{budget_iniziale-tot_conf:,.2f}")
            c3.metric("PAGATO", f"{tot_versato:,.2f} €")

            st.divider()

            if st.button("📄 Genera Report PDF Senza Scalini"):
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
                        # Pulizia Nan
                        art_val = str(row['Oggetto']).replace('nan', '').strip()
                        txt = art_val.encode('latin-1', 'replace').decode('latin-1')
                        stanza = str(row['Ambiente'])
                        v_tot = f"{row['Importo Totale']:,.2f}"
                        v_ver = f"{row['Versato']:,.2f}"

                        # Calcolo altezza riga
                        linee = pdf.multi_cell(90, 5, txt, split_only=True)
                        h_riga = max(10, len(linee) * 5)

                        # Controllo fine pagina
                        if pdf.get_y() + h_riga > 270:
                            pdf.add_page()

                        x, y = pdf.get_x(), pdf.get_y()

                        # Disegno delle celle con altezza fissa h_riga
                        pdf.rect(x, y, 30, h_riga)
                        pdf.set_xy(x, y)
                        pdf.cell(30, h_riga, stanza, 0, 0, 'L')

                        pdf.rect(x + 30, y, 90, h_riga)
                        pdf.set_xy(x + 30, y)
                        pdf.multi_cell(90, 5, txt, 0, 'L')

                        pdf.rect(x + 120, y, 35, h_riga)
                        pdf.set_xy(x + 120, y)
                        pdf.cell(35, h_riga, v_tot, 0, 0, 'R')

                        pdf.rect(x + 155, y, 35, h_riga)
                        pdf.set_xy(x + 155, y)
                        pdf.cell(35, h_riga, v_ver, 0, 1, 'R')

                        pdf.set_y(y + h_riga)

                    data_pdf = pdf.output(dest='S')
                    st.download_button("📥 Scarica Report PDF", data=bytes(data_pdf), file_name="Report_Arredi.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Errore: {e}")

            st.subheader("Dettaglio Articoli")
            st.dataframe(df_final[['Ambiente', 'Oggetto', 'Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

            st.divider()
            g1, g2 = st.columns(2)
            with g1:
                df_pie = df_final.groupby('Ambiente')['Importo Totale'].sum().reset_index()
                st.plotly_chart(px.pie(df_pie, values='Importo Totale', names='Ambiente', title="Spesa per Stanza", hole=0.4), use_container_width=True)
            with g2:
                df_bar = pd.DataFrame({"Voce": ["Budget", "Confermato", "Pagato"], "Euro": [budget_iniziale, tot_conf, tot_versato]})
                st.plotly_chart(px.bar(df_bar, x="Voce", y="Euro", color="Voce"), use_container_width=True)

    # --- STANZE ---
    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=selezione, ttl=0))
        col_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        col_stato = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'

        with st.form(f"form_{selezione}"):
            config = {
                col_sn: st.column_config.SelectboxColumn(col_sn, options=["S", "N"]),
                col_stato: st.column_config.SelectboxColumn(col_stato, options=["", "Acconto", "Saldato", "Ordinato", "Preventivo"]),
                "Link Fattura": st.column_config.LinkColumn("📂 Fattura", display_text="🌐 Apri Documento")
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
                st.success("Salvataggio riuscito!"); st.balloons(); time.sleep(1); st.rerun()

    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
        w_config = {"Foto": st.column_config.ImageColumn("Anteprima"), "Link": st.column_config.LinkColumn("🔗 Web", display_text="🌐 Vai al sito")}
        df_ed_w = st.data_editor(df_w, use_container_width=True, hide_index=True, column_config=w_config, num_rows="dynamic" if can_edit_structure else "fixed")
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w); st.balloons(); st.rerun()
