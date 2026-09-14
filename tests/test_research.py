from bot.research import ResearchCandidate, ResearchEngine


def test_research_engine_starts_empty():
    engine = ResearchEngine()

    assert engine.count() == 0
    assert engine.names() == []


def test_research_engine_registers_candidate():
    candidate = ResearchCandidate(
        name="test-strategy",
        strategy_factory=lambda: object(),
        description="test",
    )

    engine = ResearchEngine()
    engine.register(candidate)

    assert engine.count() == 1
    assert engine.names() == ["test-strategy"]


def test_research_engine_rejects_invalid_candidate():
    engine = ResearchEngine()

    try:
        engine.register("invalid")
    except TypeError:
        pass
    else:
        raise AssertionError("Expected TypeError")


def test_research_engine_builds_strategies():
    candidate = ResearchCandidate(
        name="test-strategy",
        strategy_factory=lambda: object(),
    )

    engine = ResearchEngine([candidate])

    strategies = engine.build_strategies()

    assert "test-strategy" in strategies
    assert strategies["test-strategy"] is not None


def test_research_engine_rejects_empty_factory():
    candidate = ResearchCandidate(
        name="broken-strategy",
        strategy_factory=lambda: None,
    )

    engine = ResearchEngine([candidate])

    try:
        engine.build_strategies()
    except ValueError as exc:
        assert "broken-strategy" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_research_engine_description():
    candidate = ResearchCandidate(
        name="trend",
        strategy_factory=lambda: object(),
        description="Trend following",
    )

    engine = ResearchEngine([candidate])

    result = engine.describe()

    assert result == [
        {
            "name": "trend",
            "description": "Trend following",
        }
    ]


def test_research_engine_ranking():
    results = [
        type(
            "Result",
            (),
            {
                "name": "bad",
                "status": "REJECT",
                "test_expectancy": -1.0,
                "test_profit_factor": 0.5,
                "test_drawdown_pct": 5.0,
            },
        )(),
        type(
            "Result",
            (),
            {
                "name": "good",
                "status": "SURVIVE",
                "test_expectancy": 1.0,
                "test_profit_factor": 2.0,
                "test_drawdown_pct": 1.0,
            },
        )(),
    ]

    engine = ResearchEngine()

    ranked = engine.rank(results)

    assert ranked[0].name == "good"
    assert ranked[1].name == "bad"
