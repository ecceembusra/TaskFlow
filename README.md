# TaskFlow
TaskFlow is a lightweight web-based Kanban board built with Streamlit and SQLite.  It allows users to manage tasks with WIP limits, deadlines, tags, and multiple projects.

# 🗂️ TaskFlow — Web Kanban Uygulaması

**TaskFlow**, görev ve iş takibini kolaylaştırmak için geliştirilmiş,  
**Streamlit** ve **SQLite** kullanılarak oluşturulmuş **web tabanlı bir Kanban uygulamasıdır**.

Uygulama; görevleri **Backlog**, **Doing** ve **Done** aşamalarında yönetmeyi sağlar ve
gerçek hayatta kullanılabilecek bir yapı sunar. Aynı zamanda portföy amaçlı güçlü bir demo projedir.

---

## 🚀 Canlı Demo

🔗 **Uygulama Linki:**  
https://taskflow-sayzx2piagjssu2767vbzd.streamlit.app/  
*(Streamlit Community Cloud üzerinde deploy edilmiştir)*

> Linke sahip olan herkes uygulamayı görüntüleyebilir. Giriş gerekmez.

---

## ✨ Özellikler

- 📌 **Kanban Board**: Backlog / Doing / Done kolonları
- ➕ Görev ekleme, düzenleme ve silme (CRUD)
- 🏷️ Etiket (tag) desteği
- 🔢 Öncelik seviyesi (1–5)
- 📅 Bitiş tarihi (due date)
- 🔍 Başlık ve açıklama üzerinden arama
- 🎯 WIP (Work In Progress) limiti
- 💾 SQLite ile kalıcı veri saklama
- 📤 Filtrelenmiş görevleri CSV olarak dışa aktarma
- 📝 Proje adını sidebar üzerinden yeniden adlandırma
- 🌐 Web üzerinden paylaşılabilir yapı

---

## 🧠 Proje Yapısı
```bash
taskflow-kanban/
├── app.py               # Ana Streamlit uygulaması
├── tasks.db             # SQLite veritabanı (uygulama çalışınca otomatik oluşur)
├── requirements.txt     # Python bağımlılıkları
└── README.md            # Proje dokümantasyonu
```

---

## 🛠️ Kullanılan Teknolojiler

- *Python*
- *Streamlit*
- *SQLite*
- *Pandas*

---

## ⚙️ Kurulum ve Lokal Çalıştırma

Repository’yi klonla:
```bash
git clone https://github.com/ecembusra/taskflow-kanban.git
cd taskflow-kanban
```

## ⚙️ Kurulum ve Lokal Çalıştırma

Repository’yi klonla:
```bash
git clone https://github.com/ecembusra/taskflow-kanban.git
cd taskflow-kanban
```

(Senaryo önerisi) Sanal ortam oluştur
``` bash
python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate      # Windows
```

Bağımlılıkları yükle:
``` bash
pip install -r requirements.txt
```

Uygulamayı çalıştır:
```
streamlit run app.py
```
🔐 Çok Kullanıcılı Demo Notu

Bu uygulama şu anda paylaşımlı bir demo ortamı olarak çalışmaktadır:
	•	Tüm kullanıcılar aynı görevleri görür
	•	Yapılan değişiklikler herkes için geçerlidir

Bu yapı bilinçli olarak demo amaçlı tercih edilmiştir.
İleride kullanıcı bazlı yetkilendirme ve özel board’lar eklenebilir.
