# SinaisVIP Terminal — MVP

Sistema completo de **Sinais de Mercado** com **Site Web (Vitrine + Área VIP + Admin)**, **Motor de Sinais + Auditor Automático de Erros e Acertos**, **SQLite (`sinais_vip.db`)** e **Disparador Telegram**.

## Como executar no Windows

1. Copie `.env.example` para `.env` e preencha suas credenciais.
2. Execute `iniciar.bat` (cria `.venv`, instala dependências, popula os 4 sinais iniciais no SQLite e sobe o servidor Flask).

Ou manualmente:
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python app.py
```

## URLs Locais

- Vitrine Pública & Transparência: `http://127.0.0.1:5000/`
- Login & Área VIP: `http://127.0.0.1:5000/login` e `http://127.0.0.1:5000/vip` (Assinante demo: `cliente@exemplo.com` ou código `VIP-DEMO-2026`)
- Painel Administrativo: `http://127.0.0.1:5000/admin` (Senha padrão em `.env.example`: `admin123`)

## Testes

```powershell
python -m unittest discover -s tests -v
```

## Publicação Gratuita (Cloudflare Tunnel)

- **Link rápido gratuito:** Execute `publicar_tunnel.bat` (gera uma URL `https://*.trycloudflare.com` na hora).
- **Domínio próprio fixo:** Configure `cloudflared-config.yml` a partir de `cloudflared-config.example.yml` e execute `publicar_dominio_fixo.bat`.
