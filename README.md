# UTS Machine Learning — Klasifikasi Kepribadian Extrovert & Introvert

**Klasifikasi Potensi Kepribadian Ekstrovert dan Introvert Berdasarkan Pola Interaksi Sosial Harian Menggunakan Algoritma Random Forest**

Proyek UTS Pembelajaran Mesin yang mengklasifikasikan kepribadian seseorang (*Extrovert* vs *Introvert*) berdasarkan 7 fitur pola interaksi sosial harian menggunakan algoritma **Random Forest**.

---

## Struktur Proyek

```
UTS-MachineLearning-Diaz/
├── app/
│   ├── app.py                  # Flask backend
│   ├── templates/
│   │   └── index.html          # Halaman utama
│   └── static/
│       ├── css/style.css       # Stylesheet
│       └── js/app.js           # JavaScript (GSAP, Chart.js, Lenis)
├── dataset/
│   └── personality_datasert.csv  # Dataset Kaggle
├── model/
│   ├── personality_rf_model.pkl  # Pipeline model tersimpan
│   └── model_metadata.json       # Metadata model & fitur
├── notebooks/
│   └── train_personality_rf.ipynb  # Notebook training (Colab-ready)
├── requirements.txt
└── README.md
```

## Menjalankan Secara Lokal

```bash
# 1. Clone repositori
git clone https://github.com/diazdynsa/UTS-MachineLearning-Diaz.git
cd UTS-MachineLearning-Diaz

# 2. Buat virtual environment
python -m venv venv
source venv/bin/activate    # Linux/macOS
venv\Scripts\activate       # Windows

# 3. Install dependensi
pip install -r requirements.txt

# 4. Jalankan aplikasi
cd app
python app.py
# Buka http://localhost:5000 di browser
```

## Training di Google Colab

1. Buka notebook: [`notebooks/train_personality_rf.ipynb`](notebooks/train_personality_rf.ipynb)
2. Klik tombol **"Open in Colab"** atau upload manual ke Google Colab
3. Upload dataset `dataset/personality_datasert.csv` saat diminta
4. Jalankan seluruh cell — model dan metadata akan tersimpan di folder `model/`

## Deployment

### A. Deploy ke Vercel (Serverless)

Proyek ini sudah dilengkapi konfigurasi serverless [`vercel.json`](vercel.json) dan entrypoint [`api/index.py`](api/index.py):

1. Install Vercel CLI atau sambungkan repositori GitHub langsung melalui dashboard [Vercel](https://vercel.com).
2. Import project `UTS-MachineLearning-Diaz`.
3. Vercel akan otomatis mengenali `vercel.json` dan membangun serverless function menggunakan runtime Python.
4. Klik **Deploy**.

> **Catatan:** Vercel memiliki batas ukuran serverless function (250 MB uncompressed). Jika terjadi batasan ukuran package ML saat build di akun free tier, gunakan platform PaaS (Render / Railway) di bawah ini.

### B. Deploy ke Render / Railway (PaaS Container)

1. Push repositori ke GitHub
2. Buat **Web Service** baru di [Render](https://render.com) atau [Railway](https://railway.app)
3. Konfigurasi:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `cd app && gunicorn app:app --bind 0.0.0.0:$PORT`
4. Health check endpoint: `GET /health`

## Dataset

Dataset: [Extrovert vs Introvert Behavior Data](https://www.kaggle.com/datasets/rakeshkapilavai/extrovert-vs-introvert-behavior-data) dari Kaggle (`personality_datasert.csv`) — 2900 sampel, 7 fitur pola interaksi sosial harian:

| Fitur | Tipe | Deskripsi |
|---|---|---|
| `Time_spent_Alone` | Numerik (0–11) | Jam waktu menyendiri per hari |
| `Stage_fear` | Kategorikal (Yes/No) | Rasa cemas tampil di depan umum |
| `Social_event_attendance` | Numerik (0–10) | Frekuensi kehadiran acara sosial |
| `Going_outside` | Numerik (0–7) | Frekuensi keluar rumah per minggu |
| `Drained_after_socializing` | Kategorikal (Yes/No) | Rasa lelah setelah bersosialisasi |
| `Friends_circle_size` | Numerik (0–15) | Jumlah lingkaran pertemanan dekat |
| `Post_frequency` | Numerik (0–10) | Frekuensi unggahan media sosial |

## Metrik Model

| Metrik | Nilai |
|---|---|
| Accuracy | 91.2% |
| Precision | 91.0% |
| Recall | 93.6% |
| F1-Score | 92.3% |

## Lisensi

Proyek ini dibuat untuk keperluan UTS Pembelajaran Mesin.
