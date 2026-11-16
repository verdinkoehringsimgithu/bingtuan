# 战团开发工程

回家继续开发请先读 [HOME_DEVELOPMENT.md](HOME_DEVELOPMENT.md)。

- Unity工程：`LegionBattle/LegionBattle`，Unity `2022.3.62f3c1`。
- 正式战斗：`Assets/Scenes/BattleScene.unity`；特效测试：`Assets/Scenes/BattleEffectTestScene.unity`。
- 人物标注：`CharaClassifier.exe`；技能工具：`SkillGenerator.exe`。
- 羁绊接入：`combat_numerical_paradigms/progression_difficulty/IDENTITY_RUNTIME_INTEGRATION.md`。
- 最近交接：`CC-Session-Logs/2026-10-28-identity-interactions.md`。
- 大体积研究记录：`TransferData`分卷，运行`python tools/migration/restore_research.py`恢复并逐文件校验。不需要Git LFS。

以下保留原地图系统说明，具体当前工程内容以Assets为准。

# HexTerrainStudio 六边形沙盘地图系统使用说明书

> **版本**：v1.0.0 (Release)  
> **适用引擎**：Unity 2021.3 / 2022.3 / 2023.x / Unity 6  
> **标准规格**：31 行 × 35 列（1,085 正六边形网格，外接圆半径 $R=2.5$ 米，平顶 Flat-topped odd-q）  
> **核心定位**：专为 4X 大战略、SLG、战棋及文明类游戏设计的轻量、解耦、纯数据驱动的 3D 六边形沙盘生成与编辑工作流。

---

