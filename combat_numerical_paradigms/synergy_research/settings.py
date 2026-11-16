"""Research candidates. Values are hypotheses, not previously measured results."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IDENTITIES = {
    'academy': ('学生', '老师'), 'military': ('军人',), 'mage': ('魔法师',),
    'cult': ('拜火教',), 'fighter': ('格斗家',), 'hunter': ('猎手',),
    'heroine': ('侠女',), 'maid': ('女仆',), 'lady': ('淑女',),
    'scholar': ('学者',), 'sage': ('贤者',), 'engineer': ('工程师',),
    'sword': ('剑士',), 'ninja': ('忍者',), 'adventurer': ('冒险者',),
    'sailor': ('水手',), 'gang': ('帮派',), 'merchant': ('行商',),
    'farmer': ('农民',), 'thief': ('盗贼',), 'rich': ('富翁',),
    'worker': ('社畜',), 'killer': ('杀手',),
}
CN = {key: '+'.join(names) for key, names in IDENTITIES.items()}
# n/(n+4) lets each added member matter without inventing 3/6/9 unlocks.
# Both this curve and all coefficients below are explicitly tested candidates.
DEFAULTS = dict(
    count_k=4., teacher_xp=.12, teacher_damage=.0015,
    military_hit=.75, mage_pct=.04, mage_damage=.04, cult=.035,
    fighter=.025, hunter=.35, hunter_turns=3, heroine=.035,
    maid_power=1.8, maid_heal=.08, maid_shield=.08, maid_kind='attack',
    lady=.25, lady_slots=3, scholar=.30, scholar_restore=1,
    sage_out=.25, sage_in=.25, engineer_base=.25, engineer_cast=.035,
    sword=.50, sword_decay=.50, sword_extras=3,
    ninja_base=.12, ninja_cast=.025, ninja_cap=.65,
    adventurer=.06, adventure_goals=('hit', 'crit', 'heal', 'dot', 'debuff'),
    sailor=.006, gang=.65, merchant=.30, farmer_value=.12,
    farmer_kind='heal', farmer_ripen=5, farmer_accelerate=1,
    farmer_wait=.15, thief=.015, rich_coin=1., rich_dr=.025,
    rich_cap=.60, worker=.20, killer=.60,
)
SOURCES = [
    ROOT/'AGENT.md', ROOT/'test_30man_combat_simulator.py',
    ROOT/'combat_numerical_paradigms/roster_research/roster_core.py',
    ROOT/'combat_numerical_paradigms/natural_research/natural_core.py',
    ROOT/'combat_numerical_paradigms/progression_difficulty/study.py',
    ROOT/'combat_numerical_paradigms/progression_difficulty/IDENTITY_SYNERGY_DESIGN.md',
    ROOT/'LegionBattle/LegionBattle/Assets/Characters/character_bond_labels.json',
    ROOT/'combat_numerical_paradigms/progression_difficulty/results/encounter_model.json',
]
