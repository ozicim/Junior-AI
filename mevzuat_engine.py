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
    "Güncel ve hukuken binding metin için mevzuat.gov.tr adresini kontrol ediniz."
)

class MevzuatBulutEngine:
    _model = None

    @classmethod
    def get_kanunlar(cls):
        """
        Junilex Platformu İçin Sınıflandırılmış 20 Temel Kanun Listesi.
        app.py içerisindeki selectbox ve filtreleme menülerini besler.
        """
        return [
            # --- KAMU HUKUKU ---
            {"id": "2709", "kisaAd": "AY", "isim": "Türkiye Cumhuriyeti Anayasası", "kategori": "🏛️ Kamu Hukuku", "aciklama": "Devletin Temel Yapısı ve Haklar"},
            {"id": "2577", "kisaAd": "İYUK", "isim": "İdari Yargılama Usulü Kanunu", "kategori": "🏛️ Kamu Hukuku", "aciklama": "İptal ve Tam Yargı Davaları"},
            {"id": "657", "kisaAd": "DMK", "isim": "Devlet Memurları Kanunu", "kategori": "🏛️ Kamu Hukuku", "aciklama": "Memur Hakları ve Disiplin Hükümleri"},
            {"id": "2942", "kisaAd": "KK", "isim": "Kamulaştırma Kanunu", "kategori": "🏛️ Kamu Hukuku", "aciklama": "Kamu Yararı ve Kamulaştırma Bedeli"},
            
            # --- CEZA HUKUKU ---
            {"id": "5237", "kisaAd": "TCK", "isim": "Türk Ceza Kanunu", "kategori": "⚖️ Ceza Hukuku", "aciklama": "Suçlar ve Ceza Sorumluluğu"},
            {"id": "5271", "kisaAd": "CMK", "isim": "Ceza Muhakemesi Kanunu", "kategori": "⚖️ Ceza Hukuku", "aciklama": "Ceza Soruşturma ve Kovuşturma Usulü"},
            {"id": "5275", "kisaAd": "CGİK", "isim": "Ceza ve Güvenlik Tedbirlerinin İnfazı Hakkında Kanun", "kategori": "⚖️ Ceza Hukuku", "aciklama": "İnfaz Rejimi ve Denetimli Serbestlik"},
            
            # --- ÖZEL HUKUK ---
            {"id": "4721", "kisaAd": "TMK", "isim": "Türk Medeni Kanunu", "kategori": "🏡 Özel Hukuk", "aciklama": "Kişiler, Aile, Miras ve Eşya Hukuku"},
            {"id": "6098", "kisaAd": "TBK", "isim": "Türk Borçlar Kanunu", "kategori": "🏡 Özel Hukuk", "aciklama": "Sözleşmeler ve Haksız Fiil Tazminatı"},
            {"id": "6502", "kisaAd": "TKHK", "isim": "Tüketicinin Korunması Hakkında Kanun", "kategori": "🏡 Özel Hukuk", "aciklama": "Ayıplı Mal ve Tüketici Hakem Heyeti"},
            {"id": "4722", "kisaAd": "TMKYK", "isim": "Türk Medeni Kanununun Yürürlüğü ve Uygulama Şekli Hakkında Kanun", "kategori": "🏡 Özel Hukuk", "aciklama": "Medeni Kanun Geçiş Hükümleri"},
            
            # --- TİCARET & İŞ HUKUKU ---
            {"id": "6102", "kisaAd": "TTK", "isim": "Türk Ticaret Kanunu", "kategori": "💼 Ticaret & İş Hukuku", "aciklama": "Şirketler, Kıymetli Evrak ve Deniz Ticareti"},
            {"id": "4857", "kisaAd": "İK", "isim": "İş Kanunu", "kategori": "💼 Ticaret & İş Hukuku", "aciklama": "İşçi-İşveren İlişkileri ve Kıdem Tazminatı"},
            {"id": "6331", "kisaAd": "İSGK", "isim": "İş Sağlığı ve Güvenliği Kanunu", "kategori": "💼 Ticaret & İş Hukuku", "aciklama": "İş Kazaları ve Önleyici Tedbirler"},
            {"id": "5953", "kisaAd": "BİK", "isim": "Basın İş Kanunu", "kategori": "💼 Ticaret & İş Hukuku", "aciklama": "Gazeteciler ve Basın Çalışanları Hakları"},

            # --- USUL & İCRA HUKUKU ---
            {"id": "6100", "kisaAd": "HMK", "isim": "Hukuk Muhakemeleri Kanunu", "kategori": "🏛️ Usul & İcra Hukuku", "aciklama": "Hukuk Davaları Yargılama Usulü"},
            {"id": "2004", "kisaAd": "İİK", "isim": "İcra ve İflas Kanunu", "kategori": "🏛️ Usul & İcra Hukuku", "aciklama": "İlamsız-İlamlı Takip ve İflas Rejimi"},
            {"id": "1136", "kisaAd": "AK", "isim": "Avukatlık Kanunu", "kategori": "🏛️ Usul & İcra Hukuku", "aciklama": "Avukatlık Meslek Kuralları ve Barolar"},
            {"id": "2575", "kisaAd": "DK", "isim": "Danıştay Kanunu", "kategori": "🏛️ Usul & İcra Hukuku", "aciklama": "Danıştay Organları ve Yargılama Alanı"},
            {"id": "2797", "kisaAd": "YK", "isim": "Yargıtay Kanunu", "kategori": "🏛️ Usul & İcra Hukuku", "aciklama": "Yargıtay Daireleri ve İçtihadı Birleştirme"}
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
        GENİŞLETİLMİŞ X-RAY TARAYICI: 20 kanunun tamamını otomatik olarak teşhis eder 
        ve ZIP dosyasından ilgili Kanun No'yu bularak yerel beynine kazır.
        """
        kanun_id = None
        kisa_ad = None
        
        # 20 Kanunluk Genişletilmiş Akıllı Eşleşme Haritası
        bilinen_kanunlar = {k["id"]: k["kisaAd"] for k in cls.get_kanunlar()}
        
        tum_degerler = list(args) + list(kwargs.values())
        for deger in list(tum_degerler):
            if isinstance(deger, dict):
                tum_degerler.extend(deger.keys())
                tum_degerler.extend(deger.values())
        
        for v in tum_degerler:
            v_str = str(v).strip()
            if v_str in bilinen_kanunlar:
                kanun_id = v_str
                kisa_ad = bilinen_kanunlar[v_str]
                break
            elif v_str in bilinen_kanunlar.values():
                kisa_ad = v_str
                for k, val in bilinen_kanunlar.items():
                    if val == v_str:
                        kanun_id = k
                        break
                break
                
        if not kisa_ad or not kanun_id:
            st.error(f"❌ Kritik Tarama Hatası: Kanun tanınamadı. (Gelen veri: args={args}, kwargs={kwargs})")
            return 0
            
        zip_dosya_adi = "mevzuat_arsiv.zip" 
        ic_dosya_adi = "mevzuat_ham.json"
        
        if not os.path.exists(zip_dosya_adi):
            st.error(f"⚠️ {zip_dosya_adi} bulunamadı! Lütfen arşivi GitHub'a yükleyin.")
            return 0
            
        with st.spinner(f"🧠 {kisa_ad} ({kanun_id}) dev arşivden çıkarılıp Junilex beynine kazınıyor..."):
            try:
                chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
                collection = chroma_client.get_or_create_collection(name="turk_mevzuati")
                embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
                
                with zipfile.ZipFile(zip_dosya_adi, 'r') as z:
                    with z.open(ic_dosya_adi) as f:
                        tum_mevzuat = json.loads(f.read().decode('utf-8'))
                    
                hedef_kanun = None
                for kanun in tum_mevzuat:
                    if str(kanun.get("kanun_numarasi")) == str(kanun_id):
                        hedef_kanun = kanun
                        break
                        
                if not hedef_kanun:
                    st.error(f"❌ {kisa_ad} (Kanun No: {kanun_id}) dev arşivin içinde bulunamadı!")
                    return 0
                    
                maddeler = hedef_kanun.get("maddeler", [])
                if not maddeler:
                    st.error(f"❌ {kisa_ad} bulundu ancak maddeleri boş.")
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
                
                st.success(f"🚀 BAŞARILI! {len(maddeler)} adet {kisa_ad} maddesi Junilex yerel hafızasına alındı.")
                return len(maddeler)
                
            except Exception as e:
                st.error(f"❌ Yükleme hatası: {str(e)}")
                return 0

    @classmethod
    def madde_getir_buluttan(cls, *args, **kwargs):
        """
        Arama motoru da 20 kanunluk geniş havuzda tam uyumlu çalışır.
        """
        try:
            kanun_kisa_ad = kwargs.get("kanun_kisa_ad") or kwargs.get("kanun_kisa_ad_bul") or kwargs.get("kisaAd")
            madde_no_tam = kwargs.get("madde_no_tam") or kwargs.get("madde_no") or kwargs.get("girilen_madde")
            
            tum_degerler = list(args) + list(kwargs.values())
            for deger in list(tum_degerler):
                if isinstance(deger, dict):
                    tum_degerler.extend(deger.values())

            bilinen_kisaltmalar = [k["kisaAd"] for k in cls.get_kanunlar()]
            
            if not kanun_kisa_ad:
                for v in tum_degerler:
                    if str(v).strip() in bilinen_kisaltmalar:
                        kanun_kisa_ad = str(v).strip()
                        break
            
            if not madde_no_tam:
                for v in tum_degerler:
                    v_str = str(v).strip()
                    if v_str != kanun_kisa_ad and (v_str.isdigit() or "GECİCİ" in v_str.upper() or "EK" in v_str.upper()):
                        madde_no_tam = v_str
                        break

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
