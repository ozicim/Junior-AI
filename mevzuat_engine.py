import re
import time
import streamlit as st
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import google.generativeai as genai

class MevzuatBulutEngine:
    BASE_URL = "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={}&MevzuatTur=1&MevzuatTertip=5"
    db = None

    KANUNLAR = [
        {"id": "5237", "isim": "Türk Ceza Kanunu", "kisaAd": "TCK", "kategori": "Ceza Hukuku", "aciklama": "Suç ve ceza kavramlarını düzenleyen temel kanun."},
        {"id": "5271", "isim": "Ceza Muhakemesi Kanunu", "kisaAd": "CMK", "kategori": "Ceza Hukuku", "aciklama": "Ceza yargılaması usullerini düzenler."},
        {"id": "4721", "isim": "Türk Medeni Kanunu", "kisaAd": "TMK", "kategori": "Özel Hukuk", "aciklama": "Kişiler, aile, miras ve eşya hukukunu kapsar."},
        {"id": "6098", "isim": "Türk Borçlar Kanunu", "kisaAd": "TBK", "kategori": "Özel Hukuk", "aciklama": "Borç ilişkilerini ve sözleşmeleri kapsar."},
        {"id": "6102", "isim": "Türk Ticaret Kanunu", "kisaAd": "TTK", "kategori": "Ticaret Hukuku", "aciklama": "Ticari işletme, şirketler ve kıymetli evrak hukuku."},
        {"id": "4857", "isim": "İş Kanunu", "kisaAd": "İK", "kategori": "İş Hukuku", "aciklama": "İşçi ve işveren ilişkilerini düzenler."}
    ]

    @classmethod
    def get_kanunlar(cls):
        return cls.KANUNLAR

    @classmethod
    def veritabanini_baslat(cls):
        if not firebase_admin._apps:
            # Secrets içindeki 'firebase' başlığını bir sözlük olarak alıyoruz
            firebase_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_dict)
            firebase_admin.initialize_app(cred)
        if not cls.db:
            cls.db = firestore.client()

    @classmethod
    def madde_getir_buluttan(cls, kanun_kisa_adi, madde_no):
        cls.veritabanini_baslat()
        doc_ref = cls.db.collection('kanunlar').document(kanun_kisa_adi).collection('maddeler').document(str(madde_no))
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            raise ValueError(f"'{kanun_kisa_adi}' içerisinde Madde {madde_no} bulunamadı.")

    @classmethod
    def kelime_ile_ara(cls, kanun_kisa_adi, arama_terimi):
        cls.veritabanini_baslat()
        arama_terimi = arama_terimi.lower()
        maddeler_ref = cls.db.collection('kanunlar').document(kanun_kisa_adi).collection('maddeler')
        docs = maddeler_ref.stream()
        
        sonuclar = []
        for doc in docs:
            veri = doc.to_dict()
            metin = veri.get('metin', '').lower()
            baslik = veri.get('baslik', '').lower()
            if arama_terimi in metin or arama_terimi in baslik:
                sonuclar.append(veri)
        
        return sorted(sonuclar, key=lambda x: int(x['no']) if x['no'].isdigit() else x['no'])

    # --- AI ANALİZ FONKSİYONU (DÜZELTİLDİ) ---
    @classmethod
    def madde_analiz_et(cls, api_key, madde_metni, kanun_adi, madde_no, soru): 
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            # Parametredeki 'soru' değişkenini de prompta dahil ettim
            prompt = f"""
            Sen profesyonel bir hukuk asistanısın. Aşağıda metni verilen kanun maddesini bir hukukçu titizliğiyle analiz et.
            Kullanıcının özel sorusu varsa, analizini bu soruya odaklanarak yap.
            
            Kullanıcının Sorusu/Talebi: {soru}
            
            Analiz şunları içermelidir:
            1. Maddenin Özeti (Anlaşılır bir dil)
            2. Maddenin Koruduğu Hukuki Değer / Amacı
            3. Uygulamadaki Pratik Kritik Noktalar
            
            Kanun: {kanun_adi}
            Madde No: {madde_no}
            Madde Metni: {madde_metni}
            """
            
            # Doğrudan metni döndürecek şekilde temizlendi
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            return f"Analiz başarısız oldu: {str(e)}"

    # --- KAZIMA FONKSİYONU (YAPIŞIK MADDELERİ AYIRAN DÜZELTME) ---
    @classmethod
    def kanunu_buluta_yukle(cls, kanun_id, kanun_kisa_adi):
        cls.veritabanini_baslat()
        url = cls.BASE_URL.format(kanun_id)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        driver.get(url)
        time.sleep(10) 
        
        html = driver.page_source
        driver.quit()
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(["script", "style", "nav", "header", "footer", "button"]):
                tag.extract()
            
            metin_alani = soup.find(id="MevzuatMetin") or soup.find(id="MevzuatMetinBul")
            if not metin_alani:
                metin_alani = soup
                
            # 🔴 SİLAH 1: HTML etiketlerini zorla alt satıra indir (Satırların yapışmasını engeller)
            for br in metin_alani.find_all("br"):
                br.replace_with("\n")
            for tag in metin_alani.find_all(["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
                tag.insert_before("\n")
                tag.insert_after("\n")
                
            saf_metin = metin_alani.get_text(separator="\n", strip=True)
            saf_metin = saf_metin.replace('\xa0', ' ').replace('\r', '')
            
            # 🔴 SİLAH 2: Jilet Regex! Hala yapışık kalan "Madde" başlıklarını yakala ve zorla alt satıra at
            # Kanun içinde geçen "Madde 16'ya göre" cümlelerini bozmamak için sadece sonunda tire (-) olan başlıkları hedef alırız.
            saf_metin = re.sub(r'(?i)(?<!\n)((?:ek\s+|geçici\s+)?madde\s+[0-9]+[a-zçğıöşüA-Z/]*\s*[-\u2013\u2014])', r'\n\1', saf_metin)

            satirlar = saf_metin.split('\n')
            
            aktif_madde_no = None
            aktif_madde_metni = []
            aktif_madde_baslik = ""
            kanun_ref = cls.db.collection('kanunlar').document(kanun_kisa_adi).collection('maddeler')

            # ... (üst kısımlar aynı)
            
            for satir in satirlar:
                satir = satir.strip()
                if not satir: continue
                
                # 🔴 SİLAH 3 GÜNCELLENDİ: "Ek" ve "Geçici" kelimelerini yakalayan grup (ek\s+|geçici\s+)? eklendi
                match = re.search(r'^\W*(ek\s+|geçici\s+)?madde\s*([0-9]+[a-zçğıöşüA-Z/]*)', satir, re.IGNORECASE)
                
                if match:
                    # Bir önceki maddeyi kaydet
                    if aktif_madde_no:
                        kanun_ref.document(str(aktif_madde_no)).set({
                            "no": aktif_madde_no, 
                            "baslik": aktif_madde_baslik, 
                            "metin": "\n\n".join(aktif_madde_metni)
                        })
                    
                    # 🔴 YENİ HAYAT KURTARAN KISIM: Prefix (Ön Ek) ve Asıl Numarayı ayır
                    # Eğer "Geçici" yazıyorsa onu al ve ilk harfini büyüt (Örn: "Geçici ")
                    on_ek = match.group(1).strip().capitalize() + " " if match.group(1) else ""
                    asil_no = match.group(2).upper()
                    
                    # Artık kimlikler "3", "Geçici 3", "Ek 5/A" şeklinde tertemiz ayrılıyor!
                    aktif_madde_no = f"{on_ek}{asil_no}".strip() 
                    
                    parcalar = re.split(r'[-\u2013\u2014]', satir, maxsplit=1) 
                    # Başlığı da on ek ile birlikte düzgünce oluştur
                    aktif_madde_baslik = parcalar[1].strip() if len(parcalar) > 1 else f"{on_ek}Madde {asil_no}".strip()
                    aktif_madde_metni = []
                    
                elif aktif_madde_no:
                    aktif_madde_metni.append(satir)

            # Döngü bittiğinde elde kalan son maddeyi de kaydet
            if aktif_madde_no:
                kanun_ref.document(str(aktif_madde_no)).set({
                    "no": aktif_madde_no, 
                    "baslik": aktif_madde_baslik, 
                    "metin": "\n\n".join(aktif_madde_metni)
                })
                
            print(f"✅ {kanun_kisa_adi} başarıyla eksiksiz olarak buluta yüklendi!")
            
        except Exception as e:
            print(f"❌ Hata oluştu ({kanun_kisa_adi}): {e}")

if __name__ == "__main__":
    pass
