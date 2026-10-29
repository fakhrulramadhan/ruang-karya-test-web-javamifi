# Ruang Karya

Ruang Karya adalah platform workshop kreatif. Pengunjung dapat menemukan kelas dari perajin dan seniman, melihat jadwal serta ketersediaan kursi, melakukan booking, lalu membayar melalui Midtrans Sandbox. Admin mengelola workshop dan pesanan melalui CMS.

## Arsitektur

- Frontend: React 18, Vite, Tailwind CSS v4
- Backend: Python, FastAPI, Uvicorn
- Database: PostgreSQL lokal tanpa Docker
- Payment: Midtrans Snap Sandbox atau mock payment
- Automation: n8n melalui webhook

## Stack

- Frontend: React 18, Vite, Tailwind CSS v4
- Backend: Python, FastAPI, Uvicorn
- Database: PostgreSQL 16 (instalasi lokal, tanpa Docker)
- Automation: n8n
- Payment: Midtrans Snap Sandbox atau mock payment
- External API: kurs IDR/USD dengan timeout dan fallback

## Menjalankan aplikasi

1. Salin `.env.example` menjadi `.env`.
2. Pastikan PostgreSQL lokal berjalan, lalu buat database `ruangkarya` dan sesuaikan `DATABASE_URL` (default: `postgresql://ruangkarya:ruangkarya@127.0.0.1:5432/ruangkarya`).
3. Pasang dependency frontend dan backend:

```powershell
npm install
python -m pip install -r backend/requirements.txt
```

4. Jalankan development server:

```powershell
npm run dev
```

Aplikasi tersedia di `http://localhost:5173`, API di `http://localhost:4000`. n8n dapat dijalankan terpisah sesuai instalasi lokal dan workflow di folder `n8n/`.

## Akun demo CMS

- Email: `admin@ruangkarya.id`
- Password: `admin12345`

Ganti kredensial tersebut sebelum deployment nyata.

## Fitur

- Daftar dan detail workshop dengan pencarian serta filter kategori
- Booking peserta dan mock payment
- Penguncian stok kursi saat pembayaran untuk mencegah overselling
- CMS untuk statistik, workshop, dan pesanan
- Integrasi API kurs eksternal dengan cache, timeout, dan fallback
- Webhook n8n setelah pembayaran berhasil

Workflow contoh tersedia di `n8n/ruang-karya-order-paid.json`. Import workflow tersebut ke n8n lalu atur `N8N_WEBHOOK_URL` jika ingin mengaktifkan notifikasi otomatis.

## Struktur singkat

- `src/`: aplikasi React dan halaman CMS
- `backend/app/routers/`: endpoint auth dan API
- `backend/app/database.py`: koneksi, schema, dan seed PostgreSQL
- `backend/app/services/`: integrasi eksternal, payment, dan n8n
- `n8n/`: workflow automation