## 目录
1. [系统特性与架构简介](#一系统特性与架构简介)
2. [资源包文件结构说明](#二资源包文件结构说明)
3. [快速上手指南（三步出图）](#三快速上手指南三步出图)
4. [编辑器可视化操作手册](#四编辑器可视化操作手册)
5. [程序化宏观生成算法说明](#五程序化宏观生成算法说明)
6. [二次开发与 API 接入示例](#六二次开发与-api-接入示例)
7. [数据结构与 JSON 导出规范](#七数据结构与-json-导出规范)
8. [常见问题解答 (FAQ)](#八常见问题解答-faq)

---

## 一、系统特性与架构简介

HexTerrainStudio 采用业界前沿的**三层分层物理沙盘架构**与**纯数据驱动管线**：

1. **第 1 层：基底六边形网格（Layer1_Base）**
   - 单格六角基底地块，支持动态材质切换（草原 `Hexagon 1`、雪原 `Hexagon 2`、荒漠 `Hexagon 3`）；
   - 水域采用自然镂空显示（`hasBase = false`），底层直接透出海洋背景，零冗余开销。
2. **第 2 层：大型立体山脉与丘陵（Layer2_Hills）**
   - 涵盖 3 种多格大型山脉（7格雪峰 Yama1、7格暗岩山 Yama2、16格长条山脊 Yama3）；
   - 严密契合六角网格的 60° 旋转几何，每座山体拥有独立朝向角，并支持线性山脊沿分水岭“头尾自然顺接”；
   - 仅在锚点格实例化 1 个模型，所有覆盖的子格子均被严格标记为不可通行的物理阻挡，杜绝穿模与主城重叠。
3. **第 3 层：生态林、石阵与附着物（Layer3_Attachments）**
   - 针叶林（松树、冷杉、云杉）、阔叶林（白桦、枫树）、荒漠金合欢、各类自然岩石与作物；
   - 严格按六边形网格尺寸（$R=2.5$ 米）进行米制真实比例校准，以聚集式生态群落自然分布在中立原野。
4. **工业级宏观程序化生成管线**：
   - **地幔板块构造算法（Plate Tectonics）**：泊松最远点散布 8 个大陆核心，配合 2D 相干噪声多源 Dijkstra 生长，自然切分出 7~10 个独立大陆板块与蜿蜒裂谷水系（杜绝九宫格、杜绝放射状辐条）；
   - **二维惠特克气候场（Whittaker Biomes）**：多频 2D Perlin 温度与湿度双变量控制，结合雪山降温场、荒漠干燥场与河谷增湿带，彻底告别单调的一维水平条纹；
   - **100 阵营最小优先区域生长**：各大陆按容量加权分配主城配额，采用最小领地阵营优先的广度轮转扩张，稳定保证 100 阵营全部获得 4~7 格连通领土（平均 5.5 格），全图留存约 300 格中立荒野。

---

## 二、资源包文件结构说明

导入本 UnityPackage 后，文件统一存放于 `Assets/HexTerrainStudio/` 独立命名空间下，零代码侵入：

```text
Assets/HexTerrainStudio/
├── Editor/
│   ├── HexMapEditorWindow.cs       // 可视化沙盘与笔刷编辑器主窗口
│   ├── HexPackageExporter.cs       // 一键打包导出工具
│   └── HexSceneBuilder.cs          // 编辑器场景快速构建与初始化工具
├── Maps/
│   ├── Map_01.json                 // 标准样例地图数据
│   └── Map_02_Procedural.json      // 经过板块演化与100阵营校验的最新程序化沙盘
├── Scenes/
│   └── HexMapEditorScene.unity     // 开箱即用的预设沙盘编辑场景（自带摄像机与光照）
├── Scripts/
│   ├── HexMapData.cs               // 核心数据模型 (HexMapData, HexTileData, HexAttachmentData)
│   ├── HexMapSpawner.cs            // 地图加载器与对象池/材质解析器（核心运行时组件）
│   └── HexProceduralGenerator.cs   // 地幔板块构造、12山脉定向、惠特克气候与100阵营生成核心算法
└── 使用说明.md                     // 本使用说明文档
```

另外附带核心依赖模型与材质包（存放于 `Assets/AssetRaw/GameAssets/Hexagon/`）：
- `Hexagon.prefab`：标准六角基地预制体
- `Prefabs/Yama1.prefab`：7 格大型雪山主峰
- `Prefabs/Yama2.prefab`：7 格险峻暗岩石峰
- `Prefabs/Yama3.prefab`：16 格蜿蜒长脊山脉
- `Hexagon 1.mat` / `Hexagon 2.mat` / `Hexagon 3.mat`：草原、雪地、沙漠核心 PBR 材质

---

## 三、快速上手指南（三步出图）

### 步骤 1：导入 UnityPackage
在 Unity 顶部菜单栏点击 `Assets > Import Package > Custom Package...`，选中 `HexTerrainStudio_v1.0.unitypackage` 并全选导入。

### 步骤 2：打开编辑器场景与窗口
- 双击打开 `Assets/HexTerrainStudio/Scenes/HexMapEditorScene.unity`；
- 在顶部菜单栏点击：
  ```
  Tools > Hex Terrain > Hex Map Editor Window
  ```
  即可在 Unity 中弹出 3-Layer Hex Terrain Studio 编辑窗口（支持停靠在 Inspector 或 Console 旁）。

### 步骤 3：一键生成或加载地图
- **方式 A（一键运行程序化生成）**：
  在窗口顶部的【★ 程序化宏观沙盘生成】面板中输入任意随机种子（Seed），点击 **“★ 一键运行约束驱动程序化生成 ★”**，Scene 视图中将即刻生成由裂谷水系分割出的 8 大宏伟陆块与 12 座多向旋转山脉！
- **方式 B（加载预存 JSON 地图）**：
  在窗口底部的【地图数据保存与导出】面板中点击 **“导入/加载 JSON 地图”**，选中 `Assets/HexTerrainStudio/Maps/Map_02_Procedural.json`，即可秒级还原完整沙盘！

---

## 四、编辑器可视化操作手册

窗口提供 5 大功能板块，支持 Scene 视图所见即所得的笔刷绘制：

### 1. 程序化宏观沙盘生成 (Procedural Generation)
- **随机种子 (Seed)**：输入任意整数或点击“随机”生成不同地质构造的全新世界；
- **阵营数量**：滑动调节 10~100 阵营；
- **Scene 视图高亮 100 主城 (★)**：勾选后在 Scene 视图中会以粉色光圈直观标出所有 100 个阵营主城的中心位置；
- **生成按钮**：执行完整的地幔构造与气候生成算法，并自动落盘至 `Map_02_Procedural.json`。

### 2. 网格参数与初始化 (Grid Setup)
- **规格参数**：默认 31 行 × 35 列，六角半径 $R=2.5$ 米；
- **生成/初始化基底网格**：在场景中生成指定行列数的空白六角地表；
- **清空整张地图**：一键安全清除场景内所有生成的六角地块与模型。

### 3. 笔刷模式与三层画板 (Brush & Layers)
- **笔刷模式**：
  - `笔刷绘制 (Paint)`：左键在场景中点击或拖拽进行批量地块涂抹；
  - `橡皮擦除 (Erase)`：左键擦除指定位置的图层内容（如抹掉基底镂空成河流，或移除附着物）。
- **图层切换 (Active Layer)**：
  - **第 1 层：基底**：可选择绘制 `Hexagon 1 (草原)`、`Hexagon 2 (雪地)` 或 `Hexagon 3 (沙漠)`；
  - **第 2 层：丘陵/山脉**：可选择 `Yama1`、`Yama2`、`Yama3` 笔刷在已有陆地上放置立体山体；
  - **第 3 层：附着物**：可在树木、岩石、作物之间切换，自由刷取生态植被。
- **笔刷属性**：
  - `笔刷半径 (Radius)`：支持 1~5 格范围衰减；
  - `随机 Y 轴旋转`：开启后每次下笔随机旋转角度，呈现自然杂乱感；
  - `随机缩放区间`：支持按滑块设定附着物的随机大小浮动。

### 4. 数据导出与导入 (JSON I/O)
- **导出当前地图为 JSON**：将 Scene 视图中编辑好的沙盘连同 100 阵营领土分配完整导出为标准 JSON 文件；
- **导入/加载 JSON 地图**：从任意 JSON 文件还原沙盘。

---

## 五、程序化宏观生成算法说明

生成核心 [HexProceduralGenerator.cs](file:///D:/Xinyuan/xinyuan/UnityProject/Assets/HexTerrainStudio/Scripts/HexProceduralGenerator.cs) 严格遵守以下 7 阶段工业级数学约束：

| 阶段 | 核心算法与原理 | 达成效果 |
| :--- | :--- | :--- |
| **1. 初始网格** | 平顶六边形几何投射（列间距 $1.5R$，行间距 $\sqrt{3}R$） | 严格对齐 31×35 空间坐标 |
| **2. 地幔板块裂谷水系** | 泊松散布 8 大陆核 + 2D 相干噪声多源 Dijkstra 生长 | 杜绝九宫格与放射辐条，形成 7~10 个面积均衡（100~150格）的自然大陆板块 |
| **3. 12 座立体山岳** | 4雪山 + 4暗岩山 + 4长脊，各具 60° 旋转，Yama3 头尾相接 | 形成雄浑连续的大陆分水岭山脉，彻底解决山体不转向与扎堆堆叠问题 |
| **4. 惠特克双变量气候** | 双频 2D Perlin 噪声（温度 $T$ + 湿度 $M$）+ 山脉冷热场调制 | 自然形成雪峰高原、河谷湿润草原与干旱内陆荒漠，杜绝水平条纹 |
| **5. 100 阵营主城采样** | 各大陆面积比例加权配额 + 最远点启发式距离采样 | 100 主城均匀散布各大陆，确保每座主城具备 $\ge 3$ 个空闲扩张出口 |
| **6. 最小优先区域生长** | 优先调度领地最小阵营进行同步广度扩张 | 彻底消除合围死锁，保证全部阵营稳定获得 4~7 格连续领土，留存约 300 格中立原野 |
| **7. 聚集生态附着物** | 仅在中立野外格生成，匹配真实比例（树木 0.20~0.28，岩石 0.35~0.50） | 形成自然针叶林、石阵与阔叶绿洲 |

---

## 六、二次开发与 API 接入示例

在其他工程或运行时脚本中，您可以直接调用本套系统的纯 C# API：

### 示例 1：在运行时通过代码程序化生成沙盘
```csharp
using UnityEngine;
using HexTerrainStudio;

public class WorldMapManager : MonoBehaviour
{
    public HexMapSpawner spawner;

    void Start()
    {
        // 1. 配置沙盘生成参数
        var config = new HexProceduralGenerator.GenerationConfig
        {
            columns = 35,
            rows = 31,
            hexRadius = 2.5f,
            seed = 12345,          // 任意随机种子
            targetFactions = 100,  // 100 个阵营
            minTerritorySize = 4,  // 每阵营最少 4 格
            maxTerritorySize = 7   // 每阵营最多 7 格
        };

        // 2. 运行纯逻辑算法生成内存地图数据 (零 GC，纯数学计算)
        HexMapData mapData = HexProceduralGenerator.Generate(config);

        // 3. 将数据交由 Spawner 瞬间实例化为 3D 场景
        if (spawner != null)
        {
            spawner.BuildMap(mapData);
        }
    }
}
```

### 示例 2：从 JSON 文本读取地图
```csharp
using UnityEngine;
using HexTerrainStudio;

public class LoadMapExample : MonoBehaviour
{
    public HexMapSpawner spawner;
    public TextAsset mapJsonFile;

    void Start()
    {
        if (mapJsonFile != null && spawner != null)
        {
            HexMapData data = JsonUtility.FromJson<HexMapData>(mapJsonFile.text);
            spawner.BuildMap(data);
        }
    }
}
```

### 示例 3：查询阵营领地信息
```csharp
// 查询属于阵营 15 的所有六边形地块
List<HexTileData> factionTiles = mapData.tiles.FindAll(t => t.factionId == 15);

// 查找阵营 15 的主城所在地
HexTileData capital = mapData.tiles.Find(t => t.factionId == 15 && t.isCapital);

Debug.Log($"阵营 15 主城坐标: ({capital.col}, {capital.row}), 总领地格数: {factionTiles.Count}");
```

---

## 七、数据结构与 JSON 导出规范

系统导出的地图 JSON 遵循自包含（Self-Contained）轻量规范：

```json
{
  "mapName": "HexMap_Seed_12345",
  "columns": 35,
  "rows": 31,
  "hexRadius": 2.5,
  "tiles": [
    {
      "col": 6,
      "row": 26,
      "x": 22.5,
      "y": 0.0,
      "z": 112.5833,
      "hasBase": true,
      "basePrefab": "Hexagon",
      "baseMaterial": "Hexagon 2",
      "hasHill": true,
      "hillPrefab": "Yama1",
      "hillRotY": 60.0,
      "factionId": -1,
      "isCapital": false,
      "attachments": [
        {
          "prefabName": "Pine_01",
          "attachedLayer": "Base",
          "localX": 0.42,
          "localY": 0.0,
          "localZ": -0.31,
          "worldX": 22.92,
          "worldY": 0.0,
          "worldZ": 112.2733,
          "rotX": 0.0,
          "rotY": 0.4532,
          "rotZ": 0.0,
          "rotW": 0.8914,
          "scaleX": 0.24,
          "scaleY": 0.24,
          "scaleZ": 0.24
        }
      ]
    }
  ]
}
```

---

## 八、常见问题解答 (FAQ)

### Q1：导入到新项目后材质呈粉红色怎么办？
**答**：本工程材质基于 Unity 内置 Standard Shader / URP 规范。若您的目标工程使用的是通用渲染管线（URP），请在 Unity 顶部菜单点击 `Window > Rendering > Render Pipeline Converter`，勾选 `Built-in to URP` 并执行材质一键转换即可。

### Q2：如何更换我们自己项目的树木或岩石模型？
**答**：打开 [HexMapSpawner.cs](file:///D:/Xinyuan/xinyuan/UnityProject/Assets/HexTerrainStudio/Scripts/HexMapSpawner.cs)，定位到顶部的 `StandardPrefabPaths` 字典。您可以将键名（如 `"Pine_01"`、`"Rock_01"`）映射为您项目中的任意 Prefab 资源路径，也可以直接在编辑器的附着物画板下拉列表中选取使用。

### Q3：为什么地图边缘有镂空部分？
**答**：本沙盘基于真实海岛/大陆地理设计，镂空地块即为水体/海峡（`hasBase = false`）。在场景中放置一张水面面片（Water Plane）或天空盒海洋背景，镂空处即可天然呈现壮观的水系入海视觉效果。

### Q4：如何单独导出 UnityPackage？
**答**：随时在 Unity 顶部菜单栏点击：
```
Tools > Hex Terrain > ★ 打包导出 HexTerrainStudio (.unitypackage) ★
```
系统将自动追踪所有脚本、场景、JSON 地图及山脉模型依赖，直接打包并自动在 Windows 文件管理器中定位导出文件！
