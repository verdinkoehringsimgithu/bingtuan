using System;
using LegionBattle.Core.Bridge;
using LegionBattle.Core.Config;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;

namespace LegionBattle.Core.Simulation
{
    /// <summary>
    /// 核心战斗模拟器（纯逻辑内核，可独立脱离 Unity 运行在服务端或控制台）
    /// </summary>
    public class BattleSimulator
    {
        public FormulaConfig Config { get; set; } = FormulaConfig.Default;
        public IBattlePresenter Presenter { get; set; }

        private readonly Random _rng;

        public BattleSimulator(int? seed = null, FormulaConfig config = null, IBattlePresenter presenter = null)
        {
            _rng = seed.HasValue ? new Random(seed.Value) : new Random();
            if (config != null) Config = config;
            Presenter = presenter;
        }

        /// <summary>
        /// 执行一场完整的战斗模拟
        /// </summary>
        public BattleRecord Simulate(Legion left, Legion right, int maxTurns = BattleConstants.DefaultMaxTurns)
        {
            var record = new BattleRecord
            {
                InitialLeftVigor = left.CurrentVigor,
                InitialRightVigor = right.CurrentVigor
            };

            Presenter?.OnBattleStart(left, right);

            // 1. 战前四维派生计算
            left.RecalcDerivedStats(Config);
            right.RecalcDerivedStats(Config);

            // 2. 判定首回合出手方（先机平局时左侧攻方先手，源码实锤机制）
            bool currentCasterIsLeft = DetermineFirstAttacker(left, right);

            int currentTurn = 1;
            while (left.IsAlive && right.IsAlive && currentTurn <= maxTurns)
            {
                Legion attacker = currentCasterIsLeft ? left : right;
                Legion defender = currentCasterIsLeft ? right : left;

                Presenter?.OnTurnStart(currentTurn, attacker, defender);

                // 超时狂暴广播
                if (currentTurn == Config.BerserkThreshold + 1)
                {
                    Presenter?.OnBerserkActivated(currentTurn);
                }

                // 执行半回合交锋
                bool battleEnded = ExecuteTurnPhase(attacker, defender, currentTurn, record, out int turnFixed);
                if (battleEnded) break;

                // 时钟修正（某些技能可改变回合计数）
                if (turnFixed != 0)
                {
                    currentTurn += turnFixed;
                }

                // 轮换出手方
                currentCasterIsLeft = !currentCasterIsLeft;
                currentTurn++;
            }

            // 3. 终局判定
            if (left.IsAlive && !right.IsAlive)
            {
                record.Result = BattleResult.LeftWin;
            }
            else if (!left.IsAlive && right.IsAlive)
            {
                record.Result = BattleResult.RightWin;
            }
            else
            {
                // 超时平局或同归于尽
                record.Result = left.CurrentVigor >= right.CurrentVigor ? BattleResult.LeftWin : BattleResult.RightWin;
            }

            record.TotalTurns = currentTurn;
            Presenter?.OnBattleEnd(record.Result);

            return record;
        }

