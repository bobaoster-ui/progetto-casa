import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURAZIONE (Sempre al primo posto)
st.set_page_config(page_title="Monitoraggio Arredamento", layout="wide", page_icon="🏠")

# 2. CONNESSIONE AL DATABASE
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. LOGICA DEL MENU (Nella barra laterale)
st.title("🏠 Monitoraggio Spese Arredamento")
opzioni_menu = ["Riepilogo"] + ["camera", "cucina", "salotto", "tavolo", "lavori"]
selezione = st.sidebar.selectbox("Vai a:", opzioni_menu)

# --- CASO A: VISUALIZZAZIONE RIEPILOGO ---
if selezione == "Riepilogo":
    st.subheader("📊 Riepilogo Generale dell'Investimento")

    col_rip1, col_rip2 = st.columns(2)
    totale_confermato = 0
    totale_potenziale = 0
    dati_riepilogo = []

    with st.spinner("Calcolo totali in corso..."):
        # Ciclo su tutte le tab per sommare i dati
        for s in ["camera", "cucina", "salotto", "tavolo", "lavori"]:
            try:
                temp_df = conn.read(worksheet=s, ttl=0)
                if temp_df is not None and not temp_df.empty:
                    temp_df.columns = [str(c).strip() for c in temp_df.columns]

                    # Cerca colonne Prezzo e Scelta (nomi flessibili)
                    col_prezzo = next((c for c in ['Importo Totale', 'Costo', 'Prezzo'] if c in temp_df.columns), None)
                    col_scelta = next((c for c in ['Acquista S/N', 'S/N', 'Acquistato'] if c in temp_df.columns), None)

                    if col_prezzo:
                        temp_df[col_prezzo] = pd.to_numeric(temp_df[col_prezzo], errors='coerce').fillna(0)
                        somma_pot = temp_df[col_prezzo].sum()
                        totale_potenziale += somma_pot

                        if col_scelta:
                            temp_df[col_scelta] = temp_df[col_scelta].astype(str).str.strip().str.upper()
                            spesa_conf = temp_df[(temp_df[col_scelta] == 'S') | (temp_df[col_scelta] == '1')][col_prezzo].sum()
                        else:
                            spesa_conf = 0

                        totale_confermato += spesa_conf
                        dati_riepilogo.append({
                            "Stanza": s.capitalize(),
                            "Confermato (S)": f"{spesa_conf:,.2f} €",
                            "Totale Stanza": f"{somma_pot:,.2f} €"
                        })
            except:
                continue

    # Mostra i totali in alto
    with col_rip1:
        st.metric(label="CONFERMATO (S)", value=f"{totale_confermato:,.2f} €")
    with col_rip2:
        differenza = totale_potenziale - totale_confermato
        st.metric(label="POTENZIALE TOTALE", value=f"{totale_potenziale:,.2f} €",
                  delta=f"-{differenza:,.2f} € da decidere", delta_color="inverse")

    st.divider()
    if dati_riepilogo:
        st.table(pd.DataFrame(dati_riepilogo))

# --- CASO B: VISUALIZZAZIONE STANZA SINGOLA ---
else:
    st.subheader(f"Dettaglio: {selezione.capitalize()}")
    try:
        df = conn.read(worksheet=selezione, ttl=0)
        if df is not None:
            # Editor per modificare i dati direttamente
            df_edit = st.data_editor(df, use_container_width=True, hide_index=True, key=f"ed_{selezione}", num_rows="dynamic")

            if st.button(f"💾 SALVA MODIFICHE {selezione.upper()}"):
                with st.spinner("Salvataggio su Google Sheets..."):
                    conn.update(worksheet=selezione, data=df_edit)
                    st.success("Dati aggiornati!")
                    st.balloons()
                    st.rerun()
    except Exception as e:
        st.error(f"Errore nel caricamento della stanza {selezione}.")
        st.info("Verifica che il nome della tab su Google Sheets sia tutto minuscolo.")
