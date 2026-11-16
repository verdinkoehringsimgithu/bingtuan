# 学者/剑士正式接入完成，继续推进其余机制

用户在军人/忍者交付后说“继续”，并追加“不要重复确认，一直往前做”。按已确认规则持续实施、分批验证并保存；不用每组询问。当前学者/剑士这一组已全部验收，未最终结束整项任务，下一组已宣布为格斗家、侠女、拜火教、淑女和学生/老师。

## 已完成生产变更

项目`D:/123/LegionBattle/LegionBattle`。

- 新`Assets/Scripts/Battle/CombatSupportBonds.cs`：学者智能次数恢复、剑士递归规则/状态/摘要；两个开关默认false。候选q=n/(n+4)，学者.30q、恢复1次，剑士.50q、衰减.50，最多3次追加（共4技能）。初始概率先封顶再按深度递减，避免高增益使多层都100%。参数显式校验。
- 学者每次攻击（含普攻/未命中）掷概率；排除自己、无限技能、未消耗和回合过期技能，优先当前条件满足且耗尽→当前可用部分消耗→暂时门槛未满足且耗尽→其他部分消耗；组内按原阵容顺位。次数耗尽计入extra_use。只减少uses，不改casts/failed，不即时让队友出手。
- `CombatRuntime.Next`逐个返回完整技能，chainDepth0..3及hasContinuation；候选额外剑士遵守使用次数/动态条件，100%完成已触发追加的选定，不重新按原技能chance阻挡，仍消费一次选择RNG以与原生协议一致。每次施法完整执行装备/恢复/流失等效果。原行动先后手标记沿用，下一段重新采样四维/血量。整组后才给对方，回合效果不在链接之间多结算。
- 清理每次Act的hit/selected/skillSelected，避免上一段命中状态泄漏。净化装备记录每次成功技能额度并在原回合末结算，前面出手者不因最后换人丢效果。
- `BattleSceneRequest.left/rightSupportBonds`进场Clone，`BattleTroop`送入Runtime，`BattleSceneResult`独立Summary。战报新chainDepth/hasContinuation/scholarTarget/scholarRestored。
- `BattleInspectionManager.CoExecuteTroopCombat`一次推进自动完整播放整组；抽取CoPlayTroopAction逐段完整动作/特效/伤害/回血。用每个Cue完成标记作屏障，等待真实延迟回调结束再推进，保留BattleEngine严格pendingReport检查。跳过对隐藏角色槽启动物理协程。
- 中途回调里Leave会停止剩余追加。已触发未执行的接收者不消耗次数、不计实际追加；新场清零。

## 调试与边界

1. 新对照旧研究出现实际胜负分歧，定位为旧Python连锁时heal_channel从吸血粘到下一次“当前战力自愈”，导致误用上限。仅新适配层每次动作重置通道，生产C#本身按每次技能正确取值。没有改旧研究文件/结果。
2. 首次Unity递归时迟到的WaitForSeconds回调落到下一个pendingReport，触发Presentation report is no longer current。已用Damage/Heal/Effect/Physics各自complete标记等待后再推进，153项实机验证通过。没有删严格检查或吞掉异常。

## 证据

目录`combat_numerical_paradigms/progression_difficulty/support_runtime_2026_10_28/`。

- 1920场、36,342次动作对照，核对所有旧字段以及恢复目标/次数/链深度/继续标记/RNG/链中BP；最大相对误差8.586285159580285e-14。
- 40项新不变量；旧54军忍+11原生不变量。
- 旧7200场C#/Python对照全过（2400军忍、1920开局、2400旅行、480旧核心）。
- Unity153新、142军忍、71开局、135旅行、73原场景/特效时序及3698标签检查全过。Probe测试四链种子只用于分支覆盖，不是胜率筛选。
- 37,500场综合胜率[53.8,55.4,54.6,46.7,42.4,47.2]，极差13.0pp。
- 原标签JSON、派生数据库、正式场景、特效/阵容配置SHA未变。
- README、复测ps1、verify_delivery.py、delivered_sources及delivery_manifest/delivery_checks已冻结。所有本组进程已退出，无待续计算。旧失败日志/diagnostic保留，不作为成功证据。

正式已完成6/23：水手、行商、军人、忍者、学者、剑士。剩余17项继续做，不要求用户逐项再次确认。

## 下一组设计落点（尚未实施）

格斗家：全队Output乘1+fighter(.025)×q×gain×(round−1)，影响既有源队Output的流失；每回合开始、maxDoT前同时更新双方当前回合，不在递归间增长。
侠女：实际侠女首次技能（不要求命中）完成后累全局层，后续侠女技能directFactor×1+layers×heroine(.035)×q×gain。
拜火教：高阶教徒技能按低于自身技能tier的教徒人数×cult(.035)×gain加directFactor。
淑女：覆盖前min(rosterCount,max(1,ceil(ladyCount/3)))位置技能，directFactor×1+lady(.25)×q×gain；具体强化沿用研究中的技能增伤候选。
学生/老师：需要CombatMember携带真实level（生产从BattleMember.level复制；纯旧fixture默认30）。老师技能directFactor×1+.0015×学生等级总和×gain。学生经验倍率1+.12×老师数×gain只导出给调用方，不捏造经验或奖励系统。

可新建CombatAmplificationRules/State，保持默认off，DirectFactor按原select的Teacher→Cult→Heroine→Lady顺序逐次乘到已有装备direct，Heal原管线仅增强其基础攻击、不增强恢复量。Heroine首次层在postAction、Ninja/Scholar前处理。所有既有单身份语义继续保留，种族性别不转主动效果。
