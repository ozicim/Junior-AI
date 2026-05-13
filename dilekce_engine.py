import google.generativeai as genai
from docx import Document
import io

class DilekceEngine:
    @classmethod
    def dilekce_olustur(cls, api_key, konu, taraflar, olay_ozeti, talepler):
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        
        prompt = f"""
        Sen profesyonel bir avukatsın. Aşağıdaki bilgilere dayanarak resmi, ağırbaşlı ve 
        hukuki terminolojiye uygun bir dilekçe taslağı hazırla.
        
        Dilekçe Konusu: {konu}
        Taraflar (Davacı/Davalı/Müşteki vb.): {taraflar}
        Olay Özeti: {olay_ozeti}
        Netice-i Talep: {talepler}
        
        Kurallar:
        1. Dilekçe başlığını (İlgili Makama) uygun şekilde yaz.
        2. 'Açıklamalar' ve 'Hukuki Deliller' kısımlarını ekle.
        3. Türk hukuk sistemine uygun terminoloji kullan (Örn: 'müvekkil', 'haksız fiil', 'mesnetsiz').
        4. Sadece dilekçe metnini döndür.
        """
        response = model.generate_content(prompt, stream=True)
        return response # Yanıtı bir bütün olarak değil, akış (generator) olarak döndürüyoruz
        
        response = model.generate_content(prompt)
        return response.text
        # stream=True ekledik:
        

    @classmethod
    def word_dosyasi_yap(cls, metin):
        # Yazılan metni Word dosyasına çevirir
        doc = Document()
        for line in metin.split('\n'):
            doc.add_paragraph(line)
        
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue()
