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
from streamlit_option_menu import option_menu


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


@st.cache_resource
def get_db():
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    return firestore.client()


# ==========================================
# ⚙️ AYARLAR VE BELLEK YÖNETİMİ
# ==========================================
st.set_page_config(layout="wide", page_title="JUNILEX AI")


st.markdown(
    """
    <style>
        /* ── DESIGN TOKENS & TEMA SIFIRLAMA ── */
        :root {
            --bg-main: #0B0E14;
            --bg-card: #131822;
            --bg-card-hover: #1A212E;
            --bg-input: #171D2A;
            --border: #232B3E;
            --border-highlight: rgba(201, 168, 76, 0.3);
            --text-main: #E2E8F0;
            --text-muted: #8A99AD;
            --gold-primary: #C9A84C;
            --gold-light: #E5C974;
            --gold-glow: rgba(201, 168, 76, 0.15);
            --radius-lg: 14px;
            --radius-md: 10px;
            --radius-sm: 6px;
        }

        /* ── GENEL ARKA PLAN ── */
        .stApp {
            background-color: var(--bg-main) !important;
            color: var(--text-main) !important;
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        /* ── OPTION MENU HOVER EFEKTİ SÜPER ZORLAMA (SPECIFICITY FIX) ── */
        div[id^="option-menu"] .nav-link:hover,
        .stSidebar .nav-link:hover,
        [data-testid="stSidebar"] .nav-link:hover {
            background-color: rgba(201, 168, 76, 0.12) !important;
            border-left: 3px solid #C9A84C !important;
            color: #C9A84C !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
        }

        div[id^="option-menu"] .nav-link:hover i,
        div[id^="option-menu"] .nav-link:hover span,
        .stSidebar .nav-link:hover i,
        .stSidebar .nav-link:hover span {
            color: #C9A84C !important;
        }

        /* ── KARTLAR & KONTEYNERLAR ── */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(180deg, var(--bg-card) 0%, rgba(19, 24, 34, 0.7) 100%) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-lg) !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
            backdrop-filter: blur(10px) !important;
            transition: border-color 0.2s ease, transform 0.2s ease !important;
        }

        /* ── FORM GİRDİLERİ (INPUT, TEXTAREA, SELECT) ── */
        .stTextInput input, .stTextArea textarea, .stNumberInput input {
            background: var(--bg-input) !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            font-family: 'DM Sans', sans-serif !important;
            font-size: 14px !important;
            padding: 10px 14px !important;
        }

        /* ── METRİK KARTLARI ── */
        [data-testid="stMetricValue"] {
            color: var(--gold-primary) !important;
            font-size: 26px !important;
            font-weight: 700 !important;
        }
        [data-testid="stMetricLabel"] p {
            color: var(--text-muted) !important;
            font-size: 13px !important;
        }

        /* ── SCROLLBAR ── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-main); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--gold-primary); }

        hr { border-color: var(--border) !important; opacity: 0.6; }
    </style>
""",
    unsafe_allow_html=True,
)
# -----------------------------------------------------------

# ==========================================
# 🔐 API VE MOTORLAR
# ==========================================
MY_API_KEY = st.secrets["GEMINI_API_KEY"]
SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
DB_DOSYASI = "kullanicilar.json"


def veritabani_yukle():
    baslangic_verisi = {
        "ozan@junilex.com": {
            "sifre": "123456",
            "isim": "Ozan Şahin Sicim",
            "id": "#00001",
            "arkadaslar": [],
            "gelen_istekler": [],
        }
    }

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
        db.collection("junilex_arsiv").add(
            {
                "kategori": kategori,
                "baslik": baslik,
                "metin": metin,
                "tarih": firestore.SERVER_TIMESTAMP,
                "kullanici": st.session_state.aktif_kullanici,
            }
        )
        return True, "Başarılı"
    except Exception as e:
        return False, str(e)


def onay_kodu_gonder(alici_mail, kod):
    gonderici_mail = st.secrets["GMAIL_MAIL"],
    uygulama_sifresi = st.secrets["GMAIL_SIFRE"],
    msg = MIMEText(
        f"JUNILEX'e hoş geldin!\n\nKayıt işlemini tamamlamak için doğrulama kodun: {kod}\n\nBu kodu kimseyle paylaşmayın.",
        "plain",
        "utf-8",
    )
    msg["Subject"] = "JUNILEX Doğrulama Kodu"
    msg["From"] = "JUNILEX Asistan"
    msg["To"] = alici_mail
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gonderici_mail, uygulama_sifresi)
        server.send_message(msg)
        server.quit()
        return True, "Başarılı"
    except Exception as e:
        return False, str(e)


def metni_sayfalara_bol(metin, sayfa_boyutu=1000):
    if not metin:
        return []
    paragraflar = metin.split("\n")
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


# ==========================================
# 🚀 SESSION STATE YÖNETİMİ
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "aktif_kullanici" not in st.session_state:
    st.session_state.aktif_kullanici = ""
if "aktif_kullanici_email" not in st.session_state:
    st.session_state.aktif_kullanici_email = ""
if "aktif_kullanici_id" not in st.session_state:
    st.session_state.aktif_kullanici_id = ""
if "kullanici_veritabani" not in st.session_state:
    st.session_state.kullanici_veritabani = veritabani_yukle()
if "onay_bekleyen" not in st.session_state:
    st.session_state.onay_bekleyen = None
if "aktif_ekran" not in st.session_state:
    st.session_state.aktif_ekran = "🏠 Ana Ekran"
if "secili_kanun" not in st.session_state:
    st.session_state.secili_kanun = None
if "bulunan_madde" not in st.session_state:
    st.session_state.bulunan_madde = None
if "arama_sonuclari" not in st.session_state:
    st.session_state.arama_sonuclari = []
if "islenmis_not" not in st.session_state:
    st.session_state.islenmis_not = None
if "su_anki_sinav" not in st.session_state:
    st.session_state.su_anki_sinav = None
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
if "chat_mode" not in st.session_state:
    st.session_state.chat_mode = "Özet"
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": "Selam ustam, hangi meseleyi veya belgeyi aydınlatalım?",
        }
    ]
if "aktif_dosya" not in st.session_state:
    st.session_state.aktif_dosya = None

