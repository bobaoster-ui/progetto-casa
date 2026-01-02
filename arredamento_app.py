import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. CONFIGURAZIONE PAGINA (Sempre al primo posto)
st.set_page_config(page_title="Monitoraggio Arredamento", layout="wide", page_icon="🏠")

# --- FUNZIONE DI LOGIN ---
def check_password():
    def password_entered():
        if (
            st.session_state["username"] == st.secrets["auth"]["username"]
            and st.session_state["password"] == st.secrets["auth"]["password"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Accesso Riservato")
        st.text_input("Utente", key="username")
        st.text_input("Password", type="password", key="password")
        if st.button("Accedi"):
            password_entered()
            st.rerun()
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Accesso Riservato")
        st.text_input("Utente", key="username")
        st.text_input("Password", type="password", key="password")
        if st.button("Accedi"):
            password_entered()
            st.rerun()
        st.error("😕 Utente o password errati")
        return False
    return True

# --- ESECUZIONE APP ---
if check_password():
    # Inizializziamo la connessione dentro il blocco autorizzato
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Sidebar per il Logout
    if st.sidebar.button("Esci / Logout"):
        st.session_state["password_correct"] = False
        st.rerun()

    st.title("🏠 Monitoraggio Spese Arredamento")

    # Definiamo le stanze e il menu
    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]
    opzioni_menu = ["Riepilogo"] + stanze_reali
    selezione = st.sidebar.selectbox("Vai a:", opzioni_menu)

    # --- CASO A: RIEPILOGO ---
    if selezione == "Riepilogo":
        st.subheader("📊 Analisi Investimento Totale")
        # ... (Logica riepilogo identica alla precedente)
        totale_confermato = 0
        totale_potenziale = 0
        dati_per_grafico = []
        with st.spinner("Caricamento..."):
            for s in stanze_reali:
                try:
                    temp_df = conn.read(worksheet=s, ttl=0)
                    if temp_df is not None and not temp_df.empty:
                        temp_df.columns = [str(c).strip() for c in temp_df.columns]
                        col_prezzo = next((c for c in ['Importo Totale', 'Costo', 'Prezzo'] if c in temp_df.columns), None)
                        col_scelta = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in temp_df.columns), None)
                        if col_prezzo:
                            temp_df[col_prezzo] = pd.to_numeric(temp_df[col_prezzo], errors='coerce').fillna(0)
                            s_pot = temp_df[col_prezzo].sum()
                            totale_potenziale += s_pot
                            s_conf = 0
                            if col_scelta:
                                temp_df[col_scelta] = temp_df[col_scelta].astype(str).str.strip().str.upper()
                                s_conf = temp_df[(temp_df[col_scelta] == 'S') | (temp_df[col_scelta] == '1')][col_prezzo].sum()
                            totale_confermato += s_conf
                            dati_per_grafico.append({"Stanza": s.capitalize(), "Confermato": s_conf, "Totale": s_pot})
                except: continue

        c1, c2, c3 = st.columns(3)
        c1.metric("CONFERMATO (S)", f"{totale_confermato:,.2f} €")
        c2.metric("TOTALE (S+N)", f"{totale_potenziale:,.2f} €")
        c3.metric("DA DECIDERE", f"{totale_potenziale - totale_confermato:,.2f} €")

        if dati_per_grafico:
            df_plot = pd.DataFrame(dati_per_grafico)
            fig_bar = px.bar(df_plot, x="Stanza", y=["Confermato", "Totale"], barmode="group")
            st.plotly_chart(fig_bar, use_container_width=True)

    # --- CASO B: STANZA SINGOLA ---
    else:
        st.subheader(f"Dettaglio: {selezione.capitalize()}")
        try:
            df = conn.read(worksheet=selezione, ttl=0)
            if df is not None:
                df.columns = [str(c).strip() for c in df.columns]
                col_prezzo = next((c for c in ['Costo', 'Prezzo'] if c in df.columns), None)
                col_quantita = next((c for c in ['Acquistato', 'Quantità'] if c in df.columns), None)
                col_totale = next((c for c in ['Importo Totale', 'Totale'] if c in df.columns), None)
                col_scelta = next((c for c in ['Acquista S/N', 'S/N'] if c in df.columns), None)

                config_colonne = {
                    col_prezzo: st.column_config.NumberColumn(format="%.2f €"),
                    col_totale: st.column_config.NumberColumn(format="%.2f €", disabled=True)
                }
                if col_scelta:
                    config_colonne[col_scelta] = st.column_config.SelectboxColumn("Acquista?", options=["S", "N"])

                df_edit = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config_colonne, key=f"ed_{selezione}", num_rows="dynamic")

                if st.button(f"💾 SALVA {selezione.upper()}"):
                    df_salvataggio = df_edit.dropna(how='all').copy()
                    if col_prezzo and col_quantita and col_totale:
                        p = pd.to_numeric(df_salvataggio[col_prezzo].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                        q = pd.to_numeric(df_salvataggio[col_quantita], errors='coerce').fillna(0)
                        df_salvataggio[col_totale] = (p * q).round(2)
                    conn.update(worksheet=selezione, data=df_salvataggio)
                    st.success("Dati salvati!")
                    st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")
