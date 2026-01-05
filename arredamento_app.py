import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V30.1", layout="wide", page_icon="💎")

# Connessione Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_connection()

# --- STILE ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
grad = "linear-gradient(90deg, #0f2027, #203a43, #2c5364)" if st.session_state.dark_mode else "linear-gradient(90deg, #2e5a88, #4a90e2)"
st.markdown(f"""<style>
    .stApp {{background-color: {bc}; color: {tc};}}
    .main-header {{background: {grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px;}}
    .metric-card {{background-color: {cc}; padding: 15px; border-radius: 10px; border-bottom: 4px solid #2e5a88; text-align: center; color: {tc}; margin-bottom: 10px;}}
    .metric-value {{font-size: 1.8em; font-weight: 800; color: #2e5a88;}}
    .gold-seal {{background: linear-gradient(145deg, #ffdf00, #d4af37); padding: 20px; border-radius: 15px; text-align: center; color: black; font-weight: bold; border: 2px solid #b8860b; margin-bottom: 20px;}}
</style>""", unsafe_allow_html=True)

if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]: st.session_state.password_correct = True; st.rerun()
else:
    # Stanze fisse
    stanze_fisiche = ["Camera", "Cucina", "Salotto", "Tavolo", "Lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s}" for s in stanze_fisiche])
        st.markdown("<br>---<br>✨ **Roberto & Gemini**<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    # Lettura dati dal DB (Singola chiamata veloce per tutto)
    response = supabase.table("arredamento").select("*").execute()
    df_all = pd.DataFrame(response.data)
    if not df_all.empty:
        df_all['scadenza'] = pd.to_datetime(df_all['scadenza'], errors='coerce')

    if "Riepilogo" in sel:
        st.markdown('<div class="main-header"><h1>Command Center</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        # Escludiamo la wishlist dai calcoli finanziari del Riepilogo
        df_real = df_all[df_all['stanza'].isin(stanze_fisiche)] if not df_all.empty else pd.DataFrame()

        if not df_real.empty:
            conf = df_real['importo_totale'].sum()
            pag = df_real['versato'].sum()

            m1, m2, m3 = st.columns(3)
            m1.markdown(f'<div class="metric-card">CONFERMATO<div class="metric-value">{conf:,.0f}€</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{pag:,.0f}€</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card">DA PAGARE<div class="metric-value">{conf-pag:,.0f}€</div></div>', unsafe_allow_html=True)

            c1, c2 = st.columns([1, 1.2])
            with c1:
                st.plotly_chart(px.pie(df_real, values='importo_totale', names='stanza', hole=0.5), use_container_width=True)
            with c2:
                st.subheader("🗓️ Scadenzario")
                sc = df_real[df_real['scadenza'].notna() & (df_real['versato'] < df_real['importo_totale'])].copy()
                if not sc.empty:
                    sc['gg'] = (sc['scadenza'] - pd.Timestamp(datetime.now().date())).dt.days
                    sc['Stato'] = sc['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                    st.dataframe(sc.sort_values('gg')[['stanza','articolo','scadenza','Stato']], use_container_width=True, hide_index=True)
        else:
            st.info("Nessun dato presente nel database. Inizia a popolare le stanze!")

    elif "Wishlist" in sel:
        st.title("✨ Wishlist dei Desideri")
        df_w = df_all[df_all['stanza'] == "Wishlist"].copy() if not df_all.empty else pd.DataFrame(columns=['articolo', 'importo_totale', 'nota', 'link_fattura'])

        with st.form("f_wish"):
            w_cfg = {
                "link_fattura": st.column_config.LinkColumn("🔗 Link Sito", display_text="Apri"),
                "nota": st.column_config.TextColumn("Note/Foto Link"),
                "importo_totale": st.column_config.NumberColumn("Prezzo Stimato", format="%.2f €")
            }
            # Editor dinamico per aggiungere/rimuovere desideri
            df_ew = st.data_editor(df_w[['articolo', 'importo_totale', 'nota', 'link_fattura']] if not df_w.empty else df_w,
                                  use_container_width=True, hide_index=True, num_rows="dynamic", column_config=w_cfg)

            if st.form_submit_button("✨ SALVA WISHLIST"):
                # Pulizia e sovrascrittura per la gestione semplificata dei desideri
                supabase.table("arredamento").delete().eq("stanza", "Wishlist").execute()
                for _, row in df_ew.iterrows():
                    if row['articolo']: # Salva solo se c'è un nome articolo
                        new_item = {
                            "stanza": "Wishlist",
                            "articolo": str(row['articolo']),
                            "importo_totale": float(row.get('importo_totale', 0) or 0),
                            "nota": str(row.get('nota', '')),
                            "link_fattura": str(row.get('link_fattura', '')),
                            "stanza_chiusa": False
                        }
                        supabase.table("arredamento").insert(new_item).execute()
                st.balloons(); st.success("Wishlist aggiornata!"); time.sleep(1); st.rerun()

    elif "📦" in sel:
        sn = sel.replace("📦 ", "")
        st.title(f"🏠 {sn}")
        df_s = df_all[df_all['stanza'] == sn].copy() if not df_all.empty else pd.DataFrame()

        is_closed = df_s['stanza_chiusa'].any() if not df_s.empty else False
        if is_closed:
            st.markdown(f'<div class="gold-seal">🏆 COMPLIMENTI! La stanza {sn} è completata!</div>', unsafe_allow_html=True)

        with st.form(f"f_{sn}"):
            check_chiusura = st.checkbox("🔒 Chiudi Stanza (Sigillo Oro)", value=is_closed)
            # Editor per i dati della stanza
            cols_to_show = ['articolo', 'acquistato', 'prezzo_pieno', 'sconto_percentuale', 'costo', 'importo_totale', 'versato', 'stato_pagamento', 'scadenza', 'nota']
            df_e = st.data_editor(df_s[cols_to_show], use_container_width=True, hide_index=True)

            if st.form_submit_button("💾 SALVA TUTTO"):
                for _, row in df_e.iterrows():
                    # Ricalcolo logica costi
                    p_pieno = float(row['prezzo_pieno'] or 0)
                    sconto = float(row['sconto_percentuale'] or 0)
                    qta = float(row['acquistato'] or 1)

                    c_unitario = p_pieno * (1 - (sconto/100)) if p_pieno > 0 else float(row['costo'] or 0)
                    i_tot = c_unitario * qta

                    update_data = {
                        "prezzo_pieno": p_pieno,
                        "sconto_percentuale": sconto,
                        "acquistato": qta,
                        "costo": c_unitario,
                        "importo_totale": i_tot,
                        "versato": float(row['versato'] or 0),
                        "nota": str(row['nota'] or ''),
                        "stato_pagamento": str(row['stato_pagamento'] or ''),
                        "scadenza": str(row['scadenza']) if pd.notnull(row['scadenza']) else None,
                        "stanza_chiusa": check_chiusura
                    }
                    # Aggiorna il record specifico tramite stanza + articolo
                    supabase.table("arredamento").update(update_data).eq("stanza", sn).eq("articolo", row['articolo']).execute()

                st.balloons(); st.success("Salvataggio istantaneo completato!"); time.sleep(1); st.rerun()
