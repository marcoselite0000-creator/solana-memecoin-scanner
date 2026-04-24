# ============================================================
# filters.py — Logica de filtragem dos tokens detectados
# ============================================================

import requests
import time
from config import (
    MC_MIN, MC_MAX, LIQUIDEZ_MIN, IDADE_MAX_MIN,
    DEV_MAX_PERCENT, DEXSCREENER_API
)


def buscar_dados_dexscreener(mint_address: str) -> dict | None:
    """
    Busca dados do token no Dexscreener usando o mint address.
    Retorna dict com mc, liquidez, preco, etc. ou None se falhar.
    """
    try:
        url = f"{DEXSCREENER_API}{mint_address}"
        resp = requests.get(url, timeout=5)
        data = resp.json()

        pairs = data.get('pairs', [])
        if not pairs:
            return None

        # Pega o par com maior liquidez (mais confiavel)
        pair = sorted(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)), reverse=True)[0]

        return {
            'mint': mint_address,
            'nome': pair.get('baseToken', {}).get('name', 'N/A'),
            'simbolo': pair.get('baseToken', {}).get('symbol', 'N/A'),
            'mc': float(pair.get('marketCap', 0) or 0),
            'liquidez': float(pair.get('liquidity', {}).get('usd', 0) or 0),
            'preco': float(pair.get('priceUsd', 0) or 0),
            'variacao_5m': float(pair.get('priceChange', {}).get('m5', 0) or 0),
            'variacao_1h': float(pair.get('priceChange', {}).get('h1', 0) or 0),
            'volume_5m': float(pair.get('volume', {}).get('m5', 0) or 0),
            'criado_em': pair.get('pairCreatedAt', None),  # timestamp ms
            'dex_url': pair.get('url', ''),
        }
    except Exception as e:
        print(f"[FILTRO] Erro ao buscar Dexscreener para {mint_address}: {e}")
        return None


def calcular_idade_minutos(criado_em_ms) -> float:
    """Calcula quantos minutos se passaram desde a criacao do par."""
    if not criado_em_ms:
        return 999  # Desconhecido = assume velho
    agora_ms = time.time() * 1000
    diferenca_ms = agora_ms - criado_em_ms
    return diferenca_ms / 60_000


def aplicar_filtros(dados: dict) -> tuple[bool, list[str]]:
    """
    Aplica todos os filtros na ordem de prioridade.
    Retorna (passou, lista_de_razoes_reprovado).
    """
    reprovado = []

    # 1. Market Cap
    mc = dados.get('mc', 0)
    if mc < MC_MIN:
        reprovado.append(f"MC muito baixo: ${mc:,.0f} < ${MC_MIN:,}")
    elif mc > MC_MAX:
        reprovado.append(f"MC muito alto: ${mc:,.0f} > ${MC_MAX:,}")

    # 2. Liquidez
    liq = dados.get('liquidez', 0)
    if liq < LIQUIDEZ_MIN:
        reprovado.append(f"Liquidez insuficiente: ${liq:,.0f} < ${LIQUIDEZ_MIN:,}")

    # 3. Idade do token
    criado_em = dados.get('criado_em')
    idade = calcular_idade_minutos(criado_em)
    if idade > IDADE_MAX_MIN:
        reprovado.append(f"Token muito antigo: {idade:.1f} min > {IDADE_MAX_MIN} min")

    # 4. Momentum positivo (preco subindo nos ultimos 5 min)
    variacao_5m = dados.get('variacao_5m', 0)
    if variacao_5m < 0:
        reprovado.append(f"Sem momentum: variacao 5m = {variacao_5m:.1f}%")

    passou = len(reprovado) == 0
    return passou, reprovado


def analisar_token(mint_address: str) -> dict | None:
    """
    Pipeline completo: busca dados + aplica filtros.
    Retorna o dict do token se passou nos filtros, None se nao.
    """
    dados = buscar_dados_dexscreener(mint_address)
    if not dados:
        return None

    passou, razoes = aplicar_filtros(dados)
    dados['aprovado'] = passou
    dados['razoes_reprovado'] = razoes
    dados['idade_min'] = calcular_idade_minutos(dados.get('criado_em'))

    return dados
