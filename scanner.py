# ============================================================
# scanner.py — Nucleo do sistema: escuta Pump.fun em tempo real
# v3: Paper Trading integrado inline | Sem narrativas# ============================================================

import asyncio
import json
import time
import csv
import os
from datetime import datetime
import websockets
import requests

from config import PUMP_WS_URL, LOG_FILE, CAPITAL_TOTAL, MC_MIN, MC_MAX, LIQUIDEZ_MIN, IDADE_MAX_MIN, TAMANHO_POSICAO
from alerts import alertar_terminal, alertar_telegram
from tracker import Tracker

# ===== PAPER TRADING (inline) =====
SUPPLY_PADRAO = 1_000_000_000
PAPER_POSITIONS = {}
PAPER_CAPITAL = CAPITAL_TOTAL
PAPER_TP_PCT = 15
PAPER_SL_PCT = 10
PAPER_MAX_POS = 3
PAPER_SIZE = 100

def paper_abrir(mint, nome, simbolo, mc, preco):
    global PAPER_POSITIONS
    if len(PAPER_POSITIONS) >= PAPER_MAX_POS or mint in PAPER_POSITIONS:
        return False
    PAPER_POSITIONS[mint] = {'preco': preco, 'mc': mc, 'hora': datetime.now(), 'nome': nome, 'simbolo': simbolo}
    print(f"[PAPER] Abriu: {simbolo} @ ${preco:.10f} | MC ${mc:,.0f}")
    return True

def paper_verificar():
    global PAPER_POSITIONS, PAPER_CAPITAL
    for mint in list(PAPER_POSITIONS.keys()):
        pos = PAPER_POSITIONS[mint]
        try:
            resp = requests.get(f'https://frontend-api.pump.fun/coins/{mint}', timeout=5)
            data = resp.json()
            mc_atual = data.get('usd_market_cap', 0)
            preco_atual = mc_atual / SUPPLY_PADRAO if SUPPLY_PADRAO > 0 else 0
            if preco_atual > 0:
                lucro_pct = ((preco_atual - pos['preco']) / pos['preco']) * 100
                if lucro_pct >= PAPER_TP_PCT:
                    lucro = (PAPER_SIZE * lucro_pct) / 100
                    PAPER_CAPITAL += lucro
                    print(f"[PAPER] ✅ TP! {pos['simbolo']} | +{lucro_pct:.1f}% | +${lucro:.2f}")
                    del PAPER_POSITIONS[mint]
                elif lucro_pct <= -PAPER_SL_PCT:
                    perda = (PAPER_SIZE * abs(lucro_pct)) / 100
                    PAPER_CAPITAL -= perda
                    print(f"[PAPER] ❌ SL! {pos['simbolo']} | {lucro_pct:.1f}% | -${perda:.2f}")
                    del PAPER_POSITIONS[mint]
        except:
            pass

def paper_status():
    lucro = PAPER_CAPITAL - CAPITAL_TOTAL
    pct = (lucro / CAPITAL_TOTAL) * 100 if CAPITAL_TOTAL > 0 else 0
    return f"[PAPER] Capital: ${PAPER_CAPITAL:.2f} | Lucro: ${lucro:+.2f} ({pct:+.1f}%) | Pos: {len(PAPER_POSITIONS)}/{PAPER_MAX_POS}"
# ===================================

# Preco do SOL em USD (atualizado a cada 5 min)
SOL_PRICE_USD = 86.0
_sol_price_last_update = 0


def get_sol_price() -> float:
    """Busca o preco atual do SOL em USD. Cache de 5 minutos."""
    global SOL_PRICE_USD, _sol_price_last_update
    agora = time.time()
    if agora - _sol_price_last_update > 300:  # atualiza a cada 5 min
        try:
            resp = requests.get(
                'https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd',
                timeout=5
            )
            SOL_PRICE_USD = resp.json()['solana']['usd']
            _sol_price_last_update = agora
            print(f"[SOL] Preco atualizado: ${SOL_PRICE_USD}")
        except Exception:
            pass  # Usa o ultimo preco conhecido
    return SOL_PRICE_USD


