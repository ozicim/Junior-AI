import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import json
from turtle import st
import google.generativeai as genai

# ==========================================
# ⚙️ AYARLAR VE YAPILANDIRMA
# ==========================================
API_KEY = "GEMINI_API_KEY_BURAYA"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Junilex gönderici e-posta bilgileri (Gmail önerilir)
GONDERICI_EMAIL = (st.secrets["GMAIL_MAIL"],)
GONDERICI_SIFRE = (st.secrets["GMAIL_SIFRE"],)  # Gmail uygulama şifresi


# ==========================================
# 🧠 YAPAY ZEKA İÇERİK ÜRETİM MODÜLLERİ
# ==========================================
def ai_icerik_uret(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text.replace("```html", "").replace("```", "").strip()
    except Exception as e:
        print(f"AI Hatası: {e}")
        return ""


def uret_resmi_gazete():
    prompt = """Sen bir hukukçusun. Bugünün en kritik mevzuat değişikliğini veya AYM kararını özetle. Yanıtı SADECE şu HTML formatında ver:
    <div style="background-color: #1a1a1a; padding: 15px; border-left: 4px solid #C9A84C; margin-bottom: 15px; border-radius: 8px;">
        <h3 style="color: #E2E8F0; margin-top: 0; font-size: 16px;">🗞️ Günün Hukuki Gelişmesi & Mevzuat</h3>
        <p style="color: #cccccc; font-size: 14px; line-height: 1.5;">[Gelişme buraya]</p>
    </div>"""
    return ai_icerik_uret(prompt)


def uret_emsal_karar():
    prompt = """Sen bir Yargıtay hakimi gibi düşün. Önemli bir emsal karar seç. Yanıtı SADECE şu HTML formatında ver:
    <div style="background-color: #1a1a1a; padding: 15px; border-left: 4px solid #4C6BC9; margin-bottom: 15px; border-radius: 8px;">
        <h3 style="color: #E2E8F0; margin-top: 0; font-size: 16px;">⚖️ Günün Emsal Yargıtay Kararı</h3>
        <p style="color: #cccccc; font-size: 14px; margin-bottom: 5px;"><b>Karar:</b> [Daire ve No]</p>
        <p style="color: #cccccc; font-size: 14px; line-height: 1.5;"><b>İçtihat:</b> [Karar özeti]</p>
    </div>"""
    return ai_icerik_uret(prompt)


def uret_sinav_sorusu():
    prompt = """Zorlayıcı bir pratik olay sorusu (Medeni/Ceza/Ticaret) hazırla. Yanıtı SADECE şu HTML formatında ver:
    <div style="background-color: #1a1a1a; padding: 15px; border-left: 4px solid #C94C4C; margin-bottom: 15px; border-radius: 8px;">
        <h3 style="color: #E2E8F0; margin-top: 0; font-size: 16px;">🎯 Günün Pratik Çalışması</h3>
        <p style="color: #cccccc; font-size: 14px; line-height: 1.5;"><b>Olay:</b> [Kurgu ve soru]</p>
    </div>"""
    return ai_icerik_uret(prompt)


def uret_latince_terim():
    prompt = """Hukukta kullanılan Latince bir terim ve anlamını ver. Yanıtı SADECE şu HTML formatında ver:
    <div style="background-color: #1a1a1a; padding: 15px; border-left: 4px solid #4CC98A; margin-bottom: 15px; border-radius: 8px;">
        <h3 style="color: #E2E8F0; margin-top: 0; font-size: 16px;">📚 Günün Terimi</h3>
        <p style="color: #cccccc; font-size: 14px; line-height: 1.5;"><b>[Terim]:</b> [Anlamı]</p>
    </div>"""
    return ai_icerik_uret(prompt)


# ==========================================
# 🚀 BÜLTEN DAĞITIM MOTORU
# ==========================================
def veritabani_yukle():
    try:
        with open("db.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def bultenleri_gonder():
    db_json = veritabani_yukle()
    if not db_json:
        print("⚠️ Veritabanı okunamadı.")
        return

    # Sadece mail almak isteyen ("aktif": True) birileri var mı diye kontrol edelim ki boşuna API çağrısı yapmayalım
    mail_isteyen_var_mi = any(
        v.get("bulten_tercihleri", {}).get("aktif", True) for k, v in db_json.items()
    )

    if not mail_isteyen_var_mi:
        print(
            "🛑 E-posta aboneliği aktif olan kullanıcı bulunamadı. Dağıtım durduruldu."
        )
        return

    tarih = datetime.datetime.now().strftime("%d %B %Y")
    print("⏳ AI içerikler üretiliyor...")
    icerik_rg = uret_resmi_gazete()
    icerik_emsal = uret_emsal_karar()
    icerik_sinav = uret_sinav_sorusu()
    icerik_terim = uret_latince_terim()

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GONDERICI_EMAIL, GONDERICI_SIFRE)

        gonderilen_sayi = 0

        for email, veri in db_json.items():
            tercih = veri.get(
                "bulten_tercihleri",
                {
                    "aktif": True,
                    "rg": True,
                    "emsal": True,
                    "sinav": False,
                    "terim": True,
                },
            )

            # ANA ŞALTER KONTROLÜ: Şalter kapalıysa direkt sonraki kişiye geç
            if not tercih.get("aktif", True):
                print(f"⏭️ Atlandı: {email} (Abonelik Kapalı)")
                continue

            isim = veri.get("isim", "Meslektaşım")

            baslik = f"""
            <html><body style="font-family: Arial, sans-serif; background-color: #0B0E14; padding: 20px;">
                <div style="max-width: 600px; margin: auto; background-color: #131822; border: 1px solid #232B3E; border-radius: 12px; overflow: hidden;">
                    <div style="background: #1A212E; padding: 20px; border-bottom: 2px solid #C9A84C; text-align: center;">
                        <h2 style="color: #C9A84C; margin: 0;">⚖️ Junilex AI</h2>
                        <p style="color: #8A99AD; margin: 5px 0 0 0;">Günlük Hukuk Asistanınız | {tarih}</p>
                    </div>
                    <div style="padding: 20px;">
                        <p style="color: #E2E8F0;">Günaydın <b>{isim}</b>, işte güne başlarken ihtiyacın olan özet:</p>
            """

            govde = baslik
            if tercih.get("rg"):
                govde += icerik_rg
            if tercih.get("emsal"):
                govde += icerik_emsal
            if tercih.get("sinav"):
                govde += icerik_sinav
            if tercih.get("terim"):
                govde += icerik_terim

            govde += """</div><div style="background-color: #0B0E14; padding: 15px; text-align: center; border-top: 1px solid #232B3E;">
                        <p style="color: #666; font-size: 12px;">Tercihlerinizi uygulamanın Ayarlar sekmesinden değiştirebilirsiniz.</p>
                    </div></div></body></html>"""

            msg = MIMEMultipart()
            msg["From"] = f"Junilex AI <{GONDERICI_EMAIL}>"
            msg["To"] = email
            msg["Subject"] = (
                f"⚖️ Junilex Günlük Özet - {datetime.datetime.now().strftime('%d.%m.%Y')}"
            )
            msg.attach(MIMEText(govde, "html"))

            server.sendmail(GONDERICI_EMAIL, email, msg.as_string())
            print(f"📧 Gönderildi: {email}")
            gonderilen_sayi += 1

        server.quit()
        print(
            f"🎉 Dağıtım Tamamlandı! Toplam {gonderilen_sayi} kişiye mail gönderildi."
        )

    except Exception as e:
        print(f"⚠️ Hata: {e}")


if __name__ == "__main__":
    bultenleri_gonder()
