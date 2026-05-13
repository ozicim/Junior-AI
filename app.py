import streamlit as st
import firebase_admin
from akademik_engine import AkademikEngine
from mevzuat_engine import MevzuatBulutEngine
from dilekce_engine import DilekceEngine
from akademik_sinav_modu import AkademikSinavEngine
from fpdf import FPDF
import os
import urllib.request

try:
    AkademikEngine.veritabanini_baslat()
except Exception as e:
    st.error(f"Veritabanı başlatılamadı: {e}")


# 1. SAYFA AYARLARI
st.set_page_config(page_title="JUNIOR AI", page_icon="⚖️", layout="centered")

# --- API ANAHTARINI BURAYA YAZ ---
MY_API_KEY = st.secrets["GEMINI_API_KEY"]


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


# 3. YARDIMCI FONKSİYONLAR
def ekran_degistir(yeni_ekran):
    st.session_state.aktif_ekran = yeni_ekran

def kanun_sec(kanun):
    st.session_state.secili_kanun = kanun
    st.session_state.bulunan_madde = None
    st.session_state.arama_sonuclari = []
    ekran_degistir('maddeSecim')
    
def metni_sayfalara_bol(metin, kelime_siniri=2000):
    kelimeler = metin.split()
    sayfalar = []
    for i in range(0, len(kelimeler), kelime_siniri):
        sayfalar.append(" ".join(kelimeler[i:i + kelime_siniri]))
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
        ["🏛️ Adliye (Mevzuat Sorgu)", "🎓 Akademi (Ders Notları)", "📝 Arzuhal(Dilekçe Yazım Merkezi)","⚖️ İçtihat Sorgulama"])
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
elif menu == "🎓 Akademi (Ders Notları)":
    st.header("🎓 Akademik Asistan")
    
    # Sekmeleri net bir şekilde tanımlıyoruz
    tab_mufredat, tab_notlar, tab_sinav = st.tabs(["📚 Müfredat", "📄 Notlarım", "📝 Sınav Modu"])
    
    # ==========================================
    # 1. SEKME: MÜFREDAT (Ders Listesi)
    # ==========================================
    with tab_mufredat:
        mufredat = AkademikEngine.get_akademik_mufredat()
        
        for sinif, dersler in mufredat.items():
            with st.expander(f"📍 {sinif}", expanded=False):
                for ders in dersler:
                    col_d, col_b = st.columns([4, 1])
                    with col_d:
                        st.markdown(f"{ders['ikon']} **{ders['isim']}**")
                    with col_b:
                        if st.button("Notları Aç", key=f"notes_{ders['id']}"):
                            st.session_state.secili_ders = ders
                            st.session_state.akademi_ekran = 'konular'
                            st.rerun()

        # Eğer bir ders seçildiyse alt konuları gösterelim
        if st.session_state.get('akademi_ekran') == 'konular':
            st.divider()
            secili = st.session_state.get('secili_ders', {})
            if secili:
                st.markdown(f"### 📑 {secili.get('isim', '')} Konu Başlıkları")
                konular = ["Genel Kavramlar", "Temel İlkeler", "Uygulama Örnekleri"]
                
                for konu in konular:
                    with st.expander(f"📙 {konu}"):
                        st.write("Bu konuya dair özet notlar burada yer alacak.")
                        if st.button("Hocadan Dinle (AI)", key=f"ai_{konu}_{secili['id']}"):
                            st.info(f"AI Hoca '{konu}' konusunu hazırlıyor...")

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

      # --- 3. KISIM: SORU SORMA ALANI (DİJİTAL KİTAP MODU) ---
        st.subheader("❓ Notlara Soru Sor")
        
        aktif_not_ismi = st.session_state.get('aktif_dosya', 'Hiçbiri (Genel Hukuk Bilgisi)')
        st.info(f"🔎 **Şu an incelenen evrak:** {aktif_not_ismi}")
        
        # Değişkenleri session_state'den güvenli bir şekilde alalım
        not_icerigi = st.session_state.get('islenmis_not', "")
        
        # Sadece bir tane soru kutusu kalsın ustam, eskilerini sildim
        soru_input = st.text_input("Hocaya sormak istediğin soru nedir?", placeholder="Örn: Butlan ve İptal farkı")
        
        # Sayfaları tutmak için session state hazırlığı
        if "hoca_sayfalar" not in st.session_state:
            st.session_state.hoca_sayfalar = []
        if "hoca_aktif_sayfa" not in st.session_state:
            st.session_state.hoca_aktif_sayfa = 0

        if st.button("👨‍🏫 Hocaya Sor"):
            if soru_input:
                st.markdown("### 🎓 JUNILEX Hoca Anlatıyor:")
                
                try:
                    # 1. Akışı (Streaming) başlatıyoruz - 3. parametre olarak notu ekledik
                    stream = AkademikEngine.notlarla_ai_hoca_anlat(MY_API_KEY, soru_input, not_icerigi)
            
                    # 2. SÜZGEÇ: Gelen ham paketlerden sadece metni çekiyoruz
                    def hoca_suzucu():
                        for parca in stream:
                            if hasattr(parca, 'text') and parca.text:
                                yield parca.text
            
                    # 3. Ekrana daktilo hızıyla basıyoruz ve TAM METNİ yakalıyoruz
                    tam_cevap = st.write_stream(hoca_suzucu)
                    
                    # 4. Yakaladığımız tam cevabı sayfalara bölüyoruz (Kitap Modu İçin)
                    paragraflar = tam_cevap.split('\n\n')
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
                    
                    # Sayfaları kaydedelim
                    st.session_state.hoca_sayfalar = sayfalar
                    st.session_state.hoca_aktif_sayfa = 0
                    
                except Exception as e:
                    st.error(f"Hoca anlatırken bir usul hatası oluştu: {e}")
            else:
                st.warning("Lütfen bir soru girin ustam.")

        if st.session_state.hoca_sayfalar:
            st.markdown("---")
            
            # Başlık ve İndirme Butonunu yan yana koyalım
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
            
            aktif = st.session_state.hoca_aktif_sayfa
            toplam_sayfa = len(st.session_state.hoca_sayfalar)
            
            # Estetik Kitap Sayfası
            with st.container(border=True):
                st.markdown(st.session_state.hoca_sayfalar[aktif])
                
            st.write("") 
            
            # Sayfa Navigasyonu
            col_sol, col_orta, col_sag = st.columns([1, 2, 1])
            
            with col_sol:
                if aktif > 0:
                    if st.button("⬅️ Önceki", key="btn_geri", use_container_width=True):
                        st.session_state.hoca_aktif_sayfa -= 1
                        st.rerun()
                        
            with col_orta:
                st.markdown(f"<div style='text-align: center; font-weight: bold; color: #4CAF50;'>Sayfa {aktif + 1} / {toplam_sayfa}</div>", unsafe_allow_html=True)
                
            with col_sag:
                if aktif < toplam_sayfa - 1:
                    if st.button("Sonraki ➡️", key="btn_ileri", use_container_width=True):
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

