# 特效与阵型工具落地实施日志

- **时间**：2026-10-14
- **状态**：已完成实施、独立验证通过（27,545项工具检查 + 73项生命周期检查），已安全同步至用户检查项目

## Quick Reference
关键词：炸散距离倍率、模式6、两军间距、ArmyDistance、FormationConfig、自身特效筛选、healFrame、空血回血标尺、CoHealCue、版本5迁移、无损同步。

## 实施内容总结

### 1. 炸散距离工具化
- 在 `EffectTimingProfile` 新增 `scatterDistanceScale`（默认建议值 0.45，合法区间 [0.05, 5.0]）。
- 在 `BattleCharacterPreview.cs` 的受击模式6（中心炸散）中，倍率同时等比缩放径向距离与垂直抬升（`apexPos.y`），避免水平收拢后出现异常高跳，完整保留原方向、时间段与平滑归位。
- 在 `BattleEffectTestModule` 面板中，受击模式为6时提供 `炸散距离倍率` 的浮点数步进与输入调节。
- 正式战斗 `BattleInspectionManager.CoPhysicsCue` 与测试模块 `SampleHitReaction` 贯穿传入该倍率。

### 2. 两军站位间距工具化
- 在 `FormationConfig` 中新增属性 `ArmyDistance`（两军前排原点差），根据两军原点对称更新 `leftOriginX` 与 `rightOriginX`，确保 ApplyFormationLayout 重新布局后两军整体仍居中于相机静止原点。
- 初始推荐值按 80% 间距设定（原点差由约 6.398 缩至 5.118），两军内部 spacingX/spacingY/originY/rowStaggerX 严格保持。
- 扩展 `FormationConfig`：增加基于 `.tmp` 和 `.bak` 的原子保存、双向写入 `Characters` 与 `Resources`、`UserSettings/FormationConfig.autosave.json` 自动写入，以及 `UseValidationDirectory` 隔离支持。
- 在 `BattleEffectTestModule` 提供 `两军间距` 实时调节、自动保存与 Seek 重采样。

### 3. 自身特效回血时点与空血校准预览
- 在 `BattleEffectTestModule` 新增 `仅看对自身特效` 动态筛选开关，依据最新有效 `Profile.playOnCaster` 实时过滤。
- 在 `EffectTimingProfile` 新增 `healFrame`（以特效起点为0的特效帧，支持负数）；在 `BattlePresentationTimeline` 中计算 `healTime = effectStart + HealDelay`，起止边界自适应纳入。
- 预览标尺：当 `Profile.playOnCaster == true` 时，行动方血条从 0 血（空血）开始展示（底层战团 BP 保持不变，防止触发战败），到达 `healTime` 瞬间跳变至满血；往回拖动时间轴立刻恢复为 0 血；重播重新从 0 血开始；交换方向时空血跟随行动方。
- 正式战斗分离表现：在 `BattleInspectionManager` 中拆分出 `CoHealCue`，延迟至 `timeline.healTime` 再触发飘字与 `healthBarUI.ApplyHeal`，防止 `CoDamageCue` 提前将行动方血条置为回血后的最终值。

### 4. 迁移、验证与安全同步
- `EffectTimingDocument` 升级为版本 5；版本 2、3、4 读取时平滑升级，缺省赋予 `scatterDistanceScale=0.45`、`healFrame=0`。
- 独立验证项目 `D:/.gemini/effect_sorting_validation` 执行：
  - 工具测试：27,545 项检查通过（+20项新断言全部通过，涵盖炸散缩放、模式6完整归位、间距居中、自身空血跳变与回退、版本迁移）。
  - 正式生命周期测试：73 项检查全部通过。
- 安全同步：创建预同步备份目录 `battle_scene_validation/UserSettings/SafeBackup_20261014_170711`，逐字段合并用户最新 JSON 配置，保护现有调校不被覆盖；用户 Unity 进程（pid 23284）无缝刷新，无报错。
