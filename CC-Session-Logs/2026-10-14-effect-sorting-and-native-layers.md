# 特效阵容排序与原始前后层

## 最新用户口径

特效固定在阵容正中间，不跟随人物受击移动。优先使用统一排序解决遮挡；素材提供前后层时分别适配，后层在角色下方。测试工具允许标记该类特效是否参与阵容排序，并保存。

## 原因与实现

- 原播放器固定sortingOrder=5000，导致特效无条件盖住角色。
- 用户已将中心改为初始BasePosition平均值+0.5身体高度；保留静止锚点，排除空角色。
- 移除按特定家族名自动设置2.5偏移/按前4帧动态抬升的逻辑。默认偏移0，仍保留手动校准字段。
- `BattleEffectSorting` 以有效角色实际排序范围为依据：参与排序放在阵容中间深度，取消标记位于最高角色之上。原始后层总在最低角色下方。定位不受排序影响。
- `EffectTimingProfile.useFormationSorting` 按家族持久化，默认true；配置version2迁移保留时序与缩放。
- 在原始Megapack素材中发现4类28变体的前后层：spellcast_B、spellcast_C、cure、tech_aura。原导入只用合成图，现从原素材复制独立层，不对位图做修改。
- 56张原始层精灵表烘焙到EffectDatabase.frontFrames/backFrames。前后层同步帧率/帧索引/缩放/朝向，以分层素材代替合成图。
- 原始新层导入必须显式设置Texture2D形状，否则新导入器可能无法生成Sprite；固定完整矩形网格，保留透明帧。

## 验证

- 2588项自动检查通过，覆盖67类495变体两种排序模式、28组原始层、固定位置、标记存储和既有时序功能。
- 图形模式再次通过同一检查，并生成 effect_depth.png / effect_top.png / effect_layers.png；已查看，确认前排遮挡行为、最高层差异与前后层显示。
- 正式场景55项生命周期检查通过，退出仍由调用方决定。
- 数据位于 `combat_numerical_paradigms/progression_difficulty/effect_tuning/`，操作说明 `EFFECT_TEST_MODULE.md`。

## 工作区

用户当前打开的是 `.gemini/battle_scene_validation` Unity项目。新的验证改在独立 `.gemini/effect_sorting_validation`，不关闭用户编辑器。通过验证后将已修改的脚本、资源与配置同步主项目及当前打开的测试项目；其他场景与阵容配置不覆盖。重新进入Play以重建播放器节点。
