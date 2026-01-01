import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import time
import os
import signal

# Configurazione Pagina
st.set_page_config(page_title="Home Decor Cloud v9.3", page_icon="🏠", layout="wide")

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def pulisci_df(df):
    """Pulisce e converte i dati dal foglio Google"""
    # Rimuove spazi bianchi dai nomi delle colonne
    df.columns = [str(c).strip() for c in df.columns]

    if 'Note' not in df.columns: df['Note'] = ""
    if 'Acquista S/N' not in df.columns: df['Acquista S/N'] = "N"

    # Conversione numeri (gestisce virgole e formati da Sheets)
    for col in ['Acquistato', 'Costo', 'Importo Totale']:
        if col in df.columns:
            # Sostituisce la virgola con il punto per i decimali se necessario
            if df[col].dtype == object:
                df[col] = df[col].str.replace('€', '').str.replace('.', '').str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Importo Totale'] = df['Acquistato'] * df['Costo']
    return df

# --- INTERFACCIA ---
st.title("🏠 Monitoraggio Casa Cloud")

# Lista stanze corrispondente alle Tab di Google Sheets
nomi_stanze = [
    "Camera da Letto",
    "Tavolo e Sedie",
    "Salotto",
    "Cucina",
    "Attività Muratore, Idraulico et"
]

st.sidebar.header("📍 Navigazione")
opzioni_menu = ["📊 Riepilogo Casa"] + nomi_stanze
selezione = st.sidebar.selectbox("Vai a:", opzioni_menu)

st.sidebar.write("---")
with st.sidebar.expander("🛠️ Impostazioni Avanzate"):
    abilita_chiusura = st.checkbox("Abilita tasto spegnimento")
    if abilita_chiusura:
        if st.button("🛑 CHIUDI APPLICAZIONE", use_container_width=True, type="primary"):
            os.kill(os.getpid(), signal.SIGINT)

# --- LOGICA PAGINE ---


# --- LOGICA PAGINE MODIFICATA ---

if selezione == "📊 Riepilogo Casa":
    st.subheader("Riepilogo Spese Totale")
    riassunto = []

    for stanza in nomi_stanze:
        try:
            # Forziamo la lettura ignorando la cache
            df = conn.read(worksheet=stanza, ttl=0)
            if df is not None:
                df = pulisci_df(df)
                # Calcoliamo i totali per il grafico
                tot = df['Importo Totale'].sum()
                mask = df['Acquista S/N'].astype(str).str.upper().str.strip() == 'S'
                speso = df[mask]['Importo Totale'].sum()
                riassunto.append({"Stanza": stanza, "Budget": tot, "Speso": speso})
        except Exception:
            continue # Salta silenziosamente se una tab non viene trovata

    with st.spinner("Sincronizzazione Cloud in corso..."):
        for stanza in nomi_stanze:
            try:
                # Lettura con ttl=0 per forzare l'aggiornamento
                df = conn.read(worksheet=stanza)
                if df is not None and not df.empty:
                    df = pulisci_df(df)
                    tot = df['Importo Totale'].sum()
                    mask = df['Acquista S/N'].str.upper().str.strip() == 'S'
                    speso = df[mask]['Importo Totale'].sum()
                    riassunto.append({"Stanza": stanza, "Budget": tot, "Speso": speso, "Mancante": tot-speso})
            except Exception:
                continue

    if riassunto:
        df_riepilogo = pd.DataFrame(riassunto)
        c1, c2, c3 = st.columns(3)
        c1.metric("BUDGET TOTALE", f"€ {df_riepilogo['Budget'].sum():,.2f}")
        c2.metric("TOTALE SPESO", f"€ {df_riepilogo['Speso'].sum():,.2f}",
                  delta=f"€ {df_riepilogo['Mancante'].sum():,.2f} residui", delta_color="inverse")

        st.plotly_chart(px.bar(df_riepilogo, x="Stanza", y=["Speso", "Mancante"], barmode="stack",
                               color_discrete_map={"Speso": "#2ecc71", "Mancante": "#e74c3c"}), use_container_width=True)
    else:
        st.warning("In attesa di dati... Verifica la connessione nei Secrets.")

else:
    stanza_selezionata = selezione
    st.subheader(f"Gestione: {stanza_selezionata}")

    try:
        # Lettura stanza specifica con ttl=0
        df_origine = conn.read(worksheet=stanza_selezionata)
        df_origine = pulisci_df(df_origine)

        # Metriche di riepilogo stanza
        tot_st = df_origine['Importo Totale'].sum()
        mask_s = df_origine['Acquista S/N'].str.upper().str.strip() == 'S'
        speso_st = df_origine[mask_s]['Importo Totale'].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Budget Previsto", f"€ {tot_st:,.2f}")
        m2.metric("Spesa Effettuata", f"€ {speso_st:,.2f}")
        m3.metric("Residuo", f"€ {tot_st - speso_st:,.2f}")

        # Editor dati
        df_editabile = st.data_editor(
            df_origine,
            column_config={
                "Acquista S/N": st.column_config.SelectboxColumn("S/N", options=["S", "N"]),
                "Costo": st.column_config.NumberColumn("Costo (€)", format="€ %.2f"),
                "Importo Totale": st.column_config.NumberColumn("Totale (€)", format="€ %.2f", disabled=True),
            },
            disabled=["Articolo", "Importo Totale"],
            hide_index=True, use_container_width=True, key=f"editor_{stanza_selezionata}"
        )

        if st.button("💾 SALVA MODIFICHE", use_container_width=True, type="primary"):
            df_editabile['Importo Totale'] = df_editabile['Acquistato'] * df_editabile['Costo']
            conn.update(worksheet=stanza_selezionata, data=df_editabile)
            st.success("Dati sincronizzati con Google Sheets!")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Tab '{stanza_selezionata}' non trovata o errore di connessione.")
        st.info("Verifica che il nome della Tab su Google Sheets sia identico e che l'URL nei Secrets sia corretto.")
