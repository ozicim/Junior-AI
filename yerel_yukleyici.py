"""
JUNILEX - Yerel RAG (Vektör) Veritabanı Yükleyici v3
==================================================
Lokal JSON dosyalarındaki mevzuatı ChromaDB'ye vektör olarak işler.
Kullanım: python yerel_yukleyici.py
"""

import json
import chromadb
from sentence_transformers import SentenceTransformer
import os

# 1. Vektör Veritabanı ve Embedding Modeli Kurulumu
print("⏳ Veritabanı ve yapay zeka modeli yükleniyor (Bu biraz sürebilir)...")
chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
collection = chroma_client.get_or_create_collection(name="turk_mevzuati")

# Türkçe metinleri çok iyi anlayan hafif bir model kullanıyoruz
embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def veritabanina_yukle(json_dosya_yolu):
    if not os.path.exists(json_dosya_yolu):
        print(f"❌ HATA: {json_dosya_yolu} bulunamadı!")
        return

    with open(json_dosya_yolu, "r", encoding="utf-8") as f:
        kanun_verisi = json.load(f)

    toplam = len(kanun_verisi)
    print(f"📦 {toplam} adet madde bulundu. Vektörleme başlıyor...")

    # Belleği yormamak için 100'erli paketler (batch) halinde işliyoruz
    batch_size = 100
    for i in range(0, toplam, batch_size):
        batch = kanun_verisi[i:i+batch_size]
        
        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for sira, madde in enumerate(batch):
            # JSON formatınızın "kanun_adi", "madde_no" ve "icerik" içerdiğini varsayıyoruz
            kanun_adi = madde.get("kanun_adi", "Bilinmeyen Kanun")
            madde_no = str(madde.get("madde_no", ""))
            icerik = madde.get("icerik", "")
            
            # Aramalarda kanun adı ve madde numarasını da hesaba katması için birleştiriyoruz
            aranacak_metin = f"{kanun_adi} Madde {madde_no}: {icerik}"
            
            ids.append(f"{kanun_adi.replace(' ', '_')}_{madde_no}_{i+sira}")
            documents.append(icerik)
            metadatas.append({"kanun": kanun_adi, "madde": madde_no})
            embeddings.append(embedding_model.encode(aranacak_metin).tolist())

        collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ {i + len(batch)} / {toplam} madde işlendi...")

    print("🚀 TÜM VERİLER BAŞARIYLA JUNILEX HAFIZASINA EKLENDİ!")

if __name__ == "__main__":
    # Örnek: İndirdiğin JSON dosyasının adını buraya yaz
    # Dosya formatı: [{"kanun_adi": "TCK", "madde_no": "1", "icerik": "..."}]
    ornek_json = "mevzuat_ornek.json" 
    veritabanina_yukle(ornek_json)