# ==========================================
# 🛑 GİRİŞ VE KAYIT EKRANI (Orijinal Vektörel Logo Entegreli)
# ==========================================
if not st.session_state.logged_in:
    st.markdown(
        """<style>[data-testid="collapsedControl"] {display: none;} [data-testid="stSidebar"] {display: none;}</style>""",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # ── BİREBİR ORİJİNAL VEKTÖREL LOGO & MARKALAMA (BÜYÜTÜLMÜŞ) ──
        st.markdown(
            """
            <div style='text-align:center; padding: 16px 0 20px 0;'>
                <div style='display: flex; justify-content: center; margin-bottom: 12px;'>
                    <svg width="90" height="90" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                        <!-- Dış Altın Daire -->
                        <circle cx="50" cy="50" r="45" stroke="#C9A84C" stroke-width="3" fill="none"/>
                        <!-- Terazi Çanağı / Eğri -->
                        <path d="M30 46C30 46 35 62 50 62C65 62 70 46 70 46" stroke="#C9A84C" stroke-width="3" fill="none" stroke-linecap="round"/>
                        <!-- Dikey Direk -->
                        <path d="M50 20V80" stroke="#C9A84C" stroke-width="3" stroke-linecap="round"/>
                        <!-- Yatay Koyu Çizgi -->
                        <path d="M28 34H72" stroke="#2D2820" stroke-width="4.5" stroke-linecap="round"/>
                    </svg>
                </div>
                <div style='color:#C9A84C; font-family:"DM Sans", sans-serif; font-size:26px; font-weight:800; letter-spacing:2px;'>JUNILEX AI</div>
                <div style='color:#8A99AD; font-size:11px; font-weight:700; letter-spacing:1.5px; margin-top:4px;'>LEGAL INTELLIGENCE & ACADEMY</div>
            </div>
            
            <!-- Geliştirici Künyesi (Ortalı ve Şık Rozet) -->
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="
                    background: #131822; 
                    padding: 8px 18px; 
                    border-radius: 20px; 
                    border: 1px solid #232B3E; 
                    display: inline-block;
                ">
                    <span style="color: #8A99AD; font-size: 12px;">Geliştirici:</span> 
                    <span style="color: #E2E8F0; font-size: 12px; font-weight: 600;">Ozan Şahin Sicim</span>
                    <span style="color: #8A99AD; font-size: 11px; display: block; margin-top: 2px;">Çankırı Karatekin Üniversitesi Hukuk Fakültesi</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_giris, tab_kayit = st.tabs(["🔐 Giriş Yap", "📝 Yeni Kayıt"])

        # ── 1. TAB: GİRİŞ YAP ────────────────────────────────────────────────
        with tab_giris:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-left: 4px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">👋 Hoş Geldiniz</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Hesabınıza erişmek için e-posta ve şifrenizi girin.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            giris_email = st.text_input(
                "E-Posta Adresi", key="giris_email", placeholder="ornek@domain.com"
            )
            giris_sifre = st.text_input(
                "Şifre", type="password", key="giris_sifre", placeholder="••••••••"
            )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "🚀 Sisteme Giriş Yap", use_container_width=True, type="primary"
            ):
                st.session_state.kullanici_veritabani = veritabani_yukle()
                if (
                    giris_email in st.session_state.kullanici_veritabani
                    and st.session_state.kullanici_veritabani[giris_email]["sifre"]
                    == giris_sifre
                ):
                    st.session_state.logged_in = True
                    st.session_state.aktif_kullanici = (
                        st.session_state.kullanici_veritabani[giris_email]["isim"]
                    )
                    st.session_state.aktif_kullanici_email = giris_email
                    st.session_state.aktif_kullanici_id = (
                        st.session_state.kullanici_veritabani[giris_email]["id"]
                    )
                    st.rerun()
                else:
                    st.error("❌ E-posta adresi veya şifre hatalı!")

        # ── 2. TAB: YENİ KAYIT ───────────────────────────────────────────────
        with tab_kayit:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.session_state.onay_bekleyen is None:
                st.markdown(
                    """
                    <div style="
                        background: #131822; 
                        padding: 16px 20px; 
                        border-radius: 12px; 
                        border: 1px solid #232B3E; 
                        border-left: 4px solid #C9A84C; 
                        margin-bottom: 16px;
                    ">
                        <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">✨ Hesap Oluşturun</h4>
                        <p style="color: #8A99AD; font-size: 12px; margin: 0;">Junilex Ağından faydalanmak ve yapay zeka asistanını kullanmak için kaydolun.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                kayit_isim = st.text_input(
                    "İsim Soyisim",
                    key="kayit_isim",
                    placeholder="Örn: Av. Ozan Şahin Sicim",
                )
                kayit_email = st.text_input(
                    "E-Posta Adresi", key="kayit_email", placeholder="ornek@domain.com"
                )

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    kayit_sifre = st.text_input(
                        "Yeni Şifre",
                        type="password",
                        key="kayit_sifre",
                        placeholder="••••••••",
                    )
                with col_s2:
                    kayit_sifre_tekrar = st.text_input(
                        "Şifre Tekrar",
                        type="password",
                        key="kayit_sifre_tekrar",
                        placeholder="••••••••",
                    )

                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                st.markdown(
                    """
                    <div style="
                        background: #0B0E14; 
                        padding: 10px 14px; 
                        border-radius: 8px; 
                        border-left: 3px solid #C9A84C; 
                        margin-bottom: 12px;
                    ">
                        <span style="color: #E2E8F0; font-size: 13px; font-weight: 600;">🤝 Ağ Profili (Gelişmiş Eşleşme İçin)</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                sehirler = [
                    "Seçiniz...",
                    "Adana",
                    "Ankara",
                    "Antalya",
                    "Bursa",
                    "Çankırı",
                    "Diyarbakır",
                    "Erzurum",
                    "Gaziantep",
                    "İstanbul",
                    "İzmir",
                    "Konya",
                    "Diğer",
                ]
                secilen_sehir = st.selectbox(
                    "İkamet Ettiğiniz Şehir", sehirler, key="kayit_sehir"
                )

                meslekler = [
                    "Seçiniz...",
                    "Avukat",
                    "Stajyer Avukat",
                    "Hukuk Fakültesi Öğrencisi",
                    "Hakim / Savcı",
                    "Diğer",
                ]
                secilen_meslek = st.selectbox(
                    "Mesleki Durumunuz", meslekler, key="kayit_meslek"
                )

                alt_bilgi = ""
                if secilen_meslek in ["Avukat", "Stajyer Avukat"]:
                    barolar = [
                        "Belirtmek İstemiyorum",
                        "Ankara Barosu",
                        "Antalya Barosu",
                        "Çankırı Barosu",
                        "İstanbul Barosu",
                        "İzmir Barosu",
                        "Diğer",
                    ]
                    alt_bilgi = st.selectbox(
                        "Bağlı Olduğunuz Baro (İsteğe Bağlı)", barolar, key="kayit_baro"
                    )
                elif secilen_meslek == "Hukuk Fakültesi Öğrencisi":
                    universiteler = [
                        "Belirtmek İstemiyorum",
                        "Ankara Üniversitesi",
                        "Çankırı Karatekin Üniversitesi",
                        "Dokuz Eylül Üniversitesi",
                        "İstanbul Üniversitesi",
                        "Marmara Üniversitesi",
                        "Diğer",
                    ]
                    alt_bilgi = st.selectbox(
                        "Üniversiteniz (İsteğe Bağlı)", universiteler, key="kayit_uni"
                    )

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                if st.button(
                    "📝 Kayıt Ol ve Doğrulama Kodu Al",
                    use_container_width=True,
                    type="primary",
                ):
                    st.session_state.kullanici_veritabani = veritabani_yukle()
                    if len(kayit_isim.strip()) < 3:
                        st.warning("⚠️ Lütfen geçerli bir İsim Soyisim giriniz!")
                    elif "@" not in kayit_email or "." not in kayit_email:
                        st.warning("⚠️ Lütfen geçerli bir e-posta adresi giriniz!")
                    elif kayit_email in st.session_state.kullanici_veritabani:
                        st.warning("⚠️ Bu e-posta adresi zaten sisteme kayıtlı!")
                    elif kayit_sifre != kayit_sifre_tekrar:
                        st.error("❌ Şifreler uyuşmuyor!")
                    elif len(kayit_sifre) < 6:
                        st.warning("⚠️ Şifre en az 6 karakter olmalıdır.")
                    elif (
                        secilen_sehir == "Seçiniz..." or secilen_meslek == "Seçiniz..."
                    ):
                        st.warning("⚠️ Lütfen Şehir ve Meslek bilgilerinizi seçiniz!")
                    else:
                        uretilen_kod = str(random.randint(100000, 999999))
                        with st.spinner("Doğrulama kodu e-postanıza gönderiliyor..."):
                            basarili_mi, hata_mesaji = onay_kodu_gonder(
                                kayit_email, uretilen_kod
                            )
                        if basarili_mi:
                            st.session_state.onay_bekleyen = {
                                "isim": kayit_isim.title(),
                                "email": kayit_email,
                                "sifre": kayit_sifre,
                                "kod": uretilen_kod,
                                "sehir": secilen_sehir,
                                "unvan": secilen_meslek,
                                "kurum": alt_bilgi,
                            }
                            st.success(
                                "✅ Kod gönderildi! Lütfen e-postanızı kontrol edin."
                            )
                            st.rerun()
                        else:
                            st.error(
                                f"E-posta gönderilemedi! Teknik detay: {hata_mesaji}"
                            )
            else:
                # ── DOĞRULAMA KODU (OTP) EKRANI ─────────────────────────────
                st.markdown(
                    f"""
                    <div style="
                        background: #131822; 
                        padding: 18px 22px; 
                        border-radius: 12px; 
                        border: 1px solid #232B3E; 
                        border-left: 4px solid #C9A84C; 
                        margin-bottom: 16px;
                    ">
                        <h4 style="margin:0 0 6px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">📧 E-Posta Doğrulama</h4>
                        <p style="color: #8A99AD; font-size: 12px; margin: 0;">
                            <strong style="color:#C9A84C;">{st.session_state.onay_bekleyen['email']}</strong> adresine gönderilen 6 haneli kodu girin.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                girilen_kod = st.text_input(
                    "Doğrulama Kodu",
                    key="dogrulama_kodu",
                    max_chars=6,
                    placeholder="123456",
                )

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                col_onay1, col_onay2, col_onay3 = st.columns(3)

                with col_onay1:
                    if st.button(
                        "✅ Kodu Doğrula", use_container_width=True, type="primary"
                    ):
                        if girilen_kod == st.session_state.onay_bekleyen["kod"]:
                            import datetime

                            bugun = datetime.date.today().strftime("%d.%m.%Y")

                            yeni_mail = st.session_state.onay_bekleyen["email"]
                            yeni_id = benzersiz_id_uret(
                                st.session_state.kullanici_veritabani
                            )

                            st.session_state.kullanici_veritabani[yeni_mail] = {
                                "sifre": st.session_state.onay_bekleyen["sifre"],
                                "isim": st.session_state.onay_bekleyen["isim"],
                                "id": yeni_id,
                                "sehir": st.session_state.onay_bekleyen["sehir"],
                                "unvan": st.session_state.onay_bekleyen["unvan"],
                                "kurum": st.session_state.onay_bekleyen["kurum"],
                                "kayit_tarihi": bugun,
                                "arkadaslar": [],
                                "gelen_istekler": [],
                            }
                            veritabani_kaydet(st.session_state.kullanici_veritabani)
                            st.session_state.onay_bekleyen = None
                            st.balloons()
                            st.success(
                                "🎉 Kayıt başarılı! Şimdi 'Giriş Yap' sekmesine geçerek JUNILEX'i kullanmaya başlayabilirsiniz."
                            )
                        else:
                            st.error(
                                "❌ Doğrulama kodu hatalı! Lütfen tekrar kontrol edin."
                            )
                with col_onay2:
                    if st.button("🔄 Tekrar Kod Gönder", use_container_width=True):
                        yeni_kod = str(random.randint(100000, 999999))
                        with st.spinner("Yeni kod hazırlanıyor..."):
                            basarili, mesaj = onay_kodu_gonder(
                                st.session_state.onay_bekleyen["email"], yeni_kod
                            )
                        if basarili:
                            st.session_state.onay_bekleyen["kod"] = yeni_kod
                            st.toast("✅ Yeni kod başarıyla gönderildi!", icon="📧")
                        else:
                            st.error(f"Kod gönderimi başarısız: {mesaj}")
                with col_onay3:
                    if st.button("⬅️ Düzenle", use_container_width=True):
                        st.session_state.onay_bekleyen = None
                        st.rerun()
    st.stop()
# ════════════════════════════════════════════
# 🗂  PROFESYONEL SAAS NAVİGASYON (OPTION MENU)
# ════════════════════════════════════════════

# Modül Eşleşme Haritası
MODUL_HARITASI = {
    "Adliye": "Adliye (Mevzuat Sorgu)",
    "Akademi": "Akademik Asistan",
    "Arzuhal": "Dilekçe Merkezi",
    "İçtihat": "İçtihat Sorgulama",
    "Hesaplamalar": "Pratik Hesaplamalar",
    "Chat": "💬 JUNILEX Chat",
    "Ağ": "👥 Junilex Ağı",
    "Profil": "Profil",
    "Ayarlar": "Ayarlar",
}

# ── SIDEBAR (Tek Ve Tam Navigasyon) ──────────────────────────────────────────
with st.sidebar:
    # ── CSS HİLESİ: OPTION_MENU'NÜN DIŞINDA YAZILMALIDIR ──
    st.markdown(
        """
        <style>
        /* Option Menu listesini (ul) ekranın %70'ini kaplayacak şekilde (flex) ayarlayalım */
        ul.nav.flex-column {
            height: 68vh !important;
            display: flex !important;
            flex-direction: column !important;
        }

        /* En son elemanı (Ayarlar) sayfanın en altına (auto) itiyoruz */
        ul.nav.flex-column > li.nav-item:last-child {
            margin-top: auto !important;
            width: max-content !important;
        }

        /* En son elemandaki 'Ayarlar' YAZISINI gizliyoruz, böylece sadece ikon kalır */
        ul.nav.flex-column > li.nav-item:last-child span {
            display: none !important;
        }
        
        /* Çark ikonunu daha büyük ve ortalanmış yapıyoruz */
        ul.nav.flex-column > li.nav-item:last-child i.bi-gear {
            font-size: 22px !important;
            margin-left: 2px !important;
            transition: all 0.4s ease-in-out;
        }
        
        /* Fare üzerine gelince çark döner ve neon mavi parlar */
        ul.nav.flex-column > li.nav-item:last-child a:hover i.bi-gear {
            transform: rotate(90deg);
            filter: drop-shadow(0px 0px 8px #4C6BC9);
            color: #4C6BC9 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── BİREBİR ORİJİNAL VEKTÖREL LOGO ──
    st.markdown(
        """
        <div style='text-align:center; padding: 12px 0 16px 0;'>
            <div style='display: flex; justify-content: center; margin-bottom: 10px;'>
                <svg width="48" height="48" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="50" cy="50" r="45" stroke="#C9A84C" stroke-width="3" fill="none"/>
                    <path d="M30 46C30 46 35 62 50 62C65 62 70 46 70 46" stroke="#C9A84C" stroke-width="3" fill="none" stroke-linecap="round"/>
                    <path d="M50 20V80" stroke="#C9A84C" stroke-width="3" stroke-linecap="round"/>
                    <path d="M28 34H72" stroke="#2D2820" stroke-width="4.5" stroke-linecap="round"/>
                </svg>
            </div>
            <div style='color:#C9A84C; font-family:"DM Sans", sans-serif; font-size:16px; font-weight:800; letter-spacing:2px;'>JUNILEX AI</div>
            <div style='color:#8A99AD; font-size:8px; font-weight:700; letter-spacing:1px; margin-top:3px;'>LEGAL INTELLIGENCE & ACADEMY</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # İkon ve Yazıları Hizalanmış Sidebar Menüsü
    secilen_sidebar = option_menu(
        menu_title=None,
        options=[
            "Ana Ekran",
            "Adliye",
            "Akademi",
            "Arzuhal",
            "İçtihat",
            "Hesaplamalar",
            "Chat",
            "Ağ",
            "Profil",
            "Ayarlar",  # 👈 DİKKAT: "Ayarlar" yazısını sildik, sadece 1 adet boşluk karakteri bıraktık.
        ],
        icons=[
            "house-door",
            "bank",
            "mortarboard",
            "file-earmark-text",
            "search",
            "calculator",
            "chat-square-dots",
            "people",
            "person",
            "gear",  # Boşluk ismine karşılık gelen çark ikonu
        ],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#8A99AD", "font-size": "16px"},
            "nav-link": {
                "font-size": "13px",
                "text-align": "left",
                "margin": "3px 0",
                "padding": "8px 12px",
                "color": "#8A99AD",
                "border-radius": "8px",
                "display": "flex",
                "align-items": "center",
                "gap": "10px",
                "--hover-color": "rgba(201, 168, 76, 0.12)",
            },
            "nav-link-selected": {
                "background-color": "rgba(201, 168, 76, 0.15)",
                "color": "#C9A84C",
                "border-left": "3px solid #C9A84C",
                "font-weight": "600",
            },
        },
    )

    # Seçilen menüyü uygulamanın geri kalanı için oturum (session) durumuna aktar
    st.session_state.aktif_ekran = secilen_sidebar

    # Seçime Göre Aktif Ekranı Güncelle
    if secilen_sidebar in MODUL_HARITASI:
        st.session_state.aktif_ekran = MODUL_HARITASI[secilen_sidebar]
    elif secilen_sidebar == "Ana Ekran":
        st.session_state.aktif_ekran = "Ana Ekran"

    # Çıkış Butonu
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    if st.button("↩ Çıkış", key="cikis_btn_saas", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# ── ANA İÇERİK LAYOUT ──────────────────────────────────────────────────────
col_icerik = st.container()

# ════════════════════════════════════════════
with col_icerik:

    # ==========================================
    # 🏠 DASHBOARD (ANA EKRAN - Premium SaaS UI)
    # ==========================================
    if st.session_state.aktif_ekran in ["🏠 Ana Ekran", "Ana Ekran", "Dashboard"]:

        isim = st.session_state.get("aktif_kullanici", "Kullanıcı").split()[0]
        raw_uid = str(st.session_state.get("aktif_kullanici_id", "82662")).replace(
            "#", ""
        )
        uid = f"#{raw_uid}"

        # 1. Hoş Geldin & Karşılama Kartı
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #131822 0%, #1A212E 100%);
                border: 1px solid #232B3E;
                border-left: 4px solid #C9A84C;
                border-radius: 12px;
                padding: 24px 28px;
                margin-bottom: 24px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                display: flex;
                align-items: center;
                justify-content: space-between;
            ">
                <div>
                    <h2 style="
                        margin: 0;
                        padding: 0;
                        color: #E2E8F0;
                        font-family: 'DM Sans', sans-serif;
                        font-size: 24px;
                        font-weight: 700;
                    ">
                        Hoş geldin, {isim} 👋
                    </h2>
                    <p style="
                        margin: 6px 0 0 0;
                        color: #8A99AD;
                        font-size: 13px;
                    ">
                        JUNILEX Legal AI platformu göreve hazır. Bugün ne üzerine çalışıyoruz?
                    </p>
                </div>
                <div style="
                    background: #0B0E14;
                    border: 1px solid #232B3E;
                    padding: 6px 14px;
                    border-radius: 20px;
                    color: #C9A84C;
                    font-family: monospace;
                    font-size: 13px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                ">
                    ID: {uid}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. Hızlı Erişim Kısayolları
        st.markdown(
            "<h4 style='color:#E2E8F0; font-size:15px; margin-bottom:10px;'>⚡ Hızlı Çalışma Masası</h4>",
            unsafe_allow_html=True,
        )
        col_q1, col_q2, col_q3, col_q4 = st.columns(4)

        with col_q1:
            if st.button("🏛️ Adliye & Mevzuat", use_container_width=True):
                st.session_state.aktif_ekran = "Adliye"
                st.rerun()
        with col_q2:
            if st.button("📝 Dilekçe Merkezi", use_container_width=True):
                st.session_state.aktif_ekran = "Dilekçe Merkezi"
                st.rerun()
        with col_q3:
            if st.button("⚖️ İçtihat Sorgulama", use_container_width=True):
                st.session_state.aktif_ekran = "İçtihat Sorgulama"
                st.rerun()
        with col_q4:
            if st.button("💬 JUNILEX Chat", type="primary", use_container_width=True):
                st.session_state.aktif_ekran = "💬 JUNILEX Chat"
                st.rerun()

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        # 3. Aktivite Metrikleri
        st.markdown(
            """
            <div style="
                background: #131822; 
                padding: 16px 20px; 
                border-radius: 12px; 
                border: 1px solid #232B3E; 
                border-top: 3px solid #C9A84C; 
                margin-bottom: 16px;
            ">
                <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">📊 Hukuki İşlem & Arşiv Özeti</h4>
                <p style="color: #8A99AD; font-size: 12px; margin: 0;">Hesabınıza bağlı üretilen evrak ve analiz istatistikleri.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        try:
            db_fs = get_db()
            tum_kayitlar = list(
                db_fs.collection("junilex_arsiv")
                .where("kullanici", "==", st.session_state.aktif_kullanici)
                .stream()
            )

            toplam_islem = len(tum_kayitlar)
            mevzuat_sayisi = sum(
                1 for d in tum_kayitlar if "Mevzuat" in d.to_dict().get("kategori", "")
            )
            dilekce_sayisi = sum(
                1 for d in tum_kayitlar if "Dilekçe" in d.to_dict().get("kategori", "")
            )
            ictihat_sayisi = sum(
                1 for d in tum_kayitlar if "İçtihat" in d.to_dict().get("kategori", "")
            )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Toplam Kayıt", toplam_islem)
            m2.metric("Mevzuat Şerhi", mevzuat_sayisi)
            m3.metric("Dilekçe Taslağı", dilekce_sayisi)
            m4.metric("İçtihat Analizi", ictihat_sayisi)

        except Exception as e:
            st.caption("Aktivite verileri yüklenemedi.")

        st.write("---")

        # 4. Son İşlemler Paneli
        st.markdown(
            "<h4 style='color:#E2E8F0; font-size:16px; margin-bottom:12px;'>🕒 Son Çalışılan Evraklar</h4>",
            unsafe_allow_html=True,
        )

        try:
            recent = (
                db_fs.collection("junilex_arsiv")
                .where("kullanici", "==", st.session_state.aktif_kullanici)
                .order_by("tarih", direction=firestore.Query.DESCENDING)
                .limit(3)
                .stream()
            )
            found = False
            for doc in recent:
                d = doc.to_dict()
                found = True

                st.markdown(
                    f"""
                    <div style="
                        background-color: #0B0E14; 
                        padding: 16px 20px; 
                        border-radius: 10px; 
                        border: 1px solid #232B3E; 
                        border-left: 4px solid #C9A84C; 
                        margin-bottom: 10px;
                        display: flex;
                        align-items: center;
                        gap: 14px;
                    ">
                        <div style="font-size: 24px;">📄</div>
                        <div style="flex-grow: 1;">
                            <div style="color: #E2E8F0; font-weight: 700; font-size: 15px;">{d.get('baslik')}</div>
                            <div style="color: #8A99AD; font-size: 12px; margin-top: 2px;">Kategori: {d.get('kategori')}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if not found:
                st.markdown(
                    """
                    <div style="
                        text-align: center; 
                        padding: 30px 20px; 
                        background-color: #0B0E14; 
                        border-radius: 10px; 
                        border: 1px solid #232B3E; 
                        color: #8A99AD;
                        font-size: 13px;
                    ">
                        🗄️ Henüz geçmiş bir işleminiz bulunmuyor. Sol menüden bir modül seçerek başlayabilirsiniz.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        except Exception as e:
            st.error(f"Veri çekilemedi: {e}")

    # ==========================================
    # 👥 JUNILEX AĞI (SOSYAL AĞ VE EKİPLER - Premium SaaS UI)
    # ==========================================
    elif st.session_state.aktif_ekran in [
        "👥 Junilex Ağı",
        "Junilex Ağı",
        "Ağ ve Ekipler",
    ]:

        # 1. Modül Başlık Kartı
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #131822 0%, #1A212E 100%);
                border: 1px solid #232B3E;
                border-left: 4px solid #C9A84C;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 20px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            ">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="font-size:24px; color:#C9A84C;">👥</div>
                    <div>
                        <h3 style="margin:0; color:#E2E8F0; font-family:'DM Sans',sans-serif; font-size:20px; font-weight:700;">
                            Junilex Ağı & Ekip Yönetimi
                        </h3>
                        <p style="margin:4px 0 0 0; color:#8A99AD; font-size:13px;">
                            Meslektaşlarınızla bağlantı kurun, çalışma grupları oluşturun, ortak arşivde eş zamanlı çalışın.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        benim_mailim = st.session_state.aktif_kullanici_email

        # 2. Üst Bilgi Barı (ID ve Bildirimler)
        col_id, col_bildirim = st.columns([4, 1], gap="small")
        with col_id:
            st.markdown(
                f"""
                <div style="
                    background: #131822; 
                    padding: 12px 18px; 
                    border-radius: 10px; 
                    border: 1px solid #232B3E; 
                    border-left: 3px solid #C9A84C;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                ">
                    <span style="color: #8A99AD; font-size: 13px;">📌 Senin JUNILEX ID'n:</span>
                    <span style="color: #C9A84C; font-family: monospace; font-size: 15px; font-weight: 700; background: #0B0E14; padding: 2px 8px; border-radius: 6px; border: 1px solid #232B3E;">
                        {st.session_state.aktif_kullanici_id}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_bildirim:
            with st.popover("🔔 Bildirimler", use_container_width=True):
                st.markdown(
                    "<h4 style='color:#E2E8F0; font-size:15px; margin-bottom:10px;'>📢 Son Hareketler</h4>",
                    unsafe_allow_html=True,
                )
                try:
                    db_fs = get_db()
                    bildirimler = AgEngine.bildirimleri_getir(db_fs, benim_mailim)
                    if not bildirimler:
                        st.caption("Şu an yeni bir bildiriminiz yok.")
                    else:
                        for b in bildirimler:
                            st.info(b.get("mesaj"))
                except Exception as e:
                    if "index" in str(e).lower():
                        st.error("Bildirimler için Index bekleniyor...")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        st.session_state.kullanici_veritabani = veritabani_yukle()
        db_json = st.session_state.kullanici_veritabani
        benim_verim = db_json.get(benim_mailim, {})

        gelen_istekler = benim_verim.get("gelen_istekler", [])
        arkadaslar = benim_verim.get("arkadaslar", [])

        tab_ara, tab_istekler, tab_arkadaslar, tab_ekipler = st.tabs(
            [
                "🔍 Kişi Ara",
                f"🔔 İstekler ({len(gelen_istekler)})",
                f"🤝 Arkadaşlarım ({len(arkadaslar)})",
                "🏢 Ekiplerim ve Arşiv",
            ]
        )

        # ── TAB 1: KİŞİ ARA ──────────────────────────────────────────────────
        with tab_ara:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">🔍 Hukukçu Bul</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Bağlantı kurmak istediğiniz meslektaşınızın 5 haneli Junilex ID'sini girin.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_input, col_btn = st.columns([4, 1])
            with col_input:
                aranan_id = st.text_input(
                    "Arama",
                    label_visibility="collapsed",
                    placeholder="Kullanıcının 5 Haneli ID'sini Girin (Örn: #12345)",
                )
            with col_btn:
                btn_ara = st.button(
                    "Ağda Ara", use_container_width=True, type="primary"
                )

            if btn_ara:
                st.session_state.son_aranan_id = aranan_id

            if st.session_state.get("son_aranan_id"):
                st.write("---")
                bulunan_mail, bulunan_isim = AgEngine.kisi_ara(
                    db_json, st.session_state.son_aranan_id
                )

                if bulunan_mail:
                    if bulunan_mail == benim_mailim:
                        st.warning("⚠️ Kendinizi ekleyemezsiniz.")
                    elif bulunan_mail in arkadaslar:
                        st.info(f"✅ **{bulunan_isim}** zaten sizinle bağlantılı.")
                    else:
                        st.markdown(
                            f"""
                            <div style="
                                background-color: #0B0E14; 
                                padding: 20px 24px; 
                                border-radius: 10px; 
                                border: 1px solid #232B3E; 
                                border-left: 4px solid #C9A84C; 
                                display: flex; 
                                align-items: center; 
                                justify-content: space-between;
                                margin-bottom: 16px;
                            ">
                                <div>
                                    <div style="font-size: 17px; font-weight: 700; color: #E2E8F0;">{bulunan_isim}</div>
                                    <div style="color: #8A99AD; font-size: 13px;">Junilex Ağı Kullanıcısı</div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        karsi_istekler = db_json[bulunan_mail].get("gelen_istekler", [])
                        if benim_mailim in karsi_istekler:
                            st.info(
                                "⏳ Bu kullanıcıya zaten bağlantı isteği gönderdiniz. Yanıt bekleniyor..."
                            )
                        else:
                            if st.button(
                                "➕ Bağlantı Kur", key="btn_istek_at", type="primary"
                            ):
                                db_json = AgEngine.arkadaslik_istegi_gonder(
                                    db_json, benim_mailim, bulunan_mail
                                )
                                veritabani_kaydet(db_json)
                                st.session_state.son_aranan_id = None
                                st.success("✅ İstek başarıyla gönderildi!")
                                st.rerun()
                else:
                    st.error("❌ Bu ID'ye ait bir Junilex kullanıcısı bulunamadı.")

            else:
                st.write("---")
                st.markdown(
                    "<h4 style='color:#E2E8F0; font-size:16px;'>Önerilen Meslektaşlar</h4>",
                    unsafe_allow_html=True,
                )
                st.caption("Ağınızı genişletmek için size önerilen profiller:")

                c1, c2, c3 = st.columns(3)

                vitrin_html = """
                <div style="
                    background-color: #0B0E14; 
                    padding: 20px 16px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    text-align: center; 
                    margin-bottom: 12px;
                ">
                    <div style="font-size: 32px; margin-bottom: 8px;">👤</div>
                    <div style="font-weight: 700; color: #E2E8F0; font-size: 15px;">{isim}</div>
                    <div style="color: #8A99AD; font-size: 12px; margin-top: 4px;">{unvan}</div>
                </div>
                """

                onerilenler = AgEngine.onerilen_meslektaslari_getir(
                    db_json, benim_mailim
                )
                kolonlar = [c1, c2, c3]

                if not onerilenler:
                    st.info(
                        "Ağ henüz çok yeni. Profilinize meslektaşlarınızı davet edin!"
                    )
                else:
                    for i, kisi in enumerate(onerilenler):
                        if i < len(kolonlar):
                            with kolonlar[i]:
                                st.markdown(
                                    vitrin_html.format(
                                        isim=kisi["isim"], unvan=kisi["unvan"]
                                    ),
                                    unsafe_allow_html=True,
                                )
                                st.button(
                                    "Profili İncele",
                                    key=f"vitrin_btn_{i}",
                                    use_container_width=True,
                                )

        # ── TAB 2: İSTEKLER ──────────────────────────────────────────────────
        with tab_istekler:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">🔔 Gelen Bağlantı İstekleri</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Sizinle iletişim kurmak isteyen meslektaşlarınızın isteklerini yönetin.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if not gelen_istekler:
                st.info("Şu an bekleyen bir bağlantı isteğiniz yok.")
            else:
                for istek_mail in gelen_istekler:
                    istek_isim = db_json.get(istek_mail, {}).get("isim", "Bilinmeyen")
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #0B0E14; 
                            padding: 16px 20px; 
                            border-radius: 10px; 
                            border: 1px solid #232B3E; 
                            margin-bottom: 12px;
                        ">
                        """,
                        unsafe_allow_html=True,
                    )
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(
                            f"👤 <span style='color:#E2E8F0; font-weight:600;'>{istek_isim}</span> <span style='color:#8A99AD;'>seninle bağlantı kurmak istiyor.</span>",
                            unsafe_allow_html=True,
                        )
                    with col2:
                        if st.button(
                            "✅ Kabul Et",
                            key=f"kabul_{istek_mail}",
                            use_container_width=True,
                            type="primary",
                        ):
                            db_json = AgEngine.istek_kabul_et(
                                db_json, benim_mailim, istek_mail
                            )
                            veritabani_kaydet(db_json)
                            st.success("Bağlantı kuruldu!")
                            st.rerun()
                    with col3:
                        if st.button(
                            "❌ Reddet",
                            key=f"reddet_{istek_mail}",
                            use_container_width=True,
                        ):
                            db_json = AgEngine.istek_reddet(
                                db_json, benim_mailim, istek_mail
                            )
                            veritabani_kaydet(db_json)
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        # ── TAB 3: ARKADAŞLARIM ──────────────────────────────────────────────
        with tab_arkadaslar:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">🤝 Bağlantılı Olduğum Kişiler</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Ağınızdaki aktif hukukçuları inceleyin veya yönetin.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if not arkadaslar:
                st.info(
                    "Henüz ekli bir meslektaşınız yok. 'Kişi Ara' sekmesinden Junilex ID'si ile bağlantı kurmaya başlayın!"
                )
            else:
                for ark_mail in arkadaslar:
                    ark_data = db_json.get(ark_mail, {})
                    ark_isim = ark_data.get("isim", "Bilinmeyen")
                    ark_id = ark_data.get("id", "")

                    st.markdown(
                        f"""
                        <div style="
                            background-color: #0B0E14; 
                            padding: 14px 18px; 
                            border-radius: 10px; 
                            border: 1px solid #232B3E; 
                            margin-bottom: 10px;
                        ">
                        """,
                        unsafe_allow_html=True,
                    )
                    col_isim, col_profil, col_sil = st.columns([3, 1, 1])
                    with col_isim:
                        st.markdown(
                            f"🤝 <span style='color:#E2E8F0; font-weight:600;'>{ark_isim}</span> <code style='color:#C9A84C;'>({ark_id})</code>",
                            unsafe_allow_html=True,
                        )

                    with col_profil:
                        with st.popover("👁️ Profili Gör", use_container_width=True):
                            st.markdown(
                                f"<h4 style='color:#E2E8F0; margin:0;'>{ark_isim}</h4>",
                                unsafe_allow_html=True,
                            )
                            st.caption(f"Junilex ID: {ark_id}")
                            st.divider()
                            st.write(
                                f"📅 **Ağa Katılım:** {ark_data.get('kayit_tarihi', 'Bilinmiyor')}"
                            )
                            ortak_bag = set(
                                ark_data.get("arkadaslar", [])
                            ).intersection(set(arkadaslar))
                            st.write(f"👥 **Ortak Bağlantı:** {len(ortak_bag)} kişi")

                            try:
                                ark_arsiv = (
                                    get_db()
                                    .collection("junilex_arsiv")
                                    .where("kullanici", "==", ark_isim)
                                    .get()
                                )
                                st.write(
                                    f"📊 **Hukuki İşlem Hacmi:** {len(ark_arsiv)} Evrak"
                                )
                            except Exception:
                                st.write("📊 Aktivite verisi alınamadı.")

                    with col_sil:
                        if st.button(
                            "Kaldır",
                            key=f"sil_ark_{ark_mail}",
                            use_container_width=True,
                        ):
                            db_json = AgEngine.arkadas_cikar(
                                db_json, benim_mailim, ark_mail
                            )
                            veritabani_kaydet(db_json)
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        # ── TAB 4: EKİPLERİM VE ARŞİV ─────────────────────────────────────────
        with tab_ekipler:
            db_fs = get_db()
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            c_kur, c_katil = st.columns(2, gap="medium")

            with c_kur:
                st.markdown(
                    """
                    <div style="
                        background: #131822; 
                        padding: 16px 20px; 
                        border-radius: 12px; 
                        border: 1px solid #232B3E; 
                        border-top: 3px solid #C9A84C; 
                        margin-bottom: 16px;
                    ">
                        <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">🛠️ Yeni Ekip Kur</h4>
                        <p style="color: #8A99AD; font-size: 12px; margin: 0;">Çalışma arkadaşlarınızla ortak alan oluşturun.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                ekip_adi = st.text_input("Ekip Adı", placeholder="Örn: Ceza Departmanı")
                if st.button("🚀 Ekip Kur", use_container_width=True, type="primary"):
                    if ekip_adi:
                        yeni_id = AgEngine.ekip_kur(
                            db_fs,
                            ekip_adi,
                            benim_mailim,
                            st.session_state.aktif_kullanici,
                        )
                        st.success(f"✅ Ekip kuruldu! ID: {yeni_id}")
                        st.rerun()

            with c_katil:
                st.markdown(
                    """
                    <div style="
                        background: #131822; 
                        padding: 16px 20px; 
                        border-radius: 12px; 
                        border: 1px solid #232B3E; 
                        border-top: 3px solid #C9A84C; 
                        margin-bottom: 16px;
                    ">
                        <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">🚪 Ekibe Katıl</h4>
                        <p style="color: #8A99AD; font-size: 12px; margin: 0;">Mevcut bir ekibin davet ID'si ile katılma isteği atın.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                girilen_ekip_id = st.text_input(
                    "Ekip ID'si Girin", placeholder="Örn: EKP-12345"
                )
                if st.button("İstek Gönder", use_container_width=True):
                    basarili = AgEngine.ekibe_katilma_istegi_gonder(
                        db_fs, girilen_ekip_id, benim_mailim
                    )
                    if basarili:
                        st.success("✅ Katılma isteği gönderildi.")
                    else:
                        st.error("❌ Böyle bir ekip ID'si bulunamadı.")

            st.write("---")
            st.markdown(
                "<h4 style='color:#E2E8F0; font-size:16px;'>🏢 Ekiplerim ve Yönetim</h4>",
                unsafe_allow_html=True,
            )

            ekiplerim_doc_listesi = AgEngine.ekiplerimi_getir(db_fs, benim_mailim)

            for doc in ekiplerim_doc_listesi:
                ekip = doc.to_dict()
                g_id = ekip.get("ekip_id", "ID Yok")
                g_isim = ekip.get("isim", "İsimsiz")
                g_uyeler = ekip.get("uyeler_isim", [])

                with st.expander(f"🏢 {g_isim} ({g_id})"):
                    st.info(f"🔑 **Ekip ID:** `{g_id}`")
                    st.write(f"👥 **Üyeler:** {', '.join(g_uyeler)}")

                    if ekip.get("kurucu") == benim_mailim:
                        if ekip.get("istekler"):
                            st.write("📩 **Bekleyen Katılım İstekleri:**")
                            for istek_mail in ekip.get("istekler", []):
                                col_istek, col_onay = st.columns([3, 1])
                                col_istek.write(f"👤 {istek_mail}")
                                if col_onay.button(
                                    "✅ Onayla", key=f"onay_{istek_mail}_{doc.id}"
                                ):
                                    istek_isim = db_json.get(istek_mail, {}).get(
                                        "isim", "Üye"
                                    )
                                    AgEngine.ekip_istek_onayla(
                                        doc.reference, istek_mail, istek_isim
                                    )
                                    st.rerun()

                        st.write("---")
                        if st.button(
                            "🗑️ EKİBİ TAMAMEN SİL",
                            key=f"sil_{doc.id}",
                            type="primary",
                            use_container_width=True,
                        ):
                            doc.reference.delete()
                            st.warning("Ekip silindi!")
                            st.rerun()

            st.write("---")
            st.markdown(
                "<h4 style='color:#E2E8F0; font-size:16px;'>🖥️ Aktif Ekip Çalışma Paneli</h4>",
                unsafe_allow_html=True,
            )

            if ekiplerim_doc_listesi:
                ekip_katalogu = {
                    d.to_dict().get("isim"): d for d in ekiplerim_doc_listesi
                }
                secilen_ekip_adi = st.selectbox(
                    "Çalışacağın Ekibi Seç:", list(ekip_katalogu.keys())
                )
                aktif_ekip_doc = ekip_katalogu[secilen_ekip_adi]
                aktif_ekip = aktif_ekip_doc.to_dict()
                aktif_ekip_id = aktif_ekip.get("ekip_id")

                st.markdown(
                    f"📌 **Aktif Ekip Üyeleri:** <span style='color:#C9A84C; font-weight:600;'>{', '.join(aktif_ekip.get('uyeler_isim', []))}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

                alt_tab_arsiv, alt_tab_sohbet, alt_tab_gorevler = st.tabs(
                    ["🗂️ Ortak Arşiv", "💬 Ekip İçi Sohbet", "📅 Görev ve Duruşmalar"]
                )

                # ── SUB TAB 1: ORTAK ARŞİV ───────────────────────────────────
                with alt_tab_arsiv:
                    st.markdown(
                        "<div style='height:8px'></div>", unsafe_allow_html=True
                    )
                    with st.expander("➕ Belge Yükle / Paylaş"):
                        y_baslik = st.text_input("Belge Başlığı")
                        y_metin = st.text_area("Belge İçeriği / Notlar")
                        if st.button(
                            "Belgeyi Arşive Ekle",
                            use_container_width=True,
                            type="primary",
                        ):
                            if y_baslik and y_metin:
                                AgEngine.evrak_yukle(
                                    db_fs,
                                    aktif_ekip_id,
                                    y_baslik,
                                    y_metin,
                                    st.session_state.aktif_kullanici,
                                )
                                st.success("✅ Belge ekibe başarıyla yüklendi!")
                                st.rerun()
                            else:
                                st.warning("⚠️ Başlık ve içerik boş olamaz.")

                    st.write("---")

                    ortak_evraklar = AgEngine.ekip_ortak_arsiv_getir(
                        db_fs, aktif_ekip.get("uyeler_isim", [])
                    )

                    if not ortak_evraklar:
                        st.markdown(
                            """
                            <div style="
                                text-align: center; 
                                padding: 40px 20px; 
                                background-color: #0B0E14; 
                                border-radius: 12px; 
                                border: 1px solid #232B3E; 
                                margin: 16px 0;
                            ">
                                <div style="font-size: 40px; margin-bottom: 10px;">🗄️</div>
                                <h4 style="color: #E2E8F0; margin-bottom: 4px;">Arşiv Henüz Boş</h4>
                                <p style="color: #8A99AD; font-size: 13px; margin: 0;">İlk belgenizi yukarıdaki formdan yükleyin ve ekibinizle paylaşın.</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            "<h5 style='color:#E2E8F0;'>📂 Ortak Çalışma Belgeleri</h5>",
                            unsafe_allow_html=True,
                        )
                        for evrak in ortak_evraklar:
                            e_data = evrak.to_dict()
                            st.markdown(
                                f"""
                                <div style="
                                    background-color: #0B0E14; 
                                    padding: 14px; 
                                    border-radius: 10px; 
                                    border: 1px solid #232B3E; 
                                    margin-bottom: 10px;
                                ">
                                """,
                                unsafe_allow_html=True,
                            )
                            col_icon, col_info, col_btn = st.columns([1, 6, 2])
                            with col_icon:
                                st.markdown(
                                    "<h3 style='margin:0;'>📄</h3>",
                                    unsafe_allow_html=True,
                                )
                            with col_info:
                                st.markdown(
                                    f"<span style='color:#E2E8F0; font-weight:700;'>{e_data.get('baslik')}</span>",
                                    unsafe_allow_html=True,
                                )
                                st.caption(
                                    f"Yükleyen: {e_data.get('kullanici')} | Ortak Arşiv"
                                )
                            with col_btn:
                                st.download_button(
                                    "📥 İndir",
                                    data=e_data.get("metin", ""),
                                    file_name=f"{e_data.get('baslik')}.txt",
                                    key=f"dl_{evrak.id}",
                                    use_container_width=True,
                                )

                            with st.expander("Metni İncele"):
                                st.text(e_data.get("metin"))
                            st.markdown("</div>", unsafe_allow_html=True)

                import time

                # ── SUB TAB 2: EKİP İÇİ SOHBET ────────────────────────────────
                with alt_tab_sohbet:
                    st.markdown(
                        "<div style='height:8px'></div>", unsafe_allow_html=True
                    )

                    @st.fragment(run_every=3)
                    def sohbeti_otomatik_guncelle():
                        sohbet_alani = st.container(height=400)
                        try:
                            db_mesajlari = AgEngine.sohbet_mesajlarini_getir(
                                db_fs, aktif_ekip_id
                            )

                            son_mesaj = st.session_state.get("bekleyen_mesaj", "")
                            db_de_var_mi = any(
                                m.get("mesaj") == son_mesaj
                                and m.get("isim") == st.session_state.aktif_kullanici
                                for m in db_mesajlari
                            )

                            with sohbet_alani:
                                mesaj_var_mi = False

                                for m_data in db_mesajlari:
                                    mesaj_var_mi = True
                                    gonderen = m_data.get("isim", "Bilinmeyen")
                                    mesaj = m_data.get("mesaj", "")

                                    if gonderen == st.session_state.aktif_kullanici:
                                        with st.chat_message("user", avatar="🧑‍💻"):
                                            st.markdown(f"**Sen:** {mesaj}")
                                    else:
                                        with st.chat_message("assistant", avatar="👤"):
                                            st.markdown(f"**{gonderen}:** {mesaj}")

                                if son_mesaj and not db_de_var_mi:
                                    if (
                                        time.time()
                                        - st.session_state.get(
                                            "bekleyen_mesaj_zamani", 0
                                        )
                                        < 5
                                    ):
                                        mesaj_var_mi = True
                                        with st.chat_message("user", avatar="⏳"):
                                            st.markdown(f"**Sen:** {son_mesaj}")

                                if not mesaj_var_mi:
                                    st.markdown(
                                        """
                                        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; text-align: center; color: #8A99AD; padding: 20px;">
                                            <div style="font-size: 50px; margin-bottom: 12px;">💬</div>
                                            <h4 style="color: #E2E8F0; margin-bottom: 6px;">Henüz Sohbet Başlamadı</h4>
                                            <p style="max-width: 320px; font-size: 13px;">Ekibinle dosya detayları, duruşma notları veya stratejiler üzerine konuşmak için bir mesaj gönderin.</p>
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )
                        except Exception as e:
                            if "index" not in str(e).lower():
                                st.error(f"Sohbet yüklenemedi: {e}")

                    sohbeti_otomatik_guncelle()

                    if yeni_mesaj := st.chat_input("Ekibe mesaj yaz..."):
                        st.session_state.bekleyen_mesaj = yeni_mesaj
                        st.session_state.bekleyen_mesaj_zamani = time.time()

                        AgEngine.arka_planda_mesaj_gonder(
                            aktif_ekip_id, st.session_state.aktif_kullanici, yeni_mesaj
                        )

                        st.rerun()

                # ── SUB TAB 3: GÖREV VE DURUŞMALAR (KANBAN) ───────────────────
                with alt_tab_gorevler:
                    st.markdown(
                        "<div style='height:8px'></div>", unsafe_allow_html=True
                    )

                    with st.expander("➕ Yeni Görev / Duruşma Ata"):
                        g_baslik = st.text_input(
                            "Görev Başlığı",
                            placeholder="Örn: X Şirketi Sözleşme İncelemesi",
                        )
                        g_aciklama = st.text_area(
                            "Açıklama / Detaylar",
                            placeholder="Dosya no, tarih veya notlar...",
                        )
                        g_atanan = st.selectbox(
                            "Kime Atanacak?", aktif_ekip.get("uyeler_isim", [])
                        )

                        if st.button(
                            "Görevi Kaydet", use_container_width=True, type="primary"
                        ):
                            if g_baslik:
                                AgEngine.gorev_ekle(
                                    db_fs,
                                    aktif_ekip_id,
                                    g_baslik,
                                    g_aciklama,
                                    g_atanan,
                                    st.session_state.aktif_kullanici,
                                    aktif_ekip.get("uyeler_mail", []),
                                )
                                st.success("✅ Görev başarıyla eklendi!")
                                st.rerun()
                            else:
                                st.warning("⚠️ Görev başlığı boş bırakılamaz.")

                    st.write("---")

                    try:
                        gorevler = AgEngine.gorevleri_getir(db_fs, aktif_ekip_id)

                        if not gorevler:
                            st.markdown(
                                """
                                <div style="
                                    text-align: center; 
                                    padding: 36px 20px; 
                                    background-color: #0B0E14; 
                                    border-radius: 12px; 
                                    border: 1px dashed #232B3E; 
                                    margin: 16px 0;
                                ">
                                    <div style="font-size: 44px; margin-bottom: 8px;">🗂️</div>
                                    <h4 style="color: #E2E8F0; margin-bottom: 4px; font-weight: 600;">Masa Tertemiz!</h4>
                                    <p style="color: #8A99AD; font-size: 13px; margin: 0;">Şu an ekibe atanmış aktif bir görev veya duruşma bulunmuyor.</p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            st.caption("⚡ Hızlı Şablonlarla Görev Oluştur:")
                            c_h1, c_h2, c_h3 = st.columns(3)
                            if c_h1.button("⚖️ Duruşma Ekle", use_container_width=True):
                                AgEngine.gorev_ekle(
                                    db_fs,
                                    aktif_ekip_id,
                                    "Yaklaşan Duruşma Hazırlığı",
                                    "Duruşma tarihi, saati ve dosya numarası:",
                                    st.session_state.aktif_kullanici,
                                    st.session_state.aktif_kullanici,
                                    aktif_ekip.get("uyeler_mail", []),
                                )
                                st.rerun()
                            if c_h2.button(
                                "📄 Sözleşme İncele", use_container_width=True
                            ):
                                AgEngine.gorev_ekle(
                                    db_fs,
                                    aktif_ekip_id,
                                    "Sözleşme İncelemesi",
                                    "Müvekkilden gelen sözleşmenin risk analizi yapılacak.",
                                    st.session_state.aktif_kullanici,
                                    st.session_state.aktif_kullanici,
                                    aktif_ekip.get("uyeler_mail", []),
                                )
                                st.rerun()
                            if c_h3.button(
                                "🤝 Müvekkil Görüşmesi", use_container_width=True
                            ):
                                AgEngine.gorev_ekle(
                                    db_fs,
                                    aktif_ekip_id,
                                    "Müvekkil Toplantısı",
                                    "Toplantı notları ve talep edilen evraklar hazırlanacak.",
                                    st.session_state.aktif_kullanici,
                                    st.session_state.aktif_kullanici,
                                    aktif_ekip.get("uyeler_mail", []),
                                )
                                st.rerun()
                        else:
                            col_yap, col_devam, col_bit = st.columns(3)

                            with col_yap:
                                st.markdown(
                                    "<h4 style='color:#E2E8F0; font-size:15px;'>🔴 Yapılacaklar</h4>",
                                    unsafe_allow_html=True,
                                )
                            with col_devam:
                                st.markdown(
                                    "<h4 style='color:#E2E8F0; font-size:15px;'>🟡 Devam Edenler</h4>",
                                    unsafe_allow_html=True,
                                )
                            with col_bit:
                                st.markdown(
                                    "<h4 style='color:#E2E8F0; font-size:15px;'>🟢 Tamamlananlar</h4>",
                                    unsafe_allow_html=True,
                                )

                            for g in gorevler:
                                durum = g.get("durum", "Yapılacak")
                                kart_icerik = f"**{g.get('baslik')}**\n\n👤 *Atanan: {g.get('atanan')}*\n\n📝 {g.get('aciklama')}"

                                if durum == "Yapılacak":
                                    with col_yap:
                                        with st.container(border=True):
                                            st.markdown(kart_icerik)
                                            c1, c2 = st.columns(2)
                                            if c1.button(
                                                "Başla ➡️",
                                                key=f"basla_{g['id']}",
                                                use_container_width=True,
                                                type="primary",
                                            ):
                                                AgEngine.gorev_durumu_guncelle(
                                                    db_fs,
                                                    g["id"],
                                                    "Devam Ediyor",
                                                    g.get("baslik"),
                                                    st.session_state.aktif_kullanici,
                                                    aktif_ekip.get("uyeler_mail", []),
                                                )
                                                st.rerun()
                                            if c2.button(
                                                "🗑️ Sil",
                                                key=f"sil_yap_{g['id']}",
                                                use_container_width=True,
                                            ):
                                                AgEngine.gorev_sil(db_fs, g["id"])
                                                st.rerun()

                                elif durum == "Devam Ediyor":
                                    with col_devam:
                                        with st.container(border=True):
                                            st.markdown(kart_icerik)
                                            c1, c2 = st.columns(2)
                                            if c1.button(
                                                "Bitti ✅",
                                                key=f"bitir_{g['id']}",
                                                use_container_width=True,
                                                type="primary",
                                            ):
                                                AgEngine.gorev_durumu_guncelle(
                                                    db_fs,
                                                    g["id"],
                                                    "Tamamlandı",
                                                    g.get("baslik"),
                                                    st.session_state.aktif_kullanici,
                                                    aktif_ekip.get("uyeler_mail", []),
                                                )
                                                st.rerun()
                                            if c2.button(
                                                "Geri ⬅️",
                                                key=f"geri_{g['id']}",
                                                use_container_width=True,
                                            ):
                                                AgEngine.gorev_durumu_guncelle(
                                                    db_fs,
                                                    g["id"],
                                                    "Yapılacak",
                                                    g.get("baslik"),
                                                    st.session_state.aktif_kullanici,
                                                    aktif_ekip.get("uyeler_mail", []),
                                                )
                                                st.rerun()

                                elif durum == "Tamamlandı":
                                    with col_bit:
                                        with st.container(border=True):
                                            st.markdown(kart_icerik)
                                            if st.button(
                                                "🗑️ Arşivden Sil",
                                                key=f"sil_bit_{g['id']}",
                                                use_container_width=True,
                                            ):
                                                AgEngine.gorev_sil(db_fs, g["id"])
                                                st.rerun()
                    except Exception as e:
                        if "index" in str(e).lower():
                            st.error(
                                "⚠️ Görev panosu için veritabanı dizin kurulumu gerekiyor. Lütfen terminal (Log) ekranındaki linke tıklayarak dizini oluşturun."
                            )
                        else:
                            st.error(f"Görevler yüklenemedi: {e}")
    # ==========================================
    # 🏛️ ADLİYE MODÜLÜ (Export Hub & UDF Destekli SaaS UI)
    # ==========================================
    elif st.session_state.aktif_ekran in [
        "Adliye (Mevzuat Sorgu)",
        "Adliye",
        "🏛️ Adliye",
    ]:

        # 1. Modül Başlık Kartı
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #131822 0%, #1A212E 100%);
                border: 1px solid #232B3E;
                border-left: 4px solid #C9A84C;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 20px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            ">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="font-size:26px; color:#C9A84C;">🏛️</div>
                    <div>
                        <h3 style="margin:0; color:#E2E8F0; font-family:'DM Sans',sans-serif; font-size:20px; font-weight:700;">
                            Adliye & Mevzuat Hub
                        </h3>
                        <p style="margin:4px 0 0 0; color:#8A99AD; font-size:13px;">
                            Güncel kanunlarda yapay zeka ile derinlemesine arama yapın, maddeleri analiz edin ve UYAP UDF / TXT formatında dışa aktarın.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        kanun_listesi = MevzuatBulutEngine.get_kanunlar()

        # 2. Kanun Kütüphanesi Filtre Kartı
        st.markdown(
            """
            <div style="
                background: #131822; 
                padding: 18px 20px; 
                border-radius: 12px; 
                border: 1px solid #232B3E; 
                border-top: 3px solid #C9A84C; 
                margin-bottom: 16px;
            ">
                <h4 style="margin:0 0 6px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">📚 Kanun Kütüphanesi</h4>
                <p style="color: #8A99AD; font-size: 12px; margin: 0;">Filtreleme yaparak çalışmak istediğiniz mevzuatı belirleyin.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        filtre_col, secim_col = st.columns(2)
        with filtre_col:
            kategoriler = ["Tüm Alanlar"] + sorted(
                list(set([k["kategori"] for k in kanun_listesi]))
            )
            secilen_kategori = st.selectbox(
                "Hukuk Alanı Filtresi", kategoriler, label_visibility="collapsed"
            )

        if secilen_kategori == "Tüm Alanlar":
            filtrelenmis_kanunlar = kanun_listesi
        else:
            filtrelenmis_kanunlar = [
                k for k in kanun_listesi if k["kategori"] == secilen_kategori
            ]

        with secim_col:
            gosterim_adlari = [
                f"{k['kisaAd']} | {k['isim']}" for k in filtrelenmis_kanunlar
            ]
            secilen_gosterim = st.selectbox(
                "İlgili Kanun Mevzuatı", gosterim_adlari, label_visibility="collapsed"
            )

        secilen_indeks = gosterim_adlari.index(secilen_gosterim)
        secilen_kanun = filtrelenmis_kanunlar[secilen_indeks]

        # 3. Mevzuat Metadata Kartı
        st.markdown(
            f"""
            <div style="
                background: #0B0E14; 
                padding: 12px 18px; 
                border-radius: 10px; 
                border: 1px solid #232B3E; 
                margin-bottom: 24px;
            ">
                <span style="color: #8A99AD; font-size: 12px; font-family:'DM Sans', sans-serif;">
                    📌 <b style="color:#E2E8F0;">Kategori:</b> {secilen_kanun['kategori']} &nbsp;|&nbsp; 
                    <b style="color:#E2E8F0;">Kanun No:</b> <span style="color:#C9A84C;">{secilen_kanun['id']}</span> &nbsp;|&nbsp; 
                    <b style="color:#E2E8F0;">Kapsam:</b> {secilen_kanun['aciklama']}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4. Arama Sekmeleri
        arama_sekmeleri = st.tabs(
            ["🔢 Madde Numarası İle Arama", "🔤 Kelime / Kavram İle Tarama"]
        )

        api_key = st.session_state.get(
            "gemini_api_key", MY_API_KEY if "MY_API_KEY" in globals() else ""
        )

        # ── TAB 1: MADDE NUMARASI İLE ARAMA ──
        with arama_sekmeleri[0]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 10px; 
                    border: 1px solid #232B3E;
                    border-left: 4px solid #C9A84C;
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0; color: #E2E8F0; font-size: 15px; font-weight:600;">🔍 Doğrudan Madde Çağır</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 4px 0 0 0;">Maddenin numarasını girerek tam metne, yapay zeka analizine ve dışa aktarım seçeneklerine ulaşın.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            giriş_col, buton_col = st.columns([4, 1])
            with giriş_col:
                varsayilan_madde_no = st.session_state.get("son_aranan_madde", "")
                girilen_madde = st.text_input(
                    "Aranacak Madde Numarası",
                    value=varsayilan_madde_no,
                    placeholder="Örn: 86, Geçici_1...",
                    key="input_no",
                    label_visibility="collapsed",
                )
            with buton_col:
                madde_ara_butonu = st.button(
                    "Maddeyi Getir",
                    use_container_width=True,
                    type="primary",
                    key="btn_no_ara",
                )

            if madde_ara_butonu and girilen_madde:
                st.session_state.pop("capraz_onizleme_no", None)
                with st.spinner("Hafızadan madde getiriliyor..."):
                    sonuc = MevzuatBulutEngine.madde_getir_buluttan(
                        secilen_kanun["kisaAd"], girilen_madde
                    )
                    if sonuc and isinstance(sonuc, dict):
                        st.session_state["aktif_no_sonucu"] = sonuc
                        st.session_state["aktif_no_madde"] = girilen_madde
                        st.session_state["aktif_no_kanun"] = secilen_kanun["kisaAd"]

            if (
                "aktif_no_sonucu" in st.session_state
                and st.session_state["aktif_no_kanun"] == secilen_kanun["kisaAd"]
            ):
                res = st.session_state["aktif_no_sonucu"]

                # İçerik Gösterim Kartı
                st.markdown(
                    f"""
                    <div style="
                        background: #131822; 
                        padding: 20px; 
                        border-radius: 12px; 
                        border: 1px solid rgba(201, 168, 76, 0.3); 
                        margin-top: 12px; 
                        margin-bottom: 12px;
                        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
                    ">
                        <h4 style="color: #C9A84C; margin: 0 0 12px 0; font-size: 16px; font-weight:700;">📌 {res.get('baslik')}</h4>
                        <div style="color: #E2E8F0; font-size: 14px; line-height: 1.7; font-family:'DM Sans', sans-serif;">{res.get('metin')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # 🔗 Çapraz Bağlantı Rozetleri
                baglantilar = MevzuatBulutEngine.capraz_baglantilari_getir(
                    api_key=api_key,
                    kanun_kisa_ad=secilen_kanun["kisaAd"],
                    madde_no=st.session_state["aktif_no_madde"],
                    madde_metni=res.get("metin", ""),
                )

                if baglantilar:
                    st.markdown(
                        """
                        <div style="color:#8A99AD; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; margin-top:12px; margin-bottom:8px;">
                            🔗 Akıllı Çapraz Hükümler (Hızlı İncele)
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    cols = st.columns(len(baglantilar))
                    for idx, b in enumerate(baglantilar):
                        with cols[idx]:
                            btn_label = f"🔗 {b['kanun']} M. {b['madde']}"
                            if st.button(
                                btn_label,
                                key=f"cross_no_{b['kanun']}_{b['madde']}_{idx}",
                                use_container_width=True,
                                help=b["aciklama"],
                            ):
                                with st.spinner("İlişkili madde getiriliyor..."):
                                    c_res = MevzuatBulutEngine.madde_getir_buluttan(
                                        b["kanun"], b["madde"]
                                    )
                                    st.session_state.capraz_onizleme_no = {
                                        "baslik": c_res.get(
                                            "baslik", f"{b['kanun']} M. {b['madde']}"
                                        ),
                                        "metin": c_res.get(
                                            "metin", "Madde bulunamadı."
                                        ),
                                    }

                if "capraz_onizleme_no" in st.session_state:
                    c_data = st.session_state.capraz_onizleme_no
                    st.markdown(
                        f"""
                        <div style="
                            background: #0B0E14; 
                            padding: 16px 20px; 
                            border-radius: 10px; 
                            border: 1px solid #C9A84C; 
                            margin-top: 14px;
                            margin-bottom: 14px;
                        ">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                <span style="color:#C9A84C; font-size:13px; font-weight:700;">🔍 Çapraz İnceleme: {c_data['baslik']}</span>
                            </div>
                            <div style="color:#E2E8F0; font-size:13px; line-height:1.6; max-height: 200px; overflow-y: auto;">
                                {c_data['metin']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if "henüz yüklenmemiş" not in res.get(
                    "metin"
                ) and "bulunamadı" not in res.get("metin"):
                    st.markdown(
                        "<div style='height:12px'></div>", unsafe_allow_html=True
                    )
                    if st.button(
                        "⚖️ Hakim Gözüyle Analizi Başlat",
                        type="primary",
                        key="btn_analiz_no",
                        use_container_width=True,
                    ):
                        with st.spinner(
                            "Kıdemli Yargıtay Tetkik Hakimi analizi üretiliyor..."
                        ):
                            akış = MevzuatBulutEngine.madde_analiz_et(
                                api_key,
                                secilen_kanun["kisaAd"],
                                st.session_state["aktif_no_madde"],
                                res.get("metin"),
                            )
                            if akış:
                                st.session_state.son_madde_analizi = "".join(list(akış))
                                st.session_state.son_madde_baslik = f"Mevzuat Analizi: {secilen_kanun['kisaAd']} M.{st.session_state['aktif_no_madde']}"

                if "son_madde_analizi" in st.session_state:
                    st.markdown("### 🧠 JUNILEX Yapay Zeka Analiz Raporu")
                    st.markdown(
                        f"""
                        <div style="
                            background: #0B0E14; 
                            padding: 22px; 
                            border-radius: 12px; 
                            border-left: 4px solid #C9A84C; 
                            border: 1px solid #232B3E;
                            margin-top: 10px; 
                            margin-bottom: 16px;
                        ">
                            <div style="color: #E2E8F0; font-size: 14px; line-height: 1.7;">{st.session_state.son_madde_analizi.replace(chr(10), '<br>')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # 📤 EXPORT HUB / ÇOKLU DIŞA AKTAR
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                st.markdown(
                    """
                    <div style="
                        background: #0B0E14; 
                        padding: 12px 18px; 
                        border-radius: 10px; 
                        border: 1px solid #232B3E; 
                        margin-bottom: 12px;
                    ">
                        <span style="color:#C9A84C; font-size:13px; font-weight:700;">📤 Export Hub (Resmi Belge Olarak İndir)</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                exp_col1, exp_col2, exp_col3 = st.columns(3)

                txt_data = MevzuatBulutEngine.mevzuat_raporu_olustur(
                    secilen_kanun["kisaAd"],
                    st.session_state["aktif_no_madde"],
                    res.get("metin", ""),
                    st.session_state.get("son_madde_analizi", ""),
                    format_turu="txt",
                )

                udf_data = MevzuatBulutEngine.mevzuat_raporu_olustur(
                    secilen_kanun["kisaAd"],
                    st.session_state["aktif_no_madde"],
                    res.get("metin", ""),
                    st.session_state.get("son_madde_analizi", ""),
                    format_turu="udf",
                )

                with exp_col1:
                    st.download_button(
                        label="📄 Metin Raporu (.txt)",
                        data=txt_data,
                        file_name=f"{secilen_kanun['kisaAd']}_M{st.session_state['aktif_no_madde']}_Rapor.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )
                with exp_col2:
                    st.download_button(
                        label="⚖️ UYAP Belgesi (.udf)",
                        data=udf_data,
                        file_name=f"{secilen_kanun['kisaAd']}_M{st.session_state['aktif_no_madde']}.udf",
                        mime="application/xml",
                        use_container_width=True,
                    )
                with exp_col3:
                    if st.button(
                        "💾 Arşive Kaydet",
                        key="btn_kaydet_mevzuat_no_hub",
                        use_container_width=True,
                    ):
                        basarili, mesaj = junilex_arsive_kaydet(
                            "🏛️ Mevzuat Şerhi",
                            f"Mevzuat Analizi: {secilen_kanun['kisaAd']} M.{st.session_state['aktif_no_madde']}",
                            st.session_state.get(
                                "son_madde_analizi", "Analiz bulunamadı."
                            ),
                        )
                        if basarili:
                            st.success("✅ Arşive kaydedildi!")
                        else:
                            st.error(f"Hata: {mesaj}")

        # ── TAB 2: KELİME / KAVRAM İLE TARAMA ──
        with arama_sekmeleri[1]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 10px; 
                    border: 1px solid #232B3E;
                    border-left: 4px solid #C9A84C;
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0; color: #E2E8F0; font-size: 15px; font-weight:600;">🔤 Külliyat İçinde Kelime Tara</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 4px 0 0 0;">Seçili kanunun tüm maddelerinde geçen ifadeleri anında listeleyin.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            k_giriş_col, k_buton_col = st.columns([4, 1])
            with k_giriş_col:
                aranan_kelime = st.text_input(
                    "İçinde Geçen Kelime veya İfade",
                    placeholder="Örn: yaralama, kıdem tazminatı, zamanaşımı...",
                    key="input_kelime",
                    label_visibility="collapsed",
                )
            with k_buton_col:
                kelime_ara_butonu = st.button(
                    "Kanunu Tara",
                    use_container_width=True,
                    type="primary",
                    key="btn_kelime_ara",
                )

            if kelime_ara_butonu and aranan_kelime:
                st.session_state.pop("capraz_onizleme_kelime", None)
                with st.spinner(
                    f"{secilen_kanun['kisaAd']} külliyatında '{aranan_kelime}' taranıyor..."
                ):
                    maddeler_havuzu = MevzuatBulutEngine.kelime_ile_ara(
                        secilen_kanun["kisaAd"], aranan_kelime
                    )
                    st.session_state["k_arama_sonuclari"] = maddeler_havuzu
                    st.session_state["k_arama_kelimesi"] = aranan_kelime
                    st.session_state["k_arama_kanun"] = secilen_kanun["kisaAd"]

            if (
                "k_arama_sonuclari" in st.session_state
                and st.session_state["k_arama_kanun"] == secilen_kanun["kisaAd"]
            ):
                havuz = st.session_state["k_arama_sonuclari"]
                st.info(
                    f"**'{st.session_state['k_arama_kelimesi']}'** ifadesini içeren **{len(havuz)}** adet madde listelendi:"
                )

                for i, m in enumerate(havuz):
                    with st.expander(f"Madde {m['no']} — {m['baslik']}"):
                        st.markdown(
                            f"""
                            <div style="
                                background: #0B0E14; 
                                padding: 16px; 
                                border-radius: 8px; 
                                border-left: 3px solid #C9A84C; 
                                margin-bottom: 12px;
                            ">
                                <p style="color: #E2E8F0; font-size: 14px; margin: 0; line-height: 1.6;">{m['metin']}</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        k_baglantilar = MevzuatBulutEngine.capraz_baglantilari_getir(
                            api_key=api_key,
                            kanun_kisa_ad=secilen_kanun["kisaAd"],
                            madde_no=str(m["no"]),
                            madde_metni=m["metin"],
                        )

                        if k_baglantilar:
                            st.markdown(
                                """
                                <div style="color:#8A99AD; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; margin-top:8px; margin-bottom:6px;">
                                    🔗 Akıllı Çapraz Hükümler
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            k_cols = st.columns(len(k_baglantilar))
                            for idx, kb in enumerate(k_baglantilar):
                                with k_cols[idx]:
                                    k_btn_label = f"🔗 {kb['kanun']} M. {kb['madde']}"
                                    if st.button(
                                        k_btn_label,
                                        key=f"cross_k_{m['no']}_{kb['kanun']}_{kb['madde']}_{idx}",
                                        use_container_width=True,
                                        help=kb["aciklama"],
                                    ):
                                        with st.spinner(
                                            "İlişkili madde getiriliyor..."
                                        ):
                                            kc_res = (
                                                MevzuatBulutEngine.madde_getir_buluttan(
                                                    kb["kanun"], kb["madde"]
                                                )
                                            )
                                            st.session_state.capraz_onizleme_kelime = {
                                                "baslik": kc_res.get(
                                                    "baslik",
                                                    f"{kb['kanun']} M. {kb['madde']}",
                                                ),
                                                "metin": kc_res.get(
                                                    "metin", "Madde bulunamadı."
                                                ),
                                            }

                        if "capraz_onizleme_kelime" in st.session_state:
                            kc_data = st.session_state.capraz_onizleme_kelime
                            st.markdown(
                                f"""
                                <div style="
                                    background: #131822; 
                                    padding: 14px 18px; 
                                    border-radius: 8px; 
                                    border: 1px solid #C9A84C; 
                                    margin-top: 10px;
                                    margin-bottom: 12px;
                                ">
                                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                                        <span style="color:#C9A84C; font-size:12px; font-weight:700;">🔍 Çapraz İnceleme: {kc_data['baslik']}</span>
                                    </div>
                                    <div style="color:#E2E8F0; font-size:12px; line-height:1.5; max-height: 180px; overflow-y: auto;">
                                        {kc_data['metin']}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        st.markdown(
                            "<div style='height:6px'></div>", unsafe_allow_html=True
                        )
                        if st.button(
                            "🧠 Bu Maddeyi Analiz Et",
                            key=f"btn_analiz_k_{m['no']}_{i}",
                            use_container_width=True,
                        ):
                            with st.spinner("Madde analiz ediliyor..."):
                                akış = MevzuatBulutEngine.madde_analiz_et(
                                    api_key,
                                    secilen_kanun["kisaAd"],
                                    m["no"],
                                    m["metin"],
                                )
                                if akış:
                                    analiz_text = "".join(list(akış))
                                    st.markdown(
                                        f"""
                                        <div style="
                                            background: #131822; 
                                            padding: 18px; 
                                            border-radius: 10px; 
                                            border-left: 4px solid #C9A84C; 
                                            border: 1px solid #232B3E;
                                            margin-top: 12px;
                                            color: #E2E8F0;
                                            line-height: 1.7;
                                        ">
                                            {analiz_text.replace(chr(10), '<br>')}
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )

        # 🛠️ GELİŞTİRİCİ PANELİ (Sadece Ozan Şahin Sicim)
        if st.session_state.get("aktif_kullanici") == "Ozan Şahin Sicim":
            st.write("---")
            with st.expander("🛠️ JUNILEX Geliştirici — Hafıza Paneli", expanded=False):
                hedef_kanun_adi = st.selectbox(
                    "Hafızaya Alınacak Kanun",
                    options=[k["isim"] for k in kanun_listesi],
                    key="admin_yerel_secim",
                )
                hedef_kanun = next(
                    k for k in kanun_listesi if k["isim"] == hedef_kanun_adi
                )

                if st.button(
                    "☁️ Seçilen Kanunu Vektörleştir (ChromaDB)",
                    use_container_width=True,
                ):
                    with st.spinner(f"{hedef_kanun['kisaAd']} maddeleri işleniyor..."):
                        try:
                            MevzuatBulutEngine.kanunu_buluta_yukle(
                                id=hedef_kanun["id"], kisa_ad=hedef_kanun["kisaAd"]
                            )
                        except Exception as e:
                            st.error(f"Vektörleştirme Hatası: {str(e)}")

    # ==========================================
    # 🎓 AKADEMİK ASİSTAN MODÜLÜ (6 Sekmeli Tam Kapsamlı SaaS)
    # ==========================================
    elif st.session_state.aktif_ekran in ["Akademik Asistan", "Akademi"]:

        # 1. Modül Başlık Kartı
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #131822 0%, #1A212E 100%);
                border: 1px solid #232B3E;
                border-left: 4px solid #C9A84C;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 20px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            ">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="font-size:26px; color:#C9A84C;">🎓</div>
                    <div>
                        <h3 style="margin:0; color:#E2E8F0; font-family:'DM Sans',sans-serif; font-size:20px; font-weight:700;">
                            Junilex Akademik Asistan
                        </h3>
                        <p style="margin:4px 0 0 0; color:#8A99AD; font-size:13px;">
                            Sokratik çalışma, zihin haritaları, flaş kartlar, dijital arşiv, sınav simülasyonu ve podcast stüdyosu.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        from akademik_engine import AkademikEngine
        from akademik_sinav_modu import AkademikSinavEngine

        api_key = st.session_state.get(
            "gemini_api_key", MY_API_KEY if "MY_API_KEY" in globals() else ""
        )

        # 6 BAĞIMSIZ SEKME EKLENDİ
        akademi_sekmeleri = st.tabs(
            [
                "📚 Müfredat",
                "📊 Kavram Haritası",
                "📂 Notlarım",
                "🎯 Sınav Modu",
                "🎧 Podcast",
                "🏆 Flaş Kartlar",
            ]
        )

        # ── 1. SEKMELER: MÜFREDAT ──────────────────────────────────────────
        with akademi_sekmeleri[0]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            mufredat_data = AkademikEngine.get_akademik_mufredat()
            col1, col2 = st.columns(2)
            with col1:
                secilen_sinif = st.selectbox(
                    "Sınıf Seçiniz", list(mufredat_data.keys()), key="muf_sinif_secim"
                )
            with col2:
                ders_objeleri = mufredat_data[secilen_sinif]
                ders_listesi = [f"{d['ikon']} {d['isim']}" for d in ders_objeleri]
                secilen_ders_etiket = st.selectbox(
                    "Ders Seçiniz", ders_listesi, key="muf_ders_secim"
                )
                secilen_ders = (
                    secilen_ders_etiket.split(" ", 1)[1]
                    if " " in secilen_ders_etiket
                    else secilen_ders_etiket
                )

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            ogrenci_sorusu = st.text_area(
                "Hocaya sorunuzu veya konuyu yazın:", height=110, key="muf_soru_input"
            )

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                btn_ozetle = st.button("📝 Özetle", use_container_width=True)
            with btn_col2:
                btn_pratik = st.button("⚖️ Pratik Sor", use_container_width=True)
            with btn_col3:
                btn_sinav = st.button("🎯 Sınav Soruları", use_container_width=True)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            btn_standart = st.button(
                "💬 Yanıtla / Hoca ile Tartış", type="primary", use_container_width=True
            )

            gonderilecek_soru = None
            if ogrenci_sorusu:
                if btn_ozetle:
                    gonderilecek_soru = f"Bu konuyu özetle: {ogrenci_sorusu}"
                elif btn_pratik:
                    gonderilecek_soru = f"1 adet pratik olay sor: {ogrenci_sorusu}"
                elif btn_sinav:
                    gonderilecek_soru = (
                        f"Vize/final test/klasik sorusu hazırla: {ogrenci_sorusu}"
                    )
                elif btn_standart:
                    gonderilecek_soru = ogrenci_sorusu

            if gonderilecek_soru:
                with st.spinner("Kürsünün Hakimi yanıtlıyor..."):
                    akış = AkademikEngine.mufredat_hoca_anlat(
                        api_key, "", secilen_ders, gonderilecek_soru
                    )
                    if akış:
                        st.markdown(
                            """<div style="background: #131822; padding: 22px; border-radius: 12px; border-left: 4px solid #C9A84C; border: 1px solid #232B3E; margin-top: 16px; color: #E2E8F0; line-height: 1.7;">""",
                            unsafe_allow_html=True,
                        )
                        st.session_state.son_muf_yanit = st.write_stream(akış)
                        st.markdown("</div>", unsafe_allow_html=True)
            elif "son_muf_yanit" in st.session_state:
                st.markdown(
                    """<div style="background: #131822; padding: 22px; border-radius: 12px; border-left: 4px solid #C9A84C; border: 1px solid #232B3E; margin-top: 16px; color: #E2E8F0; line-height: 1.7;">""",
                    unsafe_allow_html=True,
                )
                st.markdown(st.session_state.son_muf_yanit)
                st.markdown("</div>", unsafe_allow_html=True)

        # ── 2. SEKMELER: KAVRAM HARİTASI (MIND MAP) ──────────────────────
        with akademi_sekmeleri[1]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            mm_col1, mm_col2 = st.columns(2)
            with mm_col1:
                mm_sinif = st.selectbox(
                    "Sınıf", list(mufredat_data.keys()), key="mm_sinif_secim"
                )
            with mm_col2:
                mm_ders = st.selectbox(
                    "Ders",
                    [d["isim"] for d in mufredat_data[mm_sinif]],
                    key="mm_ders_secim",
                )

            mm_konu = st.text_input(
                "Kavram Haritası Çıkarılacak Konu:", key="mm_konu_input"
            )
            if (
                st.button(
                    "🚀 Kavram Haritasını Oluştur",
                    type="primary",
                    use_container_width=True,
                    key="btn_mm_olustur",
                )
                and mm_konu
            ):
                with st.spinner("Zihin Haritası hazırlanıyor..."):
                    akış = AkademikEngine.kavram_haritasi_uret(
                        api_key, mm_ders, mm_konu
                    )
                    if akış:
                        st.markdown(
                            """<div style="background: #131822; padding: 22px; border-radius: 12px; border-left: 5px solid #C9A84C; border: 1px solid #232B3E; margin-top: 16px; color: #E2E8F0; line-height: 1.7;">""",
                            unsafe_allow_html=True,
                        )
                        st.session_state.son_mm_yanit = st.write_stream(akış)
                        st.markdown("</div>", unsafe_allow_html=True)
            elif "son_mm_yanit" in st.session_state:
                st.markdown(
                    """<div style="background: #131822; padding: 22px; border-radius: 12px; border-left: 5px solid #C9A84C; border: 1px solid #232B3E; margin-top: 16px; color: #E2E8F0; line-height: 1.7;">""",
                    unsafe_allow_html=True,
                )
                st.markdown(st.session_state.son_mm_yanit)
                st.markdown("</div>", unsafe_allow_html=True)

        # ── 3. SEKMELER: NOTLARIM ──────────────────────────────────────────
        with akademi_sekmeleri[2]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Notunu Buraya Yükle (PDF)", type=["pdf", "txt"], key="main_uploader"
            )
            if uploaded_file is not None:
                dosya_ismi = uploaded_file.name
                with st.spinner("PDF okunuyor ve arşive işleniyor..."):
                    cikarilan_metin = AkademikEngine.dosyadan_metin_cikar(uploaded_file)
                    try:
                        AkademikEngine.veritabanini_baslat()
                        db = AkademikEngine.db
                        db.collection("ders_notlari").add(
                            {
                                "dosya_adi": dosya_ismi,
                                "metin": cikarilan_metin,
                                "tarih": (
                                    firestore.SERVER_TIMESTAMP
                                    if "firestore" in globals()
                                    else None
                                ),
                            }
                        )
                        st.session_state.islenmis_not = cikarilan_metin
                        st.session_state.aktif_dosya = dosya_ismi
                        st.success(f"✅ Başarıyla eklendi!")
                    except Exception as e:
                        st.error(f"Hata: {e}")

            st.write("---")
            with st.expander("📂 Kayıtlı Ders Notlarımı Yönet", expanded=True):
                mevcut_notlar = AkademikEngine.yuklenen_notlari_getir()
                if mevcut_notlar:
                    for not_adi in mevcut_notlar:
                        col_isim, col_sec, col_sil = st.columns([4, 1, 1])
                        with col_isim:
                            st.markdown(f"📄 {not_adi}")
                        with col_sec:
                            if st.button(
                                "Seç", key=f"sec_{not_adi}", use_container_width=True
                            ):
                                eski_metin = AkademikEngine.not_icerigi_getir(not_adi)
                                if eski_metin:
                                    st.session_state.islenmis_not = eski_metin
                                    st.session_state.aktif_dosya = not_adi
                                    st.success(f"'{not_adi}' aktif masaya alındı.")
                        with col_sil:
                            if st.button(
                                "Sil",
                                key=f"sil_{not_adi}",
                                use_container_width=True,
                                type="secondary",
                            ):
                                if AkademikEngine.not_sil(not_adi):
                                    st.rerun()

            st.write("---")
            aktif_not_ismi = st.session_state.get("aktif_dosya", "Seçili Not Yok")
            not_icerigi = st.session_state.get("islenmis_not", "")
            giriş_col, buton_col = st.columns([4, 1])
            with giriş_col:
                soru_input = st.text_input("Soru sorun:", key="hoca_not_soru_input")
            with buton_col:
                hoca_dinle_btn = st.button(
                    "Analiz Et",
                    key="btn_hoca_dinle_notlar",
                    use_container_width=True,
                    type="primary",
                )

            if hoca_dinle_btn and not_icerigi:
                with st.spinner("Notlar inceleniyor..."):
                    sonuc = AkademikEngine.notlarla_ai_hoca_anlat(
                        api_key,
                        soru_input if soru_input else aktif_not_ismi,
                        not_icerigi,
                    )
                    st.session_state.son_hoca_anlatimi = sonuc
            if "son_hoca_anlatimi" in st.session_state:
                st.markdown(
                    f"""<div style="background-color: #0B0E14; padding: 24px 28px; border: 1px solid #232B3E; border-left: 4px solid #C9A84C; border-radius: 12px; margin-top: 16px;">{st.session_state.son_hoca_anlatimi.replace(chr(10), '<br>')}</div>""",
                    unsafe_allow_html=True,
                )

        # ── 4. SEKMELER: SINAV MODU ──────────────────────────────────────────
        with akademi_sekmeleri[3]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            col_r1, col_r2 = st.columns([2, 1])
            with col_r1:
                sinav_kaynagi = st.radio(
                    "Sınav Kaynağı:",
                    ["AI Kütüphanesi", "Kişisel Notlarım"],
                    horizontal=True,
                )
            with col_r2:
                sinav_tipi = st.selectbox(
                    "Sınav Tipi", ["Çoktan Seçmeli", "Klasik (Açık Uçlu)"]
                )
                soru_sayisi = st.slider("Soru Sayısı", 1, 10, 3)

            baslat_tiklandi = False
            aktif_konu, aktif_not = "", ""
            if sinav_kaynagi == "AI Kütüphanesi":
                col1, col2 = st.columns(2)
                with col1:
                    secilen_sinif_s = st.selectbox(
                        "Sınıf", list(mufredat_data.keys()), key="s_sinif"
                    )
                with col2:
                    secilen_ders_s = st.selectbox(
                        "Ders",
                        [d["isim"] for d in mufredat_data[secilen_sinif_s]],
                        key="s_ders",
                    )
                aktif_konu = secilen_ders_s
                if st.button(
                    "🚀 Sınavı Başlat", use_container_width=True, type="primary"
                ):
                    baslat_tiklandi = True
            else:
                mevcut_notlar = AkademikEngine.yuklenen_notlari_getir()
                secilen_not_adi = st.selectbox(
                    "Kaynak Not Seçiniz:",
                    options=mevcut_notlar if mevcut_notlar else ["Not Yok"],
                )
                if st.button(
                    "🚀 Sınavı Başlat", use_container_width=True, type="primary"
                ):
                    if secilen_not_adi != "Not Yok":
                        aktif_not = AkademikEngine.not_icerigi_getir(secilen_not_adi)
                        baslat_tiklandi = True

            if baslat_tiklandi:
                with st.spinner("Sınav hazırlanıyor..."):
                    sonuc = AkademikSinavEngine.pratik_calisma_uret(
                        api_key, aktif_konu, aktif_not, sinav_tipi, soru_sayisi
                    )
                    if "hata" in sonuc:
                        st.error(sonuc["hata"])
                    else:
                        st.session_state.su_anki_sinav = sonuc
                        st.session_state.sinav_tipi_aktif = sinav_tipi

            if st.session_state.get("su_anki_sinav"):
                sinav = st.session_state.su_anki_sinav
                st.markdown(
                    f"""<div style="background-color: #0B0E14; padding: 20px; border-left: 4px solid #C9A84C; border: 1px solid #232B3E; border-radius: 10px; margin-top:20px;">📋 OLAY KURGUSU<br>{sinav.get('olay_kurgusu', '')}</div>""",
                    unsafe_allow_html=True,
                )
                for i, soru_data in enumerate(sinav.get("sorular", [])):
                    st.markdown(f"**Soru {i+1}:** {soru_data['soru']}")
                    if st.session_state.get("sinav_tipi_aktif") == "Çoktan Seçmeli":
                        secim = st.radio(
                            "Seçenekler:",
                            soru_data.get("secenekler", []),
                            key=f"q_{i}",
                            label_visibility="collapsed",
                        )
                        if st.button("Kontrol Et", key=f"b_{i}"):
                            if secim == soru_data.get("cevap"):
                                st.success(
                                    f"✅ Doğru! Çözüm: {soru_data.get('analiz', '')}"
                                )
                            else:
                                st.error(
                                    f"❌ Yanlış! Doğru Cevap: {soru_data.get('cevap')}"
                                )
                    else:
                        cevap = st.text_area("Cevabınız:", key=f"ans_{i}")
                        if st.button("Puanla", key=f"puan_{i}"):
                            with st.spinner("Okunuyor..."):
                                puan_sonucu = AkademikSinavEngine.sinav_degerlendir(
                                    api_key,
                                    soru_data["soru"],
                                    cevap,
                                    soru_data.get("analiz", ""),
                                )
                                st.metric("Puan", f"{puan_sonucu.get('puan', 0)} / 100")
                                st.info(puan_sonucu.get("gercekce", ""))

        # ── 5. SEKMELER: PODCAST STÜDYOSU (SESLİ ÇALIŞMA) ────────────────
        with akademi_sekmeleri[4]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">🎧 Junilex Hukuk Podcast Stüdyosu</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Dümdüz okuyan robotları unutun! Yapay zeka notlarınızı alır, cana yakın bir hoca gibi sohbet havasında bir podcast programına dönüştürür.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            kaynak_secimi = st.radio(
                "🎙️ Ne Dinlemek İstersiniz?",
                [
                    "Müfredat (Son Mütalaa)",
                    "Kavram Haritası (Son Harita)",
                    "Notlarım (Son Analiz)",
                    "Serbest Metin Girin",
                ],
                horizontal=True,
            )

            okunacak_metin = ""

            if kaynak_secimi == "Müfredat (Son Mütalaa)":
                okunacak_metin = st.session_state.get("son_muf_yanit", "")
                if not okunacak_metin:
                    st.info(
                        "⚠️ Müfredat sekmesinde henüz bir mütalaa üretmediniz. Lütfen önce bir konu çalışın."
                    )
            elif kaynak_secimi == "Kavram Haritası (Son Harita)":
                okunacak_metin = st.session_state.get("son_mm_yanit", "")
                if not okunacak_metin:
                    st.info(
                        "⚠️ Kavram Haritası sekmesinde henüz bir harita üretmediniz."
                    )
            elif kaynak_secimi == "Notlarım (Son Analiz)":
                okunacak_metin = st.session_state.get("son_hoca_anlatimi", "")
                if not okunacak_metin:
                    st.info("⚠️ Notlarım sekmesinde henüz bir analiz üretmediniz.")
            elif kaynak_secimi == "Serbest Metin Girin":
                okunacak_metin = st.text_area(
                    "Dinlemek İstediğiniz Metni Yapıştırın:",
                    height=150,
                    placeholder="Örn: Haksız fiil unsurları, dürüstlük kuralı istisnaları...",
                )

            if okunacak_metin:
                if st.button(
                    "🔊 Podcast'i Hazırla ve Dinle",
                    type="primary",
                    use_container_width=True,
                ):

                    # 1. Aşama: AI'a Sohbet Senaryosu Yazdırma
                    with st.spinner(
                        "🧠 1/2: Metin, sohbet havasında interaktif bir radyo programına (senaryoya) dönüştürülüyor..."
                    ):
                        senaryo = AkademikEngine.podcast_senaryosu_uret(
                            api_key, okunacak_metin
                        )
                        st.session_state.guncel_podcast_senaryosu = senaryo

                    # 2. Aşama: Senaryoyu Sese Çevirme
                    with st.spinner(
                        "🎙️ 2/2: Hoca stüdyoya girdi, podcast kaydı alınıyor..."
                    ):
                        ses = AkademikEngine.metni_sese_cevir(senaryo)
                        if ses == b"gtts_error":
                            st.error(
                                "Lütfen terminalden 'pip install gTTS' komutunu çalıştırın."
                            )
                        elif ses:
                            st.session_state.guncel_podcast_sesi = ses
                            st.session_state.guncel_podcast_kaynagi = kaynak_secimi
                        else:
                            st.error("Ses sentezleme başarısız oldu.")

            if "guncel_podcast_sesi" in st.session_state:
                st.markdown(
                    f"""
                    <div style="background-color: #0B0E14; padding: 16px; border: 1px solid #232B3E; border-left: 4px solid #C9A84C; border-radius: 12px; margin-top: 16px; margin-bottom: 8px;">
                        <span style="color:#8A99AD; font-size:12px; font-weight:700;">🎧 AKTİF YAYIN: {st.session_state.get('guncel_podcast_kaynagi', 'Bilinmeyen Kaynak')}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Sesi çalma modülü
                st.audio(st.session_state.guncel_podcast_sesi, format="audio/mp3")

                # Kullanıcı dinlerken arkada hocanın anlattığı sohbet metnini okumak isterse:
                with st.expander(
                    "📝 Podcast Senaryosunu Oku (Yapay Zekanın Ürettiği Sohbet Metni)"
                ):
                    st.markdown(
                        f"<div style='color:#E2E8F0; font-size:14px; line-height:1.6;'>{st.session_state.get('guncel_podcast_senaryosu', '')}</div>",
                        unsafe_allow_html=True,
                    )

        # ── 6. SEKMELER: FLAŞ KARTLAR (ANKI TARZI DİJİTAL KARTLAR) ───────
        with akademi_sekmeleri[5]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">🏆 Flaş Kartlar (Spaced Repetition)</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Sınav öncesi hukuki kavramları, kanun sürelerini ve kritik istisnaları Anki tarzı kartlarla ezberleyin.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            fc_col1, fc_col2 = st.columns(2)
            with fc_col1:
                fc_sinif = st.selectbox(
                    "Sınıf Seç", list(mufredat_data.keys()), key="fc_sinif_secim"
                )
            with fc_col2:
                fc_ders = st.selectbox(
                    "Ders Seç",
                    [d["isim"] for d in mufredat_data[fc_sinif]],
                    key="fc_ders_secim",
                )

            fc_konu = st.text_input(
                "Kartları Üretilecek Hukuki Konu:",
                placeholder="Örn: Butlan halleri, Miras payları, Ceza ehliyeti yaş aralıkları...",
                key="fc_konu_input",
            )

            if st.button(
                "🚀 Kartları Üret",
                type="primary",
                use_container_width=True,
                key="btn_fc_olustur",
            ):
                if fc_konu:
                    with st.spinner(
                        f"Kürsünün Hakimi '{fc_konu}' için 10 adet flaş kart hazırlıyor..."
                    ):
                        kartlar = AkademikEngine.flashcard_uret(
                            api_key, fc_ders, fc_konu
                        )
                        if isinstance(kartlar, list):
                            st.session_state.flashcards = kartlar
                            st.session_state.fc_index = 0
                            st.session_state.fc_flipped = False
                            st.success("✅ Ezber kartları başarıyla üretildi!")
                        else:
                            st.error(
                                f"Hata: {kartlar.get('hata', 'JSON formatı çözülemedi.')}"
                            )
                else:
                    st.warning("⚠️ Lütfen kart üretimi için konuyu girin.")

            if "flashcards" in st.session_state and st.session_state.flashcards:
                kart_listesi = st.session_state.flashcards
                idx = st.session_state.fc_index
                aktif_kart = kart_listesi[idx]

                st.write("---")

                # İlerleme Çubuğu ve Sayaç
                st.progress((idx + 1) / len(kart_listesi))
                st.caption(f"Kart: {idx + 1} / {len(kart_listesi)}")

                # Dinamik Kart Tasarımı (Ön Yüz ve Arka Yüz Farklı Renklerde)
                kart_arkaplan = (
                    "#1A212E" if not st.session_state.fc_flipped else "#131822"
                )
                kart_kenarlik = (
                    "#232B3E" if not st.session_state.fc_flipped else "#C9A84C"
                )
                ust_baslik = (
                    "❔ ÖN YÜZ (SORU / KAVRAM)"
                    if not st.session_state.fc_flipped
                    else "💡 ARKA YÜZ (CEVAP / TANIM)"
                )
                gosterilen_metin = (
                    aktif_kart["on_yuz"]
                    if not st.session_state.fc_flipped
                    else aktif_kart["arka_yuz"]
                )

                st.markdown(
                    f"""
                    <div style="
                        background-color: {kart_arkaplan}; 
                        padding: 60px 30px; 
                        border: 2px solid {kart_kenarlik};
                        border-radius: 16px; 
                        text-align: center;
                        min-height: 250px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        margin-bottom: 24px;
                        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
                        transition: all 0.3s ease;
                    ">
                        <div style="color: #8A99AD; font-size: 13px; font-weight:700; margin-bottom: 20px;">
                            {ust_baslik}
                        </div>
                        <div style="color: #E2E8F0; font-size: 24px; line-height: 1.6; font-family:'DM Sans', sans-serif; font-weight: 500;">
                            {gosterilen_metin}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Kontrol Butonları
                c1, c2, c3 = st.columns([1, 2, 1])

                with c1:
                    if st.button(
                        "⬅️ Önceki", use_container_width=True, disabled=(idx == 0)
                    ):
                        st.session_state.fc_index -= 1
                        st.session_state.fc_flipped = False
                        st.rerun()

                with c2:
                    btn_metni = (
                        "🔄 Kartı Çevir (Cevabı Göster)"
                        if not st.session_state.fc_flipped
                        else "🔄 Kapat (Ön Yüze Dön)"
                    )
                    if st.button(btn_metni, type="primary", use_container_width=True):
                        st.session_state.fc_flipped = not st.session_state.fc_flipped
                        st.rerun()

                with c3:
                    if st.button(
                        "Sonraki ➡️",
                        use_container_width=True,
                        disabled=(idx == len(kart_listesi) - 1),
                    ):
                        st.session_state.fc_index += 1
                        st.session_state.fc_flipped = False
                        st.rerun()

    # ==========================================
    # 📝 ARZUHAL MODÜLÜ (Dilekçe Merkezi - Premium SaaS UI)
    # ==========================================
    elif st.session_state.aktif_ekran in ["Dilekçe Merkezi", "Arzuhal"]:

        # 1. Modül Başlık Kartı
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #131822 0%, #1A212E 100%);
                border: 1px solid #232B3E;
                border-left: 4px solid #C9A84C;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 20px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            ">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="font-size:24px; color:#C9A84C;">📝</div>
                    <div>
                        <h3 style="margin:0; color:#E2E8F0; font-family:'DM Sans',sans-serif; font-size:20px; font-weight:700;">
                            Dilekçe & Sözleşme Merkezi
                        </h3>
                        <p style="margin:4px 0 0 0; color:#8A99AD; font-size:13px;">
                            UYAP ve mahkeme formatlarına uygun, yapay zeka destekli profesyonel dilekçe ve sözleşme taslakları oluşturun.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. Katalog Seçim Kartı
        st.markdown(
            """
            <div style="
                background: #131822; 
                padding: 18px 20px; 
                border-radius: 12px; 
                border: 1px solid #232B3E; 
                border-top: 3px solid #C9A84C; 
                margin-bottom: 20px;
            ">
                <h4 style="margin:0 0 6px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">📑 Dilekçe & Sözleşme Marketi</h4>
                <p style="color: #8A99AD; font-size: 12px; margin: 0;">Hazırlamak istediğiniz hukuki evrak türünü ve alanını seçin.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_a, col_b = st.columns(2)
        with col_a:
            kategori = st.selectbox(
                "Hukuk Dalı Seçin", list(DilekceEngine.DILEKCE_KATALOGU.keys())
            )
        with col_b:
            tur = st.selectbox(
                "Dilekçe Türü Seçin",
                list(DilekceEngine.DILEKCE_KATALOGU[kategori].keys()),
            )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        gerekli_alanlar = DilekceEngine.DILEKCE_KATALOGU[kategori][tur]
        form_verileri = {}

        # 3. Dinamik Form Alanı
        with st.form("arzuhal_form"):
            st.markdown(
                f"""
                <div style="
                    background: #0B0E14; 
                    padding: 12px 16px; 
                    border-radius: 8px; 
                    border-left: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <span style="color: #E2E8F0; font-size: 14px; font-weight: 600;">📋 {tur} — Gerekli Parametreler</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            cols = st.columns(2)
            for i, alan in enumerate(gerekli_alanlar):
                col = cols[i % 2]
                with col:
                    if "Tarihi" in alan:
                        form_verileri[alan] = str(st.date_input(f"{alan}"))
                    elif "Sayısı" in alan or "Miktarı" in alan:
                        form_verileri[alan] = str(
                            st.number_input(f"{alan}", min_value=0, step=1)
                        )
                    elif "Detay" in alan or "Özeti" in alan or "Gerekçe" in alan:
                        form_verileri[alan] = st.text_area(f"{alan}", height=120)
                    else:
                        form_verileri[alan] = st.text_input(f"{alan}")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "✨ Taslağı Oluştur", type="primary", use_container_width=True
            )

        if submitted:
            if all(form_verileri.values()):
                with st.spinner("Hukuki taslak UYAP formatında hazırlanıyor..."):
                    taslak_metin = DilekceEngine.dilekce_uret(
                        MY_API_KEY, tur, form_verileri
                    )
                    st.session_state.son_dilekce = taslak_metin
                    st.session_state.son_dilekce_turu = tur
            else:
                st.warning(
                    "⚠️ Lütfen taslağın doğru üretilebilmesi için tüm alanları doldurun."
                )

        # 4. Hazırlanan Dilekçe Gösterim & Aksiyon Kartı
        if "son_dilekce" in st.session_state:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 18px 22px; 
                    border-radius: 12px; 
                    border: 1px solid rgba(201, 168, 76, 0.3); 
                    margin-bottom: 14px;
                ">
                    <h4 style="margin:0 0 6px 0; color: #C9A84C; font-size: 16px; font-weight: 700;">📄 Hazırlanan Dilekçe Taslağı</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Metin üzerinde doğrudan düzenleme yapabilir, Word olarak indirebilir veya JUNILEX arşivine kaydedebilirsiniz.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.text_area(
                "Düzenleme Alanı",
                value=st.session_state.son_dilekce,
                height=420,
                label_visibility="collapsed",
            )

            word_data = DilekceEngine.word_dosyasi_yap(st.session_state.son_dilekce)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    label="📥 Word (.docx) Olarak İndir",
                    data=word_data,
                    file_name=f"{st.session_state.son_dilekce_turu}_taslak.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            with c2:
                if st.button("💾 Arşive Kaydet", use_container_width=True):
                    basarili, mesaj = junilex_arsive_kaydet(
                        "Dilekçe",
                        st.session_state.son_dilekce_turu,
                        st.session_state.son_dilekce,
                    )
                    if basarili:
                        st.success(
                            "✅ Dilekçe arşive eklendi! JUNILEX Chat ekranından çağırarak üzerinde çalışabilirsiniz."
                        )

    # ==========================================
    # ⚖️ İÇTİHAT MODÜLÜ (Premium SaaS UI)
    # ==========================================
    elif st.session_state.aktif_ekran in ["İçtihat Sorgulama", "İçtihat"]:

        # 1. Modül Başlık Kartı
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #131822 0%, #1A212E 100%);
                border: 1px solid #232B3E;
                border-left: 4px solid #C9A84C;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 20px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            ">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="font-size:24px; color:#C9A84C;">⚖️</div>
                    <div>
                        <h3 style="margin:0; color:#E2E8F0; font-family:'DM Sans',sans-serif; font-size:20px; font-weight:700;">
                            İçtihat & Emsal Merkezi
                        </h3>
                        <p style="margin:4px 0 0 0; color:#8A99AD; font-size:13px;">
                            Yargıtay, Danıştay ve yüksek mahkeme kararlarını yapay zeka ile analiz edin veya somut olayınıza uygun emsalleri arayın.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab1, tab2 = st.tabs(["📌 Karar Analizi (Şerh)", "🔍 Emsal Karar Bulucu"])

        # ── TAB 1: KARAR ANALİZİ (ŞERH) ──────────────────────────────────────
        with tab1:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">⚖️ Karar Analiz Modülü</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Incelenmesini istediğiniz mahkeme kararını yapıştırarak hızlı analiz araçlarını veya özel soru alanını kullanın.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            karar_metni = st.text_area(
                "Yargıtay Karar Metnini Buraya Yapıştırın",
                height=240,
                key="karar_text_area",
            )

            st.markdown(
                "<span style='color:#C9A84C; font-size:13px; font-weight:600;'>⚡ Hızlı Analiz Araçları:</span>",
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                btn_ozet = st.button(
                    "📝 Kararı Özetle & Hükmü Söyle", use_container_width=True
                )
            with btn_col2:
                btn_gerekce = st.button(
                    "📌 Bozma/Onama Gerekçesi", use_container_width=True
                )
            with btn_col3:
                btn_celiski = st.button(
                    "⚖️ Çelişki / Görüş Ayrılığı", use_container_width=True
                )

            st.write("---")
            st.markdown(
                "<h5 style='color:#E2E8F0; font-size:14px; margin-bottom:8px;'>💬 Veya Özel Bir Soru Sorun:</h5>",
                unsafe_allow_html=True,
            )

            input_col, submit_col = st.columns([4, 1])
            with input_col:
                soru_input = st.text_input(
                    "Bu kararla ilgili neyi merak ediyorsunuz?",
                    placeholder="Örn: İspat yükü kime verilmiş?",
                    key="karar_soru_input",
                    label_visibility="collapsed",
                )
            with submit_col:
                btn_ozel_soru = st.button(
                    "Analiz Et",
                    use_container_width=True,
                    type="primary",
                    key="btn_analiz_et",
                )

            aktif_soru = None
            if karar_metni:
                if btn_ozet:
                    aktif_soru = "Bu kararı en fazla 3 paragrafta özetle ve nihai hükmün (sonucun) ne olduğunu açıkça belirt."
                elif btn_gerekce:
                    aktif_soru = "Bu karardaki Yargıtay'ın bozma veya onama gerekçesinin dayandığı temel hukuki argümanları ve kanun maddelerini listele."
                elif btn_celiski:
                    aktif_soru = "İlk derece mahkemesi (veya istinaf) ile Yargıtay arasındaki hukuki uyuşmazlığın ve görüş ayrılığının temel noktasını tespit et."
                elif btn_ozel_soru and soru_input:
                    aktif_soru = soru_input
            elif btn_ozet or btn_gerekce or btn_celiski or btn_ozel_soru:
                st.warning(
                    "⚠️ Lütfen önce incelenecek Yargıtay karar metnini yapıştırın."
                )

            if aktif_soru and karar_metni:
                with st.spinner("Kıdemli Yargıtay Tetkik Hakimi dosyayı inceliyor..."):
                    response = IctihatEngine.karar_analiz_et(
                        MY_API_KEY, karar_metni, aktif_soru
                    )
                    tam_metn = ""
                    if isinstance(response, str):
                        tam_metn = response
                    else:
                        for chunk in response:
                            try:
                                if hasattr(chunk, "text") and chunk.text:
                                    tam_metn += chunk.text
                            except:
                                continue

                    if tam_metn:
                        st.session_state.analiz_sayfalari = metni_sayfalara_bol(
                            tam_metn, 1200
                        )
                        st.session_state.analiz_aktif_sayfa = 0
                        st.rerun()
                    else:
                        st.error("Analiz sonucu boş döndü, lütfen tekrar deneyin.")

            if (
                "analiz_sayfalari" in st.session_state
                and st.session_state.analiz_sayfalari
            ):
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                sayfalar = st.session_state.analiz_sayfalari
                aktif = st.session_state.analiz_aktif_sayfa

                st.markdown(
                    f"""
                    <div style="
                        background-color: #0B0E14; 
                        padding: 24px 28px; 
                        border: 1px solid #232B3E; 
                        border-left: 4px solid #C9A84C; 
                        border-radius: 12px; 
                        color: #E2E8F0;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
                    ">
                        <div style="font-size: 12px; color: #8A99AD; font-weight: 700; text-transform: uppercase; margin-bottom: 12px; letter-spacing:1px;">
                            KARAR ANALİZ ŞERHİ — SAYFA {aktif + 1} / {len(sayfalar)}
                        </div>
                        <div style="font-size: 15px; line-height: 1.7; font-family:'DM Sans', sans-serif;">
                            {sayfalar[aktif].replace(chr(10), '<br>')}
                        </div>
                    </div>
                    <br>
                    """,
                    unsafe_allow_html=True,
                )

                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    if aktif > 0:
                        if st.button(
                            "⬅️ Önceki Sayfa",
                            key="analiz_geri_btn",
                            use_container_width=True,
                        ):
                            st.session_state.analiz_aktif_sayfa -= 1
                            st.rerun()
                with c3:
                    if aktif < len(sayfalar) - 1:
                        if st.button(
                            "Sonraki Sayfa ➡️",
                            key="analiz_ileri_btn",
                            use_container_width=True,
                        ):
                            st.session_state.analiz_aktif_sayfa += 1
                            st.rerun()

                st.write("---")
                if st.button(
                    "💾 Bu Şerhi JUNILEX Arşivine Kaydet", use_container_width=True
                ):
                    tam_metin = "\n".join(st.session_state.analiz_sayfalari)
                    basarili, mesaj = junilex_arsive_kaydet(
                        "İçtihat Şerhi", "Karar Analizi", tam_metin
                    )
                    if basarili:
                        st.success(
                            "✅ Arşive kaydedildi! JUNILEX Chat menüsünden ulaşıp üzerinde konuşabilirsiniz."
                        )

        # ── TAB 2: EMSAL KARAR BULUCU ─────────────────────────────────────────
        with tab2:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">🔍 Yargıtay ve Danıştay Emsal Bulucu</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Somut uyuşmazlığınıza en uygun güncel içtihatları filtreleyerek arayın ve emsal analiz raporu oluşturun.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_alan, col_kavram = st.columns([1, 2])
            with col_alan:
                secilen_alan = st.selectbox(
                    "Hukuk Dalı",
                    [
                        "Seçiniz...",
                        "Ceza Hukuku",
                        "Ticaret Hukuku",
                        "İdare Hukuku",
                        "İş Hukuku",
                        "Özel Hukuk",
                    ],
                )
            with col_kavram:
                anahtar_kavram = st.text_input(
                    "Kritik Hukuki Kavram",
                    placeholder="Örn: Zamanaşımı, Temerrüt, İptal...",
                    key="emsal_kavram",
                )

            olay_input = st.text_area(
                "Uyuşmazlığın Özeti ve Aranan Hüküm",
                height=140,
                placeholder="Örn: Tacirler arası haksız rekabet davasında, ihtarname çekilmeden açılan tazminat talebinin usulden reddi ihtimali...",
                key="emsal_olay_girdisi_v4",
            )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "🚀 İçtihat Havuzunda Ara ve Analiz Et",
                use_container_width=True,
                type="primary",
                key="btn_emsal_bul_v4",
            ):
                if olay_input and secilen_alan != "Seçiniz...":
                    with st.spinner(
                        "Junilex kütüphaneleri taranıyor, ilgili emsaller çekiliyor..."
                    ):
                        try:
                            zengin_prompt = f"[{secilen_alan}] Odak Kavram: {anahtar_kavram}. Olay: {olay_input}"
                            sonuc = IctihatEngine.emsal_ara(
                                MY_API_KEY, SERPER_API_KEY, zengin_prompt
                            )

                            if sonuc:
                                st.session_state.kitap_sayfalari = metni_sayfalara_bol(
                                    sonuc, 1200
                                )
                                st.session_state.aktif_sayfa = 0
                                st.rerun()
                            else:
                                st.error("Analiz sonucu boş döndü.")
                        except Exception as e:
                            st.error(f"Teknik bir hata oluştu: {e}")
                else:
                    st.warning(
                        "⚠️ Lütfen Hukuk Dalı seçin ve uyuşmazlık özetini girin."
                    )

            if (
                "kitap_sayfalari" in st.session_state
                and st.session_state.kitap_sayfalari
            ):
                st.write("---")
                sayfalar_emsal = st.session_state.kitap_sayfalari
                aktif_emsal = st.session_state.aktif_sayfa

                st.markdown(
                    f"""
                    <div style="
                        background-color: #0B0E14; 
                        padding: 24px 28px; 
                        border: 1px solid #232B3E; 
                        border-left: 4px solid #C9A84C; 
                        border-radius: 12px; 
                        color: #E2E8F0;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
                    ">
                        <div style="font-size: 12px; text-transform: uppercase; color: #8A99AD; margin-bottom: 12px; font-weight: 700; letter-spacing:1px;">
                            EMSAL ANALİZ RAPORU — SAYFA {aktif_emsal + 1} / {len(sayfalar_emsal)}
                        </div>
                        <div style="font-size: 15px; line-height: 1.8; font-family:'DM Sans', sans-serif;">
                            {sayfalar_emsal[aktif_emsal].replace(chr(10), '<br>')}
                        </div>
                    </div>
                    <br>
                    """,
                    unsafe_allow_html=True,
                )

                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    if aktif_emsal > 0:
                        if st.button(
                            "⬅️ Önceki Sayfa",
                            key="emsal_nav_geri",
                            use_container_width=True,
                        ):
                            st.session_state.aktif_sayfa -= 1
                            st.rerun()
                with c3:
                    if aktif_emsal < len(sayfalar_emsal) - 1:
                        if st.button(
                            "Sonraki Sayfa ➡️",
                            key="emsal_nav_ileri",
                            use_container_width=True,
                        ):
                            st.session_state.aktif_sayfa += 1
                            st.rerun()

                st.write("---")
                if st.button(
                    "💾 Bu Emsal Analizini Arşive Kaydet",
                    use_container_width=True,
                    key="btn_kaydet_emsal",
                ):
                    tam_metin = "\n".join(st.session_state.kitap_sayfalari)
                    basarili, mesaj = junilex_arsive_kaydet(
                        "Emsal Yönelim", "Emsal Analizi", tam_metin
                    )
                    if basarili:
                        st.success(
                            "✅ Arşive kaydedildi! JUNILEX Chat menüsünden ulaşıp kullanabilirsiniz."
                        )
    # ==========================================
    # 💬 JUNILEX CHAT MODÜLÜ (Premium SaaS UI)
    # ==========================================
    elif st.session_state.aktif_ekran in ["💬 JUNILEX Chat", "JUNILEX Chat", "Chat"]:

        # 1. Modül Başlık Kartı
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #131822 0%, #1A212E 100%);
                border: 1px solid #232B3E;
                border-left: 4px solid #C9A84C;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 20px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            ">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="font-size:24px; color:#C9A84C;">💬</div>
                    <div>
                        <h3 style="margin:0; color:#E2E8F0; font-family:'DM Sans',sans-serif; font-size:20px; font-weight:700;">
                            JUNILEX Chat & Akıllı Bağlam Asistanı
                        </h3>
                        <p style="margin:4px 0 0 0; color:#8A99AD; font-size:13px;">
                            Hukuki araştırmalarınızı yapın, arşivedeki evraklarınızı masaya koyarak yapay zekayla interaktif tartışın.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_chat, col_context = st.columns([3, 1], gap="medium")

        # ── SAĞ SÜTUN: BAĞLAM YÖNETİMİ ──────────────────────────────────────
        with col_context:
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 18px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">🗂️ Bağlam Arşivi</h4>
                    <p style="color: #8A99AD; font-size: 11px; margin: 0;">Tartışmak istediğiniz evrağı seçip masaya koyun.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            db = get_db()
            kategori_secim = st.selectbox(
                "Kategori:",
                [
                    "Seçiniz...",
                    "🏛️ Adliye (Mevzuat)",
                    "🎓 Akademi (PDF)",
                    "📝 Dilekçe",
                    "⚖️ İçtihat",
                ],
            )

            if kategori_secim != "Seçiniz...":
                arsiv_secenekleri = {}
                try:
                    if kategori_secim == "🎓 Akademi (PDF)":
                        notlar_ref = db.collection("ders_notlari").get()
                        for doc in notlar_ref:
                            d = doc.to_dict()
                            arsiv_secenekleri[d.get("dosya_adi", "Adsız")] = d.get(
                                "metin"
                            )
                    else:
                        kategori_map = {
                            "🏛️ Adliye (Mevzuat)": "🏛️ Mevzuat Şerhi",
                            "📝 Dilekçe": "📝 Dilekçe",
                            "⚖️ İçtihat": "⚖️ İçtihat Şerhi",
                        }
                        filtre = kategori_map.get(kategori_secim)
                        if st.session_state.aktif_kullanici:
                            docs = (
                                db.collection("junilex_arsiv")
                                .where(
                                    "kullanici", "==", st.session_state.aktif_kullanici
                                )
                                .where("kategori", "==", filtre)
                                .get()
                            )
                            for doc in docs:
                                d = doc.to_dict()
                                arsiv_secenekleri[d.get("baslik", "Adsız Başlık")] = (
                                    d.get("metin")
                                )
                except Exception as e:
                    st.error("Arşiv yüklenemedi.")

                if arsiv_secenekleri:
                    secilen_belge = st.selectbox(
                        "Belgeyi Seç:", list(arsiv_secenekleri.keys())
                    )
                    if st.button(
                        "📌 Masaya Koy", use_container_width=True, type="primary"
                    ):
                        st.session_state.aktif_dosya = (
                            f"{kategori_secim} | {secilen_belge}"
                        )
                        st.session_state.islenmis_not = arsiv_secenekleri[secilen_belge]
                        st.rerun()

            # Aktif Dosya Göstergesi (Glassmorphism Kart)
            if st.session_state.get("aktif_dosya"):
                st.markdown(
                    f"""
                    <div style="
                        background: #0B0E14; 
                        padding: 14px 16px; 
                        border-radius: 10px; 
                        border-left: 4px solid #C9A84C; 
                        border: 1px solid #232B3E;
                        border-left-width: 4px;
                        margin-top: 16px;
                        margin-bottom: 12px;
                    ">
                        <small style="color: #8A99AD; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1px;">AKTİF BAĞLAM</small><br>
                        <span style="color: #E2E8F0; font-size:13px; font-weight:600;">{st.session_state.aktif_dosya}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("🗑️ Masayı Temizle", use_container_width=True):
                    st.session_state.aktif_dosya = None
                    st.session_state.islenmis_not = None
                    st.rerun()

        # ── SOL SÜTUN: CHAT ARAYÜZÜ ─────────────────────────────────────────
        with col_chat:
            # Yapılandırma Paneli
            with st.expander("⚙️ Zeka Yapılandırması ve Üslup Ayarları"):
                col_mod, col_uslup = st.columns(2)
                with col_mod:
                    secilen_mod = st.radio(
                        "İletişim Modu:",
                        ["Özet", "⚖️ Detaylı Analiz"],
                        horizontal=True,
                        key="mod_secim",
                    )
                    if secilen_mod != st.session_state.chat_mode:
                        st.session_state.chat_mode = secilen_mod
                        st.rerun()

                with col_uslup:
                    secilen_uslup = st.radio(
                        "Üslup Tercihi:",
                        ["Nötr", "Akademik ve Resmi", "Pratik ve Açıklayıcı"],
                        horizontal=True,
                        key="uslup_secim",
                    )
                    if secilen_uslup != st.session_state.get("chat_style", "Nötr"):
                        st.session_state.chat_style = secilen_uslup
                        st.rerun()

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # Hızlı Aksiyonlar
            cols_q = st.columns(3)
            if cols_q[0].button("📄 Dokümanı Özetle", use_container_width=True):
                st.session_state.pending_prompt = "Lütfen bu dosyayı benim için özetle."
            if cols_q[1].button("🔍 Hukuki Hata Denetimi", use_container_width=True):
                st.session_state.pending_prompt = (
                    "Bu dokümanda hukuki bir hata veya eksiklik var mı?"
                )
            if cols_q[2].button("📝 Karşı Argüman Üret", use_container_width=True):
                st.session_state.pending_prompt = (
                    "Bu dokümandaki argümanlara karşı etkili bir karşı argüman üret."
                )

            st.write("---")

            # Sohbet Geçmişi Gösterimi
            for message in st.session_state.chat_messages:
                avatar = "👤" if message["role"] == "user" else "⚖️"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

            # Mesaj Girişi
            prompt = st.chat_input(
                "Hukuki sorunuzu yazın veya masadaki belge hakkında soru sorun..."
            )

            # Pending Prompt Tetikleyicisi
            if st.session_state.get("pending_prompt"):
                prompt = st.session_state.pending_prompt
                st.session_state.pending_prompt = None

            if prompt:
                st.session_state.chat_messages.append(
                    {"role": "user", "content": prompt}
                )
                with st.chat_message("user", avatar="👤"):
                    st.markdown(prompt)

                with st.chat_message("assistant", avatar="⚖️"):
                    message_placeholder = st.empty()
                    full_response = ""
                    try:
                        response = ChatEngine.yanit_uret(
                            MY_API_KEY,
                            st.session_state.chat_messages[:-1],
                            prompt,
                            mod=st.session_state.chat_mode,
                            aktif_belge_metni=st.session_state.get(
                                "islenmis_not", None
                            ),
                            manuel_uslup=st.session_state.get("chat_style", "Nötr"),
                        )

                        for chunk in response:
                            if hasattr(chunk, "text") and chunk.text:
                                full_response += chunk.text
                                message_placeholder.markdown(full_response + " ▌")
                        message_placeholder.markdown(full_response)

                        st.session_state.chat_messages.append(
                            {"role": "assistant", "content": full_response}
                        )
                    except Exception as e:
                        st.error(f"Sistem Hatası: {e}")
    # ==========================================
    # 🧮 PRATİK HESAPLAMALAR MODÜLÜ (Premium SaaS UI)
    # ==========================================
    elif st.session_state.aktif_ekran in ["Pratik Hesaplamalar", "Hesaplamalar"]:

        # 1. Modül Başlık Kartı
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #131822 0%, #1A212E 100%);
                border: 1px solid #232B3E;
                border-left: 4px solid #C9A84C;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 20px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            ">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="font-size:24px; color:#C9A84C;">🧮</div>
                    <div>
                        <h3 style="margin:0; color:#E2E8F0; font-family:'DM Sans',sans-serif; font-size:20px; font-weight:700;">
                            Pratik Hesaplamalar Hub
                        </h3>
                        <p style="margin:4px 0 0 0; color:#8A99AD; font-size:13px;">
                            Hukuki iş süreçlerinde, icra takiplerinde ve dava süreçlerinde kullanılan hızlı finansal hesaplama araçları.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tabs = st.tabs(
            [
                "🧾 SMM Hesaplayıcı",
                "📈 Faiz Hesaplayıcı",
                "💼 İşçilik Alacakları",
                "⚖️ Peşin Harç",
                "📊 AAÜT / Kademeli",
            ]
        )

        # ── 1. SMM HESAPLAYICI ───────────────────────────────────────────────
        with tabs[0]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">🧾 Serbest Meslek Makbuzu Hesaplayıcı</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Anlaşma tipinize göre KDV, Stopaj ve Avukata kalan net tutarı hesaplayın.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c_tip, c_tutar, c_tev = st.columns([2, 2, 1])
            with c_tip:
                hesap_tipi = st.selectbox(
                    "Anlaşma Tipi", ["Netten Brüte (KDV Hariç Anlaşma)", "Brütten Nete"]
                )
            with c_tutar:
                tutar = st.number_input(
                    "Tutar (₺)", min_value=0.0, value=10000.0, step=500.0
                )
            with c_tev:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                tevkifat = st.checkbox("KDV Tevkifatı", help="5/10 tevkifat uygulanır.")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "🧮 Makbuzu Hesapla",
                type="primary",
                key="btn_smm_hesapla",
                use_container_width=True,
            ):
                sonuc = HesapEngine.smm_hesapla(tutar, hesap_tipi)
                st.write("---")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Brüt Ücret", f"₺{sonuc['Brüt Ücret']:,.2f}")
                c2.metric("KDV (%20)", f"₺{sonuc['KDV (%20)']:,.2f}")
                c3.metric("Stopaj (%20)", f"₺{sonuc['Stopaj (%20)']:,.2f}")
                c4.metric("Net Tahsilat", f"₺{sonuc['Avukata Kalan Net']:,.2f}")

                st.markdown(
                    f"""
                    <div style="
                        background: #0B0E14; 
                        padding: 14px 18px; 
                        border-radius: 10px; 
                        border-left: 4px solid #C9A84C; 
                        border: 1px solid #232B3E;
                        border-left-width: 4px;
                        margin-top: 16px;
                        color: #E2E8F0;
                        font-size: 14px;
                    ">
                        💡 <b>Müvekkilden Tahsil Edilecek Toplam (Net + KDV):</b> 
                        <span style="color:#C9A84C; font-weight:700; font-size:16px;">₺{sonuc['Müvekkilden Tahsil Edilecek Toplam (Net + KDV)']:,.2f}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # ── 2. FAİZ HESAPLAYICI ───────────────────────────────────────────────
        with tabs[1]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">📈 Gün Bazlı Faiz Hesaplayıcı</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Temerrüt ve hesap tarihi arasındaki gün bazlı toplam işleyen faizi hesaplayın.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns(2)
            with c1:
                anapara = st.number_input(
                    "Anapara (₺)", min_value=0.0, value=50000.0, step=1000.0
                )
                baslangic = st.date_input(
                    "Temerrüt Tarihi", value=datetime.date(2023, 1, 1)
                )
            with c2:
                faiz_orani = st.number_input(
                    "Yıllık Faiz Oranı (%)", min_value=0.0, value=9.0, step=1.0
                )
                bitis = st.date_input("Hesap Tarihi", value=datetime.date.today())

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "📈 Faizi Hesapla",
                type="primary",
                key="btn_faiz_hesapla",
                use_container_width=True,
            ):
                gun, faiz_miktari, toplam = HesapEngine.faiz_hesapla(
                    anapara, faiz_orani, baslangic, bitis
                )
                st.write("---")
                st.markdown(
                    f"""
                    <div style="color:#8A99AD; font-size:13px; font-weight:600; margin-bottom:12px;">
                        ⏱️ Geçen Süre: <span style="color:#C9A84C; font-weight:700;">{gun} Gün</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                c_a, c_f, c_t = st.columns(3)
                c_a.metric("Anapara", f"₺{anapara:,.2f}")
                c_f.metric("İşleyen Faiz", f"₺{faiz_miktari:,.2f}")
                c_t.metric("Toplam Alacak", f"₺{toplam:,.2f}")

        # ── 3. İŞÇİLİK ALACAKLARI ─────────────────────────────────────────────
        with tabs[2]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">💼 Kıdem ve İhbar Tazminatı Hesaplayıcı</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Çalışma süreleri ve kıdem tavanı dikkate alınarak net tazminat tutarlarını hesaplayın.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns(2)
            with c1:
                brut_maas = st.number_input("Brüt Maaş (₺)", value=20002.50, step=500.0)
                ise_giris = st.date_input(
                    "İşe Giriş Tarihi", value=datetime.date(2020, 1, 1)
                )
            with c2:
                kidem_tavani = st.number_input(
                    "Kıdem Tavanı (₺)", value=35058.58, step=1000.0
                )
                isten_cikis = st.date_input(
                    "İşten Çıkış Tarihi", value=datetime.date.today()
                )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "💼 Tazminatları Hesapla",
                type="primary",
                use_container_width=True,
                key="btn_isci_hesapla",
            ):
                sonuc = HesapEngine.iscil_alacaklar_hesapla(
                    brut_maas, kidem_tavani, ise_giris, isten_cikis
                )
                if "Hata" in sonuc:
                    st.error(f"⚠️ {sonuc['Hata']}")
                else:
                    st.write("---")
                    st.markdown(
                        f"""
                        <div style="
                            background: #0B0E14; 
                            padding: 10px 16px; 
                            border-radius: 8px; 
                            border: 1px solid #232B3E; 
                            margin-bottom: 14px;
                            color: #8A99AD;
                            font-size: 13px;
                        ">
                            ⏱️ <b>Çalışılan Süre:</b> {sonuc['Çalışılan Gün']} Gün &nbsp;|&nbsp; 
                            ⏱️ <b>İhbar Süresi:</b> {sonuc['İhbar Süresi (Hafta)']} Hafta
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    m1, m2 = st.columns(2)
                    m1.metric("Net Kıdem Tazminatı", f"₺{sonuc['Kıdem Net']:,.2f}")
                    m2.metric("Net İhbar Tazminatı", f"₺{sonuc['İhbar Net']:,.2f}")

        # ── 4. HARÇ HESAPLAYICI ───────────────────────────────────────────────
        with tabs[3]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">⚖️ Peşin Harç Hesaplayıcı</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Dava değerine göre nispi karar ve ilam harcı ile yatırılacak 1/4 peşin harcı hesaplayın.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            dava_degeri = st.number_input(
                "Dava Değeri (₺)", value=100000.0, step=10000.0
            )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "⚖️ Harç Hesapla",
                type="primary",
                key="btn_harc_hesapla",
                use_container_width=True,
            ):
                toplam, pesin = HesapEngine.nispi_harc_hesapla(dava_degeri)
                st.write("---")
                m1, m2 = st.columns(2)
                m1.metric("Yatırılacak Peşin Harç (1/4)", f"₺{pesin:,.2f}")
                m2.metric("Toplam Karar ve İlam Harcı", f"₺{toplam:,.2f}")

        # ── 5. AAÜT / KADEMELİ VEKALET ÜCRETİ ─────────────────────────────────
        with tabs[4]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="
                    background: #131822; 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    border: 1px solid #232B3E; 
                    border-top: 3px solid #C9A84C; 
                    margin-bottom: 16px;
                ">
                    <h4 style="margin:0 0 4px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">📊 Nispi Vekalet Ücreti Hesaplayıcı (AAÜT)</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Avukatlık Asgari Ücret Tarifesi kademeli dilimlerine göre vekalet ücretini hesaplayın.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            vekalet_tutari = st.number_input(
                "Dava/İcra Tutarı (₺)", value=500000.0, step=50000.0
            )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "📊 Vekalet Ücreti Hesapla",
                type="primary",
                key="btn_aaut_hesapla",
                use_container_width=True,
            ):
                aaut_dilimler = [
                    {"limit": 200000, "oran": 0.16},
                    {"limit": 200000, "oran": 0.15},
                    {"limit": 400000, "oran": 0.14},
                    {"limit": 600000, "oran": 0.11},
                    {"limit": 1200000, "oran": 0.08},
                    {"limit": 1600000, "oran": 0.05},
                    {"limit": 1600000, "oran": 0.03},
                    {"limit": 8000000, "oran": 0.02},
                    {"limit": None, "oran": 0.01},
                ]
                ucret, detay = HesapEngine.kademeli_tarife_hesapla(
                    vekalet_tutari, aaut_dilimler
                )
                st.write("---")
                st.metric("Hesaplanan Nispi Vekalet Ücreti", f"₺{ucret:,.2f}")

                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                with st.expander("🔍 Kademeli Dilim Detaylarını Göster"):
                    for d in detay:
                        st.markdown(
                            f"• <span style='color:#E2E8F0;'>{d}</span>",
                            unsafe_allow_html=True,
                        )
    # ==========================================
    # 👤 1. PROFİL MODÜLÜ (Sadece Kişisel Bilgiler)
    # ==========================================
    elif st.session_state.aktif_ekran in ["Profil", "👤 Profil", "Hesabım"]:

        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #131822 0%, #1A212E 100%);
                border: 1px solid #232B3E;
                border-left: 4px solid #C9A84C;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 20px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            ">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="font-size:24px; color:#C9A84C;">👤</div>
                    <div>
                        <h3 style="margin:0; color:#E2E8F0; font-family:'DM Sans',sans-serif; font-size:20px; font-weight:700;">
                            Kullanıcı Profili
                        </h3>
                        <p style="margin:4px 0 0 0; color:#8A99AD; font-size:13px;">
                            Kişisel bilgilerinizi, baro/kurum detaylarınızı ve biyografinizi güncelleyin.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        benim_mailim = st.session_state.get("aktif_kullanici_email", "")
        benim_isim = st.session_state.get("aktif_kullanici", "Kullanıcı")
        benim_id = st.session_state.get("aktif_kullanici_id", "#00000")

        db_json = veritabani_yukle()
        kullanici_verisi = db_json.get(benim_mailim, {})

        # Üst Özet Kartı
        col_profil_head, col_stats = st.columns([2, 3], gap="medium")
        with col_profil_head:
            st.markdown(
                f"""
                <div style="background: #131822; padding: 24px; border-radius: 12px; border: 1px solid #232B3E; border-top: 3px solid #C9A84C; text-align: center;">
                    <div style="width: 70px; height: 70px; background: linear-gradient(135deg, #232B3E 0%, #0B0E14 100%); border: 2px solid #C9A84C; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; margin: 0 auto 12px auto;">⚖️</div>
                    <h3 style="margin:0; color:#E2E8F0; font-size:18px; font-weight:700;">{benim_isim}</h3>
                    <p style="color:#8A99AD; font-size:13px; margin:4px 0 12px 0;">{benim_mailim}</p>
                    <span style="background: #0B0E14; color: #C9A84C; padding: 4px 12px; border-radius: 20px; border: 1px solid #232B3E; font-family: monospace; font-size: 13px; font-weight: 700;">ID: {benim_id}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_stats:
            st.markdown(
                """<div style="background: #131822; padding: 16px 20px; border-radius: 12px; border: 1px solid #232B3E; margin-bottom: 12px;"><h4 style="margin:0 0 10px 0; color: #E2E8F0; font-size: 14px; font-weight: 600;">📊 Hesap Durumu</h4><p style="color: #8A99AD; font-size: 12px; margin: 0;">Platform üzerindeki aktif rolünüz ve bağlantılarınız.</p></div>""",
                unsafe_allow_html=True,
            )
            m1, m2, m3 = st.columns(3)
            m1.metric(
                "Bağlantılarım", f"{len(kullanici_verisi.get('arkadaslar', []))} Kişi"
            )
            m2.metric(
                "Gelen İstekler",
                f"{len(kullanici_verisi.get('gelen_istekler', []))} İstek",
            )
            m3.metric("Hesap Türü", "Pro Avukat / Öğrenci")

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Sekmesiz, doğrudan profil formu
        st.markdown(
            "<h4 style='color:#E2E8F0; font-size:16px; margin-bottom: 12px;'>📝 Profil Bilgilerini Güncelle</h4>",
            unsafe_allow_html=True,
        )
        with st.form("profil_bilgi_formu"):
            c_ad, c_soyad = st.columns(2)
            with c_ad:
                yeni_isim = st.text_input(
                    "Ad Soyad / Unvan", value=kullanici_verisi.get("isim", benim_isim)
                )
            with c_soyad:
                yeni_tel = st.text_input(
                    "Telefon Numarası", value=kullanici_verisi.get("telefon", "")
                )

            c_baro, c_uzmanlik = st.columns(2)
            with c_baro:
                baro_bilgisi = st.text_input(
                    "Baro / Kurum", value=kullanici_verisi.get("baro", "")
                )
            with c_uzmanlik:
                uzmanlik = st.text_input(
                    "Uzmanlık Alanı", value=kullanici_verisi.get("uzmanlik", "")
                )

            biyografi = st.text_area(
                "Hakkımda", value=kullanici_verisi.get("biyografi", "")
            )

            if st.form_submit_button(
                "💾 Bilgileri Güncelle", type="primary", use_container_width=True
            ):
                db_json[benim_mailim]["isim"] = yeni_isim
                db_json[benim_mailim]["telefon"] = yeni_tel
                db_json[benim_mailim]["baro"] = baro_bilgisi
                db_json[benim_mailim]["uzmanlik"] = uzmanlik
                db_json[benim_mailim]["biyografi"] = biyografi
                veritabani_kaydet(db_json)
                st.session_state.aktif_kullanici = yeni_isim
                st.success("✅ Profil bilgileriniz güncellendi!")
                st.rerun()

    # ==========================================
    # ⚙️ 2. AYARLAR MODÜLÜ (Güvenlik, Bülten, Sistem)
    # ==========================================
    # Listeye " " (boşluk) şartını ekledik:
    elif st.session_state.aktif_ekran in ["Ayarlar", "⚙️ Ayarlar", "Ayarlar"]:

        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #131822 0%, #1A212E 100%);
                border: 1px solid #232B3E;
                border-left: 4px solid #4C6BC9;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 20px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            ">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="font-size:24px; color:#4C6BC9;">⚙️</div>
                    <div>
                        <h3 style="margin:0; color:#E2E8F0; font-family:'DM Sans',sans-serif; font-size:20px; font-weight:700;">
                            Sistem ve Güvenlik Ayarları
                        </h3>
                        <p style="margin:4px 0 0 0; color:#8A99AD; font-size:13px;">
                            Hesap güvenliğinizi, yapay zeka tercihlerini ve günlük e-posta bülten içeriklerinizi buradan yönetin.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        benim_mailim = st.session_state.get("aktif_kullanici_email", "")
        db_json = veritabani_yukle()
        kullanici_verisi = db_json.get(benim_mailim, {})

        ayarlar_sekmeleri = st.tabs(
            ["🔒 Güvenlik & Şifre", "📬 Günlük Bülten", "⚙️ Uygulama Tercihleri"]
        )

        # ── SEKME 1: GÜVENLİK VE ŞİFRE (Profil'den Taşındı) ──
        with ayarlar_sekmeleri[0]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="background: #131822; padding: 18px 20px; border-radius: 12px; border: 1px solid #232B3E; border-left: 4px solid #C94C4C; margin-bottom: 16px;">
                    <h4 style="margin:0 0 6px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">🔒 Hesap Güvenliği</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Junilex hesabınızın şifresini buradan güvenli bir şekilde değiştirebilirsiniz.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.form("sifre_degistir_formu"):
                eski_sifre = st.text_input("Mevcut Şifre", type="password")
                yeni_sifre = st.text_input("Yeni Şifre", type="password")
                yeni_sifre_tekrar = st.text_input(
                    "Yeni Şifre (Tekrar)", type="password"
                )

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                if st.form_submit_button(
                    "🔑 Şifreyi Güncelle", type="primary", use_container_width=True
                ):
                    if eski_sifre != kullanici_verisi.get("sifre", ""):
                        st.error("❌ Mevcut şifre hatalı!")
                    elif yeni_sifre != yeni_sifre_tekrar:
                        st.error("❌ Yeni şifreler eşleşmiyor!")
                    elif len(yeni_sifre) < 4:
                        st.warning("⚠️ Şifre en az 4 karakter olmalıdır.")
                    else:
                        db_json[benim_mailim]["sifre"] = yeni_sifre
                        veritabani_kaydet(db_json)
                        st.success("✅ Şifreniz başarıyla değiştirildi!")

        # ── SEKME 2: GÜNLÜK BÜLTEN (E-POSTA) AYARLARI ──
        with ayarlar_sekmeleri[1]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="background: #131822; padding: 18px 20px; border-radius: 12px; border: 1px solid #232B3E; border-left: 4px solid #C9A84C; margin-bottom: 16px;">
                    <h4 style="margin:0 0 6px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">📬 Junilex Günlük Bülten</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">Her sabah 08:00'de tek bir e-posta ile almak istediğiniz güncel hukuki içerikleri seçin. SPAM yok, sadece ihtiyacınız olanlar!</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Veritabanından tercihleri çek
            eski_tercihler = kullanici_verisi.get(
                "bulten_tercihleri",
                {
                    "aktif": True,
                    "rg": True,
                    "emsal": True,
                    "sinav": False,
                    "terim": True,
                },
            )

            with st.form("bulten_ayarlari_formu"):
                # ANA ŞALTER
                st.markdown(
                    "<h5 style='color:#E2E8F0; font-size:14px;'>Bülten Aboneliği Durumu</h5>",
                    unsafe_allow_html=True,
                )
                ana_salter = st.toggle(
                    "📩 Her sabah Junilex Günlük Hukuk Bülteni almak istiyorum.",
                    value=eski_tercihler.get("aktif", True),
                )
                st.write("---")

                col_bul_1, col_bul_2 = st.columns(2)
                with col_bul_1:
                    st.markdown(
                        "<span style='color:#E2E8F0; font-weight:600; font-size:13px;'>Avukat & Stajyer Modülleri</span>",
                        unsafe_allow_html=True,
                    )
                    istiyor_rg = st.checkbox(
                        "🗞️ AI Filtreli Resmi Gazete Özeti",
                        value=eski_tercihler.get("rg", True),
                        disabled=not ana_salter,
                    )
                    istiyor_emsal = st.checkbox(
                        "⚖️ Günün Emsal Yargıtay Kararı",
                        value=eski_tercihler.get("emsal", True),
                        disabled=not ana_salter,
                    )
                with col_bul_2:
                    st.markdown(
                        "<span style='color:#E2E8F0; font-weight:600; font-size:13px;'>Öğrenci & Akademi Modülleri</span>",
                        unsafe_allow_html=True,
                    )
                    istiyor_sinav = st.checkbox(
                        "🎯 Günün Pratik Sınav Sorusu",
                        value=eski_tercihler.get("sinav", False),
                        disabled=not ana_salter,
                    )
                    istiyor_terim = st.checkbox(
                        "📚 Hukuk İngilizcesi / Latince Terim",
                        value=eski_tercihler.get("terim", True),
                        disabled=not ana_salter,
                    )

                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                if st.form_submit_button(
                    "💾 Bülten Tercihlerimi Kaydet",
                    type="primary",
                    use_container_width=True,
                ):
                    db_json[benim_mailim]["bulten_tercihleri"] = {
                        "aktif": ana_salter,
                        "rg": istiyor_rg,
                        "emsal": istiyor_emsal,
                        "sinav": istiyor_sinav,
                        "terim": istiyor_terim,
                    }
                    veritabani_kaydet(db_json)
                    if ana_salter:
                        st.success("✅ Günlük bülten aboneliğiniz güncellendi!")
                    else:
                        st.warning(
                            "⚠️ Günlük bülten aboneliğiniz iptal edildi. Artık mail almayacaksınız."
                        )

        # ── SEKME 3: UYGULAMA VE SİSTEM TERCİHLERİ ──
        with ayarlar_sekmeleri[2]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="background: #131822; padding: 18px 20px; border-radius: 12px; border: 1px solid #232B3E; margin-bottom: 16px;">
                    <h4 style="margin:0 0 6px 0; color: #E2E8F0; font-size: 15px; font-weight: 600;">⚙️ Arayüz ve Yapay Zeka Tercihleri</h4>
                    <p style="color: #8A99AD; font-size: 12px; margin: 0;">JUNILEX sisteminin size nasıl yanıt vereceğini ve arayüz tepkilerini belirleyin.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.toggle("🔔 Bağlantı ve Ekip Bildirimlerini Göster", value=True)
            st.toggle("⚡ Dilekçe ve Karar Analizlerinde Otomatik Şerh Düş", value=True)
            st.selectbox(
                "Varsayılan Yapay Zeka Dili",
                [
                    "Türkçe (Resmi Hukuk Dili - Avukatlar İçin)",
                    "Türkçe (Sadeleştirilmiş - Vatandaş/Müvekkil İçin)",
                    "English (Legal English)",
                ],
            )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("💾 Sistem Ayarlarını Uygula", use_container_width=True):
                st.success(
                    "Sistem tercihleri güncellendi (Sadece bu oturum için geçerlidir)."
                )
    # ==========================================
    # 🧹 RAM TEMİZLİĞİ
    # ==========================================
gc.collect()
