# Unity 特效逐帧测试模块

## 用户要求

直接测试现有 67 类特效，不受技能类型筛选影响；在游戏中调整位置、伤害时点和受击物理时点，支持逐帧播放。自身特效在攻击方归位后播放，敌方特效从攻击接触开始，伤害与物理事件可以任意先后。用户允许选择 Unity 模块或外部程序，采用 Unity 模块以复用真实战斗。

## 实现

- `BattleEffectTestScene.unity` / `BattleEffectTestModule.cs`，菜单 `Tools/战斗/打开特效测试模块`。
- `EffectTimingConfig.cs` 按特效家族保存位置、缩放、帧率、伤害帧、物理帧与受击模式；颜色变体共享配置。
- `BattleEffectPlayer` 暴露原有资源加载与直接显示某帧的接口；销毁时释放自行创建的临时 Sprite/Texture。
- `BattleCharacterPreview.SampleHitReaction` 复用现有 10 种动力学曲线，以固定采样步长和视觉种子回看，恢复全局随机状态。
- `BattleInspectionManager` 在正式播放中分开调度扣血/飘字、物理动作和自身归位后特效。
- `BattleEngine` 保留原有公开无参行动入口；内部可先取得战报，再在伤害表现时点发布一次战报事件。数值公式与判定不变。
- `EffectDatabase` 分离到同名脚本，支持 Unity 持久化资源引用。构建准备检查补齐烘焙数据库。
- 原切图工具使用被导入器缩小的高度，长条原图切帧坐标越界。改为读取 PNG 原始宽高、保留尺寸，并验证切帧数量。

## 验证与交付

特效模块 1511 项检查通过，包含 67 家族 / 495 变体、打包资源引用、前后帧与血条、10 种物理模式、随机流保真、配置持久化以及伤害事件去重。主项目已发布测试场景、67条默认时序配置和495条完整烘焙资源，空帧数组为0。结果以 `combat_numerical_paradigms/progression_difficulty/effect_tuning/validation.json` 和 `scene_integration/lifecycle_validation.json` 为准。

使用说明：`combat_numerical_paradigms/progression_difficulty/EFFECT_TEST_MODULE.md`。

Unity验证在 `.gemini/battle_scene_validation` 独立副本执行，不关闭用户当前编辑器。场景/资源由 `.gemini/publish_effect_tuning.py` 回写主项目；复制纹理元数据前核对 GUID，不覆盖原始 PNG 或技能命名映射。

## 后续修订：统一中心播放

用户要求优先保证所有特效位于阵容中心。移除位置偏移配置和全局高度偏移，测试与正式播放器均直接取对应阵容中心；保留缩放、帧率、伤害和受击时点。操作文档同步更新。
