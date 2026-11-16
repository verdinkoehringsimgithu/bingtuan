# -*- coding: utf-8 -*-
import random, sys
sys.stdout.reconfigure(encoding='utf-8')
from test_30man_combat_simulator import BattleSkill, Troop

def calc_magic_amp_responsive(magic):
    if magic <= 0: return 1.0
    return 1.0 + (magic / (magic + 280.0)) * 1.5 + (magic / 1400.0) * 0.7

def calc_resilience_dr(resilience):
    pct_dr = min(0.68, 0.25 + (resilience / (resilience + 450.0)) * 0.45)
    flat_dr = resilience * 12.0
    return flat_dr, pct_dr

def calc_courage_stats(courage):
    crit_rate = (courage / (courage + 750.0)) * 0.45
    crit_bonus = 0.45 + (courage / (courage + 650.0)) * 0.75
    return crit_rate, crit_bonus

def calc_initiative_stats(initiative, enemy_initiative, preempt_cap=0.25):
    dodge_rate = min(0.28, (initiative / (initiative + 700.0)) * 0.35)
    diff = max(0.0, initiative - enemy_initiative)
    preempt_bonus = (diff / (diff + 600.0)) * preempt_cap if diff > 0 else 0.0
    return dodge_rate, preempt_bonus

configs = {
    "M_R": ("魔力+坚韧", 100, 500, 100, 1000),
    "M_I": ("魔力+先机", 100, 100, 500, 1000),
    "M_C": ("魔力+勇气", 500, 100, 100, 1000),
    "C_I": ("勇气+先机", 1000, 100, 500, 100),
    "C_R": ("勇气+坚韧", 1000, 500, 100, 100),
    "R_I": ("坚韧+先机", 100, 1000, 500, 100),
}

