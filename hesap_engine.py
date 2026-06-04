from datetime import date

class HesapEngine:
    @staticmethod
    def smm_hesapla(tutar, hesap_tipi="Netten Brüte (KDV Hariç Anlaşma)", tevkifat_var=False):
        """
        KDV ve Stopaj oranları güncel %20 seviyesindedir. 
        Tevkifat opsiyonu eklendi.
        """
        kdv_orani = 0.20
        stopaj_orani = 0.20
        tevkifat_orani = 0.50 if tevkifat_var else 0 # 5/10 tevkifat
        
        if hesap_tipi == "Netten Brüte (KDV Hariç Anlaşma)":
            # Net ücret üzerinden brüte gidiliyor
            brut = tutar / (1 - stopaj_orani)
        else:
            brut = tutar
            
        kdv = brut * kdv_orani
        stopaj = brut * stopaj_orani
        
        # Tevkifat varsa KDV'den kesilir
        kdv_tevkifat = kdv * tevkifat_orani
        odenecek_kdv = kdv - kdv_tevkifat
        
        tahsil_edilen = brut - stopaj + odenecek_kdv
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
        fark = bitis_tarihi - baslangic_tarihi
        gun_sayisi = fark.days
        
        if gun_sayisi < 0:
            return 0, 0, 0 
        
        # Faiz tutarı = (Anapara * Faiz Oranı * Gün) / 36500
        faiz_tutari = (anapara * faiz_orani * gun_sayisi) / 36500
        toplam_tutar = anapara + faiz_tutari
        
        return gun_sayisi, round(faiz_tutari, 2), round(toplam_tutar, 2)

    @staticmethod
    def iscil_alacaklar_hesapla(brut_maas, kidem_tavani, ise_giris, isten_cikis):
        # Sabit kesinti oranları
        DAMGA_VERGISI = 0.00759
        GELIR_VERGISI = 0.15
        
        fark = isten_cikis - ise_giris
        toplam_gun = fark.days
        
        if toplam_gun < 0:
            return {"Hata": "Tarihleri kontrol edin."}

        # Kıdem Hesabı
        if toplam_gun < 365:
            kidem_net = 0
        else:
            hesaba_esas_ucret = min(brut_maas, kidem_tavani)
            kidem_brut = (hesaba_esas_ucret / 365) * toplam_gun
            kidem_net = kidem_brut - (kidem_brut * DAMGA_VERGISI)

        # İhbar Süresi (Hafta)
        if toplam_gun < 180: ihbar_hafta = 2
        elif toplam_gun < 540: ihbar_hafta = 4
        elif toplam_gun < 1095: ihbar_hafta = 6
        else: ihbar_hafta = 8

        ihbar_brut = (brut_maas / 30) * (ihbar_hafta * 7)
        ihbar_net = ihbar_brut - (ihbar_brut * GELIR_VERGISI) - (ihbar_brut * DAMGA_VERGISI)

        return {
            "Kıdem Net": round(kidem_net, 2),
            "İhbar Net": round(ihbar_net, 2),
            "İhbar Süresi (Hafta)": ihbar_hafta,
            "Çalışılan Gün": toplam_gun
        }

    @staticmethod
    def nispi_harc_hesapla(dava_degeri):
        # 2024 Harçlar Kanunu güncel oranı
        toplam_harc = dava_degeri * 0.06831
        pesin_harc = toplam_harc / 4
        return round(toplam_harc, 2), round(pesin_harc, 2)

    @staticmethod
    def kademeli_tarife_hesapla(tutar, dilimler):
        kalan_tutar = tutar
        toplam_ucret = 0
        hesap_detayi = []

        for dilim in dilimler:
            limit = dilim["limit"]
            oran = dilim["oran"]

            if limit is None or kalan_tutar <= limit:
                uygulanan = kalan_tutar
            else:
                uygulanan = limit

            ucret = uygulanan * oran
            toplam_ucret += ucret
            hesap_detayi.append(f"₺{uygulanan:,.2f} x %{oran*100:.0f} = ₺{ucret:,.2f}")

            kalan_tutar -= uygulanan
            if kalan_tutar <= 0:
                break

        return round(toplam_ucret, 2), hesap_detayi
