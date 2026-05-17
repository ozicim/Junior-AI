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
    def kanunu_buluta_yukle(cls, *args, **kwargs):
        """
        app.py içindeki Yükleme Panelinin çökmesini engeller.
        Eski Selenium yapısını devreden çıkardığımız için sadece uyarı verir.
        """
        st.error("⚠️ **Sistem Uyarı:** Canlı web kazıma devredışı bırakılmıştır! Kanunları sisteme eklemek için lütfen terminalden `python yerel_yukleyici.py` komutunu çalıştırın.")
        return 0

    @classmethod
    def madde_getir_buluttan(cls, kanun_kisa_ad: str, madde_no_tam: str):
        """
        app.py'nin çökmemesi için string yerine DİCT (Sözlük) döndürür.
        """
        try:
            chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
            collection = chroma_client.get_collection(name="turk_mevzuati")
            
            istenen_tur = "normal"
            istenen_sayi = str(madde_no_tam).upper()
            
            if istenen_sayi.startswith("GECİCİ_") or istenen_sayi.startswith("GEÇİCİ_"):
                istenen_tur = "gecici"
                istenen_sayi = istenen_sayi.split("_")[1]
            elif istenen_sayi.startswith("EK_"):
                istenen_tur = "ek"
                istenen_sayi = istenen_sayi.split("_")[1]

            sonuclar = collection.get(where={"kanun": {"$eq": kanun_kisa_ad}})
            
            if not sonuclar or not sonuclar['documents']:
                # Sözlük olarak döndürüyoruz ki app.py .get("metin") yaparken patlamasın
                return {"no": madde_no_tam, "baslik": "Veritabanı Boş", "metin": f"⚠️ {kanun_kisa_ad} henüz Junilex'in yerel beynine yüklenmemiş. Lütfen terminalden JSON dosyasını yükleyin."}
                
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

            if not bulunan_metin:
                for metin, meta in zip(sonuclar['documents'], sonuclar['metadatas']):
                    if str(meta.get("madde", "")) == str(madde_no_tam):
                        bulunan_metin = metin
                        break

            if bulunan_metin:
                # Başarılı sonuç da sözlük formatında dönüyor
                return {
                    "no": str(madde_no_tam),
                    "baslik": f"{kanun_kisa_ad} - Madde {str(madde_no_tam).replace('_', ' ')}",
                    "metin": bulunan_metin + f"\n\n{YASAL_UYARI}"
                }
            else:
                return {"no": madde_no_tam, "baslik": "Madde Eksik", "metin": f"⚠️ {kanun_kisa_ad} Madde {str(madde_no_tam).replace('_', ' ')} veritabanında (JSON) eksik."}
                
        except Exception as e:
            return {"no": "HATA", "baslik": "Sistem Hatası", "metin": f"❌ Yerel veritabanı bağlantı hatası: {e}"}

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
