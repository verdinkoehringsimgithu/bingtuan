"""Integration boundary checks for the proposed caller-owned travel state."""
import json
import math
from pathlib import Path

from state_contract import ExpeditionState,victory_losses
import study_closure as study
from run_bonds import atomic_json
from configured_compound_core import configured


def main():
    state=ExpeditionState('player')
    state.apply_loss('a',(.2,.1,0,0,0),'event')
    before=state.to_dict();ratios=[]
    for budget in (60000,100000,1000000):
        battle=state.battle_input(budget)
        assert battle['starting_bp']==battle['effective_max_bp']==budget*.8
        ratios.append(battle['effective_max_bp']/budget)
    assert state.to_dict()==before
    try:state.apply_loss('a',(.2,0,0,0,0),'duplicate')
    except ValueError:pass
    else:raise AssertionError('Duplicate callback accepted')
    assert state.to_dict()==before
    state.supply('half',(.5,)*5)
    assert abs(state.factors[0]-math.sqrt(.8))<1e-12
    path=study.OUT/'contract_save_example.json';state.save(path);loaded=ExpeditionState.load(path)
    assert state.to_dict()==loaded.to_dict()
    try:loaded.supply('half',(1.,)*5)
    except ValueError:pass
    else:raise AssertionError('Reload cleared settlement IDs')
    state.supply('full',(1.,)*5);assert state.factors==(1.,)*5
    assert victory_losses(1.,1.,0.)[0]==.28
    # Reordering, changing equipment and new member budgets cannot clear the
    # external state. Exercise actual battle inputs, not just serialization.
    checks=0;parity=0
    for stage in range(6):
        j=next(j for j in study.jobs() if j['stage']==stage and j['mix']=='maid_engineer' and j['genre']=='C_I')
        mm,gears,enemy,ei,sim=study.prepare(j)
        enabled=study.MIXES[j['mix']]
        for gear,items in gears.items():
            raw,trace,a,b=configured(study.PARAMETERS).simulate(mm,enemy,4111,items,ei,
                p=j['macro'],enabled=enabled,telemetry=True)
            q,t,c,d=sim(mm,enemy,4111,items,ei,p=j['macro'],enabled=enabled,telemetry=True)
            assert all(q[k]==v for k,v in raw.items()) and trace==t;parity+=1
            for order in (tuple(range(len(mm))),tuple(reversed(range(len(mm))))):
                m,it=study.reordered(mm,items,order)
                damaged=ExpeditionState('player');damaged.apply_loss('initial',(.3,.2,.1,0,0),'boundary')
                rr,tr,e,f=sim(m,enemy,4111,it,ei,p=j['macro'],enabled=enabled,factors=damaged.factors,telemetry=True)
                assert abs(e.max_bp/a.max_bp-.7)<1e-12 and f.max_bp==b.max_bp
                assert tr[0]['p_bp_start']==1.
                e.current_bp=0.;e.heal(e.max_bp*100);assert e.current_bp==e.max_bp
                checks+=1
    result=dict(status='passed',actual_battle_boundary_checks=checks,no_penalty_adapter_checks=parity,
        serialization_duplicate_settlement_and_supply=True,
        scope='candidate contract; no Unity/world-map integration claimed')
    atomic_json(study.OUT/'contract_verification.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
