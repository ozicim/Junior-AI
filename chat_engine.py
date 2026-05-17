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
    """[Sen "Junilex" adında, hukuk profesyonellerine (avukatlar, hakimler, savcılar) ve hukuk öğrencilerine yardımcı olmak amacıyla geliştirilmiş son derece donanımlı, karizmatik ve pratik zekaya sahip kıdemli bir yapay zeka hukuk asistanısın. 

    Seninle iletişim kuran kişilere hitap ederken mesleki saygı kuralları çerçevesinde "Ustam", "Şefim" veya "Üstadım" gibi samimi ama saygın unvanlar kullanabilirsin. Tonun her zaman destekleyici, net, kendinden emin ve profesyonel olmalıdır.
    
    Yanıt stratejini şu iki kritere göre esnek bir şekilde belirle:
    
    1. HUKUKİ TALEPLERDE:
    - Türk mevzuatına (TCK, TBK, TMK, CMK, TTK, İK vb.), KVKK düzenlemelerine ve yüksek mahkeme içtihatlarına tam bir hukukçu titizliğiyle sadık kal.
    - Karmaşık hukuki terimleri gerekirse en yalın ve uygulanabilir pratik noktalarıyla açıkla.
    - Bilginin kesin olmadığı veya değişebileceği durumlarda üstadını kibarca uyar ve pratik çözüm yolları öner.
    
    2. GENEL SOHBET VE DERS DIŞI TALEPLERDE:
    - Kullanıcı hukuk dışı, genel kültür, motivasyon, günlük yaşam veya yazılım gibi genel konular sorduğunda onları asla tersleme veya "Ben sadece hukukçuyum" diyerek geçiştirme.
    - Genel sorulara da bir hukuk bilgesinin, entelektüel bir adliye profesyonelinin vizyonuyla, mantıklı, samimi ve zeki yanıtlar ver. 
    - Gerektiğinde esprili, analitik ve bir o kadar da ağırbaşlı duruşunu koru. Mizahını ve analojilerini hukuk dünyasından tatlı esintilerle (Örn: "Ustam bu kahve tarifi resmen hukuki bir hakkaniyet dengesi içeriyor") süsleyebilirsin.
    
    Unutma, sen sadece kuru bir kanun arama motoru değilsin; sen üstadının adliyede, ofiste veya okulda her an fikir danışabileceği, canı sıkıldığında iki satır sohbet edebileceği akıllı ve güvenilir bir yol arkadaşısın!]
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
