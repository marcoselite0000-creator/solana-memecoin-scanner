# ============================================================
# alerts.py — Sistema de alertas (terminal + Telegram opcional)
# ============================================================

import asyncio
from datetime import datetime
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

try:
    import httpx
    HTTPX_DISPONIVEL = True
except ImportError:
    HTTPX_DISPONIVEL = False


def formatar_alerta(dados: dict, tracker) -> str:
    """Formata a mensagem de alerta com todos os dados do token."""
    hora = datetime.now().strftime('%H:%M:%S')
    simbolo = dados.get('simbolo', 'N/A')
    nome = dados.get('nome', 'N/A')
    mc = dados.get('mc', 0)
    liquidez = dados.get('liquidez', 0)
    idade = dados.get('idade_min', 0)
    variacao_5m = dados.get('variacao_5m', 0)
    dex_url = dados.get('dex_url', '')
    mint = dados.get('mint', '')

    lucro_dia = tracker.lucro_hoje_usd()
    meta_usd = tracker.meta_usd()
    pct_meta = (lucro_dia / meta_usd * 100) if meta_usd > 0 else 0

    msg = (
        f"\n{'='*55}\n"
        f"  ALERTA - TOKEN APROVADO [{hora}]\n"
        f"{'='*55}\n"
        f"  Token:       {simbolo} ({nome})\n"
        f"  Market Cap:  ${mc:,.0f}\n"
        f"  Liquidez:    ${liquidez:,.0f}\n"
        f"  Idade:       {idade:.1f} min\n"
        f"  Variacao 5m: {variacao_5m:+.1f}%\n"
        f"  Mint:        {mint[:20]}...\n"
        f"  DEX:         {dex_url}\n"
        f"{'='*55}\n"
        f"  Meta hoje:   ${lucro_dia:+.2f} / ${meta_usd:.2f} ({pct_meta:.0f}%)\n"
        f"  Sugestao:    Entre com ${tracker.tamanho_posicao} | Alvo 2x\n"
        f"{'='*55}\n"
    )
    return msg


def alertar_terminal(dados: dict, tracker):
    """Exibe o alerta colorido no terminal."""
    msg = formatar_alerta(dados, tracker)
    print(msg)


async def alertar_telegram(dados: dict, tracker):
    """
    Envia alerta via Telegram Bot (opcional).
    Requer TELEGRAM_TOKEN e TELEGRAM_CHAT_ID configurados no config.py.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return  # Telegram nao configurado

    if not HTTPX_DISPONIVEL:
        print("[TELEGRAM] httpx nao instalado. Instale com: pip install httpx")
        return

    simbolo = dados.get('simbolo', 'N/A')
    nome = dados.get('nome', 'N/A')
    mc = dados.get('mc', 0)
    liquidez = dados.get('liquidez', 0)
    idade = dados.get('idade_min', 0)
    variacao_5m = dados.get('variacao_5m', 0)
    dex_url = dados.get('dex_url', '')
    mint = dados.get('mint', '')

    texto = (
        f"SCANNER SOLANA\n"
        f"Token: {simbolo} ({nome})\n"
        f"MC: ${mc:,.0f} | Liq: ${liquidez:,.0f}\n"
        f"Idade: {idade:.1f}min | 5m: {variacao_5m:+.1f}%\n"
        f"Mint: {mint[:20]}...\n"
        f"Link: {dex_url}\n"
        f"Entrada sugerida: ${tracker.tamanho_posicao}"
    )

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': texto
            }, timeout=5)
    except Exception as e:
        print(f"[TELEGRAM] Erro ao enviar: {e}")
