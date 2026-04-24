# Solana Memecoin Scanner

Scanner de memecoins Solana em tempo real via Pump.fun WebSocket.
Detecta tokens novos com filtros de Market Cap, liquidez e momentum. Meta diaria de 10%.

## Estrutura

```
solana-memecoin-scanner/
|-- scanner.py          # Core: listener Pump.fun WebSocket (rode este)
|-- filters.py          # Logica de filtragem dos tokens
|-- alerts.py           # Alertas no terminal + Telegram opcional
|-- tracker.py          # Controle de meta diaria de 10%
|-- config.py           # CONFIGURACOES - edite aqui os seus parametros
|-- requirements.txt    # Dependencias Python
```

## Como Rodar

### 1. Pre-requisitos
- Python 3.11 ou superior
- Conexao com internet

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar parametros (opcional)
Edite o arquivo `config.py` com seus parametros:
- `CAPITAL_TOTAL` = seu capital em USD
- `MC_MIN` / `MC_MAX` = faixa de market cap (padrao: $3K-$20K)
- `LIQUIDEZ_MIN` = liquidez minima (padrao: $500)
- `META_DIARIA_PCT` = meta de lucro por dia (padrao: 10%)
- `TAMANHO_POSICAO` = valor por trade em USD (padrao: $20)

### 4. Rodar o scanner
```bash
python scanner.py
```

### 5. O que voce vai ver no terminal
```
[NOVO] GRIND (GrindToken) | 4vw54BmA...
[REPROVADO] GRIND MC=$1,200 Liq=$300 | MC muito baixo
[NOVO] STAR (StarMeme) | 9xK32mBn...

=======================================================
  ALERTA - TOKEN APROVADO [14:23:01]
=======================================================
  Token:       STAR (StarMeme)
  Market Cap:  $4,560
  Liquidez:    $1,200
  Idade:       2.3 min
  Variacao 5m: +45.2%
  DEX:         https://dexscreener.com/solana/...
=======================================================
  Meta hoje:   $+0.00 / $10.00 (0%)
  Sugestao:    Entre com $20 | Alvo 2x
=======================================================
```

## Telegram (opcional)

Para receber alertas no Telegram:
1. Abra `@BotFather` no Telegram
2. Crie um novo bot: `/newbot`
3. Copie o token gerado
4. No `config.py`, preencha:
   - `TELEGRAM_TOKEN = 'seu_token_aqui'`
   - `TELEGRAM_CHAT_ID = 'seu_chat_id'`

## Registrar resultado de um trade

Depois de executar um trade manualmente, registre o resultado para o tracker atualizar a meta do dia:
```python
# Abra um terminal Python separado
from tracker import Tracker
t = Tracker(100)  # seu capital
t.registrar_trade('STAR', 20, +15.50)   # lucro de $15.50
t.registrar_trade('GRIND', 20, -8.00)   # perda de $8.00
print(t.status())
```

## Logs

Todos os tokens analisados sao salvos automaticamente em `scanner_log.csv` para analise posterior.

---

> Ferramenta apenas para sinalizacao. A decisao de entrada e saida e sempre manual e de sua responsabilidade.
