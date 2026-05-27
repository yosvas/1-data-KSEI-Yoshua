# KSEI Ownership Dashboard — Panduan Distribusi

## Cara Menjalankan (Target Komputer)

1. **Ekstrak** folder `KSEI_Dashboard.zip` ke lokasi mana saja
2. **Double-click** `KSEI_Dashboard.exe`
3. Browser akan terbuka otomatis ke `http://localhost:8501`
4. Jika browser tidak terbuka otomatis, buka manual dan ketik: `http://localhost:8501`

> ✅ Tidak perlu install Python, pip, atau paket apapun.

---

## Cara Upload Data Baru

1. Buka dashboard → lihat sidebar kiri
2. Klik **"Upload KSEI PDF"**
3. Pilih file PDF bulanan dari KSEI
4. Dashboard langsung memuat data baru

Data tersimpan di file `ksei.db` di folder yang sama dengan `KSEI_Dashboard.exe`.  
Setiap upload **menambah** data (tidak menghapus periode sebelumnya).

---

## Cara Membandingkan Antar Periode (Changelog)

1. Upload minimal **2 file PDF** dari bulan yang berbeda
2. Klik tab **"🔄 Changelog"**
3. Pilih **"Dari periode"** dan **"Ke periode"**
4. Dashboard otomatis menampilkan:
   - Pemegang saham baru yang masuk
   - Pemegang saham yang keluar
   - Perubahan % kepemilikan

---

## Struktur Folder

```
KSEI_Dashboard/
  KSEI_Dashboard.exe    ← Double-click untuk jalankan
  ksei.db               ← Database (terbuat otomatis, jangan dihapus!)
  _internal/            ← Library bundled (jangan diubah)
```

---

## Backup Data

Untuk backup semua data Anda: cukup **copy file `ksei.db`**.

Untuk pindah ke komputer lain: copy seluruh folder `KSEI_Dashboard/` termasuk `ksei.db`.

---

## Rebuild / Update App

Jika ada update app, cukup ganti isi folder `KSEI_Dashboard/`  
tapi **jangan hapus `ksei.db`** — file itu menyimpan semua data historis Anda.

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| Browser tidak terbuka | Buka manual: `http://localhost:8501` |
| Port 8501 sudah dipakai | Tutup instance lain, atau tunggu beberapa detik |
| Upload PDF gagal | Pastikan file adalah PDF resmi dari KSEI (format standar) |
| Data hilang setelah update | Pastikan `ksei.db` ikut di-copy saat upgrade |
| Windows Defender memblokir | Klik "More info" → "Run anyway" (exe ini tidak berbahaya) |