def run_test(preempt_cap=0.25, exhaust_mode="zero", mi_mult=1.0, ci_mult=1.0,
             bp_max_r=0.09, bp_cur_r=0.045, dr_f=0.60, heal_f=0.75, dot_f=0.60, sims=800):
    def get_troop(gc, base_bp=1000000):
        name, c, r, i, m = configs[gc]
        troop = Troop(1, name, 30, c, r, i, m, base_bp)
        if gc == "M_R":
            troop.skills.append(BattleSkill(1,"灭世剧毒",6,"魔力","Attack",130.0,50.0,turn_cond2=3,times_limit=1,sub_effect="combo_dot",sub_param=0.035*dot_f,sub_base=base_bp*0.035*dot_f,sub_duration=3))
            troop.skills.append(BattleSkill(2,"神恩涅槃",6,"坚韧","Heal",100.0,50.0,self_bp_cond2=40,times_limit=1,sub_effect="self_max_heal",sub_param=0.18*heal_f))
            troop.skills.append(BattleSkill(3,"生命剥离",5,"魔力","Attack",125.0,35.0,sub_effect="dot_lost",sub_param=0.060*dot_f,sub_duration=3))
            troop.skills.append(BattleSkill(4,"常态愈合",5,"坚韧","Heal",100.0,30.0,self_bp_cond2=65,sub_effect="self_max_heal",sub_param=0.12*heal_f))
        elif gc == "M_I":
            troop.skills.append(BattleSkill(1,"弑神断界斩",6,"魔力","Attack",220.0*mi_mult,50.0,is_true_damage=True,times_limit=1))
            troop.skills.append(BattleSkill(2,"瞬狱虚弱杀",6,"先机","Attack",170.0*mi_mult,45.0,turn_cond2=3,times_limit=1,exhaust_turns=1,is_true_damage=True))
            troop.skills.append(BattleSkill(3,"纯粹裂魂击",5,"魔力","Attack",185.0*mi_mult,35.0,is_true_damage=True))
            troop.skills.append(BattleSkill(4,"常态影刃",5,"魔力","Attack",150.0*mi_mult,30.0,ignore_def_ratio=0.75))
        elif gc == "M_C":
            troop.skills.append(BattleSkill(1,"湮灭核弹斩",6,"魔力","Attack",260.0,50.0,is_true_damage=True,times_limit=1,base_crit_rate=0.20))
            troop.skills.append(BattleSkill(2,"终结暴击击",6,"勇气","Attack",384.0,45.0,enemy_bp_cond2=45,times_limit=1,base_crit_rate=0.30))
            troop.skills.append(BattleSkill(3,"纯粹裂魂击",5,"魔力","Attack",200.0,35.0,is_true_damage=True,base_crit_rate=0.15))
            troop.skills.append(BattleSkill(4,"破军重劈",5,"勇气","Attack",216.0,30.0,base_crit_rate=0.20))
        elif gc == "C_I":
            troop.skills.append(BattleSkill(1,"疾风封脉破",6,"先机","Attack",170.0*ci_mult,50.0,turn_cond2=3,times_limit=1,exhaust_turns=1))
            troop.skills.append(BattleSkill(2,"狂雷终结斩",6,"勇气","Attack",456.0*ci_mult,50.0,enemy_bp_cond2=45,times_limit=1,base_crit_rate=0.25))
            troop.skills.append(BattleSkill(3,"裂地狂劈",5,"勇气","Attack",264.0*ci_mult,40.0,base_crit_rate=0.20))
            troop.skills.append(BattleSkill(4,"常态影刃",5,"先机","Attack",175.0*ci_mult,30.0))
        elif gc == "C_R":
            troop.skills.append(BattleSkill(1,"背水浴血斩",6,"勇气","Attack",264.0,50.0,self_bp_cond2=40,times_limit=1,base_crit_rate=0.25,sub_effect="self_lost_dmg",sub_param=0.35))
            troop.skills.append(BattleSkill(2,"不坏金身",5,"坚韧","Heal",100.0,45.0,self_bp_cond2=45,times_limit=1,sub_effect="self_max_heal",sub_param=0.16*heal_f))
            troop.skills.append(BattleSkill(3,"崩山重劈",5,"勇气","Attack",240.0,35.0,base_crit_rate=0.15))
        elif gc == "R_I":
            troop.skills.append(BattleSkill(1,"神恩涅槃",6,"坚韧","Heal",100.0,50.0,self_bp_cond2=40,times_limit=1,sub_effect="self_max_heal",sub_param=0.18*heal_f))
            troop.skills.append(BattleSkill(2,"瞬影封印",5,"先机","Attack",150.0,40.0,exhaust_turns=1))
            troop.skills.append(BattleSkill(3,"常态吸血",5,"坚韧","Attack",130.0,30.0,sub_effect="lifesteal",sub_param=0.35))
        return troop

    def execute(acting, defender, is_first, turn):
        base_power = acting.max_bp * bp_max_r + acting.current_bp * bp_cur_r
        m_amp = calc_magic_amp_responsive(acting.magic)
        c_crit_rate, c_crit_bonus = calc_courage_stats(acting.courage)
        dodge_rate, preempt_bonus = calc_initiative_stats(acting.initiative, defender.initiative, preempt_cap)
        preempt_factor = (1.0 + preempt_bonus) if (is_first and preempt_bonus > 0) else 1.0

        skill = None
        for s in acting.skills:
            u = acting.usage.get(s.id, 0)
            if s.can_trigger(turn, acting.bp_pct, defender.bp_pct, u):
                if random.random()*100.0 < s.trigger_chance:
                    skill = s
                    acting.usage[s.id] = u+1
                    break
        if skill is None:
            skill = BattleSkill(9999,"普通攻击",1,"通用","Attack",main_param=100.0)

        raw_skill_crit = getattr(skill,"base_crit_rate",0.0)
        esc = raw_skill_crit * m_amp if raw_skill_crit > 0 else 0.0
        tcr = c_crit_rate + esc
        eocb = 0.0
        if tcr > 1.0:
            eocb = (tcr-1.0)*1.5
            ecr = 1.0
        else:
            ecr = min(1.0, tcr)

        is_crit = (random.random() < ecr)
        if not is_crit and random.random() < dodge_rate:
            return

        mult = skill.main_param / 100.0
        if is_crit:
            mult += (c_crit_bonus + eocb)
        raw_dmg = base_power * mult * preempt_factor

        if acting.exhaust_turns > 0:
            if exhaust_mode == "zero":
                raw_dmg = 1.0
            elif exhaust_mode == "reduce":
                raw_dmg *= 0.40
            acting.exhaust_turns = 0

        if skill.main_type == "Heal":
            heal_val = 0.0
            if skill.sub_effect == "self_max_heal":
                heal_val = acting.max_bp * (skill.sub_param * m_amp)
            acting.heal(heal_val)
            raw_dmg = base_power * 1.0

        flat_dr, pct_dr = calc_resilience_dr(defender.resilience)
        flat_dr *= dr_f
        ipt = skill.is_true_damage or (skill.ignore_def_ratio * m_amp >= 0.85)
        actual_dmg = raw_dmg if ipt else max(1.0, raw_dmg*(1.0-pct_dr)-flat_dr)
        defender.current_bp = max(0.0, defender.current_bp - actual_dmg)

        eff = skill.sub_effect
        if eff == "self_lost_dmg":
            lost = max(0.0, acting.max_bp - acting.current_bp)
            extra = lost * (skill.sub_param * m_amp)
            defender.current_bp = max(0.0, defender.current_bp - max(1.0, extra))
        elif eff == "lifesteal":
            acting.heal(actual_dmg * (skill.sub_param * m_amp))
        elif eff == "dot_max":
            defender.max_bp_dots.append({"val":skill.sub_param*m_amp,"turns":skill.sub_duration})
        elif eff == "dot_lost":
            defender.turn_end_dots.append({"mode":"lost","val":skill.sub_param*m_amp,"turns":skill.sub_duration})
        elif eff == "combo_dot":
            defender.max_bp_dots.append({"val":skill.sub_param*m_amp,"turns":skill.sub_duration})
            defender.turn_end_dots.append({"mode":"flat","val":skill.sub_base*m_amp,"turns":skill.sub_duration})

        if skill.exhaust_turns > 0:
            defender.exhaust_turns = max(defender.exhaust_turns, skill.exhaust_turns)

    def battle(t1, t2):
        t1.reset(); t2.reset()
        turn = 0
        while turn < 40:
            turn += 1
            for trp in [t1, t2]:
                if trp.is_dead(): continue
                if trp.max_bp_dots:
                    _, pdr = calc_resilience_dr(trp.resilience)
                    nd = []
                    for d in trp.max_bp_dots:
                        al = max(1.0, trp.max_bp*d["val"]*(1.0-pdr))
                        trp.current_bp -= al
                        d["turns"] -= 1
                        if d["turns"]>0: nd.append(d)
                    trp.max_bp_dots = nd
            if t1.is_dead() or t2.is_dead(): break
            first, second = (t1,t2) if t1.initiative >= t2.initiative else (t2,t1)
            execute(first, second, True, turn)
            if second.is_dead(): break
            execute(second, first, False, turn)
            if first.is_dead(): break
            for trp in [t1, t2]:
                if trp.is_dead(): continue
                if trp.turn_end_dots:
                    _, pdr = calc_resilience_dr(trp.resilience)
                    nd = []
                    for d in trp.turn_end_dots:
                        cl = max(0.0,trp.max_bp-trp.current_bp) if d["mode"]=="lost" else 0
                        rl = cl*d["val"] if d["mode"]=="lost" else d["val"]
                        al = max(1.0, rl*(1.0-pdr))
                        trp.current_bp -= al
                        d["turns"] -= 1
                        if d["turns"]>0: nd.append(d)
                    trp.turn_end_dots = nd
            if t1.is_dead() or t2.is_dead(): break
        w = t1 if (not t1.is_dead() and t2.is_dead()) else (t2 if (not t2.is_dead() and t1.is_dead()) else (t1 if t1.bp_pct>=t2.bp_pct else t2))
        return {"winner":w,"turns":turn}

    genres = ["M_R","M_I","M_C","C_I","C_R","R_I"]
    wm = {g1:{g2:0 for g2 in genres} for g1 in genres}
    at = []
    for i in range(len(genres)):
        for j in range(i,len(genres)):
            g1,g2 = genres[i],genres[j]
            if g1==g2:
                wm[g1][g2]=sims//2
                continue
            for _ in range(sims):
                t1=get_troop(g1); t2=get_troop(g2)
                res=battle(t1,t2)
                at.append(res["turns"])
                if res["winner"].name==t1.name: wm[g1][g2]+=1
                else: wm[g2][g1]+=1
    wr = {}
    for g1 in genres:
        wr[g1] = (sum(wm[g1][g2] for g2 in genres)/(sims*len(genres)))*100.0
    avg = sum(at)/len(at) if at else 0
    return avg, wr

