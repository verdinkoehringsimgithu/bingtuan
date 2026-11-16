# 人物总览与羁绊标注交付

用户指令：继续完成人物。已实现认可的大窗口人物总览、点击编辑、Ctrl/Shift多选、种族/多身份/职业三栏、首次词条输入记录与点击复用、批量增删、改名/合并、上个人物词条复制、筛选、职业随机/锁定、CSV导出、自动保存与备份。

源码：`D:/123/CharacterTagging.cs`；入口`D:/123/CharaClassifier.cs`。根目录`CharaClassifier.exe`更新并默认进入总览；旧入口保留`--classify`、原修图/统计命令。旧exe备份`.gemini/character_tagging_backup/CharaClassifier_before_tagging.exe`。

主项目1230张人物，原始CHARA1403张，默认主项目图库，选择图库另开窗口，各图库JSON独立，不按同名自动合并。新模式无图片写入或阶级移动；原工具按钮仍指向原始CHARA以避免对Unity素材误执行修图。

数据文件：图库目录`character_bond_labels.json`与`.bak`；版本1包含稳定词条ID、人物ID及路径、种族、身份列表、职业与锁定、最近筛选/选择。Unity人物使用meta GUID，原图库无meta通过持久ID/内容指纹恢复唯一改名。原chara_tags及分类CSV未覆盖。JSON是权威来源，CSV只导出。

验证：`.gemini/CharacterTaggingProbe.cs`独立复制1230真实素材和meta测试，总计1253检查通过，包含全部图片、批量、重启、随机锁定、撤销、失败事务回滚、改名合并、GUID移动、无meta改名、备份恢复、双损坏拒绝覆盖、真实窗口点击切换和滚动。截图已查看，无裁切关键输入；右侧下部可滚动。结果`.gemini/character_tagging_probe/result.json`、`gallery.png`。测试只改隔离副本。

发布二进制哈希与 staging 一致：7FB8AE0DA628037B394F513F8021B19988CEFDC30A57A060F64E5E85EA7E24D9。最后仅把原工具按钮目标调整为原始图库并重新编译；核心与界面验证通过后没有其他改变。

后续：Unity读取标签与学生3/6/9/12具体羁绊效果尚未实现，用户需要先填词条；不预设种族/职业名单。标签改动即原子保存，最多撤销最近50操作仅限当前运行。完整说明`combat_numerical_paradigms/progression_difficulty/CHARACTER_TAGGING_GUIDE.md`。
