const jsonRequest = async (path, options = {}) => {
  const token = localStorage.getItem('rk_token');
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      'content-type': 'application/json',
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((item) => `${Array.isArray(item.loc) ? item.loc.at(-1) : 'field'}: ${item.msg}`).join(' | ')
      : payload.detail;
    throw new Error(detail || payload.message || 'Terjadi kesalahan.');
  }
  return payload.data;
};

export const api = jsonRequest;
export const money = (value) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(value || 0);
export const dateLabel = (value) => new Intl.DateTimeFormat('id-ID', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value));
export const Arrow = () => '↗';
