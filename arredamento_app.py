import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configurazione Pagina
st.set_page_config(page_title="Monitoraggio Arredamento Casa", layout="wide", page_icon="🏠")

st.title("🏠 Monitoraggio Spese Arredamento")

# Connessione sicura
conn = st.connection("gsheets", type=GSheetsConnection)

# Elenco stanze
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

# --- SEZIONE RIEPILOGO GENERALE ---
st.markdown("### 📊 Riepilogo Spese Confermate (S)")
col_rip1, col_rip2, col_rip3 = st.columns(3)

totale_confermato = 0
totale_potenziale = 0
dati_riepilogo = []

try:
    for s in stanze:
        temp_df = conn.read(worksheet=s, ttl=600)
        if 'Prezzo' in temp_df.columns:
            # Pulizia dati
            temp_df['Prezzo'] = pd.to_numeric(temp_df['Prezzo'], errors='coerce').fillna(0)
            
            # Calcolo Potenziale (Tutto)
            totale_potenziale += temp_df['Prezzo'].sum()
            
            # Calcolo Confermato (Solo righe con 'S')
            # Assumiamo che la colonna si chiami 'S/N'. Se si chiama diversamente, cambiala qui sotto
            colonna_filtro = 'S/N' if 'S/N' in temp_df.columns else temp_df.columns[2] # Prende la terza colonna se non trova 'S/N'
            
            spesa_confermata_stanza = temp_df[temp_df[colonna_filtro].str.upper() == 'S']['Prezzo'].sum()
            totale_confermato += spesa_confermata_stanza
            
            dati_riepilogo.append({
                "Stanza": s.capitalize(), 
                "Confermato (S)": f"{spesa_confermata_stanza:,.2f} €"
            })

    with col_rip1:
        st.metric(label="TOTALE CONFERMATO (S)", value=f"{totale_confermato:,.2f} €")
    
    with col_rip2:
        st.metric(label="TOTALE POTENZIALE (S+N)", value=f"{totale_potenziale:,.2f} €", delta=f"{totale_potenziale - totale_confermato:,.2f} € da decidere", delta_color="inverse")

    with col_rip3:
        df_sommario = pd.DataFrame(dati_riepilogo)
        st.dataframe(df_sommario, hide_index=True, use_container_width=True)

except Exception as e:
    st.info("Configurazione riepilogo in corso...")

st.divider()

# --- SEZIONE DETTAGLIO STANZA ---
selezione = st.sidebar.selectbox("Vai alla stanza specifica:", stanze)
st.subheader(f"Dettaglio: {selezione.capitalize()}")

try:
    df = conn.read(worksheet=selezione, ttl=0)
    
    if df is not None:
        df.columns = [str(c).strip() for c in df.columns]
        
        # Editor dati
        df_edit = st.data_editor(
            df, 
            use_container_width=True, 
            hide_index=True, 
            key=f"editor_{selezione}",
            num_rows="dynamic"
        )

        # Tasto Salva
        if st.button(f"💾 SALVA MODIFICHE {selezione.upper()}"):
            with st.spinner("Sincronizzazione con Google Sheets..."):
                conn.update(worksheet=selezione, data=df_edit)
                st.success("Dati salvati!")
                st.balloons()
                st.rerun()

except Exception as e:
    st.error("Errore nel caricamento dei dettagli.")
