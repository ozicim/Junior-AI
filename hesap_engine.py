from datetime import date

class HesapEngine:
    @staticmethod
    def smm_hesapla(tutar, hesap_tipi="Netten Brüte (KDV Hariç Anlaşma)"):
        """
        Avukatlık Serbest Meslek Makbuzu (SMM) Hesaplar.
        Güncel oranlar: KDV %20, Stopaj %20
        """
        kdv_orani = 0.20
        stopaj_orani = 0.20
        
        if hesap_tipi == "Netten Brüte (KDV Hariç Anlaşma)":
            # Avukat cebine girecek NET tutarı belirlemişse
            brut = tutar / (1 - stopaj_orani)
            kdv = brut * kdv_orani
            stopaj = brut * stopaj_orani
            tahsil_edilen = brut - stopaj + kdv
        else:
            # Müvekkille brüt tutar üzerinden anlaşıldıysa
            brut = tutar
            kdv = brut * kdv_orani
            stopaj = brut * stopaj_orani
            tahsil_edilen = brut - stopaj + kdv
            
        net_ucret = brut - stopaj
            
        return {
            "Brüt Ücret": round(brut, 2),
            "KDV (%20)": round(kdv, 2),
            "Stopaj (%20)": round(stopaj, 2),
            "Avukata Kalan Net": round(net_ucret, 2),
            "Müvekkilden Tahsil Edilecek Toplam (Net + KDV)": round(tahsil_edilen, 2)
        }

    @staticmethod
    def faiz_hesapla(anapara, faiz_orani, baslangic_tarihi, bitis_tarihi):
        """
        Basit faiz mantığıyla gün bazlı gecikme faizi hesaplar.
        Formül: (Anapara * Faiz Oranı * Gün) / 36500
        """
        fark = bitis_tarihi - baslangic_tarihi
        gun_sayisi = fark.days
        
        if gun_sayisi < 0:
            return 0, 0, 0 # Tarih hatası
        
        faiz_tutari = (anapara * faiz_orani * gun_sayisi) / 36500
        toplam_tutar = anapara + faiz_tutari
        
        return gun_sayisi, round(faiz_tutari, 2), round(toplam_tutar, 2)
