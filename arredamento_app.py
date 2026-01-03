import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V8.8", layout="wide", page_icon="🏠")

# Palette Colori
COLOR_AZZURRO = (46, 117, 182)

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
        except: st.info("Logo non trovato")
        st.markdown("---")
        can_edit_structure = st.toggle("Modifica Struttura", value=False)
        selezione = st.selectbox("Menu:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

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
            st.dataframe(df_final[['Ambiente', 'Oggetto', 'Importo Totale', 'Versato']], use_container_width=True, hide_index=True)
        else: st.warning("Dati non trovati.")

    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")
        # TTL=0 per leggere sempre l'ultimo dato da Sheets
        df_base = conn.read(worksheet=selezione, ttl=0)
        df = safe_clean_df(df_base)

        c_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        c_stato = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'

        with st.form(key=f"form_v88_{selezione}"):
            config = {
                c_sn: st.column_config.SelectboxColumn(c_sn, options=["S", "N"]),
                c_stato: st.column_config.SelectboxColumn(c_stato, options=["", "Acconto", "Saldato", "Ordinato", "Preventivo"])
            }
            df_edited = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config, num_rows="dynamic" if can_edit_structure else "fixed")

            submit = st.form_submit_button("💾 SALVA DEFINITIVO")

            if submit:
                # 1. Creiamo una copia pulita e resettiamo gli indici
                final_df = df_edited.copy().reset_index(drop=True)

                # 2. Ciclo di ricalcolo forzato
                for i in range(len(final_df)):
                    try:
                        p = float(final_df.loc[i, 'Prezzo Pieno'])
                        s = float(final_df.loc[i, 'Sconto %'])
                        q = float(final_df.loc[i, 'Acquistato'])

                        costo = p * (1 - (s/100)) if p > 0 else float(final_df.loc[i, 'Costo'])
                        totale = costo * q

                        final_df.at[i, 'Costo'] = costo
                        final_df.at[i, 'Importo Totale'] = totale

                        # LOGICA SALDATO
                        valore_stato = str(final_df.loc[i, c_stato]).strip()
                        if valore_stato == "Saldato":
                            final_df.at[i, 'Versato'] = totale
                    except:
                        continue

                # 3. TRUCCO: Convertiamo lo Stato in stringa pulita per Google
                final_df[c_stato] = final_df[c_stato].astype(str).replace("None", "").replace("nan", "")

                # 4. INVIO
                try:
                    conn.update(worksheet=selezione, data=final_df)
                    st.success(f"Dati inviati a Google Sheets per {selezione}!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante l'invio: {e}")

    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
        df_ed_w = st.data_editor(df_w, use_container_width=True, hide_index=True)
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w)
            st.balloons(); st.rerun()
