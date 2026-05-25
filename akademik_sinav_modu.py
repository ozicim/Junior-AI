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
            # Model ismini güncel ve stabil olanla sabitledim
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            kaynak_bilgi = ""

            # ==================================================
            # 1. KAYNAK BELİRLEME (Kullanıcı Notu mu, AI Arşivi mi?)
            # ==================================================
            if ders_notu_metni and str(ders_notu_metni).strip():
                # KULLANICI KENDİ NOTUNU YÜKLEDİYSE
                kaynak_bilgi = f"Öğrencinin Yüklediği Özel Ders Notu:\n{ders_notu_metni}"
            else:
                # AI KÜTÜPHANESİ SEÇİLDİYSE (FAISS VEKTÖR ARAMASI YAP)
                try:
                    if not os.path.exists("faiss_index") and os.path.exists("faiss_index.zip"):
                        with zipfile.ZipFile("faiss_index.zip", 'r') as zip_ref:
                            zip_ref.extractall("faiss_index")
                            
                    if os.path.exists("faiss_index"):
                        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                        vector_store = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
                        
                        # AI Arşivinden bu derse ait en iyi 4 paragrafı (kuralı) çek
                        arama_metni = f"Ders: {konu_adi}. Sınav için pratik çalışma, olay kurgusu ve hukuki analiz kuralları."
                        eslesmeler = vector_store.similarity_search(arama_metni, k=4)
                        fihrist_notlari = "\n\n".join([doc.page_content for doc in eslesmeler])
                        
                        kaynak_bilgi = f"Junilex AI Akademik Arşivi (Sadece Bu Kuralları Baz Al):\n{fihrist_notlari}"
                    else:
                        kaynak_bilgi = "Spesifik arşiv dosyası bulunamadı. Lütfen sadece genel hukuk kurallarına göre hazırla."
                except Exception as faiss_err:
                    kaynak_bilgi = "Genel hukuk öğretisi (Arşiv okuma atlandı)."

            # ==================================================
            # 2. YAPAY ZEKA PROMPT'U (SINAV ŞABLONU)
            # ==================================================
            prompt = f"""
            SEN KIDEMLİ BİR HUKUK PROFESÖRÜSÜN.
            {konu_adi} üzerine bir pratik çalışma (sınav) hazırla.
            
            KULLANACAĞIN BİLGİ KAYNAĞI:
            {kaynak_bilgi}
            
            GÖREVİN:
            - Yukarıdaki "Bilgi Kaynağı" metnine sadık kalarak bir hukuki olay kurgusu (vaka) oluştur.
            - Bu olayla ilgili zorlayıcı ve akademik seviyede çoktan seçmeli 3 soru hazırla.
            - Her sorunun doğru cevabını ve kaynağa dayalı detaylı hukuki analizini (neden diğer şıkların yanlış olduğunu) ekle.
            
            ZORUNLU FORMAT (Sadece ham JSON döndür, kod bloğu işareti kullanma, başka açıklama yazma):
