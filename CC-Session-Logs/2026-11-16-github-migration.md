# GitHub跨电脑开发迁移

用户要求把相关内容上传至https://github.com/verdinkoehringsimgithu/bingtuan，供回家继续开发。已初始化D:/123为Git仓库，main直接推送，远端原为空；不创建PR。Git使用既有全局提交身份，仓库http/https代理置空；本机Git命令因目录所有者需要`git -c safe.directory=D:/123 ...`，没有改全局safe.directory。

已上传Unity完整Assets/meta、Packages、ProjectSettings、Resources生效配置、人物标签/数据库、外部工具源码与exe、词库、人物与原特效素材、CC日志和研究源码文档。独立地图工具源码/素材HexTerrainStudio_Backup_20261023及unitypackage一并保留。

排除Unity缓存、Python环境、旧独立Release构建、重复人物备份、历史APK/拆包冷库和机器账号文件。不读取unpacked或all_tables_parsed.json。按源码/配置白名单入Git；常见凭据格式扫描3558个文本文件无命中。没有更改游戏规则、人物标注、特效调校或旧研究签名。

大证据132697文件、原5417054259字节，ZIP无损压缩2934884478字节，70个40MiB上限分卷存TransferData。原目录完整保留本机，分卷恢复回原路径。恢复脚本检查分卷/整包/逐文件SHA，重复恢复跳过相同内容，拒绝覆盖本地不同内容；单元检查已覆盖重复运行、精确字节、冲突保留、坏卷拒绝。

旧结果目录与大文件通过紧凑.gitignore忽略，研究133671非环境文件全部可由直接跟踪文件或归档恢复，缺失0。检查tools/migration/verify_repository.py，报告TransferData/repository_verification.json。全部70卷与整包SHA通过，抽样解压82文件/2086648239字节内容SHA通过，报告TransferData/verification.json。tools/migration/check_home.py验证47个已签名生产/文档文件通过；人物、技能工具源码重新编译成功，产物tools/build忽略，不覆盖原exe。

首批12卷大请求HTTP408，未到远端；仅拆分本次未发布提交，源码提交保留，不强推。随后每卷一个提交，40卷时一次网络408，从41卷继续，70卷全部成功。上传脚本含每次3次重试与StartPart恢复。数据完成提交ca3b8ad95b3612aa98baae82f7991255dc3d7393，已用ls-remote核对一致；最后迁移文档/校验报告另一个小提交。

回家入口HOME_DEVELOPMENT.md，推荐D:\123克隆，因为旧技能词库/特效同步/测试脚本部分路径固定。UnityHub添加D:\123\LegionBattle\LegionBattle，版本2022.3.62f3c1。Python3.11运行tools/migration/restore_research.py再check_home.py；普通Git，不需LFS。建议20GB加Unity缓存空间。旧ps1的Codex Python路径在家替换成本地venv；tools/requirements-home.txt提供环境依赖，tools/build_tools.ps1可编译外部工具。源码迁移保留原字节，未批量改绝对路径使旧证据失效。
