import re
import time
import shutil
import streamlit as st
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
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
        
        return sorted(sonuclar, key=lambda x: int(x['no']) if str(x['no']).isdigit() else str(x['no']))

    @classmethod
    def madde_analiz_et(cls, api_key, madde_metni, kanun_adi, madde_no, soru): 
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
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
            
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Analiz başarısız oldu: {str(e)}"

    @classmethod
    def kanunu_canli_getir_ve_yazdir(cls, kanun_id, kanun_kisa_adi):
        url = cls.BASE_URL.format(kanun_id)
        
        st.info(f"🌍 [{kanun_kisa_adi}] mevzuat sitesine canlı bağlantı kuruluyor...")
        
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless=new') 
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-extensions')
            options.page_load_strategy = 'none' 
            
            options.binary_location = shutil.which("chromium") or "/usr/bin/chromium"
            sistem_driver_yolu = shutil.which("chromedriver") or "/usr/bin/chromedriver"
            
            if not sistem_driver_yolu:
                raise Exception("Chromedriver bulunamadı! 'packages.txt' dosyasını kontrol et.")
                
            service = Service(sistem_driver_yolu)
            driver = webdriver.Chrome(service=service, options=options)
            
            driver.get(url)
            time.sleep(8) 
            
            html = driver.page_source
            
            if "Madde 1" not in html and "MADDE 1" not in html:
                st.warning("🕵️ Ana sayfada metin yok, Iframe'ler taranıyor...")
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for i, frame in enumerate(iframes):
                    driver.switch_to.frame(frame)
                    if "Madde" in driver.page_source or "MADDE" in driver.page_source:
                        html = driver.page_source
                        st.success("🎯 Doğru metin iframe'de bulundu!")
                        break
                    driver.switch_to.default_content() 
            
            driver.quit()
            
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(["script", "style", "nav", "header", "footer", "button"]):
                tag.extract()
            
            for br in soup.find_all("br"):
                br.replace_with("\n")
            for tag in soup.find_all(["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
                tag.insert_before("\n")
                tag.insert_after("\n")
                
            saf_metin = soup.get_text(separator="\n", strip=True)
            saf_metin = saf_metin.replace('\xa0', ' ').replace('\r', '')
            saf_metin = re.sub(r'(?i)(?<!\n)((?:ek\s+|geçici\s+)?madde\s+[0-9]+[a-zçğıöşüA-Z/]*\s*[-\u2013\u2014])', r'\n\1', saf_metin)

            satirlar = saf_metin.split('\n')
            
            aktif_madde_no = None
            aktif_madde_metni = []
            aktif_madde_baslik = ""
            
            cekilen_maddeler = []

            for satir in satirlar:
                satir = satir.strip()
                if not satir: continue
                
                match = re.search(r'^\W*(ek\s+|geçici\s+)?madde\s*([0-9]+[a-zçğıöşüA-Z/]*)', satir, re.IGNORECASE)
                
                if match:
                    if aktif_madde_no:
                        cekilen_maddeler.append({
                            "no": aktif_madde_no, 
                            "baslik": aktif_madde_baslik, 
                            "metin": "\n\n".join(aktif_madde_metni)
                        })
                    
                    on_ek = match.group(1).strip().capitalize() + " " if match.group(1) else ""
                    asil_no = match.group(2).upper()
                    
                    aktif_madde_no = f"{on_ek}{asil_no}".strip() 
                    parcalar = re.split(r'[-\u2013\u2014]', satir, maxsplit=1) 
                    aktif_madde_baslik = parcalar[1].strip() if len(parcalar) > 1 else f"{on_ek}Madde {asil_no}".strip()
                    aktif_madde_metni = []
                    
                elif aktif_madde_no:
                    aktif_madde_metni.append(satir)

            if aktif_madde_no:
                cekilen_maddeler.append({
                    "no": aktif_madde_no, 
                    "baslik": aktif_madde_baslik, 
                    "metin": "\n\n".join(aktif_madde_metni)
                })
                
            if len(cekilen_maddeler) > 0:
                st.success(f"✅ BAŞARILI! Toplam {len(cekilen_maddeler)} madde canlı olarak çekildi.")
                
                st.markdown(f"### 📜 {kanun_kisa_adi} Maddeleri")
                for madde in cekilen_maddeler:
                    with st.expander(f"Madde {madde['no']} - {madde['baslik']}", expanded=False):
                        st.write(madde['metin'])
            else:
                st.error(f"⚠️ DİKKAT: {kanun_kisa_adi} için 0 madde bulundu! Metin çekilemedi.")
                
        except Exception as e:
            st.error(f"❌ TEKNİK HATA OLUŞTU ({kanun_kisa_adi}): {str(e)}")

if __name__ == "__main__":
    pass
