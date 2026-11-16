# 人物总览滚动文字修复

用户截图：向下滚动后人物图像在、姓名与资料文字消失。

原因：CharacterGallery.OnPaint使用Graphics.TranslateTransform移动GDI+人物与卡片，而GDI TextRenderer不默认继承该变换，文字仍按原始内容坐标绘制，滚出视口。

修复：移除绘图全局变换，卡片矩形显式加AutoScrollPosition.Y。图片、背景、姓名、状态统一使用视口坐标，点击索引仍按内容坐标换算。

证据：.gemini/CharacterScrollProbe.cs修复前在滚动150像素时稳定报Name missing；修复后在0、150、3157、9000、底部和返回顶部六处检查姓名/状态可见及点击正确，共66检查通过，result.json及滚动截图在.gemini/character_scroll_validation。已查看3157像素滚动截图文字正常。

发布：更新CharacterTagging.cs与CharaClassifier.exe，旧exe和当前用户标签备份.gemini/character_scroll_backup。只改表现坐标，发布前后标签JSON哈希一致；未改用户种族、性别、身份、职业。
