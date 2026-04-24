# ============================================================
# config.py — Configuracoes centrais do Solana Memecoin Scanner
# Edite estes valores conforme sua estrategia
# ============================================================

# --- FILTROS DE ENTRADA ---
MC_MIN = 3_000          # Market cap minimo em USD para considerar o token
MC_MAX = 20_000         # Market cap maximo em USD para considerar o token
LIQUIDEZ_MIN = 500      # Liquidez minima em USD no pool
IDADE_MAX_MIN = 10      # Idade maxima do token em minutos desde o lancamento
DEV_MAX_PERCENT = 20    # % maximo que o dev pode segurar do supply

# --- GESTAO DE CAPITAL ---
CAPITAL_TOTAL = 100     # Capital total em USD disponivel para trading
TAMANHO_POSICAO = 20    # Valor em USD por trade (ex: $20 por entrada)
META_DIARIA_PCT = 10    # Meta de lucro diario em % (ex: 10 = 10%)
STOP_DIARIO_PCT = 5     # Stop loss diario em % (para o dia se perder isso)

# --- ALVOS POR TRADE ---
TAKE_PROFIT_X = 2.0     # Vende quando preco dobrar (2x)
STOP_LOSS_PCT = 50      # Stop loss por trade em % de perda

# --- TELEGRAM ALERTS ---
TELEGRAM_TOKEN = '8508360616:AAF1sc8PzkkRcPWT5H-TgGusaKJXw4BHbyU'
TELEGRAM_CHAT_ID = '8751092942'

# --- FONTES DE DADOS (gratuitas) ---
PUMP_WS_URL = 'wss://pumpportal.fun/api/data'
DEXSCREENER_API = 'https://api.dexscreener.com/latest/dex/tokens/'
SOLANA_RPC = 'https://api.mainnet-beta.solana.com'

# --- LOGS ---
LOG_FILE = 'scanner_log.csv'  # Arquivo onde todos os tokens detectados sao salvos
