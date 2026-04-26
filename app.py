import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import time
import os
from fpdf import FPDF

# ==========================================================
# 1. CONFIGURATION, STYLE & PERSISTANCE (V50)
# ==========================================================
st.set_page_config(page_title="QualiH2 - Magnum Opus", layout="wide", page_icon="🛡️")
LOG_FILE = "industrial_master_log.csv"

def apply_ui_style(purity, threshold):
    """Alerte visuelle dynamique selon la conformité."""
    color = "#4b0000" if purity < threshold else "#0e1117"
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {color}; transition: 0.5s; }}
        .metric-card {{ background-color: #1c2128; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }}
        </style>
    """, unsafe_allow_html=True)

def log_data(purity, status, r, g, b):
    """Sauvegarde sécurisée sans caractères spéciaux pour éviter les erreurs de lecture."""
    clean_status = status.replace("✅", "").replace("🚨", "").replace("⚠️", "").strip()
    new_entry = pd.DataFrame([{
        "Horodatage": time.strftime("%Y-%m-%d %H:%M:%S"),
        "Purete_Pct": round(purity, 2),
        "Verdict": clean_status,
        "R": int(r), "V": int(g), "B": int(b)
    }])
    header = not os.path.exists(LOG_FILE)
    new_entry.to_csv(LOG_FILE, mode='a', index=False, header=header, encoding='utf-8')

# ==========================================================
# 2. GÉNÉRATEUR PDF PROFESSIONNEL (MULTI-CANAUX)
# ==========================================================
class MasterPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(0, 50, 150)
        self.cell(0, 10, 'CERTIFICAT D\'EXPERTISE QUALIH2', 0, 1, 'C')
        self.ln(5)

    def generate(self, purity, status, r, g, b, img_path=None):
        clean_status = status.replace("✅", "").replace("🚨", "").replace("⚠️", "").strip()
        self.add_page()
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f"Date d'Expertise : {time.strftime('%d/%m/%Y %H:%M:%S')}", 0, 1)
        
        if img_path and os.path.exists(img_path):
            self.ln(5)
            self.cell(0, 10, "Capture de la signature spectrale :", 0, 1)
            self.image(img_path, x=65, w=80)
            self.ln(10)

        self.set_fill_color(230, 230, 230)
        self.set_font('Arial', 'B', 14)
        self.cell(0, 12, f"VERDICT : {clean_status}", 1, 1, 'C', True)
        self.ln(5)
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f"Purete Mesuree : {purity:.2f}%", 0, 1)
        self.cell(0, 10, f"Details RVB : R={int(r)} | V={int(g)} | B={int(b)}", 0, 1)
        return self.output(dest='S').encode('latin-1', errors='replace')

# ==========================================================
# 3. MOTEUR D'ANALYSE SPECTRAL V50 (ROI + RATIO)
# ==========================================================
class HydrogenEngineV50:
    def analyze(self, frame, roi_coords=None):
        if roi_coords:
            x, y, w, h = roi_coords
            roi = frame[y:y+h, x:x+w]
        else:
            roi = frame

        B, G, R = cv2.split(roi)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 45, 255, cv2.THRESH_BINARY)
        
        if cv2.countNonZero(mask) < 150: return None
        
        mR, mG, mB = np.mean(R[mask>0]), np.mean(G[mask>0]), np.mean(B[mask>0])
        
        # Algorithme de Contamination Spectrale
        score_contamination = (mR + mG) / (2 * mB + 1)
        
        if score_contamination > 0.82 or mR > (mB * 0.90):
            purity, status = 0.0, "🚨 NON CONFORME : SODIUM / CALCIUM"
        elif mG > (mB * 1.02):
            purity, status = 0.0, "🚨 NON CONFORME : CUIVRE (VERT)"
        elif mB > (mR * 1.1):
            ratio = mB / (mR + mG + 1)
            purity = min(ratio * 295, 99.99)
            status = "✅ GAZ CONFORME : H2 PUR"
        else:
            purity, status = 15.0, "⚠️ SIGNAL INSTABLE / POLLUE"
            
        return {"purity": purity, "status": status, "r": mR, "g": mG, "b": mB}

# ==========================================================
# 4. INTERFACE UNIFIÉE "TOUTES OPTIONS"
# ==========================================================
def main():
    engine = HydrogenEngineV50()
    
    with st.sidebar:
        st.header("🛡️ QualiH2 - C.U.Maghnia")
        mode = st.radio("Mode d'Opération", ["Live Stream Video", "Analyse Photo HD"])
        threshold = st.slider("Seuil de Qualité (%)", 50, 99, 92)
        st.divider()
        st.subheader("🎯 Contrôle du Focus")
        rx = st.slider("Position X", 0, 640, 200)
        ry = st.slider("Position Y", 0, 480, 150)
        rs = st.slider("Taille Zone (ROI)", 50, 400, 180)
        if st.button("🗑️ Purger l'Historique"):
            if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
            st.rerun()

    tab1, tab2, tab3 = st.tabs(["🔍 Diagnostic Direct", "📈 Tendances & Stats", "📄 Rapports & PDF"])

    # --- ONGLET 1 : DIAGNOSTIC ---
    with tab1:
        if mode == "Live Stream Video":
            run_cam = st.toggle("ACTIVER LE CAPTEUR", key="active")
            v_place = st.image([], width="stretch")
            m_cols = st.columns(3)
            
            if run_cam:
                cap = cv2.VideoCapture(0)
                while st.session_state.active:
                    ret, frame = cap.read()
                    if not ret: break
                    
                    res = engine.analyze(frame, (rx, ry, rs, rs))
                    color_box = (0, 255, 0) if res and res['purity'] >= threshold else (255, 0, 0)
                    cv2.rectangle(frame, (rx, ry), (rx+rs, ry+rs), color_box, 3)
                    
                    v_place.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), width="stretch")
                    
                    if res:
                        apply_ui_style(res['purity'], threshold)
                        m_cols[0].metric("Sodium (R)", int(res['r']))
                        m_cols[1].metric("Cuivre (V)", int(res['g']))
                        m_cols[2].metric("Pureté H2", f"{res['purity']:.1f}%")
                        st.session_state['last_res'] = res
                        st.session_state['last_img'] = frame[ry:ry+rs, rx:rx+rs]
                        
                        if int(time.time()) % 10 == 0:
                            log_data(res['purity'], res['status'], res['r'], res['g'], res['b'])
                cap.release()
        else:
            up = st.file_uploader("Charger Preuve Visuelle", type=["jpg", "png", "jpeg"])
            if up:
                img_pil = Image.open(up).convert("RGB")
                frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
                res = engine.analyze(frame)
                if res:
                    apply_ui_style(res['purity'], threshold)
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.image(img_pil, width="stretch")
                        fig = go.Figure(go.Bar(x=['Soudium','Cuivre','H2'], y=[res['r'], res['g'], res['b']], 
                                             marker_color=['red','green','blue']))
                        fig.update_layout(template="plotly_dark", height=250)
                        st.plotly_chart(fig, width="stretch")
                    with c2:
                        st.metric("PURETÉ", f"{res['purity']:.2f}%")
                        st.subheader(res['status'])
                        st.session_state['last_res'] = res
                        st.session_state['last_img'] = np.array(img_pil)
                        log_data(res['purity'], res['status'], res['r'], res['g'], res['b'])

    # --- ONGLET 2 : STATISTIQUES ---
    with tab2:
        if os.path.exists(LOG_FILE):
            df = pd.read_csv(LOG_FILE)
            col_p = [c for c in df.columns if "Purete" in c][0]
            fig_trend = go.Figure(go.Scatter(x=df['Horodatage'], y=df[col_p], mode='lines+markers', line=dict(color='#00ff00')))
            fig_trend.add_hline(y=threshold, line_dash="dash", line_color="red", annotation_text="Limite Qualité")
            fig_trend.update_layout(title="Stabilité du Gaz sur le Temps", template="plotly_dark")
            st.plotly_chart(fig_trend, width="stretch")
            st.dataframe(df.sort_values(by="Horodatage", ascending=False), width="stretch")
        else:
            st.info("Aucune donnée enregistrée.")

    # --- ONGLET 3 : RAPPORTS ---
    with tab3:
        if 'last_res' in st.session_state:
            lr = st.session_state['last_res']
            st.write(f"Analyse prête pour : {lr['status']} ({lr['purity']:.2f}%)")
            if st.button("🛠️ Générer Certificat PDF"):
                temp_p = "last_snap.jpg"
                Image.fromarray(cv2.cvtColor(st.session_state['last_img'], cv2.COLOR_BGR2RGB)).save(temp_p)
                pdf_b = MasterPDF().generate(lr['purity'], lr['status'], lr['r'], lr['g'], lr['b'], temp_p)
                st.download_button("📥 Télécharger Rapport Officiel", pdf_b, "Certificat_QualiH2.pdf")
        else:
            st.warning("Effectuez une analyse pour activer cette section.")

if __name__ == "__main__":
    main()
