"""Konfigurasi aplikasi dan pembacaan berkas .env."""







from __future__ import annotations







import os



from pathlib import Path







ROOT = Path(__file__).resolve().parents[2]











def _load_env_file(path: Path) -> None:



    if not path.exists():



        return



    for raw in path.read_text(encoding="utf-8").splitlines():



        line = raw.strip()



        if not line or line.startswith("#") or "=" not in line:



            continue



        key, value = line.split("=", 1)



        key = key.strip()



        value = value.strip()



        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":



            value = value[1:-1]



        os.environ.setdefault(key, value)











_load_env_file(ROOT / ".env")



_load_env_file(ROOT / "backend" / ".env")











def _text(name: str, default: str = "") -> str:



    value = os.environ.get(name)



    return default if value is None or value == "" else value











def _number(name: str, default: int) -> int:



    try:



        return int(os.environ[name])



    except (KeyError, TypeError, ValueError):



        return default











def _flag(name: str, default: bool = False) -> bool:



    value = os.environ.get(name)



    if value is None:



        return default



    return value.strip().lower() in {"1", "true", "yes", "on"}











class Settings:



    """Nilai konfigurasi yang dipakai seluruh modul."""







    def __init__(self) -> None:



        self.root = ROOT



        self.environment = _text("APP_ENV", _text("NODE_ENV", "development"))



        self.port = _number("API_PORT", 4000)



        self.database_url = _text(



            "DATABASE_URL", "postgresql://ruangkarya:ruangkarya@127.0.0.1:5432/ruangkarya"



        )



        self.session_secret = _text("SESSION_SECRET", "ruang-karya-dev-secret")



        self.internal_api_key = _text("INTERNAL_API_KEY", "n8n-ruangkarya-2026")



        self.admin_email = _text("ADMIN_EMAIL", "admin@ruangkarya.id")



        self.admin_password = _text("ADMIN_PASSWORD", "admin12345")



        self.admin_name = _text("ADMIN_NAME", "Rara Wulandari")







        self.payment_mode = _text("PAYMENT_MODE", "mock").lower()



        self.payment_expiry_minutes = _number("PAYMENT_EXPIRY_MINUTES", 45)



        self.midtrans_server_key = _text("MIDTRANS_SERVER_KEY")



        self.midtrans_client_key = _text("MIDTRANS_CLIENT_KEY")



        self.midtrans_production = _flag("MIDTRANS_IS_PRODUCTION", False)







        self.n8n_webhook_url = _text("N8N_WEBHOOK_URL")



        self.n8n_timeout_ms = _number("N8N_TIMEOUT_MS", 4000)







        self.exchange_rate_url = _text(



            "EXCHANGE_RATE_URL", "https://open.er-api.com/v6/latest/IDR"



        )



        self.exchange_rate_ttl_minutes = _number("EXCHANGE_RATE_TTL_MINUTES", 60)



        self.exchange_rate_timeout_ms = _number("EXCHANGE_RATE_TIMEOUT_MS", 3500)







        self.dist_dir = ROOT / "dist"







    @property



    def midtrans_enabled(self) -> bool:



        return self.payment_mode == "midtrans" and bool(self.midtrans_server_key)







    @property



    def midtrans_snap_base(self) -> str:



        host = "app.midtrans.com" if self.midtrans_production else "app.sandbox.midtrans.com"



        return f"https://{host}/snap/v1"







    @property



    def midtrans_snap_script(self) -> str:



        host = "app.midtrans.com" if self.midtrans_production else "app.sandbox.midtrans.com"



        return f"https://{host}/snap/snap.js"







    @property



    def is_production(self) -> bool:



        return self.environment == "production"











settings = Settings()











