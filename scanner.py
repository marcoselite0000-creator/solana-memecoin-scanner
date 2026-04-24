# ============================================================
# scanner.py — Nucleo do sistema: escuta Pump.fun em tempo real
# Fonte: wss://pumpportal.fun/api/data (100% gratuito)
# ============================================================

import asyncio
import json
import time
import csv
import os
from datetime import datetime
import websockets

from config import PUMP_WS_URL, LOG_FILE, CAPITAL_TOTAL
from filters import analisar_token
from alerts import alertar_terminal, alertar_telegram
from tracker import Tracker


def inicializar_log():
    """Cria o arquivo CSV de log se nao existir."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'mint', 'nome', 'simbolo',
                'mc', 'liquidez', 'idade_min',
                'variacao_5m', 'aprovado', 'razoes'
            ])


def salvar_log(dados: dict):
    """Salva um token analisado no CSV de log."""
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            dados.get('mint', ''),
            dados.get('nome', ''),
            dados.get('simbolo', ''),
            dados.get('mc', 0),
            dados.get('liquidez', 0),
            round(dados.get('idade_min', 0), 2),
            dados.get('variacao_5m', 0),
            dados.get('aprovado', False),
            ' | '.join(dados.get('razoes_reprovado', []))
        ])


async def processar_token(mint_address: str, tracker: Tracker):
    """
    Recebe um mint address novo do Pump.fun,
    analisa e alerta se passar nos filtros.
    """
    if tracker.meta_batida():
        return  # Meta diaria atingida, para de processar

    if tracker.stop_diario_atingido():
        return  # Stop diario atingido, para de operar

    # Pequena pausa para dar tempo do Dexscreener indexar o token
    await asyncio.sleep(2)

    dados = analisar_token(mint_address)
    if not dados:
        return

    salvar_log(dados)

    if dados['aprovado']:
        alertar_terminal(dados, tracker)
        await alertar_telegram(dados, tracker)
    else:
        # Log silencioso para tokens reprovados
        print(f"[REPROVADO] {dados.get('simbolo','?')} "
              f"MC=${dados.get('mc',0):,.0f} "
              f"Liq=${dados.get('liquidez',0):,.0f} "
              f"| {', '.join(dados.get('razoes_reprovado', []))}")


async def escutar_pump():
    """
    Conecta ao WebSocket do Pump.fun e escuta novos tokens em tempo real.
    Reconecta automaticamente em caso de queda.
    """
    tracker = Tracker(CAPITAL_TOTAL)
    inicializar_log()

    print("=" * 60)
    print(" SOLANA MEMECOIN SCANNER - Iniciando...")
    print(f" Capital: ${CAPITAL_TOTAL} | Meta: +{tracker.meta_pct}%/dia")
    print(f" Filtros: MC ${tracker.mc_min:,}-${tracker.mc_max:,}")
    print("=" * 60)

    while True:
        try:
            print(f"\n[WS] Conectando ao Pump.fun...")
            async with websockets.connect(
                PUMP_WS_URL,
                ping_interval=20,
                ping_timeout=10
            ) as ws:
                # Inscreve no feed de novos tokens
                payload = {"method": "subscribeNewToken"}
                await ws.send(json.dumps(payload))
                print("[WS] Conectado! Escutando novos tokens...\n")

                async for message in ws:
                    try:
                        data = json.loads(message)

                        # Pega o mint address do novo token
                        mint = data.get('mint') or data.get('mintAddress')
                        if not mint:
                            continue

                        nome = data.get('name', 'N/A')
                        simbolo = data.get('symbol', 'N/A')
                        print(f"[NOVO] {simbolo} ({nome}) | {mint[:8]}...")

                        # Processa em background para nao bloquear o stream
                        asyncio.create_task(
                            processar_token(mint, tracker)
                        )

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"[ERRO] Processando mensagem: {e}")

        except websockets.exceptions.ConnectionClosed:
            print("[WS] Conexao fechada. Reconectando em 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[WS] Erro de conexao: {e}. Reconectando em 10s...")
            await asyncio.sleep(10)


def main():
    """Ponto de entrada principal."""
    try:
        asyncio.run(escutar_pump())
    except KeyboardInterrupt:
        print("\n[INFO] Scanner encerrado pelo usuario.")


if __name__ == '__main__':
    main()
