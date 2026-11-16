"""Joint-study engine: count all explicit equipment four-stat contributions.

The frozen baseline counts item.stats for engineers. This protocol additionally
counts owner_stats, which is already implemented as an equipment stat effect.
No skill, shield, healing or other item mechanism is multiplied by engineers.
"""
import inspect
import bond_core as frozen


class Team(frozen.Team):
    @property
    def gear_stats(self):
        return self._joint_gear_stats

    @gear_stats.setter
    def gear_stats(self, value):
        # The parent assigns this after members/items and base stats exist,
        # before the engineer, sailor and merchant opening effects execute.
        self._joint_gear_stats = [v + sum(m.stats[k] * item.value
                                         for m, item in zip(self.members, self.items)
                                         if item.kind == 'owner_stats')
                                  for k, v in enumerate(value)]


_namespace = {**vars(frozen), 'Team': Team}
exec(compile(inspect.getsource(frozen.simulate), '<joint-study-simulate>', 'exec'), _namespace)
simulate = _namespace['simulate']
