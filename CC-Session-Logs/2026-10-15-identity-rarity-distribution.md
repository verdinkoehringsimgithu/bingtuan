# 排除阴影与羁绊稀有度分布

GroundShadow.png位于Assets/Characters根目录，是BattleSceneSetupTool创建/引用的地面阴影；该场景工具本来排除它，人物工具Scan漏了排除。已按文件名大小写不敏感排除，未删除原PNG/meta以保留战斗场景依赖。根目录exe更新并重新打开；旧程序备份.gemini/character_distribution_backup。

本次统计采用最新人物标注JSON，经CharacterLabelStore同一合并及阶级规则，8组动作去重，只按身份作为羁绊。排除阴影后1213人、25个身份、未填0、多身份0；T1～T6分别147/219/290/311/183/63。各行、各列合计与人物总数一致。

结果：combat_numerical_paradigms/progression_difficulty/character_statistics/IDENTITY_BY_RARITY_2026-10-15.md、identity_by_rarity_2026-10-15.csv、summary_2026-10-15.json及distribution_2026-10-15.json。复现：.gemini/CharacterDistributionReport.cs编译引用最新人物工具，再运行.gemini/summarize_character_distribution.py。统计只读主资料。

学生86人分布20/12/26/27/1/0（T1～T6），85人处于T1～T4；侠客10人中9人T6；忍者9人。这里只给实际分类分布，不修改任何人物身份/阶级或羁绊效果。
