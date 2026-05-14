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

    # --- AI ANALİZ FONKSİYONU (YENİ SİLAHIMIZ) ---
    @classmethod
    def madde_analiz_et(cls, api_key, madde_metni, kanun_adi, madde_no, soru): # 'soru' burada olmalı
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            
            prompt = f"""
            Sen profesyonel bir hukuk asistanısın. Aşağıda metni verilen kanun maddesini bir hukukçu titizliğiyle analiz et.
            
            Analiz şunları içermelidir:
            1. Maddenin Özeti (Anlaşılır bir dil)
            2. Maddenin Koruduğu Hukuki Değer / Amacı
            3. Uygulamadaki Pratik Kritik Noktalar
            
            Kanun: {kanun_adi}
            Madde No: {madde_no}
            Madde Metni: {madde_metni}
            """
            response = model.generate_content(prompt, stream=True)
            return response
            
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Analiz başarısız oldu: {str(e)}"

    # --- KAZIMA FONKSİYONU (HATA BURADAYDI, DÜZELTİLDİ) ---
    @classmethod
    def kanunu_buluta_yukle(cls, kanun_id, kanun_kisa_adi):
        cls.veritabanini_baslat()
        url = cls.BASE_URL.format(kanun_id)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        driver.get(url)
        time.sleep(15)
        
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            time.sleep(2)
        
        html = driver.page_source
        driver.quit()
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(["script", "style", "nav", "header", "footer", "button"]):
                tag.extract()
                
            saf_metin = soup.get_text(separator="\n", strip=True)
            saf_metin = saf_metin.replace('\xa0', ' ').replace('\r', '')
            satirlar = saf_metin.split('\n')
            
            aktif_madde_no = None
            aktif_madde_metni = []
            aktif_madde_baslik = ""
            kanun_ref = cls.db.collection('kanunlar').document(kanun_kisa_adi).collection('maddeler')

            for satir in satirlar:
                satir = satir.strip()
                if not satir: continue
                match = re.search(r'^madde\s*(\d+)', satir, re.CASEINSENSITIVE)
                
                if match:
                    if aktif_madde_no:
                        kanun_ref.document(str(aktif_madde_no)).set({
                            "no": aktif_madde_no, 
                            "baslik": aktif_madde_baslik, 
                            "metin": "\n\n".join(aktif_madde_metni)
                        })
                    aktif_madde_no = match.group(1)
                    parcalar = re.split(r'[-\u2013\u2014]', satir, maxsplit=1) 
                    aktif_madde_baslik = parcalar[1].strip() if len(parcalar) > 1 else f"Madde {aktif_madde_no}"
                    aktif_madde_metni = []
                elif aktif_madde_no:
                    aktif_madde_metni.append(satir)

            if aktif_madde_no:
                kanun_ref.document(str(aktif_madde_no)).set({
                    "no": aktif_madde_no, 
                    "baslik": aktif_madde_baslik, 
                    "metin": "\n\n".join(aktif_madde_metni)
                })
        except Exception as e:
            print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    pass
