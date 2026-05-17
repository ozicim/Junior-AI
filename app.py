import streamlit as st
import firebase_admin
import random
import smtplib
from email.mime.text import MIMEText
from akademik_engine import AkademikEngine
from mevzuat_engine import MevzuatBulutEngine
from dilekce_engine import DilekceEngine
from akademik_sinav_modu import AkademikSinavEngine
from ictihat_engine import IctihatEngine
from chat_engine import ChatEngine
from fpdf import FPDF
from firebase_admin import firestore, credentials
import os
import urllib.request
import google.generativeai as genai
import streamlit as st
import json

# =========================================
# 🔴 FIX #1: SAYFA AYARLARI EN BAŞA TAŞINDI
# =========================================
st.set_page_config(page_title="JUNIOR AI", page_icon="⚖️", layout="centered")

# ==========================================
# 💾 KALICI VERİTABANI MOTORU (JSON)
# ==========================================
DB_DOSYASI = "kullanicilar.json"


def veritabani_yukle():
    if not os.path.exists(DB_DOSYASI):
        baslangic_verisi = {
            "ozan@junilex.com": {"sifre": "123456", "isim": "Ozan Şahin Sicim"}
        }
        with open(DB_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(baslangic_verisi, f, ensure_ascii=False, indent=4)
        return baslangic_verisi
    with open(DB_DOSYASI, "r", encoding="utf-8") as f:
        return json.load(f)


def veritabani_kaydet(veri):
    with open(DB_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)


# ==========================================
# 📧 E-POSTA GÖNDERME MOTORU
# ==========================================
def onay_kodu_gonder(alici_mail, kod):
    gonderici_mail = "ozan.scm@gmail.com"
    # 🔴 FIX #1: Gmail şifresi Secrets'tan çekiliyor
    uygulama_sifresi = st.secrets["GMAIL_SIFRE"]

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


# ==========================================
# 🔐 GÜVENLİK VE VERİTABANI BAŞLATMA
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "aktif_kullanici" not in st.session_state:
    st.session_state.aktif_kullanici = ""
if "kullanici_veritabani" not in st.session_state:
    st.session_state.kullanici_veritabani = veritabani_yukle()
if "onay_bekleyen" not in st.session_state:
    st.session_state.onay_bekleyen = None

# ==========================================
# 🛑 GİRİŞ VE KAYIT EKRANI
# ==========================================
if not st.session_state.logged_in:
    st.markdown(
        """<style>[data-testid="collapsedControl"] {display: none;} [data-testid="stSidebar"] {display: none;}</style>""",
        unsafe_allow_html=True,
    )

    st.write("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            "<h1 style='text-align: center; font-size: 3rem;'>⚖️ JUNILEX</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; color: gray; font-size: 1.2rem; margin-bottom: 0px;'>Kıdemli Yapay Zeka Hukuk Asistanı</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; color: #64748b; font-size: 0.9rem;'><em>Geliştirici: Ozan Şahin Sicim<br>Çankırı Karatekin Üniversitesi Hukuk Fakültesi Öğrencisi</em></p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        tab_giris, tab_kayit = st.tabs(["🔐 Giriş Yap", "📝 Yeni Kayıt"])

        with tab_giris:
            giris_email = st.text_input("E-Posta Adresi", key="giris_email")
            giris_sifre = st.text_input("Şifre", type="password", key="giris_sifre")

            if st.button("🚀 Sisteme Giriş Yap", use_container_width=True):
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
                    st.rerun()
                else:
                    st.error("E-posta adresi veya şifre hatalı!")

        with tab_kayit:
            if st.session_state.onay_bekleyen is None:
                kayit_isim = st.text_input("İsim Soyisim", key="kayit_isim")
                kayit_email = st.text_input("E-Posta Adresi", key="kayit_email")
                kayit_sifre = st.text_input(
                    "Yeni Şifre", type="password", key="kayit_sifre"
                )
                kayit_sifre_tekrar = st.text_input(
                    "Şifre Tekrar", type="password", key="kayit_sifre_tekrar"
                )

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
                            basarili_mi, hata_mesaji = onay_kodu_gonder(
                                kayit_email, uretilen_kod
                            )

                        if basarili_mi:
                            st.session_state.onay_bekleyen = {
                                "isim": kayit_isim.title(),
                                "email": kayit_email,
                                "sifre": kayit_sifre,
                                "kod": uretilen_kod,
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
                st.info(
                    f"📧 **{st.session_state.onay_bekleyen['email']}** adresine 6 haneli bir doğrulama kodu gönderdik."
                )
                girilen_kod = st.text_input(
                    "Doğrulama Kodu", key="dogrulama_kodu", max_chars=6
                )

                col_onay1, col_onay2, col_onay3 = st.columns(3)

                with col_onay1:
                    if st.button("✅ Kodu Doğrula", use_container_width=True):
                        if girilen_kod == st.session_state.onay_bekleyen["kod"]:
                            yeni_mail = st.session_state.onay_bekleyen["email"]
                            st.session_state.kullanici_veritabani[yeni_mail] = {
                                "sifre": st.session_state.onay_bekleyen["sifre"],
                                "isim": st.session_state.onay_bekleyen["isim"],
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

# 🔴 FIX #6: Firebase bağlantısını session_state'te cache'le — bir kez başlat
if "firebase_db" not in st.session_state:
    try:
        AkademikEngine.veritabanini_baslat()
        st.session_state.firebase_db = firestore.client()
    except Exception as e:
        st.error(f"Veritabanı başlatılamadı: {e}")

# --- API ANAHTARLARI ---
MY_API_KEY = st.secrets["GEMINI_API_KEY"]
SERPER_API_KEY = st.secrets["SERPER_API_KEY"]

# ==========================================
# 📌 SESSION STATE BAŞLATMA
# ==========================================
if "aktif_ekran" not in st.session_state:
    st.session_state.aktif_ekran = "liste"
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


# ==========================================
# 🔴 FIX #4: STREAM İŞLEME FONKSİYONU
# ==========================================
def stream_isle_ve_goster(response, placeholder):
    """Stream cevabı işler, ekrana yazar, tam metni döndürür."""
    full_response = ""
    for chunk in response:
        try:
            if chunk.candidates:
                sebep = chunk.candidates[0].finish_reason.name
                if sebep not in ["STOP", "FINISH_REASON_UNSPECIFIED"]:
                    full_response += f"\n\n🚨 **[GOOGLE FİŞİ ÇEKTİ! SEBEP: {sebep}]**"
            if chunk.text:
                full_response += chunk.text
                placeholder.markdown(full_response + " ▌")
        except ValueError as ve:
            full_response += f"\n\n🛑 **[DEĞER HATASI (Filtre/Boşluk): {str(ve)}]**"
            placeholder.markdown(full_response)
            break
        except Exception as e:
            full_response += f"\n\n❌ **[TEKNİK HATA: {str(e)}]**"
            placeholder.markdown(full_response)
            break

    if not full_response.strip():
        full_response = "⚠️ Ustam, sistem tamamen sessiz kaldı. Çıktı engellendi."

    placeholder.markdown(full_response)
    return full_response


# ==========================================
# 3. YARDIMCI FONKSİYONLAR
# ==========================================
def ekran_degistir(yeni_ekran):
    st.session_state.aktif_ekran = yeni_ekran


def kanun_sec(kanun):
    st.session_state.secili_kanun = kanun
    st.session_state.bulunan_madde = None
    st.session_state.arama_sonuclari = []
    ekran_degistir("maddeSecim")


def metni_sayfalara_bol(metin, sayfa_boyutu=1000):
    """Metni belirtilen karakter sınırına göre sayfalara böler."""
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
# 4. CSS BLOĞU
# ==========================================
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400..700;1,400..700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Lora', serif; }
        .header-container { text-align: center; padding: 20px 0; }
        .header-logo-svg { width: 100px; height: auto; margin: 0 auto 10px auto; display: block; }
        .main-title { font-size: 52px; font-weight: 800; color: #1A1A1A; letter-spacing: 6px; margin: 0; text-transform: uppercase; }
        .sub-title { color: #C5A059; font-weight: 600; letter-spacing: 4px; font-size: 14px; text-align: center; margin-bottom: 20px; }

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
""",
    unsafe_allow_html=True,
)

# ==========================================
# 5. KENAR ÇUBUĞU (SIDEBAR)
# ==========================================
with st.sidebar:
    st.title("⚖️ Junilex AI")
    secim = st.radio(
        "Lütfen bir departman seçin:",
        [
            "🏛️ Adliye (Mevzuat Sorgu)",
            "🎓 Akademi (Ders Notları)",
            "📝 Arzuhal(Dilekçe Yazım Merkezi)",
            "⚖️ İçtihat Sorgulama",
            "💬 JUNILEX Chat",
        ],
    )
    st.divider()
    st.info("Ozan Şahin Sicim | JUNILEX AI v2.0")

    if st.sidebar.button("🗑️ Sohbeti Sıfırla"):
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": "Selam ustam, ben Junilex. Bugün hangi hukuki meseleyi aydınlatalım?",
            }
        ]
        st.rerun()

# ==========================================
# 6. LOGO VE ÜST BAŞLIK
# ==========================================
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# ==========================================
# 🧭 DEPARTMAN KONTROL PANELİ
# ==========================================
if secim == "🏛️ Adliye (Mevzuat Sorgu)":
    st.header("⚖️ JUNILEX Adliye - Mevzuat Araştırma Merkezi")

    kanun_listesi = MevzuatBulutEngine.get_kanunlar()

    st.markdown("### 🔍 Nokta Atışı Madde Sorgulama")
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        secilen_kanun_adi = st.selectbox(
            "İncelenecek Kanun",
            options=[k["isim"] for k in kanun_listesi],
            key="adliye_k_secim",
        )
        secilen_kanun = next(k for k in kanun_listesi if k["isim"] == secilen_kanun_adi)
    with col_m2:
        girilen_madde = st.text_input(
            "Madde No (Örn: 3, Geçici 2)", placeholder="No..."
        )

    st.write("<br>", unsafe_allow_html=True)
    if st.button("🚀 Maddeyi Getir", use_container_width=True):
        if girilen_madde.strip() == "":
            st.warning("Lütfen bir madde numarası girin!")
        else:
            if "aktif_madde" in st.session_state:
                del st.session_state["aktif_madde"]

            with st.spinner(
                f"Firestore'dan {secilen_kanun['kisaAd']} Madde {girilen_madde} çekiliyor..."
            ):
                try:
                    madde_verisi = MevzuatBulutEngine.madde_getir_buluttan(
                        secilen_kanun["kisaAd"], girilen_madde
                    )
                    st.session_state.aktif_madde = {
                        "kanun_adi": secilen_kanun_adi,
                        "madde_no": girilen_madde.upper(),
                        "baslik": madde_verisi.get("baslik", f"Madde {girilen_madde}"),
                        "metin": madde_verisi.get("metin", "Metin bulunamadı."),
                    }
                except Exception as e:
                    st.error(f"⚠️ Veritabanı Uyarısı: {str(e)}")
                    st.info(
                        "💡 Eğer bu kanunu veritabanına henüz eklemediyseniz, lütfen sayfanın altındaki Geliştirici Panelinden yerel senkronizasyon yapın."
                    )

    if "aktif_madde" in st.session_state:
        madde = st.session_state.aktif_madde
        st.markdown("---")
        st.subheader(f"📜 {madde['kanun_adi']} - Madde {madde['madde_no']}")
        st.markdown(f"**Mevzuat Başlığı:** {madde['baslik']}")
        st.info(madde["metin"])

        ozel_soru = st.text_input(
            "Bu maddeye ilişkin özel bir sorunuz var mı? (İsteğe bağlı)",
            placeholder="Yapay zekaya sorun...",
        )
        if st.button(
            "🤖 Maddeyi JUNILEX AI ile Analiz Et",
            use_container_width=True,
            type="primary",
        ):
            API_KEY = st.secrets["GEMINI_API_KEY"]
            with st.spinner("JUNILEX yapay zekası maddeyi yorumluyor..."):
                analiz_sonucu = MevzuatBulutEngine.madde_analiz_et(
                    api_key=API_KEY,
                    madde_metni=madde["metin"],
                    kanun_adi=madde["kanun_adi"],
                    madde_no=madde["madde_no"],
                    soru=ozel_soru,
                )
            st.markdown("### 🧠 JUNILEX Yapay Zeka Analiz Raporu")
            st.success(analiz_sonucu)

    if st.session_state.get("aktif_kullanici") == "Ozan Şahin Sicim":
        st.write("<br><br><br>", unsafe_allow_html=True)
        with st.expander(
            "🔑 JUNILEX Geliştirici Özel Veri Yükleme Paneli", expanded=False
        ):
            st.markdown(
                "<small>Devlet sitesinin IP engellerini aşmak için tarayıcınız üzerinden doğrudan Firestore enjeksiyonu yapar.</small>",
                unsafe_allow_html=True,
            )

            yuklenen_json = st.file_uploader(
                "Firebase Anahtar Dosyasını Seç (kilit.json)", type=["json"]
            )
            hedef_kanun_adi = st.selectbox(
                "Yüklenecek Kanun",
                options=[k["isim"] for k in kanun_listesi],
                key="admin_yerel_secim",
            )
            hedef_kanun = next(k for k in kanun_listesi if k["isim"] == hedef_kanun_adi)

            if st.button(
                "⚡ Kanunu Tarayıcıdan Firestore'a Fırlat", use_container_width=True
            ):
                if yuklenen_json is None:
                    st.error(
                        "Lütfen önce bilgisayarınızdaki kilit.json dosyasını yukarıya yükleyin!"
                    )
                else:
                    with st.spinner(
                        "Maddeler tarayıcınız üzerinden kazınıyor ve Firebase'e aktarılıyor..."
                    ):
                        try:
                            import json

                            credentials_dict = json.load(yuklenen_json)
                            if not firebase_admin._apps:
                                cred = credentials.Certificate(credentials_dict)
                                firebase_admin.initialize_app(cred)
                            local_db = firestore.client()

                            MevzuatBulutEngine.kanunu_buluta_yukle(
                                hedef_kanun["id"],
                                hedef_kanun["kisaAd"],
                                ozel_db=local_db,
                            )
                        except Exception as e:
                            st.error(f"Yerel Enjeksiyon Hatası: {str(e)}")

elif secim == "🎓 Akademi (Ders Notları)":
    st.header("🎓 Akademik Asistan")

    tab_mufredat, tab_notlar, tab_sinav = st.tabs(
        ["📚 Müfredat", "📄 Notlarım", "📝 Sınav Modu"]
    )
    mufredat_sozlugu = AkademikEngine.get_akademik_mufredat()
    ders_listesi = []
    for sinif_adi, dersler in mufredat_sozlugu.items():
        for ders in dersler:
            ders_listesi.append(f"{ders['ikon']} {ders['isim']}")

    konu_listesi = ["Genel Tanımlar", "Hoca Notları", "Özet Analiz"]

    with tab_mufredat:
        st.subheader("📚 Ders ve Konu Seçimi")
        col1, col2 = st.columns(2)
        with col1:
            secilen_ders = st.selectbox(
                "Ders Seçiniz", options=ders_listesi, key="akademi_ders_v3"
            )
        with col2:
            secilen_konu = st.selectbox(
                "Konu Seçiniz", options=konu_listesi, key="akademi_konu_v3"
            )

        akademik_input = st.text_area(
            "Eklemek istediğiniz ders notları veya sorular (Opsiyonel)",
            height=100,
            key="akademi_text",
        )

        if st.button("📚 Notları Analiz Et / Özetle", use_container_width=True):
            try:
                with st.spinner("Hoca ders notlarını hazırlıyor..."):
                    from akademik_engine import AkademikEngine

                    sonuc = AkademikEngine.mufredat_hoca_anlat(
                        MY_API_KEY,
                        SERPER_API_KEY,
                        secilen_ders,
                        secilen_konu,
                        akademik_input,
                    )

                    if sonuc:
                        st.session_state.akademi_notlari = metni_sayfalara_bol(
                            sonuc, 300
                        )
                        st.session_state.akademi_aktif_sayfa = 0
                        st.success("✅ Ders notları başarıyla hazırlandı!")
                        st.rerun()
                    else:
                        st.error(
                            "AI bir sonuç döndürmedi. Lütfen API anahtarını kontrol edin."
                        )
            except Exception as e:
                st.error(f"Hoca derse giremedi ustam: {e}")

        if "akademi_notlari" in st.session_state and st.session_state.akademi_notlari:
            import re

            sayfalar = st.session_state.akademi_notlari
            aktif = st.session_state.get("akademi_aktif_sayfa", 0)

            icerik = sayfalar[aktif]

            icerik = re.sub(
                r"#{3}\s+(.*?)(?=\n|$)",
                r"<h3 style='color:#1b5e20; font-family:Georgia; border-bottom: 2px solid #2e7d32; padding-bottom:5px; margin-top:20px; font-size:18px;'>\1</h3><br>",
                icerik,
            )

            icerik = re.sub(
                r"#{1,2}\s+(.*?)(?=\n|$)",
                r"<br><br><b style='color:#3e2723; font-size:16px;'>\1</b><br>",
                icerik,
            )
            icerik = re.sub(
                r"#{4,5}\s+(.*?)(?=\n|$)",
                r"<br><b style='color:#3e2723; font-size:15px;'>\1</b><br>",
                icerik,
            )

            icerik = re.sub(r"\n\s*\*\*(.*?)\*\*", r"<br><br><b>\1</b>", icerik)

            icerik = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", icerik)

            icerik = icerik.replace(
                "🔍 GERÇEK EMSAL:",
                "<br><br><b style='color:#2e7d32;'>🔍 GERÇEK EMSAL:</b>",
            )
            icerik = icerik.replace(
                "⚖️ HUKUKİ DAYANAK:",
                "<br><br><b style='color:#795548;'>⚖️ HUKUKİ DAYANAK:</b>",
            )
            icerik = icerik.replace(
                "📢 SONUÇ:", "<br><br><b style='color:#1565c0;'>📢 SONUÇ:</b>"
            )

            icerik = icerik.replace("* ", "• ").replace("\n", "<br>")

            st.markdown(
                f"""
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
            """,
                unsafe_allow_html=True,
            )
            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                if aktif > 0:
                    if st.button("⬅️ Geri"):
                        st.session_state.akademi_aktif_sayfa -= 1
                        st.rerun()

            with col2:
                st.markdown(
                    f"<center><b>{aktif + 1} . Sayfa</b></center>",
                    unsafe_allow_html=True,
                )

            with col3:
                if aktif < len(sayfalar) - 1:
                    if st.button("İleri ➡️"):
                        st.session_state.akademi_aktif_sayfa += 1
                        st.rerun()

    with tab_notlar:
        st.header("📥 Not Yükleme Alanı")

        uploaded_file = st.file_uploader(
            "Notunu Buraya Yükle (PDF)", type="pdf", key="main_uploader"
        )

        if uploaded_file is not None:
            dosya_ismi = uploaded_file.name

            with st.spinner("PDF okunuyor ve arşive işleniyor... (Bu biraz sürebilir)"):
                cikarilan_metin = AkademikEngine.dosyadan_metin_cikar(uploaded_file)

                try:
                    db = st.session_state.firebase_db

                    db.collection("ders_notlari").add(
                        {
                            "dosya_adi": dosya_ismi,
                            "metin": cikarilan_metin,
                            "tarih": firestore.SERVER_TIMESTAMP,
                        }
                    )

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
                    col_isim, col_sec, col_sil = st.columns([3, 1, 1])

                    with col_isim:
                        st.markdown(f"📄 **{not_adi}**")

                    with col_sec:
                        if st.button("✅ Seç", key=f"sec_{not_adi}"):
                            eski_metin = AkademikEngine.not_icerigi_getir(not_adi)

                            if eski_metin:
                                st.session_state.islenmis_not = eski_metin
                                st.session_state.aktif_dosya = not_adi
                                st.success(
                                    f"📌 '{not_adi}' masaya koyuldu, soruları buna soracaksın!"
                                )
                            else:
                                st.warning(
                                    "Bu dosyanın metni yok! (Eski, hatalı yükleme olabilir. Lütfen silip tekrar yükle.)"
                                )

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

        aktif_not_ismi = st.session_state.get(
            "aktif_dosya", "Hiçbiri (Genel Hukuk Bilgisi)"
        )
        st.info(f"🔎 **Şu an incelenen evrak:** {aktif_not_ismi}")

        not_icerigi = st.session_state.get("islenmis_not", "")

        soru_input = st.text_input(
            "Hocaya sormak istediğin soru nedir?",
            placeholder="Örn: Butlan ve İptal farkı",
            key="hoca_not_soru_input",
        )

        if st.button("Hocadan Dinle", key="btn_hoca_dinle_notlar"):
            if not_icerigi:
                with st.spinner("Hoca kürsüye çıkıyor, notları inceliyor..."):
                    try:
                        sonuc = AkademikEngine.notlarla_ai_hoca_anlat(
                            MY_API_KEY, aktif_not_ismi, not_icerigi
                        )

                        if sonuc:
                            paragraflar = sonuc.split("\n\n")
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
                    urllib.request.urlretrieve(
                        "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf",
                        font_reg,
                    )
                if not os.path.exists(font_bold):
                    urllib.request.urlretrieve(
                        "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
                        font_bold,
                    )

                svg_logo = """<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="50" cy="50" r="45" stroke="#C5A059" stroke-width="2" fill="none"/>
                    <path d="M30 45C30 45 35 60 50 60C65 60 70 45 70 45" stroke="#C5A059" stroke-width="2" fill="none"/>
                    <path d="M50 20V80" stroke="#C5A059" stroke-width="2"/>
                    <path d="M25 35H75" stroke="#1A1A1A" stroke-width="4"/>
                </svg>"""

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
                pdf.cell(0, 6, f"İncelenen Evrak: {aktif_not_ismi}", ln=True, align="C")

                pdf.set_font("Roboto", "", size=10)
                pdf.cell(0, 6, f"İncelenen Evrak: {aktif_not_ismi}", ln=True, align="C")
                pdf.cell(
                    0,
                    6,
                    "Hazırlayan: Ozan Şahin Sicim (Çankırı Karatekin Üniversitesi Hukuk Fakültesi)",
                    ln=True,
                    align="C",
                )
                pdf.ln(10)

                pdf.set_font("Roboto", size=11)
                pdf.multi_cell(0, 7, tam_metin)

                pdf_bytes = bytes(pdf.output())

                st.download_button(
                    label="📥 PDF Olarak İndir",
                    data=pdf_bytes,
                    file_name=f"Junilex_Mutaala_{aktif_not_ismi}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            aktif = st.session_state.hoca_aktif_sayfa
            sayfalar = st.session_state.hoca_sayfalar

            icerik = sayfalar[aktif]

            st.markdown(
                f"""
            <div style="background-color: #fcfaf5; padding: 40px; border: 1px solid #e0dcd0; border-top: 8px solid #2e7d32; border-radius: 4px; color: #2c3e50;">
                <div style="font-size: 12px; color: #2e7d32; font-weight: bold; margin-bottom: 20px;">
                    🎓 NOT ANALİZİ - Sayfa {aktif + 1} / {len(sayfalar)}
                </div>
                <div style="font-size: 18px; line-height: 1.8;">
                    {icerik.replace("\n", "<br>")}
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

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
        st.markdown("#### 📝 Pratik Çalışma")
        sinav_konusu = st.text_input(
            "Sınav Konusu", placeholder="Örn: Ceza Hukuku Genel Hükümler"
        )

        if st.button("🔥 Sınavı Başlat"):
            if sinav_konusu:
                with st.spinner("Sınav hazırlanıyor..."):
                    islenmis = st.session_state.get("islenmis_not", "")
                    sonuc = AkademikSinavEngine.pratik_calisma_uret(
                        MY_API_KEY, sinav_konusu, islenmis
                    )

                    if "hata" in sonuc:
                        st.error(f"Sınav üretilemedi: {sonuc['hata']}")
                    else:
                        st.session_state.su_anki_sinav = sonuc
            else:
                st.warning("Lütfen bir konu girin.")

        if st.session_state.get("su_anki_sinav"):
            sinav = st.session_state.su_anki_sinav

            if "olay_kurgusu" in sinav:
                st.info(f"📖 OLAY: {sinav['olay_kurgusu']}")

                for i, soru_data in enumerate(sinav.get("sorular", [])):
                    st.markdown("---")
                    st.markdown(f"**Soru {i+1}:** {soru_data['soru']}")

                    secim = st.radio(
                        f"Seçenekler ({i+1})", soru_data["secenekler"], key=f"q_{i}"
                    )

                    if st.button(f"Kontrol Et ({i+1})", key=f"b_{i}"):
                        if secim.strip().lower() == soru_data["cevap"].strip().lower():
                            st.success(
                                f"✅ DOĞRU! \n\n **Analiz:** {soru_data['analiz']}"
                            )
                        else:
                            st.error(
                                f"❌ YANLIŞ! \n\n **Doğru Cevap:** {soru_data['cevap']}"
                            )
                            st.warning(f"**Gerekçe:** {soru_data['analiz']}")
            else:
                st.error("Sınav formatı bozuk. Lütfen sıfırlayıp tekrar başlatın.")

elif secim == "📝 Arzuhal(Dilekçe Yazım Merkezi)":
    st.header("📝 Dilekçe Taslağı Oluştur")
    st.info("Lütfen olayları ve tarafları detaylıca giriniz.")

    col1, col2 = st.columns(2)
    with col1:
        d_konu = st.text_input(
            "Dilekçe Konusu", placeholder="Örn: Hakaret Suçu Şikayeti"
        )
        d_taraflar = st.text_area("Taraflar", placeholder="Davacı: ...\nDavalı: ...")
    with col2:
        d_olay = st.text_area(
            "Olayın Özeti", placeholder="Olayları buraya özetleyin..."
        )
        d_talep = st.text_area(
            "Talepler", placeholder="Netice-i talep kısmını buraya yazın..."
        )

    if st.button("📝 Dilekçeyi Yaz ve Hazırla"):
        if d_konu and d_olay:
            st.markdown("### 📄 JUNILEX Dilekçe Taslağı:")

            stream = DilekceEngine.dilekce_olustur(
                MY_API_KEY, d_konu, d_taraflar, d_olay, d_talep
            )

            def dilekce_suzucu():
                for parca in stream:
                    if parca.text:
                        yield parca.text

            tam_metin = st.write_stream(dilekce_suzucu)

            st.session_state.son_dilekce = tam_metin

            word_data = DilekceEngine.word_dosyasi_yap(tam_metin)

            st.download_button(
                label="📥 Word Dosyası Olarak Kaydet",
                data=word_data,
                file_name=f"{d_konu}_taslak.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        else:
            st.warning("Lütfen konu ve olay özetini doldurunuz ustam!")

elif secim == "⚖️ İçtihat Sorgulama":
    st.header("⚖️ İçtihat ve Emsal Merkezi")

    tab1, tab2 = st.tabs(["🔍 Karar Analizi (Şerh)", "🔎 Emsal Karar Bulucu"])

    with tab1:
        st.subheader("⚖️ Karar Analiz Modülü")
        karar_metni = st.text_area(
            "Yargıtay Karar Metnini Buraya Yapıştırın",
            height=250,
            key="karar_text_area",
        )
        soru_input = st.text_input(
            "Bu kararla ilgili neyi merak ediyorsunuz?",
            placeholder="Örn: İspat yükü kime verilmiş?",
            key="karar_soru_input",
        )

        if st.button("⚖️ Analiz Et", use_container_width=True, key="btn_analiz_et"):
            if karar_metni and soru_input:
                with st.spinner("Hakim Junilex dosyayı inceliyor..."):
                    from ictihat_engine import IctihatEngine

                    response = IctihatEngine.karar_analiz_et(
                        MY_API_KEY, karar_metni, soru_input
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

        if "analiz_sayfalari" in st.session_state and st.session_state.analiz_sayfalari:
            sayfalar = st.session_state.analiz_sayfalari
            aktif = st.session_state.analiz_aktif_sayfa

            st.markdown(
                f"""
            <div style="background-color: #fdfaf1; padding: 30px; border-left: 10px solid #5d4037; border-radius: 5px; color: #2c3e50; font-family: 'Georgia', serif;">
                <div style="font-size: 12px; color: #8d6e63; font-weight: bold; text-transform: uppercase;">🏛️ Analiz Şerhi - Sayfa {aktif + 1} / {len(sayfalar)}</div>
                <div style="font-size: 16px; line-height: 1.7; text-align: justify; margin-top: 15px;">
                    {sayfalar[aktif].replace("\n", "<br>")}
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

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

        olay_input = st.text_area(
            "Hukuki Olayı Detaylıca Anlatın",
            height=150,
            placeholder="Örn: Banka hesabından rıza dışı para çekilmesi...",
            key="emsal_olay_girdisi_v4",
        )

        if st.button("🔎 Analiz Et", use_container_width=True, key="btn_emsal_bul_v4"):
            if olay_input:
                with st.spinner("Junilex kütüphaneleri tarıyor ve analiz ediyor..."):
                    try:
                        from ictihat_engine import IctihatEngine

                        sonuc = IctihatEngine.emsal_ara(
                            MY_API_KEY, SERPER_API_KEY, olay_input
                        )

                        if sonuc:
                            st.session_state.kitap_sayfalari = metni_sayfalara_bol(
                                sonuc, 1200
                            )
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

            st.markdown(
                f"""
            <div style="background-color: #fdfaf1; padding: 30px; border-left: 10px solid #5d4037; border-radius: 5px; color: #2c3e50; font-family: 'Georgia', serif;">
                <div style="font-size: 12px; text-transform: uppercase; color: #8d6e63; margin-bottom: 10px; font-weight: bold;">🏛️ Yargıtay Yönelim Şerhi - Sayfa {aktif_emsal + 1} / {len(sayfalar_emsal)}</div>
                <div style="font-size: 16px; line-height: 1.8; text-align: justify;">{sayfalar_emsal[aktif_emsal].replace("\n", "<br>")}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

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

elif secim == "💬 JUNILEX Chat":
    st.header("💬 JUNILEX Chat")

    if "chat_mode" not in st.session_state:
        st.session_state.chat_mode = "Özet"
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": "Selam ustam, hangi meseleyi aydınlatalım?",
            }
        ]

    for message in st.session_state.chat_messages:
        if message["role"] == "user":
            simge = "https://api.dicebear.com/9.x/micah/png?seed=OzanSahinSicim&backgroundColor=transparent"
        else:
            simge = "https://api.dicebear.com/9.x/bottts-neutral/png?seed=Junilex&backgroundColor=0f172a"

        with st.chat_message(message["role"], avatar=simge):
            st.markdown(message["content"])

    st.markdown("---")

    col_devam, col_mod = st.columns([1, 1])

    with col_mod:
        with st.popover(
            f"🧠 Mod: {st.session_state.chat_mode}", use_container_width=True
        ):
            secilen_mod = st.radio(
                "Zeka Yapılandırması:",
                ["Özet", "⚖️ Detaylı Analiz"],
                index=0 if "Özet" in st.session_state.chat_mode else 1,
                key="chat_mode_radio",
            )
            if secilen_mod != st.session_state.chat_mode:
                st.session_state.chat_mode = secilen_mod
                st.rerun()

    with col_devam:
        if (
            len(st.session_state.chat_messages) > 1
            and st.session_state.chat_messages[-1]["role"] == "assistant"
        ):
            if st.button("⏭️ Devam Et", help="Cevap yarıda kaldıysa tıklayın."):

                yarim_kalan_mesaj = st.session_state.chat_messages[-1]["content"]
                son_kelimeler = (
                    yarim_kalan_mesaj[-60:].strip()
                    if len(yarim_kalan_mesaj) > 60
                    else yarim_kalan_mesaj
                )

                devam_komutu = (
                    f"Önceki cevabın tam olarak şu kelimelerle yarım kaldı: '...{son_kelimeler}'.\n"
                    "KRİTİK GÖREV: Lütfen asla giriş cümlesi kurma, konuyu baştan anlatma ve yazdıklarını tekrar etme. "
                    "SADECE yarım kalan kelimeyi/cümleyi tamamla ve doğrudan konunun devamını yaz."
                )

                st.session_state.chat_messages.append(
                    {"role": "user", "content": "Devam et..."}
                )

                with st.chat_message(
                    "assistant",
                    avatar="https://api.dicebear.com/9.x/bottts-neutral/png?seed=Junilex&backgroundColor=0f172a",
                ):
                    message_placeholder = st.empty()

                    response = ChatEngine.yanit_uret(
                        MY_API_KEY,
                        st.session_state.chat_messages[:-1],
                        devam_komutu,
                        mod=st.session_state.chat_mode,
                    )

                    if isinstance(response, str) and response.startswith("HATA"):
                        st.error(response)
                    else:
                        full_response = stream_isle_ve_goster(
                            response, message_placeholder
                        )
                        st.session_state.chat_messages.append(
                            {"role": "assistant", "content": full_response}
                        )
                        st.rerun()

    if prompt := st.chat_input("Mesajınızı yazın..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        container = st.empty()

        with container.container():
            with st.chat_message(
                "user",
                avatar="https://api.dicebear.com/9.x/micah/png?seed=OzanSahinSicim&backgroundColor=transparent",
            ):
                st.markdown(prompt)

            with st.chat_message(
                "assistant",
                avatar="https://api.dicebear.com/9.x/bottts-neutral/png?seed=Junilex&backgroundColor=0f172a",
            ):
                message_placeholder = st.empty()

                response = ChatEngine.yanit_uret(
                    MY_API_KEY,
                    st.session_state.chat_messages[:-1],
                    prompt,
                    mod=st.session_state.chat_mode,
                )

                if isinstance(response, str) and response.startswith("HATA"):
                    st.error(response)
                else:
                    full_response = stream_isle_ve_goster(response, message_placeholder)
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "content": full_response}
                    )
                    st.rerun()
