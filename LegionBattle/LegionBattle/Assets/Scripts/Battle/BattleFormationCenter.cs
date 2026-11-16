using UnityEngine;

namespace LegionBattle.Battle
{
    public static class BattleFormationCenter
    {
        public static Vector3 Visible(BattleCharacterPreview[] members)
        {
            return GetCenter(members);
        }

        /// <summary>
        /// 阵型基准几何中心：基于所有活跃成员初始站位(BasePosition)的算术平均值，
        /// 不随任何受击击飞/位移动态漂移，起点稳固在方阵最正中。
        /// </summary>
        public static Vector3 GetCenter(BattleCharacterPreview[] members)
        {
            if (members == null || members.Length == 0) return Vector3.zero;
            Vector3 sum = Vector3.zero;
            int count = 0;
            for (int i = 0; i < members.Length; i++)
            {
                var m = members[i];
                if (m != null && m.gameObject.activeInHierarchy && m.CharacterData != null)
                {
                    sum += m.BasePosition;
                    count++;
                }
            }
            if (count == 0) return Vector3.zero;
            Vector3 center = sum / count;
            center.y += 0.5f; // 抬升至小人身体视觉腰部，精准落在 30 人方阵最正中心
            center.z = 0f;
            return center;
        }
    }
}
