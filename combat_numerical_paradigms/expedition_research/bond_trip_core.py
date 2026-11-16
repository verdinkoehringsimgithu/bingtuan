"""Isolated persistent limits over each configured compound-bond engine."""
from contextvars import ContextVar
from functools import lru_cache
import inspect
import json

import trip_core
from configured_compound_core import configured


@lru_cache(None)
def adapter(encoded='{}'):
    source = configured(json.loads(encoded))
    limits = ContextVar('compound_trip_limits', default=(1.,) * 5)

    class Team(source.Team):
        def __init__(self, *args, **kwargs):
            self.travel_factors = (1.,) * 5
            self.minimum_bp_fraction = 1.
            super().__init__(*args, **kwargs)
            if self.side == 0:
                self.travel_factors = limits.get()
                self.max_bp *= self.travel_factors[0]
                self.current_bp = self.max_bp

        def get_effective_stats(self):
            return tuple(v * f for v, f in zip(super().get_effective_stats(), self.travel_factors[1:]))

        def add(self, key, value):
            super().add(key, value)
            if key == 'damage_received' and self.max_bp > 0:
                self.minimum_bp_fraction = min(self.minimum_bp_fraction, max(0., self.current_bp) / self.max_bp)

    namespace = {**source._simulate_ns, 'Team': Team}
    exec(compile(inspect.getsource(source.frozen.simulate), '<compound-expedition>', 'exec'), namespace)
    native = namespace['simulate']

    def simulate(*args, factors=(1.,) * 5, **kwargs):
        assert len(factors) == 5 and all(0 < f <= 1 for f in factors)
        token = limits.set(tuple(factors))
        try:
            result, trace, a, b = native(*args, **kwargs)
        finally:
            limits.reset(token)
        result.update(minimum_bp_fraction=a.minimum_bp_fraction,
            damage_exposure=min(1., a.metrics['damage_received'] / a.max_bp),
            effective_max_bp=a.max_bp, travel_factors=list(factors),
            first_events=a.first_events, enemy_first_events=b.first_events,
            maid_effect_level=a.maid_level if a.active('maid') else 0)
        return result, trace, a, b

    return simulate


def configured_trip(parameters):
    return adapter(json.dumps(parameters, sort_keys=True))
