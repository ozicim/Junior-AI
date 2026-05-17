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
    def _modeli_hazirla(cls, api_key):
        if cls._model is None:
            genai.configure(api_key=api_key)
            cls._model = genai.GenerativeModel('models/gemini-2.5-flash')
        return cls._model

    @classmethod
    def madde_getir(cls, kanun_kisa_ad: str, madde_no_tam: str):
        try:
            chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
            collection = chroma_client.get_collection(name="turk_mevzuati")
            
            # --- AKILLI FİLTRELEME: Arayüzden gelen ID'yi çözümleme ---
            # Kullanıcı arayüzünden "1", "GECİCİ_1" veya "EK_1" formatında veri gelir
            istenen_tur = "normal"
            istenen_sayi = str(madde_no_tam).upper()
            
            if istenen_sayi.startswith("GECİCİ_") or istenen_sayi.startswith("GEÇİCİ_"):
                istenen_tur = "gecici"
                istenen_sayi = istenen_sayi.split("_")[1]
            elif istenen_sayi.startswith("EK_"):
                istenen_tur = "ek"
                istenen_sayi = istenen_sayi.split("_")[1]

            # O kanunun tüm maddelerini yerel hafızadan getir (0.01 sn sürer)
            sonuclar = collection.get(where={"kanun": {"$eq": kanun_kisa_ad}})
            
            if not sonuclar or not sonuclar['documents']:
                st.warning(f"⚠️ {kanun_kisa_ad} yerel veritabanında bulunamadı.")
                return None
                
            bulunan_metin = None
            
            for metin, meta in zip(sonuclar['documents'], sonuclar['metadatas']):
                db_madde_no = str(meta.get("madde", "")).upper()
                metin_baslik = metin[:100].upper() # Metnin sadece başını kontrol ediyoruz
                
                # Veritabanındaki numaradan sadece rakamı al (JSON "Geçici 1" olarak kaydetmiş olabilir)
                rakam_eslesmesi = re.findall(r'\d+', db_madde_no)
                db_rakam = rakam_eslesmesi[0] if rakam_eslesmesi else db_madde_no
                
                # Sadece numaralar eşleşiyorsa tür analizi yap
                if db_rakam == istenen_sayi:
                    if istenen_tur == "normal":
                        # Normal isteniyorsa, içinde GEÇİCİ veya EK kelimeleri KESİNLİKLE geçmemeli
                        if "GEÇİCİ" not in db_madde_no and "GEÇİCİ" not in metin_baslik and "EK MADDE" not in metin_baslik:
                            bulunan_metin = metin
                            break
                            
                    elif istenen_tur == "gecici":
                        # Geçici isteniyorsa, metnin başında veya numarasında mutlaka GEÇİCİ yazmalı
                        if "GEÇİCİ" in db_madde_no or "GECİCİ" in db_madde_no or "GEÇİCİ" in metin_baslik:
                            bulunan_metin = metin
                            break
                            
                    elif istenen_tur == "ek":
                        # Ek Madde isteniyorsa EK yazmalı
                        if "EK" in db_madde_no or "EK MADDE" in metin_baslik:
                            bulunan_metin = metin
                            break

            # Katı filtre bulamazsa (çok bozuk bir JSON ise) direkt eşleşmeye dön (Fallback)
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
                st.warning(f"⚠️ {kanun_kisa_ad} Madde {str(madde_no_tam).replace('_', ' ')} bulunamadı. JSON dosyanızda bu madde eksik olabilir.")
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
