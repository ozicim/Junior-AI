import google.generativeai as genai

class ChatEngine:
    @classmethod
    def yanit_uret(cls, api_key, mesaj_gecmisi, yeni_mesaj, mod="Özet"):
        try:
            genai.configure(api_key=api_key)
            
            # --- MODA GÖRE PERSONA VE AYARLAR ---
            if mod == "Özet":
                sistem_talimati = (
                    "Sen JUNILEX CHAT'sin. Ozan Şahin Sicim tarafından geliştirilmiş kıdemli bir hukuk asistanısın. "
                    "KRİTİK KURAL: Cevapların kısa, öz ve doğrudan olmalı. Gereksiz giriş cümlelerinden kaçın. "
                    "Lafı uzatmadan en önemli maddeleri ve hukuki sonucu söyle. Maddeleme (bullet points) kullan. "
                    "Maddelerin açıklamalrını olabildiğince kısalt."
                    "Kesinlikle uydurma karar numarası verme. Profesyonel ve net ol."
            
                )
                yapilandirma = {"max_output_tokens": 1000, "temperature": 0.5}
            else: # Detay Modu
                sistem_talimati = (
                    "Sen JUNILEX CHAT Detaylı Analiz Modu'sun. Ozan Şahin Sicim tarafından geliştirilmiş, "
                    "hukuki derinliği en üst seviyede olan kıdemli bir hukuk asistanısın. "
                    "BU MODUN GÖREVİ: Kullanıcıya yüzeysel bilgi vermek yerine, konuyu tüm boyutlarıyla (Mevzuat, Doktrin, Uygulama) analiz etmektir. "
                    "\n\nANALİZ KURALLARI:\n"
                    "1. DERİNLİK: Sadece soruyu cevaplama; olayın hukuki temelini, ilgili temel kanun maddelerini (TMK, TBK, TCK, İİK vb.) mutlaka belirt.\n"
                    "2. YAPI: Analizini mantıklı bir sırayla sun. Mevcut durumu, yasal dayanakları ve olası riskleri ayrı ayrı ele al.\n"
                    "3. DİL: Samimi ama son derece profesyonel bir hukukçu dili kullan. Gereksiz formalitelerden kaçın ama ciddiyeti koru.\n"
                    "4. KESİN YASAK: Asla uydurma Esas/Karar numarası verme. Bilginin kaynağını genel olarak belirt (Örn: 'Yargıtay'ın yerleşik içtihatları bu yöndedir').\n"
                    "5. KAPSAM: Bu modda cevaplar daha kapsamlı, detaylı ve öğretici olmalıdır. Kullanıcının aklında soru işareti bırakmayacak şekilde analiz yap."
                )
                yapilandirma = {"max_output_tokens": 2500, "temperature": 0.8}

            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash', # Hız için flash, derinlik için gerekirse pro
                system_instruction=sistem_talimati,
                generation_config=yapilandirma
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
