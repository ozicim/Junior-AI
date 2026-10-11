import streamlit as st
import chromadb
import google.generativeai as genai
import re
import json
import os
import zipfile

YASAL_UYARI = (
    "⚠️ **Bilgi Amaçlıdır:** Bu madde metni Junilex yerel veritabanından getirilmiştir. "
    "Güncel ve hukuken bağlayıcı metin için mevzuat.gov.tr adresini kontrol ediniz."
)


class MevzuatBulutEngine:
    _model = None

    @classmethod
    def get_kanunlar(cls):
        return [
            # --- KAMU HUKUKU ---
            {
                "id": "2709",
                "kisaAd": "AY",
                "isim": "Türkiye Cumhuriyeti Anayasası",
                "kategori": "Kamu Hukuku",
                "aciklama": "Devletin Temel Yapısı ve Haklar",
            },
            {
                "id": "2577",
                "kisaAd": "İYUK",
                "isim": "İdari Yargılama Usulü Kanunu",
                "kategori": "Kamu Hukuku",
                "aciklama": "İptal ve Tam Yargı Davaları",
            },
            {
                "id": "657",
                "kisaAd": "DMK",
                "isim": "Devlet Memurları Kanunu",
                "kategori": "Kamu Hukuku",
                "aciklama": "Memur Hakları ve Disiplin Hükümleri",
            },
            {
                "id": "2942",
                "kisaAd": "KK",
                "isim": "Kamulaştırma Kanunu",
                "kategori": "Kamu Hukuku",
                "aciklama": "Kamu Yararı ve Kamulaştırma Bedeli",
            },
            # --- CEZA HUKUKU ---
            {
                "id": "5237",
                "kisaAd": "TCK",
                "isim": "Türk Ceza Kanunu",
                "kategori": "Ceza Hukuku",
                "aciklama": "Suçlar ve Ceza Sorumluluğu",
            },
            {
                "id": "5271",
                "kisaAd": "CMK",
                "isim": "Ceza Muhakemesi Kanunu",
                "kategori": "Ceza Hukuku",
                "aciklama": "Ceza Soruşturma ve Kovuşturma Usulü",
            },
            {
                "id": "5275",
                "kisaAd": "CGİK",
                "isim": "Ceza ve Güvenlik Tedbirlerinin İnfazı Hakkında Kanun",
                "kategori": "Ceza Hukuku",
                "aciklama": "İnfaz Rejimi ve Denetimli Serbestlik",
            },
            # --- ÖZEL HUKUK ---
            {
                "id": "4721",
                "kisaAd": "TMK",
                "isim": "Türk Medeni Kanunu",
                "kategori": "Özel Hukuk",
                "aciklama": "Kişiler, Aile, Miras ve Eşya Hukuku",
            },
            {
                "id": "6098",
                "kisaAd": "TBK",
                "isim": "Türk Borçlar Kanunu",
                "kategori": "Özel Hukuk",
                "aciklama": "Sözleşmeler ve Haksız Fiil Tazminatı",
            },
            {
                "id": "6502",
                "kisaAd": "TKHK",
                "isim": "Tüketicinin Korunması Hakkında Kanun",
                "kategori": "Özel Hukuk",
                "aciklama": "Ayıplı Mal ve Tüketici Hakem Heyeti",
            },
            {
                "id": "4722",
                "kisaAd": "TMKYK",
                "isim": "Türk Medeni Kanununun Yürürlüğü ve Uygulama Şekli Hakkında Kanun",
                "kategori": "Özel Hukuk",
                "aciklama": "Medeni Kanun Geçiş Hükümleri",
            },
            # --- TİCARET & İŞ HUKUKU ---
            {
                "id": "6102",
                "kisaAd": "TTK",
                "isim": "Türk Ticaret Kanunu",
                "kategori": "Ticaret & İş Hukuku",
                "aciklama": "Şirketler, Kıymetli Evrak ve Deniz Ticareti",
            },
            {
                "id": "4857",
                "kisaAd": "İK",
                "isim": "İş Kanunu",
                "kategori": "Ticaret & İş Hukuku",
                "aciklama": "İşçi-İşveren İlişkileri ve Kıdem Tazminatı",
            },
            {
                "id": "6331",
                "kisaAd": "İSGK",
                "isim": "İş Sağlığı ve Güvenliği Kanunu",
                "kategori": "Ticaret & İş Hukuku",
                "aciklama": "İş Kazaları ve Önleyici Tedbirler",
            },
            {
                "id": "5953",
                "kisaAd": "BİK",
                "isim": "Basın İş Kanunu",
                "kategori": "Ticaret & İş Hukuku",
                "aciklama": "Gazeteciler ve Basın Çalışanları Hakları",
            },
            # --- USUL & İCRA HUKUKU ---
            {
                "id": "6100",
                "kisaAd": "HMK",
                "isim": "Hukuk Muhakemeleri Kanunu",
                "kategori": "Usul & İcra Hukuku",
                "aciklama": "Hukuk Davaları Yargılama Usulü",
            },
            {
                "id": "2004",
                "kisaAd": "İİK",
                "isim": "İcra ve İflas Kanunu",
                "kategori": "Usul & İcra Hukuku",
                "aciklama": "İlamsız-İlamlı Takip ve İflas Rejimi",
            },
            {
                "id": "1136",
                "kisaAd": "AK",
                "isim": "Avukatlık Kanunu",
                "kategori": "Usul & İcra Hukuku",
                "aciklama": "Avukatlık Meslek Kuralları ve Barolar",
            },
            {
                "id": "2575",
                "kisaAd": "DK",
                "isim": "Danıştay Kanunu",
                "kategori": "Usul & İcra Hukuku",
                "aciklama": "Danıştay Organları ve Yargılama Alanı",
            },
            {
                "id": "2797",
                "kisaAd": "YK",
                "isim": "Yargıtay Kanunu",
                "kategori": "Usul & İcra Hukuku",
                "aciklama": "Yargıtay Daireleri ve İçtihadı Birleştirme",
            },
        ]

    @staticmethod
    @st.cache_resource
    def _get_chroma_collection():
        try:
            client = chromadb.PersistentClient(path="./junilex_vector_db")
            return client.get_or_create_collection(name="turk_mevzuati")
        except Exception as e:
            st.error(f"Veritabanı başlatılamadı: {e}")
            return None

    @classmethod
    def _modeli_hazirla(cls, api_key):
        if cls._model is None:
            genai.configure(api_key=api_key)
            cls._model = genai.GenerativeModel("models/gemini-2.5-flash")
        return cls._model

    @classmethod
    def kanunu_buluta_yukle(cls, *args, **kwargs):
        kanun_id = None
        kisa_ad = None
        bilinen_kanunlar = {k["id"]: k["kisaAd"] for k in cls.get_kanunlar()}
        tum_degerler = list(args) + list(kwargs.values())

        for deger in list(tum_degerler):
            if isinstance(deger, dict):
                tum_degerler.extend(deger.keys())
                tum_degerler.extend(deger.values())
        for v in tum_degerler:
            v_str = str(v).strip()
            if v_str in bilinen_kanunlar:
                kanun_id = v_str
                kisa_ad = bilinen_kanunlar[v_str]
                break
            elif v_str in bilinen_kanunlar.values():
                kisa_ad = v_str
                for k, val in bilinen_kanunlar.items():
                    if val == v_str:
                        kanun_id = k
                        break
                break
        if not kisa_ad or not kanun_id:
            st.error("Kritik Tarama Hatası: Kanun tanınamadı.")
            return 0

        zip_dosya_adi = "mevzuat_arsiv.zip"
        ic_dosya_adi = "mevzuat_ham.json"

        if not os.path.exists(zip_dosya_adi):
            st.error(f"{zip_dosya_adi} bulunamadı!")
            return 0

        with st.spinner(
            f"{kisa_ad} dev arşivden çıkarılıp Junilex beynine kazınıyor..."
        ):
            try:
                from sentence_transformers import SentenceTransformer

                collection = cls._get_chroma_collection()
                if collection is None:
                    return 0

                embedding_model = SentenceTransformer(
                    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                )

                with zipfile.ZipFile(zip_dosya_adi, "r") as z:
                    with z.open(ic_dosya_adi) as f:
                        tum_mevzuat = json.loads(f.read().decode("utf-8"))

                hedef_kanun = next(
                    (
                        k
                        for k in tum_mevzuat
                        if str(k.get("kanun_numarasi")) == str(kanun_id)
                    ),
                    None,
                )

                if not hedef_kanun:
                    st.error(f"{kisa_ad} dev arşivde bulunamadı!")
                    return 0

                maddeler = hedef_kanun.get("maddeler", [])
                BATCH_SIZE = 100
                total_maddeler = len(maddeler)

                for i in range(0, total_maddeler, BATCH_SIZE):
                    batch_maddeler = maddeler[i : i + BATCH_SIZE]
                    ids, documents, metadatas, embeddings = [], [], [], []

                    for sira, madde in enumerate(batch_maddeler):
                        gercek_sira = i + sira
                        madde_no_ham = str(madde.get("madde_numarasi", ""))
                        madde_no = (
                            madde_no_ham.replace("MADDE", "")
                            .replace("Madde", "")
                            .strip()
                        )
                        icerik = madde.get("text", "")
                        aranacak_metin = f"{kisa_ad} Madde {madde_no}: {icerik}"

                        ids.append(f"{kisa_ad}_{madde_no}_{gercek_sira}")
                        documents.append(icerik)
                        metadatas.append({"kanun": kisa_ad, "madde": madde_no.upper()})
                        embeddings.append(
                            embedding_model.encode(aranacak_metin).tolist()
                        )

                    collection.add(
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids,
                    )

                st.success(
                    f"BAŞARILI! {total_maddeler} adet {kisa_ad} maddesi Junilex yerel hafızasına alındı."
                )
                return total_maddeler

            except Exception as e:
                st.error(f"Yükleme hatası: {str(e)}")
                return 0

    @classmethod
    def madde_getir_buluttan(cls, *args, **kwargs):
        try:
            kanun_kisa_ad = (
                kwargs.get("kanun_kisa_ad")
                or kwargs.get("kanun_kisa_ad_bul")
                or kwargs.get("kisaAd")
            )
            madde_no_tam = (
                kwargs.get("madde_no_tam")
                or kwargs.get("madde_no")
                or kwargs.get("girilen_madde")
            )
            tum_degerler = list(args) + list(kwargs.values())

            for deger in list(tum_degerler):
                if isinstance(deger, dict):
                    tum_degerler.extend(deger.values())

            bilinen_kisaltmalar = [k["kisaAd"] for k in cls.get_kanunlar()]

            if not kanun_kisa_ad:
                for v in tum_degerler:
                    if str(v).strip() in bilinen_kisaltmalar:
                        kanun_kisa_ad = str(v).strip()
                        break

            if not madde_no_tam:
                for v in tum_degerler:
                    v_str = str(v).strip()
                    if v_str != kanun_kisa_ad and (
                        v_str.isdigit()
                        or "GECİCİ" in v_str.upper()
                        or "EK" in v_str.upper()
                    ):
                        madde_no_tam = v_str
                        break

            if not kanun_kisa_ad or not madde_no_tam:
                return {
                    "no": "BİLİNMEYEN",
                    "baslik": "Hata",
                    "metin": "Eksik parametre gönderildi.",
                }

            collection = cls._get_chroma_collection()
            if collection is None:
                return {
                    "no": "HATA",
                    "baslik": "Veritabanı Hatası",
                    "metin": "Veritabanına bağlanılamadı.",
                }

            istenen_madde_str = str(madde_no_tam).upper().strip()

            # İyileştirme: Doğrudan ChromaDB 'where' filtresi kullanarak performans artırıldı
            sonuclar = collection.get(
                where={
                    "$and": [
                        {"kanun": {"$eq": kanun_kisa_ad}},
                        {"madde": {"$eq": istenen_madde_str}},
                    ]
                }
            )

            # Eğer tam eşleşme bulunamazsa esnek arama yedek mekanizması
            if not sonuclar or not sonuclar["documents"]:
                sonuclar = collection.get(where={"kanun": {"$eq": kanun_kisa_ad}})

            if not sonuclar or not sonuclar["documents"]:
                return {
                    "no": madde_no_tam,
                    "baslik": "Veritabanı Boş",
                    "metin": f"{kanun_kisa_ad} henüz yüklenmemiş.",
                }

            bulunan_metin = None
            for metin, meta in zip(sonuclar["documents"], sonuclar["metadatas"]):
                db_madde_no = str(meta.get("madde", "")).upper()
                if db_madde_no == istenen_madde_str:
                    bulunan_metin = metin
                    break

            if bulunan_metin:
                return {
                    "no": str(madde_no_tam),
                    "baslik": f"{kanun_kisa_ad} - Madde {str(madde_no_tam).replace('_', ' ')}",
                    "metin": bulunan_metin + f"\n\n{YASAL_UYARI}",
                }
            else:
                return {
                    "no": madde_no_tam,
                    "baslik": "Madde Eksik",
                    "metin": f"{kanun_kisa_ad} Madde {str(madde_no_tam).replace('_', ' ')} bulunamadı.",
                }
        except Exception as e:
            return {
                "no": "HATA",
                "baslik": "Bağlantı Hatası",
                "metin": f"Veritabanı Hatası: {e}",
            }

    @classmethod
    def capraz_baglantilari_getir(
        cls, api_key: str, kanun_kisa_ad: str, madde_no: str, madde_metni: str = ""
    ):
        """
        Garantili ve Hızlı Hibrit Çapraz Bağlantı Motoru.
        Hata alsa bile asla boş dönmez.
        """
        baglantilar = []
        metin_alt = madde_metni.lower() if madde_metni else ""

        # ── 1. KATMAN: REGEKS VE METİN İÇİ AÇIK ATIFLAR ──
        atif_kaliplari = [
            (
                r"(?:türk ceza kanunu|tck)\D*?(\d+)",
                "TCK",
                "Doğrudan Atıf Yapılan TCK Hükmü",
            ),
            (
                r"(?:ceza muhakemesi kanunu|cmk)\D*?(\d+)",
                "CMK",
                "Doğrudan Atıf Yapılan CMK Hükmü",
            ),
            (
                r"(?:türk borçlar kanunu|tbk)\D*?(\d+)",
                "TBK",
                "Doğrudan Atıf Yapılan Borçlar Hükmü",
            ),
            (
                r"(?:türk medeni kanunu|tmk)\D*?(\d+)",
                "TMK",
                "Doğrudan Atıf Yapılan Medeni Kanun Hükmü",
            ),
            (
                r"(?:hukuk muhakemeleri kanunu|hmk)\D*?(\d+)",
                "HMK",
                "Doğrudan Atıf Yapılan Yargılama Usulü Hükmü",
            ),
            (
                r"(?:icra ve iflas kanunu|iik)\D*?(\d+)",
                "İİK",
                "Doğrudan Atıf Yapılan İcra Takip Hükmü",
            ),
            (r"(?:iş kanunu)\D*?(\d+)", "İK", "Doğrudan Atıf Yapılan İş Kanunu Hükmü"),
        ]

        for kalip, k_kisa, aciklama in atif_kaliplari:
            bulunanlar = re.findall(kalip, metin_alt)
            for m_no in bulunanlar:
                if str(m_no) != str(madde_no) and not any(
                    b["kanun"] == k_kisa and b["madde"] == str(m_no)
                    for b in baglantilar
                ):
                    baglantilar.append(
                        {"kanun": k_kisa, "madde": str(m_no), "aciklama": aciklama}
                    )

        # ── 2. KATMAN: KAVRAMSAL VE MANTIKSAL ANLAMSAL EŞLEŞTİRME ──
        if "zamanaşımı" in metin_alt or "zaman aşımı" in metin_alt:
            if kanun_kisa_ad in ["TCK", "CMK"]:
                baglantilar.append(
                    {
                        "kanun": "TCK",
                        "madde": "66",
                        "aciklama": "Dava Zamanaşımı Süreleri",
                    }
                )
            elif kanun_kisa_ad in ["TBK", "TMK", "TTK", "İK"]:
                baglantilar.append(
                    {
                        "kanun": "TBK",
                        "madde": "72",
                        "aciklama": "Haksız Fiillerde Zamanaşımı",
                    }
                )

        if (
            "tazminat" in metin_alt
            or "zarar" in metin_alt
            or "haksız fiil" in metin_alt
        ):
            if kanun_kisa_ad != "TBK":
                baglantilar.append(
                    {
                        "kanun": "TBK",
                        "madde": "49",
                        "aciklama": "Sorumluluk ve Tazminat Yükümlülüğü",
                    }
                )

        if "yetki" in metin_alt or "mahkeme" in metin_alt or "dava" in metin_alt:
            if kanun_kisa_ad in ["TBK", "TMK", "TTK", "TKHK", "İK"]:
                if not any(b["kanun"] == "HMK" for b in baglantilar):
                    baglantilar.append(
                        {
                            "kanun": "HMK",
                            "madde": "6",
                            "aciklama": "Genel Yetkili Mahkeme Kuralı",
                        }
                    )
            elif kanun_kisa_ad in ["TCK", "CMK"]:
                if not any(b["kanun"] == "CMK" for b in baglantilar):
                    baglantilar.append(
                        {
                            "kanun": "CMK",
                            "madde": "12",
                            "aciklama": "Davaya Bakmaya Yetkili Mahkeme",
                        }
                    )

        if "ispat" in metin_alt or "delil" in metin_alt:
            if kanun_kisa_ad in ["TBK", "TMK", "TTK"]:
                baglantilar.append(
                    {
                        "kanun": "TMK",
                        "madde": "6",
                        "aciklama": "İspat Yükü Genel Kuralı",
                    }
                )
            elif kanun_kisa_ad in ["TCK", "CMK"]:
                baglantilar.append(
                    {
                        "kanun": "CMK",
                        "madde": "217",
                        "aciklama": "Delilleri Takdir Etme Yetkisi",
                    }
                )

        if "şikayet" in metin_alt or "uzlaşma" in metin_alt:
            if kanun_kisa_ad in ["TCK", "CMK"]:
                baglantilar.append(
                    {
                        "kanun": "CMK",
                        "madde": "253",
                        "aciklama": "Uzlaştırma Kapsamı ve Usulü",
                    }
                )

        # Eğer yukarıdaki 2 katmandan yeterli sonuç çıktıysa doğrudan dön
        if len(baglantilar) >= 2:
            return baglantilar[:4]

        # ── 3. KATMAN: LLM / YAPAY ZEKA DESTEKLİ ANLAMSAL ÇAPRAZ BAĞLANTI ──
        if api_key and madde_metni and len(baglantilar) < 2:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("models/gemini-2.5-flash")
                prompt = f"""
                Sen kıdemli bir Yargıtay Tetkik Hakimisiniz.
                Aşağıdaki mevzuat maddesini incele ve bu maddeyle doğrudan ilişkili (usul, görev, yetki, zamanaşımı veya haksız fiil/suç boyutu olan) diğer Türk Kanunlarındaki EN ALAKALI 2 maddeyi tespit et.

                İncelenen Madde: {kanun_kisa_ad} Madde {madde_no}
                Metin: {madde_metni[:1000]}

                SADECE şu geçerli JSON formatında yanıt ver:
                [
                    {{"kanun": "HMK", "madde": "6", "aciklama": "Genel yetkili mahkeme kuralı"}},
                    {{"kanun": "TBK", "madde": "49", "aciklama": "Haksız fiil sorumluluğu"}}
                ]
                """
                response = model.generate_content(
                    prompt, generation_config={"response_mime_type": "application/json"}
                )

                if response and response.text:
                    ai_baglantilar = json.loads(response.text)
                    for ab in ai_baglantilar:
                        k_adi = str(ab.get("kanun", "")).upper().strip()
                        m_no = str(ab.get("madde", "")).strip()
                        if (
                            k_adi
                            and m_no
                            and not any(
                                b["kanun"] == k_adi and b["madde"] == m_no
                                for b in baglantilar
                            )
                        ):
                            baglantilar.append(
                                {
                                    "kanun": k_adi,
                                    "madde": m_no,
                                    "aciklama": ab.get(
                                        "aciklama", "İlişkili Hukuk Hükmü"
                                    ),
                                }
                            )
            except Exception as e:
                pass

        # Hiçbir şey bulunamazsa varsayılan usul kurallarını ekle (Boş kalmaması için)
        if not baglantilar:
            if kanun_kisa_ad in ["TCK", "CMK"]:
                baglantilar.append(
                    {
                        "kanun": "CMK",
                        "madde": "12",
                        "aciklama": "Yetkili Mahkeme Kuralı",
                    }
                )
            else:
                baglantilar.append(
                    {
                        "kanun": "HMK",
                        "madde": "6",
                        "aciklama": "Genel Yetkili Mahkeme Kuralı",
                    }
                )

        return baglantilar[:4]

    @classmethod
    def mevzuat_raporu_olustur(cls, kanun_kisa_ad: str, madde_no: str, madde_metni: str, analiz_metni: str = "", format_turu: str = "txt"):
        """
        Mevzuat maddesini ve analizini TXT / UDF formatına dönüştürür.
        """
        rapor_icerigi = f"""================================================================================
🏛️ JUNILEX AI - RESMİ MEVZUAT VE HUKUKİ ANALİZ RAPORU
================================================================================
Mevzuat: {kanun_kisa_ad} Madde {madde_no}
Oluşturulma Tarihi: Junilex Dijital Hafızası

[1. MADDE METNİ]
--------------------------------------------------------------------------------
{madde_metni}

"""
        if analiz_metni:
            rapor_icerigi += f"""[2. YARGITAY TETKİK HAKİMİ ANALİZİ VE RİSK DEĞERLENDİRMESİ]
--------------------------------------------------------------------------------
{analiz_metni}

"""

        rapor_icerigi += """================================================================================
⚠️ YASAL UYARI: Bu rapor Junilex AI tarafından bilgi amaçlı üretilmiştir. 
Hukuken bağlayıcı metin için mevzuat.gov.tr adresini esas alınız.
================================================================================"""

        if format_turu == "udf":
            udf_wrapper = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><udf_document><content>{rapor_icerigi}</content></udf_document>"
            return udf_wrapper.encode('utf-8')
        else:
            return rapor_icerigi.encode('utf-8')