# --- MOD 4: İÇTİHAT SORGULAMA (Eksik Olan Kısım) ---
elif menu == "⚖️ İçtihat Sorgulama":
    st.header("⚖️ İçtihat ve Emsal Merkezi")
    
    # Mevzuattaki gibi ikili pencere yapısı
    tab1, tab2 = st.tabs(["🔍 Karar Analizi (Şerh)", "🔎 Emsal Karar Bulucu"])
    
    with tab1:
        st.subheader("📄 Mevcut Kararı İncele")
        karar_input = st.text_area("Karar Metni", height=300, key="karar_serh", placeholder="İncelemek istediğiniz kararı yapıştırın...")
        soru_input = st.text_input("Bu kararda neyi arıyoruz?", key="karar_soru")
        
        if st.button("⚖️ Kararı Şerh Düş"):
            if karar_input and soru_input:
                st.info("📊 Karar tetkik ediliyor...")
                from ictihat_engine import IctihatEngine
                stream = IctihatEngine.karar_analiz_et(MY_API_KEY, karar_input, soru_input)
                
                def ictihat_suzucu():
                    for parca in stream:
                        if hasattr(parca, 'text') and parca.text:
                            yield parca.text
                st.write_stream(ictihat_suzucu)
            else:
                st.warning("Lütfen alanları doldurunuz.")
        
        with tab2:
            st.subheader("🔎 Olaydan Emsal Bul")
            olay_input = st.text_area("Olayı Anlatın", height=250, key="o_input_new")
        
            if st.button("🔎 Benzer İçtihatları Getir", use_container_width=True):
                if olay_input:
                    st.info("🔎 Kütüphane taranıyor...")
                    # 1. AI'dan tam yanıtı alıyoruz
                    stream = IctihatEngine.emsal_ara(MY_API_KEY, olay_input)
                    tam_yanit = "".join([p.text for p in stream if hasattr(p, 'text')])
        
        #
                    st.session_state.kitap_sayfalari = metni_sayfalara_bol(tam_yanit, 2000)
                    st.session_state.aktif_sayfa = 0 # İlk sayfadan başla
                    from ictihat_engine import IctihatEngine
                
                    # 1. AI'dan tam yanıtı al (Akış bittikten sonra sayfalamaya geçeceğiz)
                    stream = IctihatEngine.emsal_ara(MY_API_KEY, olay_input)
                    tam_yanit = ""
                    placeholder = st.empty()
                
                    for parca in stream:
                        if hasattr(parca, 'text') and parca.text:
                            tam_yanit += parca.text
                            placeholder.markdown(tam_yanit + "▌")
                
                    # 2. Yanıtı sayfalara böl ve Session State'e kaydet
                    st.session_state.kitap_sayfalari = metni_sayfalara_bol(tam_yanit, 2000)
                    st.session_state.aktif_sayfa = 0
                    placeholder.empty()

            # 3. SAYFALAMA VE GÖRÜNÜM (Eğer hafızada sayfa varsa göster)
            if "kitap_sayfalari" in st.session_state and st.session_state.kitap_sayfalari:
                sayfalar = st.session_state.kitap_sayfalari
                aktif = st.session_state.aktif_sayfa
            
                # --- Dijital Kitap Sayfası Tasarımı ---
                st.markdown(f"""
                <div style="
                    background-color: #fdf6e3; 
                    padding: 40px; 
                    border-left: 12px solid #8e735b; 
                    border-radius: 5px; 
                    box-shadow: 5px 5px 20px rgba(0,0,0,0.1);
                    color: #2c2c2c;
                    font-family: 'Georgia', serif;
                    min-height: 500px;
                ">
                    <div style="text-align: right; font-size: 12px; color: #8e735b; font-weight: bold;">
                        SAYFA {aktif + 1} / {len(sayfalar)}
                    </div>
                    <h2 style="color: #8e735b; border-bottom: 1px solid #8e735b; margin-bottom: 20px;">📜 İÇTİHAT ŞERHİ</h2>
                    <div style="font-size: 17px; line-height: 1.8; text-align: justify;">
                        {sayfalar[aktif].replace('\n', '<br>')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # --- Sayfa Geçiş Butonları ---
                st.write("") # Boşluk
                col1, col2, col3 = st.columns([1, 2, 1])
            
                with col1:
                    if aktif > 0:
                        if st.button("⬅️ Önceki Sayfa", use_container_width=True):
                            st.session_state.aktif_sayfa -= 1
                            st.rerun()
            
                with col3:
                    if aktif < len(sayfalar) - 1:
                        if st.button("Sonraki Sayfa ➡️", use_container_width=True):
                            st.session_state.aktif_sayfa += 1
                            st.rerun()
            
                with col2:
                    st.write(f"<center>Toplam {len(sayfalar)} sayfa bulundu.</center>", unsafe_allow_html=True)
        
              
