import { useEffect, useState } from 'react';
import { api, money } from '../lib/api';
import { Brand } from '../components/Brand';

export function AdminPage({ navigate }) {
  const [loggedIn, setLoggedIn] = useState(Boolean(localStorage.getItem('rk_token'))); const [login, setLogin] = useState({ email: 'admin@ruangkarya.id', password: 'admin12345' }); const [error, setError] = useState(''); const [stats, setStats] = useState(null); const [orders, setOrders] = useState([]); const [workshops, setWorkshops] = useState([]); const [showForm, setShowForm] = useState(false); const [form, setForm] = useState({ title: '', category: 'Keramik', location: 'Bandung', date: '', time: '10.00—13.00', price: 350000, capacity: 12, description: '', image: '', featured: false, status: 'published' });
  const load = async () => { const [nextStats, nextOrders, nextWorkshops] = await Promise.all([api('/admin/stats'), api('/admin/orders'), api('/admin/workshops')]); setStats(nextStats); setOrders(nextOrders); setWorkshops(nextWorkshops); };
  useEffect(() => { if (loggedIn) load().catch((e) => setError(e.message)); }, [loggedIn]);
  const submitLogin = async (e) => { e.preventDefault(); try { const result = await api('/auth/login', { method: 'POST', body: JSON.stringify(login) }); localStorage.setItem('rk_token', result.token); setLoggedIn(true); } catch (e) { setError(e.message); } };
  const create = async (e) => {
    e.preventDefault();
    setError('');
    const description = form.description.trim();
    if (description.length < 10) {
      setError('Deskripsi minimal 10 karakter.');
      return;
    }
    if (!form.date) {
      setError('Tanggal workshop wajib diisi.');
      return;
    }
    try {
      await api('/admin/workshops', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          title: form.title.trim(),
          category: form.category.trim(),
          location: form.location.trim(),
          time: form.time.trim(),
          description,
          price: Number(form.price),
          capacity: Number(form.capacity),
          image: form.image.trim() || null,
        }),
      });
      setShowForm(false);
      setForm({ ...form, title: '', date: '', description: '', image: '' });
      await load();
    } catch (e) {
      setError(e.message);
    }
  };
  if (!loggedIn) return <main className="admin-login"><div className="admin-card"><Brand onClick={() => navigate('home')} /><p className="kicker">CMS / RUANG KARYA</p><h1>Selamat datang<br /><span>di meja admin.</span></h1>{error && <p className="error-box">{error}</p>}<form onSubmit={submitLogin}><label>Email<input type="email" value={login.email} onChange={(e) => setLogin({ ...login, email: e.target.value })} /></label><label>Password<input type="password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} /></label><button className="button button-dark">Masuk ke CMS ↗</button></form></div></main>;
  return <main className="shell page-pad admin-page"><div className="admin-top"><div><p className="kicker">CMS / OVERVIEW</p><h1>Selamat pagi, Rara.</h1></div><div><button className="button button-outline" onClick={() => { localStorage.removeItem('rk_token'); setLoggedIn(false); }}>Keluar</button> <button className="button button-dark" onClick={() => setShowForm(!showForm)}>+ Workshop</button></div></div>{error && <p className="error-box">{error}</p>}<div className="admin-stats">{[['Pendapatan', money(stats?.revenue)], ['Peserta', stats?.attendees || 0], ['Workshop aktif', stats?.workshops || 0], ['Pesanan', stats?.orders || 0]].map(([label, value]) => <div key={label}><span>{label}</span><b>{value}</b></div>)}</div>{showForm && <form className="admin-form" onSubmit={create}>{[['title','Judul'],['category','Kategori'],['location','Lokasi'],['date','Tanggal'],['time','Jam'],['price','Harga'],['capacity','Kapasitas'],['image','URL gambar']].map(([key,label]) => <label key={key}>{label}<input required={['title','category','location','date','time','price','capacity'].includes(key)} type={key === 'date' ? 'date' : key === 'price' || key === 'capacity' ? 'number' : 'text'} value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} /></label>)}<label className="wide">Deskripsi<textarea required rows="3" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label><button className="button button-dark wide">Simpan workshop</button></form>}<section className="admin-section"><p className="kicker">AKTIVITAS TERBARU</p><h2>Pesanan masuk</h2><div className="table-wrap"><table><thead><tr><th>Kode</th><th>Peserta</th><th>Workshop</th><th>Total</th><th>Status</th></tr></thead><tbody>{orders.slice(0, 10).map((order) => <tr key={order.id}><td>{order.code}</td><td>{order.customer_name}</td><td>{order.title}</td><td>{money(order.total)}</td><td><span className={`status status-${order.status}`}>{order.status}</span></td></tr>)}</tbody></table></div></section><section className="admin-section"><p className="kicker">KONTEN</p><h2>Workshop</h2>{workshops.map((item) => <div className="admin-workshop" key={item.id}><img src={item.image} alt="" /><div><b>{item.title}</b><span>{item.location} · {item.available} kursi tersisa</span></div><em>{item.status}</em></div>)}</section></main>;
}
