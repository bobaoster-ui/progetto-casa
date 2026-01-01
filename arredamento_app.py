# --- SEZIONE RIEPILOGO GENERALE ---
st.markdown("### 📊 Riepilogo Spese Confermate (S)")
col_rip1, col_rip2, col_rip3 = st.columns(3)

totale_confermato = 0
totale_potenziale = 0
dati_riepilogo = []

try:
    for s in stanze:
        temp_df = conn.read(worksheet=s, ttl=0) 
        if not temp_df.empty:
            # 1. Pulizia Nomi Colonne
            temp_df.columns = [str(c).strip() for c in temp_df.columns]
            
            # 2. Pulizia Prezzi
            if 'Prezzo' in temp_df.columns:
                temp_df['Prezzo'] = pd.to_numeric(temp_df['Prezzo'], errors='coerce').fillna(0)
                somma_potenziale = temp_df['Prezzo'].sum()
                totale_potenziale += somma_potenziale
                
                # 3. Calcolo Confermato (Cerca la colonna "Acquista S/N")
                # Cerchiamo la colonna esatta o una che contenga "Acquista"
                col_target = None
                if 'Acquista S/N' in temp_df.columns:
                    col_target = 'Acquista S/N'
                else:
                    # Cerca se esiste una colonna che contiene la parola "Acquista"
                    for c in temp_df.columns:
                        if 'Acquista' in c:
                            col_target = c
                            break
                
                if col_target:
                    # Puliamo il contenuto (S o N)
                    temp_df[col_target] = temp_df[col_target].astype(str).str.strip().str.upper()
                    spesa_confermata_stanza = temp_df[temp_df[col_target] == 'S']['Prezzo'].sum()
                else:
                    spesa_confermata_stanza = 0
                
                totale_confermato += spesa_confermata_stanza
                
                dati_riepilogo.append({
                    "Stanza": s.capitalize(), 
                    "Confermato (S)": f"{spesa_confermata_stanza:,.2f} €",
                    "Totale": f"{somma_potenziale:,.2f} €"
                })

    with col_rip1:
        st.metric(label="TOTALE CONFERMATO (S)", value=f"{totale_confermato:,.2f} €")
    
    with col_rip2:
        st.metric(label="TOTALE POTENZIALE (S+N)", value=f"{totale_potenziale:,.2f} €")

    with col_rip3:
        if dati_riepilogo:
            df_sommario = pd.DataFrame(dati_riepilogo)
            st.dataframe(df_sommario, hide_index=True, use_container_width=True)

except Exception as e:
    st.error(f"Errore nel calcolo del riepilogo: {e}")
