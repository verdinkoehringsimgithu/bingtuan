# 人物底部阶级标记

用户要求重新加入1～6阶标记，放在最下面。

完成：右侧固定底部六个按钮，单人/批量、颜色表示全部/部分匹配、自动保存、撤销、自动下一位；卡片、详情、筛选及CSV统一读取标记。身份区继续占剩余高度。

格式版本3兼容1/2，人物rarity字段0沿用目录，1～6覆盖工具中阶级。标记不移动素材及meta、不调用原修图逻辑、不自动写Unity CharacterDatabase数值。旧职业数据仍仅安全保留在历史JSON。

独立副本20检查通过：六阶逐项设置/重启恢复、撤销、非法值、六按钮可见、点击、筛选、素材未移动。截图已查看，证据.gemini/character_tier_validation。源码CharacterTagging.cs及根目录exe已更新，旧程序/用户JSON备份.gemini/character_tier_backup。
