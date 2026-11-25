import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _default_env_path() -> str:
    if os.name == "nt":
        local_app = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(local_app, "Heuristika", ".env")
    return os.path.join(os.path.expanduser("~"), ".config", "heuristika", ".env")


ENV_PATH = os.getenv("HEURISTIKA_ENV_PATH") or _default_env_path()
if os.path.isfile(ENV_PATH):
    load_dotenv(ENV_PATH, override=False)
else:
    load_dotenv(override=False)


def _default_database_path() -> str:
    """Mantém o SQLite fora do Google Drive para evitar corrupção por sincronização."""
    if os.name == "nt":
        local_app = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(local_app, "Heuristika", "sinais_vip.db")
    return os.path.join(os.path.expanduser("~"), ".local", "share", "heuristika", "sinais_vip.db")


DATABASE_PATH = os.getenv("DATABASE_PATH") or os.getenv("DB_PATH") or _default_database_path()
DB_PATH = DATABASE_PATH

SECRET_KEY = os.getenv("SECRET_KEY", "sinais-vip-dev-secret-key")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
VIP_CHAT_ID = os.getenv("VIP_CHAT_ID", "").strip()
FREE_CHAT_ID = os.getenv("FREE_CHAT_ID", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
TELEGRAM_VIP_CHANNEL_URL = os.getenv("TELEGRAM_VIP_CHANNEL_URL", "https://t.me/seu_canal_vip").strip()

# Links comerciais & Pix
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:5050").rstrip("/")
CHECKOUT_URL = os.getenv("CHECKOUT_URL", "https://seu-checkout.com/vip").strip()
SUPORTE_URL = os.getenv("SUPORTE_URL", "https://t.me/seu_suporte").strip()
PIX_KEY = os.getenv("PIX_KEY", "seu-pix@exemplo.com").strip()
PIX_RECEIVER = os.getenv("PIX_RECEIVER", "Heurístika Mesa Quantitativa").strip()
PIX_INSTITUTION = os.getenv("PIX_INSTITUTION", "Transferência Pix Instantânea").strip()

# Categorias suportadas
CATEGORIAS = ["Ações", "Fundos", "Futuros", "Forex", "Cripto", "Índices"]

# Catálogo inicial editável por categoria
# Campos: symbol (nome exibido), binance (opcional), yahoo (opcional), stooq (opcional), fallback_price, decimals
CATALOGO_ATIVOS = {
    "Cripto": [
        {"symbol": "BTC/USD", "binance": "BTCUSDT", "yahoo": "BTC-USD", "stooq": None, "fallback_price": 91500.0, "decimals": 2},
        {"symbol": "ETH/USD", "binance": "ETHUSDT", "yahoo": "ETH-USD", "stooq": None, "fallback_price": 3120.0, "decimals": 2},
        {"symbol": "SOL/USD", "binance": "SOLUSDT", "yahoo": "SOL-USD", "stooq": None, "fallback_price": 215.0, "decimals": 2},
        {"symbol": "BNB/USD", "binance": "BNBUSDT", "yahoo": "BNB-USD", "stooq": None, "fallback_price": 620.0, "decimals": 2},
    ],
    "Forex": [
        {"symbol": "EUR/USD", "binance": None, "yahoo": "EURUSD=X", "stooq": "eurusd", "fallback_price": 1.0580, "decimals": 4},
        {"symbol": "GBP/USD", "binance": None, "yahoo": "GBPUSD=X", "stooq": "gbpusd", "fallback_price": 1.2670, "decimals": 4},
        {"symbol": "USD/JPY", "binance": None, "yahoo": "USDJPY=X", "stooq": "usdjpy", "fallback_price": 154.20, "decimals": 2},
        {"symbol": "AUD/USD", "binance": None, "yahoo": "AUDUSD=X", "stooq": "audusd", "fallback_price": 0.6510, "decimals": 4},
    ],
    "Futuros": [
        {"symbol": "ES=F", "binance": None, "yahoo": "ES=F", "stooq": None, "fallback_price": 5920.0, "decimals": 2},
        {"symbol": "NQ=F", "binance": None, "yahoo": "NQ=F", "stooq": None, "fallback_price": 20750.0, "decimals": 2},
        {"symbol": "GC=F", "binance": None, "yahoo": "GC=F", "stooq": None, "fallback_price": 2650.0, "decimals": 2},
        {"symbol": "CL=F", "binance": None, "yahoo": "CL=F", "stooq": None, "fallback_price": 69.50, "decimals": 2},
    ],
    "Índices": [
        {"symbol": "SPX500", "binance": None, "yahoo": "^GSPC", "stooq": "^spx", "fallback_price": 5910.0, "decimals": 2},
        {"symbol": "NDX100", "binance": None, "yahoo": "^NDX", "stooq": "^ndq", "fallback_price": 20680.0, "decimals": 2},
        {"symbol": "IBOV", "binance": None, "yahoo": "^BVSP", "stooq": "^bvp", "fallback_price": 127800.0, "decimals": 0},
        {"symbol": "DAX40", "binance": None, "yahoo": "^GDAXI", "stooq": "^dax", "fallback_price": 19150.0, "decimals": 2},
    ],
    "Ações": [
        {"symbol": "PETR4", "binance": None, "yahoo": "PETR4.SA", "stooq": None, "fallback_price": 36.40, "decimals": 2},
        {"symbol": "VALE3", "binance": None, "yahoo": "VALE3.SA", "stooq": None, "fallback_price": 58.20, "decimals": 2},
        {"symbol": "AAPL", "binance": None, "yahoo": "AAPL", "stooq": "aapl.us", "fallback_price": 228.50, "decimals": 2},
        {"symbol": "NVDA", "binance": None, "yahoo": "NVDA", "stooq": "nvda.us", "fallback_price": 141.20, "decimals": 2},
    ],
    "Fundos": [
        {"symbol": "HGLG11", "binance": None, "yahoo": "HGLG11.SA", "stooq": None, "fallback_price": 156.80, "decimals": 2},
        {"symbol": "MXRF11", "binance": None, "yahoo": "MXRF11.SA", "stooq": None, "fallback_price": 9.85, "decimals": 2},
        {"symbol": "IVVB11", "binance": None, "yahoo": "IVVB11.SA", "stooq": None, "fallback_price": 352.00, "decimals": 2},
        {"symbol": "BOVA11", "binance": None, "yahoo": "BOVA11.SA", "stooq": None, "fallback_price": 124.50, "decimals": 2},
    ],
}

# Parâmetros dos indicadores técnicos e regras operacionais
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
ATR_PERIOD = 14

ANTI_DUPLICATE_MINUTES = int(os.getenv("ANTI_DUPLICATE_MINUTES", "60"))
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))
AUDIT_INTERVAL_SECONDS = int(os.getenv("AUDIT_INTERVAL_SECONDS", "30"))
ENABLE_SIMULATION_FALLBACK = os.getenv("ENABLE_SIMULATION_FALLBACK", "false").lower() == "true"

