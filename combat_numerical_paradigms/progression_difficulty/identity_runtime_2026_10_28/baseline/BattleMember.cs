using System;
using System.Collections.Generic;
using UnityEngine;

namespace LegionBattle.Battle
{
    /// <summary>
    /// 单个上阵战斗成员模型 (完全支持自由配置属性、战力、品阶与携带技能)
    /// </summary>
    [Serializable]
    public class BattleMember
    {
        public int memberIndex;
        public string characterName = "战士";
        public int rarityTier = 1;
        public int level = 1;
        public int[] levelOneStats;     // C/R/I/M，装备加成独立于成长端点
        public int[] levelThirtyStats;
        public CombatItem equipment = new CombatItem(); // 每位成员一件装备，机制绑定持有者

        public double baseBP = 3200;   // 战力保留精度，显示时取整
        public int speed = 0;          // 先攻
        public int defense = 0;        // 防御
        public int dodge = 0;          // 闪避
        public int authority = 0;      // 王者

        public List<BattleSkill> skills = new List<BattleSkill>();
        public CharacterSheetData sheetData; // 关联的行走图数据 (可选)

        public BattleMember() { }

        public BattleMember(string name, int tier, int bp, int spd = 0, int def = 0, int ddg = 0, int auth = 0)
        {
            this.characterName = name;
            this.rarityTier = tier;
            this.baseBP = bp;
            this.speed = spd;
            this.defense = def;
            this.dodge = ddg;
            this.authority = auth;
        }

        /// <summary>
        /// 从 CharacterSheetData 动态构建一个战斗成员
        /// </summary>
        public static BattleMember FromSheetData(CharacterSheetData data, int index = 0)
        {
            if (data == null)
            {
                return new BattleMember("新兵", 1, 3200);
            }

            int tier = Mathf.Clamp(data.rarity, 1, 6);
            // 战力优先读取自定义设置，若未配置则使用品阶基准作为默认初值，绝不在计算层写死不可变
            int bp = data.customBP > 0 ? data.customBP : CharacterSheetData.GetBaseBP(tier);

            BattleMember member = new BattleMember(
                string.IsNullOrEmpty(data.characterName) ? $"角色_{index + 1}" : data.characterName,
                tier,
                bp,
                data.speed,
                data.defense,
                data.dodge,
                data.authority
            );
            member.memberIndex = index;
            member.sheetData = data;

            return member;
        }
    }
}
