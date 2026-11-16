# 人物性别标记

用户要求性别固定男/女/无/双，说明种族、性别是非主动的固有资料，用作某些效果目标筛选条件。

完成：CharacterTagging.cs新增gender字段、固定按钮、单人/批量设置、清除、混合选择着色、人数统计、性别/未标记筛选、概览/详情显示、复制上一人物、CSV导出及自动保存/撤销。清除或旧资料是未标记，与“无”分开。版本2读取版本1，保留现有种族/身份/职业，不按外观推测性别。

固有资料供后续效果读取，不自动激活人数羁绊；当前没有接入战斗目标选择。文档与AGENT已更新。

独立1230人副本测试1265项通过：覆盖四值持久化、版本迁移、已有资料保留、非法值拒绝、批量撤销、性别筛选与CSV，以及原有全部回归。证据.gemini/character_tagging_probe/result.json和gallery.png；截图已检查。

CharaClassifier.exe已更新，SHA256 8BE1A11D053DEF2E6E0F035FF5B6F74D49E3E6E0534305846BF6D9CDEC7F1691，旧exe备份.gemini/character_gender_backup/CharaClassifier_before_gender.exe。测试未改用户人物标注资料；打开正式工具后正常保存会迁移到版本2并保留.bak。
