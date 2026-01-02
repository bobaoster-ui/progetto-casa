import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento", layout="wide", page_icon="🏠")

# --- FUNZIONE DI LOGIN ---
def check_password():
    """Restituisce True se l'utente ha inserito le credenziali corrette."""

    def password_entered():
        """Controlla se le credenziali inserite corrispondono ai Secrets."""
        if (
            st.session_state["username"] == st.secrets["auth"]["username"]
            and st.session_state["password"] == st.secrets["auth"]["password"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Rimuove la password dalla memoria
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Prima volta che si accede: mostra i campi di input
        st.title("🔒 Accesso Riservato")
        st.text_input("Utente", key="username")
        st.text_input("Password", type="password", key="password")
        if st.button("Accedi"):
            password_entered()
            if not st.session_state.get("password_correct", False):
                st.error("😕 Utente o password errati")
        return False

    elif not st.session_state["password_correct"]:
        # Tentativo fallito: mostra di nuovo l'input
        st.text_input("Utente", key="username")
        st.text_input("Password", type="password", key="password")
        if st.button("Accedi"):
            password_entered()
            if not st.session_state["password_correct"]:
                st.error("😕 Utente o password errati")
        return False

    else:
        # Password corretta
        return True

# --- LOGICA DELL'APPLICAZIONE (Eseguita solo se loggati) ---
if check_password():

    # Tasto Logout nella sidebar
    if st.sidebar.button("Esci / Logout"):
        del st.session_state["password_correct"]
        st.rerun()

    # 2. CONNESSIONE
    conn = st.connection("gsheets", type=GSheetsConnection)

    # 3. LOGICA MENU
    st.title("🏠 Monitoraggio Spese Arredamento")
    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]
    opzioni_menu = ["Riepilogo"] + stanze_reali
    selezione = st.sidebar.selectbox("Vai a:", opzioni_menu)

    # --- CASO A: RIEPILOGO CON GRAFICI ---
    if selezione == "Riepilogo":
        st.subheader("📊 Analisi Investimento Totale")

        totale_confermato = 0
        totale_potenziale = 0
        dati_per_grafico = []

        with st.spinner("Elaborazione dati in corso..."):
            for s in stanze_reali:
                try:
                    temp_df = conn.read(worksheet=s, ttl=0)
                    if temp_df is not None and not temp_df.empty:
                        temp_df.columns = [str(c).strip() for c in temp_df.columns]
                        col_prezzo = next((c for c in ['Importo Totale', 'Costo', 'Prezzo'] if c in temp_df.columns), None)
                        col_scelta = next((c for c in ['Acquista S/N', 'S/N', 'Acquistato', 'Scelta'] if c in temp_df.columns), None)

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
                except:
                    continue

        c1, c2, c3 = st.columns(3)
        c1.metric("CONFERMATO (S)", f"{totale_confermato:,.2f} €")
        c2.metric("TOTALE (S+N)", f"{totale_potenziale:,.2f} €")
        c3.metric("DA DECIDERE", f"{totale_potenziale - totale_confermato:,.2f} €")

        st.divider()

        if dati_per_grafico:
            g1, g2 = st.columns(2)
            df_plot = pd.DataFrame(dati_per_grafico)
            with g1:
                st.markdown("##### Distribuzione Spese per Stanza")
                fig_bar = px.bar(df_plot, x="Stanza", y=["Confermato", "Totale"], barmode="group",
                                 color_discrete_sequence=["#2ecc71", "#e74c3c"])
                st.plotly_chart(fig_bar, use_container_width=True)
            with g2:
                st.markdown("##### Stato Budget Totale")
                fig_pie = px.pie(values=[totale_confermato, totale_potenziale - totale_confermato],
                                 names=["Confermato (S)", "Ancora da decidere (N)"],
                                 color_discrete_sequence=["#2ecc71", "#ecf0f1"], hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

# --- CASO B: STANZA SINGOLA CON AGGIUNTA/RIMOZIONE RIGHE ---
else:
    st.subheader(f"Dettaglio: {selezione.capitalize()}")
    try:
        df = conn.read(worksheet=selezione, ttl=0)
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]

            # Identificazione colonne
            col_prezzo = next((c for c in ['Costo', 'Prezzo', 'Prezzo Unitario'] if c in df.columns), None)
            col_quantita = next((c for c in ['Acquistato', 'Quantità', 'Q.tà'] if c in df.columns), None)
            col_totale = next((c for c in ['Importo Totale', 'Totale'] if c in df.columns), None)
            col_scelta = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df.columns), None)

            config_colonne = {
                col_prezzo: st.column_config.NumberColumn(format="%.2f €"),
                col_totale: st.column_config.NumberColumn(format="%.2f €", disabled=True)
            }
            if col_scelta:
                config_colonne[col_scelta] = st.column_config.SelectboxColumn("Acquista?", options=["S", "N"], required=True)

            # IL CUORE DELLA MODIFICA: num_rows="dynamic" permette di aggiungere/togliere
            df_edit = st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                column_config=config_colonne,
                key=f"ed_{selezione}",
                num_rows="dynamic"  # <-- QUESTA È LA MAGIA
            )

            st.info("💡 Per eliminare una riga: selezionala a sinistra e premi 'Canc' sulla tastiera. Per aggiungere: usa il tasto '+' in fondo alla tabella.")

            if st.button(f"💾 SALVA E RICALCOLA {selezione.upper()}"):
                with st.spinner("Aggiornamento database in corso..."):
                    # Creiamo una copia pulita rimuovendo eventuali righe completamente vuote
                    df_salvataggio = df_edit.dropna(how='all').copy()

                    if col_prezzo and col_quantita and col_totale:
                        # Gestione conversione numerica
                        if df_salvataggio[col_prezzo].dtype == object:
                            df_salvataggio[col_prezzo] = df_salvataggio[col_prezzo].astype(str).str.replace(',', '.')

                        p = pd.to_numeric(df_salvataggio[col_prezzo], errors='coerce').fillna(0).astype(float)
                        q = pd.to_numeric(df_salvataggio[col_quantita], errors='coerce').fillna(0).astype(float)

                        # Calcolo finale
                        df_salvataggio[col_totale] = (p * q).round(2)

                        # Riempie eventuali S/N mancanti con 'N' di default per le nuove righe
                        if col_scelta:
                            df_salvataggio[col_scelta] = df_salvataggio[col_scelta].fillna('N').str.upper()

                    conn.update(worksheet=selezione, data=df_salvataggio)
                    st.success(f"Database aggiornato! Righe ricalcolate correttamente.")
                    st.balloons()
                    st.rerun()
    except Exception as e:
        st.error(f"Errore durante l'operazione: {e}")
