export function Brand({ onClick, light = false }) {
  return (
    <button onClick={onClick} className="brand" aria-label="Kembali ke beranda">
      <span className={`brand-mark ${light ? 'brand-mark-light' : ''}`}>RK</span>
      <span>ruang<span className="brand-accent">karya</span></span>
    </button>
  );
}

export function Header({ route, navigate }) {
  return (
    <header className="site-header">
      <div className="shell header-inner">
        <Brand onClick={() => navigate('home')} />
        <nav className="nav-links" aria-label="Navigasi utama">
          {[['classes', 'Kelas'], ['about', 'Tentang'], ['journal', 'Jurnal']].map(([key, label]) => (
            <button key={key} onClick={() => navigate(key)} className={route === key ? 'active' : ''}>{label}</button>
          ))}
        </nav>
        <button className="cms-link" onClick={() => navigate('admin')}>CMS <span>↗</span></button>
      </div>
    </header>
  );
}

export function Footer({ navigate }) {
  return (
    <footer className="site-footer">
      <div className="shell footer-grid">
        <Brand onClick={() => navigate('home')} light />
        <p>Workshop kecil, tangan yang sibuk, cerita yang menetap.</p>
        <p className="footer-meta">Bandung · Yogyakarta · Jakarta<br />© 2026 Ruang Karya</p>
      </div>
    </footer>
  );
}
