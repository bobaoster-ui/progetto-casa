import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
import signal

st.set_page_config(page_title="Home Decor Master v8.2", page_icon="🏠", layout="wide")

# --- FUNZIONE CARICAMENTO DATI ---
def carica_dati(file):
    if os.path.exists(file):
        dict_fogli = pd.read_excel(file, sheet_name=None)
        fogli_finali = {}
        for nome_f, df in dict_fogli.items():
            df.columns = [str(c).strip() for c in df.columns]
            if 'Note' not in df.columns: df['Note'] = ""
            else: df['Note'] = df['Note'].astype(str).replace('nan', '')
            if 'Acquista S/N' not in df.columns: df['Acquista S/N'] = "N"
            else: df['Acquista S/N'] = df['Acquista S/N'].astype(str).str.upper().str.strip()

            for col in ['Acquistato', 'Costo', 'Importo Totale']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            df['Importo Totale'] = df['Acquistato'] * df['Costo']
            fogli_finali[nome_f] = df
        return fogli_finali
    return None

FILE_EXCEL = "Arredamenti.xlsx"
fogli = carica_dati(FILE_EXCEL)

if fogli:
    nomi_stanze = list(fogli.keys())
    opzioni_menu = ["🏠 HOME - Riepilogo Casa"] + nomi_stanze

    # --- SIDEBAR ---
    st.sidebar.header("📍 Navigazione")
    selezione = st.sidebar.selectbox("Vai a:", opzioni_menu)

    st.sidebar.write("---")

    # --- TRUCCO PER IL TASTO CHIUDI ---
    # Usiamo un expander o una checkbox per "proteggere" il tasto
    with st.sidebar.expander("🛠️ Impostazioni Avanzate"):
        abilita_chiusura = st.checkbox("Abilita tasto spegnimento")
        if abilita_chiusura:
            if st.button("🛑 CHIUDI APPLICAZIONE", use_container_width=True, type="primary"):
                st.warning("Sessione terminata. Se sei sul Cloud, dovrai fare il REBOOT dal dashboard.")
                time.sleep(2)
                os.kill(os.getpid(), signal.SIGINT)

    # --- LOGICA PAGINE (HOME / STANZE) ---
    if selezione == "🏠 HOME - Riepilogo Casa":
        st.title("📊 Riepilogo Spese Tutta Casa")
        riassunto = []
        for nome, df in fogli.items():
            tot = df['Importo Totale'].sum()
            mask = df['Acquista S/N'].astype(str).str.upper().str.strip() == 'S'
            speso = df[mask]['Importo Totale'].sum()
            riassunto.append({"Stanza": nome, "Budget": tot, "Speso": speso, "Mancante": tot-speso})

        df_riepilogo = pd.DataFrame(riassunto)
        c1, c2, c3 = st.columns(3)
        c1.metric("BUDGET TOTALE", f"€ {df_riepilogo['Budget'].sum():,.2f}")
        c2.metric("TOTALE SPESO", f"€ {df_riepilogo['Speso'].sum():,.2f}",
                  delta=f"€ {df_riepilogo['Mancante'].sum():,.2f} residui", delta_color="inverse")
        c3.metric("STANZE", len(nomi_stanze))

        st.plotly_chart(px.bar(df_riepilogo, x="Stanza", y=["Speso", "Mancante"], barmode="stack",
                               color_discrete_map={"Speso": "#2ecc71", "Mancante": "#e74c3c"}), use_container_width=True)

    else:
        stanza_selezionata = selezione
        df_origine = fogli[stanza_selezionata].copy()
        st.title(f"🏠 Stanza: {stanza_selezionata}")

        # Totali Stanza sempre visibili
        tot_st = df_origine['Importo Totale'].sum()
        mask_s = df_origine['Acquista S/N'].str.upper().str.strip() == 'S'
        speso_st = df_origine[mask_s]['Importo Totale'].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric(f"Totale {stanza_selezionata}", f"€ {tot_st:,.2f}")
        m2.metric("Acquistato", f"€ {speso_st:,.2f}")
        m3.metric("Da spendere", f"€ {tot_st - speso_st:,.2f}")
        st.write("---")

        tab_lista, tab_grafici = st.tabs(["📋 Lista e Modifica", "📊 Grafici"])

        with tab_lista:
            with st.expander("➕ Aggiungi nuovo articolo"):
                new_art = st.text_input("Nome nuovo articolo")
                if st.button("Inserisci"):
                    if new_art:
                        nuova_riga = pd.DataFrame([{"Articolo": new_art, "Acquistato": 1, "Costo": 0, "Importo Totale": 0, "Acquista S/N": "N", "Note": ""}])
                        df_nuovo = pd.concat([df_origine, nuova_riga], ignore_index=True)
                        with pd.ExcelWriter(FILE_EXCEL, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
                            df_nuovo.to_excel(writer, sheet_name=stanza_selezionata, index=False)
                        st.rerun()

            df_editabile = st.data_editor(
                df_origine,
                column_config={
                    "Acquista S/N": st.column_config.SelectboxColumn("S/N", options=["S", "N"]),
                    "Costo": st.column_config.NumberColumn("Costo (€)", format="€ %.2f"),
                    "Importo Totale": st.column_config.NumberColumn("Totale (€)", format="€ %.2f", disabled=True),
                    "Note": st.column_config.TextColumn("Note")
                },
                disabled=["Articolo", "Importo Totale"],
                hide_index=True, use_container_width=True, key=f"v82_{stanza_selezionata}"
            )

            if st.button("💾 SALVA MODIFICHE", use_container_width=True):
                df_editabile['Importo Totale'] = df_editabile['Acquistato'] * df_editabile['Costo']
                with pd.ExcelWriter(FILE_EXCEL, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
                    df_editabile.to_excel(writer, sheet_name=stanza_selezionata, index=False)
                st.success("Dati salvati con successo!")
                time.sleep(1)
                st.rerun()

        with tab_grafici:
            st.plotly_chart(px.pie(df_editabile, values='Importo Totale', names='Articolo', hole=0.4), use_container_width=True)

else:
    st.error("File Arredamenti.xlsx non trovato.")
