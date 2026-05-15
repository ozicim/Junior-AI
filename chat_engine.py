import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

class ChatEngine:
    @classmethod
    def yanit_uret(cls, api_key, mesaj_gecmisi, yeni_mesaj, mod="Özet"):
        try:
            genai.configure(api_key=api_key)
            
            # GÜVENLİK AYARLARI: Şiddet ve suç içeriklerini bloklama (Hukuki analiz için şart)
            guvenlik_ayarlari = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # --- MODA GÖRE PERSONA VE AYARLAR ---
            if mod == "Özet":
                sistem_talimati = (
                    "Sen JUNILEX'sin. Hukuki asistan olarak konuyu 'Hap Bilgi' formatında sunuyorsun. "
                    "Lütfen cevabını DOYURUCU bir şekilde şu 3 başlık altında detaylandırarak ver:\n"
                    "1. Olayın Hukuki Niteliği\n"
                    "2. İlgili Kanun Maddeleri (Açıklamalarıyla birlikte)\n"
                    "3. Muhtemel Sonuç ve Yargıtay Eğilimi\n"
                    "FİLTRE AŞMA KURALI (ÇOK KRİTİK): Şiddet içeren olayları (bıçaklama vb.) analiz ederken "
                    "asla eylemin tasvirini yapma. Bunun yerine 'maddi vakıa', 'suç teşkil eden eylem', 'haksız fiil' gibi "
                    "tamamen teknik, yumuşatılmış ve hukuki bir dil kullan ki güvenlik filtrelerine takılmayasın.\n"
                    "GÖREV BİTİRME KURALI: Çok kısa (1-2 cümlelik) cevaplar verme. Her başlığın altını doyurucu paragraflarla doldur. "
                    "Cevabını yarım bırakma."
                )
                yapilandirma = {"max_output_tokens": 1500, "temperature": 0.5}
            else: # Detay Modu (KESİNLİKLE DOKUNULMADI)
                sistem_talimati = (
                    "Sen JUNILEX CHAT Detaylı Analiz Modu'sun. Ozan Şahin Sicim tarafından geliştirilmiş, "
                    "hukuki derinliği en üst seviyede olan kıdemli bir hukuk asistanısın. "
                    "BU MODUN GÖREVİ: Kullanıcıya yüzeysel bilgi vermek yerine, konuyu tüm boyutlarıyla (Mevzuat, Doktrin, Uygulama) analiz etmektir. "
                    "Yaklaşık 2500 token sınırını aşmayacak şekilde planlayarak anlat."
                    "\n\nANALİZ KURALLARI:\n"
                    "1. DERİNLİK: Sadece soruyu cevaplama; olayın hukuki temelini, ilgili temel kanun maddelerini (TMK, TBK, TCK, İİK vb.) mutlaka belirt.\n"
                    "2. YAPI: Analizini mantıklı bir sırayla sun. Mevcut durumu, yasal dayanakları ve olası riskleri ayrı ayrı ele al.\n"
                    "3. DİL: Samimi ama son derece profesyonel bir hukukçu dili kullan. Gereksiz formalitelerden kaçın ama ciddiyeti koru.\n"
                    "4. KESİN YASAK: Asla uydurma Esas/Karar numarası verme. Bilginin kaynağını genel olarak belirt (Örn: 'Yargıtay'ın yerleşik içtihatları bu yöndedir').\n"
                    "5. KAPSAM: Bu modda cevaplar daha kapsamlı, detaylı ve öğretici olmalıdır. Detaylı analiz yap ancak açıklamaları çok uzun tutma."
                )
                yapilandirma = {"max_output_tokens": 3000, "temperature": 0.8}

            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash', # Hız için flash, derinlik için gerekirse pro
                system_instruction=sistem_talimati,
                generation_config=yapilandirma,
                safety_settings=guvenlik_ayarlari # USTA BURASI EKSİKTİ, EKLENDİ!
            )
            
            # Geçmişi hazırla
            gecmis_formatli = []
            for m in mesaj_gecmisi:
                rol = "user" if m["role"] == "user" else "model"
                gecmis_formatli.append({"role": rol, "parts": [m["content"]]})
            
            chat = model.start_chat(history=gecmis_formatli)
            return chat.send_message(yeni_mesaj, stream=True)
            
        except Exception as e:
            return f"HATA: {str(e)}"