def fmt(w):
    return "  ".join(f"{configs[k][0]}:{v:.1f}%" for k,v in w.items())

if __name__ == "__main__":
    tests = [
        ("基准 (先机弱化状态)",              dict(preempt_cap=0.25, exhaust_mode="zero")),
        ("C 单项: 倍率 +10%",               dict(preempt_cap=0.25, exhaust_mode="zero", mi_mult=1.10, ci_mult=1.10)),
        ("C 单项: 倍率 +15%",               dict(preempt_cap=0.25, exhaust_mode="zero", mi_mult=1.15, ci_mult=1.15)),
        ("A(0.35)+C(+10%)",                  dict(preempt_cap=0.35, exhaust_mode="zero", mi_mult=1.10, ci_mult=1.10)),
        ("A(0.35)+C(+12%)",                  dict(preempt_cap=0.35, exhaust_mode="zero", mi_mult=1.12, ci_mult=1.12)),
        ("A(0.35)+C(+15%)",                  dict(preempt_cap=0.35, exhaust_mode="zero", mi_mult=1.15, ci_mult=1.15)),
        ("A(0.30)+C(+15%)",                  dict(preempt_cap=0.30, exhaust_mode="zero", mi_mult=1.15, ci_mult=1.15)),
    ]
    for name, kwargs in tests:
        a, w = run_test(sims=1000, **kwargs)
        print(f"=== {name} ===")
        print(f"全局 {a:.2f} 回合 | {fmt(w)}")
        print()
