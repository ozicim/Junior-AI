import streamlit as st
import firebase_admin
import random
import smtplib
from email.mime.text import MIMEText
from akademik_engine import AkademikEngine
from mevzuat_engine import MevzuatBulutEngine, YASAL_UYARI
from dilekce_engine import DilekceEngine
from akademik_sinav_modu import AkademikSinavEngine
from ictihat_engine import IctihatEngine
from chat_engine import ChatEngine
from fpdf import FPDF
from firebase_admin import firestore
import os
import urllib.request
import google.generativeai as genai
import streamlit as st
import json  
# Diğer importların (genai, ChatEngine vs.) burada kalmaya devam etsin...

# ==========================================
# 💾 KALICI VERİTABANI MOTORU (JSON)
# ==========================================
DB_DOSYASI = "kullanicilar.json"

def veritabani_yukle():
    # Eğer daha önce dosya açılmamışsa, yeni dosya yarat ve seni yönetici yap
    if not os.path.exists(DB_DOSYASI):
        baslangic_verisi = {"ozan@junilex.com": {"sifre": "123456", "isim": "Ozan Şahin Sicim"}}
        with open(DB_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(baslangic_verisi, f, ensure_ascii=False, indent=4)
        return baslangic_verisi
    # Dosya varsa içindekileri oku
    with open(DB_DOSYASI, "r", encoding="utf-8") as f:
        return json.load(f)

def veritabani_kaydet(veri):
    # Yeni biri kayıt olduğunda dosyayı fiziksel olarak güncelle
    with open(DB_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

# ==========================================
# 📧 E-POSTA GÖNDERME MOTORU
# ==========================================
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
    except Exception as e:
        return False, str(e)

# ==========================================
# 🔐 GÜVENLİK VE VERİTABANI BAŞLATMA
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "aktif_kullanici" not in st.session_state:
    st.session_state.aktif_kullanici = ""
    
# 🔴 YENİ: Veritabanını artık JSON dosyasından çekiyoruz
if "kullanici_veritabani" not in st.session_state:
    st.session_state.kullanici_veritabani = veritabani_yukle() 
    
if "onay_bekleyen" not in st.session_state:
    st.session_state.onay_bekleyen = None 

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
        
        # --- 1. GİRİŞ YAP SEKMESİ ---
        with tab_giris:
            giris_email = st.text_input("E-Posta Adresi", key="giris_email")
            giris_sifre = st.text_input("Şifre", type="password", key="giris_sifre")
            
            if st.button("🚀 Sisteme Giriş Yap", use_container_width=True):
                # Anlık olarak JSON'daki en güncel veriyi çekelim ki başka cihazdan kayıt olanları da görsün
                st.session_state.kullanici_veritabani = veritabani_yukle()
                
                if giris_email in st.session_state.kullanici_veritabani and st.session_state.kullanici_veritabani[giris_email]["sifre"] == giris_sifre:
                    st.session_state.logged_in = True
                    st.session_state.aktif_kullanici = st.session_state.kullanici_veritabani[giris_email]["isim"]
                    st.rerun() 
                else:
                    st.error("E-posta adresi veya şifre hatalı!")
                    
        # --- 2. YENİ KAYIT SEKMESİ ---
        with tab_kayit:
            # EĞER KOD GÖNDERİLMEDİYSE (İlk Form Ekranı)
            if st.session_state.onay_bekleyen is None:
                kayit_isim = st.text_input("İsim Soyisim", key="kayit_isim") 
                kayit_email = st.text_input("E-Posta Adresi", key="kayit_email")
                kayit_sifre = st.text_input("Yeni Şifre", type="password", key="kayit_sifre")
                kayit_sifre_tekrar = st.text_input("Şifre Tekrar", type="password", key="kayit_sifre_tekrar")
                
                if st.button("Kayıt Ol", use_container_width=True):
                    st.session_state.kullanici_veritabani = veritabani_yukle()
                    
                    if len(kayit_isim.strip()) < 3:
                        st.warning("⚠️ Lütfen geçerli bir İsim Soyisim giriniz!")
                    elif "@" not in kayit_email or "." not in kayit_email:
                        st.warning("⚠️ Lütfen geçerli bir e-posta adresi giriniz!")
                    elif kayit_email in st.session_state.kullanici_veritabani:
                        st.warning("Bu e-posta adresi zaten sisteme kayıtlı!")
                    elif kayit_sifre != kayit_sifre_tekrar:
                        st.error("Şifreler uyuşmuyor!")
                    elif len(kayit_sifre) < 6:
                        st.warning("Şifre en az 6 karakter olmalıdır.")
                    else:
                        uretilen_kod = str(random.randint(100000, 999999))
                        
                        with st.spinner("Onay kodu e-postanıza gönderiliyor..."):
                            basarili_mi, hata_mesaji = onay_kodu_gonder(kayit_email, uretilen_kod)
                        
                        if basarili_mi:
                            st.session_state.onay_bekleyen = {
                                "isim": kayit_isim.title(),
                                "email": kayit_email,
                                "sifre": kayit_sifre,
                                "kod": uretilen_kod
                            }
                            st.success("✅ Kod gönderildi! Lütfen e-postanızı kontrol edin.")
                            st.rerun()
                        else:
                            st.error(f"E-posta gönderilemedi! Teknik detay: {hata_mesaji}")
            
            # --- ONAY KODU EKRANI (Kod gönderildikten sonraki aşama) ---
            else:
                st.info(f"📧 **{st.session_state.onay_bekleyen['email']}** adresine 6 haneli bir doğrulama kodu gönderdik.")
                girilen_kod = st.text_input("Doğrulama Kodu", key="dogrulama_kodu", max_chars=6)
                
                # 3 Sütunlu modern buton dizilimi
                col_onay1, col_onay2, col_onay3 = st.columns(3)
                
                with col_onay1:
                    if st.button("✅ Kodu Doğrula", use_container_width=True):
                        if girilen_kod == st.session_state.onay_bekleyen["kod"]:
                            # 1. Veritabanına Kalıcı Kayıt
                            yeni_mail = st.session_state.onay_bekleyen["email"]
                            st.session_state.kullanici_veritabani[yeni_mail] = {
                                "sifre": st.session_state.onay_bekleyen["sifre"], 
                                "isim": st.session_state.onay_bekleyen["isim"]
                            }
                            veritabani_kaydet(st.session_state.kullanici_veritabani)
                            
                            # 2. Bekleme durumunu temizle ve başarıyı kutla
                            st.session_state.onay_bekleyen = None
                            st.balloons() 
                            st.success("🎉 Kayıt başarılı! Şimdi 'Giriş Yap' sekmesine geçerek JUNILEX'i kullanmaya başlayabilirsiniz.")
                        else:
                            # 🔴 HATALI KOD UYARISI
                            st.error("❌ Doğrulama kodu hatalı! Lütfen tekrar kontrol edin.")
                
                with col_onay2:
                    # 🔄 TEKRAR KOD GÖNDERME BUTONU
                    if st.button("🔄 Tekrar Kod Gönder", use_container_width=True):
                        yeni_kod = str(random.randint(100000, 999999))
                        with st.spinner("Yeni kod hazırlanıyor..."):
                            basarili, mesaj = onay_kodu_gonder(st.session_state.onay_bekleyen["email"], yeni_kod)
                        
                        if basarili:
                            st.session_state.onay_bekleyen["kod"] = yeni_kod
                            st.toast("✅ Yeni kod başarıyla gönderildi!", icon="📧")
                        else:
                            st.error(f"Kod gönderimi başarısız: {mesaj}")
                
                with col_onay3:
                    if st.button("⬅️ Bilgileri Düzenle", use_container_width=True):
                        st.session_state.onay_bekleyen = None
                        st.rerun()
    st.stop()

# ==========================================
# ✅ ANA UYGULAMA (SADECE GİRİŞ YAPANLAR GÖREBİLİR)
# ==========================================
st.sidebar.markdown(f"### 🧑‍💻 Hoş geldin, {st.session_state.aktif_kullanici}")
if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.aktif_kullanici = ""
    st.rerun()
st.sidebar.markdown("---")
try:
    AkademikEngine.veritabanini_baslat()
except Exception as e:
    st.error(f"Veritabanı başlatılamadı: {e}")


# 1. SAYFA AYARLARI
st.set_page_config(page_title="JUNIOR AI", page_icon="⚖️", layout="centered")

# --- API ANAHTARINI BURAYA YAZ ---
MY_API_KEY = st.secrets["GEMINI_API_KEY"]
SERPER_API_KEY = st.secrets["SERPER_API_KEY"]


# 2. SESSION STATE BAŞLATMA
if 'aktif_ekran' not in st.session_state:
    st.session_state.aktif_ekran = 'liste'
if 'secili_kanun' not in st.session_state:
    st.session_state.secili_kanun = None
if 'bulunan_madde' not in st.session_state:
    st.session_state.bulunan_madde = None
if 'arama_sonuclari' not in st.session_state:
    st.session_state.arama_sonuclari = []
if 'islenmis_not' not in st.session_state: 
    st.session_state.islenmis_not = None
if 'su_anki_sinav' not in st.session_state: 
    st.session_state.su_anki_sinav = None
    # --- SESSION STATE BAŞLATMA (GÜVENLİK KİLİDİ) ---
# Eğer bu anahtarlar yoksa, hata vermemesi için sıfır olarak tanımlıyoruz
if "aktif_sayfa" not in st.session_state:
    st.session_state.aktif_sayfa = 0
if "analiz_aktif_sayfa" not in st.session_state:
    st.session_state.analiz_aktif_sayfa = 0
if "akademi_aktif_sayfa" not in st.session_state:
    st.session_state.akademi_aktif_sayfa = 0
if "kitap_sayfalari" not in st.session_state:
    st.session_state.kitap_sayfalari = []
if "analiz_sayfalari" not in st.session_state:
    st.session_state.analiz_sayfalari = []
if "akademi_notlari" not in st.session_state:
    st.session_state.akademi_notlari = []


# 3. YARDIMCI FONKSİYONLAR
def ekran_degistir(yeni_ekran):
    st.session_state.aktif_ekran = yeni_ekran

def kanun_sec(kanun):
    st.session_state.secili_kanun = kanun
    st.session_state.bulunan_madde = None
    st.session_state.arama_sonuclari = []
    ekran_degistir('maddeSecim')
    
def metni_sayfalara_bol(metin, sayfa_boyutu=1000):
    """Metni belirtilen karakter sınırına göre sayfalara böler."""
    if not metin:
        return []
    # Paragrafları koruyarak bölmek daha estetiktir
    paragraflar = metin.split('\n')
    sayfalar = []
    suanki_sayfa = ""
        
    for p in paragraflar:
        if len(suanki_sayfa) + len(p) > sayfa_boyutu:
            sayfalar.append(suanki_sayfa.strip())
            suanki_sayfa = p + "\n"
        else:
            suanki_sayfa += p + "\n"
                
    if suanki_sayfa.strip():
        sayfalar.append(suanki_sayfa.strip())
    return sayfalar

# 4. CSS BLOĞU (TAŞMAYI ÖNLEYEN KESİN ÇÖZÜM)
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400..700;1,400..700&display=swap" rel="stylesheet">
    <style>
        /* Yazı Tipi */
        html, body, [class*="css"] { font-family: 'Lora', serif; }

        /* Başlık ve Logo Alanı */
        .header-container { text-align: center; padding: 20px 0; }
        .header-logo-svg { width: 100px; height: auto; margin: 0 auto 10px auto; display: block; }
        .main-title { font-size: 52px; font-weight: 800; color: #1A1A1A; letter-spacing: 6px; margin: 0; text-transform: uppercase; }
        .sub-title { color: #C5A059; font-weight: 600; letter-spacing: 4px; font-size: 14px; text-align: center; margin-bottom: 20px; }

        /* NOKTALI SİYAH KUTU */
        .madde-kutusu {
            background-color: #121212 !important;
            color: #FFFFFF !important;
            padding: 35px;
            border-radius: 12px;
            border: 2px solid #C5A059;
            background-image: radial-gradient(#2a2a2a 2px, transparent 2px) !important;
            background-size: 25px 25px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            margin: 25px 0;
            line-height: 1.8;
        }

        .madde-baslik { 
            color: #C5A059 !important; 
            font-weight: 700; 
            font-size: 24px; 
            border-bottom: 1px solid #333; 
            padding-bottom: 15px; 
            margin-bottom: 20px; 
            text-align: left;
        }

        .madde-icerik p { margin-bottom: 15px; color: #f0f0f0 !important; }

        /* Akademik Hoca Kutusu */
        .hoca-anlatim-kutusu {
            background-color: #fdf6e3;
            padding: 25px;
            border-radius: 12px;
            border-left: 8px solid #C5A059;
            color: #2c3e50;
            line-height: 1.7;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            margin-top: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# # 5. KENAR ÇUBUĞU (SIDEBAR)
# ==========================================
with st.sidebar:
    st.title("⚖️ Junilex AI")
    # Kullanıcının seçtiği departmanı 'secim' değişkenine eşitliyoruz
    secim = st.radio(
        "Lütfen bir departman seçin:",
        [
            "🏛️ Adliye (Mevzuat Sorgu)", 
            "🎓 Akademi (Ders Notları)", 
            "📝 Arzuhal(Dilekçe Yazım Merkezi)",
            "⚖️ İçtihat Sorgulama", 
            "💬 JUNILEX Chat"
        ]
    )
    st.divider()
    st.info("Ozan Şahin Sicim | JUNILEX AI v2.0")
    
   

# ==========================================
# # 6. LOGO VE ÜST BAŞLIK (HER SAYFADA ORTAK)
# ==========================================
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


# ==========================================
# 🧭 DEPARTMAN KONTROL PANELİ (IF-ELIF ZİNCİRİ)
# ==========================================

if secim == "🏛️ Adliye (Mevzuat Sorgu)":
    st.title("🏛️ Junilex Akıllı Mevzuat Bankası")
    st.markdown("Kategori filtreli kanun kütüphanesi. Maddeleri numarayla çağırabilir veya içinde geçen kelimelerle aratabilirsiniz.")

    kanun_listesi = MevzuatBulutEngine.get_kanunlar()

    # 1. Kategori ve Kanun Seçim Paneli
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

    # 2. SEKMELİ ARAMA MOTORU MİMARİSİ
    arama_sekmeleri = st.tabs(["🔢 Madde Numarası İle Nokta Atışı", "🔤 Kelime / Kavram İle İçerik Taraması"])

    # --------------------------------------------------------
    # TAB 1: MADDE NUMARASI İLE ARAMA
    # --------------------------------------------------------
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
                        api_key = MY_API_KEY if 'MY_API_KEY' in locals() else st.secrets["GEMINI_API_KEY"]
                        akış = MevzuatBulutEngine.madde_analiz_et(api_key, secilen_kanun['kisaAd'], st.session_state["aktif_no_madde"], res.get("metin"))
                        if akış: st.write_stream(akış)

    # --------------------------------------------------------
    # TAB 2: KELİME İLE MEVZUAT TARAMASI
    # --------------------------------------------------------
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
                # Her bir eşleşen maddeyi şık akordeon (expander) içinde saklıyoruz
                with st.expander(f"📜 {m['baslik']}"):
                    st.info(m['metin'])
                    
                    # Her expander'ın içine bağımsız çalışan bir AI analiz butonu yerleştiriyoruz
                    if st.button("🏛️ Bu Maddeyi Yapay Zekaya Analiz Ettir", key=f"btn_analiz_k_{m['no']}_{i}"):
                        with st.spinner("🔮 Madde analiz ediliyor..."):
                            api_key = MY_API_KEY if 'MY_API_KEY' in locals() else st.secrets["GEMINI_API_KEY"]
                            akış = MevzuatBulutEngine.madde_analiz_et(api_key, secilen_kanun['kisaAd'], m['no'], m['metin'])
                            if akış: st.write_stream(akış)
           

    if "aktif_madde" in st.session_state:
        madde = st.session_state.aktif_madde
        st.markdown("---")
        st.subheader(f"📜 {madde['kanun_adi']} — Madde {madde['madde_no']}")
        st.markdown(f"**Başlık:** {madde['baslik']}")

        # Madde metni siyah kutu
        st.markdown(f"""
        <div class="madde-kutusu">
            <div class="madde-baslik">📋 MADDE {madde['madde_no']} — {madde['baslik'].upper()}</div>
            <div class="madde-icerik"><p>{madde['metin'].replace(chr(10), '<br>')}</p></div>
        </div>
        """, unsafe_allow_html=True)

        # Kaynak bağlantısı
        resmi_url = f"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={madde['kanun_no']}&MevzuatTur=1&MevzuatTertip=5"
        st.caption(f"📌 Resmi kaynak: [mevzuat.gov.tr]({resmi_url}) — Hukuken bağlayıcı metin için bu adresi ziyaret edin.")

        st.markdown("---")
        ozel_soru = st.text_input(
            "Bu maddeye ilişkin özel bir sorunuz var mı? (İsteğe bağlı)",
            placeholder="Örn: Bu madde kapsamında zamanaşımı süresi nedir?",
            key="adliye_ozel_soru"
        )
        if st.button("🤖 Maddeyi JUNILEX AI ile Analiz Et", use_container_width=True, type="primary"):
            with st.spinner("JUNILEX yapay zekası maddeyi yorumluyor..."):
                analiz_sonucu = MevzuatBulutEngine.madde_analiz_et(
                    api_key=MY_API_KEY,
                    madde_metni=madde["metin"],
                    kanun_adi=madde["kanun_adi"],
                    madde_no=madde["madde_no"],
                    soru=ozel_soru
                )
            st.markdown("### 🧠 JUNILEX Yapay Zeka Analiz Raporu")
            st.markdown(f"""
            <div class="hoca-anlatim-kutusu">
                {analiz_sonucu.replace(chr(10), '<br>')}
            </div>
            """, unsafe_allow_html=True)
            # Analiz altına da uyarı ekle
            st.caption("⚠️ Yapay zeka analizi hukuki danışmanlık değildir. Kesin bilgi için avukat veya resmi kaynaklara başvurunuz.")

 # ============================================================
    # 🔑 GELİŞTİRİCİ PANELİ (YENİ NESİL CHROMADB VE ZIP SİSTEMİ)
    # ============================================================
    if st.session_state.get("aktif_kullanici") == "Ozan Şahin Sicim":
        st.write("<br><br><br>", unsafe_allow_html=True)
        with st.expander("🔑 JUNILEX Geliştirici — Kalıcı Hafızaya Kazıma Paneli", expanded=False):
            hedef_kanun_adi = st.selectbox(
                "Yapay Zeka Hafızasına Alınacak Kanun",
                options=[k["isim"] for k in kanun_listesi],
                key="admin_yerel_secim"
            )
            hedef_kanun = next(k for k in kanun_listesi if k["isim"] == hedef_kanun_adi)

            if st.button("⚡ Seçilen Kanunu Junilex Yerel Beynine (ChromaDB) Kazı", use_container_width=True):
                with st.spinner(f"🧠 {hedef_kanun['kisaAd']} maddeleri çözülüyor ve yapay zeka beynine kazınıyor..."):
                    try:
                        # Yeni esnek motorumuzu çağırıyoruz (Firebase veya kilit.json bağımlılığı tamamen bitti)
                        adet = MevzuatBulutEngine.kanunu_buluta_yukle(
                            id=hedef_kanun["id"], 
                            kisa_ad=hedef_kanun["kisaAd"]
                        )
                        if adet > 0:
                            st.success(f"🚀 Muhteşem! {adet} adet {hedef_kanun['kisaAd']} maddesi başarıyla Junilex hafızasına işlendi ve kullanıma hazır.")
                    except Exception as e:
                        st.error(f"❌ Yerel Vektörleştirme Hatası: {str(e)}")

# 💬 Buradan aşağıya diğer elif secim == "🎓 Akademi (Ders Notları)": vs. sekmelerin devam edebilir dayı...
# --- MOD 2: AKADEMİ ---
# app.py içinde İçtihat veya Akademi butonunun tam içine:
elif secim == "🎓 Akademi (Ders Notları)":
    st.header("🎓 Akademik Asistan")
    
    # Sekmeleri net bir şekilde tanımlıyoruz
    tab_mufredat, tab_notlar, tab_sinav = st.tabs(["📚 Müfredat", "📄 Notlarım", "📝 Sınav Modu"])
    mufredat_sozlugu = AkademikEngine.get_akademik_mufredat()
    ders_listesi = []
    for sinif_adi, dersler in mufredat_sozlugu.items():
        for ders in dersler:
        # İkon ve isim birleştirerek listeye ekle (Örn: "📜 Hukuk Başlangıcı")
            ders_listesi.append(f"{ders['ikon']} {ders['isim']}")
            
    konu_listesi = ["Genel Tanımlar", "Hoca Notları", "Özet Analiz"]
    
    # ==========================================
    # 1. SEKME: MÜFREDAT (Ders Listesi)
    # ==========================================
    with tab_mufredat:
        st.subheader("📚 Ders ve Konu Seçimi")
        col1, col2 = st.columns(2)
        with col1:
            secilen_ders = st.selectbox("Ders Seçiniz", options=ders_listesi, key="akademi_ders_v3")
        with col2:
            secilen_konu = st.selectbox("Konu Seçiniz", options=konu_listesi, key="akademi_konu_v3")
        
        akademik_input = st.text_area("Eklemek istediğiniz ders notları veya sorular (Opsiyonel)", height=100, key="akademi_text")

        if st.button("📚 Notları Analiz Et / Özetle", use_container_width=True):
            try:
                # Spinner yerine bilgi mesajı veriyoruz, çünkü akışı aşağıda canlı göreceğiz
                st.info("🏛️ Profesör kürsüye çıkıyor, Junilex arşivi inceleniyor...")
                
                # AKADEMİK MOTORU KULLANIYORUZ
                from akademik_engine import AkademikEngine
                
                # Motoru çağır (Bize kelime kelime akacak bir jeneratör döndürüyor)
                cevap_generator = AkademikEngine.mufredat_hoca_anlat(
                    MY_API_KEY, 
                    SERPER_API_KEY, 
                    secilen_ders, 
                    secilen_konu, 
                    akademik_input
                )
                
                # 🌟 İŞTE SİHİR BURADA: st.write_stream yazıyı canlı akıtır ve bitince tam metni sonuc'a atar
                sonuc = st.write_stream(cevap_generator)
                
                # Gelen sonuç bir hata mesajı (⚠️) değilse sayfalama işlemini yap
                if sonuc and not sonuc.startswith("⚠️"):
                    # Sonucu sayfalara böl ve hafızaya al
                    st.session_state.akademi_notlari = metni_sayfalara_bol(sonuc, 300)
                    st.session_state.akademi_aktif_sayfa = 0
                    st.success("✅ Ders notları kitabınıza eklendi! Sayfanın altından okuyabilirsiniz.")
                    
                    # NOT: Burada eskiden st.rerun() vardı. Onu kaldırdım. 
                    # Çünkü sayfa yenilenirse az önce canlı akan yazı anında ekrandan kaybolur. 
                    # Artık kullanıcı yazının akışını izleyecek, bitince alt taraftaki kitabında da görecek.
                else:
                    st.error("AI bir sonuç döndürmedi veya arşivde not bulunamadı.")
            except Exception as e:
                st.error(f"Hoca derse giremedi ustam: {e}")
        # --- DİJİTAL KİTAP GÖRÜNÜMÜ (PRESTİGE ŞERH - KESİN ÇÖZÜM) ---
        if "akademi_notlari" in st.session_state and st.session_state.akademi_notlari:
            import re
            
            sayfalar = st.session_state.akademi_notlari
            aktif = st.session_state.get('akademi_aktif_sayfa', 0)
            
            # 1. METİN TEMİZLİĞİ (Alt Başlık Hizalaması ve Kitap Boyutu)
            icerik = sayfalar[aktif]
            
            # 1. SADECE ANA BAŞLIĞI (###) yakala, altına ekstra bir <br> (Enter) koy
            icerik = re.sub(r"#{3}\s+(.*?)(?=\n|$)", r"<h3 style='color:#1b5e20; font-family:Georgia; border-bottom: 2px solid #2e7d32; padding-bottom:5px; margin-top:20px; font-size:18px;'>\1</h3><br>", icerik)
            
            # 2. AI'ın attığı GEREKSİZ BÜYÜK başlıkları (# veya ##) ezip normal kalın yazı yapıyoruz!
            icerik = re.sub(r"#{1,2}\s+(.*?)(?=\n|$)", r"<br><br><b style='color:#3e2723; font-size:16px;'>\1</b><br>", icerik)
            icerik = re.sub(r"#{4,5}\s+(.*?)(?=\n|$)", r"<br><b style='color:#3e2723; font-size:15px;'>\1</b><br>", icerik)
            
            # 3. NUMARALI MADDELERİ (Örn: **1. Teorik Çerçeve:**) YAKALA: Önüne net bir Enter (<br><br>) at!
            icerik = re.sub(r"\n\s*\*\*(.*?)\*\*", r"<br><br><b>\1</b>", icerik)
            
            # 4. Cümle içinde kalan diğer kalın yazıları düzelt
            icerik = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", icerik)
            
            # 5. Özel kutulara nefes aldır (Önlerine boşluk koyduk)
            icerik = icerik.replace("🔍 GERÇEK EMSAL:", "<br><br><b style='color:#2e7d32;'>🔍 GERÇEK EMSAL:</b>")
            icerik = icerik.replace("⚖️ HUKUKİ DAYANAK:", "<br><br><b style='color:#795548;'>⚖️ HUKUKİ DAYANAK:</b>")
            icerik = icerik.replace("📢 SONUÇ:", "<br><br><b style='color:#1565c0;'>📢 SONUÇ:</b>")
            
            # 6. Kalan satır sonlarını standart alt satıra çevir
            icerik = icerik.replace("* ", "• ").replace("\n", "<br>")

            # 2. HTML GİYDİRME (Gövde metni 15px, tam kitap kıvamı!)
            # 356. satır civarındaki st.markdown bloğu
            st.markdown(f"""
            <div style="background-color: #fcfaf5; padding: 40px; border: 1px solid #e0dcd0; border-top: 8px solid #2e7d32; border-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); color: #2c3e50; font-family: 'Georgia', serif;">
                <div style="font-size: 12px; color: #2e7d32; font-weight: bold; text-transform: uppercase; margin-bottom: 20px; letter-spacing: 1px; border-bottom: 1px solid #e0dcd0; padding-bottom: 10px;">
                    🎓 AKADEMİK ANALİZ ŞERHİ - Sayfa {aktif + 1}
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
                # Sayfa numarasını ortada göster
                st.markdown(f"<center><b>{aktif + 1} . Sayfa</b></center>", unsafe_allow_html=True)
                
            with col3:
                if aktif < len(sayfalar) - 1:
                    if st.button("İleri ➡️"):
                        st.session_state.akademi_aktif_sayfa += 1
                        st.rerun()

    # ==========================================
    # 2. SEKME: NOTLARIM (Yükleme, Arşiv ve Çöp Kutusu)
    # ==========================================
    with tab_notlar:
        st.header("📥 Not Yükleme Alanı")
        
        uploaded_file = st.file_uploader("Notunu Buraya Yükle (PDF)", type="pdf", key="main_uploader")
        
        if uploaded_file is not None:
            dosya_ismi = uploaded_file.name
            
            with st.spinner("PDF okunuyor ve arşive işleniyor... (Bu biraz sürebilir)"):
                # 1. PDF'İN İÇİNDEKİ YAZILARI ÇIKARIYORUZ
                cikarilan_metin = AkademikEngine.dosyadan_metin_cikar(uploaded_file)
                
                try:
                    from firebase_admin import firestore
                    db = firestore.client()
                    
                    # 2. VERİTABANINA İSMİ VE "METNİ" BİRLİKTE KAYDEDİYORUZ
                    db.collection("ders_notlari").add({
                        "dosya_adi": dosya_ismi,
                        "metin": cikarilan_metin,  # <-- Eksik olan asıl evrak buydu!
                        "tarih": firestore.SERVER_TIMESTAMP
                    })
                    
                    # 3. Yüklenen dosyayı anında "Aktif Not" yapıyoruz
                    st.session_state.islenmis_not = cikarilan_metin
                    st.session_state.aktif_dosya = dosya_ismi
                    
                    st.success(f"✅ {dosya_ismi} başarıyla okundu ve arşive eklendi!")
                except Exception as e:
                    st.error(f"Veritabanına işlenirken hata: {e}")

        st.markdown("---") 

        st.subheader("📚 Dijital Arşivim")
        with st.expander("Daha Önce Tarattığın Notları Gör ve Yönet", expanded=True):
            mevcut_notlar = AkademikEngine.yuklenen_notlari_getir()
            
            if mevcut_notlar: 
                for not_adi in mevcut_notlar:
                    # Sütunları 3'e böldük: İsim, Seç Butonu, Sil Butonu
                    col_isim, col_sec, col_sil = st.columns([3, 1, 1])
                    
                    with col_isim:
                        st.markdown(f"📄 **{not_adi}**")
                        
                    with col_sec:
                        if st.button("✅ Seç", key=f"sec_{not_adi}"):
                            # Arşivdeki notun metnini veritabanından çekip aktif ediyoruz!
                            eski_metin = AkademikEngine.not_icerigi_getir(not_adi)
                            
                            if eski_metin:
                                st.session_state.islenmis_not = eski_metin
                                st.session_state.aktif_dosya = not_adi
                                st.success(f"📌 '{not_adi}' masaya koyuldu, soruları buna soracaksın!")
                            else:
                                st.warning("Bu dosyanın metni yok! (Eski, hatalı yükleme olabilir. Lütfen silip tekrar yükle.)")
                                
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

      
        if st.button("Hocadan Dinle"):
            if not_icerigi:
                with st.spinner("Hoca kürsüye çıkıyor, notları inceliyor..."):
                    try:
                        # 1. Analizi yap
                        sonuc = AkademikEngine.notlarla_ai_hoca_anlat(
                            MY_API_KEY, 
                            aktif_not_ismi, 
                            not_icerigi
                        )
                        
                        if sonuc:
                            # 2. Metni sayfalara böl
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
                            
                            # 3. BURASI KRİTİK: 'hoca_sayfalar' olarak kaydet!
                            st.session_state.hoca_sayfalar = sayfalar
                            st.session_state.hoca_aktif_sayfa = 0
                            st.rerun()
                    except Exception as e:
                        st.error(f"Hoca anlatırken bir usul hatası oluştu: {e}")
            else:
                st.warning("Lütfen önce bir not yükleyin ustam.")
        
        # --- GÖRÜNTÜLEME ALANI (Her şey bu if'in içinde olmalı) ---
        if "hoca_sayfalar" in st.session_state and st.session_state.hoca_sayfalar:
            st.markdown("---")
        
        # --- 3. KISIM: SORU SORMA ALANI (DİJİTAL KİTAP MODU) ---
        st.subheader("❓ Notlardan Soru Sor")
        
        aktif_not_ismi = st.session_state.get('aktif_dosya', 'Hiçbiri (Genel Hukuk Bilgisi)')
        st.info(f"🔎 **Şu an incelenen evrak:** {aktif_not_ismi}")
        
        # Değişkenleri session_state'den güvenli bir şekilde alalım
        not_icerigi = st.session_state.get('islenmis_not', "")
        
        # Soru kutusu
        # 521. satırı bu şekilde değiştir ustam:
        soru_input = st.text_input(
            "Hocaya sormak istediğin soru nedir?", 
            placeholder="Örn: Butlan ve İptal farkı", 
            key="hoca_not_soru_input" # Bu anahtar bu kutuyu benzersiz yapar
        )
        
        # Eğer butonlarda da hata alırsan:
        if st.button("Hocadan Dinle", key="btn_hoca_dinle_notlar"):
            # ... işlemler
            if not_icerigi:
                with st.spinner("Hoca kürsüye çıkıyor, notları inceliyor..."):
                    try:
                        # 1. Analizi yap
                        sonuc = AkademikEngine.notlarla_ai_hoca_anlat(
                            MY_API_KEY, 
                            aktif_not_ismi, 
                            not_icerigi
                        )
                        
                        if sonuc:
                            # 2. Metni sayfalara böl
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
                            
                            # 3. BURASI KRİTİK: 'hoca_sayfalar' olarak kaydet!
                            st.session_state.hoca_sayfalar = sayfalar
                            st.session_state.hoca_aktif_sayfa = 0
                            st.rerun()
                    except Exception as e:
                        st.error(f"Hoca anlatırken bir usul hatası oluştu: {e}")
            else:
                st.warning("Lütfen önce bir not yükleyin ustam.")

        # --- GÖRÜNTÜLEME ALANI (Her şey bu if'in içinde olmalı) ---
        if "hoca_sayfalar" in st.session_state and st.session_state.hoca_sayfalar:
            st.markdown("---")
                
            # Başlık ve İndirme Butonu
            col_baslik, col_indir = st.columns([3, 1])
            with col_baslik:
                st.markdown("### 📖 Hoca'nın Notu")
                
            with col_indir:
                 # 1. Metni Al (Filtre yok, orijinal Türkçe metin!)
                tam_metin = "\n\n".join(st.session_state.hoca_sayfalar)
                
                # 2. Türkçe Destekli Fontları (Roboto) Otomatik İndir
                font_reg = "Roboto-Regular.ttf"
                font_bold = "Roboto-Bold.ttf"
                
                # Sunucuda (veya bilgisayarında) yoksa 1 saniyede Google'dan çeker
                if not os.path.exists(font_reg):
                    urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_reg)
                if not os.path.exists(font_bold):
                    urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", font_bold)
                
                # 3. Junilex SVG Logosunu Tanımla
                svg_logo = """<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="50" cy="50" r="45" stroke="#C5A059" stroke-width="2" fill="none"/>
                    <path d="M30 45C30 45 35 60 50 60C65 60 70 45 70 45" stroke="#C5A059" stroke-width="2" fill="none"/>
                    <path d="M50 20V80" stroke="#C5A059" stroke-width="2"/>
                    <path d="M25 35H75" stroke="#1A1A1A" stroke-width="4"/>
                </svg>"""
                
                with open("temp_logo.svg", "w", encoding="utf-8") as f:
                    f.write(svg_logo)
                
                # 4. PDF Motorunu Başlat
                pdf = FPDF()
                pdf.add_page()
                
                # 5. İndirdiğimiz Türkçe Fontları PDF'e Tanıt
                pdf.add_font("Roboto", "", font_reg)
                pdf.add_font("Roboto", "B", font_bold)
                
                # 6. Logoyu Ekle
                pdf.image("temp_logo.svg", x=85, y=10, w=40)
                pdf.ln(35) 
                
                if os.path.exists("temp_logo.svg"):
                    os.remove("temp_logo.svg")
                
                # 7. Antet ve Başlıkları Ekle (TÜRKÇE SERBEST!)
                pdf.set_font("Roboto", style="B", size=16)
                pdf.cell(0, 6, f"İncelenen Evrak: {aktif_not_ismi}", ln=True, align='C')
                
                # Fontu normale çevirip detayları yazıyoruz
                pdf.set_font("Roboto", "", size=10)
                pdf.cell(0, 6, f"İncelenen Evrak: {aktif_not_ismi}", ln=True, align='C')
                pdf.cell(0, 6, "Hazırlayan: Ozan Şahin Sicim (Çankırı Karatekin Üniversitesi Hukuk Fakültesi)", ln=True, align='C')
                pdf.ln(10)
                
                # 8. Ana Metni Ekle
                pdf.set_font("Roboto", size=11)
                pdf.multi_cell(0, 7, tam_metin) 
                
                # 9. PDF'i Byte olarak belleğe al
                pdf_bytes = bytes(pdf.output())
                
                # 10. İndirme Butonu
                st.download_button(
                    label="📥 PDF Olarak İndir",
                    data=pdf_bytes,
                    file_name=f"Junilex_Mutaala_{aktif_not_ismi}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            # --- KİTAP GÖRÜNÜMÜ ---
            aktif = st.session_state.hoca_aktif_sayfa
            sayfalar = st.session_state.hoca_sayfalar
            
            # Kitap şerh kartı (Müfredat kısmındakini buraya kopyalıyoruz ama değişkenleri hoca_sayfalar yapıyoruz)
            icerik = sayfalar[aktif]
            
            # HTML Tasarımı (Burada senin paylaştığın Prestige Şerh tasarımını kullanabilirsin)
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
        
            # Navigasyon
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
    # ==========================================
    # 3. SEKME: SINAV MODU
    # ==========================================
    with tab_sinav:
        st.markdown("#### 📝 Pratik Çalışma")
        sinav_konusu = st.text_input("Sınav Konusu", placeholder="Örn: Ceza Hukuku Genel Hükümler")
        
        if st.button("🔥 Sınavı Başlat"):
            if sinav_konusu:
                with st.spinner("Sınav hazırlanıyor..."):
                    # Not yoksa hata vermemesi için '.get()' kullanıyoruz
                    islenmis = st.session_state.get('islenmis_not', "")
                    sonuc = AkademikSinavEngine.pratik_calisma_uret(MY_API_KEY, sinav_konusu, islenmis)
                    
                    if "hata" in sonuc:
                        st.error(f"Sınav üretilemedi: {sonuc['hata']}")
                    else:
                        st.session_state.su_anki_sinav = sonuc
            else:
                st.warning("Lütfen bir konu girin.")

        # Sınav Ekrana Basma
        if st.session_state.get('su_anki_sinav'):
            sinav = st.session_state.su_anki_sinav
            
            if "olay_kurgusu" in sinav:
                st.info(f"📖 OLAY: {sinav['olay_kurgusu']}")
                
                for i, soru_data in enumerate(sinav.get('sorular', [])):
                    st.markdown("---")
                    st.markdown(f"**Soru {i+1}:** {soru_data['soru']}")
                    
                    secim = st.radio(
                        f"Seçenekler ({i+1})", 
                        soru_data['secenekler'], 
                        key=f"q_{i}"
                    )
                    
                    if st.button(f"Kontrol Et ({i+1})", key=f"b_{i}"):
                        if secim.strip().lower() == soru_data['cevap'].strip().lower():
                            st.success(f"✅ DOĞRU! \n\n **Analiz:** {soru_data['analiz']}")
                        else:
                            st.error(f"❌ YANLIŞ! \n\n **Doğru Cevap:** {soru_data['cevap']}")
                            st.warning(f"**Gerekçe:** {soru_data['analiz']}")
            else:
                st.error("Sınav formatı bozuk. Lütfen sıfırlayıp tekrar başlatın.")
                # app.py içinde sekmelerin olduğu kısma ekle
#tab_dilekce = st.tabs(["Dilekçe Yaz"]) # Mevcut sekmelerine ekle

# 3. BÖLÜM: DİLEKÇE (YENİ YERİ)
elif secim == "📝 Arzuhal(Dilekçe Yazım Merkezi)":
    st.header("📝 Dilekçe Taslağı Oluştur")
    st.info("Lütfen olayları ve tarafları detaylıca giriniz.")
    
    col1, col2 = st.columns(2)
    with col1:
        d_konu = st.text_input("Dilekçe Konusu", placeholder="Örn: Hakaret Suçu Şikayeti")
        d_taraflar = st.text_area("Taraflar", placeholder="Davacı: ...\nDavalı: ...")
    with col2:
        d_olay = st.text_area("Olayın Özeti", placeholder="Olayları buraya özetleyin...")
        d_talep = st.text_area("Talepler", placeholder="Netice-i talep kısmını buraya yazın...")

    if st.button("📝 Dilekçeyi Yaz ve Hazırla"):
        if d_konu and d_olay:
            st.markdown("### 📄 JUNILEX Dilekçe Taslağı:")
        
            # 1. Akışı başlatıyoruz
            stream = DilekceEngine.dilekce_olustur(MY_API_KEY, d_konu, d_taraflar, d_olay, d_talep)
        
            # 2. Süzgeç fonksiyonu
            def dilekce_suzucu():
                for parca in stream:
                    if parca.text:
                        yield parca.text
        
            # 3. Ekrana yazdırıyoruz ve sonucu TAM_METIN içine alıyoruz
            tam_metin = st.write_stream(dilekce_suzucu)
        
            # 4. Session State kaydı (Her iki satırı da tam_metin yapalım)
            st.session_state.son_dilekce = tam_metin
                
            # 5. WORD İNDİRME (Hata buradaydı: 'metin' yerine 'tam_metin' yazdık)
            word_data = DilekceEngine.word_dosyasi_yap(tam_metin) 
                
            st.download_button(
                label="📥 Word Dosyası Olarak Kaydet",
                data=word_data,
                file_name=f"{d_konu}_taslak.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            st.warning("Lütfen konu ve olay özetini doldurunuz ustam!")
                
            # Word İndirme
            word_data = DilekceEngine.word_dosyasi_yap(metin)
            st.download_button(
                label="📥 Word Dosyası Olarak Kaydet",
                data=word_data,
                file_name=f"{d_konu}_taslak.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

# --- MOD 4: İÇTİHAT SORGULAMA (Tamamen Düzeltilmiş) ---
elif secim == "⚖️ İçtihat Sorgulama":
    # --- KESİN ÇÖZÜM BURASI ---
    # Değişkeni en başta, hiçbir bloğa girmeden 'boş' olarak tanımlıyoruz.
    
    st.header("⚖️ İçtihat ve Emsal Merkezi")
    
    tab1, tab2 = st.tabs(["🔍 Karar Analizi (Şerh)", "🔎 Emsal Karar Bulucu"])
    
    with tab1:
        st.subheader("⚖️ Karar Analiz Modülü")
        karar_metni = st.text_area("Yargıtay Karar Metnini Buraya Yapıştırın", height=250, key="karar_text_area")
        soru_input = st.text_input("Bu kararla ilgili neyi merak ediyorsunuz?", placeholder="Örn: İspat yükü kime verilmiş?", key="karar_soru_input")
        
        if st.button("⚖️ Analiz Et", use_container_width=True, key="btn_analiz_et"):
            if karar_metni and soru_input:
                with st.spinner("Hakim Junilex dosyayı inceliyor..."):
                    from ictihat_engine import IctihatEngine
                    
                    # Motoru çağır
                    response = IctihatEngine.karar_analiz_et(MY_API_KEY, karar_metni, soru_input)
                    
                    # Yanıtın türünü kontrol edip metni alıyoruz
                    tam_metn = ""
                    if isinstance(response, str):
                        tam_metn = response
                    else:
                        # Eğer stream geliyorsa (generator)
                        for chunk in response:
                            try:
                                if hasattr(chunk, "text") and chunk.text:
                                    tam_metn += chunk.text
                            except: continue
                    
                    if tam_metn:
                        # 400 karakter çok az ustam, sayfa çok kısa olur. 1200 idealdir.
                        st.session_state.analiz_sayfalari = metni_sayfalara_bol(tam_metn, 1200)
                        st.session_state.analiz_aktif_sayfa = 0
                        st.rerun()
                    else:
                        st.error("Analiz sonucu boş döndü, lütfen tekrar deneyin.")

        # --- GÖRÜNTÜLEME VE BUTONLAR (KARAR ANALİZİ) ---
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
    with tab2:
        st.subheader("🔎 Yargıtay Yönelim Analizi")
        
        # 1. DEĞİŞKENİ TANIMLIYORUZ (Hizaya dikkat: with tab2'nin 1 tab içinde)
        olay_input = st.text_area(
            "Hukuki Olayı Detaylıca Anlatın", 
            height=150, 
            placeholder="Örn: Banka hesabından rıza dışı para çekilmesi...", 
            key="emsal_olay_girdisi_v4" # Benzersiz bir key verdik
        )
        
        if st.button("🔎 Analiz Et", use_container_width=True, key="btn_emsal_bul_v4"):
            if olay_input: 
                with st.spinner("Junilex kütüphaneleri tarıyor ve analiz ediyor..."):
                    try:
                        from ictihat_engine import IctihatEngine
                        
                        # Artık 'olay_input' burada %100 tanımlı
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

        # --- GÖRÜNTÜLEME BLOĞU (Hala tab2 içinde kalmalı!) ---
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
# ... diğer elif (Akademi, Adliye vb.) bloklarından sonra ekle:

elif secim == "💬 JUNILEX Chat":
    st.header("💬 JUNILEX Chat")
    
    # 1. Hafıza ve Mod Başlatma
    if 'chat_mode' not in st.session_state:
        st.session_state.chat_mode = "Özet"
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [{"role": "assistant", "content": "Selam ustam, hangi meseleyi aydınlatalım?"}]

    # 2. Mesaj Geçmişini Göster (Yeni Nesil Avatarlarla)
    for message in st.session_state.chat_messages:
        if message["role"] == "user":
            simge = "https://api.dicebear.com/9.x/micah/png?seed=OzanSahinSicim&backgroundColor=transparent"
        else:
            simge = "https://api.dicebear.com/9.x/bottts-neutral/png?seed=Junilex&backgroundColor=0f172a"
            
        with st.chat_message(message["role"], avatar=simge):
            st.markdown(message["content"])

    # --- ALT KUMANDA PANELİ ---
    st.markdown("---")
    
    col_devam, col_mod = st.columns([1, 1])

    with col_mod:
        with st.popover(f"🧠 Mod: {st.session_state.chat_mode}", use_container_width=True):
            secilen_mod = st.radio(
                "Zeka Yapılandırması:",
                ["Özet", "⚖️ Detaylı Analiz"],
                index=0 if "Özet" in st.session_state.chat_mode else 1,
                key="chat_mode_radio"
            )
            if secilen_mod != st.session_state.chat_mode:
                st.session_state.chat_mode = secilen_mod
                st.rerun()

    with col_devam:
        # 4. "Devam Et" Butonu
        if len(st.session_state.chat_messages) > 1 and st.session_state.chat_messages[-1]["role"] == "assistant":
            if st.button("⏭️ Devam Et", help="Cevap yarıda kaldıysa tıklayın."):
                
                yarim_kalan_mesaj = st.session_state.chat_messages[-1]["content"]
                son_kelimeler = yarim_kalan_mesaj[-60:].strip() if len(yarim_kalan_mesaj) > 60 else yarim_kalan_mesaj
                
                devam_komutu = (
                    f"Önceki cevabın tam olarak şu kelimelerle yarım kaldı: '...{son_kelimeler}'.\n"
                    "KRİTİK GÖREV: Lütfen asla giriş cümlesi kurma, konuyu baştan anlatma ve yazdıklarını tekrar etme. "
                    "SADECE yarım kalan kelimeyi/cümleyi tamamla ve doğrudan konunun devamını yaz."
                )

                st.session_state.chat_messages.append({"role": "user", "content": "Devam et..."})
                
                with st.chat_message("assistant", avatar="https://api.dicebear.com/9.x/bottts-neutral/png?seed=Junilex&backgroundColor=0f172a"):
                    message_placeholder = st.empty()
                    
                    # 🔴 KRİTİK DÜZELTME: NameError hatasını çözen değişken tanımlaması BURADA
                    full_response = "" 
                    
                    from chat_engine import ChatEngine
                    
                    response = ChatEngine.yanit_uret(
                        MY_API_KEY, 
                        st.session_state.chat_messages[:-1], 
                        devam_komutu,
                        mod=st.session_state.chat_mode
                    )
                    
                    if isinstance(response, str) and response.startswith("HATA"):
                        st.error(response)
                    else:
                        for chunk in response:
                            try:
                                if chunk.candidates:
                                    sebep = chunk.candidates[0].finish_reason.name
                                    if sebep not in ['STOP', 'FINISH_REASON_UNSPECIFIED']:
                                        full_response += f"\n\n🚨 **[GOOGLE FİŞİ ÇEKTİ! SEBEP: {sebep}]**"
                                
                                if chunk.text:
                                    full_response += chunk.text
                                    message_placeholder.markdown(full_response + " ▌")
                                    
                            except ValueError as ve:
                                full_response += f"\n\n🛑 **[DEĞER HATASI (Filtre/Boşluk): {str(ve)}]**"
                                message_placeholder.markdown(full_response)
                                break 
                                
                            except Exception as e:
                                full_response += f"\n\n❌ **[TEKNİK HATA: {str(e)}]**"
                                message_placeholder.markdown(full_response)
                                break
                                
                        if not full_response.strip():
                            full_response = "⚠️ Ustam, sistem tamamen sessiz kaldı. Çıktı engellendi."
                        
                        message_placeholder.markdown(full_response)
                        st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
                        st.rerun()

    # 5. Ana Soru Girişi
    if prompt := st.chat_input("Mesajınızı yazın..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        container = st.empty() 

        with container.container():
            with st.chat_message("user", avatar="https://api.dicebear.com/9.x/micah/png?seed=OzanSahinSicim&backgroundColor=transparent"):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar="https://api.dicebear.com/9.x/bottts-neutral/png?seed=Junilex&backgroundColor=0f172a"):
                message_placeholder = st.empty() 
                
                # 🔴 KRİTİK DÜZELTME: NameError hatasını çözen değişken tanımlaması BURADA
                full_response = ""
                
                from chat_engine import ChatEngine
                
                response = ChatEngine.yanit_uret(
                    MY_API_KEY, 
                    st.session_state.chat_messages[:-1], 
                    prompt,
                    mod=st.session_state.chat_mode
                )
                
                if isinstance(response, str) and response.startswith("HATA"):
                    st.error(response)
                else:
                    for chunk in response:
                        try:
                            if chunk.candidates:
                                sebep = chunk.candidates[0].finish_reason.name
                                if sebep not in ['STOP', 'FINISH_REASON_UNSPECIFIED']:
                                    full_response += f"\n\n🚨 **[GOOGLE FİŞİ ÇEKTİ! SEBEP: {sebep}]**"
                            
                            if chunk.text:
                                full_response += chunk.text
                                message_placeholder.markdown(full_response + " ▌")
                                
                        except ValueError as ve:
                            full_response += f"\n\n🛑 **[DEĞER HATASI (Filtre/Boşluk): {str(ve)}]**"
                            message_placeholder.markdown(full_response)
                            break
                            
                        except Exception as e:
                            full_response += f"\n\n❌ **[TEKNİK HATA: {str(e)}]**"
                            message_placeholder.markdown(full_response)
                            break
                    
                    if not full_response.strip():
                        full_response = "⚠️ Ustam, sistem tamamen sessiz kaldı. Çıktı engellendi."
                    
                    message_placeholder.markdown(full_response)
                    st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
                    st.rerun()
            
    # 6. Sidebar Temizleme Butonu
    if st.sidebar.button("🗑️ Sohbeti Sıfırla"):
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Selam ustam, ben Junilex. Bugün hangi hukuki meseleyi aydınlatalım?"}
        ]
        st.rerun()
