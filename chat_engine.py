import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- SABIT TANIMLAMALAR (class dışında, bir kez yüklenir) ---
_GUVENLIK_AYARLARI = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

_SISTEM_OZET = (
    "Sen JUNILEX'sin. Hukuki asistan olarak konuyu 'Hap Bilgi' formatında sunuyorsun. "
    "Lütfen cevabını DOYURUCU bir şekilde şu 3 başlık altında detaylandırarak ver:\n"
    "1. Olayın Hukuki Niteliği\n"
    "2. İlgili Kanun Maddeleri (Açıklamalarıyla birlikte)\n"
    "3. Muhtemel Sonuç ve Yargıtay Eğilimi\n"
    "GİZLİ KURAL: Kullanıcının girdiği eylemleri fiziksel olarak tasvir etme. Sadece 'maddi vakıa', "
    "'haksız fiil', 'TCK ihlali' gibi tamamen soyut ve hukuki terimler kullan.\n"
    "GÖREV: Her başlığın altını doyurucu paragraflarla doldur, kesinlikle 1-2 cümlelik kısa cevaplar verme."
)

_SISTEM_DETAY = (
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

_CONFIG_OZET = genai.types.GenerationConfig(max_output_tokens=8192, temperature=0.5)
_CONFIG_DETAY = genai.types.GenerationConfig(max_output_tokens=8192, temperature=0.8)


class ChatEngine:
    # ✅ Model nesneleri class seviyesinde cache'leniyor — her istekte yeniden oluşturulmuyor
    _model_ozet = None
    _model_detay = None
    _configured_key = None

    @classmethod
    def _modeli_hazirla(cls, api_key, mod):
        """Modeli ilk kullanımda oluşturur, sonraki çağrılarda cache'den döner."""
        # API key değiştiyse (geliştirme sırasında olabilir) yeniden yapılandır
        if cls._configured_key != api_key:
            genai.configure(api_key=api_key)
            cls._configured_key = api_key
            cls._model_ozet = None
            cls._model_detay = None

        if mod == "Özet":
            if cls._model_ozet is None:
                cls._model_ozet = genai.GenerativeModel(
                    model_name='gemini-2.5-flash',
                    system_instruction=_SISTEM_OZET,
                    generation_config=_CONFIG_OZET,
                    safety_settings=_GUVENLIK_AYARLARI
                )
            return cls._model_ozet
        else:
            if cls._model_detay is None:
                cls._model_detay = genai.GenerativeModel(
                    model_name='gemini-2.5-flash',
                    system_instruction=_SISTEM_DETAY,
                    generation_config=_CONFIG_DETAY,
                    safety_settings=_GUVENLIK_AYARLARI
                )
            return cls._model_detay

    @classmethod
    def yanit_uret(cls, api_key, mesaj_gecmisi, yeni_mesaj, mod="Özet"):
        try:
            model = cls._modeli_hazirla(api_key, mod)

            gecmis_formatli = [
                {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
                for m in mesaj_gecmisi
            ]

            chat = model.start_chat(history=gecmis_formatli)
            return chat.send_message(yeni_mesaj, stream=True)

        except Exception as e:
            return f"HATA: {str(e)}"
