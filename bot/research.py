from dataclasses import dataclass
from typing import Callable, Any


@dataclass(frozen=True)
class ResearchCandidate:
    name: str
    strategy_factory: Callable
    description: str = ""


@dataclass
class ResearchResult:
    name: str
    status: str
    train_score: float
    test_pnl: float
    test_expectancy: float
    test_profit_factor: float
    test_drawdown_pct: float
    test_trades: int


class ResearchEngine:
    """
    Strategy research coordinator.

    This layer does not execute live orders.
    It evaluates strategy candidates through
    the existing backtest infrastructure.
    """

    def __init__(self, candidates=None):
        self.candidates = list(candidates or [])

    def register(self, candidate):
        if not isinstance(candidate, ResearchCandidate):
            raise TypeError("candidate must be ResearchCandidate")

        self.candidates.append(candidate)

    def names(self):
        return [candidate.name for candidate in self.candidates]

    def count(self):
        return len(self.candidates)

    def build_strategies(self):
        """
        Instantiate all registered strategy candidates.
        """
        strategies = {}

        for candidate in self.candidates:
            strategy = candidate.strategy_factory()

            if strategy is None:
                raise ValueError(
                    f"Strategy factory returned None: {candidate.name}"
                )

            strategies[candidate.name] = strategy

        return strategies

    def describe(self):
        return [
            {
                "name": candidate.name,
                "description": candidate.description,
            }
            for candidate in self.candidates
        ]

    def rank(self, results):
        """
        Rank research results without changing their parameters.

        Primary objective:
        1. surviving status
        2. expectancy
        3. profit factor
        4. lower drawdown
        """
        return sorted(
            results,
            key=lambda result: (
                result.status == "SURVIVE",
                result.test_expectancy,
                result.test_profit_factor,
                -result.test_drawdown_pct,
            ),
            reverse=True,
        )
