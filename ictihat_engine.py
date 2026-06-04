import google.generativeai as genai
import requests
import json

class IctihatEngine:
    @classmethod
    def karar_analiz_et(cls, api_key, karar_metni, soru):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            # Dinamik Prompt Mimarisi: Soruya göre özel başlıklandırma yapar.
            prompt = f"""
            Sen kıdemli bir Yargıtay Tetkik Hakimi ve hakim/savcı/avukatlara destek olan bir junior asistan yapay zekasın. 
            Aşağıdaki Yargıtay karar metnini, kullanıcının sorduğu soruya odaklanarak analiz et.
            
            KARAR METNİ: {karar_metni}
            İSTENEN ANALİZ / SORU: {soru}
            
            GÖREVİN:
            Eğer kullanıcı sadece bir özet istiyorsa sadece özet ver. Eğer mahkemeler arası çelişki soruluyorsa sadece o çelişkiyi anlat. 
            Gereksiz yere sabit şablon başlıklar (Örn: Uyuşmazlık, Gerekçe vb.) üretme, doğrudan kullanıcının sorduğu hususa hukuki ve net bir yanıt ver.
            Gerekçelerini ve tespitlerini daima HMK, CMK, TMK, TBK gibi temel kanunlara dayandırarak açıkla.
            """
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"HATA: {str(e)}"

    @classmethod
    def serper_search(cls, query, api_key):
        url = "https://google.serper.dev/search"
        # Arama Havuzu Yargıtay'ın resmi sitesini içerecek şekilde genişletildi
        payload = json.dumps({
            "q": f"(site:karararama.yargitay.gov.tr OR site:kararara.com OR site:kazanci.com.tr) {query} Yargıtay kararı",
            "gl": "tr", "hl": "tr"
        })
        headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()
    
    @classmethod
    def emsal_ara(cls, gemini_key, serper_key, olay_input):
        try:
            search_results = cls.serper_search(olay_input, serper_key)
            context = ""
            for result in search_results.get('organic', []):
                context += f"\nBaşlık: {result.get('title')}\nÖzet: {result.get('snippet')}\n"

            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            # Halüsinasyon kalkanı esnetildi: Gerçek verileri saklamaz.
            prompt = f"""
            SEN AVUKATLARA VE HAKİMLERE ASİSTANLIK YAPAN KIDEMLİ BİR YARGITAY UYGULAMALARI UZMANISIN.
            Aşağıda internetten (Serper API) gelen gerçek arama sonuçları ve kullanıcının hukuki olayı verilmiştir.
            
            GELEN GERÇEK VERİLER: {context}
            HUKUKİ OLAY: {olay_input}
            
            GÖREVİN:
            1. Kendi kendine ASLA Esas/Karar numarası, tarih veya mahkeme ismi uydurma.
            2. ANCAK, yukarıdaki "GELEN GERÇEK VERİLER" içinde spesifik bir Yargıtay Esas ve Karar numarası veya tarihi geçiyorsa, bunları BİREBİR KULLANARAK avukata referans olarak sun. 
            3. Amacın Yargıtay'ın genel yönelimini ve uygulama trendini analiz etmektir.
            
            ANALİZ FORMATI (Sadece bu başlıkları kullan):
            
            ### 🏛️ YARGITAY YÖNELİM ANALİZİ
            **1. Yerleşik Uygulama Trendi:** Yargıtay bu tip olaylara genel olarak nasıl bakıyor?
            
            **2. Emsal Karar Referansları:** (Gelen verilerde Esas/Karar numarası varsa buraya ekle. Yoksa "Spesifik numara bulunamadı ancak genel yönelim şöyledir" de.)
            
            **3. Kritik Eşikler ve Kriterler:** Mahkemenin bir karara varırken aradığı ana şartlar nelerdir?
            
            **4. İlgili Kanun Maddeleri ve Mevzuat Dayanağı:** Uygulanması gereken temel kanun maddelerini açıkla.
            
            **5. Stratejik Hukuki Yorum:** Bu olayda davanın kaderini belirleyecek olan en temel hukuki argüman ne olmalıdır?
            """
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Operasyon Hatası: {str(e)}"
