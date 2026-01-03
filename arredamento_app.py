import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V7.1", layout="wide", page_icon="🏠")

# Palette Colori
COLOR_PALETTE = ["#2E75B6", "#FFD700", "#1F4E78", "#F4B400", "#4472C4"]

# --- CLASSE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 11)
        testo_header = f'Proprietà: Jacopo - {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo_header.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

# --- FUNZIONE PULIZIA DATI ---
def safe_clean_df(df):
    if df is None: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    num_cols = ['Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo', 'Versato', 'Importo Totale']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    for col in df.columns:
        if col not in num_cols:
            df[col] = df[col].astype(str).replace(['nan', 'None', '<NA>'], '')
    return df

# --- LOGIN ---
if "password_correct" not in st.session_state:
    st.title("🔒 Accesso Riservato")
    u = st.text_input("Utente")
    p = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Credenziali errate")
else:
    # FORZIAMO IL REFRESH DELLA CONNESSIONE
    conn = st.connection("gsheets", type=GSheetsConnection)

    with st.sidebar:
        st.markdown("### 🛠 Sicurezza")
        can_edit_structure = st.toggle("Modifica Struttura", value=False)
        st.divider()
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]
    selezione = st.sidebar.selectbox("Menu Principale:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)

    # --- 1. RIEPILOGO GENERALE ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")
        try:
            df_imp = conn.read(worksheet="impostazioni", ttl=0)
            budget_max = float(df_imp[df_imp['Parametro'] == 'Budget Totale']['Valore'].values[0])
        except: budget_max = 10000.0

        lista_dettaglio = []
        tot_conf, tot_versato = 0.0, 0.0
        dati_per_grafico = []

        for s in stanze_reali:
            try:
                df_s = conn.read(worksheet=s, ttl=0)
                if df_s is not None and not df_s.empty:
                    df_s = safe_clean_df(df_s)
                    col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df_s.columns), 'Acquista S/N')
                    imp_stanza = df_s['Importo Totale'].sum()
                    if imp_stanza > 0: dati_per_grafico.append({"Stanza": s.capitalize(), "Budget": imp_stanza})
                    conf_mask = df_s[col_s].astype(str).str.upper() == 'S'
                    df_c = df_s[conf_mask].copy()
                    if not df_c.empty:
                        tot_conf += df_c['Importo Totale'].sum()
                        tot_versato += df_c['Versato'].sum()
                        col_o = next((c for c in ['Oggetto', 'Articolo'] if c in df_c.columns), df_c.columns[0])
                        temp_df = pd.DataFrame({
                            'Ambiente': s.capitalize(), 'Oggetto': df_c[col_o],
                            'Importo Totale': df_c['Importo Totale'], 'Versato': df_c['Versato'],
                            'Stato': df_c['Stato Pagamento'] if 'Stato Pagamento' in df_c.columns else "-"
                        })
                        lista_dettaglio.append(temp_df)
            except: continue

        # (Grafici e Metriche rimangono invariati rispetto alla 7.0)
        st.subheader(f"📊 Budget Totale: {budget_max:,.2f} €")
        # ... [Visualizzazione Dashboard] ...

    # --- 2. STANZE (LA "CURA" PER IL DOPPIO SALVATAGGIO) ---
    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")

        # Leggiamo senza cache
        df_raw = conn.read(worksheet=selezione, ttl=0)
        df = safe_clean_df(df_raw)

        config = {
            "Acquista S/N": st.column_config.SelectboxColumn("Scelta", options=["S", "N"]),
            "Stato Pagamento": st.column_config.SelectboxColumn("Stato", options=["Da Pagare", "Acconto", "Saldato"]),
            "Importo Totale": st.column_config.NumberColumn("Totale €", format="%.2f", disabled=True)
        }

        # Usiamo un FORM per separare l'editing dal salvataggio
        with st.form(key=f"form_{selezione}"):
            df_edit = st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic" if can_edit_structure else "fixed",
                column_config=config
            )

            submit_button = st.form_submit_button(label="💾 SALVA E CALCOLA TUTTO")

        if submit_button:
            with st.spinner("Forzatura ricalcolo e scrittura..."):
                # Operiamo su una copia per essere certi dei tipi dato
                for i in range(len(df_edit)):
                    try:
                        p_pieno = float(df_edit.at[i, 'Prezzo Pieno'])
                        sconto = float(df_edit.at[i, 'Sconto %'])
                        qta = float(df_edit.at[i, 'Acquistato'])

                        # CALCOLO COSTO
                        if p_pieno > 0:
                            costo_unitario = p_pieno * (1 - (sconto / 100))
                            df_edit.at[i, 'Costo'] = costo_unitario
                        else:
                            costo_unitario = float(df_edit.at[i, 'Costo'])

                        # CALCOLO TOTALE RIGOROSO
                        df_edit.at[i, 'Importo Totale'] = costo_unitario * qta

                        # AUTOMAZIONE SALDATO
                        if str(df_edit.at[i, 'Stato Pagamento']) == "Saldato":
                            df_edit.at[i, 'Versato'] = df_edit.at[i, 'Importo Totale']
                    except:
                        continue

                # Scrittura e svuotamento cache
                conn.update(worksheet=selezione, data=df_edit)
                st.cache_data.clear() # Svuota la memoria per forzare la rilettura
                st.success("Dati sincronizzati!")
                time.sleep(0.5)
                st.rerun()

    # --- 3. WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        df_wish = conn.read(worksheet="desideri", ttl=0)
        if df_wish is not None:
            df_wish = safe_clean_df(df_wish)
            df_edit_w = st.data_editor(df_wish, use_container_width=True, hide_index=True,
                                       num_rows="dynamic" if can_edit_structure else "fixed")
            if st.button("💾 SALVA WISHLIST"):
                conn.update(worksheet="desideri", data=df_edit_w)
                st.rerun()
