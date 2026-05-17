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
    # TAB 1: MADDE NUMARASI İLE NOKTA ATIŞI ARAMA
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
    # TAB 2: KELİME / KAVRAM İLE İÇERİK TARAMASI
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
                with st.expander(f"📜 {m['baslik']}"):
                    st.info(m['metin'])
                    
                    if st.button("🏛️ Bu Maddeyi Yapay Zekaya Analiz Ettir", key=f"btn_analiz_k_{m['no']}_{i}"):
                        with st.spinner("🔮 Madde analiz ediliyor..."):
                            api_key = MY_API_KEY if 'MY_API_KEY' in locals() else st.secrets["GEMINI_API_KEY"]
                            akış = MevzuatBulutEngine.madde_analiz_et(api_key, secilen_kanun['kisaAd'], m['no'], m['metin'])
                            if akış: st.write_stream(akış)
