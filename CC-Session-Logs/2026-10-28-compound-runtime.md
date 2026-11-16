# 23项羁绊完整验收通过，继续混合触发覆盖审计

用户授权一直往前做，本轮连续完成Support/Amplification/Augmentation/Tactical后接完Compound。23项生产实现与全部回归均完成，见各目录冻结验收。用户随后再次“继续”，开始审计混合配置下的实际触发覆盖，不改变已冻结生产规则。

新增CombatCompoundBonds.cs及请求left/rightCompoundBonds，配置/状态/事件/结果副本。最前女仆替换原技能，概率1、忽略现有全部门槛/次数，先替换再应用本人装备，施法时恢复（未命中也生效、受杀手），动作后固定开局四维基数增长，命中减益/技能暴击/附加真伤依人数档解锁。候选支持完整纯真伤和附加真伤预算，默认附加真伤完整预算，但布尔全off。无独立封印状态，后续封印应使用IsMaidLeader免疫。

果实一个共享ready，首攻round+5播种；未成熟每攻-1最低当前回合，本次只加速；成熟下次攻收获，再清空等待重新播种。回复与固定开局均值×低属性优先增量同时，等待放大两者，回复独立技能减疗。

冒险目标默认四血线+暴击+闪避，可配置；全队共享场内首次，严格低于、跨多线同完、恢复不重置，损伤在装备/社畜保命前观测，仅增强后续冒险技能。另观测首次命中/有效恢复/流失/负面/绝对闪避。学者跳过无限女仆长。

数值新3360场/63244次出手通过，最大相对误差2.99760216648792e-15；35新边界通过。旧18720场回归通过，总22080场、238边界通过。Unity新117及旧114/132/132/153/142/71/135/73、3698标签全部通过。37500原基准综合胜率[53.8,55.8,53.8,46.3,43.5,46.8]、极差12.3pp。两批处理已退出，无运行中session。

已解决验证过程中问题：新oracle编译select时必须显式random=ev.g.tape，否则早于旧adapter构建的namespace仍用原random导致保底选人没入带；只改新oracle、旧源冻结。Compound首次事件对最大流失阶段沿native外围标签max_dot记录，固定流失在内层分类而事件phase仍max_dot；只改诊断标签，物理无变。旧ExpeditionRuntimeProbe反射Deal私有方法，由3参数更新5参数（null source、direct phase），原断言不变；因此重新跑全部Unity。

新目录compound_runtime_2026_10_28包含baseline/protected/新oracle/复测脚本/验证harness/README/verify_delivery，verify_delivery.py --record已成功生成delivered_sources、delivery_manifest、delivery_checks。保护资产全部SHA不变。统一接入指南IDENTITY_RUNTIME_INTEGRATION.md已写并签名。所有旧版本签名均保持冻结。

下一步先只读统计compound_cases中的混合profile6实际触发（engineerQueued、scholarRestored、chainDepth、heroineFirst、stolenStats、coinsEarned、maidCast、fruitEvent）。原混合pattern女仆在第3位，保证发动可能让后方身份永远无法实际出手，因此开启全部机制不能等同于覆盖全部交互；根据覆盖审计补充能真实触发的混合顺位测试。该测试为物理一致性/集成覆盖，不冒充最优顺位收益或新增平衡结论。
