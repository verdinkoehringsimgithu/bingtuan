# 人物资料与水手/行商正式接入

用户在旅行损耗接入交付后询问“还有啥，继续吧”。本轮选择补齐外部人物标注到Unity运行时的链路，并完整移植两项开局结算羁绊：水手、行商。没有把其余21项研究机制冒充已上线，没有新增地区、奖励、价格或战斗界面。

## 产物

生产项目`D:/123/LegionBattle/LegionBattle`。

- 新增`Assets/Scripts/Battle/CharacterTraits.cs`：人物ID、动作素材GUID、种族、性别、单身份、手工阶位标记；Clone隔离。
- 新增`OpeningBondRules.cs`：默认关闭的水手/行商规则与开局归因报告。人数曲线与系数沿用settings.DEFAULTS候选，开关和参数由调用方显式传入。
- 新增`Assets/Editor/CharacterTraitsImporter.cs`：读标注主文件/.bak最新有效者；启动、导入、建库及构建前同步。多身份/未知词条/动作组冲突拒绝猜测。同步菜单`Tools/战斗/同步人物固有标签`。
- 改动`CharacterSheetData`、`BattleMember`、`CombatMember`与场景输入快照链，传递traits；FromSheetData及场景Clone独立复制。
- `BattleSceneRequest.leftOpeningBonds/rightOpeningBonds`分别启用双方；`BattleSceneResult.leftOpeningBonds/rightOpeningBonds`返回人数、增量和行商目标轴。
- 新增Editor与UNITY_EDITOR探针`IdentityRuntimeValidation`、`IdentityRuntimeProbe`，不加入玩家构建或保存场景。

1229条素材对应1213个人物（8组三动作变体共用人物ID）。派生人物数据库已填入资料。种族/性别仅作为固有资料，没有主动加成；markedTier保留外部标记，不覆盖数值阶位或培养。原有数据库不去重、不移动图片。

## 结算顺序

角色与装备求和→水手→行商→遭遇先机差→有效属性中的旅行比例和临时削弱。水手按成员自身四维平均（不含装备）×不同已填身份×0.006×q(水手数)×g增加各维；行商给最低一维增加最高维×0.30×q(行商数)×g；q=n/(n+4)是既有研究候选。并列最低按C/R/I/M；开局一次、不要求施法。全队顺位由调用方提供，未自动重新排阵。

阶段参考生成器会按外观携带标签，但尚无固定身份NPC模板。已校准固定遭遇默认继续关闭；要开启敌方羁绊，传入身份明确的实际阵容，不把随机外观当成已校准身份模板。

## 调试发现与处理

1. 旧数据库9条首帧Sprite引用失效，不能由当前首帧对象反推GUID。一次迁移通过精确且唯一的源纹理文件名解析实际GUID，并用对应标注ID取资料；存下assetGuid后不再依赖文件名。没有按名字/外观猜测身份，没有修图或修Sprite引用。
2. Unity整库SaveAsset会清除失效引用并补写默认数值字段。初次资产审计发现后，已恢复基线所有非traits字段，改为仅原子写入YAML traits区块再ImportAsset。拒绝隐式保存已有未保存的数据库人工修改。最终移除traits后与修改前数据库逐行完全相同。临时副本测试实际覆盖1229条写入、丢失引用保留和脏数据库保护，副本已删除。
3. 旧研究macro(b,p)把敌方先机恢复到base值，会抹掉水手的开局先机。新对照使用真实joint_core.Team构造器的开局结果作本场初始预算，再跑原生动作管线；正式Unity保留开局加成再施加遭遇theta。旧研究源码与旧测量未改写。

## 最终验证

证据与指南`combat_numerical_paradigms/progression_difficulty/identity_runtime_2026_10_28/`。

- 3698项人物导入/异常/隔离检查：1229素材、1213人物，全部GUID核对。
- 1920场新开局羁绊数值对照：六阶段、四组双方开关和旅行组合；187294次随机取值，最大相对误差4.3972906764897086e-15。固定技能装备输入中的身份为受控机制测试，不宣称真实收集分布。
- 2400场旅行、480场旧核心对照、11项机制不变量全部通过。
- Unity最终71项新接入、135项旅行、73项原有场景/特效时序检查均通过。
- 37,500场基准综合胜率[53.9,56.1,53.9,46.7,41.7,47.7]，极差14.4pp。
- `verify_delivery.py --record`首次冻结并审计通过。标签源JSON、正式场景、特效配置、阵容配置哈希不变；人物数据库仅traits变化。

主文档README.md，生产快照delivered_sources/，签名delivery_manifest.json，结果delivery_checks.json。复测run_numeric_checks.ps1和run_unity_checks.ps1，审计verify_delivery.py。上轮10/27签名仍指其旧快照，当前源文件授权演进后不能要求旧签名与新版本相等；不要改写旧签名。

所有本轮进程正常结束。没有暂停的计算或待清理验证资产。旧诊断database_migration.diff是发现整库序列化问题时的失败证据，不是最终数据库差异。

后续优先分批移植军人/忍者、学者/剑士等事件机制，需要真实检查次数、命中和递归攻击的战报与特效顺序。23项用户设计、复合女仆/果实/冒险目标及六阶段研究已经存档，不从自走棋规则重写，也不重复已有百万级相似扫描。