# Camada opcional de LLM do Gerente de Estratégias (desligada por padrão - Custo Zero)
LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini_free").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MAX_RPM = int(os.getenv("LLM_MAX_RPM", "5"))
LLM_MAX_RPD = int(os.getenv("LLM_MAX_RPD", "50"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "450"))

# Planos comerciais exibidos na vitrine (pagamento exclusivo via Pix)
PLANOS = [
    {
        "nome": "Mensal",
        "preco": "R$ 29,99",
        "periodo": "/mês",
        "destaque": True,
        "badge": "PIX • ACESSO IMEDIATO",
        "beneficios": [
            "Pagamento único via transferência Pix",
            "Acesso total ao Painel Web VIP",
            "Convite exclusivo no Canal VIP do Telegram",
            "Sinais em tempo real (6 categorias)",
        ],
    },
    {
        "nome": "Trimestral",
        "preco": "R$ 79,90",
        "periodo": "/trimestre",
        "destaque": False,
        "badge": "ECONOMIA NO PIX",
        "beneficios": [
            "Equivalente a R$ 26,63/mês no Pix",
            "Acesso total ao Painel Web VIP + Telegram",
            "Auditoria automática TP1, TP2 e Stop",
            "Sem renovação automática no cartão",
        ],
    },
    {
        "nome": "Anual",
        "preco": "R$ 269,90",
        "periodo": "/ano",
        "destaque": False,
        "badge": "25% OFF + CARTEIRAS",
        "beneficios": [
            "Carteiras Gerenciadas (2, 5 e 10+ anos) — 01/12/2026",
            "Canal VIP Telegram + Painel Web 24/7",
            "Perfis Conservador, Moderado e Agressivo",
            "Prioridade no suporte e atualizações do robô",
        ],
    },
]


def find_asset_config(categoria: str, symbol: str):
    """Retorna o dicionário de configuração do ativo ou None."""
    for item in CATALOGO_ATIVOS.get(categoria, []):
        if item["symbol"].upper() == symbol.upper():
            return item
    return None
