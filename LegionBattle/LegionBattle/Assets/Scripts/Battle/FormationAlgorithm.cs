using System;
using System.Collections.Generic;
using UnityEngine;

namespace LegionBattle.Battle
{
    /// <summary>
    /// 任意人数军团对称阵型与三角形队列算法
    /// 规则：
    /// 1. 第一排至少 1 人；
    /// 2. 第一排优先保持 1 / 3 / 5 的排列（严禁 2 或 4），形成对称单顶点或稳固箭头；
    /// 3. 以第一排为顶点向后逐排展开，左右两侧沿垂直轴线（Y 轴）严格居中对称；
    /// 4. 动态计算每一位的局部坐标 (xOffset, yOffset) 与渲染层级 (sortingOrder)。
    /// </summary>
    public static class FormationAlgorithm
    {
        public struct FormationSlot
        {
            public int index;        // 成员总序号 0..N-1
            public int row;          // 从前往后排数 (0 为最前排/顶点)
            public int colInRow;     // 在该排内的序号 0..countInRow-1
            public float xOffset;    // 相对于军团原点的横向偏移 (沿冲锋方向推进)
            public float yOffset;    // 相对于军团对称中心的纵向偏移 (0 为正中)
        }

        /// <summary>
        /// 计算任意总人数 N 下的逐排人数分布 (支持 1 到 30 人任意动态人数)
        /// 规则：
        /// 1. 第一排人数必须为 1、3 或 5（绝对禁止 2 或 4），形成稳固对称顶点或锋矢；
        /// 2. 从顶点向后逐排呈三角形/金字塔对称展开；
        /// 3. 左右两侧关于纵向中线严格居中对称。
        /// </summary>
        public static List<int> CalculateRowCounts(int totalCount, int preferredFront = 1)
        {
            List<int> rows = new List<int>();
            if (totalCount <= 0) return rows;

            // 顶点人数仅允许 1, 3, 5，严禁 2 或 4
            int frontCount = (preferredFront == 3 || preferredFront == 5) ? preferredFront : 1;
            if (totalCount < frontCount) frontCount = 1;

            if (totalCount == 1) { rows.Add(1); return rows; }
            if (totalCount == 2) { rows.Add(1); rows.Add(1); return rows; }
            if (totalCount == 3)
            {
                if (frontCount == 3) { rows.Add(3); return rows; }
                rows.Add(1); rows.Add(2); return rows;
            }
            if (totalCount == 4)
            {
                if (frontCount == 3) { rows.Add(3); rows.Add(1); return rows; }
                rows.Add(1); rows.Add(3); return rows;
            }

            rows.Add(frontCount);
            int remain = totalCount - frontCount;

            // 随后逐排展开递增
            int nextWidth = (frontCount == 1) ? 2 : (frontCount + 1);
            int maxRowWidth = 7; // 单排上限，避免横向过度拉伸遮挡

            while (remain > 0)
            {
                int take = Mathf.Min(nextWidth, maxRowWidth);
                if (remain <= take)
                {
                    rows.Add(remain);
                    remain = 0;
                }
                else
                {
                    rows.Add(take);
                    remain -= take;
                    if (nextWidth < maxRowWidth) nextWidth++;
                }
            }

            // 平滑调整末排
            BalanceRows(rows, frontCount);
            return rows;
        }

        private static void BalanceRows(List<int> rows, int frontCount)
        {
            if (rows.Count <= 2) return;

            // 若最后一排人数过少(仅1人)且上一排有多余人，平滑匀1人
            int lastIdx = rows.Count - 1;
            if (rows[lastIdx] == 1 && rows[lastIdx - 1] > 2)
            {
                rows[lastIdx - 1]--;
                rows[lastIdx]++;
            }

            // 再次严厉校验：第一排必须为 1、3 或 5，绝不允许为 2 或 4
            if (rows[0] == 2 || rows[0] == 4)
            {
                int diff = 1;
                rows[0] -= diff;
                if (rows.Count > 1) rows[1] += diff;
            }
        }

        /// <summary>
        /// 获取当前人数与阵型排布的简述信息 (如 "人数: 10人 | 排布: [1, 2, 3, 4] (顶点1人，对称三角)")
        /// </summary>
        public static string GetFormationSummary(int totalCount, int preferredFront = 1)
        {
            List<int> rows = CalculateRowCounts(totalCount, preferredFront);
            string rowStr = string.Join(", ", rows.ConvertAll(r => r.ToString()).ToArray());
            return string.Format("人数: {0}人 | 共{1}排: [{2}] (第1排{3}人顶点，居中对称)",
                totalCount, rows.Count, rowStr, rows.Count > 0 ? rows[0] : 0);
        }

        /// <summary>
        /// 为任意人数 N 计算所有站位坐标
        /// </summary>
        /// <param name="totalCount">队伍总人数 (1..30)</param>
        /// <param name="spacingX">横向排间距 (前进深度)</param>
        /// <param name="spacingY">纵向列间距 (上下宽度)</param>
        /// <param name="isFacingRight">是否面向右侧 (左军为 true，右军为 false)</param>
        /// <param name="preferredFront">第一排偏好人数 (1, 3, 5)</param>
        public static List<FormationSlot> GenerateSlots(int totalCount, float spacingX, float spacingY, bool isFacingRight, int preferredFront = 1)
        {
            List<int> rowCounts = CalculateRowCounts(totalCount, preferredFront);
            List<FormationSlot> slots = new List<FormationSlot>(totalCount);

            int currentGlobalIdx = 0;
            for (int r = 0; r < rowCounts.Count; r++)
            {
                int countInRow = rowCounts[r];
                // r = 0 为最前排（顶点，靠近战场中线）
                // 随 r 增加，向各自本方后方延伸 (左军往左延伸即 -X，右军往右延伸即 +X)
                float x = r * spacingX * (isFacingRight ? -1f : 1f);

                for (int c = 0; c < countInRow; c++)
                {
                    // 纵向沿 Y=0 中心轴对称居中分布
                    // 例如 1 人在 0; 3 人在 -1, 0, 1; 2 人在 -0.5, 0.5
                    float y = (c - (countInRow - 1) * 0.5f) * spacingY;

                    FormationSlot slot = new FormationSlot
                    {
                        index = currentGlobalIdx++,
                        row = r,
                        colInRow = c,
                        xOffset = x,
                        yOffset = y
                    };
                    slots.Add(slot);
                }
            }

            return slots;
        }
    }
}
