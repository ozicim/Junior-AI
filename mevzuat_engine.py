import re
import time
import shutil
import streamlit as st
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import google.generativeai as genai

class MevzuatBulutEngine:
    BASE_URL = "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={}&MevzuatTur=1&MevzuatTertip=5"

    KANUNLAR = [
        {"id": "5237", "isim": "Türk Ceza Kanunu", "kisaAd": "TCK", "kategori": "Ceza Hukuku"},
        {"id": "5271", "isim": "Ceza Muhakemesi Kanunu", "kisaAd": "CMK", "kategori": "Ceza Hukuku"},
        {"id": "4721", "isim": "Türk Medeni Kanunu", "kisaAd": "TMK", "kategori": "Özel Hukuk"},
        {"id": "6098", "isim": "Türk Borçlar Kanunu", "kisaAd": "TBK", "kategori": "Özel Hukuk"},
        {"id": "6102", "isim": "Türk Ticaret Kanunu", "kisaAd": "TTK", "kategori": "Ticaret Hukuku"},
        {"id": "4857", "isim": "İş Kanunu", "kisaAd": "İK", "kategori": "İş Hukuku"}
    ]

    @classmethod
    def get_kanunlar(cls):
        return cls.KANUNLAR

    # 🔴 YENİ: NOKTA ATIŞI CANLI MADDE ÇEKİCİ (VERİTABANI YOK)
    @classmethod
    def tek_madde_getir(cls, kanun_id, istenen_madde_no):
        url = cls.BASE_URL.format(kanun_id)
        
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless=new') 
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-extensions')
            
            # Sitenin ağır kodlarını bekleme, iskelet gelince kopar al
            options.page_load_strategy = 'eager' 
            
            options.binary_location = shutil.which("chromium") or "/usr/bin/chromium"
            sistem_driver_yolu = shutil.which("chromedriver") or "/usr/bin/chromedriver"
            
            if not sistem_driver_yolu:
                raise Exception("Chromedriver bulunamadı! 'packages.txt' dosyasını kontrol et.")
                
            service = Service(sistem_driver_yolu)
            driver = webdriver.Chrome(service=service, options=options)
            
            driver.get(url)
            time.sleep(4) # Çok kısa bekleme süresi, çünkü sadece 1 madde arıyoruz
            
            html = driver.page_source
            
            if "Madde 1" not in html and "MADDE 1" not in html:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for frame in iframes:
                    driver.switch_to.frame(frame)
                    if "Madde" in driver.page_source or "MADDE" in driver.page_source:
                        html = driver.page_source
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
            
            madde_bulundu = False
            kaydedilen_metin = []
            bulunan_baslik = ""
            
            # Aranacak maddeyi standart format yap (Örn: "geçici 3" -> "GEÇİCİ 3")
            hedef_no = str(istenen_madde_no).strip().upper()

            for satir in satirlar:
                satir = satir.strip()
                if not satir: continue
                
                match = re.search(r'^\W*(ek\s+|geçici\s+)?madde\s*([0-9]+[a-zçğıöşüA-Z/]*)', satir, re.IGNORECASE)
                
                if match:
                    on_ek = match.group(1).strip().capitalize() + " " if match.group(1) else ""
                    asil_no = match.group(2).upper()
                    okunan_no = f"{on_ek}{asil_no}".strip()
                    
                    if madde_bulundu:
                        # HIZ HİLESİ: Aradığımız maddeyi okuyorduk, şimdi BİR SONRAKİ maddeye denk geldik.
                        # Sayfanın geri kalan 1000 satırını okumaya gerek yok, direkt çık!
                        break
                        
                    if okunan_no == hedef_no:
                        # İstenen maddeyi bulduk, kaydetmeye başla
                        madde_bulundu = True
                        parcalar = re.split(r'[-\u2013\u2014]', satir, maxsplit=1) 
                        bulunan_baslik = parcalar[1].strip() if len(parcalar) > 1 else f"{on_ek}Madde {asil_no}".strip()
                        
                elif madde_bulundu:
                    kaydedilen_metin.append(satir)

            if not kaydedilen_metin and not bulunan_baslik:
                return False, None, f"⚠️ Bu kanunda '{hedef_no}' numaralı madde bulunamadı."
                
            return True, bulunan_baslik, "\n\n".join(kaydedilen_metin)

        except Exception as e:
            return False, None, f"❌ Çekim sırasında hata oluştu: {str(e)}"

    @classmethod
    def madde_analiz_et(cls, api_key, madde_metni, kanun_adi, madde_no, soru=""): 
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            prompt = f"""
            Sen profesyonel bir hukuk asistanısın. Aşağıda metni verilen kanun maddesini bir hukukçu titizliğiyle analiz et.
            
            Kullanıcının Sorusu: {soru}
            
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
