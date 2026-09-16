class HybridContextV1:
    """
    Reusable coarse context for the hybrid learning system.

    This context is for EXPERIENCE / POST-MORTEM grouping only.
    It is NOT a BUY/SELL signal.
    """

    @staticmethod
    def _bucket(value, edges):
        for i, edge in enumerate(edges):
            if value < edge:
                return i
        return len(edges)

    @classmethod
    def from_features(
        cls,
        r1,
        r6,
        r24,
        volatility,
    ):
        return (
            cls._bucket(r1, (-0.003, 0.003)),
            cls._bucket(r6, (-0.01, 0.01)),
            cls._bucket(r24, (-0.03, 0.03)),
            cls._bucket(volatility, (0.004, 0.012)),
        )

    @classmethod
    def from_experience(cls, experience):
        return cls.from_features(
            experience.r1,
            experience.r6,
            experience.r24,
            experience.volatility,
        )

    @classmethod
    def from_state(cls, state):
        if len(state) < 4:
            raise ValueError("state must contain at least 4 features")

        # StateEncoder already returns discrete buckets.
        # Convert the first four dimensions directly.
        return (
            int(state[0]),
            int(state[1]),
            int(state[2]),
            int(state[3]),
        )


def audit():
    samples = [
        (0.001, 0.004, 0.012, 0.006),
        (0.002, 0.006, 0.015, 0.007),
        (-0.006, -0.020, -0.040, 0.020),
        (0.010, 0.020, 0.050, 0.020),
    ]

    contexts = [
        HybridContextV1.from_features(*x)
        for x in samples
    ]

    assert contexts[0] == contexts[1]
    assert contexts[0] != contexts[2]
    assert contexts[2] != contexts[3]

    class E:
        r1 = 0.001
        r6 = 0.004
        r24 = 0.012
        volatility = 0.006

    assert HybridContextV1.from_experience(E()) == contexts[0]

    state = (2, 2, 2, 1, 3, 0)
    assert HybridContextV1.from_state(state) == (2, 2, 2, 1)

    print("HYBRID CONTEXT V1 AUDIT = PASS")


if __name__ == "__main__":
    audit()
