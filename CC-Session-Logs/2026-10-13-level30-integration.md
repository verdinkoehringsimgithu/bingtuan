# 30级成长接入与同步审计

用户授权以已确认的成长/难度规范为准，核对关联修改，取消35级并统一30级满级。

已改：Unity成员level与四维起止端点、阵容成长函数、去除100级BP倍增和军阶属性重复注入；30人参考BP为1,000,000。修正多个技能概率相加错误。新六阶段模拟入口复用已验证研究模型；生成器预算说明标明30级并重新编译SkillGenerator.exe。更新当前养成规范与AGENT导航。

验证：完整Unity程序集与生成器编译通过；8,640组C#/Python成长数据一致；0/31/35/100级拒绝；576场六阶段入口检查；768场阶段6确认结果逐流派精确复现。canonical Python物理文件SHA保持不变；历史结果保留。

证据与完整差异：`combat_numerical_paradigms/progression_difficulty/INTEGRATION_2026-10-13.md`。新增脚本：`test_stage_combat_simulator.py`；验证文件integration_validation.json、integration_smoke.json、integration_reproduction.json。

后续明确差异：Unity BattleEngine/BattleStats仍是旧伤害物理，需完整移植V11管线、真实生成器技能参数及装备机制才能复现研究。旧觉醒/心法/经验消耗没有重定标。现有Unity50选30阵容启发式不同于研究主C/保底/填充构建，不把它宣称为研究阵容。不要将等级接入误写为完整Unity战斗同步。

本日志记录操作、证据与剩余事项，不保存内部思维链。
