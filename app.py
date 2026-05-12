import streamlit as st
from mevzuat_engine import MevzuatBulutEngine
from akademik_engine import AkademikEngine
from akademik_sinav_modu import AkademikSinavEngine
from dilekce_engine import DilekceEngine

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

# 4. CSS BLOĞU (TAŞMAYI ÖNLEYEN KESİN ÇÖZÜM)
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400..700;1,400..700&display=swap" rel="stylesheet">
    <style>
        /* Yazı Tipi */
        html, body, [class*="css"] { font-family: 'Lora', serif; }

        /* Başlık ve Logo Alanı */
        .header-container { text-align: center; padding: 20px 0; }
        .header-logo-svg { width: 65px; height: auto; margin: 0 auto 10px auto; display: block; }
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
    st.markdown("### 🏛️ JUNIOR AI PANEL")
    ana_mod = st.radio("Çalışma Alanı Seçiniz:", ["⚖️ Adliye (Mevzuat)", "🎓 Akademi (Ders Notları)", "📝Arzuhal(Dilekçe Yazım Merkezi))"])
    st.divider()
    st.info("Ozan Şahin Sicim | JUNIOR AI v2.0")

# 6. LOGO VE ÜST BAŞLIK
st.markdown("""
    <div class="header-container">
        <svg class="header-logo-svg" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="45" stroke="#C5A059" stroke-width="2" fill="none"/>
            <path d="M30 45C30 45 35 60 50 60C65 60 70 45 70 45" stroke="#C5A059" stroke-width="2" fill="none"/>
            <path d="M50 20V80" stroke="#C5A059" stroke-width="2"/>
            <path d="M25 35H75" stroke="#1A1A1A" stroke-width="4"/>
        </svg>
        <h1 class="main-title">JUNIOR AI</h1>
        <p class="sub-title">LEGAL INTELLIGENCE & ACADEMY</p>
    </div>
""", unsafe_allow_html=True)

# --- MOD 1: ADLİYE (MEVZUAT) ---
if "Adliye" in ana_mod:
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
        
        st.divider()
        st.subheader("🤖 JUNIOR AI Analizi")
        if st.button("🚀 Maddeyi Yapay Zeka ile Yorumla"):
            with st.spinner("AI analiz yapıyor..."):
                analiz = MevzuatBulutEngine.madde_analiz_et(MY_API_KEY, madde['metin'], kanun['isim'], madde['no'])
                st.markdown(f'<div class="hoca-anlatim-kutusu">{analiz}</div>', unsafe_allow_html=True)

