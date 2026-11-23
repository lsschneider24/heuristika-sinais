import hmac
import sqlite3
import secrets
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
import config


def get_connection():
    conn = sqlite3.connect(config.DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL,
            ativo TEXT NOT NULL,
            direcao TEXT NOT NULL,
            entrada REAL NOT NULL,
            sl REAL NOT NULL,
            tp1 REAL NOT NULL,
            tp2 REAL NOT NULL,
            preco_atual REAL,
            destino TEXT NOT NULL DEFAULT 'VIP',
            status TEXT NOT NULL DEFAULT 'ABERTO',
            resultado_pct REAL DEFAULT 0.0,
            origem TEXT NOT NULL DEFAULT 'MANUAL',
            observacao TEXT DEFAULT '',
            telegram_vip_msg_id INTEGER,
            telegram_free_msg_id INTEGER,
            criado_em TEXT NOT NULL,
            encerrado_em TEXT
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            contato TEXT NOT NULL UNIQUE,
            plano TEXT NOT NULL DEFAULT 'Mensal',
            codigo_acesso TEXT NOT NULL UNIQUE,
            ativo INTEGER NOT NULL DEFAULT 1,
            telegram_invite_link TEXT DEFAULT '',
            expira_em TEXT NOT NULL,
            criado_em TEXT NOT NULL
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_settings (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            horizonte TEXT NOT NULL,
            perfil TEXT NOT NULL,
            ativo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            peso_pct REAL NOT NULL,
            tese TEXT NOT NULL,
            vigencia TEXT NOT NULL DEFAULT '01/12/2026',
            atualizado_em TEXT NOT NULL
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS academy_students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            documento TEXT DEFAULT '',
            pin TEXT NOT NULL,
            criado_em TEXT NOT NULL
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            codigo TEXT NOT NULL UNIQUE,
            nota_pct REAL NOT NULL,
            acertos INTEGER NOT NULL,
            total_questoes INTEGER NOT NULL,
            emitido_em TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES academy_students(id)
        );
        """
    )

    defaults = {
        "auto_scan_enabled": "0",
        "auto_audit_enabled": "1",
        "last_scan_at": "-",
        "last_audit_at": "-",
    }
    for k, v in defaults.items():
        cur.execute(
            "INSERT OR IGNORE INTO bot_settings (chave, valor) VALUES (?, ?);",
            (k, v),
        )

    conn.commit()
    conn.close()


def seed_initial_data(force: bool = False):
    """Popula 4 sinais iniciais (2 acertos, 1 erro, 1 aberto) e 1 assinante demo."""
    conn = get_connection()
    cur = conn.cursor()

    count = cur.execute("SELECT COUNT(*) FROM signals;").fetchone()[0]
    if count == 0 or force:
        if force:
            cur.execute("DELETE FROM signals;")

        now = datetime.now()
        t1 = (now - timedelta(hours=30)).strftime("%Y-%m-%d %H:%M:%S")
        t1_end = (now - timedelta(hours=22)).strftime("%Y-%m-%d %H:%M:%S")
        t2 = (now - timedelta(hours=18)).strftime("%Y-%m-%d %H:%M:%S")
        t2_end = (now - timedelta(hours=11)).strftime("%Y-%m-%d %H:%M:%S")
        t3 = (now - timedelta(hours=14)).strftime("%Y-%m-%d %H:%M:%S")
        t3_end = (now - timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        t4 = (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")

        initial_signals = [
            # 1. Encerrado com Acerto TP2
            (
                "Cripto", "BTC/USD", "COMPRA",
                88500.00, 87200.00, 90200.00, 92800.00, 92950.00,
                "VIP", "ACERTO_TP2", 4.86, "ROBO",
                "Rompimento de EMA9/21 com volume institucional.",
                None, None, t1, t1_end,
            ),
            # 2. Encerrado com Acerto TP1
            (
                "Forex", "EUR/USD", "COMPRA",
                1.0520, 1.0480, 1.0615, 1.0690, 1.0620,
                "AMBOS", "ACERTO_TP1", 0.90, "MANUAL",
                "Sinal vitrine após defesa de suporte diário.",
                None, None, t2, t2_end,
            ),
            # 3. Encerrado com Stop Loss
            (
                "Índices", "SPX500", "VENDA",
                5940.00, 5978.00, 5885.00, 5830.00, 5980.00,
                "FREE", "ERRO_SL", -0.64, "ROBO",
                "Rejeição em resistência, mas fluxo comprador acionou SL.",
                None, None, t3, t3_end,
            ),
            # 4. Sinal em Aberto (VIP)
            (
                "Cripto", "SOL/USD", "COMPRA",
                212.50, 204.00, 224.00, 236.00, 215.40,
                "VIP", "ABERTO", 1.36, "ROBO",
                "Tendência de alta confirmada em H1 (RSI 58).",
                None, None, t4, None,
            ),
        ]

        cur.executemany(
            """
            INSERT INTO signals (
                categoria, ativo, direcao, entrada, sl, tp1, tp2, preco_atual,
                destino, status, resultado_pct, origem, observacao,
                telegram_vip_msg_id, telegram_free_msg_id, criado_em, encerrado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            initial_signals,
        )

    sub_count = cur.execute("SELECT COUNT(*) FROM subscribers;").fetchone()[0]
    if sub_count == 0:
        exp = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        cur.execute(
            """
            INSERT INTO subscribers (nome, contato, plano, codigo_acesso, ativo, telegram_invite_link, expira_em, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("Assinante Demo", "cliente@exemplo.com", "Trimestral", "VIP-DEMO-2026", 1, "", exp, now_str()),
        )

    port_count = cur.execute("SELECT COUNT(*) FROM portfolios;").fetchone()[0]
    if port_count == 0 or force:
        if force:
            cur.execute("DELETE FROM portfolios;")
        ts = now_str()
        vig = "01/12/2026"
        initial_portfolios = [
            # CURTO PRAZO (2 anos)
            ("Curto (2 anos)", "Conservador", "TESOURO SELIC", "Fundos", 55.0, "Liquidez diária e proteção contra juros altos.", vig, ts),
            ("Curto (2 anos)", "Conservador", "HGLG11", "Fundos", 25.0, "Renda mensal com baixa volatilidade imobiliária.", vig, ts),
            ("Curto (2 anos)", "Conservador", "IVVB11", "Índices", 10.0, "Exposição dolarizada moderada ao S&P 500.", vig, ts),
            ("Curto (2 anos)", "Conservador", "EUR/USD", "Forex", 10.0, "Reserva cambial tática em moeda forte.", vig, ts),

            ("Curto (2 anos)", "Moderado", "TESOURO IPCA+ 2028", "Fundos", 35.0, "Proteção real contra inflação no horizonte de 24 meses.", vig, ts),
            ("Curto (2 anos)", "Moderado", "PETR4 / VALE3", "Ações", 30.0, "Geração de caixa e dividendos em blue chips B3.", vig, ts),
            ("Curto (2 anos)", "Moderado", "MXRF11 / HGLG11", "Fundos", 20.0, "Fluxo de proventos recorrentes isentos.", vig, ts),
            ("Curto (2 anos)", "Moderado", "BTC/USD", "Cripto", 15.0, "Assimetria controlada em ativo líquido.", vig, ts),

            ("Curto (2 anos)", "Agressivo", "BTC/USD + SOL/USD", "Cripto", 35.0, "Captura de momentum e convexidade de curto prazo.", vig, ts),
            ("Curto (2 anos)", "Agressivo", "NVDA / AAPL", "Ações", 30.0, "Crescimento acelerado em tecnologia e IA.", vig, ts),
            ("Curto (2 anos)", "Agressivo", "ES=F / GC=F", "Futuros", 20.0, "Operações táticas em S&P Futuro e Ouro.", vig, ts),
            ("Curto (2 anos)", "Agressivo", "CAIXA TÁTICO", "Fundos", 15.0, "Liquidez para aproveitar correções agudas.", vig, ts),

            # MÉDIO PRAZO (5 anos)
            ("Médio (5 anos)", "Conservador", "TESOURO IPCA+ 2031", "Fundos", 45.0, "Juro real travado para vencimento em 5 anos.", vig, ts),
            ("Médio (5 anos)", "Conservador", "HGLG11 / MXRF11", "Fundos", 30.0, "Reinvestimento de dividendos imobiliários.", vig, ts),
            ("Médio (5 anos)", "Conservador", "IVVB11", "Índices", 15.0, "Diversificação geográfica em dólar.", vig, ts),
            ("Médio (5 anos)", "Conservador", "GC=F (Ouro)", "Futuros", 10.0, "Seguro contra eventos de cauda e desvalorização fiduciária.", vig, ts),

            ("Médio (5 anos)", "Moderado", "IVVB11 / AAPL", "Índices", 30.0, "Composição de juros compostos no mercado americano.", vig, ts),
            ("Médio (5 anos)", "Moderado", "PETR4 / VALE3", "Ações", 30.0, "Valor e dividendos no ciclo de commodities.", vig, ts),
            ("Médio (5 anos)", "Moderado", "HGLG11 / BOVA11", "Fundos", 25.0, "Equilíbrio entre renda passiva e índice local.", vig, ts),
            ("Médio (5 anos)", "Moderado", "BTC/USD + ETH/USD", "Cripto", 15.0, "Alocação estrutural para ciclo de 4–5 anos.", vig, ts),

            ("Médio (5 anos)", "Agressivo", "NVDA / NDX100", "Índices", 40.0, "Liderança global em semicondutores e Nasdaq 100.", vig, ts),
            ("Médio (5 anos)", "Agressivo", "BTC/USD / ETH/USD / SOL/USD", "Cripto", 35.0, "Exposição de alta convicção em ativos digitais.", vig, ts),
            ("Médio (5 anos)", "Agressivo", "VALE3 / PETR4", "Ações", 15.0, "Alavancagem operacional em commodities.", vig, ts),
            ("Médio (5 anos)", "Agressivo", "GC=F (Ouro)", "Futuros", 10.0, "Hedge descorrelacionado para redução de drawdown.", vig, ts),

            # LONGO PRAZO (10+ anos)
            ("Longo (10+ anos)", "Conservador", "TESOURO IPCA+ 2035+", "Fundos", 40.0, "Preservação secular de poder de compra.", vig, ts),
            ("Longo (10+ anos)", "Conservador", "SPX500 / IVVB11", "Índices", 35.0, "Crescimento estrutural das 500 maiores empresas dos EUA.", vig, ts),
            ("Longo (10+ anos)", "Conservador", "HGLG11", "Fundos", 25.0, "Ativos reais com reajuste inflacionário de longo prazo.", vig, ts),

            ("Longo (10+ anos)", "Moderado", "IVVB11 / NDX100", "Índices", 40.0, "Motor principal de multiplicação patrimonial global.", vig, ts),
            ("Longo (10+ anos)", "Moderado", "VALE3 / PETR4", "Ações", 25.0, "Reinvestimento contínuo de proventos na B3.", vig, ts),
            ("Longo (10+ anos)", "Moderado", "HGLG11 / MXRF11", "Fundos", 20.0, "Base geradora de fluxo mensal.", vig, ts),
            ("Longo (10+ anos)", "Moderado", "BTC/USD", "Cripto", 15.0, "Reserva digital escassa no horizonte de 10+ anos.", vig, ts),

            ("Longo (10+ anos)", "Agressivo", "NVDA / AAPL / NDX100", "Ações", 45.0, "Convexidade secular em tecnologia e automação.", vig, ts),
            ("Longo (10+ anos)", "Agressivo", "BTC/USD / ETH/USD / SOL/USD", "Cripto", 35.0, "Assimetria máxima em redes descentralizadas.", vig, ts),
            ("Longo (10+ anos)", "Agressivo", "VALE3 / GC=F", "Futuros", 20.0, "Proteção real em ativos tangíveis e metais.", vig, ts),
        ]
        cur.executemany(
            """
            INSERT INTO portfolios (horizonte, perfil, ativo, categoria, peso_pct, tese, vigencia, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            initial_portfolios,
        )

    conn.commit()
    conn.close()


def get_setting(chave: str, default: str = "") -> str:
    conn = get_connection()
    row = conn.execute("SELECT valor FROM bot_settings WHERE chave = ?;", (chave,)).fetchone()
    conn.close()
    return row["valor"] if row else default


def set_setting(chave: str, valor: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO bot_settings (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor;",
        (chave, str(valor)),
    )
    conn.commit()
    conn.close()


def get_all_settings() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT chave, valor FROM bot_settings;").fetchall()
    conn.close()
    return {r["chave"]: r["valor"] for r in rows}


def insert_signal(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO signals (
            categoria, ativo, direcao, entrada, sl, tp1, tp2, preco_atual,
            destino, status, resultado_pct, origem, observacao, criado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ABERTO', 0.0, ?, ?, ?);
        """,
        (
            data["categoria"],
            data["ativo"].upper().strip(),
            data["direcao"].upper().strip(),
            float(data["entrada"]),
            float(data["sl"]),
            float(data["tp1"]),
            float(data["tp2"]),
            float(data.get("preco_atual") or data["entrada"]),
            data.get("destino", "VIP").upper().strip(),
            data.get("origem", "MANUAL").upper().strip(),
            data.get("observacao", "").strip(),
            now_str(),
        ),
    )
    signal_id = cur.lastrowid
    conn.commit()
    conn.close()
    return signal_id


def update_signal_telegram_ids(signal_id: int, vip_msg_id=None, free_msg_id=None):
    conn = get_connection()
    conn.execute(
        "UPDATE signals SET telegram_vip_msg_id = COALESCE(?, telegram_vip_msg_id), telegram_free_msg_id = COALESCE(?, telegram_free_msg_id) WHERE id = ?;",
        (vip_msg_id, free_msg_id, signal_id),
    )
    conn.commit()
    conn.close()


def get_signal_by_id(signal_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM signals WHERE id = ?;", (signal_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def reopen_signal(signal_id: int) -> bool:
    conn = get_connection()
    cur = conn.execute(
        """
        UPDATE signals
        SET status = 'ABERTO',
            encerrado_em = NULL,
            resultado_pct = 0.0,
            preco_atual = COALESCE(preco_atual, entrada)
        WHERE id = ?;
        """,
        (signal_id,),
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def delete_signal(signal_id: int) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM signals WHERE id = ?;", (signal_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def list_signals(categoria: str = None, status_list: list = None, limit: int = 100):
    conn = get_connection()
    query = "SELECT * FROM signals WHERE 1=1"
    params = []

    if categoria and categoria != "Todos":
        query += " AND categoria = ?"
        params.append(categoria)

    if status_list:
        placeholders = ",".join("?" for _ in status_list)
        query += f" AND status IN ({placeholders})"
        params.extend(status_list)

    query += " ORDER BY id DESC LIMIT ?;"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def has_recent_open_or_duplicate_signal(ativo: str, minutes: int) -> bool:
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    row = conn.execute(
        """
        SELECT id FROM signals
        WHERE UPPER(ativo) = UPPER(?)
          AND (status = 'ABERTO' OR criado_em >= ?)
        LIMIT 1;
        """,
        (ativo, cutoff),
    ).fetchone()
    conn.close()
    return row is not None


def get_performance_stats(categoria: str = None) -> dict:
    conn = get_connection()
    where = ""
    params = []
    if categoria and categoria != "Todos":
        where = "WHERE categoria = ?"
        params.append(categoria)

    rows = conn.execute(f"SELECT status, resultado_pct FROM signals {where};", params).fetchall()
    conn.close()

    total_tp1 = sum(1 for r in rows if r["status"] == "ACERTO_TP1")
    total_tp2 = sum(1 for r in rows if r["status"] == "ACERTO_TP2")
    total_acertos = total_tp1 + total_tp2
    total_erros = sum(1 for r in rows if r["status"] == "ERRO_SL")
    abertos = sum(1 for r in rows if r["status"] == "ABERTO")
    encerrados = total_acertos + total_erros
    taxa_acerto = round((total_acertos / encerrados) * 100, 1) if encerrados > 0 else 0.0
    retorno_acumulado = round(
        sum(float(r["resultado_pct"] or 0.0) for r in rows if r["status"] in ("ACERTO_TP1", "ACERTO_TP2", "ERRO_SL")),
        2,
    )

    return {
        "total_sinais": len(rows),
        "total_acertos": total_acertos,
        "total_tp1": total_tp1,
        "total_tp2": total_tp2,
        "total_erros": total_erros,
        "abertos": abertos,
        "encerrados": encerrados,
        "taxa_acerto": taxa_acerto,
        "retorno_acumulado": retorno_acumulado,
    }


def get_stats_by_category() -> list:
    stats = []
    for cat in config.CATEGORIAS:
        s = get_performance_stats(cat)
        s["categoria"] = cat
        stats.append(s)
    return stats


def generate_access_code() -> str:
    part1 = secrets.token_hex(2).upper()
    part2 = secrets.token_hex(2).upper()
    return f"VIP-{part1}-{part2}"


def create_subscriber(nome: str, contato: str, plano: str = "Mensal", dias: int = 30) -> dict:
    conn = get_connection()
    codigo = generate_access_code()
    expira_em = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO subscribers (nome, contato, plano, codigo_acesso, ativo, expira_em, criado_em)
        VALUES (?, ?, ?, ?, 1, ?, ?);
        """,
        (nome.strip(), contato.strip().lower(), plano, codigo, expira_em, now_str()),
    )
    sub_id = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM subscribers WHERE id = ?;", (sub_id,)).fetchone()
    conn.close()
    return dict(row)


def list_subscribers() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM subscribers ORDER BY id DESC;").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def authenticate_subscriber(identificador: str):
    """Autentica por e-mail/contato ou código de acesso se estiver ativo e dentro da validade."""
    ident = identificador.strip()
    if not ident:
        return None
    conn = get_connection()
    row = conn.execute(
        """
        SELECT * FROM subscribers
        WHERE (LOWER(contato) = LOWER(?) OR UPPER(codigo_acesso) = UPPER(?))
          AND ativo = 1
        LIMIT 1;
        """,
        (ident, ident),
    ).fetchone()
    conn.close()
    if not row:
        return None
    sub = dict(row)
    hoje = datetime.now().strftime("%Y-%m-%d")
    if sub["expira_em"] < hoje:
        return None
    return sub


def is_subscriber_valid(sub: dict) -> bool:
    """Retorna True se o assinante existe, está ativo e ainda dentro da validade."""
    return bool(
        sub
        and sub.get("ativo")
        and str(sub.get("expira_em") or "") >= datetime.now().strftime("%Y-%m-%d")
    )


def get_subscriber_by_id(sub_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM subscribers WHERE id = ?;", (sub_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def toggle_subscriber_status(sub_id: int) -> bool:
    conn = get_connection()
    cur = conn.execute("UPDATE subscribers SET ativo = CASE WHEN ativo = 1 THEN 0 ELSE 1 END WHERE id = ?;", (sub_id,))
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def renew_subscriber(sub_id: int, dias: int = 30):
    """Soma dias à maior data entre hoje e a validade atual, evitando encurtar planos longos."""
    conn = get_connection()
    row = conn.execute("SELECT expira_em FROM subscribers WHERE id = ?;", (sub_id,)).fetchone()
    if not row:
        conn.close()
        return None
    today = datetime.now().date()
    try:
        current_exp = datetime.strptime(str(row["expira_em"] or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        current_exp = today
    base_date = max(today, current_exp)
    nova_data = (base_date + timedelta(days=int(dias))).strftime("%Y-%m-%d")
    conn.execute("UPDATE subscribers SET ativo = 1, expira_em = ? WHERE id = ?;", (nova_data, sub_id))
    conn.commit()
    conn.close()
    return nova_data


def update_subscriber_plan(sub_id: int, plano: str):
    """Atualiza o plano do assinante estendendo validade em upgrades e preservando datas maiores."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM subscribers WHERE id = ?;", (sub_id,)).fetchone()
    if not row:
        conn.close()
        return None
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")
    current_exp = str(row["expira_em"] or "")[:10]
    new_exp = current_exp
    new_ativo = row["ativo"]
    plan_days_map = {"Mensal": 30, "Trimestral": 90, "Anual": 365, "Vitalício": 36500}
    old_days = plan_days_map.get(row["plano"], 30)
    plan_days = plan_days_map.get(plano, 30)

    if plano == "Vitalício":
        min_vital = (today + timedelta(days=36500)).strftime("%Y-%m-%d")
        if new_exp < min_vital:
            new_exp = min_vital
        new_ativo = 1
    elif not current_exp or current_exp < today_str:
        new_exp = (today + timedelta(days=plan_days)).strftime("%Y-%m-%d")
        new_ativo = 1
    elif plan_days > old_days:
        min_upgrade = (today + timedelta(days=plan_days)).strftime("%Y-%m-%d")
        if new_exp < min_upgrade:
            new_exp = min_upgrade
        new_ativo = 1

    conn.execute(
        "UPDATE subscribers SET plano = ?, expira_em = ?, ativo = ? WHERE id = ?;",
        (plano, new_exp, new_ativo, sub_id),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM subscribers WHERE id = ?;", (sub_id,)).fetchone()
    conn.close()
    return dict(updated) if updated else None


def delete_subscriber(sub_id: int) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM subscribers WHERE id = ?;", (sub_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def set_subscriber_invite_link(sub_id: int, link: str):
    conn = get_connection()
    conn.execute("UPDATE subscribers SET telegram_invite_link = ? WHERE id = ?;", (link, sub_id))
    conn.commit()
    conn.close()


# ==============================================================================
# CARTEIRAS GERENCIADAS (CURTO 2a, MÉDIO 5a, LONGO 10+a — VIGÊNCIA 01/12/2026)
# ==============================================================================
def list_portfolios(horizonte: str = None, perfil: str = None) -> list:
    conn = get_connection()
    query = "SELECT * FROM portfolios WHERE 1=1"
    params = []
    if horizonte and horizonte != "Todos":
        query += " AND horizonte = ?"
        params.append(horizonte)
    if perfil and perfil != "Todos":
        query += " AND perfil = ?"
        params.append(perfil)
    query += " ORDER BY horizonte, perfil, peso_pct DESC;"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_portfolio_item(horizonte: str, perfil: str, ativo: str, categoria: str, peso_pct: float, tese: str, vigencia: str = "01/12/2026"):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO portfolios (horizonte, perfil, ativo, categoria, peso_pct, tese, vigencia, atualizado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (horizonte, perfil, ativo.upper().strip(), categoria, float(peso_pct), tese.strip(), vigencia.strip(), now_str()),
    )
    conn.commit()
    conn.close()


def update_portfolio_item(item_id: int, peso_pct: float, tese: str, vigencia: str = None):
    conn = get_connection()
    row = conn.execute("SELECT * FROM portfolios WHERE id = ?;", (item_id,)).fetchone()
    if not row:
        conn.close()
        return None
    vig = (vigencia or "").strip() or row["vigencia"]
    conn.execute(
        """
        UPDATE portfolios
        SET peso_pct = ?, tese = ?, vigencia = ?, atualizado_em = ?
        WHERE id = ?;
        """,
        (float(peso_pct), tese.strip(), vig, now_str(), item_id),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM portfolios WHERE id = ?;", (item_id,)).fetchone()
    conn.close()
    return dict(updated) if updated else None


def _vigencia_sort_key(val: str):
    try:
        return (1, datetime.strptime(str(val).strip(), "%d/%m/%Y"))
    except ValueError:
        return (0, datetime.min)


def get_portfolio_weight_summary() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT horizonte, perfil, peso_pct, vigencia FROM portfolios;"
    ).fetchall()
    conn.close()

    buckets = {}
    for r in rows:
        key = (r["horizonte"], r["perfil"])
        b = buckets.setdefault(key, {"qtd": 0, "total_peso": 0.0, "vigencias": []})
        b["qtd"] += 1
        b["total_peso"] += float(r["peso_pct"] or 0.0)
        if r["vigencia"]:
            b["vigencias"].append(r["vigencia"])

    horizontes = ["Curto (2 anos)", "Médio (5 anos)", "Longo (10+ anos)"]
    perfis = ["Conservador", "Moderado", "Agressivo"]
    summary = []
    for h in horizontes:
        for p in perfis:
            item = buckets.get((h, p))
            qtd = item["qtd"] if item else 0
            total_peso = round(item["total_peso"], 2) if item else 0.0
            vigencia = max(item["vigencias"], key=_vigencia_sort_key) if (item and item["vigencias"]) else "-"
            summary.append(
                {
                    "horizonte": h,
                    "perfil": p,
                    "qtd": qtd,
                    "total_peso": total_peso,
                    "vigencia": vigencia,
                    "ok": abs(total_peso - 100.0) < 0.01,
                }
            )
    return summary


def get_portfolio_combo_weight(horizonte: str, perfil: str) -> float:
    conn = get_connection()
    row = conn.execute(
        "SELECT ROUND(COALESCE(SUM(peso_pct), 0.0), 2) AS total FROM portfolios WHERE horizonte = ? AND perfil = ?;",
        (horizonte, perfil),
    ).fetchone()
    conn.close()
    return float(row["total"]) if row else 0.0


def delete_portfolio_item(item_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM portfolios WHERE id = ?;", (item_id,))
    conn.commit()
    conn.close()


# ==============================================================================
# ACADEMIA EDUCACIONAL & CERTIFICAÇÃO AVANÇADA
# ==============================================================================
def _is_hashed_pin(stored: str) -> bool:
    return str(stored or "").startswith(("scrypt:", "pbkdf2:"))


def register_student(nome: str, email: str, documento: str, pin: str) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        pin_hash = generate_password_hash(pin.strip())
        cur.execute(
            """
            INSERT INTO academy_students (nome, email, documento, pin, criado_em)
            VALUES (?, ?, ?, ?, ?);
            """,
            (nome.strip(), email.strip().lower(), documento.strip(), pin_hash, now_str()),
        )
        sid = cur.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM academy_students WHERE id = ?;", (sid,)).fetchone()
        return dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def authenticate_student(email: str, pin: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM academy_students WHERE LOWER(email) = LOWER(?) LIMIT 1;",
            (email.strip(),),
        ).fetchone()
        if not row:
            return None

        stored = str(row["pin"] or "")
        candidate = pin.strip()
        if _is_hashed_pin(stored):
            valid = check_password_hash(stored, candidate)
        else:
            valid = hmac.compare_digest(stored, candidate)
            if valid:
                conn.execute(
                    "UPDATE academy_students SET pin = ? WHERE id = ?;",
                    (generate_password_hash(candidate), row["id"]),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM academy_students WHERE id = ?;", (row["id"],)).fetchone()

        return dict(row) if valid else None
    finally:
        conn.close()


def get_student_by_id(student_id: int):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM academy_students WHERE id = ?;", (student_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def issue_certificate(student_id: int, nota_pct: float, acertos: int, total_questoes: int) -> dict:
    conn = get_connection()
    try:
        codigo = f"CERT-HRK-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO certificates (student_id, codigo, nota_pct, acertos, total_questoes, emitido_em)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (student_id, codigo, round(nota_pct, 1), acertos, total_questoes, now_str()),
        )
        cid = cur.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM certificates WHERE id = ?;", (cid,)).fetchone()
        return dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_student_certificates(student_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM certificates WHERE student_id = ? ORDER BY id DESC;",
        (student_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_certificate_by_code(codigo: str):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT c.*, s.nome AS student_nome, s.email AS student_email, s.documento AS student_documento
        FROM certificates c
        JOIN academy_students s ON s.id = c.student_id
        WHERE UPPER(c.codigo) = UPPER(?)
        LIMIT 1;
        """,
        (codigo.strip(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None
