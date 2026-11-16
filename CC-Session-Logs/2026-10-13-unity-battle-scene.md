# Unity战斗场景整合

用户确认正式化范围为Unity项目内部战斗场景，支持外部调用、完整战斗和离开；退出去向由调用方决定。

新增正式场景BattleScene、BattleSceneFlow入口、BattleSceneController、请求/结果/会话模型。Additive载入，复制真实阵容，复用V11数值及现有表现链路；自动/手动战斗、结果、离开按钮；Entered/TurnResolved/Completed/Closed回调。退出不选择其他场景。

预览场景继续用于表现调试。特效代码只增加场景实例绑定接口，名称匹配算法继续由并行工作维护。角色数据库已修复有效脚本引用，30级成长与装备机制继续沿用已测模型。

场景接入规范：combat_numerical_paradigms/progression_difficulty/BATTLE_SCENE_INTEGRATION.md。
Unity场景验证：scene_integration/lifecycle_validation.json，55项检查全部通过，覆盖六阶段、自动/手动、输入隔离、退出与回调、异常清理、调用方导航、直接Play、离开按钮、初始化状态和种子复现。已验证的BattleScene及对应GUID同步至主项目并加入Build Settings；published_scene_manifest.json记录交付文件哈希。

前一阶段独立运行构建仅保留为开发验证记录，当前交付以Unity场景为准。本日志记录操作与证据，不保存内部思维链。
