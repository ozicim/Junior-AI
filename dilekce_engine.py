import google.generativeai as genai
from docx import Document
import io

class DilekceEngine:
    _model = None
    _configured_key = None

    # 20 Dilekçe Tipi Katalogu
    DILEKCE_KATALOGU = {
        "Aile Hukuku": {
            "Anlaşmalı Boşanma": ["Evlilik Tarihi", "Çocuk Sayısı", "Anlaşma Detayları"],
            "Çekişmeli Boşanma": ["Boşanma Sebebi", "Kusur İddiaları", "Tazminat Talebi"],
            "Nafaka Artırım": ["Mevcut Nafaka", "Gelir Değişimi", "Gerekçe"],
            "Velayet Davası": ["Çocuk Bilgisi", "Velayet Gerekçesi", "Yaşam Koşulları"],
            "İştirak Nafakası": ["Çocuk Giderleri", "Gelir Durumu"]
        },
        "Ceza Hukuku": {
            "Hakaret Şikayeti": ["Şüpheli", "Olay Tarihi", "Hakaret İçeriği"],
            "Tehdit Şikayeti": ["Tehdit Şekli", "Olayın Gelişimi", "Tanıklar"],
            "Basit Yaralama Şikayeti": ["Darp Raporu Detayı", "Olay Yeri", "Fail"],
            "Suç Duyurusu (Genel)": ["Suç Türü", "Olay Özeti", "Deliller"],
            "Şikayetten Vazgeçme": ["Soruşturma/Dosya No", "Vazgeçme Gerekçesi"]
        },
        "İcra ve Borçlar": {
            "İcra Takibine İtiraz": ["Takip Dosya No", "İtiraz Gerekçesi", "Borç Miktarı"],
            "Kira Tahliye İhtarnamesi": ["Kira Sözleşme Tarihi", "Tahliye Nedeni", "Süre"],
            "Alacak İhtarnamesi": ["Alacak Miktarı", "Borç Nedeni", "Ödeme Tarihi"],
            "İşçi İstifa Dilekçesi": ["İşe Giriş Tarihi", "İstifa Nedeni", "İhbar Süresi"],
            "Ödeme Emrine İtiraz": ["Dosya No", "İtiraz Nedeni"]
        },
        "İdari ve Diğer": {
            "İdari Başvuru": ["Kurum Adı", "Talep Konusu", "Dayanak"],
            "Dava Cevap Dilekçesi": ["Dosya No", "Cevap Gerekçeleri", "Red Talebi"],
            "Tanık Listesi": ["Dosya No", "Tanık İsimleri", "Tanıklık Konusu"],
            "İhtiyati Tedbir Talebi": ["Dava Konusu", "Tedbir Nedeni", "Aciliyet"],
            "Duruşma Günü Talebi": ["Dosya No", "Gerekçe"]
        }
    }

    @classmethod
    def _modeli_hazirla(cls, api_key):
        if cls._configured_key != api_key:
            genai.configure(api_key=api_key)
            cls._configured_key = api_key
            cls._model = None
        if cls._model is None:
            cls._model = genai.GenerativeModel('models/gemini-2.0-flash')
        return cls._model

    @classmethod
    def dilekce_uret(cls, api_key, tur, veriler): # 3 argüman olacak şekilde güncelledik
        model = cls._modeli_hazirla(api_key)
        
        # 'veriler' sözlüğünü metne çeviriyoruz
        veri_metni = "\n".join([f"{k}: {v}" for k, v in veriler.items()])
        
        prompt = f"""
        Sen profesyonel bir avukatsın. {tur} türünde, hukuki terminolojiye uygun resmi bir dilekçe hazırla.
        
        Verilen Bilgiler:
        {veri_metni}
        
        Kurallar:
        1. Başlığı ve ilgili makamı doğru yaz.
        2. Açıklamalar ve Hukuki Nedenler bölümlerini ekle.
        3. Hukuki Risk Kontrolü bölümü ekle.
        """
        response = model.generate_content(prompt)
        return response.text

    @classmethod
    def word_dosyasi_yap(cls, metin):
        doc = Document()
        for line in metin.split('\n'):
            doc.add_paragraph(line)
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue()
