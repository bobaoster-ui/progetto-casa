import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURAZIONE PAGINA (Sempre per prima!)
st.set_page_config(page_title="Monitoraggio Arredamento Casa", layout="wide", page_icon="🏠")

st.title("🏠 Monitoraggio Spese Arredamento")

# 2. CONNESSIONE
conn = st.connection("gsheets", type=GSheetsConnection)

# Elenco stanze
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

# --- 3. SEZIONE RIEPILOGO GENERALE ---
st.markdown("### 📊 Riepilogo Spese Confermate (S)")
col_rip1, col_rip2, col_rip3 = st.columns(3)

totale_confermato = 0
totale_potenziale = 0
dati_riepilogo = []

try:
    for s in stanze:
        # Leggiamo ogni tab
        temp_df = conn.read(worksheet=s, ttl=0)
        if temp_df is not None and not temp_df.empty:
            # Pulizia nomi colonne
            temp_df.columns = [str(c).strip() for c in temp_df.columns]
            
            # Identifichiamo le colonne corrette
            # Cerchiamo 'Prezzo' o 'Costo' o 'Importo Totale' (dalla tua immagine vedo 'Importo Totale')
            col_prezzo = None
            for c in ['Importo Totale', 'Costo', 'Prezzo']:
                if c in temp_df.columns:
                    col_prezzo = c
                    break
            
            # Cerchiamo la colonna per il filtro S/N
            col_scelta = None
            for c in ['Acquista S/N', 'S/N', 'Acquistato']:
                if c in temp_df.columns:
                    col_scelta = c
                    break

            if col_prezzo:
                # Convertiamo in numeri
                temp_df[col_prezzo] = pd.to_numeric(temp_df[col_prezzo], errors='coerce').fillna(0)
                
                # Somma Potenziale
                somma_pot_stanza = temp_df[col_prezzo].sum()
                totale_potenziale += somma_pot_stanza
                
                # Somma Confermata (S)
                if col_scelta:
                    # Se nella tua immagine 'Acquistato' è un numero (1 o 0), o una S/N
                    temp_df[col_scelta] = temp_df[col_scelta].astype(str).str.strip().str.upper()
                    # Consideriamo confermato se c'è 'S' oppure se c'è '1'
                    spesa_conf_stanza = temp_df[(temp_df[col_scelta] == 'S') | (temp_df[col_scelta] == '1')][col_prezzo].sum()
                else:
                    spesa_conf_stanza = 0
                
                totale_confermato += spesa_conf_stanza
                
                dati_riepilogo.append({
                    "Stanza": s.capitalize(), 
                    "Confermato (S)": f"{spesa_conf_stanza:,.2f} €",
                    "Totale": f"{somma_pot_stanza:,.2f} €"
                })

    with col_rip1:
        st.metric(label="TOTALE CONFERMATO (S)", value=f"{totale_confermato:,.2f} €")
    
    with col_rip2:
        st.metric(label="TOTALE POTENZIALE (S+N)", value=f"{totale_potenziale:,.2f} €")

    with col_rip3:
        if dati_riepilogo:
            st.dataframe(pd.DataFrame(dati_riepilogo), hide_index=True, use_container_width=True)

except Exception as e:
    st.info("Configurazione riepilogo in corso... assicurati che le colonne siano uniformi.")

st.divider()

# --- 4. SEZIONE DETTAGLIO STANZA ---
selezione = st.sidebar.selectbox("Vai alla stanza specifica:", stanze)
st.subheader(f"Dettaglio: {selezione.capitalize()}")

try:
    df = conn.read(worksheet=selezione, ttl=0)
    if df is not None:
        # Editor per modificare i dati
        df_edit = st.data_editor(df, use_container_width=True, hide_index=True, key=f"ed_{selezione}", num_rows="dynamic")
        
        if st.button(f"💾 SALVA MODIFICHE {selezione.upper()}"):
            conn.update(worksheet=selezione, data=df_edit)
            st.success("Dati salvati!")
            st.balloons()
            st.rerun()
except Exception as e:
    st.error("Errore nel caricamento della stanza.")
