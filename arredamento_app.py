import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V8.7", layout="wide", page_icon="🏠")

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
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]

    if 'Articolo' in df.columns and 'Oggetto' not in df.columns:
        df['Oggetto'] = df['Articolo']

    # Pulizia forzata dei tipi dati
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
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
        except: st.info("Logo non trovato")
        st.markdown("---")
        can_edit_structure = st.toggle("Modifica Struttura", value=False)
        selezione = st.selectbox("Menu:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

    # --- 1. RIEPILOGO GENERALE ---
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
        else: st.warning("Nessun dato confermato trovato.")

    # --- 2. STANZE ---
    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=selezione, ttl=0))

        c_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        c_stato = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'

        with st.form(f"form_{selezione}"):
            config = {
                c_sn: st.column_config.SelectboxColumn(c_sn, options=["S", "N"]),
                c_stato: st.column_config.SelectboxColumn(c_stato, options=["", "Acconto", "Saldato", "Ordinato", "Preventivo"])
            }
            # L'editor ora restituisce i dati modificati
            df_edit = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config, num_rows="dynamic" if can_edit_structure else "fixed")

            if st.form_submit_button("💾 SALVA MODIFICHE"):
                # Creiamo un nuovo DataFrame da zero per evitare residui di memoria
                df_updated = df_edit.copy()

                for i in range(len(df_updated)):
                    # Lettura valori riga per riga
                    try:
                        p = float(df_updated.iloc[i]['Prezzo Pieno'])
                        s = float(df_updated.iloc[i]['Sconto %'])
                        q = float(df_updated.iloc[i]['Acquistato'])

                        costo = p * (1 - (s/100)) if p > 0 else float(df_updated.iloc[i]['Costo'])
                        totale = costo * q

                        # Aggiornamento valori numerici
                        df_updated.at[df_updated.index[i], 'Costo'] = costo
                        df_updated.at[df_updated.index[i], 'Importo Totale'] = totale

                        # Logica Saldato
                        stato_pag = str(df_updated.iloc[i][c_stato]).strip()
                        if stato_pag == "Saldato":
                            df_updated.at[df_updated.index[i], 'Versato'] = totale
                    except Exception as e:
                        st.write(f"Nota: riga {i+1} ignorata per dati incompleti.")
                        continue

                # Sincronizzazione finale con Google Sheets
                conn.update(worksheet=selezione, data=df_updated)
                st.balloons()
                st.success("Sincronizzazione completata!")
                time.sleep(1)
                st.rerun()

    # --- 3. WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
        df_ed_w = st.data_editor(df_w, use_container_width=True, hide_index=True)
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w)
            st.balloons(); st.rerun()
