# DNBB Deals

Radar automatizado de preços para MacBooks e equipamentos Pioneer DJ / AlphaTheta.

## O que já funciona

- Busca pública via API do Mercado Livre.
- Catálogo configurável em `catalog.json`.
- Filtros contra acessórios, peças e anúncios defeituosos.
- Histórico de preços em SQLite.
- Score de oferta de 0 a 100.
- Alertas por Telegram.
- Execução automática a cada quatro horas pelo GitHub Actions.
- Testes automatizados do filtro e da lógica de alerta.

## Executar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Sem credenciais do Telegram, as ofertas são impressas no terminal.

## Configurar Telegram no GitHub

Crie estes secrets no repositório:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Depois execute manualmente o workflow **Monitor deals** ou aguarde a agenda automática.

## Produtos iniciais

- MacBook Air M2
- MacBook Air M3
- DDJ-FLX4
- DDJ-FLX10
- XDJ-RX3
- OPUS-QUAD

Os preços-alvo podem ser alterados diretamente em `catalog.json`.
