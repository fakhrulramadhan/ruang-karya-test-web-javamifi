import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { api, Arrow, money } from './lib/api';
import { Header, Footer } from './components/Brand';
import { Home, Classes, About, Journal, Booking } from './pages/PublicPages';
import { AdminPage } from './pages/AdminPage';

function Payment({ navigate }) {
  const code = sessionStorage.getItem('rk_order');
  const [payment, setPayment] = useState(() => JSON.parse(sessionStorage.getItem('rk_payment') || 'null'));
  const [paid, setPaid] = useState(payment?.order?.status === 'paid');
  const [busy, setBusy] = useState(false);
  const [paymentError, setPaymentError] = useState('');

  useEffect(() => {
    if (payment?.payment?.provider !== 'midtrans' || !payment.payment.token) return undefined;
    const scriptUrl = payment.payment.snapScript || 'https://app.sandbox.midtrans.com/snap/snap.js';
    if (window.snap) return undefined;
    const script = document.createElement('script');
    script.src = scriptUrl;
    script.setAttribute('data-client-key', payment.payment.clientKey || '');
    script.async = true;
    script.onerror = () => setPaymentError('Halaman pembayaran Midtrans tidak dapat dimuat.');
    document.body.appendChild(script);
    return () => { script.remove(); };
  }, [payment]);

  if (!code || !payment) {
    return (
      <main className="shell empty-page">
        <h1>Belum ada pesanan.</h1>
        <button className="button button-dark" onClick={() => navigate('classes')}>Pilih kelas <Arrow /></button>
      </main>
    );
  }

  const pay = async () => {
    setBusy(true);
    setPaymentError('');
    try {
      if (payment.payment?.provider === 'midtrans') {
        if (!payment.payment.token) throw new Error('Token pembayaran Midtrans belum tersedia.');
        if (!window.snap) throw new Error('Midtrans Snap belum selesai dimuat. Muat ulang halaman lalu coba lagi.');
        window.snap.pay(payment.payment.token, {
          onSuccess: async () => {
            const order = await api(`/orders/${code}/pay`, { method: 'POST' });
            setPayment({ ...payment, order });
            setPaid(true);
          },
          onPending: () => setPaymentError('Pembayaran masih menunggu konfirmasi.'),
          onError: () => setPaymentError('Midtrans menolak pembayaran. Coba metode lain.'),
          onClose: () => setPaymentError('Jendela pembayaran ditutup sebelum selesai.'),
        });
        return;
      }
      const order = await api(`/orders/${code}/pay`, { method: 'POST' });
      setPayment({ ...payment, order });
      setPaid(true);
    } catch (error) {
      window.alert(error.message);
    } finally {
      setBusy(false);
    }
  };

  const isMidtrans = payment.payment?.provider === 'midtrans';

  return (
    <main className="payment-page shell">
      <p className="kicker">PESANAN / {code}</p>
      <div className={`payment-mark ${paid ? 'is-paid' : ''}`}>{paid ? '✓' : '○'}</div>
      <h1>{paid ? <>Sampai jumpa<br /><span>di kelas.</span></> : <>Satu langkah<br /><span>lagi.</span></>}</h1>
      <p>{paid ? 'Pesananmu sudah dikonfirmasi. Sampai bertemu di meja kerja.' : isMidtrans ? 'Selesaikan pembayaran melalui Midtrans untuk mengunci kursimu.' : 'Selesaikan pembayaran simulasi untuk mengunci kursimu.'}</p>
      <div className="payment-receipt">
        <span>{payment.order.title}</span>
        <strong>{money(payment.order.total)}</strong>
      </div>
      {paymentError && <p className="error-box">{paymentError}</p>}
      {!paid && (
        <button className="button button-dark" onClick={pay} disabled={busy}>
          {busy ? 'Mengonfirmasi...' : isMidtrans ? 'Bayar dengan Midtrans' : 'Konfirmasi pembayaran'} <Arrow />
        </button>
      )}
      {!paid && isMidtrans && payment.payment.redirectUrl && (
        <a className="text-link" href={payment.payment.redirectUrl} target="_blank" rel="noreferrer">Buka halaman pembayaran Midtrans</a>
      )}
      <button className="text-link" onClick={() => navigate('home')}>Kembali ke beranda</button>
    </main>
  );
}

function App() {
  const [route, setRoute] = useState(window.location.hash.replace('#/', '') || 'home');
  const [workshops, setWorkshops] = useState([]);
  const [selected, setSelected] = useState(null);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    api('/workshops').then(setWorkshops).catch(() => setNotice('API belum aktif. Jalankan npm run dev.'));
    const handle = () => setRoute(window.location.hash.replace('#/', '') || 'home');
    window.addEventListener('hashchange', handle);
    return () => window.removeEventListener('hashchange', handle);
  }, []);

  const navigate = (next) => {
    setRoute(next);
    window.location.hash = `/${next}`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const onCreated = (code) => {
    setSelected(null);
    sessionStorage.setItem('rk_order', code);
    navigate('payment');
  };

  let content = <Home workshops={workshops} navigate={navigate} onSelect={setSelected} />;
  if (route === 'classes') content = <Classes workshops={workshops} onSelect={setSelected} />;
  else if (route === 'about') content = <About />;
  else if (route === 'journal') content = <Journal />;
  else if (route === 'admin') content = <AdminPage navigate={navigate} />;
  else if (route === 'payment') content = <Payment navigate={navigate} />;

  const chrome = route !== 'admin';

  return (
    <div className="app">
      {chrome && <Header route={route} navigate={navigate} />}
      {content}
      {chrome && <Footer navigate={navigate} />}
      {selected && <Booking workshop={selected} close={() => setSelected(null)} onCreated={onCreated} />}
      {notice && <div className="toast">{notice}<button onClick={() => setNotice('')}>×</button></div>}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