# --- MOD 2: AKADEMİ ---
else:
    st.markdown("### 🎓 Akademik Kütüphane")
    tab_lib, tab_hoca, tab_sinav = st.tabs(["📂 Ders Notları", "👨‍🏫 JUNIOR AI Hoca", "📝 Sınav Modu"])

    with tab_lib:
        
        mufredat = AkademikEngine.get_akademik_mufredat()
    
    # 1. 2. 3. 4. Sınıf Grupları
    for sinif, dersler in mufredat.items():
        with st.expander(f"📍 {sinif}", expanded=False):
            for ders in dersler:
                col_d, col_b = st.columns([4, 1])
                with col_d:
                    st.markdown(f"{ders['ikon']} **{ders['isim']}**")
                with col_b:
                    # Derse özel 'Notları Aç' butonu
                    if st.button("Ders Notları", key=f"notes_{ders['id']}"):
                        st.session_state.secili_ders = ders
                        st.session_state.akademi_ekran = 'konular'
                        st.rerun()

    # Eğer bir ders seçildiyse alt konuları gösterelim
    if 'akademi_ekran' in st.session_state and st.session_state.akademi_ekran == 'konular':
        st.divider()
        secili = st.session_state.secili_ders
        st.markdown(f"### 📑 {secili['isim']} Konu Başlıkları")
        
        # Örnek Konu Başlıkları (Burayı her ders için özelleştirebiliriz)
        konular = ["Genel Kavramlar", "Temel İlkeler", "Uygulama Örnekleri"]
        
        for konu in konular:
            with st.expander(f"📙 {konu}"):
                st.write("Bu konuya dair özet notlar burada yer alacak.")
                if st.button("Hocadan Dinle (AI)", key=f"ai_{konu}_{secili['id']}"):
                    # AI Hoca sekmesine yönlendir veya burada anlat
                    st.info(f"AI Hoca '{konu}' konusunu hazırlıyor...")

    with tab_hoca:
        st.markdown("#### 👨‍🏫 Ders Notuna Göre Anlatım")
        st.write("Kendi PDF notlarını yükle, JUNIOR AI o notlara göre ders anlatsın.")
    
    # Dosya Yükleyici
    yuklenen_not = st.file_uploader("Ders Notunu Yükle (PDF veya TXT)", type=["pdf", "txt"])
    
    if yuklenen_not:
        st.success("Not başarıyla sisteme tanımlandı.")
        # Notu metne çevirip session_state'e alalım
        if 'islenmis_not' not in st.session_state:
            st.session_state.islenmis_not = AkademikEngine.dosyadan_metin_cikar(yuklenen_not)
    
    konu_sorgu = st.text_input("Notlarda hangi kısmı anlamadın?", placeholder="Örn: Butlan ve İptal farkı")
    
    if st.button("Hocam Notlara Bakıp Anlatır mısınız?", use_container_width=True):
        if konu_sorgu and yuklenen_not:
            with st.spinner("Hoca notlarını inceliyor..."):
                cevap = AkademikEngine.notlarla_ai_hoca_anlat(
                    MY_API_KEY, 
                    konu_sorgu, 
                    st.session_state.islenmis_not
                )
                st.markdown(f'<div class="hoca-anlatim-kutusu">{cevap}</div>', unsafe_allow_html=True)
        elif not yuklenen_not:
            st.warning("Lütfen önce bir ders notu yükleyin.")
        else:
            st.warning("Lütfen bir soru girin.")
    with tab_sinav:
        st.markdown("#### 📝 Pratik Çalışma")
        sinav_konusu = st.text_input("Sınav Konusu", placeholder="Örn: Ceza Hukuku Genel Hükümler")
        
        if st.button("🔥 Sınavı Başlat"):
            if sinav_konusu:
                with st.spinner("Sınav hazırlanıyor..."):
                    sonuc = AkademikSinavEngine.pratik_calisma_uret(MY_API_KEY, sinav_konusu, st.session_state.islenmis_not)
                    if "hata" in sonuc:
                        st.error(f"Sınav üretilemedi: {sonuc['hata']}")
                    else:
                        st.session_state.su_anki_sinav = sonuc
            else:
                st.warning("Lütfen bir konu girin.")

        # Hata kontrolü yaparak ekrana basma
        if st.session_state.su_anki_sinav:
            sinav = st.session_state.su_anki_sinav
            
            if "olay_kurgusu" in sinav:
                st.info(f"📖 OLAY: {sinav['olay_kurgusu']}")
                
                # Soruları tek tek dönüyoruz
                for i, soru in enumerate(sinav.get('sorular', [])):
                    st.markdown(f"---")
                    st.markdown(f"**Soru {i+1}:** {soru['soru']}")
                    
                    # BURASI KRİTİK: 'secim' burada tanımlanıyor
                    secim = st.radio(
                        f"Seçenekler ({i+1})", 
                        soru['secenekler'], 
                        key=f"q_{i}"
                    )
                    
                    # Kontrol butonu
                    if st.button(f"Kontrol Et ({i+1})", key=f"b_{i}"):
                        # Artık 'secim' yukarıda tanımlandığı için hata vermez
                        if secim.strip().lower() == soru['cevap'].strip().lower():
                            st.success(f"✅ DOĞRU! \n\n **Analiz:** {soru['analiz']}")
                        else:
                            st.error(f"❌ YANLIŞ! \n\n **Doğru Cevap:** {soru['cevap']}")
                            st.warning(f"**Gerekçe:** {soru['analiz']}")
            else:
                st.error("Sınav formatı bozuk. Lütfen sıfırlayıp tekrar başlatın.")
                # app.py içinde sekmelerin olduğu kısma ekle
tab_dilekce = st.tabs(["Dilekçe Yaz"]) # Mevcut sekmelerine ekle

# 3. BÖLÜM: DİLEKÇE (YENİ YERİ)
elif menu == "📝 Dilekçe Yazım Merkezi":
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
            with st.spinner("Hukuki terminolojiye uygun taslak hazırlanıyor..."):
                metin = DilekceEngine.dilekce_olustur(MY_API_KEY, d_konu, d_taraflar, d_olay, d_talep)
                st.session_state.son_dilekce = metin
                st.markdown("### 📄 Dilekçe Önizlemesi")
                st.text_area("", value=metin, height=400)
                
                # Word İndirme
                word_data = DilekceEngine.word_dosyasi_yap(metin)
                st.download_button(
                    label="📥 Word Dosyası Olarak Kaydet",
                    data=word_data,
                    file_name=f"{d_konu}_taslak.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
