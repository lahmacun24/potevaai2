# ❄️ Pot Eva Tahmin Sistemi

Kullanıcının girdiği kabin/devre değerlerine göre, önceden eğitilmiş
zincirleme (chained) makine öğrenmesi modelleriyle şu üç değeri sırayla
tahmin eden bir Streamlit web uygulaması:

1. **Pas sayısı**
2. **Pot eva boru uzunluğu**
3. **Pot eva levha uzunluğu**

Güvenlik filtresi aktiftir: kullanıcı, veri setinde bulunmayan bir
`Cabinet code` girerse ya da girdiği sayısal değerler kendi grubundaki
en yakın komşudan **%20'den fazla** sapıyorsa tahmin **reddedilir** ve
hangi değişkenin sınırı aştığı ekranda gösterilir.

---

## 📁 Klasördeki Dosyalar

```
pot_eva_app/
├── app.py                          # Streamlit uygulaması
├── requirements.txt                # Python bağımlılıkları
├── ideal_eva_zincir_modeller.pkl   # Eğitilmiş modeller
├── ideal_eva_zincir_sirasi.pkl     # Zincir sırası
└── son_hal_2.xlsx                  # Referans veri (güvenlik filtresi için)
```

Bu 5 dosyanın **hepsi aynı klasörde** olmalı; app.py diğer dosyaları
göreli yoldan (relative path) okuyor.

---

## 🖥️ Bilgisayarında Çalıştırma (Test İçin)

```bash
cd pot_eva_app
pip install -r requirements.txt
streamlit run app.py
```

Tarayıcıda otomatik olarak `http://localhost:8501` açılır.

---

## 🌍 Ücretsiz Yayınlama (Streamlit Community Cloud)

Böylece uygulama gerçek bir internet adresine (`.streamlit.app`) sahip
olur, herkes tarayıcıdan erişebilir.

1. **GitHub'da yeni bir repo aç** (örn. `pot-eva-tahmin`) ve bu klasördeki
   5 dosyayı repoya yükle.
   > ⚠️ `son_hal_2.xlsx` (~33 MB) GitHub'a yüklenebilir ama repo'yu
   > "public" yapmak istemiyorsan Streamlit Cloud'un ücretsiz planında
   > private repo bağlamak da mümkün (GitHub hesabı ile giriş yaptığında
   > seçenek çıkar).
2. [share.streamlit.io](https://share.streamlit.io) adresine git, GitHub
   hesabınla giriş yap.
3. **"New app"** butonuna tıkla, repo'yu ve `app.py` dosyasını seç.
4. **Deploy** butonuna bas — birkaç dakika içinde site linkin hazır olur.

Alternatif olarak Hugging Face Spaces (Streamlit SDK) veya Render.com
üzerinden de aynı şekilde yayınlanabilir; adımlar neredeyse birebir aynı.

---

## 🔄 Modelleri Güncellemek İstersen

Eğer veri setine yeni satırlar eklenip modelleri yeniden eğitmek
istersen, elindeki eğitim kodunu (chained pipeline, LOO-CV) tekrar
çalıştırıp yeni `ideal_eva_zincir_modeller.pkl` ve
`ideal_eva_zincir_sirasi.pkl` dosyalarını bu klasördeki eskilerinin
üzerine kopyalaman yeterli — `app.py`'de hiçbir değişiklik gerekmez.

**Not:** Modeller `scikit-learn==1.6.1` ile eğitildi. Yeniden eğitim
yaparken de aynı sürümü kullan, aksi halde `requirements.txt`'teki
sürümle uyumsuzluk (unpickle hatası) yaşanabilir.

---

## ⚙️ Girdi Alanları

| Alan | Açıklama |
|---|---|
| Cabinet code | 9 seçenek (D70, D78, D83, G83, K60, K70, K74, K78, K83) |
| Charge (gr) | Sayısal |
| Energy efficiency class | C / D / E / F |
| Capacity @max rpm | Sayısal |
| Kapileri boru çapı | Sayısal (ör. 0.066–0.08 arası) |
| Kapileri boru uzunluğu | Sayısal |
| Hacim/fancap | Sayısal |

Bu 7 alan, eğitimde kullanılan girdi (feature) setiyle birebir aynıdır.
