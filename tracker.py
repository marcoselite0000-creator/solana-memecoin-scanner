# ============================================================
# tracker.py — Controle de meta diaria e gestao de capital
# ============================================================

from datetime import date
from config import (
    META_DIARIA_PCT, STOP_DIARIO_PCT,
    TAMANHO_POSICAO, MC_MIN, MC_MAX
)


class Tracker:
    """
    Controla o progresso diario de lucro/perda.
    Reset automatico a cada novo dia.
    """

    def __init__(self, capital_total: float):
        self.capital = capital_total
        self.meta_pct = META_DIARIA_PCT
        self.stop_pct = STOP_DIARIO_PCT
        self.tamanho_posicao = TAMANHO_POSICAO
        self.mc_min = MC_MIN
        self.mc_max = MC_MAX

        self._lucro_hoje = 0.0
        self._data_atual = date.today()
        self._trades_hoje = []
        self._total_alertas = 0
        self._total_tokens_scaneados = 0

    def _checar_reset_diario(self):
        """Reseta os contadores se for um novo dia."""
        hoje = date.today()
        if hoje != self._data_atual:
            print(f"\n[TRACKER] Novo dia ({hoje}). Resetando contadores...")
            self._lucro_hoje = 0.0
            self._data_atual = hoje
            self._trades_hoje = []
            self._total_alertas = 0

    def registrar_trade(self, simbolo: str, valor_entrada: float, resultado_usd: float):
        """
        Registra o resultado de um trade manualmente.
        Use isto para atualizar o lucro/perda do dia.
        """
        self._checar_reset_diario()
        self._lucro_hoje += resultado_usd
        self._trades_hoje.append({
            'simbolo': simbolo,
            'entrada': valor_entrada,
            'resultado': resultado_usd
        })
        status = 'LUCRO' if resultado_usd >= 0 else 'PERDA'
        print(f"[TRADE] {simbolo}: {status} ${resultado_usd:+.2f} | Dia: ${self._lucro_hoje:+.2f}")

    def registrar_alerta(self):
        """Incrementa o contador de alertas disparados."""
        self._checar_reset_diario()
        self._total_alertas += 1

    def registrar_scan(self):
        """Incrementa o contador de tokens scaneados."""
        self._total_tokens_scaneados += 1

    def lucro_hoje_usd(self) -> float:
        """Retorna o lucro/perda acumulado hoje em USD."""
        self._checar_reset_diario()
        return self._lucro_hoje

    def meta_usd(self) -> float:
        """Retorna a meta diaria em USD."""
        return self.capital * (self.meta_pct / 100)

    def stop_usd(self) -> float:
        """Retorna o limite de perda diaria em USD."""
        return self.capital * (self.stop_pct / 100)

    def meta_batida(self) -> bool:
        """Retorna True se a meta diaria foi atingida."""
        self._checar_reset_diario()
        if self._lucro_hoje >= self.meta_usd():
            print(f"[META] Meta diaria de ${self.meta_usd():.2f} atingida! Parando por hoje.")
            return True
        return False

    def stop_diario_atingido(self) -> bool:
        """Retorna True se o stop loss diario foi atingido."""
        self._checar_reset_diario()
        if self._lucro_hoje <= -self.stop_usd():
            print(f"[STOP] Stop diario de -${self.stop_usd():.2f} atingido! Parando por hoje.")
            return True
        return False

    def status(self) -> str:
        """Retorna um resumo do status atual."""
        self._checar_reset_diario()
        lucro = self._lucro_hoje
        meta = self.meta_usd()
        stop = self.stop_usd()
        pct = (lucro / meta * 100) if meta > 0 else 0

        return (
            f"[STATUS {self._data_atual}] "
            f"Lucro: ${lucro:+.2f} / Meta: ${meta:.2f} ({pct:.0f}%) | "
            f"Trades: {len(self._trades_hoje)} | "
            f"Alertas: {self._total_alertas} | "
            f"Scaneados: {self._total_tokens_scaneados}"
        )
