"""Long-term player-only limits over frozen battle physics; full between fights."""
from contextvars import ContextVar
import inspect
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SYNERGY = HERE.parent / 'synergy_research'
sys.path.insert(0, str(SYNERGY))
import joint_core as base

_limits = ContextVar('expedition_limits', default=(1., 1., 1., 1., 1.))


class Team(base.Team):
    def __init__(self, *args, **kwargs):
        self.travel_factors = (1., 1., 1., 1., 1.)
        self.minimum_bp_fraction = 1.
        super().__init__(*args, **kwargs)
        if self.side == 0:
            self.travel_factors = _limits.get()
            self.max_bp *= self.travel_factors[0]
            self.current_bp = self.max_bp

    def get_effective_stats(self):
        values = super().get_effective_stats()
        return tuple(value * factor for value, factor in zip(values, self.travel_factors[1:]))

    def add(self, key, value):
        super().add(key, value)
        if key == 'damage_received' and self.max_bp > 0:
            self.minimum_bp_fraction = min(self.minimum_bp_fraction, max(0., self.current_bp) / self.max_bp)


_namespace = {**vars(base.frozen), 'Team': Team}
exec(compile(inspect.getsource(base.frozen.simulate), '<expedition-physics>', 'exec'), _namespace)
_simulate = _namespace['simulate']


def simulate(*args, factors=(1., 1., 1., 1., 1.), **kwargs):
    assert len(factors) == 5 and all(0 < x <= 1 for x in factors)
    token = _limits.set(tuple(factors))
    try:
        result, trace, a, b = _simulate(*args, **kwargs)
    finally:
        _limits.reset(token)
    result['minimum_bp_fraction'] = a.minimum_bp_fraction
    result['damage_exposure'] = min(1., a.metrics['damage_received'] / a.max_bp)
    result['effective_max_bp'] = a.max_bp
    result['travel_factors'] = list(factors)
    return result, trace, a, b


def factors(profile, wear):
    assert wear >= 0
    return tuple(math.exp(-weight * wear) for weight in profile)


def rest(wear, removal=1.):
    assert wear >= 0 and 0 <= removal <= 1
    return wear * (1 - removal)
