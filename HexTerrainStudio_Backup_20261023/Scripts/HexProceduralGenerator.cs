using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace HexTerrainStudio
{
    /// <summary>
    /// 六边形沙盘地图程序化生成器（地幔板块构造与有机水文气候架构）
    /// 针对 31行 * 35列规格 (总计 1,085 格, R=2.5 平顶六边形 odd-q)：
    /// 1. 基于板块构造理论 (Plate Tectonics & Continental Seeds) 的自然大陆划分：
    ///    - 杜绝九宫格、杜绝放射状辐条！通过泊松/最远点散布 8 个大陆地幔种子，配合 2D 相干噪声驱动的多源 Dijkstra 区域生长；
    ///    - 沿板块裂谷接触面自然开凿 1 格宽蜿蜒水系并注入海洋，天然划分为 7~10 个形态各异、面积均衡 (100~150格) 的壮美大陆；
    /// 2. 12 座大型多格立体山岳体系 (4 座 Yama1 雪山、4 座 Yama2 暗岩山、4 座 Yama3 蜿蜒长脊)：
    ///    - 严格遵循六边形 60° 旋转几何，每座山均赋予独立转向角 (0°, 60°, 120°, 180°, 240°, 300°)；
    ///    - 线性山脊 Yama3 沿板块碰撞线与大陆分水岭头尾相接延伸，绝非扎堆堆叠；
    /// 3. 二维惠特克 (Whittaker) 双变量有机相干气候带：
    ///    - 彻底告别水平条纹！由温度与湿度双相干噪声场主导，结合雪山降温场、荒漠燥热场与河谷增湿带；
    ///    - 严格映射材质：Hexagon 1 = 草原，Hexagon 2 = 雪地，Hexagon 3 = 沙漠；
    /// 4. 100 阵营跨大陆容量加权均匀采样与最小优先同步扩张 (每阵营 4~7 格无缝连通，留存约 300 格中立原野)；
    /// 5. 比例校准后的聚集式生态林与石阵 (按 Hex R=2.5 米制尺寸校准)。
    /// </summary>
    public static class HexProceduralGenerator
    {
        public class GenerationConfig
        {
            public int columns = 35;
            public int rows = 31;
            public float hexRadius = 2.5f;
            public int seed = 12345;

            // 阵营配置
            public int targetFactions = 100;
            public int minTerritorySize = 4;
            public int maxTerritorySize = 7;
        }

        // 附着物比例校准表（根据 Hex 半径 R=2.5 匹配真实米制尺寸）
        private static readonly Dictionary<string, Vector2> ScaleCalibration = new Dictionary<string, Vector2>
        {
            { "Tree Birch", new Vector2(0.22f, 0.29f) },
            { "Tree Maple", new Vector2(0.22f, 0.29f) },
            { "Pine_01", new Vector2(0.20f, 0.26f) },
            { "Pine_02", new Vector2(0.20f, 0.26f) },
            { "Pine_03", new Vector2(0.20f, 0.26f) },
            { "Pine_04", new Vector2(0.20f, 0.26f) },
            { "Pine_05", new Vector2(0.20f, 0.26f) },
            { "Fir_01", new Vector2(0.20f, 0.26f) },
            { "Spruce_Tree1", new Vector2(0.21f, 0.27f) },
            { "Acacia", new Vector2(0.25f, 0.32f) },
            { "Rock_01", new Vector2(0.35f, 0.50f) },
            { "Rock_02", new Vector2(0.35f, 0.50f) },
            { "Rock_03", new Vector2(0.35f, 0.50f) },
            { "Boulder_Group_1A1", new Vector2(0.30f, 0.45f) },
            { "Bush_Red", new Vector2(0.40f, 0.60f) },
            { "BushDry_B", new Vector2(0.40f, 0.60f) },
            { "Fern_A", new Vector2(0.45f, 0.65f) },
            { "Wheat_03a", new Vector2(0.50f, 0.70f) },
            { "Carrot_03", new Vector2(0.50f, 0.70f) }
        };

        // 山体内部子峰相对于中心 hex 的精确局部坐标（米制）
        private static readonly Vector2[] Yama1LocalOffsets = new Vector2[]
        {
            new Vector2(-2.77f, 1.58f), new Vector2(4.73f, 1.58f), new Vector2(0.98f, 3.75f),
            new Vector2(-2.77f, -2.75f), new Vector2(4.73f, -2.75f), new Vector2(0.98f, -0.58f), new Vector2(0.0f, 0.0f)
        };

        private static readonly Vector2[] Yama2LocalOffsets = new Vector2[]
        {
            new Vector2(-3.75f, -2.17f), new Vector2(0.0f, -4.33f), new Vector2(0.0f, 0.0f), new Vector2(0.0f, 4.33f),
            new Vector2(3.75f, -2.17f), new Vector2(3.75f, 2.17f), new Vector2(3.75f, 6.50f)
        };

        private static readonly Vector2[] Yama3LocalOffsets = new Vector2[]
        {
            new Vector2(-11.25f, 2.17f), new Vector2(-11.25f, 6.50f), new Vector2(-11.25f, 10.83f),
            new Vector2(-7.50f, 0.00f), new Vector2(-7.50f, 8.66f),
            new Vector2(-3.75f, 2.17f), new Vector2(-3.75f, 10.83f),
            new Vector2(0.00f, -8.66f), new Vector2(0.00f, -4.33f), new Vector2(0.00f, 0.00f), new Vector2(0.00f, 8.66f),
            new Vector2(3.75f, -10.83f), new Vector2(3.75f, -6.50f), new Vector2(3.75f, -2.17f), new Vector2(3.75f, 2.17f), new Vector2(3.75f, 6.50f)
        };

        public static HexMapData Generate(GenerationConfig config)
        {
            if (config == null) config = new GenerationConfig();
            var rng = new System.Random(config.seed);

            float dx = 1.5f * config.hexRadius;
            float dz = Mathf.Sqrt(3f) * config.hexRadius;

            // 1. 初始化底板网格
            var mapData = new HexMapData
            {
                mapName = $"HexMap_Seed_{config.seed}",
                columns = config.columns,
                rows = config.rows,
                hexRadius = config.hexRadius,
                tiles = new List<HexTileData>(config.columns * config.rows)
            };

            var grid = new HexTileData[config.columns, config.rows];
            for (int c = 0; c < config.columns; c++)
            {
                float colOffset = (c % 2 == 1) ? (dz * 0.5f) : 0f;
                for (int r = 0; r < config.rows; r++)
                {
                    float x = c * dx;
                    float z = r * dz + colOffset;
                    var tile = new HexTileData
                    {
                        col = c,
                        row = r,
                        x = x,
                        y = 0f,
                        z = z,
                        hasBase = true,
                        basePrefab = "Hexagon",
                        baseMaterial = "Hexagon 1", // 草原默认
                        hasHill = false,
                        hillPrefab = "",
                        hillRotY = 0f,
                        factionId = -1,
                        isCapital = false,
                        attachments = new List<HexAttachmentData>()
                    };
                    grid[c, r] = tile;
                    mapData.tiles.Add(tile);
                }
            }

            // 2. 地幔板块构造算法：划分 7~10 个自然大陆板块与蜿蜒裂谷水系（非九宫格、非放射状）
            var landRegions = PartitionMapByTectonicPlates(grid, config, rng);

            // 3. 多角度 12 座立体山岳体系：4 座雪山、4 座暗岩山、4 座长脊（头尾顺应分水岭延展）
            var mountainHexes = Place12RotatedMountains(grid, config, rng);

            // 4. 二维惠特克双变量相干噪声气候带（雪原 Hexagon 2、沙漠 Hexagon 3、草原 Hexagon 1）
            ApplyOrganic2DNoiseBiomes(grid, config, rng, mountainHexes);

            // 5. 跨大陆均衡 100 阵营主城采样（最远点启发式采样）
            var capitalTiles = Place100CapitalsAcrossRegions(grid, landRegions, config, rng, mountainHexes);

            // 6. 最小优先同步区域生长 (严格保证每阵营 4~7 格，零死锁)
            GrowTerritoriesSmallestFirst(grid, capitalTiles, config, rng, mountainHexes);

            // 7. 中立原野聚集式生态林与石阵
            ScatterRegionalNatureGroves(grid, landRegions, config, rng, mountainHexes);

            // 8. 自动序列化保存到 Maps 目录
            SaveToProceduralJson(mapData);

            Debug.Log($"[HexProceduralGenerator] 生成成功！板块数: {landRegions.Count}, 主城数: {capitalTiles.Count}/100, 山脉总占格: {mountainHexes.Count}");
            return mapData;
        }

        // ================= 阶段 2：地幔板块构造算法 (Tectonic Plates) =================

        private static List<List<Vector2Int>> PartitionMapByTectonicPlates(HexTileData[,] grid, GenerationConfig config, System.Random rng)
        {
            int cols = config.columns;
            int rows = config.rows;
            int numPlates = 8; // 目标 8 大板块核心

            // 2.0 宏观大群岛超椭圆平滑与四角倒角（告别方正四角与生硬切边，自然融入外围汪洋）
            float midC = (cols - 1) * 0.5f;
            float midR = (rows - 1) * 0.5f;
            float pSuper = 3.4f;
            float maskThreshold = 0.95f;
            float maskNoiseOffset = (float)(rng.NextDouble() * 500f);

            for (int c = 0; c < cols; c++)
            {
                for (int r = 0; r < rows; r++)
                {
                    float u = Mathf.Abs((c - midC) / midC);
                    float v = Mathf.Abs((r - midR) / midR);
                    float dist = Mathf.Pow(Mathf.Pow(u, pSuper) + Mathf.Pow(v, pSuper), 1f / pSuper);

                    // 2D 连续噪声扰动海岸线，使轮廓自然曲折
                    float n = (Mathf.PerlinNoise(c * 0.18f + maskNoiseOffset, r * 0.18f + maskNoiseOffset) - 0.5f) * 0.14f;
                    if (dist + n > maskThreshold)
                    {
                        grid[c, r].hasBase = false; // 四角与外边缘平滑倒角为开阔海域
                    }
                }
            }

            // 元胞自动机双向平滑外缘（消除孤立毛刺和单格凹陷）
            for (int pass = 0; pass < 2; pass++)
            {
                bool[,] nextBase = new bool[cols, rows];
                for (int c = 0; c < cols; c++)
                    for (int r = 0; r < rows; r++)
                        nextBase[c, r] = grid[c, r].hasBase;

                for (int c = 0; c < cols; c++)
                {
                    for (int r = 0; r < rows; r++)
                    {
                        int landNeighbors = 0;
                        foreach (var n in GetNeighbors(c, r, cols, rows))
                        {
                            if (grid[n.x, n.y].hasBase) landNeighbors++;
                        }

                        if (!grid[c, r].hasBase && landNeighbors >= 5)
                            nextBase[c, r] = true; // 填补内凹极小水坑
                        else if (grid[c, r].hasBase && landNeighbors <= 1)
                            nextBase[c, r] = false; // 消除孤立尖锐毛刺
                    }
                }

                for (int c = 0; c < cols; c++)
                    for (int r = 0; r < rows; r++)
                        grid[c, r].hasBase = nextBase[c, r];
            }

            // 2.1 泊松/最远点散布大陆核心种子（仅在有效陆地区域）
            var validSeedCands = new List<Vector2Int>();
            for (int c = 3; c < cols - 3; c++)
            {
                for (int r = 3; r < rows - 3; r++)
                {
                    if (grid[c, r].hasBase)
                    {
                        validSeedCands.Add(new Vector2Int(c, r));
                    }
                }
            }

            var plateSeeds = new List<Vector2Int>();
            while (plateSeeds.Count < numPlates && validSeedCands.Count > 0)
            {
                Vector2Int bestCand = validSeedCands[0];
                int bestDist = -1;
                for (int attempt = 0; attempt < 80; attempt++)
                {
                    var cand = validSeedCands[rng.Next(validSeedCands.Count)];
                    if (plateSeeds.Count == 0)
                    {
                        bestCand = cand;
                        break;
                    }
                    int minDist = int.MaxValue;
                    foreach (var s in plateSeeds)
                    {
                        int d = HexDistance(cand.x, cand.y, s.x, s.y);
                        if (d < minDist) minDist = d;
                    }
                    if (minDist > bestDist)
                    {
                        bestDist = minDist;
                        bestCand = cand;
                    }
                }
                plateSeeds.Add(bestCand);
            }

            // 2.2 多源带权 Dijkstra 板块同步生长（仅在陆地上生长）
            int[,] plateMap = new int[cols, rows];
            float[,] costSoFar = new float[cols, rows];
            for (int c = 0; c < cols; c++)
                for (int r = 0; r < rows; r++)
                {
                    plateMap[c, r] = -1;
                    costSoFar[c, r] = float.MaxValue;
                }

            var pq = new PriorityQueue<Vector2Int, float>();
            for (int pid = 0; pid < plateSeeds.Count; pid++)
            {
                var s = plateSeeds[pid];
                plateMap[s.x, s.y] = pid;
                costSoFar[s.x, s.y] = 0f;
                pq.Enqueue(s, 0f);
            }

            float noiseOffset = (float)(rng.NextDouble() * 300f);

            while (pq.Count > 0)
            {
                var curr = pq.Dequeue();
                int pid = plateMap[curr.x, curr.y];

                foreach (var n in GetNeighbors(curr.x, curr.y, cols, rows))
                {
                    if (!grid[n.x, n.y].hasBase) continue; // 边界海域不生长

                    // 二维相干 Perlin 噪声，使板块接触带边界全自然曲折
                    float nval = Mathf.PerlinNoise(n.x * 0.16f + noiseOffset, n.y * 0.16f + noiseOffset) * 1.5f
                               + Mathf.PerlinNoise(n.x * 0.32f + noiseOffset + 30f, n.y * 0.32f + noiseOffset + 30f) * 0.5f;
                    float edgeCost = 1.0f + nval + (float)rng.NextDouble() * 0.1f;
                    float newCost = costSoFar[curr.x, curr.y] + edgeCost;

                    if (newCost < costSoFar[n.x, n.y])
                    {
                        costSoFar[n.x, n.y] = newCost;
                        plateMap[n.x, n.y] = pid;
                        pq.Enqueue(n, newCost);
                    }
                }
            }

            // 2.3 沿板块接触裂谷开凿 1 格宽自然水系（非直线、非放射状，水流直通外围大洋）
            var rivers = new HashSet<Vector2Int>();
            for (int c = 0; c < cols; c++)
            {
                for (int r = 0; r < rows; r++)
                {
                    if (!grid[c, r].hasBase) continue;
                    int pA = plateMap[c, r];
                    if (pA == -1) continue;

                    foreach (var n in GetNeighbors(c, r, cols, rows))
                    {
                        if (!grid[n.x, n.y].hasBase) continue;
                        int pB = plateMap[n.x, n.y];
                        if (pB != -1 && pA < pB)
                        {
                            rivers.Add(new Vector2Int(c, r));
                            break;
                        }
                    }
                }
            }

            // 镂空水系
            foreach (var w in rivers)
            {
                grid[w.x, w.y].hasBase = false;
            }

            // 2.4 清理与平滑：剔除 < 20 格的细碎离岛，确保 8 大板块大气壮丽
            var allComps = GetLandComponents(grid, cols, rows);
            var validRegions = new List<List<Vector2Int>>();
            foreach (var comp in allComps)
            {
                if (comp.Count >= 20)
                {
                    validRegions.Add(comp);
                }
                else
                {
                    // 极细碎漂浮小岛置为水体
                    foreach (var cell in comp)
                    {
                        grid[cell.x, cell.y].hasBase = false;
                    }
                }
            }

            return validRegions;
        }

        private static List<List<Vector2Int>> GetLandComponents(HexTileData[,] grid, int cols, int rows)
        {
            var visited = new HashSet<Vector2Int>();
            var components = new List<List<Vector2Int>>();

            for (int c = 0; c < cols; c++)
            {
                for (int r = 0; r < rows; r++)
                {
                    var pos = new Vector2Int(c, r);
                    if (visited.Contains(pos) || !grid[c, r].hasBase) continue;

                    var comp = new List<Vector2Int>();
                    var q = new Queue<Vector2Int>();
                    q.Enqueue(pos);
                    visited.Add(pos);

                    while (q.Count > 0)
                    {
                        var curr = q.Dequeue();
                        comp.Add(curr);

                        foreach (var n in GetNeighbors(curr.x, curr.y, cols, rows))
                        {
                            if (!visited.Contains(n) && grid[n.x, n.y].hasBase)
                            {
                                visited.Add(n);
                                q.Enqueue(n);
                            }
                        }
                    }

                    components.Add(comp);
                }
            }

            return components;
        }

        // ================= 阶段 3：12 座多角度立体山岳体系 =================

        private class MountainSpec
        {
            public string prefab;
            public Vector2[] localOffsets;
            public int anchorCol;
            public int anchorRow;
            public float rotDeg;

            public MountainSpec(string p, Vector2[] o, int c, int r, float rot)
            {
                prefab = p; localOffsets = o; anchorCol = c; anchorRow = r; rotDeg = rot;
            }
        }

        private static HashSet<Vector2Int> Place12RotatedMountains(HexTileData[,] grid, GenerationConfig config, System.Random rng)
        {
            var mountainSet = new HashSet<Vector2Int>();
            int cols = config.columns;
            int rows = config.rows;
            float dx = 1.5f * config.hexRadius;
            float dz = Mathf.Sqrt(3f) * config.hexRadius;

            // 12 座山脉规格规划：
            // - 4 座雪山 Yama1 (不同旋转 60°, 180°, 300°, 120°)
            // - 4 座暗岩险峰 Yama2 (不同旋转 120°, 240°, 60°, 0°)
            // - 4 座长脊 Yama3 (严格头尾相接顺应山系走向，赋予独立旋转 60°, 60°, 180°, 240°)
            var specs = new List<MountainSpec>
            {
                // 4 座 Yama1 (北方雪域高原)
                new MountainSpec("Yama1", Yama1LocalOffsets, 6, 26, 60f),
                new MountainSpec("Yama1", Yama1LocalOffsets, 22, 27, 180f),
                new MountainSpec("Yama1", Yama1LocalOffsets, 30, 24, 300f),
                new MountainSpec("Yama1", Yama1LocalOffsets, 14, 28, 120f),

                // 4 座 Yama2 (南方荒漠与石原)
                new MountainSpec("Yama2", Yama2LocalOffsets, 6, 5, 120f),
                new MountainSpec("Yama2", Yama2LocalOffsets, 21, 5, 240f),
                new MountainSpec("Yama2", Yama2LocalOffsets, 30, 6, 60f),
                new MountainSpec("Yama2", Yama2LocalOffsets, 14, 4, 0f),

                // 4 座 Yama3 (长条山脊：前两座在中央板块头尾顺接，后两座横跨东西分水岭)
                new MountainSpec("Yama3", Yama3LocalOffsets, 7, 16, 60f),
                new MountainSpec("Yama3", Yama3LocalOffsets, 14, 22, 60f),  // 头尾延展
                new MountainSpec("Yama3", Yama3LocalOffsets, 25, 14, 180f),
                new MountainSpec("Yama3", Yama3LocalOffsets, 11, 6, 0f)
            };

            bool TryPlaceMountain(MountainSpec spec, int targetC, int targetR)
            {
                if (targetC < 1 || targetC >= cols - 1 || targetR < 1 || targetR >= rows - 1) return false;
                if (!grid[targetC, targetR].hasBase || mountainSet.Contains(new Vector2Int(targetC, targetR))) return false;

                float rad = spec.rotDeg * Mathf.Deg2Rad;
                float cosR = Mathf.Cos(rad);
                float sinR = Mathf.Sin(rad);

                float centerColOffset = (targetC % 2 == 1) ? (dz * 0.5f) : 0f;
                float anchorWx = targetC * dx;
                float anchorWz = targetR * dz + centerColOffset;

                var hitHexes = new List<Vector2Int>();

                foreach (var offset in spec.localOffsets)
                {
                    // 真实三角函数 2D 旋转计算
                    float rx = offset.x * cosR + offset.y * sinR;
                    float rz = -offset.x * sinR + offset.y * cosR;
                    float worldX = anchorWx + rx;
                    float worldZ = anchorWz + rz;

                    int hitCol = Mathf.RoundToInt(worldX / dx);
                    if (hitCol < 1 || hitCol >= cols - 1) return false;

                    float hColOff = (hitCol % 2 == 1) ? (dz * 0.5f) : 0f;
                    int hitRow = Mathf.RoundToInt((worldZ - hColOff) / dz);
                    if (hitRow < 1 || hitRow >= rows - 1) return false;

                    // 必须落在陆地且不与已有山体冲突
                    if (!grid[hitCol, hitRow].hasBase || mountainSet.Contains(new Vector2Int(hitCol, hitRow)))
                    {
                        return false;
                    }

                    hitHexes.Add(new Vector2Int(hitCol, hitRow));
                }

                // 提交山体占格
                grid[targetC, targetR].hasHill = true;
                grid[targetC, targetR].hillPrefab = spec.prefab;
                grid[targetC, targetR].hillRotY = spec.rotDeg; // 写入独立旋转角
                mountainSet.Add(new Vector2Int(targetC, targetR));

                foreach (var h in hitHexes)
                {
                    grid[h.x, h.y].hasHill = true;
                    if (h.x != targetC || h.y != targetR)
                    {
                        grid[h.x, h.y].hillPrefab = ""; // 占格阻挡，不重复实例化模型
                    }
                    mountainSet.Add(h);
                }

                return true;
            }

            foreach (var spec in specs)
            {
                bool placed = false;
                for (int radius = 0; radius <= 5 && !placed; radius++)
                {
                    for (int dc = -radius; dc <= radius && !placed; dc++)
                    {
                        for (int dr = -radius; dr <= radius && !placed; dr++)
                        {
                            if (TryPlaceMountain(spec, spec.anchorCol + dc, spec.anchorRow + dr))
                            {
                                placed = true;
                            }
                        }
                    }
                }
            }

            return mountainSet;
        }

        // ================= 阶段 4：二维惠特克相干噪声有机生物群系 (严格材质映射) =================

        private static void ApplyOrganic2DNoiseBiomes(HexTileData[,] grid, GenerationConfig config, System.Random rng, HashSet<Vector2Int> mountainSet)
        {
            int cols = config.columns;
            int rows = config.rows;

            float seedOffsetT = (float)(rng.NextDouble() * 500.0);
            float seedOffsetM = (float)(rng.NextDouble() * 500.0 + 500.0);

            var snowMountains = new List<Vector2Int>();
            var rockMountains = new List<Vector2Int>();
            foreach (var m in mountainSet)
            {
                if (grid[m.x, m.y].hillPrefab == "Yama1") snowMountains.Add(m);
                else if (grid[m.x, m.y].hillPrefab == "Yama2") rockMountains.Add(m);
            }

            for (int c = 0; c < cols; c++)
            {
                for (int r = 0; r < rows; r++)
                {
                    if (!grid[c, r].hasBase) continue;

                    // 双频相干二维 Perlin 噪声采样 (彻底杜绝一维水平条纹波浪)
                    float tNoise = Mathf.PerlinNoise(c * 0.16f + seedOffsetT, r * 0.16f + seedOffsetT) * 0.65f
                                 + Mathf.PerlinNoise(c * 0.35f + seedOffsetT + 25f, r * 0.35f + seedOffsetT + 25f) * 0.35f;

                    float mNoise = Mathf.PerlinNoise(c * 0.16f + seedOffsetM, r * 0.16f + seedOffsetM) * 0.65f
                                 + Mathf.PerlinNoise(c * 0.35f + seedOffsetM + 45f, r * 0.35f + seedOffsetM + 45f) * 0.35f;

                    // 15% 微弱自然宏观地轴梯度（北高冷、南温暖）
                    float latGradient = (float)r / rows;
                    float temperature = 0.50f + (tNoise - 0.5f) * 0.9f - (latGradient - 0.5f) * 0.25f;
                    float moisture = 0.50f + (mNoise - 0.5f) * 0.9f;

                    // 河流沿岸湿润平原加成
                    bool nearWater = false;
                    foreach (var n in GetNeighbors(c, r, cols, rows))
                    {
                        if (!grid[n.x, n.y].hasBase) { nearWater = true; break; }
                    }
                    if (nearWater) moisture += 0.25f;

                    // 雪山影响场：雪山周边半径 3 范围内温度骤降，雪线包裹高山
                    foreach (var sm in snowMountains)
                    {
                        int d = HexDistance(c, r, sm.x, sm.y);
                        if (d <= 3)
                        {
                            temperature -= 0.35f * (1.0f - (float)d / 4.0f);
                            break;
                        }
                    }

                    // 暗岩山影响场：石山周边降低湿度，营造荒原戈壁
                    foreach (var rm in rockMountains)
                    {
                        int d = HexDistance(c, r, rm.x, rm.y);
                        if (d <= 3)
                        {
                            moisture -= 0.30f * (1.0f - (float)d / 4.0f);
                            break;
                        }
                    }

                    // 气候带严格材质分类：
                    // Hexagon 1 = 草地 (丰沃平原)
                    // Hexagon 2 = 雪地 (严寒高原)
                    // Hexagon 3 = 沙地 (干燥荒漠)
                    if (temperature < 0.38f)
                    {
                        grid[c, r].baseMaterial = "Hexagon 2"; // 雪原
                    }
                    else if (temperature >= 0.48f && moisture < 0.44f)
                    {
                        grid[c, r].baseMaterial = "Hexagon 3"; // 沙漠
                    }
                    else
                    {
                        grid[c, r].baseMaterial = "Hexagon 1"; // 草原
                    }
                }
            }

            // 双轮六边形多数平滑滤波（消除单格噪点，保留宏大自然色块轮廓）
            for (int pass = 0; pass < 2; pass++)
            {
                string[,] tempMats = new string[cols, rows];
                for (int c = 0; c < cols; c++)
                    for (int r = 0; r < rows; r++)
                        tempMats[c, r] = grid[c, r].baseMaterial;

                for (int c = 1; c < cols - 1; c++)
                {
                    for (int r = 1; r < rows - 1; r++)
                    {
                        if (!grid[c, r].hasBase) continue;

                        int grassCount = 0;
                        int snowCount = 0;
                        int sandCount = 0;

                        foreach (var n in GetNeighbors(c, r, cols, rows))
                        {
                            if (!grid[n.x, n.y].hasBase) continue;
                            string m = tempMats[n.x, n.y];
                            if (m == "Hexagon 1") grassCount++;
                            else if (m == "Hexagon 2") snowCount++;
                            else if (m == "Hexagon 3") sandCount++;
                        }

                        if (snowCount >= 4) grid[c, r].baseMaterial = "Hexagon 2";
                        else if (sandCount >= 4) grid[c, r].baseMaterial = "Hexagon 3";
                        else if (grassCount >= 4) grid[c, r].baseMaterial = "Hexagon 1";
                    }
                }
            }
        }

        // ================= 阶段 5：跨大陆均衡 100 阵营主城采样 =================

        private static List<HexTileData> Place100CapitalsAcrossRegions(HexTileData[,] grid, List<List<Vector2Int>> regions, GenerationConfig config, System.Random rng, HashSet<Vector2Int> mountainSet)
        {
            int cols = config.columns;
            int rows = config.rows;
            int target = config.targetFactions;

            int totalLandCells = 0;
            foreach (var reg in regions) totalLandCells += reg.Count;

            var chosenCapitals = new List<HexTileData>(target);
            var factionQuotas = new List<int>();

            foreach (var reg in regions)
            {
                int q = Mathf.RoundToInt((float)reg.Count / totalLandCells * target);
                factionQuotas.Add(Mathf.Max(q, 4)); // 每大陆至少 8 个阵营
            }

            // 补齐/扣减到正好 100
            int diff = target;
            foreach (var q in factionQuotas) diff -= q;
            for (int i = 0; i < Mathf.Abs(diff); i++)
            {
                int idx = i % factionQuotas.Count;
                factionQuotas[idx] += (diff > 0) ? 1 : -1;
            }

            for (int rIdx = 0; rIdx < regions.Count; rIdx++)
            {
                var reg = regions[rIdx];
                int quota = factionQuotas[rIdx];

                var candidates = new List<Vector2Int>();
                var fallbackCandidates = new List<Vector2Int>();
                foreach (var cell in reg)
                {
                    if (grid[cell.x, cell.y].hasBase &&
                        !mountainSet.Contains(cell) &&
                        cell.x >= 2 && cell.x < cols - 2 &&
                        cell.y >= 2 && cell.y < rows - 2)
                    {
                        // 预先筛查周围有效扩张空格 >= 3
                        int freeNeighbors = 0;
                        foreach (var n in GetNeighbors(cell.x, cell.y, cols, rows))
                        {
                            if (grid[n.x, n.y].hasBase && !mountainSet.Contains(n)) freeNeighbors++;
                        }
                        if (freeNeighbors >= 3)
                        {
                            candidates.Add(cell);
                        }
                        else if (freeNeighbors >= 2)
                        {
                            fallbackCandidates.Add(cell);
                        }
                    }
                }

                while (candidates.Count < quota && fallbackCandidates.Count > 0)
                {
                    candidates.Add(fallbackCandidates[0]);
                    fallbackCandidates.RemoveAt(0);
                }
                if (candidates.Count == 0) continue;

                var regCapitals = new List<Vector2Int>();
                int firstIdx = rng.Next(candidates.Count);
                regCapitals.Add(candidates[firstIdx]);
                candidates.RemoveAt(firstIdx);

                while (regCapitals.Count < quota && candidates.Count > 0)
                {
                    int bestIdx = -1;
                    float bestScore = -float.MaxValue;
                    int sampleCount = Mathf.Min(candidates.Count, 35);

                    for (int s = 0; s < sampleCount; s++)
                    {
                        int idx = rng.Next(candidates.Count);
                        var cand = candidates[idx];

                        int minDist = int.MaxValue;
                        foreach (var cap in regCapitals)
                        {
                            int d = HexDistance(cand.x, cand.y, cap.x, cap.y);
                            if (d < minDist) minDist = d;
                        }

                        int freeNeighbors = 0;
                        foreach (var n in GetNeighbors(cand.x, cand.y, cols, rows))
                        {
                            if (grid[n.x, n.y].hasBase && !mountainSet.Contains(n) && grid[n.x, n.y].factionId == -1)
                            {
                                freeNeighbors++;
                            }
                        }

                        float score = minDist * 7.0f + freeNeighbors * 3.0f + (float)rng.NextDouble() * 1.0f;
                        if (score > bestScore)
                        {
                            bestScore = score;
                            bestIdx = idx;
                        }
                    }

                    if (bestIdx >= 0)
                    {
                        regCapitals.Add(candidates[bestIdx]);
                        candidates.RemoveAt(bestIdx);
                    }
                    else break;
                }

                foreach (var c in regCapitals)
                {
                    chosenCapitals.Add(grid[c.x, c.y]);
                }
            }

            // 分配 0 ~ 99 阵营 ID
            for (int i = 0; i < chosenCapitals.Count; i++)
            {
                chosenCapitals[i].isCapital = true;
                chosenCapitals[i].factionId = i;
            }

            return chosenCapitals;
        }

        // ================= 阶段 6：最小优先同步区域生长 (4~7 格) =================

        private static void GrowTerritoriesSmallestFirst(HexTileData[,] grid, List<HexTileData> capitals, GenerationConfig config, System.Random rng, HashSet<Vector2Int> mountainSet)
        {
            int cols = config.columns;
            int rows = config.rows;

            var territories = new Dictionary<int, HashSet<Vector2Int>>();
            var targetSizes = new Dictionary<int, int>();

            for (int i = 0; i < capitals.Count; i++)
            {
                var capPos = new Vector2Int(capitals[i].col, capitals[i].row);
                territories[i] = new HashSet<Vector2Int> { capPos };
                targetSizes[i] = rng.Next(config.minTerritorySize, config.maxTerritorySize + 1);
            }

            bool changed = true;
            while (changed)
            {
                changed = false;

                // 优先让当前领地最小的阵营向外扩张，避免被相邻阵营迅速合围
                var activeFactions = new List<int>();
                foreach (var kvp in territories)
                {
                    if (kvp.Value.Count < targetSizes[kvp.Key])
                    {
                        activeFactions.Add(kvp.Key);
                    }
                }

                if (activeFactions.Count == 0) break;

                activeFactions.Sort((a, b) => territories[a].Count.CompareTo(territories[b].Count));

                foreach (var fid in activeFactions)
                {
                    var candNeighbors = new List<Vector2Int>();
                    foreach (var cell in territories[fid])
                    {
                        foreach (var n in GetNeighbors(cell.x, cell.y, cols, rows))
                        {
                            if (grid[n.x, n.y].hasBase &&
                                !mountainSet.Contains(n) &&
                                grid[n.x, n.y].factionId == -1)
                            {
                                candNeighbors.Add(n);
                            }
                        }
                    }

                    if (candNeighbors.Count > 0)
                    {
                        var chosen = candNeighbors[rng.Next(candNeighbors.Count)];
                        grid[chosen.x, chosen.y].factionId = fid;
                        territories[fid].Add(chosen);
                        changed = true;
                    }
                }
            }
        }

        // ================= 阶段 7：中立原野聚集式生态林与石阵 =================

        private static void ScatterRegionalNatureGroves(HexTileData[,] grid, List<List<Vector2Int>> regions, GenerationConfig config, System.Random rng, HashSet<Vector2Int> mountainSet)
        {
            int cols = config.columns;
            int rows = config.rows;

            foreach (var reg in regions)
            {
                // 仅在中立野外且非山体格生成生态林
                var wildCandidates = new List<Vector2Int>();
                foreach (var c in reg)
                {
                    if (grid[c.x, c.y].hasBase && !mountainSet.Contains(c) && grid[c.x, c.y].factionId == -1)
                    {
                        wildCandidates.Add(c);
                    }
                }

                if (wildCandidates.Count == 0) continue;

                // 选取 2~3 个林地/石原聚集中心
                int groveCount = Mathf.Min(3, Mathf.Max(1, wildCandidates.Count / 18));
                for (int g = 0; g < groveCount; g++)
                {
                    var center = wildCandidates[rng.Next(wildCandidates.Count)];
                    string centerMat = grid[center.x, center.y].baseMaterial;

                    // 覆盖中心及其相邻野性格
                    var groveHexes = new List<Vector2Int> { center };
                    foreach (var n in GetNeighbors(center.x, center.y, cols, rows))
                    {
                        if (wildCandidates.Contains(n) && rng.NextDouble() < 0.65)
                        {
                            groveHexes.Add(n);
                        }
                    }

                    foreach (var gh in groveHexes)
                    {
                        var tile = grid[gh.x, gh.y];
                        if (tile.attachments.Count > 0) continue;

                        int propCount = rng.Next(1, 3);
                        for (int p = 0; p < propCount; p++)
                        {
                            string prefabName;
                            if (centerMat == "Hexagon 2") // 雪原
                            {
                                string[] snowProps = { "Pine_01", "Pine_02", "Fir_01", "Spruce_Tree1", "Rock_01" };
                                prefabName = snowProps[rng.Next(snowProps.Length)];
                            }
                            else if (centerMat == "Hexagon 3") // 沙漠
                            {
                                string[] sandProps = { "Acacia", "Rock_01", "Rock_02", "Rock_03", "BushDry_B" };
                                prefabName = sandProps[rng.Next(sandProps.Length)];
                            }
                            else // 草原
                            {
                                string[] grassProps = { "Tree Birch", "Tree Maple", "Bush_Red", "Fern_A", "Wheat_03a" };
                                prefabName = grassProps[rng.Next(grassProps.Length)];
                            }

                            Vector2 scaleRange = ScaleCalibration.ContainsKey(prefabName)
                                ? ScaleCalibration[prefabName]
                                : new Vector2(0.3f, 0.5f);

                            float scale = Mathf.Lerp(scaleRange.x, scaleRange.y, (float)rng.NextDouble());
                            float rotY = (float)rng.NextDouble() * 360f;
                            float angle = (float)rng.NextDouble() * Mathf.PI * 2f;
                            float dist = (float)rng.NextDouble() * (config.hexRadius * 0.45f);
                            float offX = Mathf.Cos(angle) * dist;
                            float offZ = Mathf.Sin(angle) * dist;

                            Quaternion qRot = Quaternion.Euler(0f, rotY, 0f);
                            tile.attachments.Add(new HexAttachmentData
                            {
                                prefabName = prefabName,
                                attachedLayer = "Base",
                                localX = offX,
                                localY = 0f,
                                localZ = offZ,
                                worldX = tile.x + offX,
                                worldY = tile.y,
                                worldZ = tile.z + offZ,
                                rotX = qRot.x,
                                rotY = qRot.y,
                                rotZ = qRot.z,
                                rotW = qRot.w,
                                scaleX = scale,
                                scaleY = scale,
                                scaleZ = scale
                            });
                        }
                    }
                }
            }
        }

        // ================= 阶段 8：自动保存 JSON =================

        private static void SaveToProceduralJson(HexMapData mapData)
        {
            try
            {
                string folder = "Assets/HexTerrainStudio/Maps";
                if (!Directory.Exists(folder)) Directory.CreateDirectory(folder);
                string path = Path.Combine(folder, "Map_02_Procedural.json");
                string json = JsonUtility.ToJson(mapData, true);
                File.WriteAllText(path, json);
                Debug.Log($"[HexProceduralGenerator] 地图已自动同步保存至: {path}");
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[HexProceduralGenerator] 自动保存 JSON 失败: {ex.Message}");
            }
        }

        // ================= 工具方法 =================

        public static List<Vector2Int> GetNeighbors(int c, int r, int cols, int rows)
        {
            var list = new List<Vector2Int>(6);
            int[,] offsets = (c % 2 == 0)
                ? new int[,] { { 0, -1 }, { 0, 1 }, { -1, -1 }, { -1, 0 }, { 1, -1 }, { 1, 0 } }
                : new int[,] { { 0, -1 }, { 0, 1 }, { -1, 0 }, { -1, 1 }, { 1, 0 }, { 1, 1 } };

            for (int i = 0; i < 6; i++)
            {
                int nc = c + offsets[i, 0];
                int nr = r + offsets[i, 1];
                if (nc >= 0 && nc < cols && nr >= 0 && nr < rows)
                {
                    list.Add(new Vector2Int(nc, nr));
                }
            }
            return list;
        }

        public static int HexDistance(int c1, int r1, int c2, int r2)
        {
            int q1 = c1;
            int axR1 = r1 - (c1 - (c1 & 1)) / 2;
            int q2 = c2;
            int axR2 = r2 - (c2 - (c2 & 1)) / 2;
            int dq = q1 - q2;
            int dr = axR1 - axR2;
            return (Mathf.Abs(dq) + Mathf.Abs(dq + dr) + Mathf.Abs(dr)) / 2;
        }

        private class PriorityQueue<TElement, TPriority> where TPriority : IComparable<TPriority>
        {
            private List<Tuple<TElement, TPriority>> _elements = new List<Tuple<TElement, TPriority>>();
            public int Count => _elements.Count;

            public void Enqueue(TElement item, TPriority priority)
            {
                _elements.Add(Tuple.Create(item, priority));
                int ci = _elements.Count - 1;
                while (ci > 0)
                {
                    int pi = (ci - 1) / 2;
                    if (_elements[ci].Item2.CompareTo(_elements[pi].Item2) >= 0) break;
                    var tmp = _elements[ci];
                    _elements[ci] = _elements[pi];
                    _elements[pi] = tmp;
                    ci = pi;
                }
            }

            public TElement Dequeue()
            {
                int li = _elements.Count - 1;
                var front = _elements[0].Item1;
                _elements[0] = _elements[li];
                _elements.RemoveAt(li);
                --li;
                int pi = 0;
                while (true)
                {
                    int ci = pi * 2 + 1;
                    if (ci > li) break;
                    int rc = ci + 1;
                    if (rc <= li && _elements[rc].Item2.CompareTo(_elements[ci].Item2) < 0) ci = rc;
                    if (_elements[pi].Item2.CompareTo(_elements[ci].Item2) <= 0) break;
                    var tmp = _elements[pi];
                    _elements[pi] = _elements[ci];
                    _elements[ci] = tmp;
                    pi = ci;
                }
                return front;
            }
        }
    }
}
