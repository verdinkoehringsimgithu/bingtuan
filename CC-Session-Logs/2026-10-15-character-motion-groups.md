# 同人物动作归组

用户确认Glenys与Wyvera各三个条目是同人动作，应归为一人。

实现范围：外部人物标注工具。自动匹配相同前缀walk与pose数字成组，必须两类都存在，不凭相似名字合并。主项目8组共24张素材合为8人物，总览1230→1214。walk优先预览，分组名称去动作后缀。

文档版本4兼容1～3，groups存主资源ID及成员ID，主ID优先walk GUID；原全部character记录及PNG/meta保留。动作文件以后改名分组仍由ID维持。旧pose选择映射到主人物。

身份合并并集，种族/性别只有一个有效值时补齐空白；存在不同非空值保留并提示。阶级不同亦提示。在界面选择标记会统一所有成员；查看素材按钮列出各原始记录与冲突。标记更新、复制、撤销、CSV均按人物，CSV附资源路径和待统一字段。Unity数据库/战斗暂无自动去重。

验证：.gemini/CharacterGroupingProbe.cs，16检查覆盖数量、walk预览、旧数据迁移、原始冲突保留、身份并集、成员同步、撤销、改名持久、独立walk不误并、CSV与UI。66滚动/点击回归与20阶级回归通过。截图已看。结果分别在.gemini/character_group_validation、character_scroll_validation/group-scroll.json与character_tier_validation。

发布：根目录exe更新；旧程序和发布前用户JSON在.gemini/character_group_backup。打开工具后按新格式正常保存，原单素材数据备份保留。未改原PNG、meta、技能或数值。
