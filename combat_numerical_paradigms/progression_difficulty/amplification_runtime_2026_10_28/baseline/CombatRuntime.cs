using System;
using System.Collections.Generic;

namespace LegionBattle.Battle
{
    [Serializable] public class CombatSkill
    {
        public string name, axis = "C", mainType = "Attack", subEffect = "";
        public double mainParam = 100, chance = 30, baseCrit, pierce, subParam;
        public int tier = 1, limit = 999, turnLower, turnUpper, duration, initiativeBonus;
        public double selfLower, selfUpper, enemyLower, enemyUpper;
        public bool Eligible(int turn, double self, double enemy, int used, int extra)
        {
            int cap = limit > 0 && limit < 999 ? limit + extra : limit;
            return !(cap > 0 && cap < 999 && used >= cap) && turn > turnLower &&
                (turnUpper <= 0 || turn < turnUpper) && (selfLower <= 0 || self > selfLower) &&
                (selfUpper <= 0 || self < selfUpper) && (enemyLower <= 0 || enemy > enemyLower) &&
                (enemyUpper <= 0 || enemy < enemyUpper);
        }
    }
    [Serializable] public class CombatItem
    {
        public string kind = "none";
        public double value, bp;
        public double[] stats = new double[4];
        public bool top;
    }
    [Serializable] public class CombatMember
    {
        public string name, role;
        public CharacterTraits traits;
        public int sample;
        public double bp;
        public double[] stats = new double[4];
        public CombatSkill skill;
        public CombatItem item = new CombatItem();
    }
    public sealed class CombatStatus
    {
        public string kind;
        public double value;
        public int turns, owner;
        public CombatTeam source;
    }
    public sealed class CombatTeam
    {
        public List<CombatMember> members;
        public double maxBP, bp, shield, attack = 1, absorption, regen, frequency = 1;
        public double[] stats = new double[4];
        public int[] uses, casts, failed;
        public bool[] locks;
        public int selected = -1;
        public bool hit, skillSelected;
        public List<CombatStatus> statuses = new List<CombatStatus>();
        private readonly CombatPersistentLimits persistentLimits;
        public double UnrestrictedMaxBP { get; private set; }
        public double DamageReceived { get; private set; }
        public double MinimumBPRatio { get; private set; } = 1;
        public double DamageExposure { get { return Math.Min(1, DamageReceived / maxBP); } }
        public OpeningBondReport OpeningBonds { get; private set; }
        public CombatEvasionState EvasionBonds { get; private set; }
        public CombatSupportState SupportBonds { get; private set; }
        internal readonly List<int> cleansePending = new List<int>();
        public CombatTeam(List<CombatMember> roster, CombatPersistentLimits limits = null, OpeningBondRules openingBonds = null, CombatEvasionRules evasionBonds = null, int memberCapacity = 0, CombatSupportRules supportBonds = null)
        {
            persistentLimits = (limits ?? new CombatPersistentLimits()).Clone();
            if (roster == null || roster.Count < 1 || roster.Count > 30) throw new ArgumentException("Roster requires 1..30 members");
            members = roster; int top = 0;
            foreach (var m in roster)
            {
                if (m == null || m.stats == null || m.stats.Length != 4 || m.bp <= 0) throw new ArgumentException("Invalid member");
                var item = m.item ?? new CombatItem(); m.item = item;
                if (item.stats == null || item.stats.Length != 4 || item.value < 0) throw new ArgumentException("Invalid equipment");
                if (item.top) top++;
                maxBP += m.bp + item.bp;
                for (int i = 0; i < 4; i++) stats[i] += m.stats[i] + item.stats[i] + (item.kind == "owner_stats" ? m.stats[i] * item.value : 0);
            }
            // Match native roster aggregation. Floating sum noise must not break an initiative tie.
            maxBP = Math.Round(maxBP, 6);
            for (int i = 0; i < 4; i++) stats[i] = Math.Round(stats[i], 10);
            if (top > 4 || maxBP <= 0) throw new ArgumentException("At most four top equipment items per team");
            OpeningBonds = (openingBonds ?? new OpeningBondRules()).Clone().Apply(roster, stats);
            EvasionBonds = new CombatEvasionState(roster, memberCapacity==0?roster.Count:memberCapacity, evasionBonds);
            SupportBonds = new CombatSupportState(roster,supportBonds);
            UnrestrictedMaxBP = maxBP; maxBP *= persistentLimits.bp;
            bp = maxBP; uses = new int[roster.Count]; casts = new int[roster.Count]; failed = new int[roster.Count]; locks = new bool[roster.Count];
        }
        public bool Dead { get { return bp <= .0001; } }
        public double Percent { get { return bp / maxBP * 100; } }
        public double Effective(int axis)
        {
            double factor = 1; foreach (var s in statuses) if (s.kind == "stats") factor *= 1 - s.value;
            return stats[axis] * factor * persistentLimits.Stat(axis);
        }
        internal void RecordDamage(double before, double net)
        {
            // Count actual BP removed after shields, before lethal recovery; exclude overkill.
            DamageReceived += Math.Min(Math.Max(0, before), net);
            MinimumBPRatio = Math.Min(MinimumBPRatio, Math.Max(0, bp) / maxBP);
        }
        public double Output()
        {
            double factor = 1; foreach (var s in statuses) if (s.kind == "weak") factor *= 1 - s.value;
            return factor;
        }
        public double Heal(double amount)
        {
            double before = bp; bp = Math.Min(maxBP, bp + Math.Max(0, amount));
            if (selected >= 0 && members[selected].item.kind == "overheal_shield")
                shield += Math.Max(0, amount - (bp - before)) * members[selected].item.value;
            return bp - before;
        }
        public void Macro(double alpha, double beta, double gamma = 0, double delta = 0, double theta = 0, double mu = 1)
        {
            if (alpha <= 0 || beta < 0 || gamma < 0 || gamma > 1 || delta < 0 || mu < 0) throw new ArgumentException("Invalid encounter parameters");
            maxBP *= alpha; UnrestrictedMaxBP *= alpha; bp = maxBP; attack = beta / alpha; absorption = gamma; regen = delta; frequency = mu; stats[2] = Math.Max(0, stats[2] + theta);
        }
    }
    public sealed class CombatAction
    {
        public int round, side, owner = -1;
        public int chainDepth,scholarTarget=-1,scholarRestored;
        public bool hasContinuation;
        public bool normal, critical, missed, pure, ended, censored, forcedHit, absoluteEvaded;
        public double damage, healing, preDamage, postDamage;
        public int winner = -1;
    }
    // Pure numerical runtime: visuals consume reports and never decide damage.
    public sealed class CombatRuntime
    {
        public readonly CombatTeam[] teams;
        private readonly Func<double> random;
        private int phase, first;
        private int forcedOwner=-1,chainDepth;
        public int Round { get; private set; } = 1;
        public bool Ended { get; private set; }
        public bool Censored { get; private set; }
        public int Winner { get; private set; } = -1;
        public int MaxRounds { get; private set; }
        public CombatRuntime(CombatTeam left, CombatTeam right, Func<double> randomSource = null, int maxRounds = 120)
        {
            if (left == null || right == null || maxRounds < 1) throw new ArgumentException("Invalid battle");
            teams = new[] { left, right }; var rng = new Random(); random = randomSource ?? rng.NextDouble; MaxRounds = maxRounds;
            foreach (var t in teams) foreach (var m in t.members) if (m.item.kind == "opening_shield") t.shield += t.maxBP * m.item.value;
        }
        public static double Magic(double m) { return m <= 0 ? 1 : 1 + m / (m + 280) * 1.5 + m / 1400 * .7; }
        public static double DR(double r) { r = Math.Max(0, r); return Math.Min(.68, .25 + r / (r + 450) * .45); }
        public static double Dodge(double i) { i = Math.Max(0, i); return Math.Min(.35, i / (i + 450) * .48); }
        private double Deal(CombatTeam defender, double amount, bool clamp = true)
        {
            double net = Math.Max(0, amount) * (1 - defender.absorption);
            double saved = Math.Min(defender.shield, net); defender.shield -= saved; net -= saved;
            double before = defender.bp;
            defender.bp = clamp ? Math.Max(0, defender.bp - net) : defender.bp - net;
            defender.RecordDamage(before, net);
            if (defender.Dead)
                for (int i = 0; i < defender.members.Count; i++)
                    if (defender.members[i].item.kind == "death_lock" && !defender.locks[i])
                    { defender.locks[i] = true; defender.bp = defender.maxBP * defender.members[i].item.value; break; }
            return net;
        }
        private double Dots(CombatTeam target, string kind)
        {
            double total = 0, dr = DR(target.Effective(1));
            for (int i = 0; i < target.statuses.Count; )
            {
                var s = target.statuses[i]; if (s.kind != kind) { i++; continue; }
                double basis = kind == "max" ? target.maxBP : Math.Max(0, target.maxBP - target.bp);
                double amount = Math.Max(1, basis * s.value * (1 - dr) * s.source.Output());
                total += Deal(target, amount, false); s.turns--;
                if (s.turns <= 0) target.statuses.RemoveAt(i); else i++;
            }
            return total;
        }
        private void Finish()
        {
            if (!teams[0].Dead && !teams[1].Dead) return;
            Ended = true; Winner = teams[0].Dead == teams[1].Dead ? -1 : teams[0].Dead ? 1 : 0;
        }
        private void Cleanse()
        {
            foreach (var t in teams)
            {
                foreach(int charges in t.cleansePending)
                {
                    int remaining = charges;
                    foreach (string kind in new[] { "stats", "weak" })
                        for (int i = 0; i < t.statuses.Count && remaining > 0; )
                            if (t.statuses[i].kind == kind) { t.statuses.RemoveAt(i); remaining--; } else i++;
                }
                t.cleansePending.Clear();
            }
        }
        private void EndRound(CombatAction report)
        {
            if (!Ended)
            {
                foreach (var t in teams)
                {
                    if (t.Dead) continue;
                    report.postDamage += Dots(t, "lost");
                    for (int i = t.statuses.Count - 1; i >= 0; i--)
                        if (t.statuses[i].kind == "stats" || t.statuses[i].kind == "weak")
                        { if (--t.statuses[i].turns <= 0) t.statuses.RemoveAt(i); }
                }
                Finish();
                foreach (var t in teams) if (!t.Dead && t.regen > 0) t.Heal(t.maxBP * t.regen);
            }
            Cleanse();
            foreach(var team in teams)team.EvasionBonds.EndRound();
            if (!Ended && Round >= MaxRounds) { Ended = true; Censored = true; Winner = -1; }
            if (!Ended) Round++;
            phase = 0;
        }
        public CombatAction Next()
        {
            if (Ended) return new CombatAction { round = Round, ended = true, censored = Censored, winner = Winner, side = first };
            var result = new CombatAction { round = Round,chainDepth=chainDepth };
            if (phase == 0 && forcedOwner<0)
            {
                foreach (var t in teams) { t.selected = -1; t.hit = false; t.skillSelected = false; }
                foreach (var t in teams) if (!t.Dead) result.preDamage += Dots(t, "max");
                Finish();
                double i = teams[0].Effective(2), j = teams[1].Effective(2);
                first = i > j || (i == j && random() < .5) ? 0 : 1;
            }
            result.side = phase == 0 ? first : 1 - first;
            if (!Ended)
            {
                var actor=teams[result.side];var enemy=teams[1-result.side];
                Act(actor, enemy, phase == 0, result,forcedOwner);
                actor.EvasionBonds.AfterAction(result.owner,!result.normal);
                if(actor.hit&&actor.skillSelected&&actor.selected>=0&&actor.members[actor.selected].item.kind=="cleanse")
                    actor.cleansePending.Add((int)actor.members[actor.selected].item.value);
                actor.SupportBonds.AfterAction(actor,enemy,Round,result,random);
            }
            Finish();
            int continuation=Ended?-1:teams[result.side].SupportBonds.NextSword(teams[result.side],teams[1-result.side],Round,result,random);
            if(continuation>=0)
            {
                forcedOwner=continuation;chainDepth++;result.hasContinuation=true;
                return result;
            }
            forcedOwner=-1;chainDepth=0;
            if (phase == 1 || Ended) EndRound(result); else phase = 1;
            result.ended = Ended; result.censored = Censored; result.winner = Winner;
            return result;
        }
        private void Act(CombatTeam a, CombatTeam b, bool isFirst, CombatAction report,int forced=-1)
        {
            a.selected=-1;a.hit=false;a.skillSelected=false;
            // Effective stats and base power are sampled before initiative growth or healing.
            double c = a.Effective(0), r = b.Effective(1), i = a.Effective(2), j = b.Effective(2), amp = Magic(a.Effective(3));
            double basis = (a.maxBP * .09 + a.bp * .045) * a.attack;
            double diff = Math.Max(0, i - j), preempt = isFirst ? 1 + diff / (diff + 500) * .35 : 1;
            CombatSkill skill = null; CombatItem item = null; double direct = 1; bool overflowTrue = false;
            for (int pos = forced>=0?forced:0; pos < (forced>=0?forced+1:a.members.Count); pos++)
            {
                var s = a.members[pos].skill; if (s == null) continue; var gear = a.members[pos].item;
                int extra = gear.kind == "extra_use" ? (int)gear.value : 0;
                if (!s.Eligible(Round, a.Percent, b.Percent, a.uses[pos], extra)) continue;
                double chance = s.chance / 100 * a.frequency;
                if (gear.kind == "skill_chance") chance += gear.value;
                if (gear.kind == "chance_ramp") chance += gear.value * a.failed[pos];
                if (random() < (forced>=0?1:Math.Min(1, Math.Max(0, chance))))
                {
                    a.uses[pos]++; a.casts[pos]++; a.failed[pos] = 0; a.selected = pos; a.skillSelected = true;
                    skill = s; item = gear; report.owner = pos; break;
                }
                a.failed[pos]++;
            }
            if (skill == null)
            {
                a.selected = Math.Min(a.members.Count - 1, (int)(random() * a.members.Count));
                item = a.members[a.selected].item; skill = new CombatSkill { chance = 100 }; report.normal = true; report.owner = a.selected;
                if (item.kind == "normal_damage") direct = 1 + item.value;
            }
            else
            {
                report.forcedHit=a.EvasionBonds.ForceHit(a.selected,random);
                if (item.kind == "skill_damage") direct = 1 + item.value;
                if (item.kind == "cast_ramp") direct = 1 + item.value * (a.casts[a.selected] - 1);
                overflowTrue = item.kind == "skill_crit";
            }
            double main = skill.mainParam * (skill.mainType != "Heal" && !report.normal ? a.frequency : 1);
            double pierce = skill.pierce + (!report.normal && item.kind == "skill_pierce" ? item.value : 0);
            double critBase = skill.baseCrit + (!report.normal && item.kind == "skill_crit" ? item.value : 0);
            double sub = skill.subParam;
            if (!report.normal && item.kind == "skill_heal" && (skill.mainType == "Heal" || skill.subEffect == "战力吸收")) sub *= 1 + item.value;
            if (!report.normal && item.kind == "skill_dot" && (skill.subEffect == "最大流失" || skill.subEffect == "已损流失" || skill.subEffect == "固定流失")) sub *= 1 + item.value;
            if (skill.initiativeBonus > 0) a.stats[2] += skill.initiativeBonus;
            if(!report.forcedHit&&b.EvasionBonds.AbsoluteMiss(random))
            {report.missed=true;report.absoluteEvaded=true;return;}
            double critChance = c / (c + 750) * .45 + critBase * (1 + (amp - 1) * .45);
            double overflow = Math.Max(0, critChance - 1) * 1.5;
            report.critical = random() < Math.Min(1, critChance);
            if (!report.critical && !report.forcedHit && random() < Dodge(j)) { report.missed = true; return; }
            a.hit = true;
            double mult = main / 100 + (report.critical ? .45 + c / (c + 650) * .75 + (overflowTrue ? 0 : overflow) : 0);
            double raw = basis * mult * preempt * a.Output() * direct;
            if (skill.mainType == "Heal")
            {
                report.healing += a.Heal((skill.subEffect == "当前战力自愈" ? Math.Max(0, a.bp) : a.maxBP) * sub);
                raw = basis * a.Output() * direct;
            }
            double dr = DR(r); report.pure = pierce * amp >= .85;
            double actual = report.pure ? raw * (1 + (amp - 1) * .20) : Math.Max(1, raw * (1 - Math.Max(0, dr * (1 - pierce * amp))) - r * 4.56);
            double directNet = Deal(b, actual); report.damage += directNet;
            if (report.critical && skill.mainType != "Heal" && overflowTrue && overflow > 0)
                report.damage += Deal(b, basis * overflow * preempt * a.Output() * direct);
            switch (skill.subEffect)
            {
                case "自身已损反噬": report.damage += Deal(b, Math.Max(1, Math.Max(0, a.maxBP - a.bp) * sub * (1 - dr))); break;
                case "敌方已损斩杀": report.damage += Deal(b, Math.Max(1, Math.Max(0, b.maxBP - b.bp) * sub * (1 - dr))); break;
                case "敌方当前压制": report.damage += Deal(b, Math.Max(1, Math.Max(0, b.bp) * sub * (1 - dr))); break;
                case "战力吸收": report.healing += a.Heal(directNet * sub * amp); break;
                case "最大流失": case "固定流失": case "已损流失":
                    b.statuses.Add(new CombatStatus { kind = skill.subEffect == "已损流失" ? "lost" : "max", value = (skill.subEffect == "固定流失" ? sub / b.maxBP : sub) * amp, turns = skill.duration, source = a, owner = a.selected }); break;
                case "虚弱压制": case "四维削弱":
                    b.statuses.Add(new CombatStatus { kind = skill.subEffect == "虚弱压制" ? "weak" : "stats", value = Math.Min(skill.subEffect == "虚弱压制" ? .60 : .40, sub / 100 * (1 + (amp - 1) * .25)), turns = skill.duration, source = a }); break;
            }
        }
    }
}
