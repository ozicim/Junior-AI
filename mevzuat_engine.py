import streamlit as st
import chromadb
import google.generativeai as genai
import re
import json
import os
import zipfile
from sentence_transformers import SentenceTransformer

YASAL_UYARI = (
    "⚠️ **Bilgi Amaçlıdır:** Bu madde metni Junilex yerel veritabanından getirilmiştir. "
    "Güncel ve hukuken bağlayıcı metin için mevzuat.gov.tr adresini kontrol ediniz."
)

class MevzuatBulutEngine:
    _model = None

    @classmethod
    def get_kanunlar(cls):
        # Bütün arşivi indirdiğimiz için menüyü dilediğin kadar genişletebilirsin!
        return [
            {"id": "5237", "kisaAd": "TCK", "isim": "Türk Ceza Kanunu", "kategori": "Ceza Hukuku", "aciklama": "Temel Ceza Mevzuatı"},
            {"id": "5271", "kisaAd": "CMK", "isim": "Ceza Muhakemesi Kanunu", "kategori": "Ceza Hukuku", "aciklama": "Yargılama Usulleri"},
            {"id": "4721", "kisaAd": "TMK", "isim": "Türk Medeni Kanunu", "kategori": "Özel Hukuk", "aciklama": "Temel Medeni Haklar"},
            {"id": "6098", "kisaAd": "TBK", "isim": "Türk Borçlar Kanunu", "kategori": "Özel Hukuk", "aciklama": "Borç İlişkileri ve Sözleşmeler"},
            {"id": "6102", "kisaAd": "TTK", "isim": "Türk Ticaret Kanunu", "kategori": "Ticaret Hukuku", "aciklama": "Ticari İşletme ve Şirketler"},
            {"id": "4857", "kisaAd": "İK", "isim": "İş Kanunu", "kategori": "İş Hukuku", "aciklama": "İşçi ve İşveren İlişkileri"},
            {"id": "2004", "kisaAd": "İİK", "isim": "İcra ve İflas Kanunu", "kategori": "İcra Hukuku", "aciklama": "Takip ve Tahsilat"},
            {"id": "6502", "kisaAd": "TKHK", "isim": "Tüketicinin Korunması Hakkında Kanun", "kategori": "Özel Hukuk", "aciklama": "Tüketici Hakları"}
        ]

    @classmethod
    def _modeli_hazirla(cls, api_key):
        if cls._model is None:
            genai.configure(api_key=api_key)
            cls._model = genai.GenerativeModel('models/gemini-2.5-flash')
        return cls._model

    @classmethod
    def kanunu_buluta_yukle(cls, *args, **kwargs):
        """
        ZIP dosyasını açmadan hafızadan okur ve sadece istenilen kanunu ChromaDB'ye işler.
        """
        kisa_ad = kwargs.get("kisa_ad") or kwargs.get("kisaAd") or kwargs.get("kisa_ad_bul")
        kanun_id = kwargs.get("kanun_id") or kwargs.get("id")
        
        if not kisa_ad or not kanun_id:
            if len(args) >= 3:
                kanun_id = args[1]
                kisa_ad = args[2]
                
        if not kisa_ad or not kanun_id:
            st.error("❌ Hata: Kanun kısa adı veya numarası alınamadı.")
            return 0
            
        zip_dosya_adi = "mevzuat_arsiv.zip" 
        ic_dosya_adi = "mevzuat_ham.json"
        
        if not os.path.exists(zip_dosya_adi):
            st.error(f"⚠️ {zip_dosya_adi} bulunamadı! Lütfen arşivi GitHub'a yükleyin.")
            return 0
            
        with st.spinner(f"🧠 {kisa_ad} dev arşivden (ZIP) çıkarılıp Junilex beynine işleniyor... (Bu işlem 1-2 dakika sürebilir)"):
            try:
                chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
                collection = chroma_client.get_or_create_collection(name="turk_mevzuati")
                embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
                
                # ZIP dosyasının içinden JSON'u belleğe okuyoruz (Diske çıkarmadan!)
                with zipfile.ZipFile(zip_dosya_adi, 'r') as z:
                    with z.open(ic_dosya_adi) as f:
                        tum_mevzuat = json.loads(f.read().decode('utf-8'))
                    
                hedef_kanun = None
                for kanun in tum_mevzuat:
                    if str(kanun.get("kanun_numarasi")) == str(kanun_id):
                        hedef_kanun = kanun
                        break
                        
                if not hedef_kanun:
                    st.error(f"❌ {kisa_ad} (Kanun No: {kanun_id}) dev arşivde bulunamadı!")
                    return 0
                    
                maddeler = hedef_kanun.get("maddeler", [])
                if not maddeler:
                    st.error(f"❌ {kisa_ad} bulundu ancak içi boş (maddeleri yok).")
                    return 0
                    
                ids = []
                documents = []
                metadatas = []
                embeddings = []
                
                for sira, madde in enumerate(maddeler):
                    madde_no_ham = str(madde.get("madde_numarasi", ""))
                    madde_no = madde_no_ham.replace("MADDE", "").replace("Madde", "").strip()
                    icerik = madde.get("text", "")
                    
                    aranacak_metin = f"{kisa_ad} Madde {madde_no}: {icerik}"
                    
                    ids.append(f"{kisa_ad}_{madde_no}_{sira}")
                    documents.append(icerik)
                    metadatas.append({"kanun": kisa_ad, "madde": madde_no})
                    embeddings.append(embedding_model.encode(aranacak_metin).tolist())
                    
                collection.add(
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                st.success(f"🚀 BAŞARILI! {len(maddeler)} adet {kisa_ad} maddesi Junilex'in kalıcı hafızasına kazındı.")
                return len(maddeler)
                
            except Exception as e:
                st.error(f"❌ Yükleme sırasında hata: {str(e)}")
                return 0

    @classmethod
    def madde_getir_buluttan(cls, *args, **kwargs):
        try:
            kanun_kisa_ad = kwargs.get("kanun_kisa_ad") or kwargs.get("kanun_kisa_ad_bul")
            madde_no_tam = kwargs.get("madde_no_tam") or kwargs.get("madde_no")
            
            if not kanun_kisa_ad and len(args) >= 1:
                kanun_kisa_ad = args[0]
            if not madde_no_tam and len(args) >= 2:
                madde_no_tam = args[1]
                
            if not kanun_kisa_ad or not madde_no_tam:
                return {"no": "BİLİNMEYEN", "baslik": "Hata", "metin": "❌ Eksik parametre gönderildi."}

            chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
            collection = chroma_client.get_collection(name="turk_mevzuati")
            
            istenen_tur = "normal"
            istenen_sayi = str(madde_no_tam).upper()
            
            if istenen_sayi.startswith("GECİCİ_") or istenen_sayi.startswith("GEÇİCİ_"):
                istenen_tur = "gecici"
                istenen_sayi = istenen_sayi.split("_")[1]
            elif istenen_sayi.startswith("EK_"):
                istenen_tur = "ek"
                istenen_sayi = istenen_sayi.split("_")[1]

            sonuclar = collection.get(where={"kanun": {"$eq": kanun_kisa_ad}})
            
            if not sonuclar or not sonuclar['documents']:
                return {"no": madde_no_tam, "baslik": "Veritabanı Boş", "metin": f"⚠️ {kanun_kisa_ad} henüz yüklenmemiş. Önce yükleme panelinden kanunu hafızaya alın."}
                
            bulunan_metin = None
            for metin, meta in zip(sonuclar['documents'], sonuclar['metadatas']):
                db_madde_no = str(meta.get("madde", "")).upper()
                metin_baslik = metin[:100].upper()
                rakam_eslesmesi = re.findall(r'\d+', db_madde_no)
                db_rakam = rakam_eslesmesi[0] if rakam_eslesmesi else db_madde_no
                
                if db_rakam == istenen_sayi:
                    if istenen_tur == "normal" and "GEÇİCİ" not in db_madde_no and "EK MADDE" not in metin_baslik:
                        bulunan_metin = metin
                        break
                    elif istenen_tur == "gecici" and ("GEÇİCİ" in db_madde_no or "GECİCİ" in db_madde_no):
                        bulunan_metin = metin
                        break
                    elif istenen_tur == "ek" and "EK" in db_madde_no:
                        bulunan_metin = metin
                        break

            if not bulunan_metin:
                for metin, meta in zip(sonuclar['documents'], sonuclar['metadatas']):
                    if str(meta.get("madde", "")) == str(madde_no_tam):
                        bulunan_metin = metin
                        break

            if bulunan_metin:
                return {
                    "no": str(madde_no_tam),
                    "baslik": f"{kanun_kisa_ad} - Madde {str(madde_no_tam).replace('_', ' ')}",
                    "metin": bulunan_metin + f"\n\n{YASAL_UYARI}"
                }
            else:
                return {"no": madde_no_tam, "baslik": "Madde Eksik", "metin": f"⚠️ {kanun_kisa_ad} Madde {str(madde_no_tam).replace('_', ' ')} bulunamadı."}
                
        except Exception as e:
            return {"no": "HATA", "baslik": "Bağlantı Hatası", "metin": f"❌ Veritabanı Hatası: {e}"}

    @classmethod
    def madde_analiz_et(cls, api_key, kanun_kisa_ad, madde_no_tam, madde_metni):
        try:
            model = cls._modeli_hazirla(api_key)
            prompt = f"""Sen Yargıtay Tetkik Hakimisin. Aşağıdaki kanunu analiz et.
            Mevzuat: {kanun_kisa_ad} Madde {str(madde_no_tam).replace('_', ' ')}
            Metin: {madde_metni}
            
            Başlıklar:
            - **🎯 Maddenin Amacı:**
            - **⚖️ Şartlar:**
            - **🏛️ Yargıtay Eğilimi:**
            """
            return model.generate_content(prompt, stream=True)
        except Exception as e:
            st.error(f"❌ Hata: {str(e)}")
            return None
