import random
import threading
from firebase_admin import firestore

class AgEngine:
    @staticmethod
    def kisi_ara(db_json, aranan_id):
        """JSON veritabanında ID'ye göre kullanıcı arar."""
        for mail, data in db_json.items():
            if data.get("id") == aranan_id:
                return mail, data.get("isim")
        return None, None

    @staticmethod
    def arkadaslik_istegi_gonder(db_json, gonderen_mail, alan_mail):
        """Karşı tarafın gelen_istekler listesine göndereni ekler."""
        db_json[alan_mail].setdefault("gelen_istekler", []).append(gonderen_mail)
        return db_json

    @staticmethod
    def istek_kabul_et(db_json, benim_mailim, karsi_mail):
        """İsteği kabul eder ve karşılıklı arkadaş olarak ekler."""
        db_json[benim_mailim].setdefault("arkadaslar", []).append(karsi_mail)
        db_json[karsi_mail].setdefault("arkadaslar", []).append(benim_mailim)
        if karsi_mail in db_json[benim_mailim].get("gelen_istekler", []):
            db_json[benim_mailim]["gelen_istekler"].remove(karsi_mail)
        return db_json

    @staticmethod
    def istek_reddet(db_json, benim_mailim, karsi_mail):
        """Gelen isteği listeden siler."""
        if karsi_mail in db_json[benim_mailim].get("gelen_istekler", []):
            db_json[benim_mailim]["gelen_istekler"].remove(karsi_mail)
        return db_json

    @staticmethod
    def arkadas_cikar(db_json, benim_mailim, karsi_mail):
        """Karşılıklı olarak arkadaş listelerinden çıkarır."""
        if karsi_mail in db_json[benim_mailim].get("arkadaslar", []):
            db_json[benim_mailim]["arkadaslar"].remove(karsi_mail)
        if benim_mailim in db_json.get(karsi_mail, {}).get("arkadaslar", []):
            db_json[karsi_mail]["arkadaslar"].remove(benim_mailim)
        return db_json

    @staticmethod
    def ekip_kur(db_fs, ekip_adi, kurucu_mail, kurucu_isim):
        """Yeni bir ekip kurup Firestore'a kaydeder."""
        ekip_id = "#E-" + str(random.randint(10000, 99999))
        db_fs.collection("junilex_ekipler").add({
            "isim": ekip_adi, 
            "ekip_id": ekip_id,
            "kurucu": kurucu_mail,
            "uyeler_mail": [kurucu_mail],
            "uyeler_isim": [kurucu_isim],
            "istekler": []
        })
        return ekip_id

    @staticmethod
    def ekibe_katilma_istegi_gonder(db_fs, girilen_ekip_id, benim_mailim):
        """Ekip ID'sine göre ekibi bulup istek atar. Bulunursa True döner."""
        ekip_sorgu = db_fs.collection("junilex_ekipler").where("ekip_id", "==", girilen_ekip_id).stream()
        bulundu = False
        for doc in ekip_sorgu:
            doc.reference.update({"istekler": firestore.ArrayUnion([benim_mailim])})
            bulundu = True
        return bulundu

    @staticmethod
    def ekip_istek_onayla(doc_ref, istek_mail, istek_isim):
        """Kurucunun onayladığı kişiyi ekibe katar."""
        doc_ref.update({
            "uyeler_mail": firestore.ArrayUnion([istek_mail]),
            "uyeler_isim": firestore.ArrayUnion([istek_isim]),
            "istekler": firestore.ArrayRemove([istek_mail])
        })

    @staticmethod
    def ekiplerimi_getir(db_fs, benim_mailim):
        """Kullanıcının üye olduğu ekiplerin dokümanlarını döner."""
        return list(db_fs.collection("junilex_ekipler").where("uyeler_mail", "array_contains", benim_mailim).stream())

    @staticmethod
    def ekip_ortak_arsiv_getir(db_fs, sorgu_isimleri):
        """Ekip üyelerinin arşive kaydettiği belgeleri getirir."""
        if not sorgu_isimleri: return []
        sorgu = db_fs.collection("junilex_arsiv").where("kullanici", "in", sorgu_isimleri).order_by("tarih", direction=firestore.Query.DESCENDING).limit(50).stream()
        return list(sorgu)

    @staticmethod
    def sohbet_mesajlarini_getir(db_fs, aktif_ekip_id):
        """Belirli bir ekibin mesaj geçmişini tarihe göre sıralı getirir."""
        sorgu = db_fs.collection("junilex_ekip_sohbet").where("ekip_id", "==", aktif_ekip_id).order_by("tarih", direction=firestore.Query.ASCENDING).limit(100).stream()
        return [m.to_dict() for m in sorgu]

    @staticmethod
    def arka_planda_mesaj_gonder(ekip_id, isim, mesaj):
        """Mesajı arayüzü kitlemeden arka planda (Thread) Firebase'e yollar."""
        def gonder_thread():
            try:
                import firebase_admin
                from firebase_admin import firestore as thread_fs
                if not firebase_admin._apps:
                    firebase_admin.initialize_app()
                db_thread = thread_fs.client()
                db_thread.collection("junilex_ekip_sohbet").add({
                    "ekip_id": ekip_id,
                    "isim": isim,
                    "mesaj": mesaj,
                    "tarih": thread_fs.SERVER_TIMESTAMP
                })
            except Exception:
                pass
        
        threading.Thread(target=gonder_thread).start()
    @staticmethod
    def gorev_ekle(db_fs, ekip_id, baslik, aciklama, atanan_kisi, olusturan):
        """Yeni bir görevi veya duruşmayı veritabanına ekler."""
        db_fs.collection("junilex_gorevler").add({
            "ekip_id": ekip_id,
            "baslik": baslik,
             "aciklama": aciklama,
            "atanan": atanan_kisi,
            "olusturan": olusturan,
            "durum": "Yapılacak", # Başlangıç durumu
            "tarih": firestore.SERVER_TIMESTAMP
        })
    
    @staticmethod
    def gorevleri_getir(db_fs, ekip_id):
        """Ekibe ait görevleri ID'leri ile birlikte getirir."""
        sorgu = db_fs.collection("junilex_gorevler").where("ekip_id", "==", ekip_id).order_by("tarih", direction=firestore.Query.DESCENDING).stream()
        return [{"id": d.id, **d.to_dict()} for d in sorgu]
    
    @staticmethod
    def gorev_durumu_guncelle(db_fs, gorev_id, yeni_durum):
        """Görevi Yapılacak -> Devam Ediyor -> Tamamlandı olarak kaydırır."""
        db_fs.collection("junilex_gorevler").document(gorev_id).update({"durum": yeni_durum})
            
    @staticmethod
    def gorev_sil(db_fs, gorev_id):
        """İptal edilen veya biten görevi tamamen siler."""
        db_fs.collection("junilex_gorevler").document(gorev_id).delete()
