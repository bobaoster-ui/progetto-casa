import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# Configurazione Pagina
st.set_page_config(page_title="Monitoraggio Casa", page_icon="🏠", layout="wide")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

def pulisci_df(df):
    """Pulisce i dati e gestisce i formati numerici"""
    df.columns = [str(c).strip() for c in df.columns]
    if 'Acquista S/N' not in df.columns: df['Acquista S/N'] = "N"

    for col in ['Costo', 'Importo Totale', 'Acquistato']:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace('€', '').str.replace('.', '').str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Importo Totale'] = df['Acquistato'] * df['Costo']
    return df

st.title("🏠 Monitoraggio Casa")

# --- NUOVA LOGICA DI RECUPERO TAB ---
# Invece di scrivere noi i nomi, proviamo a leggerli direttamente dal file
try:
    # Carichiamo il foglio senza specificare la tab (legge la prima)
    # e forziamo la pulizia della cache
    df_iniziale = conn.read(ttl=0)
    st.sidebar.success("✅ Cloud Collegato")
except Exception as e:
    st.sidebar.error("❌ Errore connessione")
    st.stop()

# Nomi stanze che hai impostato
nomi_stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

st.sidebar.header("📍 Navigazione")
selezione = st.sidebar.selectbox("Vai a:", ["Riepilogo"] + nomi_stanze)

if selezione == "Riepilogo":
    st.subheader("Situazione Generale Spese")
    st.info("Seleziona una stanza dal menu a sinistra per vedere i tuoi dati (Cucina, Camera, ecc.)")

else:
    stanza_selezionata = selezione
    st.subheader(f"Gestione: {stanza_selezionata}")

    try:
        # TENTATIVO DI LETTURA DIRETTA
        df_origine = conn.read(worksheet=stanza_selezionata, ttl=0)

        if df_origine is not None and not df_origine.empty:
            df_origine = pulisci_df(df_origine)

            df_editabile = st.data_editor(
                df_origine,
                column_config={
                    "Acquista S/N": st.column_config.SelectboxColumn("Acquista", options=["S", "N"]),
                    "Costo": st.column_config.NumberColumn("Costo €", format="%.2f"),
                    "Importo Totale": st.column_config.NumberColumn("Totale €", format="%.2f", disabled=True)
                },
                hide_index=True, use_container_width=True, key=f"ed_{stanza_selezionata}"
            )

            if st.button("💾 SALVA MODIFICHE"):
                conn.update(worksheet=stanza_selezionata, data=df_editabile)
                st.success("Sincronizzato!")
                time.sleep(1)
                st.rerun()
        else:
            st.warning(f"La tab '{stanza_selezionata}' sembra vuota.")

    except Exception as e:
        st.error(f"Errore tecnico su '{stanza_selezionata}'")
        st.info("💡 PROVA FINALE: Su Google Sheets, rinomina 'camera' in 'Foglio1' e prova a caricarlo.")