        private bool ExecuteTurnPhase(
            Legion attacker,
            Legion defender,
            int currentTurn,
            BattleRecord record,
            out int turnFixed)
        {
            turnFixed = 0;

            // Step A: 回合前 BUFF 结算（创伤流血 - 扣除当前精力百分比）
            var (preDmg, preDefy) = BuffProcessor.ProcessPreTurnBuffs(attacker, Config);
            if (preDmg > 0)
            {
                Presenter?.OnBuffTick(attacker, "Hemorrhage", preDmg);
                if (preDefy) Presenter?.OnDeathDefy(attacker, attacker.DeathDefyCount);
                if (!attacker.IsAlive) return true; // 流血致死
            }

            // Step B: 技能概率抽取
            ActiveSkillData skill = SkillSelector.SelectSkill(attacker, defender, currentTurn, _rng);
            attacker.RecordSkillUse(skill.Id);
            Presenter?.OnSkillCast(attacker, skill);

            // Step C: 闪避判定（精准技能或无视闪避技能强制跳过）
            bool isEvaded = false;
            if (!skill.IgnoreEvasion && skill.EffectType != SkillEffectType.PrecisionStrike && skill.EffectType != SkillEffectType.TrueDamage)
            {
                int dodgeRoll = _rng.Next(1, 1001);
                isEvaded = dodgeRoll <= defender.EvasionChancePermille;
            }

            if (isEvaded)
            {
                attacker.LastTurnHitSuccess = false;
                Presenter?.OnEvasion(defender);
            }
            else
            {
                attacker.LastTurnHitSuccess = true;
            }

            // Step D: 结算技能核心效果
            var resolution = SkillResolver.Resolve(attacker, defender, skill, isEvaded, currentTurn, Config);
            turnFixed = resolution.TurnFixed;

            if (resolution.DamageDealt > 0)
            {
                Presenter?.OnDamageDealt(defender, resolution.DamageDealt, resolution.DamageType);
                if (resolution.TriggeredDeathDefy)
                {
                    Presenter?.OnDeathDefy(defender, defender.DeathDefyCount);
                }
            }

            if (resolution.HealApplied > 0)
            {
                bool isOverheal = attacker.CurrentVigor > attacker.MaxVigor;
                Presenter?.OnHealApplied(attacker, resolution.HealApplied, isOverheal);
            }

            // Step E: 附带效果处理（若未被闪避，或 need_hit == false）
            if (!isEvaded || !skill.NeedHit)
            {
                ApplySkillSideEffects(attacker, defender, skill);
            }

            // 记录上回合技能
            attacker.LastTurnSkill = skill;

            // Step F: 回合后 BUFF 结算（腐蚀剧毒 - 扣除最大精力百分比）
            var (postDmg, postDefy) = BuffProcessor.ProcessPostTurnBuffs(attacker, Config);
            if (postDmg > 0)
            {
                Presenter?.OnBuffTick(attacker, "Toxin", postDmg);
                if (postDefy) Presenter?.OnDeathDefy(attacker, attacker.DeathDefyCount);
                if (!attacker.IsAlive) return true;
            }

            // Step G: 状态与 BUFF 衰减
            attacker.DecayBuffs();
            attacker.ExhaustTurns = Math.Max(0, attacker.ExhaustTurns - 1);

            // 派生属性刷新
            attacker.RecalcDerivedStats(Config);
            defender.RecalcDerivedStats(Config);

            // Step H: 记录单步回放切片
            record.AddTurn(new BattleTurnRecord
            {
                TurnIndex = currentTurn,
                CasterIsLeft = attacker.IsLeft,
                SkillId = skill.Id,
                IsEvaded = isEvaded,
                DamageDealt = resolution.DamageDealt,
                HealApplied = resolution.HealApplied,
                DamageType = resolution.DamageType,
                LeftVigor = attacker.IsLeft ? attacker.CurrentVigor : defender.CurrentVigor,
                LeftShield = attacker.IsLeft ? attacker.ShieldVigor : defender.ShieldVigor,
                RightVigor = attacker.IsLeft ? defender.CurrentVigor : attacker.CurrentVigor,
                RightShield = attacker.IsLeft ? defender.ShieldVigor : attacker.ShieldVigor,
                BufferId1 = skill.BuffId1,
                BufferId2 = skill.BuffId2,
                BufferId3 = skill.BuffId3
            });

            return !attacker.IsAlive || !defender.IsAlive;
        }

        private void ApplySkillSideEffects(Legion attacker, Legion defender, ActiveSkillData skill)
        {
            // 虚弱赋予
            if (skill.ExhaustDuration > 0)
            {
                defender.ExhaustTurns = Math.Max(defender.ExhaustTurns, skill.ExhaustDuration);
            }

            // 敌方四维修正
            if (skill.TargetStatModifiers != null && skill.TargetStatModifiers.Length >= 4)
            {
                defender.Initiative += skill.TargetStatModifiers[0];
                defender.Fortitude += skill.TargetStatModifiers[1];
                defender.Agility += skill.TargetStatModifiers[2];
                defender.Dominance += skill.TargetStatModifiers[3];
            }

            // 自身四维修正
            if (skill.SelfStatModifiers != null && skill.SelfStatModifiers.Length >= 4)
            {
                attacker.Initiative += skill.SelfStatModifiers[0];
                attacker.Fortitude += skill.SelfStatModifiers[1];
                attacker.Agility += skill.SelfStatModifiers[2];
                attacker.Dominance += skill.SelfStatModifiers[3];
            }
        }

        /// <summary>
        /// 判定首回合出手方（先机平局时左侧攻方绝对优先）
        /// </summary>
        private static bool DetermineFirstAttacker(Legion left, Legion right)
        {
            if (left.Initiative > right.Initiative) return true;
            if (left.Initiative < right.Initiative) return false;
            return true; // 平局攻方先手
        }
    }
}
