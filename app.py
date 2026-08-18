"""
=============================================================
  Pot Eva Tahmin Sistemi - Streamlit Web Uygulaması
=============================================================
Kullanıcının girdiği kabin ve devre değerlerine göre, önceden
eğitilmiş zincirleme (chained) modelleri kullanarak:
    1) pas sayısı
    2) pot eva boru uzunluk
    3) pot eva levha uzunluğu
değerlerini sırayla tahmin eder.

Güvenlik filtresi: kullanıcı, veri setindeki hiçbir dolapla
(Cabinet code) örtüşmeyen ya da en yakın komşusundan %20'den
fazla sapan değerler girerse tahmin YAPILMAZ; bunun yerine
hangi değişkenin sınırı aştığı gösterilir.
=============================================================
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
import streamlit as st

from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

# ==============================================================
# 0. SAYFA AYARLARI VE STİL
# ==============================================================
st.set_page_config(
    page_title="Pot Eva Tahmin Sistemi",
    page_icon="❄️",
    layout="centered",
)

st.markdown("""
<style>
    .stApp { background-color: #0f172a; }
    h1, h2, h3 { color: #e2e8f0 !important; }
    p, label, .stMarkdown { color: #cbd5e1; }
    div[data-testid="stForm"] {
        background-color: #1e293b;
        padding: 2rem;
        border-radius: 14px;
        border: 1px solid #334155;
    }
    .result-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 0.9rem;
    }
    .result-title { color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .result-value { color: #38bdf8; font-size: 2rem; font-weight: 700; margin-top: 0.2rem; }
    .stButton>button {
        background-color: #0ea5e9;
        color: white;
        border-radius: 10px;
        padding: 0.6rem 1.4rem;
        border: none;
        font-weight: 600;
    }
    .stButton>button:hover { background-color: #0284c7; }
    .reject-box {
        background-color: #3f1d1d;
        border: 1px solid #ef4444;
        border-radius: 12px;
        padding: 1rem 1.4rem;
        color: #fecaca;
    }
</style>
""", unsafe_allow_html=True)

MODEL_DOSYASI = "ideal_eva_zincir_modeller.pkl"
SIRA_DOSYASI = "ideal_eva_zincir_sirasi.pkl"
VERI_DOSYASI = "son_hal_2.xlsx"
SIZINTI_SUTUNLARI = ["pot eva levha alan_çarpılmış"]
TOLERANS = 0.20  # %20 sapma sınırı

HEDEF_ETIKETLERI = {
    "pas sayısı": "Pas Sayısı",
    "pot eva boru uzunluk": "Pot Eva Boru Uzunluğu (m)",
    "pot eva levha uzunluğu": "Pot Eva Levha Uzunluğu (mm)",
}

# ==============================================================
# 1. VERİ VE MODELLERİ YÜKLE (cache'lenir, tekrar tekrar okunmaz)
# ==============================================================
@st.cache_resource
def kaynaklari_yukle():
    egitilmis_zincir = joblib.load(MODEL_DOSYASI)
    chain_sirasi = joblib.load(SIRA_DOSYASI)
    df = pd.read_excel(VERI_DOSYASI)

    X_egitim_ham = df.drop(columns=chain_sirasi)
    sizinti_mevcut = [c for c in SIZINTI_SUTUNLARI if c in X_egitim_ham.columns]
    if sizinti_mevcut:
        X_egitim_ham = X_egitim_ham.drop(columns=sizinti_mevcut)

    return egitilmis_zincir, chain_sirasi, X_egitim_ham


def guvenlik_preprocessor_olustur(X: pd.DataFrame):
    sayisal_sutunlar = X.select_dtypes(include=[np.number]).columns.tolist()
    kategorik_sutunlar = X.select_dtypes(exclude=[np.number]).columns.tolist()

    sayisal_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    kategorik_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    transformers = [("sayisal", sayisal_pipeline, sayisal_sutunlar)]
    if kategorik_sutunlar:
        transformers.append(("kategorik", kategorik_pipeline, kategorik_sutunlar))
    return ColumnTransformer(transformers=transformers)


@st.cache_resource
def guvenlik_preprocessor_hazirla(_X_egitim_ham: pd.DataFrame):
    pre = guvenlik_preprocessor_olustur(_X_egitim_ham)
    pre.fit(_X_egitim_ham)
    return pre


# ==============================================================
# 2. GÜVENLİK KONTROLLÜ ZİNCİRLEME TAHMİN
# ==============================================================
def zincir_tahmin_et(df_yeni, egitilmis_zincir, chain_sirasi, X_egitim_ham, guvenlik_preprocessor):
    girilen_cabinet = df_yeni["Cabinet code"].iloc[0]
    X_filtrelenmis = X_egitim_ham[X_egitim_ham["Cabinet code"] == girilen_cabinet].copy()

    if X_filtrelenmis.empty:
        return {
            "basarili": False,
            "sebep": "cabinet_yok",
            "mesaj": f"Veri setinde '{girilen_cabinet}' koduna sahip dolap bulunmuyor.",
        }

    X_filtrelenmis_scaled = guvenlik_preprocessor.transform(X_filtrelenmis)
    df_yeni_scaled = guvenlik_preprocessor.transform(df_yeni)

    nn = NearestNeighbors(n_neighbors=1)
    nn.fit(X_filtrelenmis_scaled)
    _, indeksler = nn.kneighbors(df_yeni_scaled)
    en_yakin_komsu = X_filtrelenmis.iloc[indeksler[0][0]]
    girilen_degerler = df_yeni.iloc[0]

    sayisal_sutunlar = X_egitim_ham.select_dtypes(include=[np.number]).columns
    sorunlu_degiskenler = []

    for sutun in sayisal_sutunlar:
        yeni_val = float(girilen_degerler[sutun])
        komsu_val = float(en_yakin_komsu[sutun])

        if komsu_val == 0:
            if abs(yeni_val) > 0.01:
                sorunlu_degiskenler.append((sutun, yeni_val, komsu_val, None))
        else:
            yuzdelik_fark = abs(yeni_val - komsu_val) / abs(komsu_val)
            if yuzdelik_fark > TOLERANS:
                sorunlu_degiskenler.append((sutun, yeni_val, komsu_val, yuzdelik_fark * 100))

    if sorunlu_degiskenler:
        return {
            "basarili": False,
            "sebep": "sapma",
            "cabinet": girilen_cabinet,
            "sorunlu_degiskenler": sorunlu_degiskenler,
            "komsu": en_yakin_komsu,
        }

    df_calisma = df_yeni.copy()
    tahminler = {}
    for hedef in chain_sirasi:
        _, pipe = egitilmis_zincir[hedef]
        zincir_girdi_sutunlari = pipe.named_steps["preprocessor"].feature_names_in_
        df_girdi = df_calisma.reindex(columns=zincir_girdi_sutunlari)
        tahmin = pipe.predict(df_girdi)[0]
        tahminler[hedef] = tahmin
        df_calisma[hedef] = tahmin

    return {
        "basarili": True,
        "cabinet": girilen_cabinet,
        "tahminler": tahminler,
        "komsu": en_yakin_komsu,
    }


# ==============================================================
# 3. ARAYÜZ
# ==============================================================
st.title("❄️ Pot Eva Kombinasyon Tahmin Sistemi")
st.write(
    "Kabin ve devre değerlerini gir, sistem eğitilmiş modelleri kullanarak "
    "**pas sayısı**, **pot eva boru uzunluğu** ve **pot eva levha uzunluğu** "
    "değerlerini zincirleme olarak önersin."
)

try:
    egitilmis_zincir, CHAIN_SIRASI, X_egitim_ham = kaynaklari_yukle()
    guvenlik_pre = guvenlik_preprocessor_hazirla(X_egitim_ham)
except FileNotFoundError as e:
    st.error(f"Gerekli dosya bulunamadı: {e}. Model ve veri dosyalarının app.py ile aynı klasörde olduğundan emin ol.")
    st.stop()

cabinet_secenekleri = sorted(X_egitim_ham["Cabinet code"].dropna().unique().tolist())
enerji_secenekleri = sorted(X_egitim_ham["Energy efficiency class (EU_2021_EP)"].dropna().unique().tolist())

with st.form("tahmin_formu"):
    st.subheader("Girdi Değerleri")

    col1, col2 = st.columns(2)
    with col1:
        cabinet_code = st.selectbox("Cabinet code", cabinet_secenekleri)
        charge = st.number_input("Charge (gr)", min_value=0.0, value=60.0, step=1.0)
        capacity = st.number_input("Capacity @max rpm", min_value=0.0, value=190.0, step=1.0)
        boru_capi = st.number_input("Kapileri boru çapı", min_value=0.0, value=0.07, step=0.001, format="%.4f")
    with col2:
        enerji_sinifi = st.selectbox("Energy efficiency class (EU_2021_EP)", enerji_secenekleri)
        boru_uzunlugu = st.number_input("Kapileri boru uzunluğu", min_value=0.0, value=3.5, step=0.1, format="%.2f")
        hacim_fancap = st.number_input("Hacim/fancap", min_value=0.0, value=3.3, step=0.1, format="%.3f")

    gonder = st.form_submit_button("🔍 Tahmin Et")

if gonder:
    df_yeni = pd.DataFrame([{
        "Cabinet code": cabinet_code,
        "Charge (gr)": charge,
        "Energy efficiency class (EU_2021_EP)": enerji_sinifi,
        "capacity @max rpm": capacity,
        "kapileri boru çapı": boru_capi,
        "kapileri boru uzunluğu": boru_uzunlugu,
        "hacim/fancap": hacim_fancap,
    }])
    df_yeni = df_yeni.reindex(columns=X_egitim_ham.columns)

    sonuc = zincir_tahmin_et(df_yeni, egitilmis_zincir, CHAIN_SIRASI, X_egitim_ham, guvenlik_pre)

    st.divider()

    if not sonuc["basarili"]:
        if sonuc["sebep"] == "cabinet_yok":
            st.markdown(f"<div class='reject-box'>❌ <b>Tahmin reddedildi:</b> {sonuc['mesaj']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div class='reject-box'>❌ <b>Tahmin reddedildi (Güvenlik Sınırı Aşıldı)</b><br>"
                f"Girdiğiniz değerler, referans '<b>{sonuc['cabinet']}</b>' dolabına göre "
                f"%{int(TOLERANS*100)}'den fazla sapıyor.</div>",
                unsafe_allow_html=True,
            )
            st.write("")
            satirlar = []
            for hata in sonuc["sorunlu_degiskenler"]:
                sutun, yeni_val, komsu_val, fark = hata
                satirlar.append({
                    "Değişken": sutun,
                    "Girilen Değer": round(yeni_val, 3),
                    "En Yakın Komşu": round(komsu_val, 3),
                    "Fark (%)": round(fark, 1) if fark is not None else "—",
                })
            st.dataframe(pd.DataFrame(satirlar), hide_index=True, use_container_width=True)
            st.caption("İpucu: Bu değerleri en yakın komşuya daha yakın girerek tekrar deneyebilirsin.")
    else:
        st.success(f"✅ Veri onaylandı (Değerler '{sonuc['cabinet']}' dolaplarına uyumlu). Tahmin tamamlandı.")
        st.write("")

        for hedef in CHAIN_SIRASI:
            deger = sonuc["tahminler"][hedef]
            etiket = HEDEF_ETIKETLERI.get(hedef, hedef)
            st.markdown(f"""
            <div class="result-card">
                <div class="result-title">{etiket}</div>
                <div class="result-value">{deger:.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("🔎 Referans alınan en yakın komşu ile karşılaştırma"):
            karsilastirma = pd.DataFrame({
                "Girdiğin Değer": df_yeni.iloc[0],
                "En Yakın Komşu": sonuc["komsu"],
            })
            st.dataframe(karsilastirma, use_container_width=True)

st.divider()
st.caption(
    "Model: Zincirleme (chained) regresyon — her hedef bir öncekinin tahminini girdi olarak kullanır. "
    "Güvenlik filtresi: aynı Cabinet code grubundaki en yakın komşudan %20'den fazla sapan girdiler reddedilir."
)
