using System;
using System.Collections.Generic;
using LegionBattle.Core.Bridge;
using LegionBattle.Core.Config;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;
using LegionBattle.Core.Simulation;

namespace TestRunner
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("=================================================================");
            Console.WriteLine("    LEGION BATTLE SIMULATION ENGINE - VERIFICATION SUITE");
            Console.WriteLine("=================================================================\n");

            var presenter = new SamplePresenter();

            // ─── 案例 1: 暴击流 VS 高防精准流 ───
            Console.WriteLine(">>> TEST CASE 1: HAVOC (CRIT) vs PRECISION (HIGH FORTITUDE)");
            var havocLegion = new Legion("Havoc Vanguard", 1000000, init: 120, fort: 20, agi: 10, dom: 60, isLeft: true);
            havocLegion.EquippedSkills.Add(new ActiveSkillData
            {
                Id = 101,
                Name = "Havoc Judgement",
                EffectType = SkillEffectType.HavocStrike,
                Param = 220f,
                TriggerWeight = 700
            });
            havocLegion.EquippedSkills.Add(new ActiveSkillData
            {
                Id = 102,
                Name = "Quick Strike",
                EffectType = SkillEffectType.Strike,
                Param = 120f,
                TriggerWeight = 300
            });

            var precisionLegion = new Legion("Iron Precision", 1000000, init: 30, fort: 180, agi: 10, dom: 30, isLeft: false);
            precisionLegion.DeathDefyCount = 1; // 赋予 1 次名刀免死
            precisionLegion.EquippedSkills.Add(new ActiveSkillData
            {
                Id = 201,
                Name = "True Ray",
                EffectType = SkillEffectType.PrecisionStrike,
                Param = 130f,
                TriggerWeight = 800
            });

            var sim1 = new BattleSimulator(seed: 42, presenter: presenter);
            var rec1 = sim1.Simulate(havocLegion, precisionLegion, maxTurns: 15);
            Console.WriteLine($"\n[Result 1] Winner: {rec1.Result} in {rec1.TotalTurns} turns.");

            // ─── 案例 2: 精准流 VS 闪避恢复流 ───
            Console.WriteLine("\n\n>>> TEST CASE 2: PRECISION vs TENACITY (HIGH AGILITY + OVERHEAL)");
            var precLegion2 = new Legion("True Arrow", 1000000, init: 50, fort: 100, agi: 20, dom: 50, isLeft: true);
            precLegion2.EquippedSkills.Add(new ActiveSkillData
            {
                Id = 202,
                Name = "Lock-on Precision",
                EffectType = SkillEffectType.PrecisionStrike,
                Param = 140f,
                TriggerWeight = 1000
            });

            var tenacityLegion = new Legion("Ghost Healer", 1000000, init: 40, fort: 20, agi: 150, dom: 20, isLeft: false);
            tenacityLegion.EquippedSkills.Add(new ActiveSkillData
            {
                Id = 301,
                Name = "Divine Over-Restore",
                EffectType = SkillEffectType.SelfMaxRestore,
                Param = 30f,
                Param2 = 80f,
                TriggerWeight = 800
            });

            var sim2 = new BattleSimulator(seed: 42, presenter: presenter);
            var rec2 = sim2.Simulate(precLegion2, tenacityLegion, maxTurns: 15);
            Console.WriteLine($"\n[Result 2] Winner: {rec2.Result} in {rec2.TotalTurns} turns.");

            // ─── 案例 3: 程序化生成干员 + 宝可梦个体值 (IVs) + 10孔神器 (首轮必发词条) ───
            Console.WriteLine("\n\n>>> TEST CASE 3: PROCEDURAL OPERATIVE (POKEMON IVs) + 10-SOCKET RELIC (FIRST-TURN GUARANTEE)");
            var op = new OperativeInstance
            {
                CustomName = "Desert Blade Lord (Procedural S-Tier)",
                Tier = 5,
                OriginRegion = "Sands of Salzaar",
                IndividualValues = new IndividualValues
                {
                    SkillParamBonus = 25f,   // 宝可梦天资: 伤害倍率+25%
                    SkillChanceBonus = 10,   // 宝可梦天资: 触发率+10%
                    QualityGrade = "S"
                },
                EquippedActiveSkill = new ActiveSkillData
                {
                    Id = 999,
                    Name = "Desert Dragon Slash",
                    EffectType = SkillEffectType.HavocStrike,
                    Param = 220f,
                    TriggerWeight = 200,     // 原本仅 20% 概率
                    UseCountLimit = 1
                },
                EquippedRelic = new RelicInstance
                {
                    Name = "Crown of the Desert King",
                    Sockets = new List<AffixData>
                    {
                        new AffixData { Type = AffixType.FirstTurnGuaranteed, Name = "Mandate of First Strike" }, // 首轮必发词条!
                        new AffixData { Type = AffixType.HavocCritMultiplier, Value = 30f, Name = "Havoc Fang" }  // 暴伤+30%!
                    }
                }
            };

            var compiledSkill = op.CompileFinalSkill();
            Console.WriteLine($"  [Operative Compiled Skill]: {compiledSkill.Name} | Param: {compiledSkill.Param}% (Original 220% + IV 25% + Relic 30% = 275%) | Guaranteed Turn 1: {compiledSkill.IsFirstTurnGuaranteed}");

            var playerLegion = new Legion(op.CustomName, 1200000, init: 140, fort: 30, agi: 20, dom: 70, isLeft: true);
            playerLegion.EquippedSkills.Add(compiledSkill);

            var enemyLegion = new Legion("Bandit Stronghold Boss", 1000000, init: 80, fort: 100, agi: 10, dom: 30, isLeft: false);

            var sim3 = new BattleSimulator(seed: 99, presenter: presenter);
            var rec3 = sim3.Simulate(playerLegion, enemyLegion, maxTurns: 10);
            Console.WriteLine($"\n[Result 3] Winner: {rec3.Result} in {rec3.TotalTurns} turns.");

            Console.WriteLine("\n=================================================================");
            Console.WriteLine("    SIMULATION ENGINE VERIFICATION COMPLETED SUCCESSFULLY!");
            Console.WriteLine("=================================================================");
        }
    }
}
