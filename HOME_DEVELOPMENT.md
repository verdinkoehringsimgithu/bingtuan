# 回家继续开发

迁移日期：2026-11-16。仓库：https://github.com/verdinkoehringsimgithu/bingtuan

## 获取工程

安装Git for Windows、Unity Hub、Python 3.11（含pip、Tkinter）。推荐克隆到`D:\123`，部分外部工具与旧研究脚本仍使用这个绝对路径。

```powershell
git clone https://github.com/verdinkoehringsimgithu/bingtuan.git D:\123
Set-Location D:\123
python tools/migration/restore_research.py
python tools/migration/check_home.py
```

克隆到空目录，已有修改先保存。普通Git即可，不需要LFS。研究分卷首次下载较大；恢复脚本校验分卷、整包和每个文件的SHA-256，已有相同文件跳过，内容不同时停止保留本地修改。正常Unity开发可不先恢复研究记录，完整复现实验与旧验收需恢复。

没有D盘可克隆至其他目录并直接打开Unity；人物工具支持传入图库目录。技能工具词库、特效外部同步及旧研究脚本需相应调整路径。本次保留已验收源码和签名，不批量重写历史文件。

## 打开Unity

通过Unity Hub安装`2022.3.62f3c1`，添加`D:\123\LegionBattle\LegionBattle`，不是外层LegionBattle。首次导入重建Library，Packages使用锁定注册表，需联网下载。

打开`Assets/Scenes/BattleScene.unity`检查正式战斗；特效用`Assets/Scenes/BattleEffectTestScene.unity`或`Tools/战斗/打开特效测试模块`。必须保留全部.meta文件。

重要配置：

- `Assets/Characters/character_bond_labels.json`：人物标签。
- `Assets/Characters/CharacterDatabase.asset`：人物数据库。
- `Assets/Resources/EffectTimingConfig.json`：特效位置、缩放、排序、时点、动作与回血时点。
- `Assets/Resources/FormationConfig.json`：阵容布局。
- 根目录`effect_names.json`、`effect_animation_ids.json`、`effect_skill_mapping.json`：外部命名、ID与配对。

UserSettings中的Config自动保存存在时也会上传；本机当前未发现额外Config自动保存，Resources内有生效配置。编辑器账号和搜索布局偏好不上传。

## 外部工具与Python

```powershell
.\CharaClassifier.exe "D:\123\LegionBattle\LegionBattle\Assets\Characters"
.\SkillGenerator.exe
python -m venv combat_numerical_paradigms/v11_research/.venv
.\combat_numerical_paradigms\v11_research\.venv\Scripts\python.exe -m pip install -r tools/requirements-home.txt
.\combat_numerical_paradigms\v11_research\.venv\Scripts\python.exe pixel_effect_namer.py
.\combat_numerical_paradigms\v11_research\.venv\Scripts\python.exe test_30man_combat_simulator.py
```

重编外部工具：`powershell -ExecutionPolicy Bypass -File tools/build_tools.ps1`。默认输出tools/build，不覆盖原exe；该目录的人物工具需显式传入图库路径。技能工具仍读取D:\123词库。

各研究requirements保留原固定版本，home依赖另补Pillow/openpyxl。历史ps1中的Codex缓存Python路径属于旧机器，在家改成本地虚拟环境，或直接用对应python执行研究脚本。

## 开发基线与同步

23项羁绊已接入，按调用方配置开启。最新完整验收在`progression_difficulty/compound_runtime_2026_10_28`，混合交互在`identity_interactions_2026_10_28`；累计25,200场数值对照。数值一致性验证与平衡候选的适用范围分别见接入/研究规范。

先读AGENT.md与最近CC-Session-Logs。六阶段5/10/15/20/25/30人，上限30级，每人一件装备、每队最多4顶级装备。旧研究与签名快照保留，新机制建新版本。

开始前`git pull --ff-only`；结束关闭正在写配置的工具，用`git status`检查并一起提交Assets、meta、标签、Resources配置和源码，再push。恢复后的旧研究大记录由迁移清单忽略，避免重复上传；新增记录另建受控目录或分卷。

迁移不含Unity缓存、Python虚拟环境、旧独立Release构建、重复备份、APK及历史拆包冷库。外部技能工具默认历史拆包技能表未迁移，可打开已有导出CSV或生成新表；当前Unity使用Resources内正式数据。原地图独立导出备份未替代当前工程，原说明保留在docs及根README后半部。
