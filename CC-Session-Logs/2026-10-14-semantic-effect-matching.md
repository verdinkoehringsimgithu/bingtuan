# 技能词条与特效配对优化

用户要求：检查适配性，更充分使用已有类型和变体；用户同时在检查测试场景。

完成：主Unity项目SkillEffectMatcher与根目录SkillGenerator.cs同步优化整体意象优先、语义同类候选及前部元素/材质颜色识别。重新编译并更新SkillGenerator.exe和SkillGenerator_cli.exe，旧程序保存在.gemini/matching_optimization_backup。

证据：同一冻结24000条语料（seed314159；4流派×6阶×1000）变体376→427/467，类型63→63，前五类占比33.05%→27.47%，非法配对0。实际生成12000条通过；Unity独立项目27525项工具检查通过（含24000条两端一致性和11条语义样例），正式生命周期73项通过，退出由调用方决定。

保留：有效已有ID、动画图片/元数据、全部用户特效调校、战斗数值。只有新生成或显式全表刷新采用新配对；没有静默重分配有效ID。

现场状态：.gemini/battle_scene_validation是用户正在检查的项目，本轮未同步也未关闭其Unity进程。独立验证在.gemini/effect_sorting_validation完成。之后同步须保留用户当前调校及自动备份，不能拿主项目JSON覆盖。

交付说明：combat_numerical_paradigms/progression_difficulty/EFFECT_MATCHING_GUIDE.md。完整统计与逐条记录位于同目录effect_tuning；Unity最终日志unity_semantic_matching.log及unity_semantic_matching_lifecycle.log。
