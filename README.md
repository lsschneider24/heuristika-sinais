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

## Auditoria Automática & Gate de Fases (Regra Obrigatória)

- **NENHUMA fase pode ser declarada concluída** sem executar `python audit/run_audit.py` e obter um relatório em `audit/reports/audit_AAAA-MM-DD_HHMM.md` com **`exit code 0`** gerado naquele momento.
- Se o script de auditoria falhar, corrija o problema e execute novamente até retornar `exit code 0`. Nunca declare "testes OK" sem citar o caminho do relatório gerado.
- Instruções do Agente Auditor independente estão em [AUDITOR.md](AUDITOR.md).

## Publicação Gratuita (Cloudflare Tunnel)

- **Link rápido gratuito:** Execute `publicar_tunnel.bat` (gera uma URL `https://*.trycloudflare.com` na hora).
- **Domínio próprio fixo:** Configure `cloudflared-config.yml` a partir de `cloudflared-config.example.yml` e execute `publicar_dominio_fixo.bat`.

## Laboratório de Estratégias, Agente e Botão Único
- **Interface:** `/carteiras` inclui o painel *Gerente de Estratégias & Radar Global* (comparador, fila de propostas com aprovação Admin, Radar Global e chat determinístico). No bundle estático do GitHub Pages, chat e aprovação ficam desabilitados.
- **Agente (`strategy_agent.py`):** modo determinístico por padrão (`LLM_ENABLED=false`), 12 ferramentas e recusa de recomendação personalizada.
- **Botão Único ("Atualizar laboratório"):** disponível no `/admin` (`POST /api/admin/atualizar-laboratorio`) e via `powershell -ExecutionPolicy Bypass -File .\atualizar_tudo.ps1`.
