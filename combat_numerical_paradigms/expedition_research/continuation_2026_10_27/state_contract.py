"""Executable candidate contract for caller-owned persistent troop wear."""
from dataclasses import dataclass, field
import json
import math
from pathlib import Path

AXES=('bp','courage','resilience','initiative','magic')


@dataclass
class ExpeditionState:
    troop_id: str
    wear: list = field(default_factory=lambda:[0.]*5)
    ledger: list = field(default_factory=list)
    version: int = 1

    def __post_init__(self):
        if not self.troop_id or self.version!=1 or len(self.wear)!=5:
            raise ValueError('Invalid persistent troop state')
        if any(not math.isfinite(x) or x<0 for x in self.wear):raise ValueError('Invalid wear')
        ids=[r['id'] for r in self.ledger]
        if len(ids)!=len(set(ids)):raise ValueError('Duplicate persisted result ID')

    @property
    def factors(self):
        return tuple(math.exp(-x) for x in self.wear)

    def _record(self,result_id,kind,before,after,metadata):
        if not result_id or any(r['id']==result_id for r in self.ledger):
            raise ValueError('Missing or duplicate settlement ID')
        self.ledger.append(dict(id=result_id,kind=kind,before=list(before),after=list(after),metadata=metadata))
        self.wear=list(after)

    def apply_loss(self,result_id,losses,source):
        if len(losses)!=5 or any(not math.isfinite(x) or not 0<=x<1 for x in losses):
            raise ValueError('Loss fractions must be finite and in [0,1)')
        after=[w-math.log1p(-x) for w,x in zip(self.wear,losses)]
        self._record(result_id,'loss',self.wear,after,dict(source=source,losses=list(losses)))

    def supply(self,result_id,removal):
        if len(removal)!=5 or any(not math.isfinite(x) or not 0<=x<=1 for x in removal):
            raise ValueError('Explicit removal fraction is required for each channel')
        self._record(result_id,'supply',self.wear,[w*(1-r) for w,r in zip(self.wear,removal)],
                     dict(removal=list(removal)))

    def battle_input(self,unrestricted_max_bp):
        if not math.isfinite(unrestricted_max_bp) or unrestricted_max_bp<=0:raise ValueError('Invalid BP budget')
        maximum=unrestricted_max_bp*self.factors[0]
        return dict(factors=self.factors,effective_max_bp=maximum,starting_bp=maximum)

    def to_dict(self):
        return dict(version=self.version,troop_id=self.troop_id,wear=list(self.wear),ledger=self.ledger)

    def save(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix(path.suffix+'.tmp')
        temporary.write_text(json.dumps(self.to_dict(),ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(path)

    @classmethod
    def load(cls,path):
        return cls(**json.loads(Path(path).read_text(encoding='utf-8')))


def victory_losses(hp,exposure,roll):
    if not all(math.isfinite(x) and 0<=x<=1 for x in (hp,exposure,roll)):raise ValueError('Invalid telemetry')
    return (.08+.20*exposure if roll<.65 else 0.,0.,0.,0.,0.)
