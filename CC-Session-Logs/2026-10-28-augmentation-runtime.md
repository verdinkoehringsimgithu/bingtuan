# 工程师、贤者、盗贼、杀手正式接入完成

用户要求不用重复确认，一直推进。当前已验证15/23项；继续下一组魔法师、猎手、帮派、富翁、社畜，然后女仆、农民、冒险者。

新增CombatAugmentationBonds.cs，候选q=n/(n+4)、gain1，全默认off；请求left/rightAugmentationBonds独立Clone到Runtime，结果独立Summary。

工程师gear基数=显式装备stats+owner_stats实际贡献，开局×.25qg在水手/行商前提交；实际技能发动排队×.035qg，Cleanse后提交，下回合生效。贤者只改原生虚弱/四维削弱/最大/已损/固定流失幅度，系数(1+.25q己g)(1−.25q敌g)，不改时长。盗贼每次攻击后转移min(敌方raw,有效属性×min(1,.015qg))，只改本场stats。杀手命中技能给下一技能min(1,.60qg)减疗，重复取大；选定真实技能时消费，普攻保留，后续未命中也消费，非技能宏恢复/装备免死独立。Heal请求在封顶/溢出盾前缩减，Filter上下文在try/finally内覆盖完整post钩子。

新战报engineerQueued、stolenStats、killerMarked、appliedHealPenalty、healingPrevented；减疗累计属于受到减疗方。原Python当前自愈的阻止统计以maxBP中间量记账，新oracle仅在内存纠正统计为实际currentBP请求，物理不变。冻结研究和旧证据未改。

证据augmentation_runtime_2026_10_28：2880场/53880次出手，最大相对误差1.0635936575909e-13；38定向检查。旧12480场及29+40+54+11边界回归通过。Unity新132、旧132/153/142/71/135/73场景、3698标签通过。37500场胜率[53.4,55.6,54.1,46.8,42.7,47.4]，极差12.9pp。保护资产SHA不变。README/复测脚本/verify_delivery/最终快照及delivery_checks已冻结，所有批处理退出。

下一组按冻结bond_core.py移植：Mage全队实际技能顺序、Hunter折前分量转3回合真流失、Gang替换normal不消费原技能、Rich本场金币减伤、Worker装备免死后一次复起。最后三项以THREE_BOND_DESIGN_GUIDANCE.md及compound_effects/configured_compound_core为准，不能回到早期单一女仆/果实候选。
