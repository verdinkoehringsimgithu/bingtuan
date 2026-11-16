using System;
using System.Collections.Generic;
using UnityEngine;

namespace LegionBattle.Battle
{
    [Serializable]
    public class CharacterSheetData
    {
        public string characterName;
        public CharacterTraits traits;
        public int rarity = 1; // 1:灰阶, 2:绿阶, 3:蓝阶, 4:紫阶, 5:金阶, 6:彩阶
        public Sprite[] downFrames = new Sprite[4];
        public Sprite[] leftFrames = new Sprite[4];
        public Sprite[] rightFrames = new Sprite[4];
        public Sprite[] upFrames = new Sprite[4];

        public int customBP = 0; // 自定义战力 (大于 0 时优先使用，不锁死品阶基准)
        public int speed = 0;    // 先攻
        public int defense = 0;  // 防御
        public int dodge = 0;    // 闪避
        public int authority = 0;// 王者
        public List<int> skillIds = new List<int>();

        public bool IsValid => downFrames != null && downFrames.Length == 4 && downFrames[0] != null;

        public int BaseBP => customBP > 0 ? customBP : GetBaseBP(rarity);

        public static int GetBaseBP(int r)
        {
            switch (r)
            {
                case 1: return 3200;  // T1 灰阶·杂兵 (~3,200) -> 30人 ≈ 96,000 BP
                case 2: return 5800;  // T2 绿阶·过渡 (~5,800) -> 30人 ≈ 174,000 BP
                case 3: return 9600;  // T3 蓝阶·骨干 (~9,600) -> 30人 ≈ 288,000 BP
                case 4: return 16000; // T4 紫阶·中坚 (~16,000) -> 30人 ≈ 480,000 BP
                case 5: return 28000; // T5 金阶·主力 (~28,000) -> 30人 ≈ 840,000 BP
                case 6: return 50000; // T6 彩阶·大核 (~50,000) -> 30人 ≈ 1,500,000 BP
                default: return 8000;
            }
        }
    }

}
