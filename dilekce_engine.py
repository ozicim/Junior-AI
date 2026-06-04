import google.generativeai as genai
from docx import Document
import io

class DilekceEngine:
    _model = None
    _configured_key = None

    # 20 Dilekçe Tipi Katalogu
    DILEKCE_KATALOGU = {
        "Aile Hukuku": {
            "Anlaşmalı Boşanma": ["Evlilik Tarihi", "Çocuk Sayısı", "Anlaşma Detayları (Nafaka, Velayet, Mal Rejimi)"],
            "Çekişmeli Boşanma": ["Boşanma Sebebi", "Kusur İddiaları", "Maddi/Manevi Tazminat Talebi"],
            "Nafaka Artırım": ["Mevcut Nafaka Miktarı", "Gelir Değişimi/Ekonomik Kriz Etkisi", "Gerekçe"],
            "Velayet Davası": ["Çocuk Bilgisi (Yaş/Cinsiyet)", "Velayet Değişikliği Gerekçesi", "Mevcut Yaşam Koşulları"],
            "İştirak Nafakası": ["Çocuğun Aylık Giderleri", "Tarafların Gelir Durumu"]
        },
        "Ceza Hukuku": {
            "Hakaret Şikayeti": ["Şüpheli (Biliniyorsa)", "Olay Tarihi ve Saati", "Hakaret İçeriği (Tam Kelimeler)"],
            "Tehdit Şikayeti": ["Tehdit Şekli (Sözlü/Silahlı vb.)", "Olayın Gelişimi", "Varsa Tanıklar"],
            "Basit Yaralama Şikayeti": ["Darp Raporu Tarihi/Detayı", "Olay Yeri", "Fail"],
            "Suç Duyurusu (Genel)": ["Suç Türü", "Olay Özeti", "Mevcut Deliller"],
            "Şikayetten Vazgeçme": ["Soruşturma/Mahkeme Dosya No", "Vazgeçme Gerekçesi"]
        },
        "İcra ve Borçlar": {
            "İcra Takibine İtiraz": ["Takip Dosya No ve İcra Dairesi", "İtiraz Gerekçesi (Borca/Yetkiye)", "Talep Edilen Borç Miktarı"],
            "Kira Tahliye İhtarnamesi": ["Kira Sözleşme Tarihi", "Tahliye Nedeni (İhtiyaç/Temerrüt)", "Verilen Süre"],
            "Alacak İhtarnamesi": ["Alacak Miktarı", "Borç Nedeni", "Ödeme İçin Verilen Tarih/Süre"],
            "İşçi İstifa Dilekçesi": ["İşe Giriş Tarihi", "İstifa Nedeni (Haklı Fesih mi?)", "İhbar Süresi"],
            "Ödeme Emrine İtiraz": ["İcra Dosya No", "İtiraz Nedeni"]
        },
        "İdari ve Diğer": {
            "İdari Başvuru": ["Başvuru Yapılacak Kurum Adı", "Talep Konusu", "Hukuki Dayanak"],
            "Dava Cevap Dilekçesi": ["Mahkeme ve Dosya No", "Davaya Cevap Gerekçeleri", "Red Talebi"],
            "Tanık Listesi": ["Mahkeme ve Dosya No", "Tanık İsimleri ve TC'leri", "Hangi Konuda Tanıklık Yapacakları"],
            "İhtiyati Tedbir Talebi": ["Dava Konusu", "Tedbir İstenen Malvarlığı/Durum", "Gecikmesinde Sakınca Bulunan Hal (Aciliyet)"],
            "Duruşma Günü Talebi": ["Mahkeme ve Dosya No", "Öne Çekme Gerekçesi"]
        }
    }

    @classmethod
    def _modeli_hazirla(cls, api_key):
        if cls._configured_key != api_key:
            genai.configure(api_key=api_key)
            cls._configured_key = api_key
            cls._model = None
        if cls._model is None:
            # flash modeli hızlı ve metin üretimi için idealdir
            cls._model = genai.GenerativeModel('models/gemini-2.5-flash')
        return cls._model

    @classmethod
    def dilekce_uret(cls, api_key, tur, veriler): 
        model = cls._modeli_hazirla(api_key)
        
        veri_metni = "\n".join([f"- **{k}:** {v}" for k, v in veriler.items()])
        
        # HMK/CMK Usullerine Göre Katı Prompt Mimarisi
        prompt = f"""
        Sen Türkiye'de görev yapan kıdemli ve titiz bir avukatsın. Aşağıda formdan gelen kısıtlı bilgileri kullanarak UYAP formatına ve Türk Hukuk Usulüne (HMK Madde 119 veya CMK) tam uyumlu, resmi bir "{tur}" taslağı hazırlamanı istiyorum.

        Müvekkilden/Kullanıcıdan Gelen Bilgiler:
        {veri_metni}

        KESİN KURALLAR:
        1. Dilekçeyi bir taslak olarak düşün. Kullanıcının doldurmadığı kimlik, adres, TCKN gibi alanları köşeli parantez içinde boş bırak (Örn: [DAVACININ ADI SOYADI VE TCKN]).
        2. Dilekçenin Kurgusu (Format) Şöyle Olmalıdır:
           - İLGİLİ MAHKEME VEYA MAKAMA (Örn: ANKARA NÖBETÇİ AİLE MAHKEMESİNE)
           - DAVACI / ŞİKAYETÇİ: [Boşluk]
           - VEKİLİ: [Boşluk]
           - DAVALI / ŞÜPHELİ: [Boşluk]
           - KONU: (Dilekçenin türüne uygun hukuki konu özetlenmeli)
           - AÇIKLAMALAR: (Formdan gelen verileri burada mantıklı bir hukuki kurguya ve kronolojiye oturt. Gerekirse hayatın olağan akışına uygun detaylarla profesyonelce zenginleştir).
           - HUKUKİ NEDENLER: (Bu dava/talep türü için geçerli olan HMK, TMK, TCK vb. kanun maddelerini mutlaka yaz).
           - HUKUKİ DELİLLER: (Tanık, bilirkişi, yemin, dekont vb. standart delilleri listele).
           - SONUÇ VE İSTEM: (Net, şüpheye yer bırakmayan hukuki talep).
        
        3. RİSK VE USUL DENETİMİ: Dilekçe metni bittikten sonra en alta "--- ⚠️ JUNILEX USUL VE RİSK DENETİMİ ---" adında bir başlık aç. Burada, formdan gelen bilgilere bakarak eksik gördüğün hukuki detayları avukata uyar. (Örn: "Anlaşmalı boşanma dilekçesi hazırlanmıştır ancak tarafların mal paylaşımına dair protokol eklenmesi unutulmamalıdır" gibi).
        """
        response = model.generate_content(prompt)
        return response.text

    @classmethod
    def word_dosyasi_yap(cls, metin):
        doc = Document()
        
        # Word dosyasını şekillendirme (Başlıklar ve formatlama için)
        for line in metin.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Kalın başlıkları algıla ve Word'de kalın yap
            if line.startswith("**") and line.endswith("**"):
                p = doc.add_paragraph()
                p.add_run(line.replace("**", "")).bold = True
            # HMK Başlıklarını ortala ve kalın yap (Örn: AÇIKLAMALAR:)
            elif line.isupper() and len(line) > 3 and not line.startswith("-"):
                p = doc.add_paragraph()
                run = p.add_run(line)
                run.bold = True
            else:
                doc.add_paragraph(line)
                
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue()
