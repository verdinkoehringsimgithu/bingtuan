# 人物侧栏布局调整

用户明确不再需要职业，身份过多导致窄小词条区反复翻动。

完成：职业编辑、随机、锁定、筛选、详情、复制与CSV列移除；停止新增职业词条。旧JSON职业字段只为安全保留历史记录，界面和当前业务不再使用，不批量删除用户旧资料。

右栏从340加宽420，资料与人物预览并排；改用TableLayoutPanel，身份词条独占剩余百分比高度，随窗口扩大。种族/性别紧凑固定区，身份搜索沿用输入框。外层无需滚动；身份本身超多时仍可滚动，避免裁切。

验证：独立副本叠加36个测试身份，11项布局/点击/导出/保存检查通过，检查大窗口与最小窗口、随高度扩展、无职业控件或CSV列。截图已检查。滚动文字与点击回归66检查通过。证据.gemini/character_layout_validation与character_scroll_validation/layout-scroll.json。

发布：CharaClassifier.exe更新；旧exe及用户JSON备份.gemini/character_layout_backup。发布前后人物JSON哈希一致，无用户标签被覆盖。当前文档与AGENT已按最新需求更新，旧会话日志仅为历史。
