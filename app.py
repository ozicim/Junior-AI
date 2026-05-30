import streamlit as st
import firebase_admin
from firebase_admin import firestore
import random
import smtplib
from email.mime.text import MIMEText
import os
import urllib.request
import json
import datetime
import google.generativeai as genai
from fpdf import FPDF
import gc
import requests
from streamlit_lottie import st_lottie

@st.cache_data
def lottie_yukle(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# Engine'ler
from akademik_engine import AkademikEngine
from mevzuat_engine import MevzuatBulutEngine, YASAL_UYARI
from dilekce_engine import DilekceEngine
from akademik_sinav_modu import AkademikSinavEngine
from ictihat_engine import IctihatEngine
from chat_engine import ChatEngine
from ag_engine import AgEngine
from hesap_engine import HesapEngine



# ==========================================
# ⚙️ AYARLAR VE BELLEK YÖNETİMİ
# ==========================================
st.set_page_config(layout="wide", page_title="JUNILEX AI")

@st.cache_resource
def get_db():
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    return firestore.client()

# ==========================================
# 🎨 CSS VE TASARIM (PREMIUM SAAS)
# ==========================================
if st.session_state.get("aktif_ekran", "🏠 Ana Ekran") == "🏠 Ana Ekran":
    st.markdown("""<style>[data-testid="stSidebar"] { display: none; }</style>""", unsafe_allow_html=True)

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
        
        /* Buton Hover ve Soft Shadow Efektleri */
        button[kind="secondary"] { transition: all 0.3s ease !important; border-radius: 8px !important; }
        button[kind="secondary"]:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important; border-color: #C5A059 !important; color: #C5A059 !important; }
        
        button[kind="primary"] { transition: all 0.3s ease !important; border-radius: 8px !important; background-color: #1A1A1A !important; }
        button[kind="primary"]:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(26,26,26,0.3) !important; background-color: #C5A059 !important; border-color: #C5A059 !important; color: white !important; }

        /* Konteyner (Kutu) Tasarımları */
        [data-testid="stVerticalBlockBorderWrapper"] { border-radius: 12px !important; box-shadow: 0 4px 16px rgba(0,0,0,0.04) !important; border: 1px solid rgba(0,0,0,0.05) !important; transition: all 0.3s ease; background-color: #ffffff; }
        [data-testid="stVerticalBlockBorderWrapper"]:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.08) !important; }
        
        /* Expander Tasarımı */
        [data-testid="stExpander"] { border-radius: 12px !important; border: 1px solid rgba(0,0,0,0.05) !important; box-shadow: 0 2px 8px rgba(0,0,0,0.02) !important; }

        /* Input Alanları */
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] { border-radius: 8px !important; border: 1px solid #e2e8f0 !important; transition: all 0.2s ease; }
        .stTextInput input:focus, .stTextArea textarea:focus { border-color: #C5A059 !important; box-shadow: 0 0 0 1px #C5A059 !important; }

        /* Üst Başlıklar */
        .header-container { text-align: center; padding: 20px 0; }
        .header-logo-svg { width: 90px; height: auto; margin: 0 auto 10px auto; display: block; transition: transform 0.5s ease; }
        .header-logo-svg:hover { transform: scale(1.05); }
        .main-title { font-size: 48px; font-weight: 800; color: #1A1A1A; letter-spacing: 5px; margin: 0; text-transform: uppercase; }
        .sub-title { color: #C5A059; font-weight: 600; letter-spacing: 3px; font-size: 13px; text-align: center; margin-bottom: 20px; }
        
        /* İçerik Kutuları */
        .madde-kutusu { background-color: #121212 !important; color: #FFFFFF !important; padding: 30px; border-radius: 12px; border: 1px solid #333; box-shadow: 0 10px 30px rgba(0,0,0,0.2); margin: 20px 0; line-height: 1.8; }
        .madde-baslik { color: #C5A059 !important; font-weight: 700; font-size: 20px; border-bottom: 1px solid #333; padding-bottom: 15px; margin-bottom: 15px; text-align: left; }
        .madde-icerik p { margin-bottom: 10px; color: #e2e8f0 !important; font-size: 15px; }
        .hoca-anlatim-kutusu { background-color: #faf8f5; padding: 25px; border-radius: 12px; border-left: 6px solid #C5A059; color: #2d3748; line-height: 1.7; box-shadow: 0 4px 15px rgba(0,0,0,0.03); margin-top: 20px; font-size: 15px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 API VE MOTORLAR
# ==========================================
MY_API_KEY = st.secrets["GEMINI_API_KEY"]
SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
DB_DOSYASI = "kullanicilar.json"

def veritabani_yukle():
    baslangic_verisi = {"ozan@junilex.com": {"sifre": "123456", "isim": "Ozan Şahin Sicim", "id": "#00001", "arkadaslar": [], "gelen_istekler": []}}
    
    if not os.path.exists(DB_DOSYASI):
        with open(DB_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(baslangic_verisi, f, ensure_ascii=False, indent=4)
        return baslangic_verisi
        
    try:
        with open(DB_DOSYASI, "r", encoding="utf-8") as f:
            db = json.load(f)
    except json.JSONDecodeError:
        # HATA YAKALANDI: Dosya var ama içi boş/bozuk. Dosyayı sıfırlıyoruz.
        with open(DB_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(baslangic_verisi, f, ensure_ascii=False, indent=4)
        return baslangic_verisi
        
    # YAMA: Eski kullanıcıların veritabanına otomatik ID ve arkadaş listesi ekler
    degisiklik = False
    for mail, data in db.items():
        if "id" not in data:
            data["id"] = "#" + str(random.randint(10000, 99999))
            degisiklik = True
        if "arkadaslar" not in data:
            data["arkadaslar"] = []
            degisiklik = True
        if "gelen_istekler" not in data:
            data["gelen_istekler"] = []
            degisiklik = True
            
    if degisiklik:
        with open(DB_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=4)
            
    return db

def veritabani_kaydet(veri):
    with open(DB_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

def benzersiz_id_uret(db):
    while True:
        yeni_id = "#" + str(random.randint(10000, 99999))
        if not any(kullanici.get("id") == yeni_id for kullanici in db.values()):
            return yeni_id

def junilex_arsive_kaydet(kategori, baslik, metin):
    try:
        db = get_db()
        db.collection("junilex_arsiv").add({
            "kategori": kategori, "baslik": baslik, "metin": metin,
            "tarih": firestore.SERVER_TIMESTAMP, "kullanici": st.session_state.aktif_kullanici
        })
        return True, "Başarılı"
    except Exception as e: return False, str(e)

def onay_kodu_gonder(alici_mail, kod):
    gonderici_mail = "ozan.scm@gmail.com"
    uygulama_sifresi = "eidf uhkc zqxl gyhs"
    msg = MIMEText(f"JUNILEX'e hoş geldin!\n\nKayıt işlemini tamamlamak için doğrulama kodun: {kod}\n\nBu kodu kimseyle paylaşmayın.", "plain", "utf-8")
    msg['Subject'] = "JUNILEX Doğrulama Kodu"
    msg['From'] = "JUNILEX Asistan"
    msg['To'] = alici_mail
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gonderici_mail, uygulama_sifresi)
        server.send_message(msg)
        server.quit()
        return True, "Başarılı"
    except Exception as e: return False, str(e)

def metni_sayfalara_bol(metin, sayfa_boyutu=1000):
    if not metin: return []
    paragraflar = metin.split('\n')
    sayfalar = []
    suanki_sayfa = ""
    for p in paragraflar:
        if len(suanki_sayfa) + len(p) > sayfa_boyutu:
            sayfalar.append(suanki_sayfa.strip())
            suanki_sayfa = p + "\n"
        else: suanki_sayfa += p + "\n"
    if suanki_sayfa.strip(): sayfalar.append(suanki_sayfa.strip())
    return sayfalar

# ==========================================
# 🚀 SESSION STATE YÖNETİMİ
# ==========================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "aktif_kullanici" not in st.session_state: st.session_state.aktif_kullanici = ""
if "aktif_kullanici_email" not in st.session_state: st.session_state.aktif_kullanici_email = ""
if "aktif_kullanici_id" not in st.session_state: st.session_state.aktif_kullanici_id = ""
if "kullanici_veritabani" not in st.session_state: st.session_state.kullanici_veritabani = veritabani_yukle() 
if "onay_bekleyen" not in st.session_state: st.session_state.onay_bekleyen = None 
if 'aktif_ekran' not in st.session_state: st.session_state.aktif_ekran = '🏠 Ana Ekran'
if 'secili_kanun' not in st.session_state: st.session_state.secili_kanun = None
if 'bulunan_madde' not in st.session_state: st.session_state.bulunan_madde = None
if 'arama_sonuclari' not in st.session_state: st.session_state.arama_sonuclari = []
if 'islenmis_not' not in st.session_state: st.session_state.islenmis_not = None
if 'su_anki_sinav' not in st.session_state: st.session_state.su_anki_sinav = None
if "aktif_sayfa" not in st.session_state: st.session_state.aktif_sayfa = 0
if "analiz_aktif_sayfa" not in st.session_state: st.session_state.analiz_aktif_sayfa = 0
if "akademi_aktif_sayfa" not in st.session_state: st.session_state.akademi_aktif_sayfa = 0
if "kitap_sayfalari" not in st.session_state: st.session_state.kitap_sayfalari = []
if "analiz_sayfalari" not in st.session_state: st.session_state.analiz_sayfalari = []
if "akademi_notlari" not in st.session_state: st.session_state.akademi_notlari = []
if "chat_mode" not in st.session_state: st.session_state.chat_mode = "Özet"
if "chat_messages" not in st.session_state: st.session_state.chat_messages = [{"role": "assistant", "content": "Selam ustam, hangi meseleyi veya belgeyi aydınlatalım?"}]
if "aktif_dosya" not in st.session_state: st.session_state.aktif_dosya = None

# ==========================================
# 🛑 GİRİŞ VE KAYIT EKRANI
# ==========================================
if not st.session_state.logged_in:
    st.markdown("""<style>[data-testid="collapsedControl"] {display: none;} [data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
    st.write("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center; font-size: 3rem;'>⚖️ JUNILEX</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; font-size: 1.2rem; margin-bottom: 0px;'>Kıdemli Yapay Zeka Hukuk Asistanı</p>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.9rem;'><em>Geliştirici: Ozan Şahin Sicim<br>Çankırı Karatekin Üniversitesi Hukuk Fakültesi Öğrencisi</em></p>", unsafe_allow_html=True)
        st.markdown("---")
        
        tab_giris, tab_kayit = st.tabs(["🔐 Giriş Yap", "📝 Yeni Kayıt"])
        
        with tab_giris:
            giris_email = st.text_input("E-Posta Adresi", key="giris_email")
            giris_sifre = st.text_input("Şifre", type="password", key="giris_sifre")
            if st.button("🚀 Sisteme Giriş Yap", use_container_width=True):
                st.session_state.kullanici_veritabani = veritabani_yukle()
                if giris_email in st.session_state.kullanici_veritabani and st.session_state.kullanici_veritabani[giris_email]["sifre"] == giris_sifre:
                    st.session_state.logged_in = True
                    st.session_state.aktif_kullanici = st.session_state.kullanici_veritabani[giris_email]["isim"]
                    st.session_state.aktif_kullanici_email = giris_email
                    st.session_state.aktif_kullanici_id = st.session_state.kullanici_veritabani[giris_email]["id"]
                    st.rerun() 
                else: st.error("E-posta adresi veya şifre hatalı!")
                    
        with tab_kayit:
            if st.session_state.onay_bekleyen is None:
                kayit_isim = st.text_input("İsim Soyisim", key="kayit_isim") 
                kayit_email = st.text_input("E-Posta Adresi", key="kayit_email")
                kayit_sifre = st.text_input("Yeni Şifre", type="password", key="kayit_sifre")
                kayit_sifre_tekrar = st.text_input("Şifre Tekrar", type="password", key="kayit_sifre_tekrar")
                if st.button("Kayıt Ol", use_container_width=True):
                    st.session_state.kullanici_veritabani = veritabani_yukle()
                    if len(kayit_isim.strip()) < 3: st.warning("⚠️ Lütfen geçerli bir İsim Soyisim giriniz!")
                    elif "@" not in kayit_email or "." not in kayit_email: st.warning("⚠️ Lütfen geçerli bir e-posta adresi giriniz!")
                    elif kayit_email in st.session_state.kullanici_veritabani: st.warning("Bu e-posta adresi zaten sisteme kayıtlı!")
                    elif kayit_sifre != kayit_sifre_tekrar: st.error("Şifreler uyuşmuyor!")
                    elif len(kayit_sifre) < 6: st.warning("Şifre en az 6 karakter olmalıdır.")
                    else:
                        uretilen_kod = str(random.randint(100000, 999999))
                        with st.spinner("Onay kodu e-postanıza gönderiliyor..."):
                            basarili_mi, hata_mesaji = onay_kodu_gonder(kayit_email, uretilen_kod)
                        if basarili_mi:
                            st.session_state.onay_bekleyen = {"isim": kayit_isim.title(), "email": kayit_email, "sifre": kayit_sifre, "kod": uretilen_kod}
                            st.success("✅ Kod gönderildi! Lütfen e-postanızı kontrol edin.")
                            st.rerun()
                        else: st.error(f"E-posta gönderilemedi! Teknik detay: {hata_mesaji}")
            else:
                st.info(f"📧 **{st.session_state.onay_bekleyen['email']}** adresine 6 haneli bir doğrulama kodu gönderdik.")
                girilen_kod = st.text_input("Doğrulama Kodu", key="dogrulama_kodu", max_chars=6)
                col_onay1, col_onay2, col_onay3 = st.columns(3)
                
                with col_onay1:
                    if st.button("✅ Kodu Doğrula", use_container_width=True):
                        if girilen_kod == st.session_state.onay_bekleyen["kod"]:
                            import datetime  # Tarihi almak için eklendi
                            bugun = datetime.date.today().strftime("%d.%m.%Y")
                            
                            yeni_mail = st.session_state.onay_bekleyen["email"]
                            yeni_id = benzersiz_id_uret(st.session_state.kullanici_veritabani)
                            
                            st.session_state.kullanici_veritabani[yeni_mail] = {
                                "sifre": st.session_state.onay_bekleyen["sifre"], 
                                "isim": st.session_state.onay_bekleyen["isim"],
                                "id": yeni_id,
                                "kayit_tarihi": bugun,  # 🔥 KAYIT TARİHİ BURADA EKLENİYOR
                                "arkadaslar": [],
                                "gelen_istekler": []
                            }
                            veritabani_kaydet(st.session_state.kullanici_veritabani)
                            st.session_state.onay_bekleyen = None
                            st.balloons() 
                            st.success("🎉 Kayıt başarılı! Şimdi 'Giriş Yap' sekmesine geçerek JUNILEX'i kullanmaya başlayabilirsiniz.")
                        else: st.error("❌ Doğrulama kodu hatalı! Lütfen tekrar kontrol edin.")
                with col_onay2:
                    if st.button("🔄 Tekrar Kod Gönder", use_container_width=True):
                        yeni_kod = str(random.randint(100000, 999999))
                        with st.spinner("Yeni kod hazırlanıyor..."):
                            basarili, mesaj = onay_kodu_gonder(st.session_state.onay_bekleyen["email"], yeni_kod)
                        if basarili:
                            st.session_state.onay_bekleyen["kod"] = yeni_kod
                            st.toast("✅ Yeni kod başarıyla gönderildi!", icon="📧")
                        else: st.error(f"Kod gönderimi başarısız: {mesaj}")
                with col_onay3:
                    if st.button("⬅️ Bilgileri Düzenle", use_container_width=True):
                        st.session_state.onay_bekleyen = None
                        st.rerun()
    st.stop()

# ==========================================
# 🧭 SIDEBAR (SADECE MODÜLLERDE GÖRÜNÜR)
# ==========================================
try:
    AkademikEngine.veritabanini_baslat()
except Exception as e:
    pass

if st.session_state.aktif_ekran != "🏠 Ana Ekran":
    with st.sidebar:
        st.markdown(f"### 🧑‍💻 Hoş geldin, {st.session_state.aktif_kullanici}")
        st.caption(f"Senin ID'n: **{st.session_state.aktif_kullanici_id}**")
        
        if st.button("🏠 Ana Menüye Dön", use_container_width=True):
            st.session_state.aktif_ekran = "🏠 Ana Ekran"
            st.rerun()
        st.divider()
        
        # GÜNCELLEME: "🧮 Pratik Hesaplamalar" listeye eklendi
        secenekler = [
            "🏠 Ana Ekran", 
            "🏛️ Adliye (Mevzuat Sorgu)", 
            "🎓 Akademi (Ders Notları)", 
            "📝 Arzuhal(Dilekçe Yazım Merkezi)", 
            "⚖️ İçtihat Sorgulama", 
            "💬 JUNILEX Chat", 
            "👥 Junilex Ağı",
            "🧮 Pratik Hesaplamalar"
        ]
        
        if st.session_state.aktif_ekran not in secenekler:
            st.session_state.aktif_ekran = secenekler[1]
            
        current_index = secenekler.index(st.session_state.aktif_ekran)
        secilen = st.radio("Departman:", secenekler, index=current_index)
        
        if secilen != st.session_state.aktif_ekran:
            st.session_state.aktif_ekran = secilen
            st.rerun()
            
        st.divider()
        with st.expander("📊 Çalışma Verileri", expanded=False):
            try:
                db = get_db()
                arsiv_ref = db.collection("junilex_arsiv").where("kullanici", "==", st.session_state.aktif_kullanici).get()
                pdf_ref = db.collection("ders_notlari").get()
                col1, col2 = st.columns(2)
                col1.metric("Arşiv", len(arsiv_ref))
                col2.metric("PDF", len(pdf_ref))
            except Exception:
                st.caption("Veriler yükleniyor...")
                
        st.divider()
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.aktif_kullanici = ""
            st.rerun()
        st.info("Ozan Şahin Sicim | JUNILEX AI v2.2")

# ==========================================
# 🏠 DASHBOARD (ANA EKRAN)
# ==========================================
if st.session_state.aktif_ekran == "🏠 Ana Ekran":
    spacer_sol, ana_kolon, spacer_sag = st.columns([1, 2, 1])
    
    with ana_kolon:
        st.markdown("""
            <div class="header-container">
                <svg class="header-logo-svg" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="50" cy="50" r="45" stroke="#C5A059" stroke-width="2" fill="none"/>
                    <path d="M30 45C30 45 35 60 50 60C65 60 70 45 70 45" stroke="#C5A059" stroke-width="2" fill="none"/>
                    <path d="M50 20V80" stroke="#C5A059" stroke-width="2"/>
                    <path d="M25 35H75" stroke="#1A1A1A" stroke-width="4"/>
                </svg>
                <h1 class="main-title">JUNILEX AI</h1>
                <p class="sub-title">LEGAL INTELLIGENCE & ACADEMY</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.title(f"Selam {st.session_state.aktif_kullanici.split(' ')[0]},")
        st.markdown("Bugün hangi hukuk sahasında derinleşelim?")
        st.write("---")
        
        üst_satir_1, üst_satir_2 = st.columns(2)
        if üst_satir_1.button("🏛️ Adliye", use_container_width=True): st.session_state.aktif_ekran = "🏛️ Adliye (Mevzuat Sorgu)"; st.rerun()
        if üst_satir_2.button("🎓 Akademi", use_container_width=True): st.session_state.aktif_ekran = "🎓 Akademi (Ders Notları)"; st.rerun()
            
        alt_satir_1, alt_satir_2 = st.columns(2)
        if alt_satir_1.button("📝 Arzuhal", use_container_width=True): st.session_state.aktif_ekran = "📝 Arzuhal(Dilekçe Yazım Merkezi)"; st.rerun()
        if alt_satir_2.button("⚖️ İçtihat", use_container_width=True): st.session_state.aktif_ekran = "⚖️ İçtihat Sorgulama"; st.rerun()
        
        st.write("<br>", unsafe_allow_html=True)
        
        # GÜNCELLEME: Hesaplamalar Butonu eklendi (Artık 3 Kolon)
        col_chat, col_ag, col_hesap = st.columns(3)
        if col_chat.button("💬 JUNILEX Chat", use_container_width=True, type="primary"): st.session_state.aktif_ekran = "💬 JUNILEX Chat"; st.rerun()
        if col_ag.button("👥 Junilex Ağı", use_container_width=True): st.session_state.aktif_ekran = "👥 Junilex Ağı"; st.rerun()
        if col_hesap.button("🧮 Hesaplayıcılar", use_container_width=True): st.session_state.aktif_ekran = "🧮 Pratik Hesaplamalar"; st.rerun()

        st.write("---")
        
        st.subheader("📊 Aktivite Özeti")
        try:
            db_fs = get_db()
            tum_kayitlar = list(db_fs.collection("junilex_arsiv").where("kullanici", "==", st.session_state.aktif_kullanici).stream())
            
            toplam_islem = len(tum_kayitlar)
            mevzuat_sayisi = sum(1 for d in tum_kayitlar if "Mevzuat" in d.to_dict().get("kategori", ""))
            dilekce_sayisi = sum(1 for d in tum_kayitlar if "Dilekçe" in d.to_dict().get("kategori", ""))
            ictihat_sayisi = sum(1 for d in tum_kayitlar if "İçtihat" in d.to_dict().get("kategori", ""))
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Toplam Kayıt", toplam_islem)
            m2.metric("Mevzuat Şerhi", mevzuat_sayisi)
            m3.metric("Dilekçe Taslağı", dilekce_sayisi)
            m4.metric("İçtihat Analizi", ictihat_sayisi)
            
        except Exception as e:
            st.caption("Aktivite verileri yüklenemedi.")

        st.write("---")
        st.subheader("🕒 Son 3 İşlem")
        try:
            recent = db_fs.collection("junilex_arsiv").where("kullanici", "==", st.session_state.aktif_kullanici).order_by("tarih", direction=firestore.Query.DESCENDING).limit(3).stream()
            found = False
            for doc in recent:
                d = doc.to_dict()
                with st.container(border=True):
                    col_i, col_b = st.columns([1, 8])
                    col_i.markdown("📄")
                    col_b.markdown(f"**{d.get('baslik')}** \n *Kategori: {d.get('kategori')}*")
                    found = True
            if not found: st.info("Henüz geçmiş işlem yok.")
        except Exception as e:
            st.error(f"Veri çekilemedi: {e}")

# ==========================================
# 👥 JUNILEX AĞI (SOSYAL AĞ VE EKİPLER)
# ==========================================
elif st.session_state.aktif_ekran == "👥 Junilex Ağı":
    st.title("👥 Junilex Ağı ve Ekipler")
    st.markdown("Meslektaşlarınla bağlantı kur, ekipler oluştur ve ortak arşivde çalış.")
    
    benim_mailim = st.session_state.aktif_kullanici_email
    
    col_id, col_bildirim = st.columns([4, 1])
    with col_id:
        st.info(f"📌 **Senin JUNILEX ID'n:** `{st.session_state.aktif_kullanici_id}`")
    with col_bildirim:
        with st.popover("🔔 Bildirimler", use_container_width=True):
            st.markdown("### 📢 Son Hareketler")
            try:
                db_fs = get_db()
                bildirimler = AgEngine.bildirimleri_getir(db_fs, benim_mailim)
                if not bildirimler:
                    st.write("Şu an yeni bir bildiriminiz yok.")
                else:
                    for b in bildirimler:
                        st.info(b.get("mesaj"))
            except Exception as e:
                if "index" in str(e).lower():
                    st.error("Bildirimler için Index bekleniyor...")
    
    st.session_state.kullanici_veritabani = veritabani_yukle()
    db_json = st.session_state.kullanici_veritabani
    benim_verim = db_json.get(benim_mailim, {})
    
    gelen_istekler = benim_verim.get("gelen_istekler", [])
    arkadaslar = benim_verim.get("arkadaslar", [])
    
    tab_ara, tab_istekler, tab_arkadaslar, tab_ekipler = st.tabs([
        "🔍 Kişi Ara", 
        f"🔔 İstekler ({len(gelen_istekler)})", 
        f"🤝 Arkadaşlarım ({len(arkadaslar)})",
        "🏢 Ekiplerim ve Arşiv"
    ])
    
    with tab_ara:
        st.subheader("Hukukçu Bul")
        aranan_id = st.text_input("Kullanıcının 5 Haneli ID'sini Girin (Örn: #12345)")
        
        if st.button("Ara", use_container_width=True, type="primary"):
            st.session_state.son_aranan_id = aranan_id
            
        if st.session_state.get("son_aranan_id"):
            bulunan_mail, bulunan_isim = AgEngine.kisi_ara(db_json, st.session_state.son_aranan_id)
            
            if bulunan_mail:
                if bulunan_mail == benim_mailim:
                    st.warning("Kendini ekleyemezsin ustam!")
                elif bulunan_mail in arkadaslar:
                    st.info(f"✅ **{bulunan_isim}** zaten seninle bağlantılı.")
                else:
                    st.success(f"👤 Kullanıcı Bulundu: **{bulunan_isim}**")
                    
                    karsi_istekler = db_json[bulunan_mail].get("gelen_istekler", [])
                    if benim_mailim in karsi_istekler:
                        st.info("⏳ Bu kullanıcıya zaten bağlantı isteği gönderdin. Yanıt bekleniyor...")
                    else:
                        if st.button(f"➕ {bulunan_isim}'e İstek Gönder", key="btn_istek_at"):
                            db_json = AgEngine.arkadaslik_istegi_gonder(db_json, benim_mailim, bulunan_mail)
                            veritabani_kaydet(db_json)
                            st.session_state.son_aranan_id = None
                            st.success("İstek başarıyla gönderildi!")
                            st.rerun()
            else:
                st.error("Bu ID'ye ait bir Junilex kullanıcısı bulunamadı.")

    with tab_istekler:
        st.subheader("Gelen Bağlantı İstekleri")
        if not gelen_istekler:
            st.info("Şu an bekleyen bir isteğin yok.")
        else:
            for istek_mail in gelen_istekler:
                istek_isim = db_json.get(istek_mail, {}).get("isim", "Bilinmeyen")
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"👤 **{istek_isim}** seninle bağlantı kurmak istiyor.")
                    with col2:
                        if st.button("✅ Kabul Et", key=f"kabul_{istek_mail}", use_container_width=True):
                            db_json = AgEngine.istek_kabul_et(db_json, benim_mailim, istek_mail)
                            veritabani_kaydet(db_json)
                            st.success("Bağlantı kuruldu!")
                            st.rerun()
                    with col3:
                        if st.button("❌ Reddet", key=f"reddet_{istek_mail}", use_container_width=True):
                            db_json = AgEngine.istek_reddet(db_json, benim_mailim, istek_mail)
                            veritabani_kaydet(db_json)
                            st.rerun()

    with tab_arkadaslar:
        st.subheader("Bağlantılı Olduğum Kişiler")
        if not arkadaslar:
            st.info("Henüz ekli bir meslektaşın yok. Kişi Ara sekmesinden Junilex ID'si ile bağlantı kurmaya başla!")
        else:
            for ark_mail in arkadaslar:
                ark_data = db_json.get(ark_mail, {})
                ark_isim = ark_data.get("isim", "Bilinmeyen")
                ark_id = ark_data.get("id", "")
                
                with st.container(border=True):
                    col_isim, col_profil, col_sil = st.columns([3, 1, 1])
                    with col_isim:
                        st.markdown(f"🤝 **{ark_isim}** `({ark_id})`")
                    
                    with col_profil:
                        with st.popover("👁️ Profili Gör", use_container_width=True):
                            st.markdown(f"#### {ark_isim}")
                            st.caption(f"Junilex ID: {ark_id}")
                            st.divider()
                            st.write(f"📅 **Ağa Katılım:** {ark_data.get('kayit_tarihi', 'Bilinmiyor')}")
                            ortak_bag = set(ark_data.get("arkadaslar", [])).intersection(set(arkadaslar))
                            st.write(f"👥 **Ortak Bağlantı:** {len(ortak_bag)} kişi")
                            
                            try:
                                ark_arsiv = get_db().collection("junilex_arsiv").where("kullanici", "==", ark_isim).get()
                                st.write(f"📊 **Hukuki İşlem Hacmi:** {len(ark_arsiv)} Evrak")
                            except Exception:
                                st.write("📊 Aktivite verisi alınamadı.")

                    with col_sil:
                        if st.button("Kaldır", key=f"sil_ark_{ark_mail}", use_container_width=True):
                            db_json = AgEngine.arkadas_cikar(db_json, benim_mailim, ark_mail)
                            veritabani_kaydet(db_json)
                            st.rerun()

    with tab_ekipler:
        db_fs = get_db()
        c_kur, c_katil = st.columns(2)
        
        with c_kur:
            st.subheader("🛠️ Yeni Ekip Kur")
            ekip_adi = st.text_input("Ekip Adı", placeholder="Örn: Ceza Departmanı")
            if st.button("🚀 Ekip Kur", use_container_width=True, type="primary"):
                if ekip_adi:
                    yeni_id = AgEngine.ekip_kur(db_fs, ekip_adi, benim_mailim, st.session_state.aktif_kullanici)
                    st.success(f"Ekip kuruldu! ID: {yeni_id}")
                    st.rerun()
        
        with c_katil:
            st.subheader("🚪 Ekibe Katıl")
            girilen_ekip_id = st.text_input("Ekip ID'si Girin")
            if st.button("İstek Gönder", use_container_width=True):
                basarili = AgEngine.ekibe_katilma_istegi_gonder(db_fs, girilen_ekip_id, benim_mailim)
                if basarili:
                    st.success("Katılma isteği gönderildi.")
                else:
                    st.error("Böyle bir ekip ID'si yok.")

        st.divider()
        st.subheader("🏢 Ekiplerim")
        
        ekiplerim_doc_listesi = AgEngine.ekiplerimi_getir(db_fs, benim_mailim)
        
        for doc in ekiplerim_doc_listesi:
            ekip = doc.to_dict()
            g_id = ekip.get('ekip_id', 'ID Yok')
            g_isim = ekip.get('isim', 'İsimsiz')
            g_uyeler = ekip.get('uyeler_isim', [])
            
            with st.expander(f"🏢 {g_isim} ({g_id})"):
                st.info(f"🔑 **Ekip ID:** `{g_id}`")
                st.write(f"👥 **Üyeler:** {', '.join(g_uyeler)}")
                
                if ekip.get('kurucu') == benim_mailim:
                    if ekip.get('istekler'):
                        st.write("📩 **Bekleyen İstekler:**")
                        for istek_mail in ekip.get('istekler', []):
                            col_istek, col_onay = st.columns([3, 1])
                            col_istek.write(f"👤 {istek_mail}")
                            if col_onay.button("✅ Onayla", key=f"onay_{istek_mail}_{doc.id}"):
                                istek_isim = db_json.get(istek_mail, {}).get("isim", "Üye")
                                AgEngine.ekip_istek_onayla(doc.reference, istek_mail, istek_isim)
                                st.rerun()
                    
                    st.markdown("---")
                    if st.button("🗑️ EKİBİ TAMAMEN SİL", key=f"sil_{doc.id}", type="primary", use_container_width=True):
                        doc.reference.delete()
                        st.warning("Ekip silindi!")
                        st.rerun()

        st.divider()
        st.subheader("🏢 Aktif Ekip Paneli")
        
        if ekiplerim_doc_listesi:
            ekip_katalogu = {d.to_dict().get("isim"): d for d in ekiplerim_doc_listesi}
            secilen_ekip_adi = st.selectbox("Çalışacağın Ekibi Seç:", list(ekip_katalogu.keys()))
            aktif_ekip_doc = ekip_katalogu[secilen_ekip_adi]
            aktif_ekip = aktif_ekip_doc.to_dict()
            aktif_ekip_id = aktif_ekip.get("ekip_id")
            
            st.markdown(f"**Üyeler:** {', '.join(aktif_ekip.get('uyeler_isim', []))}")
            st.divider()
            
            # Görevler sekmesini de ekledik
            alt_tab_arsiv, alt_tab_sohbet, alt_tab_gorevler = st.tabs(["🗂️ Ortak Arşiv", "💬 Ekip İçi Sohbet", "📅 Görev ve Duruşmalar"])
            
            with alt_tab_arsiv:
                ortak_evraklar = AgEngine.ekip_ortak_arsiv_getir(db_fs, aktif_ekip.get('uyeler_isim', []))
                
                if not ortak_evraklar:
                    # Büyüteç / Boş Kutu Animasyonu
                    animasyon_arsiv = lottie_yukle("https://lottie.host/2117fc04-5801-447a-ba92-b4ea4e84b7f0/L58u8rK7fD.json")
                    if animasyon_arsiv:
                        st_lottie(animasyon_arsiv, height=200, key="lottie_arsiv")
                    st.info("Bu ekibin üyeleri arşive henüz bir belge işlememiş.")
                else:
                    # ... (Buradaki eski for evrak in ortak_evraklar: kodu aynen kalacak)
                    for evrak in ortak_evraklar:
                        e_data = evrak.to_dict()
                        with st.expander(f"📄 {e_data.get('baslik')} | 👤 {e_data.get('kullanici')}"):
                            st.write(e_data.get("metin"))
                            st.download_button("📥 TXT İndir", data=e_data.get("metin", ""), file_name=f"{e_data.get('baslik')}.txt", key=f"dl_{evrak.id}", use_container_width=True)

            import time

            with alt_tab_sohbet:
                @st.fragment(run_every=3)
                def sohbeti_otomatik_guncelle():
                    sohbet_alani = st.container(height=400)
                    try:
                        db_mesajlari = AgEngine.sohbet_mesajlarini_getir(db_fs, aktif_ekip_id)
                        
                        son_mesaj = st.session_state.get("bekleyen_mesaj", "")
                        db_de_var_mi = any(m.get("mesaj") == son_mesaj and m.get("isim") == st.session_state.aktif_kullanici for m in db_mesajlari)

                        with sohbet_alani:
                            mesaj_var_mi = False
                            
                            for m_data in db_mesajlari:
                                mesaj_var_mi = True
                                gonderen = m_data.get("isim", "Bilinmeyen")
                                mesaj = m_data.get("mesaj", "")
                                
                                if gonderen == st.session_state.aktif_kullanici:
                                    with st.chat_message("user", avatar="🧑‍💻"): st.markdown(f"**Sen:** {mesaj}")
                                else:
                                    with st.chat_message("assistant", avatar="👤"): st.markdown(f"**{gonderen}:** {mesaj}")
                                        
                            if son_mesaj and not db_de_var_mi:
                                if time.time() - st.session_state.get("bekleyen_mesaj_zamani", 0) < 5: 
                                    mesaj_var_mi = True
                                    with st.chat_message("user", avatar="⏳"): st.markdown(f"**Sen:** {son_mesaj}")
                                        
                            # Sohbet boşsa gösterilecek modern arayüz
                            if not mesaj_var_mi:
                                st.markdown("""
                                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; text-align: center; color: #9ca3af; padding: 20px;">
                                    <div style="font-size: 60px; margin-bottom: 20px;">💬</div>
                                    <h3 style="color: #374151; margin-bottom: 10px;">Henüz Sohbet Başlamadı</h3>
                                    <p style="max-width: 300px; font-size: 14px;">Ekibinle dosya detayları, duruşma notları veya stratejiler üzerine konuşmak için bir mesaj gönder.</p>
                                    <div style="margin-top: 15px; padding: 10px 20px; background: #f3f4f6; border-radius: 20px; font-size: 12px; font-weight: 500;">
                                        🚀 İlk adımı sen at!
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                    except Exception as e:
                        if "index" not in str(e).lower():
                            st.error(f"Sohbet yüklenemedi: {e}")

                sohbeti_otomatik_guncelle()

                if yeni_mesaj := st.chat_input("Ekibe mesaj yaz..."):
                    st.session_state.bekleyen_mesaj = yeni_mesaj
                    st.session_state.bekleyen_mesaj_zamani = time.time()
                    
                    # Motor üzerinden arka planda Firebase'e atıyoruz
                    AgEngine.arka_planda_mesaj_gonder(aktif_ekip_id, st.session_state.aktif_kullanici, yeni_mesaj)
                    
                    st.rerun()
            with alt_tab_gorevler:
                st.subheader("📌 Ekip İş ve Duruşma Takibi")
                
                # 1. YENİ GÖREV EKLEME FORMU
                with st.expander("➕ Yeni Görev / Duruşma Ata"):
                    g_baslik = st.text_input("Görev Başlığı", placeholder="Örn: X Şirketi Sözleşme İncelemesi")
                    g_aciklama = st.text_area("Açıklama / Detaylar", placeholder="Dosya no, tarih veya notlar...")
                    g_atanan = st.selectbox("Kime Atanacak?", aktif_ekip.get('uyeler_isim', []))
                    
                    if st.button("Görevi Kaydet", use_container_width=True, type="primary"):
                        if g_baslik:
                            # GÜNCELLEME: Bildirim atabilmesi için uyeler_mail eklendi
                            AgEngine.gorev_ekle(db_fs, aktif_ekip_id, g_baslik, g_aciklama, g_atanan, st.session_state.aktif_kullanici, aktif_ekip.get('uyeler_mail', []))
                            st.success("Görev başarıyla eklendi!")
                            st.rerun()
                        else:
                            st.warning("Görev başlığı boş bırakılamaz.")
                
                st.divider()
                
                # 2. KANBAN PANOSU (3 Kolonlu Görev Yönetimi)
                try:
                    gorevler = AgEngine.gorevleri_getir(db_fs, aktif_ekip_id)
                    
                    if not gorevler:
                        # NOTION TARZI MİNİMALİST BOŞ DURUM
                        st.markdown("""
                        <div style="text-align: center; padding: 40px 20px; background-color: #fafafa; border-radius: 12px; border: 2px dashed #e5e7eb; margin: 20px 0;">
                            <div style="font-size: 48px; margin-bottom: 10px;">🗂️</div>
                            <h3 style="color: #374151; margin-bottom: 5px; font-weight: 600;">Masa Tertemiz!</h3>
                            <p style="color: #6b7280; font-size: 15px; margin-bottom: 0px;">Şu an ekibe atanmış aktif bir görev veya duruşma bulunmuyor.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # HIZLI ŞABLON BUTONLARI (Kullanıcı dostu özellik)
                        st.caption("⚡ Hızlı Şablonlarla Görev Oluştur:")
                        c_h1, c_h2, c_h3 = st.columns(3)
                        if c_h1.button("⚖️ Duruşma Ekle", use_container_width=True):
                            AgEngine.gorev_ekle(db_fs, aktif_ekip_id, "Yaklaşan Duruşma Hazırlığı", "Duruşma tarihi, saati ve dosya numarası:", st.session_state.aktif_kullanici, st.session_state.aktif_kullanici, aktif_ekip.get('uyeler_mail', []))
                            st.rerun()
                        if c_h2.button("📄 Sözleşme İncele", use_container_width=True):
                            AgEngine.gorev_ekle(db_fs, aktif_ekip_id, "Sözleşme İncelemesi", "Müvekkilden gelen sözleşmenin risk analizi yapılacak.", st.session_state.aktif_kullanici, st.session_state.aktif_kullanici, aktif_ekip.get('uyeler_mail', []))
                            st.rerun()
                        if c_h3.button("🤝 Müvekkil Görüşmesi", use_container_width=True):
                            AgEngine.gorev_ekle(db_fs, aktif_ekip_id, "Müvekkil Toplantısı", "Toplantı notları ve talep edilen evraklar hazırlanacak.", st.session_state.aktif_kullanici, st.session_state.aktif_kullanici, aktif_ekip.get('uyeler_mail', []))
                            st.rerun()
                        col_yap, col_devam, col_bit = st.columns(3)
                        
                        with col_yap: st.markdown("### 🔴 Yapılacaklar")
                        with col_devam: st.markdown("### 🟡 Devam Edenler")
                        with col_bit: st.markdown("### 🟢 Tamamlananlar")
                            
                        for g in gorevler:
                            durum = g.get("durum", "Yapılacak")
                            kart_icerik = f"**{g.get('baslik')}**\n\n👤 *Atanan: {g.get('atanan')}*\n\n📝 {g.get('aciklama')}"
                            
                            # Kartları durumlarına göre kolonlara dağıt
                            if durum == "Yapılacak":
                                with col_yap:
                                    with st.container(border=True):
                                        st.markdown(kart_icerik)
                                        c1, c2 = st.columns(2)
                                        if c1.button("Başla ➡️", key=f"basla_{g['id']}", use_container_width=True):
                                            # GÜNCELLEME: Bildirim parametreleri eklendi
                                            AgEngine.gorev_durumu_guncelle(db_fs, g['id'], "Devam Ediyor", g.get('baslik'), st.session_state.aktif_kullanici, aktif_ekip.get('uyeler_mail', []))
                                            st.rerun()
                                        if c2.button("🗑️ Sil", key=f"sil_yap_{g['id']}", use_container_width=True):
                                            AgEngine.gorev_sil(db_fs, g['id'])
                                            st.rerun()
                                            
                            elif durum == "Devam Ediyor":
                                with col_devam:
                                    with st.container(border=True):
                                        st.markdown(kart_icerik)
                                        c1, c2 = st.columns(2)
                                        if c1.button("Bitti ✅", key=f"bitir_{g['id']}", use_container_width=True):
                                            # GÜNCELLEME: Bildirim parametreleri eklendi
                                            AgEngine.gorev_durumu_guncelle(db_fs, g['id'], "Tamamlandı", g.get('baslik'), st.session_state.aktif_kullanici, aktif_ekip.get('uyeler_mail', []))
                                            st.rerun()
                                        if c2.button("Geri ⬅️", key=f"geri_{g['id']}", use_container_width=True):
                                            # GÜNCELLEME: Bildirim parametreleri eklendi
                                            AgEngine.gorev_durumu_guncelle(db_fs, g['id'], "Yapılacak", g.get('baslik'), st.session_state.aktif_kullanici, aktif_ekip.get('uyeler_mail', []))
                                            st.rerun()
                                            
                            elif durum == "Tamamlandı":
                                with col_bit:
                                    with st.container(border=True):
                                        st.markdown(kart_icerik)
                                        if st.button("🗑️ Arşivden Sil", key=f"sil_bit_{g['id']}", use_container_width=True):
                                            AgEngine.gorev_sil(db_fs, g['id'])
                                            st.rerun()
                except Exception as e:
                    if "index" in str(e).lower():
                        st.error("⚠️ Görev panosu için veritabanı dizin kurulumu gerekiyor. Lütfen terminal (Log) ekranındaki linke tıklayarak dizini oluştur.")
                    else:
                        st.error(f"Görevler yüklenemedi: {e}")
# ==========================================
# 🏛️ ADLİYE MODÜLÜ
# ==========================================
elif st.session_state.aktif_ekran == "🏛️ Adliye (Mevzuat Sorgu)":
    st.title("🏛️ Junilex Akıllı Mevzuat Bankası")
    st.markdown("Kategori filtreli kanun kütüphanesi. Maddeleri numarayla çağırabilir veya içinde geçen kelimelerle aratabilirsiniz.")

    kanun_listesi = MevzuatBulutEngine.get_kanunlar()

    filtre_col, secim_col = st.columns([1, 2])
    with filtre_col:
        kategoriler = ["🌟 Tüm Alanlar"] + sorted(list(set([k["kategori"] for k in kanun_listesi])))
        secilen_kategori = st.selectbox("📁 Hukuk Alanı Filtresi", kategoriler)

    if secilen_kategori == "🌟 Tüm Alanlar":
        filtrelenmis_kanunlar = kanun_listesi
    else:
        filtrelenmis_kanunlar = [k for k in kanun_listesi if k["kategori"] == secilen_kategori]

    with secim_col:
        gosterim_adlari = [f"{k['kisaAd']} | {k['isim']}" for k in filtrelenmis_kanunlar]
        secilen_gosterim = st.selectbox("📜 İlgili Kanun Mevzuatı", gosterim_adlari)

    secilen_indeks = gosterim_adlari.index(secilen_gosterim)
    secilen_kanun = filtrelenmis_kanunlar[secilen_indeks]

    st.caption(f"📂 **Kategori:** {secilen_kanun['kategori']} | 🆔 **Kanun No:** {secilen_kanun['id']} | 💡 **Kapsam:** {secilen_kanun['aciklama']}")
    st.write("---")

    arama_sekmeleri = st.tabs(["🔢 Madde Numarası İle Nokta Atışı", "🔤 Kelime / Kavram İle İçerik Taraması"])

    with arama_sekmeleri[0]:
        giriş_col, buton_col = st.columns([2, 1])
        with giriş_col:
            girilen_madde = st.text_input("🔢 Aranacak Madde Numarası", placeholder="Örn: 86, Geçici_1...", key="input_no")
        with buton_col:
            st.write("##")
            madde_ara_butonu = st.button("🔍 Maddeyi Getir", use_container_width=True, key="btn_no_ara")

        if madde_ara_butonu and girilen_madde:
            with st.spinner("⚖️ Hafızadan madde getiriliyor..."):
                sonuc = MevzuatBulutEngine.madde_getir_buluttan(secilen_kanun['kisaAd'], girilen_madde)
                if sonuc and isinstance(sonuc, dict):
                    st.session_state["aktif_no_sonucu"] = sonuc
                    st.session_state["aktif_no_madde"] = girilen_madde
                    st.session_state["aktif_no_kanun"] = secilen_kanun['kisaAd']

        if "aktif_no_sonucu" in st.session_state and st.session_state["aktif_no_kanun"] == secilen_kanun['kisaAd']:
            res = st.session_state["aktif_no_sonucu"]
            st.success(f"✅ {res.get('baslik')}")
            st.info(res.get("metin"))
            
            if "henüz yüklenmemiş" not in res.get("metin") and "bulunamadı" not in res.get("metin"):
                st.write("---")
                st.subheader("🤖 Hakim Gözüyle Yapay Zeka Analizi")
                if st.button("🏛️ Hukuki Analizi Başlat", type="primary", key="btn_analiz_no"):
                    with st.spinner("🔮 Kıdemli Yargıtay Tetkik Hakimi analizi üretiliyor..."):
                        akış = MevzuatBulutEngine.madde_analiz_et(MY_API_KEY, secilen_kanun['kisaAd'], st.session_state["aktif_no_madde"], res.get("metin"))
                        if akış: st.write_stream(akış)

    with arama_sekmeleri[1]:
        k_giriş_col, k_buton_col = st.columns([2, 1])
        with k_giriş_col:
            aranan_kelime = st.text_input("🔤 İçinde Geçen Kelime veya İfade", placeholder="Örn: yaralama, kıdem tazminatı, zamanaşımı...", key="input_kelime")
        with k_buton_col:
            st.write("##")
            kelime_ara_butonu = st.button("🔎 Kanunu Baştan Sona Tara", use_container_width=True, key="btn_kelime_ara")

        if kelime_ara_butonu and aranan_kelime:
            with st.spinner(f"🔎 {secilen_kanun['kisaAd']} külliyatında '{aranan_kelime}' taranıyor..."):
                maddeler_havuzu = MevzuatBulutEngine.kelime_ile_ara(secilen_kanun['kisaAd'], aranan_kelime)
                st.session_state["k_arama_sonuclari"] = maddeler_havuzu
                st.session_state["k_arama_kelimesi"] = aranan_kelime
                st.session_state["k_arama_kanun"] = secilen_kanun['kisaAd']

        if "k_arama_sonuclari" in st.session_state and st.session_state["k_arama_kanun"] == secilen_kanun['kisaAd']:
            havuz = st.session_state["k_arama_sonuclari"]
            st.markdown(f"📊 **'{st.session_state['k_arama_kelimesi']}'** ifadesini içeren **{len(havuz)}** adet madde listelendi:")
            
            for i, m in enumerate(havuz):
                with st.expander(f"📜 {m['baslik']}"):
                    st.info(m['metin'])
                    if st.button("🏛️ Bu Maddeyi Yapay Zekaya Analiz Ettir", key=f"btn_analiz_k_{m['no']}_{i}"):
                        with st.spinner("🔮 Madde analiz ediliyor..."):
                            akış = MevzuatBulutEngine.madde_analiz_et(MY_API_KEY, secilen_kanun['kisaAd'], m['no'], m['metin'])
                            if akış: st.write_stream(akış)

    if "aktif_madde" in st.session_state:
        madde = st.session_state.aktif_madde
        st.markdown("---")
        st.subheader(f"📜 {madde['kanun_adi']} — Madde {madde['madde_no']}")
        st.markdown(f"**Başlık:** {madde['baslik']}")

        st.markdown(f"""
        <div class="madde-kutusu">
            <div class="madde-baslik">📋 MADDE {madde['madde_no']} — {madde['baslik'].upper()}</div>
            <div class="madde-icerik"><p>{madde['metin'].replace(chr(10), '<br>')}</p></div>
        </div>
        """, unsafe_allow_html=True)

        resmi_url = f"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={madde['kanun_no']}&MevzuatTur=1&MevzuatTertip=5"
        st.caption(f"📌 Resmi kaynak: [mevzuat.gov.tr]({resmi_url}) — Hukuken bağlayıcı metin için bu adresi ziyaret edin.")

        st.markdown("---")
        ozel_soru = st.text_input("Bu maddeye ilişkin özel bir sorunuz var mı? (İsteğe bağlı)", placeholder="Örn: Bu madde kapsamında zamanaşımı süresi nedir?", key="adliye_ozel_soru")
        if st.button("🤖 Maddeyi JUNILEX AI ile Analiz Et", use_container_width=True, type="primary"):
            with st.spinner("JUNILEX yapay zekası maddeyi yorumluyor..."):
                analiz_sonucu = MevzuatBulutEngine.madde_analiz_et(
                    api_key=MY_API_KEY,
                    madde_metni=madde["metin"],
                    kanun_adi=madde["kanun_adi"],
                    madde_no=madde["madde_no"],
                    soru=ozel_soru
                )
                st.session_state.son_madde_analizi = analiz_sonucu
                st.session_state.son_madde_baslik = f"Mevzuat Analizi: {madde['kanun_adi']} M.{madde['madde_no']}"

        if "son_madde_analizi" in st.session_state:
            st.markdown("### 🧠 JUNILEX Yapay Zeka Analiz Raporu")
            st.markdown(f"""
            <div class="hoca-anlatim-kutusu">
                {st.session_state.son_madde_analizi.replace(chr(10), '<br>')}
            </div>
            """, unsafe_allow_html=True)
            st.caption("⚠️ Yapay zeka analizi hukuki danışmanlık değildir. Kesin bilgi için avukat veya resmi kaynaklara başvurunuz.")
            
            if st.button("💾 Bu Analizi JUNILEX Arşivine Kaydet", key="btn_kaydet_mevzuat"):
                basarili, mesaj = junilex_arsive_kaydet("🏛️ Mevzuat Şerhi", st.session_state.son_madde_baslik, st.session_state.son_madde_analizi)
                if basarili:
                    st.success("✅ Arşive kaydedildi! JUNILEX Chat > Bağlam Arşivi menüsünden seçip tartışabilirsin.")
                else:
                    st.error(f"Hata: {mesaj}")

    # GELİŞTİRİCİ PANELİ
    if st.session_state.get("aktif_kullanici") == "Ozan Şahin Sicim":
        st.write("<br><br><br>", unsafe_allow_html=True)
        with st.expander("🔑 JUNILEX Geliştirici — Kalıcı Hafızaya Kazıma Paneli", expanded=False):
            hedef_kanun_adi = st.selectbox("Yapay Zeka Hafızasına Alınacak Kanun", options=[k["isim"] for k in kanun_listesi], key="admin_yerel_secim")
            hedef_kanun = next(k for k in kanun_listesi if k["isim"] == hedef_kanun_adi)

            if st.button("⚡ Seçilen Kanunu Junilex Yerel Beynine (ChromaDB) Kazı", use_container_width=True):
                with st.spinner(f"🧠 {hedef_kanun['kisaAd']} maddeleri çözülüyor ve yapay zeka beynine kazınıyor..."):
                    try:
                        adet = MevzuatBulutEngine.kanunu_buluta_yukle(id=hedef_kanun["id"], kisa_ad=hedef_kanun["kisaAd"])
                        if adet > 0:
                            st.success(f"🚀 Muhteşem! {adet} adet {hedef_kanun['kisaAd']} maddesi başarıyla Junilex hafızasına işlendi.")
                    except Exception as e:
                        st.error(f"❌ Yerel Vektörleştirme Hatası: {str(e)}")

# ==========================================
# 🎓 AKADEMİ MODÜLÜ
# ==========================================
elif st.session_state.aktif_ekran == "🎓 Akademi (Ders Notları)":
    st.header("🎓 Akademik Asistan")
    
    tab_mufredat, tab_notlar, tab_sinav = st.tabs(["📚 Müfredat", "📄 Notlarım", "📝 Sınav Modu"])
    mufredat_sozlugu = AkademikEngine.get_akademik_mufredat()
    ders_listesi = [f"{ders['ikon']} {ders['isim']}" for sinif_adi, dersler in mufredat_sozlugu.items() for ders in dersler]
            
    with tab_mufredat:
        st.subheader("📚 Ders Seçimi ve Soru")
        
        mufredat = AkademikEngine.get_akademik_mufredat()
        sinif_listesi = list(mufredat.keys())
        
        col1, col2 = st.columns(2)
        with col1:
            secilen_sinif = st.selectbox("Sınıf Seçiniz", options=sinif_listesi, key="akademi_sinif_v3")
        with col2:
            secilen_sinifa_ait_dersler = [ders["isim"] for ders in mufredat[secilen_sinif]]
            secilen_ders = st.selectbox("Ders Seçiniz", options=secilen_sinifa_ait_dersler, key="akademi_ders_v3")
            
        akademik_input = st.text_area("Bu dersle ilgili sorunuzu veya öğrenmek istediğiniz konuyu yazın:", height=100, key="akademi_text")

        if st.button("📚 Soruyu Yanıtla / Anlat", use_container_width=True):
            if not akademik_input.strip():
                st.warning("Lütfen hocaya yöneltmek için bir soru veya konu girin.")
            else:
                try:
                    st.info(f"🏛️ Profesör {secilen_ders} arşivini tarıyor...")
                    cevap_generator = AkademikEngine.mufredat_hoca_anlat(MY_API_KEY, SERPER_API_KEY, secilen_ders, akademik_input)
                    sonuc = st.write_stream(cevap_generator)
                        
                    if sonuc and not sonuc.startswith("⚠️"):
                        st.session_state.akademi_notlari = metni_sayfalara_bol(sonuc, 800)
                        st.session_state.akademi_aktif_sayfa = 0
                        st.success("✅ Hoca yanıtladı! Cevabı aşağıdan okuyabilirsiniz.")
                    else:
                        st.error("AI bir sonuç döndürmedi.")
                except Exception as e:
                    st.error(f"Hoca derse giremedi: {e}")

        if "akademi_notlari" in st.session_state and st.session_state.akademi_notlari:
            import re
            
            sayfalar = st.session_state.akademi_notlari
            aktif = st.session_state.get('akademi_aktif_sayfa', 0)
            
            icerik = sayfalar[aktif]
            icerik = re.sub(r"#{3}\s+(.*?)(?=\n|$)", r"<h3 style='color:#1b5e20; font-family:Georgia; border-bottom: 2px solid #2e7d32; padding-bottom:5px; margin-top:20px; font-size:18px;'>\1</h3><br>", icerik)
            icerik = re.sub(r"#{1,2}\s+(.*?)(?=\n|$)", r"<br><br><b style='color:#3e2723; font-size:16px;'>\1</b><br>", icerik)
            icerik = re.sub(r"#{4,5}\s+(.*?)(?=\n|$)", r"<br><b style='color:#3e2723; font-size:15px;'>\1</b><br>", icerik)
            icerik = re.sub(r"\n\s*\*\*(.*?)\*\*", r"<br><br><b>\1</b>", icerik)
            icerik = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", icerik)
            icerik = icerik.replace("🔍 GERÇEK EMSAL:", "<br><br><b style='color:#2e7d32;'>🔍 GERÇEK EMSAL:</b>")
            icerik = icerik.replace("⚖️ HUKUKİ DAYANAK:", "<br><br><b style='color:#795548;'>⚖️ HUKUKİ DAYANAK:</b>")
            icerik = icerik.replace("📢 SONUÇ:", "<br><br><b style='color:#1565c0;'>📢 SONUÇ:</b>")
            icerik = icerik.replace("* ", "• ").replace("\n", "<br>")

            st.markdown(f"""
            <div style="background-color: #fcfaf5; padding: 40px; border: 1px solid #e0dcd0; border-top: 8px solid #2e7d32; border-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); color: #2c3e50; font-family: 'Georgia', serif;">
                <div style="font-size: 12px; color: #2e7d32; font-weight: bold; text-transform: uppercase; margin-bottom: 20px; letter-spacing: 1px; border-bottom: 1px solid #e0dcd0; padding-bottom: 10px;">
                    🎓 AKADEMİK ANALİZ - Sayfa {aktif + 1}
                </div>
                <div style="font-size: 18px; line-height: 1.8; text-align: justify;">
                    {icerik.replace("\n", "<br>")}
                </div>
                <div style="text-align: right; font-size: 11px; color: #999; margin-top: 30px; font-style: italic;">
                    Junilex Akademik Kaynaklarından derlenmiştir. Toplam {len(sayfalar)} sayfa.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
    
            with col1:
                if aktif > 0:
                    if st.button("⬅️ Geri"):
                        st.session_state.akademi_aktif_sayfa -= 1
                        st.rerun()
            
            with col2:
                st.markdown(f"<center><b>{aktif + 1} . Sayfa</b></center>", unsafe_allow_html=True)
                
            with col3:
                if aktif < len(sayfalar) - 1:
                    if st.button("İleri ➡️"):
                        st.session_state.akademi_aktif_sayfa += 1
                        st.rerun()

    with tab_notlar:
        st.header("📥 Not Yükleme Alanı")
        st.info("💡 Burası sadece senin dışarıdan yüklediğin PDF ders notlarını barındırır. Ürettiğin diğer analizler doğrudan Chat menüsündeki arşivine düşer.")
        
        uploaded_file = st.file_uploader("Notunu Buraya Yükle (PDF)", type="pdf", key="main_uploader")
        
        if uploaded_file is not None:
            dosya_ismi = uploaded_file.name
            with st.spinner("PDF okunuyor ve arşive işleniyor... (Bu biraz sürebilir)"):
                cikarilan_metin = AkademikEngine.dosyadan_metin_cikar(uploaded_file)
                try:
                    db = get_db()
                    db.collection("ders_notlari").add({
                        "dosya_adi": dosya_ismi,
                        "metin": cikarilan_metin,  
                        "tarih": firestore.SERVER_TIMESTAMP
                    })
                    st.session_state.islenmis_not = cikarilan_metin
                    st.session_state.aktif_dosya = dosya_ismi
                    st.success(f"✅ {dosya_ismi} başarıyla okundu ve arşive eklendi!")
                except Exception as e:
                    st.error(f"Veritabanına işlenirken hata: {e}")

        st.markdown("---") 
        st.subheader("📚 Dijital Arşivim")
        with st.expander("Daha Önce Tarattığın PDF Metinleri Yönet", expanded=True):
            mevcut_notlar = AkademikEngine.yuklenen_notlari_getir()
            
            if mevcut_notlar: 
                for not_adi in mevcut_notlar:
                    col_isim, col_sec, col_sil = st.columns([3, 1, 1])
                    with col_isim:
                        st.markdown(f"📄 **{not_adi}**")
                    with col_sec:
                        if st.button("✅ Seç", key=f"sec_{not_adi}"):
                            eski_metin = AkademikEngine.not_icerigi_getir(not_adi)
                            if eski_metin:
                                st.session_state.islenmis_not = eski_metin
                                st.session_state.aktif_dosya = not_adi
                                st.success(f"📌 '{not_adi}' masaya koyuldu, Chat kısmından çalışabilirsin!")
                            else:
                                st.warning("Bu dosyanın metni yok! (Eski, hatalı yükleme olabilir.)")
                    with col_sil:
                        if st.button("🗑️ Sil", key=f"sil_{not_adi}"):
                            basarili = AkademikEngine.not_sil(not_adi)
                            if basarili:
                                st.success("Arşivden silindi!")
                                st.rerun()
                            else:
                                st.error("Silinemedi.")
            else:
                st.info("Henüz yüklü notun yok.")

        st.markdown("---")
        
        st.subheader("❓ Notlardan Soru Sor")
        aktif_not_ismi = st.session_state.get('aktif_dosya', 'Hiçbiri (Genel Hukuk Bilgisi)')
        st.info(f"🔎 **Şu an incelenen evrak:** {aktif_not_ismi}")
        
        not_icerigi = st.session_state.get('islenmis_not', "")
        
        soru_input = st.text_input(
            "Hocaya sormak istediğin soru nedir?", 
            placeholder="Örn: Butlan ve İptal farkı", 
            key="hoca_not_soru_input" 
        )
        
        if st.button("Hocadan Dinle", key="btn_hoca_dinle_notlar"):
            if not_icerigi:
                with st.spinner("Hoca kürsüye çıkıyor, notları inceliyor..."):
                    try:
                        sonuc = AkademikEngine.notlarla_ai_hoca_anlat(
                            MY_API_KEY, 
                            aktif_not_ismi, 
                            not_icerigi
                        )
                        if sonuc:
                            paragraflar = sonuc.split('\n\n')
                            sayfalar = []
                            suanki_sayfa = ""
                            for p in paragraflar:
                                if len(suanki_sayfa) + len(p) > 1500:
                                    sayfalar.append(suanki_sayfa.strip())
                                    suanki_sayfa = p + "\n\n"
                                else:
                                    suanki_sayfa += p + "\n\n"
                            if suanki_sayfa.strip():
                                sayfalar.append(suanki_sayfa.strip())
                            
                            st.session_state.hoca_sayfalar = sayfalar
                            st.session_state.hoca_aktif_sayfa = 0
                            st.rerun()
                    except Exception as e:
                        st.error(f"Hoca anlatırken bir usul hatası oluştu: {e}")
            else:
                st.warning("Lütfen önce bir not yükleyin ustam.")

        if "hoca_sayfalar" in st.session_state and st.session_state.hoca_sayfalar:
            st.markdown("---")
            col_baslik, col_indir = st.columns([3, 1])
            with col_baslik:
                st.markdown("### 📖 Hoca'nın Notu")
                
            with col_indir:
                tam_metin = "\n\n".join(st.session_state.hoca_sayfalar)
                font_reg = "Roboto-Regular.ttf"
                font_bold = "Roboto-Bold.ttf"
                
                if not os.path.exists(font_reg):
                    urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_reg)
                if not os.path.exists(font_bold):
                    urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", font_bold)
                
                svg_logo = '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="50" cy="50" r="45" stroke="#C5A059" stroke-width="2" fill="none"/>
                    <path d="M30 45C30 45 35 60 50 60C65 60 70 45 70 45" stroke="#C5A059" stroke-width="2" fill="none"/>
                    <path d="M50 20V80" stroke="#C5A059" stroke-width="2"/>
                    <path d="M25 35H75" stroke="#1A1A1A" stroke-width="4"/>
                </svg>'''
                
                with open("temp_logo.svg", "w", encoding="utf-8") as f:
                    f.write(svg_logo)
                
                pdf = FPDF()
                pdf.add_page()
                pdf.add_font("Roboto", "", font_reg)
                pdf.add_font("Roboto", "B", font_bold)
                pdf.image("temp_logo.svg", x=85, y=10, w=40)
                pdf.ln(35) 
                
                if os.path.exists("temp_logo.svg"):
                    os.remove("temp_logo.svg")
                
                pdf.set_font("Roboto", style="B", size=16)
                pdf.cell(0, 6, f"İncelenen Evrak: {aktif_not_ismi}", ln=True, align='C')
                
                pdf.set_font("Roboto", "", size=10)
                pdf.cell(0, 6, f"İncelenen Evrak: {aktif_not_ismi}", ln=True, align='C')
                pdf.cell(0, 6, "Hazırlayan: Ozan Şahin Sicim (Çankırı Karatekin Üniversitesi Hukuk Fakültesi)", ln=True, align='C')
                pdf.ln(10)
                
                pdf.set_font("Roboto", size=11)
                pdf.multi_cell(0, 7, tam_metin) 
                
                pdf_bytes = bytes(pdf.output())
                st.download_button(
                    label="📥 PDF Olarak İndir",
                    data=pdf_bytes,
                    file_name=f"Junilex_Mutaala_{aktif_not_ismi}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            aktif = st.session_state.hoca_aktif_sayfa
            sayfalar = st.session_state.hoca_sayfalar
            icerik = sayfalar[aktif]
            
            st.markdown(f"""
            <div style="background-color: #fcfaf5; padding: 40px; border: 1px solid #e0dcd0; border-top: 8px solid #2e7d32; border-radius: 4px; color: #2c3e50;">
                <div style="font-size: 12px; color: #2e7d32; font-weight: bold; margin-bottom: 20px;">
                    🎓 NOT ANALİZİ - Sayfa {aktif + 1} / {len(sayfalar)}
                </div>
                <div style="font-size: 18px; line-height: 1.8;">
                    {icerik.replace("\n", "<br>")}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
            col_sol, col_orta, col_sag = st.columns([1, 2, 1])
            with col_sol:
                if aktif > 0:
                    if st.button("⬅️ Önceki", key="hoca_geri"):
                        st.session_state.hoca_aktif_sayfa -= 1
                        st.rerun()
            with col_sag:
                if aktif < len(sayfalar) - 1:
                    if st.button("Sonraki ➡️", key="hoca_ileri"):
                        st.session_state.hoca_aktif_sayfa += 1
                        st.rerun()

    with tab_sinav:
        st.markdown("#### 📝 Pratik Çalışma ve Sınav")
        
        col_r1, col_r2 = st.columns([2, 1])
        with col_r1:
            sinav_kaynagi = st.radio("Sınav Kaynağı:", ["📚 AI Kütüphane", "📂 Kişisel Notlarım"], horizontal=True)
        with col_r2:
            sinav_tipi = st.selectbox("Sınav Tipi", ["Çoktan Seçmeli", "Klasik (Açık Uçlu)"])
            soru_sayisi = st.slider("Soru Sayısı", 1, 10, 3)

        st.markdown("---")

        baslat_tiklandi = False
        aktif_konu = ""
        aktif_not = ""

        if sinav_kaynagi == "📚 AI Kütüphane":
            mufredat = AkademikEngine.get_akademik_mufredat()
            col1, col2 = st.columns(2)
            with col1:
                secilen_sinif = st.selectbox("Sınıf", list(mufredat.keys()), key="s_sinif")
            with col2:
                secilen_ders = st.selectbox("Ders", [d['isim'] for d in mufredat[secilen_sinif]], key="s_ders")
            aktif_konu = secilen_ders
            if st.button("🔥 Sınavı Başlat", use_container_width=True):
                baslat_tiklandi = True
        else:
            mevcut_notlar = AkademikEngine.yuklenen_notlari_getir()
            if not mevcut_notlar:
                st.warning("⚠️ Not bulunamadı.")
            else:
                secilen_not_adi = st.selectbox("Not Seçiniz:", options=mevcut_notlar)
                aktif_konu = st.text_input("Konu (İsteğe Bağlı):", placeholder="Örn: Kusurluluk")
                if st.button("🔥 Sınavı Başlat", use_container_width=True):
                    aktif_not = AkademikEngine.not_icerigi_getir(secilen_not_adi)
                    baslat_tiklandi = True

        if baslat_tiklandi:
            with st.spinner("Hoca sınavı hazırlıyor..."):
                sonuc = AkademikSinavEngine.pratik_calisma_uret(MY_API_KEY, aktif_konu, aktif_not, sinav_tipi, soru_sayisi)
                if "hata" in sonuc:
                    st.error(f"Hata: {sonuc['hata']}")
                else:
                    st.session_state.su_anki_sinav = sonuc
                    st.rerun()

        if st.session_state.get('su_anki_sinav'):
            sinav = st.session_state.su_anki_sinav
            st.info(f"📖 OLAY: {sinav['olay_kurgusu']}")
            
            for i, soru_data in enumerate(sinav.get('sorular', [])):
                st.markdown(f"**Soru {i+1}:** {soru_data['soru']}")
                
                if sinav_tipi == "Çoktan Seçmeli":
                    secim_cvp = st.radio("Seçenekler:", soru_data['secenekler'], key=f"q_{i}")
                    if st.button(f"Kontrol Et {i+1}", key=f"b_{i}"):
                        if secim_cvp == soru_data['cevap']:
                            st.success("✅ Doğru!")
                        else:
                            st.error(f"❌ Yanlış! Doğrusu: {soru_data['cevap']}")
                else:
                    cevap = st.text_area("Cevabını yaz:", key=f"ans_{i}")
                    if st.button("Hoca Puanlasın!", key=f"puan_{i}"):
                        with st.spinner("Hoca kağıdı okuyor..."):
                            puan_sonucu = AkademikSinavEngine.sinav_degerlendir(MY_API_KEY, soru_data['soru'], cevap, soru_data['analiz'])
                            st.metric("Puan", f"{puan_sonucu['puan']}/100")
                            st.write(f"**Hoca'nın Yorumu:** {puan_sonucu['gercekce']}")

# ==========================================
# 📝 ARZUHAL MODÜLÜ
# ==========================================
elif st.session_state.aktif_ekran == "📝 Arzuhal(Dilekçe Yazım Merkezi)":
    st.header("⚖️ Dilekçe Marketi")
    st.markdown("""
        <style>
        div[data-testid="stForm"] { background-color: #161616; padding: 25px; border-radius: 12px; border: 1px solid #333; }
        </style>
    """, unsafe_allow_html=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        kategori = st.selectbox("Kategori Seçin:", list(DilekceEngine.DILEKCE_KATALOGU.keys()))
    with col_b:
        tur = st.selectbox("Dilekçe Türü:", list(DilekceEngine.DILEKCE_KATALOGU[kategori].keys()))
    
    st.markdown("---")
    
    gerekli_alanlar = DilekceEngine.DILEKCE_KATALOGU[kategori][tur]
    form_verileri = {}
    
    with st.form("arzuhal_form"):
        st.subheader(f"📋 {tur} Detayları")
        cols = st.columns(2)
        for i, alan in enumerate(gerekli_alanlar):
            col = cols[i % 2]
            with col:
                if "Tarihi" in alan:
                    form_verileri[alan] = str(st.date_input(f"{alan}"))
                elif "Sayısı" in alan or "Miktarı" in alan:
                    form_verileri[alan] = str(st.number_input(f"{alan}", min_value=0, step=1))
                elif "Detay" in alan or "Özeti" in alan or "Gerekçe" in alan:
                    form_verileri[alan] = st.text_area(f"{alan}:", height=120)
                else:
                    form_verileri[alan] = st.text_input(f"{alan}:")
        
        submitted = st.form_submit_button("🚀 Dilekçeyi Hazırla", use_container_width=True)
    
    if submitted:
        if all(form_verileri.values()):
            with st.spinner("Hukuki taslak oluşturuluyor..."):
                taslak_metin = DilekceEngine.dilekce_uret(MY_API_KEY, tur, form_verileri)
                st.session_state.son_dilekce = taslak_metin
                st.session_state.son_dilekce_turu = tur
        else:
            st.warning("Lütfen tüm alanları doldurunuz ustam!")

    if "son_dilekce" in st.session_state:
        st.markdown("### 📄 JUNILEX Dilekçe Taslağı:")
        st.text_area("Taslak Metin", value=st.session_state.son_dilekce, height=400)
        word_data = DilekceEngine.word_dosyasi_yap(st.session_state.son_dilekce)
        
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "📥 Word Dosyası Olarak Kaydet", 
                data=word_data, 
                file_name=f"{st.session_state.son_dilekce_turu}_taslak.docx", 
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                use_container_width=True
            )
        with c2:
            if st.button("💾 Dilekçeyi Arşive Kaydet", use_container_width=True):
                basarili, mesaj = junilex_arsive_kaydet("📝 Dilekçe", st.session_state.son_dilekce_turu, st.session_state.son_dilekce)
                if basarili:
                    st.success("✅ Dilekçe arşive kaydedildi! Chat kısmından seçip üzerinde çalışmaya devam edebilirsin.")

# ==========================================
# ⚖️ İÇTİHAT MODÜLÜ
# ==========================================
elif st.session_state.aktif_ekran == "⚖️ İçtihat Sorgulama":
    st.header("⚖️ İçtihat ve Emsal Merkezi")
    
    tab1, tab2 = st.tabs(["🔍 Karar Analizi (Şerh)", "🔎 Emsal Karar Bulucu"])
    
    with tab1:
        st.subheader("⚖️ Karar Analiz Modülü")
        karar_metni = st.text_area("Yargıtay Karar Metnini Buraya Yapıştırın", height=250, key="karar_text_area")
        soru_input = st.text_input("Bu kararla ilgili neyi merak ediyorsunuz?", placeholder="Örn: İspat yükü kime verilmiş?", key="karar_soru_input")
        
        if st.button("⚖️ Analiz Et", use_container_width=True, key="btn_analiz_et"):
            if karar_metni and soru_input:
                with st.spinner("Hakim Junilex dosyayı inceliyor..."):
                    response = IctihatEngine.karar_analiz_et(MY_API_KEY, karar_metni, soru_input)
                    tam_metn = ""
                    if isinstance(response, str):
                        tam_metn = response
                    else:
                        for chunk in response:
                            try:
                                if hasattr(chunk, "text") and chunk.text:
                                    tam_metn += chunk.text
                            except: continue
                    
                    if tam_metn:
                        st.session_state.analiz_sayfalari = metni_sayfalara_bol(tam_metn, 1200)
                        st.session_state.analiz_aktif_sayfa = 0
                        st.rerun()
                    else:
                        st.error("Analiz sonucu boş döndü, lütfen tekrar deneyin.")

        if "analiz_sayfalari" in st.session_state and st.session_state.analiz_sayfalari:
            sayfalar = st.session_state.analiz_sayfalari
            aktif = st.session_state.analiz_aktif_sayfa
            
            st.markdown(f"""
            <div style="background-color: #fdfaf1; padding: 30px; border-left: 10px solid #5d4037; border-radius: 5px; color: #2c3e50; font-family: 'Georgia', serif;">
                <div style="font-size: 12px; color: #8d6e63; font-weight: bold; text-transform: uppercase;">🏛️ Analiz Şerhi - Sayfa {aktif + 1} / {len(sayfalar)}</div>
                <div style="font-size: 16px; line-height: 1.7; text-align: justify; margin-top: 15px;">
                    {sayfalar[aktif].replace("\n", "<br>")}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if aktif > 0:
                    if st.button("⬅️ Geri", key="analiz_geri_btn"):
                        st.session_state.analiz_aktif_sayfa -= 1
                        st.rerun()
            with c3:
                if aktif < len(sayfalar) - 1:
                    if st.button("İleri ➡️", key="analiz_ileri_btn"):
                        st.session_state.analiz_aktif_sayfa += 1
                        st.rerun()
            
            st.markdown("---")
            if st.button("💾 Bu Şerhi JUNILEX Arşivine Kaydet", key="btn_kaydet_serh"):
                tam_metin = "\n".join(st.session_state.analiz_sayfalari)
                basarili, mesaj = junilex_arsive_kaydet("⚖️ İçtihat Şerhi", "Karar Analizi", tam_metin)
                if basarili:
                    st.success("✅ Arşive kaydedildi! JUNILEX Chat menüsünden ulaşıp üzerinde konuşabilirsiniz.")

    with tab2:
        st.subheader("🔎 Yargıtay Yönelim Analizi")
        
        olay_input = st.text_area(
            "Hukuki Olayı Detaylıca Anlatın", 
            height=150, 
            placeholder="Örn: Banka hesabından rıza dışı para çekilmesi...", 
            key="emsal_olay_girdisi_v4" 
        )
        
        if st.button("🔎 Analiz Et", use_container_width=True, key="btn_emsal_bul_v4"):
            if olay_input: 
                with st.spinner("Junilex kütüphaneleri tarıyor ve analiz ediyor..."):
                    try:
                        sonuc = IctihatEngine.emsal_ara(MY_API_KEY, SERPER_API_KEY, olay_input)
                        if sonuc:
                            st.session_state.kitap_sayfalari = metni_sayfalara_bol(sonuc, 1200)
                            st.session_state.aktif_sayfa = 0
                            st.rerun()
                        else:
                            st.error("⚠️ Analiz sonucu boş döndü.")
                    except Exception as e:
                        st.error(f"⚠️ Teknik bir hata oluştu: {e}")
            else:
                st.warning("Ustam, önce bir olay anlatman lazım.")

        if "kitap_sayfalari" in st.session_state and st.session_state.kitap_sayfalari:
            st.markdown("---")
            sayfalar_emsal = st.session_state.kitap_sayfalari
            aktif_emsal = st.session_state.aktif_sayfa
            
            st.markdown(f"""
            <div style="background-color: #fdfaf1; padding: 30px; border-left: 10px solid #5d4037; border-radius: 5px; color: #2c3e50; font-family: 'Georgia', serif;">
                <div style="font-size: 12px; text-transform: uppercase; color: #8d6e63; margin-bottom: 10px; font-weight: bold;">🏛️ Yargıtay Yönelim Şerhi - Sayfa {aktif_emsal + 1} / {len(sayfalar_emsal)}</div>
                <div style="font-size: 16px; line-height: 1.8; text-align: justify;">{sayfalar_emsal[aktif_emsal].replace("\n", "<br>")}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if aktif_emsal > 0:
                    if st.button("⬅️ Geri", key="emsal_nav_geri"):
                        st.session_state.aktif_sayfa -= 1
                        st.rerun()
            with c3:
                if aktif_emsal < len(sayfalar_emsal) - 1:
                    if st.button("İleri ➡️", key="emsal_nav_ileri"):
                        st.session_state.aktif_sayfa += 1
                        st.rerun()
            
            st.markdown("---")
            if st.button("💾 Bu Emsal Analizini Arşive Kaydet", key="btn_kaydet_emsal"):
                tam_metin = "\n".join(st.session_state.kitap_sayfalari)
                basarili, mesaj = junilex_arsive_kaydet("🔎 Emsal Yönelim", "Emsal Analizi", tam_metin)
                if basarili:
                    st.success("✅ Arşive kaydedildi! JUNILEX Chat menüsünden ulaşıp kullanabilirsiniz.")

# ==========================================
# 💬 CHAT MODÜLÜ
# ==========================================
elif st.session_state.aktif_ekran == "💬 JUNILEX Chat":
    st.header("💬 JUNILEX Chat")
    
    col_chat, col_context = st.columns([3, 1])

    with col_context:
        st.markdown("### 🗂️ Bağlam Arşivi")
        
        db = get_db()
        
        kategori_secim = st.selectbox("Kategori Seçin:", ["Seçiniz...", "🏛️ Adliye (Mevzuat)", "🎓 Akademi (PDF)", "📝 Dilekçe", "⚖️ İçtihat"])
        
        if kategori_secim != "Seçiniz...":
            arsiv_secenekleri = {}
            
            try:
                if kategori_secim == "🎓 Akademi (PDF)":
                    notlar_ref = db.collection("ders_notlari").get()
                    for doc in notlar_ref:
                        d = doc.to_dict()
                        arsiv_secenekleri[d.get('dosya_adi', 'Adsız')] = d.get('metin')
                else:
                    kategori_map = {"🏛️ Adliye (Mevzuat)": "🏛️ Mevzuat Şerhi", "📝 Dilekçe": "📝 Dilekçe", "⚖️ İçtihat": "⚖️ İçtihat Şerhi"}
                    filtre = kategori_map.get(kategori_secim)
                    
                    if st.session_state.aktif_kullanici:
                        docs = db.collection("junilex_arsiv").where("kullanici", "==", st.session_state.aktif_kullanici).where("kategori", "==", filtre).get()
                        for doc in docs:
                            d = doc.to_dict()
                            arsiv_secenekleri[d.get('baslik', 'Adsız Başlık')] = d.get('metin')
            except Exception as e:
                st.error("Arşiv yüklenirken hata.")

            if arsiv_secenekleri:
                secilen_belge = st.selectbox("Belgeyi Seç:", list(arsiv_secenekleri.keys()))
                if st.button("📌 Masaya Koy", use_container_width=True):
                    st.session_state.aktif_dosya = f"{kategori_secim} | {secilen_belge}"
                    st.session_state.islenmis_not = arsiv_secenekleri[secilen_belge]
                    st.rerun()
            else:
                st.warning("Bu kategoride kayıt bulunamadı.")
            
        if st.session_state.get('aktif_dosya'):
            st.divider()
            st.success(f"**Aktif:** {st.session_state.aktif_dosya}")
            if st.button("🗑️ Masayı Temizle", use_container_width=True):
                st.session_state.aktif_dosya = None
                st.session_state.islenmis_not = None
                st.rerun()

    with col_chat:
        for message in st.session_state.chat_messages:
            simge = "https://api.dicebear.com/9.x/micah/png?seed=OzanSahinSicim&backgroundColor=transparent" if message["role"] == "user" else "https://api.dicebear.com/9.x/bottts-neutral/png?seed=Junilex&backgroundColor=0f172a"
            with st.chat_message(message["role"], avatar=simge):
                st.markdown(message["content"])

        st.markdown("---")
        with st.popover(f"🧠 Mod: {st.session_state.chat_mode}", use_container_width=True):
            secilen_mod = st.radio("Zeka Yapılandırması:", ["Özet", "⚖️ Detaylı Analiz"])
            if secilen_mod != st.session_state.chat_mode:
                st.session_state.chat_mode = secilen_mod
                st.rerun()

        if prompt := st.chat_input("Mesajınızı yazın..."):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant", avatar="https://api.dicebear.com/9.x/bottts-neutral/png?seed=Junilex&backgroundColor=0f172a"):
                message_placeholder = st.empty()
                full_response = ""
                
                try:
                    response = ChatEngine.yanit_uret(
                        MY_API_KEY, 
                        st.session_state.chat_messages[:-1], 
                        prompt, 
                        mod=st.session_state.chat_mode,
                        aktif_belge_metni=st.session_state.get('islenmis_not', None)
                    )
                    
                    for chunk in response:
                        if hasattr(chunk, "text") and chunk.text:
                            full_response += chunk.text
                            message_placeholder.markdown(full_response + " ▌")
                    message_placeholder.markdown(full_response)
                    
                    st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    st.error(f"Sistem Hatası: {e}")
# ==========================================
# 🧮 PRATİK HESAPLAMALAR
# ==========================================
elif st.session_state.aktif_ekran == "🧮 Pratik Hesaplamalar":
    st.title("🧮 Hukuki Pratik Hesaplamalar")
    st.markdown("Günlük ofis işlerinizde vakit kazandıracak hızlı hesaplama araçları.")
    
    # 5 sekmeye çıkardık
    tab_smm, tab_faiz, tab_isci, tab_harc, tab_kademeli = st.tabs([
        "🧾 SMM", "📈 Faiz", "💼 İşçilik Alacakları", "⚖️ Harç", "📊 AAÜT / Kademeli"
    ])
    
    # --- 1. SMM HESAPLAYICI ---
    with tab_smm:
        st.subheader("Serbest Meslek Makbuzu (SMM) Hesaplayıcı")
        st.info("KDV %20 ve Stopaj %20 üzerinden hesaplanmaktadır.")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            hesap_tipi = st.selectbox("Anlaşma Tipi", ["Netten Brüte (KDV Hariç Anlaşma)", "Brütten Nete"])
            tutar = st.number_input("Tutar (₺)", min_value=0.0, value=10000.0, step=500.0)
            
            if st.button("Makbuzu Hesapla", type="primary"):
                sonuc = HesapEngine.smm_hesapla(tutar, hesap_tipi)
                
                st.divider()
                st.markdown("### 📊 Hesaplama Sonucu")
                
                c_brut, c_kdv, c_stopaj = st.columns(3)
                c_brut.metric("Brüt Ücret", f"₺{sonuc['Brüt Ücret']:,.2f}")
                c_kdv.metric("KDV (%20)", f"₺{sonuc['KDV (%20)']:,.2f}")
                c_stopaj.metric("Stopaj (%20)", f"₺{sonuc['Stopaj (%20)']:,.2f}")
                
                st.success(f"**Avukata Kalan Net:** ₺{sonuc['Avukata Kalan Net']:,.2f}")
                st.warning(f"**Müvekkilden Tahsil Edilecek Toplam:** ₺{sonuc['Müvekkilden Tahsil Edilecek Toplam (Net + KDV)']:,.2f}")

    # --- 2. FAİZ HESAPLAYICI ---
    with tab_faiz:
        st.subheader("Gün Bazlı Faiz Hesaplayıcı")
        
        col_anapara, col_oran = st.columns(2)
        with col_anapara:
            anapara = st.number_input("Anapara (₺)", min_value=0.0, value=50000.0, step=1000.0)
        with col_oran:
            faiz_orani = st.number_input("Yıllık Faiz Oranı (%)", min_value=0.0, value=9.0, step=1.0, help="Yasal faiz %9, Avans faizi değişkenlik gösterir.")
            
        col_bas, col_bit = st.columns(2)
        with col_bas:
            import datetime
            baslangic = st.date_input("Başlangıç (Temerrüt) Tarihi", value=datetime.date(2023, 1, 1))
        with col_bit:
            bitis = st.date_input("Bitiş (Hesap) Tarihi", value=datetime.date.today())
            
        if st.button("Faizi Hesapla", type="primary"):
            gun, faiz_miktari, toplam = HesapEngine.faiz_hesapla(anapara, faiz_orani, baslangic, bitis)
            
            if gun < 0:
                st.error("Bitiş tarihi, başlangıç tarihinden önce olamaz!")
            else:
                st.divider()
                st.markdown(f"Geçen Süre: **{gun} Gün**")
                
                c_ana, c_faiz, c_top = st.columns(3)
                c_ana.metric("Anapara", f"₺{anapara:,.2f}")
                c_faiz.metric("İşleyen Faiz", f"₺{faiz_miktari:,.2f}")
                c_top.metric("Toplam Alacak", f"₺{toplam:,.2f}")
    # --- 3. İŞÇİLİK ALACAKLARI HESAPLAYICI ---
    with tab_isci:
        st.subheader("Kıdem ve İhbar Tazminatı Hesaplayıcı")
        st.info("Kıdem tavanını güncel resmi gazete verisine göre değiştirebilirsiniz.")
        
        c_maas, c_tavan = st.columns(2)
        with c_maas: brut_maas = st.number_input("Brüt Maaş (₺)", value=20002.50, step=500.0)
        with c_tavan: kidem_tavani = st.number_input("Güncel Kıdem Tavanı (₺)", value=35058.58, step=1000.0)
            
        c_giris, c_cikis = st.columns(2)
        import datetime
        with c_giris: ise_giris = st.date_input("İşe Giriş Tarihi", value=datetime.date(2020, 1, 1))
        with c_cikis: isten_cikis = st.date_input("İşten Çıkış Tarihi", value=datetime.date.today())
            
        if st.button("Tazminatları Hesapla", type="primary", use_container_width=True):
            sonuc = HesapEngine.iscil_alacaklar_hesapla(brut_maas, kidem_tavani, ise_giris, isten_cikis)
            if "Hata" in sonuc:
                st.error(sonuc["Hata"])
            else:
                st.divider()
                st.write(f"⏱️ **Kıdeme Esas Süre:** {sonuc['Çalışılan Gün']} Gün | **İhbar Süresi:** {sonuc['İhbar Süresi (Hafta)']} Hafta")
                m1, m2 = st.columns(2)
                m1.metric("Net Kıdem Tazminatı", f"₺{sonuc['Kıdem Net']:,.2f}")
                m2.metric("Net İhbar Tazminatı", f"₺{sonuc['İhbar Net']:,.2f}")

    # --- 4. NİSPİ HARÇ HESAPLAYICI ---
    with tab_harc:
        st.subheader("Peşin Harç Hesaplayıcı (Binde 68.31)")
        dava_degeri = st.number_input("Dava Değeri (Müddeabih) ₺", value=100000.0, step=10000.0)
        
        if st.button("Harç Hesapla", type="primary"):
            toplam, pesin = HesapEngine.nispi_harc_hesapla(dava_degeri)
            st.success(f"**Yatırılacak Peşin Harç (1/4):** ₺{pesin:,.2f}")
            st.caption(f"Toplam Karar ve İlam Harcı: ₺{toplam:,.2f}")

    # --- 5. KADEMELİ TARİFE (AAÜT) ---
    with tab_kademeli:
        st.subheader("Nispi Vekalet Ücreti Hesaplayıcı")
        st.write("2023-2024 AAÜT İcra/Dava dilimleri (Gerektiğinde koddaki oranları revize edin).")
        
        vekalet_tutari = st.number_input("Hükmedilen Tutar / Tahsilat (₺)", value=500000.0, step=50000.0)
        
        # Güncel AAÜT oranlarını list of dicts olarak UI'da tutuyoruz
        # İleride veritabanından dinamik çekilebilir
        aaut_dilimler = [
            {"limit": 200000, "oran": 0.16},
            {"limit": 200000, "oran": 0.15},
            {"limit": 400000, "oran": 0.14},
            {"limit": 600000, "oran": 0.11},
            {"limit": 1200000, "oran": 0.08},
            {"limit": 1600000, "oran": 0.05},
            {"limit": 1600000, "oran": 0.03},
            {"limit": 8000000, "oran": 0.02},
            {"limit": None, "oran": 0.01} # Üstü
        ]
        
        if st.button("Vekalet Ücreti Hesapla", type="primary"):
            ucret, detay = HesapEngine.kademeli_tarife_hesapla(vekalet_tutari, aaut_dilimler)
            st.success(f"**Hesaplanan Vekalet Ücreti:** ₺{ucret:,.2f}")
            with st.expander("Hesaplama Detayları"):
                for d in detay:
                    st.write(d)

# ==========================================
# 🧹 RAM TEMİZLİĞİ 
# ==========================================
gc.collect()
