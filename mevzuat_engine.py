import streamlit as st
import chromadb
import google.generativeai as genai
import re

YASAL_UYARI = (
    "⚠️ **Bilgi Amaçlıdır:** Bu madde metni Junilex yerel veritabanından getirilmiştir. "
    "Güncel ve hukuken bağlayıcı metin için mevzuat.gov.tr adresini kontrol ediniz."
)




class MevzuatBulutEngine:
    _model = None

    @classmethod
    def get_kanunlar(cls):
        """
        app.py içerisindeki selectbox ve arayüz elemanlarının 
        beklediği Sözlük formatında ve eksiksiz kanun listesini döner.
        """
        return [
            {"id": "5237", "kisaAd": "TCK", "isim": "Türk Ceza Kanunu", "kategori": "Ceza Hukuku", "aciklama": "Temel Ceza Mevzuatı"},
            {"id": "5271", "kisaAd": "CMK", "isim": "Ceza Muhakemesi Kanunu", "kategori": "Ceza Hukuku", "aciklama": "Yargılama Usulleri"},
            {"id": "4721", "kisaAd": "TMK", "isim": "Türk Medeni Kanunu", "kategori": "Özel Hukuk", "aciklama": "Temel Medeni Haklar"},
            {"id": "6098", "kisaAd": "TBK", "isim": "Türk Borçlar Kanunu", "kategori": "Özel Hukuk", "aciklama": "Borç İlişkileri ve Sözleşmeler"},
            {"id": "6102", "kisaAd": "TTK", "isim": "Türk Ticaret Kanunu", "kategori": "Ticaret Hukuku", "aciklama": "Ticari İşletme ve Şirketler"},
            {"id": "4857", "kisaAd": "İK", "isim": "İş Kanunu", "kategori": "İş Hukuku", "aciklama": "İşçi ve İşveren İlişkileri"}
        ]

    @classmethod
    def _modeli_hazirla(cls, api_key):
        if cls._model is None:
            genai.configure(api_key=api_key)
            cls._model = genai.GenerativeModel('models/gemini-2.5-flash')
        return cls._model

    @classmethod
    def madde_getir_buluttan(cls, kanun_kisa_ad: str, madde_no_tam: str):
        try:
            chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
            collection = chroma_client.get_collection(name="turk_mevzuati")
            
            # --- AKILLI FİLTRELEME: Arayüzden gelen ID'yi çözümleme ---
            istenen_tur = "normal"
            istenen_sayi = str(madde_no_tam).upper()
            
            if istenen_sayi.startswith("GECİCİ_") or istenen_sayi.startswith("GEÇİCİ_"):
                istenen_tur = "gecici"
                istenen_sayi = istenen_sayi.split("_")[1]
            elif istenen_sayi.startswith("EK_"):
                istenen_tur = "ek"
                istenen_sayi = istenen_sayi.split("_")[1]

            # O kanunun tüm maddelerini yerel hafızadan getir
            sonuclar = collection.get(where={"kanun": {"$eq": kanun_kisa_ad}})
            
            if not sonuclar or not sonuclar['documents']:
                st.warning(f"⚠️ {kanun_kisa_ad} yerel veritabanında bulunamadı.")
                return None
                
            bulunan_metin = None
            
            for metin, meta in zip(sonuclar['documents'], sonuclar['metadatas']):
                db_madde_no = str(meta.get("madde", "")).upper()
                metin_baslik = metin[:100].upper()
                
                rakam_eslesmesi = re.findall(r'\d+', db_madde_no)
                db_rakam = rakam_eslesmesi[0] if rakam_eslesmesi else db_madde_no
                
                if db_rakam == istenen_sayi:
                    if istenen_tur == "normal":
                        if "GEÇİCİ" not in db_madde_no and "GEÇİCİ" not in metin_baslik and "EK MADDE" not in metin_baslik:
                            bulunan_metin = metin
                            break
                    elif istenen_tur == "gecici":
                        if "GEÇİCİ" in db_madde_no or "GECİCİ" in db_madde_no or "GEÇİCİ" in metin_baslik:
                            bulunan_metin = metin
                            break
                    elif istenen_tur == "ek":
                        if "EK" in db_madde_no or "EK MADDE" in metin_baslik:
                            bulunan_metin = metin
                            break

            # Fallback mantığı
            if not bulunan_metin:
                for metin, meta in zip(sonuclar['documents'], sonuclar['metadatas']):
                    if str(meta.get("madde", "")) == str(madde_no_tam):
                        bulunan_metin = metin
                        break

            if bulunan_metin:
                st.success("✅ Madde yerel veritabanından akıllı filtre ile getirildi!")
                st.markdown(f"### {kanun_kisa_ad} - Madde {str(madde_no_tam).replace('_', ' ')}")
                st.info(bulunan_metin)
                st.caption(YASAL_UYARI)
                return bulunan_metin
            else:
                st.warning(f"⚠️ {kanun_kisa_ad} Madde {str(madde_no_tam).replace('_', ' ')} bulunamadı. Lütfen yerel veritabanınızı kontrol edin.")
                return None
                
        except Exception as e:
            st.error(f"❌ Yerel veritabanı bağlantı hatası: {e}")
            return None

    @classmethod
    def madde_analiz_et(cls, api_key, kanun_kisa_ad, madde_no_tam, madde_metni):
        try:
            model = cls._modeli_hazirla(api_key)
            prompt = f"""
            Sen kıdemli bir Yargıtay Tetkik Hakimisin. Aşağıda sana verilen kanun maddesini, 
            meslektaşların (avukatlar ve hakimler) için yapısal bir şekilde analiz et.
            
            İncelenecek Mevzuat: {kanun_kisa_ad} Madde {str(madde_no_tam).replace('_', ' ')}
            Kanun Metni: {madde_metni}
            
            Lütfen analizini SADECE şu başlıklar altında yap:
            - **🎯 Maddenin Amacı ve Korunan Hukuki Yarar:**
            - **⚖️ Kritik Unsurlar ve Şartlar:**
            - **🏛️ Uygulama ve Yargıtay Eğilimi (Muhtemel Riskler):**
            
            DİKKAT: Analizini tamamen sana verdiğim kanun metnine dayandır. Başka bir madde uydurma.
            """
            response = model.generate_content(prompt, stream=True)
            return response
        except Exception as e:
            st.error(f"❌ AI Analiz Hatası: {str(e)}")
            return None
