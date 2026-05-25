import google.generativeai as genai
import json
import re
import os
import zipfile
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

class AkademikSinavEngine:
    @classmethod
    def pratik_calisma_uret(cls, api_key, konu_adi, ders_notu_metni=""):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            kaynak_bilgi = ""

            if ders_notu_metni and str(ders_notu_metni).strip():
                kaynak_bilgi = f"Öğrencinin Yüklediği Özel Ders Notu:\n{ders_notu_metni}"
            else:
                try:
                    if not os.path.exists("faiss_index") and os.path.exists("faiss_index.zip"):
                        with zipfile.ZipFile("faiss_index.zip", 'r') as zip_ref:
                            zip_ref.extractall("faiss_index")
                            
                    if os.path.exists("faiss_index"):
                        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                        vector_store = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
                        
                        arama_metni = f"Ders: {konu_adi}. Sınav için pratik çalışma ve kurallar."
                        eslesmeler = vector_store.similarity_search(arama_metni, k=4)
                        fihrist_notlari = "\n\n".join([doc.page_content for doc in eslesmeler])
                        
                        kaynak_bilgi = f"Junilex AI Arşivi:\n{fihrist_notlari}"
                    else:
                        kaynak_bilgi = "Sadece genel hukuk kurallarına göre hazırla."
                except Exception as faiss_err:
                    kaynak_bilgi = "Genel hukuk öğretisi."

            prompt = f"""
            SEN KIDEMLİ BİR HUKUK PROFESÖRÜSÜN.
            {konu_adi} üzerine bir pratik çalışma (sınav) hazırla.
            
            KULLANACAĞIN BİLGİ KAYNAĞI:
            {kaynak_bilgi}
            
            GÖREVİN:
            - Yukarıdaki kaynağa sadık kalarak bir hukuki olay kurgusu (vaka) oluştur.
            - Bu olayla ilgili çoktan seçmeli 3 soru hazırla.
            - Her sorunun doğru cevabını ve detaylı hukuki analizini ekle.
            
            ZORUNLU FORMAT:
            {{
                "olay_kurgusu": "olay metni...",
                "sorular": [
                    {{
                        "soru": "soru metni...",
                        "secenekler": ["A şıkkı", "B şıkkı", "C şıkkı", "D şıkkı"],
                        "cevap": "Doğru şıkkın tam metni",
                        "analiz": "Hukuki gerekçe ve analiz..."
                    }}
                ]
            }}
            """
            
            response = model.generate_content(prompt)
            if not response or not response.text:
                return {"hata": "AI boş cevap döndürdü."}
                
            ham_yanit = response.text
            
            temiz_metin = re.sub(r'```json|```', '', ham_yanit).strip()
            temiz_metin = re.sub(r"[\x00-\x1F\x7F]", "", temiz_metin)
            
            try:
                sinav_verisi = json.loads(temiz_metin, strict=False)
                if "olay_kurgusu" not in sinav_verisi:
                    return {"hata": "AI uygun formatta sınav üretemedi."}
                return sinav_verisi
                
            except json.JSONDecodeError:
                return {"hata": "JSON Ayrıştırma Hatası."}

        except Exception as e:
            return {"hata": f"Sistem Hatası: {str(e)}"}
