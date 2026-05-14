import streamlit as st
import firebase_admin
from akademik_engine import AkademikEngine
from mevzuat_engine import MevzuatBulutEngine
from dilekce_engine import DilekceEngine
from akademik_sinav_modu import AkademikSinavEngine
from ictihat_engine import IctihatEngine
from chat_engine import ChatEngine
from fpdf import FPDF
import os
import urllib.request
import google.generativeai as genai
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

# 5. KENAR ÇUBUĞU
with st.sidebar:
    st.title("⚖️ Junilex AI")
    # İşte burası 'menu' değişkeninin doğduğu yer:
    menu = st.radio(
        "Lütfen bir departman seçin:",
        ["🏛️ Adliye (Mevzuat Sorgu)", "🎓 Akademi (Ders Notları)", "📝 Arzuhal(Dilekçe Yazım Merkezi)","⚖️ İçtihat Sorgulama", "💬 JUNILEX Chat"])
    st.divider()
    st.info("Ozan Şahin Sicim | JUNILEX AI v2.0")

# 6. LOGO VE ÜST BAŞLIK
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

# --- MOD 1: ADLİYE (MEVZUAT) ---
if "Adliye" in menu:
    if st.session_state.aktif_ekran == 'liste':
        st.markdown("### ⚖️ Mevzuat Kütüphanesi")
        kategori_ikonlari = {"Ceza Hukuku": "⚖️", "Özel Hukuk": "🏛️", "Ticaret Hukuku": "💼", "İş Hukuku": "🤝"}
        tum_kanunlar = MevzuatBulutEngine.get_kanunlar()
        kategoriler = sorted(list(set(k['kategori'] for k in tum_kanunlar)))

        for kategori in kategoriler:
            ikon = kategori_ikonlari.get(kategori, "📌")
            with st.expander(f"{ikon} {kategori}", expanded=False):
                kategori_kanunlari = [k for k in tum_kanunlar if k['kategori'] == kategori]
                for kanun in kategori_kanunlari:
                    c1, c2 = st.columns([4, 1])
                    with c1: st.markdown(f"**{kanun['isim']}** ({kanun['kisaAd']})")
                    with c2:
                        if st.button("Seç", key=f"btn_{kanun['id']}", use_container_width=True):
                            kanun_sec(kanun)
                            st.rerun()

    elif st.session_state.aktif_ekran == 'maddeSecim':
        kanun = st.session_state.secili_kanun
        if st.button("⬅️ Kanun Listesine Dön"):
            ekran_degistir('liste')
            st.rerun()
        
        st.markdown(f"## 📖 {kanun['isim']}")
        t1, t2 = st.tabs(["🔢 Madde No", "🔍 Kelime ile Ara"])
        
        with t1:
            with st.form("no_sorgu"):
                no_in = st.text_input("Madde Numarası")
                if st.form_submit_button("Sorgula"):
                    try:
                        st.session_state.bulunan_madde = MevzuatBulutEngine.madde_getir_buluttan(kanun['kisaAd'], no_in.strip())
                        ekran_degistir('maddeGosterim')
                        st.rerun()
                    except Exception as e: st.error(str(e))

        with t2:
            with st.form("kelime_sorgu"):
                anahtar = st.text_input("Aranacak Kavram")
                if st.form_submit_button("Kanunu Tara"):
                    st.session_state.arama_sonuclari = MevzuatBulutEngine.kelime_ile_ara(kanun['kisaAd'], anahtar)
            
            if st.session_state.arama_sonuclari:
                for s in st.session_state.arama_sonuclari:
                    with st.expander(f"Madde {s['no']}: {s['baslik']}"):
                        st.write(s['metin'][:200] + "...")
                        if st.button("Tam Metin", key=f"det_{kanun['kisaAd']}_{s['no']}"):
                            st.session_state.bulunan_madde = s
                            ekran_degistir('maddeGosterim')
                            st.rerun()

    elif st.session_state.aktif_ekran == 'maddeGosterim':
        kanun = st.session_state.secili_kanun
        madde = st.session_state.bulunan_madde
        
        col_geri, col_ana = st.columns(2)
        with col_geri:
            if st.button("⬅️ Yeni Sorgu"):
                ekran_degistir('maddeSecim')
                st.rerun()
        with col_ana:
            if st.button("🏠 Ana Menü"):
                ekran_degistir('liste')
                st.rerun()
        
        p_html = "".join([f"<p>{p}</p>" for p in madde['metin'].split('\n') if p.strip()])
        st.markdown(f"""
            <div class="madde-kutusu">
                <div class="madde-baslik">
                    <span style="font-size:12px; color:#888; font-weight:400; text-transform:uppercase;">{kanun['isim']}</span><br>
                    Madde {madde['no']}: {madde['baslik']}
                </div>
                <div class="madde-icerik">{p_html}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if st.session_state.bulunan_madde: # Eğer bir madde bulunduysa
            # 1. Önce maddenin metnini bir değişkene hapsedelim
            mevcut_madde = st.session_state.bulunan_madde
            madde_metni = mevcut_madde['metin'] # İşte NameError'ı bitiren satır!
    
            st.divider()
            st.markdown("### 🤖 JUNILEX AI - Madde Yorumlama")
    
            mevzuat_sorusu = st.text_input("Bu madde hakkında neyi merak ediyorsun?", key="mevzuat_input")

            if st.button("⚖️ Maddeyi Analiz Et"):
                if mevzuat_sorusu and st.session_state.bulunan_madde:
                    st.info("📊 JUNILEX Analiz Ediyor...")
        
                    # 1. Akışı (Stream) başlatıyoruz
                    stream = MevzuatBulutEngine.madde_analiz_et(
                        MY_API_KEY, 
                        st.session_state.bulunan_madde['metin'], 
                        st.session_state.secili_kanun['isim'], 
                        st.session_state.bulunan_madde['no'], 
                        mevzuat_sorusu
                    )
        
                    # 2. İŞTE BURASI KRİTİK: Gelen paketlerden sadece metni süzen fonksiyon
                    def metin_suzucu():
                        for parca in stream:
                            # Paket boş değilse ve içinde metin varsa gönder
                            if parca.text:
                                yield parca.text

                    # 3. Filtrelenmiş metni daktilo gibi yazdırıyoruz
                    st.write_stream(metin_suzucu)
                else:
                    st.warning("Lütfen bir soru yazın ustam!")

# --- MOD 2: AKADEMİ ---
# app.py içinde İçtihat veya Akademi butonunun tam içine:
elif menu == "🎓 Akademi (Ders Notları)":
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
                with st.spinner("Hoca ders notlarını hazırlıyor..."):
                    # AKADEMİK MOTORU KULLANIYORUZ
                    from akademik_engine import AkademikEngine
                    
                    # Motoru çağır (Ders, Konu ve Ek Notu gönderiyoruz)
                    sonuc = AkademikEngine.mufredat_hoca_anlat(
                        MY_API_KEY, 
                        SERPER_API_KEY, 
                        secilen_ders, 
                        secilen_konu, 
                        akademik_input
                    )
                    
                    if sonuc:
                        # Sonucu sayfalara böl ve hafızaya al
                        st.session_state.akademi_notlari = metni_sayfalara_bol(sonuc, 300)
                        st.session_state.akademi_aktif_sayfa = 0
                        st.success("✅ Ders notları başarıyla hazırlandı!")
                        st.rerun() # Sayfayı yenileyerek kitabı göster
                    else:
                        st.error("AI bir sonuç döndürmedi. Lütfen API anahtarını kontrol edin.")
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
elif menu == "📝 Arzuhal(Dilekçe Yazım Merkezi)":
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
elif menu == "⚖️ İçtihat Sorgulama":
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

elif menu == "💬 JUNILEX Chat":
    # Başlık ve Mod Göstergesi yan yana olsun
    st.header("💬 JUNILEX Chat")
    
    # 1. Zeka Modu Menüsü (Popover - Tıklayınca açılan kısım)
    # Soru sorma kutusunun hemen üzerinde şık bir buton olarak görünecek
    with st.popover(f"⚡ Mod: {st.session_state.get('chat_mode', 'Özet')}"):
        st.markdown("### 🧠 Zeka Yapılandırması")
        yeni_mod = st.radio(
            "Yanıt derinliğini seçin:",
            ["Özet", "Detaylı Analiz"],
            key="chat_mode_radio",
            help="Özet: Hızlı ve net. Detaylı: Derin mütalaa ve kanun analizi."
        )
        st.session_state.chat_mode = yeni_mod
        st.info(f"Şu an '{yeni_mod}' modundasın ustam.")

    # Sohbet Hafızası Başlatma
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [{"role": "assistant", "content": "Selam ustam, hangi hukuki meseleyi istişare edelim?"}]

    # Mesajları Görüntüle
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 2. Soru Sorma Kısmı
    if prompt := st.chat_input("Mesajınızı yazın..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            from chat_engine import ChatEngine
            
            # Seçilen modu Session State'den alıp motora gönderiyoruz
            aktif_mod = st.session_state.get('chat_mode', 'Özet')
            
            response = ChatEngine.yanit_uret(
                MY_API_KEY, 
                st.session_state.chat_messages[:-1], 
                prompt,
                mod=aktif_mod
            )
            
            if isinstance(response, str) and response.startswith("HATA"):
                st.error(response)
            else:
                for chunk in response:
                    if hasattr(chunk, "text") and chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + " ▌")
                
                message_placeholder.markdown(full_response)
                st.session_state.chat_messages.append({"role": "assistant", "content": full_response})

    # Sidebar Temizleme Butonu
    if st.sidebar.button("🗑️ Sohbeti Sıfırla"):
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Selam ustam, ben Junilex. Bugün hangi hukuki meseleyi aydınlatalım?"}
        ]
        st.rerun()
