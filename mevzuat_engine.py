import streamlit as st
import chromadb
import google.generativeai as genai

YASAL_UYARI = (
    "⚠️ **Bilgi Amaçlıdır:** Bu madde metni Junilex yerel veritabanından getirilmiştir. "
    "Güncel ve hukuken bağlayıcı metin için mevzuat.gov.tr adresini kontrol ediniz."
)

class MevzuatBulutEngine:
    _model = None

    @classmethod
    def _modeli_hazirla(cls, api_key):
        """Modeli ilk kullanımda oluşturur, sonraki çağrılarda tekrar yüklemez."""
        if cls._model is None:
            genai.configure(api_key=api_key)
            # Hukuki analiz için hızlı ve stabil olan flash modelini kullanıyoruz
            cls._model = genai.GenerativeModel('models/gemini-2.5-flash')
        return cls._model

    @classmethod
    def madde_getir(cls, kanun_kisa_ad: str, madde_no_tam: str):
        """
        Firebase/Selenium yerine ChromaDB yerel vektör tabanını kullanır.
        Bulunan madde metnini hem ekrana basar hem de AI analizi için döndürür.
        """
        try:
            chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
            collection = chroma_client.get_collection(name="turk_mevzuati")
            
            # Tam eşleşme araması
            sonuclar = collection.get(
                where={"$and": [
                    {"kanun": {"$eq": kanun_kisa_ad}},
                    {"madde": {"$eq": str(madde_no_tam)}}
                ]}
            )
            
            if sonuclar and sonuclar['documents'] and len(sonuclar['documents']) > 0:
                metin = sonuclar['documents'][0]
                
                # Streamlit arayüzünde gösterme
                st.success("✅ Madde yerel veritabanından getirildi!")
                st.markdown(f"### {kanun_kisa_ad} - Madde {madde_no_tam}")
                st.info(metin)
                st.caption(YASAL_UYARI)
                
                # AI analizinde kullanılması için metni döndürüyoruz
                return metin 
            else:
                st.warning(f"⚠️ {kanun_kisa_ad} Madde {madde_no_tam} yerel veritabanında bulunamadı. Lütfen 'yerel_yukleyici.py' ile veritabanınızı güncelleyin.")
                return None
                
        except Exception as e:
            st.error(f"❌ Yerel veritabanı bağlantı hatası: {e}\n(ChromaDB klasörünün oluşturulduğundan emin olun)")
            return None

    @classmethod
    def madde_analiz_et(cls, api_key, kanun_kisa_ad, madde_no_tam, madde_metni):
        """
        Yerel veritabanından getirilen kesin metin üzerinden AI'a hukuki yorum yaptırır.
        """
        try:
            model = cls._modeli_hazirla(api_key)
            
            prompt = f"""
            Sen kıdemli bir Yargıtay Tetkik Hakimisin. Aşağıda sana verilen kanun maddesini, 
            meslektaşların (avukatlar ve hakimler) için yapısal bir şekilde analiz et.
            
            İncelenecek Mevzuat: {kanun_kisa_ad} Madde {madde_no_tam}
            Kanun Metni: {madde_metni}
            
            Lütfen analizini SADECE şu başlıklar altında yap:
            - **🎯 Maddenin Amacı ve Korunan Hukuki Yarar:**
            - **⚖️ Kritik Unsurlar ve Şartlar:**
            - **🏛️ Uygulama ve Yargıtay Eğilimi (Muhtemel Riskler):**
            
            DİKKAT: Analizini tamamen sana verdiğim kanun metnine dayandır. Başka bir madde uydurma.
            """
            
            # Streamlit üzerinde akıcı (stream) bir şekilde yazılması için
            response = model.generate_content(prompt, stream=True)
            return response
            
        except Exception as e:
            st.error(f"❌ AI Analiz Hatası: {str(e)}")
            return None
