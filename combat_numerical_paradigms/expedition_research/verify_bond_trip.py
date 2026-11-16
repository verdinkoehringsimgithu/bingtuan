"""Exact no-wear equivalence and current-cap healing with compound recovery."""
import json

import measure_response as lab
from bond_trip_core import configured_trip
from configured_compound_core import configured, variants
from rosters import availability
from run_bonds import atomic_json


def main():
    models = [('maid', dict(variants('maid'))['addition_0.5']),
              ('maid', dict(variants('maid'))['addition_1']), ('farmer', {})]
    counts = {(r['stage']-1,r['bond']):r['available'] for r in availability()}
    exact = 0; cap_checks = 0
    for stage in range(6):
        for bond, parameters in models:
            members, items = lab.build(stage, 'C_I', 1370000,
                ((bond,min(lab.STAGES[stage][0],counts[stage,bond])),), 'front', 'final')
            enemy, ei = lab.build(stage, 'M_R', 1470003, (), 'front', 'final')
            source = configured(parameters); simulate = configured_trip(parameters)
            for bs in (31001,31002,31003,31004):
                r,t,a,b = source.simulate(members,enemy,bs,items,ei,enabled=(bond,),telemetry=True)
                q,u,c,d = simulate(members,enemy,bs,items,ei,enabled=(bond,),telemetry=True)
                assert all(q[k] == value for k,value in r.items())
                assert t == u and a.max_bp == c.max_bp and b.max_bp == d.max_bp
                exact += 1
            q,u,c,d = simulate(members,enemy,31001,items,ei,enabled=(bond,),telemetry=True,
                               factors=(.5,.75,.75,.75,.75))
            assert c.max_bp == a.max_bp*.5 and d.max_bp == b.max_bp
            assert u[0]['p_bp_start'] == 1.
            c.current_bp = 0.; c.heal(c.max_bp*5)
            assert c.current_bp == c.max_bp
            cap_checks += 1
    result = dict(passed=True, exact_no_wear_battles=exact, independent_cap_healing_checks=cap_checks)
    atomic_json(lab.OUT/'recovery_stress/core_verification.json',result)
    print(json.dumps(result))


if __name__ == '__main__': main()