def inicializar_log():
    """Cria o arquivo CSV de log se nao existir."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'mint', 'nome', 'simbolo',
                'mc', 'liquidez', 'aprovado', 'razoes'
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
            dados.get('aprovado', False),
            ' | '.join(dados.get('razoes_reprovado', []))
        ])


def extrair_dados_pump(data: dict) -> dict:
    """
    Extrai e calcula MC e liquidez a partir dos dados
    enviados pelo proprio WebSocket do Pump.fun.
    """
    sol_price = get_sol_price()

    mint = data.get('mint', '')
    nome = data.get('name', 'N/A')
    simbolo = data.get('symbol', 'N/A')

    # MC em SOL -> USD
    # O Pump.fun envia marketCapSol ou vSolInBondingCurve
    mc_sol = float(data.get('marketCapSol', 0) or data.get('vSolInBondingCurve', 0) or 0)
    mc_usd = mc_sol * sol_price

    # Liquidez: usa vSolInBondingCurve como proxy da liquidez
    liq_sol = float(data.get('vSolInBondingCurve', 0) or 0)
    liq_usd = liq_sol * sol_price

    # Link Pump.fun e Dexscreener
    pump_url = f"https://pump.fun/{mint}"
    dex_url = f"https://dexscreener.com/solana/{mint}"

    return {
        'mint': mint,
        'nome': nome,
        'simbolo': simbolo,
        'mc': mc_usd,
        'liquidez': liq_usd,
        'mc_sol': mc_sol,
        'liq_sol': liq_sol,
        'pump_url': pump_url,
        'dex_url': dex_url,
        'idade_min': 0,  # token acabou de nascer
        'variacao_5m': 0,
                'preco_token_usd': mc_usd / SUPPLY_PADRAO if SUPPLY_PADRAO > 0 else 0,
    }


def aplicar_filtros(dados: dict) -> tuple:
    """Aplica os filtros e retorna (aprovado, lista_razoes)."""
    reprovado = []

    mc = dados.get('mc', 0)
    liq = dados.get('liquidez', 0)

    if mc < MC_MIN:
        reprovado.append(f"MC baixo: ${mc:,.0f} < ${MC_MIN:,}")
    elif mc > MC_MAX:
        reprovado.append(f"MC alto: ${mc:,.0f} > ${MC_MAX:,}")

    if liq < LIQUIDEZ_MIN:
        reprovado.append(f"Liquidez baixa: ${liq:,.0f} < ${LIQUIDEZ_MIN:,}")

    return len(reprovado) == 0, reprovado


async def processar_token(data: dict, tracker: Tracker):
    """Processa um token recebido do WebSocket do Pump.fun."""
    if tracker.meta_batida() or tracker.stop_diario_atingido():
        return

    dados = extrair_dados_pump(data)
    aprovado, razoes = aplicar_filtros(dados)
    dados['aprovado'] = aprovado
    dados['razoes_reprovado'] = razoes

    salvar_log(dados)

    if aprovado:
        alertar_terminal(dados, tracker)
        await alertar_telegram(dados, tracker)
        tracker.registrar_alerta()

                # Paper Trading: abre posicao
        if len(PAPER_POSITIONS) < PAPER_MAX_POS:
            preco = dados.get('preco_token_usd', 0)
            if preco > 0:
                paper_abrir(dados['mint'], dados['nome'], dados['simbolo'], dados['mc'], preco)
    else:
        simbolo = dados.get('simbolo', '?')
        mc = dados.get('mc', 0)
        liq = dados.get('liquidez', 0)
        print(f"[REPROVADO] {simbolo} MC=${mc:,.0f} Liq=${liq:,.0f} | {', '.join(razoes)}")

    tracker.registrar_scan()
async def verificar_posicoes_loop():
    '''Loop de verificacao de posicoes paper trading'''
    while True:
        try:
            paper_verificar()
        except:
            pass
        await asyncio.sleep(30)



async def escutar_pump():
    """Conecta ao Pump.fun WebSocket e escuta novos tokens em tempo real."""
    tracker = Tracker(CAPITAL_TOTAL)
    inicializar_log()
    get_sol_price()  # busca preco inicial do SOL
        asyncio.create_task(verificar_posicoes_loop())

    print("=" * 60)
    print(" SOLANA MEMECOIN SCANNER v3 - Paper Trading - Iniciando...")
    print(f" Capital: ${CAPITAL_TOTAL} | Meta: +{tracker.meta_pct}%/dia")
    print(f" Filtros: MC ${MC_MIN:,}-${MC_MAX:,} | Liq min: ${LIQUIDEZ_MIN:,}")
    print(f" SOL Price: ${get_sol_price()}")
    print("=" * 60)
        print(f" {paper_status()}")

    while True:
        try:
            print(f"\n[WS] Conectando ao Pump.fun...")
            async with websockets.connect(
                PUMP_WS_URL,
                ping_interval=20,
                ping_timeout=10
            ) as ws:
                payload = {"method": "subscribeNewToken"}
                await ws.send(json.dumps(payload))
                print("[WS] Conectado! Escutando novos tokens...\n")

                async for message in ws:
                    try:
                        data = json.loads(message)
                        mint = data.get('mint') or data.get('mintAddress')
                        if not mint:
                            continue

                        nome = data.get('name', 'N/A')
                        simbolo = data.get('symbol', 'N/A')
                        print(f"[NOVO] {simbolo} ({nome}) | {mint[:8]}...")

                        asyncio.create_task(processar_token(data, tracker))

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"[ERRO] {e}")

        except websockets.exceptions.ConnectionClosed:
            print("[WS] Conexao fechada. Reconectando em 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[WS] Erro: {e}. Reconectando em 10s...")
            await asyncio.sleep(10)


def main():
    try:
        asyncio.run(escutar_pump())
    except KeyboardInterrupt:
        print("\n[INFO] Scanner encerrado.")


if __name__ == '__main__':
    main()
