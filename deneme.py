import streamlit as st
import plotly.express as px
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Vodafone Şikayetleri", layout="wide")
st.title("Vodafone Şikayetleri")

# --- 2. VERİ ÇEKME FONKSİYONU (5 Sayfa = Yaklaşık 150 Şikayet) ---
@st.cache_data(ttl=3600)
def veri_topla(sayfa_sayisi=5):
    tum_sikayetler = []
    for i in range(1, sayfa_sayisi + 1):
        url = "https://www.sikayetvar.com/vodafone" if i == 1 else f"https://www.sikayetvar.com/vodafone?page={i}"
        headers = {"User-Agent": "Mozilla/5.0"}
        cevap = requests.get(url, headers=headers)
        
        if cevap.status_code == 200:
            sayfa = BeautifulSoup(cevap.text, "html.parser")
            basliklar = sayfa.find_all(class_="complaint-title")
            tum_sikayetler.extend([b.text.strip() for b in basliklar])
        time.sleep(1)
    return tum_sikayetler

# --- 3. KATEGORİZE ETME ---
def kategorize_et(liste):
    kategoriler = {"Fatura ve Ücret": [], "İnternet ve Çekim": [], "Müşteri Hizmetleri": [], "Diğer": []}
    for s in liste:
        s_low = s.lower()
        if "fatura" in s_low or "ücret" in s_low or "borç" in s_low or "tl" in s_low:
            kategoriler["Fatura ve Ücret"].append(s)
        elif "internet" in s_low or "çekmi" in s_low or "hız" in s_low or "hat" in s_low or "şebeke" in s_low:
            kategoriler["İnternet ve Çekim"].append(s)
        elif "müşteri" in s_low or "temsilci" in s_low or "saygı" in s_low or "iptal" in s_low:
            kategoriler["Müşteri Hizmetleri"].append(s)
        else:
            kategoriler["Diğer"].append(s)
    return kategoriler

# --- 4. UYGULAMA AKIŞI ---
try:
    with st.spinner('İnternetten veriler toplanıyor, bu işlem birkaç saniye sürebilir...'):
        ham_veriler = veri_topla()
        
    siniflandirilmis = kategorize_et(ham_veriler)

    ozet_tablo = pd.DataFrame({
        "Kategori": siniflandirilmis.keys(),
        "Sayı": [len(v) for v in siniflandirilmis.values()]
    })

    # ANA GRAFİK VE TIKLAMA (Seçim) ÖZELLİĞİ
    st.markdown("### 👆 Şikayetleri okumak için grafikteki renkli sütunların üzerine tıklayın!")
    
    fig = px.bar(ozet_tablo, x="Kategori", y="Sayı", color="Kategori",
                 text_auto=True, template="plotly_dark")
    
    # on_select="rerun" ile grafiği tıklanabilir yapıyoruz
    grafik_olayi = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    st.divider()
    
    if grafik_olayi and "selection" in grafik_olayi and grafik_olayi["selection"]["points"]:
        secilen_kategori = grafik_olayi["selection"]["points"][0]["x"]
        
        st.subheader(f"📍 {secilen_kategori} Kategorisindeki Şikayetler ({len(siniflandirilmis[secilen_kategori])} adet)")
        st.caption("Detayını görmek istediğiniz şikayetin üzerine tıklayın.")
        
        for i, sikayet in enumerate(siniflandirilmis[secilen_kategori]):
            kutu_basligi = f"{i+1}. {sikayet[:60]}..." if len(sikayet) > 60 else f"{i+1}. {sikayet}"
            with st.expander(kutu_basligi):
                st.write(f"**Tam Şikayet Metni:** {sikayet}")
    else:
        st.info("Bekleniyor... Şikayetleri görmek için yukarıdaki grafikten bir sütuna tıklayın.")

except Exception as e:
    st.error(f"Bir hata oluştu: {e}")
