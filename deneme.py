import re
import streamlit as st
import plotly.express as px
import pandas as pd
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Vodafone Şikayet Analizi", layout="wide")
st.title("📊 Vodafone Şikayet Analizi")

# --- 2. VERİ ÇEKME FONKSİYONU (5 Sayfa = Yaklaşık 120 Şikayet) ---
@st.cache_data(ttl=3600)
def veri_topla(sayfa_sayisi=5):
    tum_sikayetler = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for i in range(1, sayfa_sayisi + 1):
        url = "https://www.sikayetvar.com/vodafone" if i == 1 else f"https://www.sikayetvar.com/vodafone?page={i}"
        cevap = requests.get(url, headers=headers, timeout=20)

        if cevap.status_code != 200:
            continue

        sayfa = BeautifulSoup(cevap.text, "html.parser")
        artikeller = sayfa.select("article.card-v2")

        for a in artikeller:
            title_tag = a.select_one(".complaint-title a")
            desc_tag = a.select_one(".complaint-description")
            user_tag = a.select_one(".username")
            time_tag = a.select_one(".post-time .time")
            view_tag = a.select_one(".js-view-count")

            if not title_tag:
                continue

            title = title_tag.text.strip()
            link = title_tag.get("href", "").strip()
            full_url = f"https://www.sikayetvar.com{link}" if link.startswith("/") else link
            body = desc_tag.get_text(separator=" ", strip=True) if desc_tag else ""
            body = body.replace("...", "").strip()
            user = user_tag.text.strip() if user_tag else ""
            date = time_tag.get("title", time_tag.text.strip()) if time_tag else ""

            view_text = view_tag.text.strip() if view_tag else ""
            view_digits = re.sub(r"[^0-9]", "", view_text)
            view_count = int(view_digits) if view_digits else 0
            interaction = view_count if view_count > 0 else max(len(body) // 10, 1)

            sentiment = TextBlob(body).sentiment if body else TextBlob("").sentiment
            polarity = round(sentiment.polarity, 4)
            subjectivity = round(sentiment.subjectivity, 4)
            sentiment_label = "Pozitif" if polarity > 0.1 else "Negatif" if polarity < -0.1 else "Nötr"

            tum_sikayetler.append({
                "Başlık": title,
                "Metin": body,
                "Tarih": date,
                "Kullanıcı": user,
                "URL": full_url,
                "Kategori": kategori_tespit(body),
                "Etkileşim": interaction,
                "Polarity": polarity,
                "Subjectivity": subjectivity,
                "Sentiment": sentiment_label,
            })

        time.sleep(1)

    return pd.DataFrame(tum_sikayetler)

# --- 3. KATEGORİ TESPİTİ ---
def kategori_tespit(metin):
    s = metin.lower()
    if any(kelime in s for kelime in ["fatura", "ücret", "borç", "tl", "faturalı", "faturasız", "tarife"]):
        return "Fatura ve Ücret"
    if any(kelime in s for kelime in ["internet", "çekim", "hız", "şebeke", "sinyal", "bağlantı", "mobil", "kapalı"]):
        return "İnternet ve Çekim"
    if any(kelime in s for kelime in ["müşteri", "temsilci", "destek", "iptal", "abonelik", "başvuru", "çağrı"]):
        return "Müşteri Hizmetleri"
    return "Diğer"

# --- 4. UYGULAMA AKIŞI ---
try:
    with st.spinner('İnternetten veriler toplanıyor, bu işlem birkaç saniye sürebilir...'):
        df = veri_topla()

    if df.empty:
        st.warning("Şu anda veri bulunamadı. Lütfen internet bağlantınızı kontrol edin veya daha sonra tekrar deneyin.")
    else:
        df["Kategori"] = df["Kategori"].fillna("Diğer")

        st.markdown("### 📌 Gerçek Vodafone Şikayetleri ve TextBlob Analizi")

        kategori_ozet = df["Kategori"].value_counts().reset_index(name="Sayı")
        sentiment_ozet = df["Sentiment"].value_counts().reset_index(name="Sayı")
        top_interaction = df.sort_values(by="Etkileşim", ascending=False).head(5)

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown("#### Kategori Bazlı Şikayetler")
            fig = px.bar(kategori_ozet, x="Kategori", y="Sayı", color="Kategori",
                         text_auto=True, template="plotly_dark")
            st.plotly_chart(fig, width='stretch')

            st.markdown("#### Kategoriye Göre Şikayet Listesi")
            secilen_kategori = st.selectbox("İncelemek için bir kategori seçin:", kategori_ozet["Kategori"].tolist())
            fil_df = df[df["Kategori"] == secilen_kategori].reset_index(drop=True)

            st.write(f"{secilen_kategori} kategorisinde toplam {len(fil_df)} şikayet bulundu.")
            for idx, row in fil_df.head(20).iterrows():
                with st.expander(f"{idx + 1}. {row['Başlık'][:90]}"):
                    st.write(row["Metin"])
                    st.write(f"**Etkileşim:** {row['Etkileşim']}  |  **Duygu:** {row['Sentiment']}  |  **Tarih:** {row['Tarih']}")
                    st.write(row["URL"])

        with col2:
            st.markdown("#### 🔥 En Çok Etkileşim Alan Şikayetler")
            st.table(top_interaction[["Başlık", "Kategori", "Etkileşim", "Sentiment"]].rename(columns={"Başlık": "Şikayet", "Etkileşim": "Etkileşim"}))

            st.markdown("#### 📈 Sentiment Dağılımı")
            st.bar_chart(sentiment_ozet.set_index("Duygu"), width='stretch')

        st.markdown("### 📋 Tüm Çekilen Şikayetler")
        st.dataframe(df[["Tarih", "Kullanıcı", "Başlık", "Metin", "Kategori", "Etkileşim", "Sentiment", "Polarity", "Subjectivity", "URL"]], width='stretch')

except Exception as e:
    st.error(f"Bir hata oluştu: {e}")
