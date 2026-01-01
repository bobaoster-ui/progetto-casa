import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# Configurazione Pagina
st.set_page_config(page_title="Monitoraggio Casa", page_icon="🏠", layout="wide")

st.title("🏠 Monitoraggio Casa")

# --- CONNESSIONE DIRETTA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def pulisci_df(df):
    """Pulisce i dati e converte i prezzi (es. 6.878,22 della cucina)"""
    df.columns = [str(c).strip() for c in df.columns]
    if 'Acquista S/N' not in df.columns: df['Acquista S/N'] = "N"

    for col in ['Costo', 'Importo Totale', 'Acquistato']:
        if col in df.columns:
            # Rimuove simboli e sistema la punteggiatura italiana
            df[col] = df[col].astype(str).str.replace('€', '').str.replace('.', '').str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Importo Totale'] = df['Acquistato'] * df['Costo']
    return df

# Nomi stanze (Assicurati che su Google Sheets siano tornati così)
nomi_stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

st.sidebar.header("📍 Navigazione")
selezione = st.sidebar.selectbox("Vai a:", ["Riepilogo"] + nomi_stanze)

# --- LOGICA DI CARICAMENTO ---
if selezione == "Riepilogo":
    st.subheader("Situazione Generale Spese")
    try:
        # Legge il foglio senza specificare la tab per sbloccare la cache
        conn.read(ttl="1s")
        st.sidebar.success("✅ Sistema Online")
        st.info("Seleziona una stanza dal menu per vedere i prezzi.")
    except Exception as e:
        st.sidebar.error("❌ Errore di Sincronizzazione")
        st.write("Verifica l'URL nei Secrets.")

else:
    st.subheader(f"Gestione: {selezione}")
    try:
        # Carichiamo i dati con un timeout minimo per evitare il blocco "clessidra"
        df_raw = conn.read(worksheet=selezione, ttl="1s")

        if df_raw is not None:
            df = pulisci_df(df_raw)

            # Tabella Interattiva
            df_edit = st.data_editor(
                df,
                column_config={
                    "Acquista S/N": st.column_config.SelectboxColumn("Acquista", options=["S", "N"]),
                    "Costo": st.column_config.NumberColumn("Costo €", format="%.2f"),
                    "Importo Totale": st.column_config.NumberColumn("Totale €", format="%.2f", disabled=True)
                },
                hide_index=True, use_container_width=True, key=f"ed_{selezione}"
            )

            if st.button("💾 AGGIORNA CLOUD"):
                conn.update(worksheet=selezione, data=df_edit)
                st.success("Dati inviati con successo!")
                time.sleep(1)
                st.rerun()
    except Exception as e:
        st.error(f"Errore nella lettura della tab '{selezione}'")
        st.info("💡 CONSIGLIO: Su Google Sheets, vai nella tab 'camera', seleziona tutto, COPIA, crea una nuova tab, INCOLLA e chiamala di nuovo 'camera'.")
