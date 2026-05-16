import re
import urllib.request
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# ========================================================
# 🔑 FIREBASE AYARLARI (KENDİ BİLGİSAYARIN İÇİN)
# ========================================================
# İNDİRDİĞİN JSON DOSYASININ YOLUNU BURAYA YAZ:
FIREBASE_JSON_YOLU = "kilit.json" 

# Firebase'i Başlat
cred = credentials.Certificate(FIREBASE_JSON_YOLU)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ========================================================
# 🚀 IŞIK HIZINDA KAZIMA MOTORU (YEREL İNTERNETİNLE)
# ========================================================
def kanunu_firebase_yukle(kanun_id, kanun_kisa_adi):
    url = f"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={kanun_id}&MevzuatTur=1&MevzuatTertip=5"
    print(f"🌍 {kanun_kisa_adi} çekiliyor... Lütfen bekle.")
    
    try:
        # Senin bilgisayarından istek gittiği için engellenmeyecek!
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')
        
        db.collection('kanunlar').document(kanun_kisa_adi).set({"isim": kanun_kisa_adi, "durum": "Aktif"}, merge=True)
        
        soup = BeautifulSoup(html, 'html.parser')
        metin_alani = soup.find(id="MevzuatMetin") or soup.find(id="MevzuatMetinBul") or soup
            
        for tag in metin_alani(["script", "style", "nav", "header", "footer", "button"]): tag.extract()
        for br in metin_alani.find_all("br"): br.replace_with("\n")
        for tag in metin_alani.find_all(["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
            tag.insert_before("\n")
            tag.insert_after("\n")
            
        saf_metin = metin_alani.get_text(separator="\n", strip=True)
        saf_metin = saf_metin.replace('\xa0', ' ').replace('\r', '')
        saf_metin = re.sub(r'(?i)(?<!\n)((?:ek\s+|geçici\s+)?madde\s+[0-9]+[a-zçğıöşüA-Z/]*\s*[-\u2013\u2014])', r'\n\1', saf_metin)

        satirlar = saf_metin.split('\n')
        aktif_madde_no = None
        aktif_madde_metni = []
        aktif_madde_baslik = ""
        kanun_ref = db.collection('kanunlar').document(kanun_kisa_adi).collection('maddeler')
        eklenen_sayi = 0

        for satir in satirlar:
            satir = satir.strip()
            if not satir: continue
            
            match = re.search(r'^\W*(ek\s+|geçici\s+)?madde\s*([0-9]+[a-zçğıöşüA-Z/]*)', satir, re.IGNORECASE)
            if match:
                if aktif_madde_no:
                    kanun_ref.document(str(aktif_madde_no)).set({"no": aktif_madde_no, "baslik": aktif_madde_baslik, "metin": "\n\n".join(aktif_madde_metni)})
                    eklenen_sayi += 1
                on_ek = match.group(1).strip().capitalize() + " " if match.group(1) else ""
                asil_no = match.group(2).upper()
                aktif_madde_no = f"{on_ek}{asil_no}".strip() 
                parcalar = re.split(r'[-\u2013\u2014]', satir, maxsplit=1) 
                aktif_madde_baslik = parcalar[1].strip() if len(parcalar) > 1 else f"{on_ek}Madde {asil_no}".strip()
                aktif_madde_metni = []
            elif aktif_madde_no:
                aktif_madde_metni.append(satir)

        if aktif_madde_no:
            kanun_ref.document(str(aktif_madde_no)).set({"no": aktif_madde_no, "baslik": aktif_madde_baslik, "metin": "\n\n".join(aktif_madde_metni)})
            eklenen_sayi += 1
            
        print(f"✅ BAŞARILI! {kanun_kisa_adi} bitti. Toplam {eklenen_sayi} madde Firebase'e yazıldı.")
            
    except Exception as e:
        print(f"❌ HATA ({kanun_kisa_adi}): {str(e)}")

# ========================================================
# 🚀 HANGİ KANUNU YÜKLEMEK İSTİYORSAN BURADAN ÇALIŞTIR
# ========================================================
if __name__ == "__main__":
    print("Mevzuat Yükleyici Başlatılıyor...")
    
    # İstediğin kanunun başındaki # işaretini kaldırıp çalıştır!
    
    kanunu_firebase_yukle("5237", "TCK") 
    kanunu_firebase_yukle("4857", "İK")
    kanunu_firebase_yukle("4721", "TMK")
    # kanunu_firebase_yukle("6098", "TBK")
    # kanunu_firebase_yukle("6102", "TTK")
    # kanunu_firebase_yukle("5271", "CMK")
