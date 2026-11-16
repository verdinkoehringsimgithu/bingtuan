using System;
using System.Collections.Generic;
using System.Data;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

namespace LegionBattle.Generator
{
    public class SkillGeneratorForm : Form
    {
        // ─── 配表数据核心 ───
        private DataTable _skillTable;
        private string[] _csvHeaderLine1; // 中文表头
        private string[] _csvHeaderLine2; // 字段类型
        private string[] _csvHeaderLine3; // 英文字段名
        private string _currentFilePath = "";
        private bool _isDirty = false;

        // 默认技能配表路径
        private const string DefaultCsvPath = @"D:\123\unpacked\res\data\active_skill.csv";

        // ─── UI 控件 (Tab 1: 配表工作台) ───
        private TabControl tabControlMain;
        private TabPage tabEditor;
        private TabPage tabAffixes;
        private TabPage tabConsole;

        private DataGridView gridSkills;
        private TextBox txtSearch;
        private Label lblStats;
        private Label lblStatusFeedback;
        private TextBox txtRowDetail;
        private ComboBox cbTableRarity;
        private EffectAnimationPreviewControl _editorEffectPreview;

        // ─── UI 控件 (Tab 2: 前后字段设置) ───
        private ComboBox cbAffixCategory;
        private ComboBox cbConnectMode;
        private TextBox txtPrefixes;
        private TextBox txtSuffixes;
        private Label lblPrefixCount;
        private Label lblSuffixCount;
        private TextBox txtTestOutput;
        private int _currentCategoryIndex = 0;
        private EffectAnimationPreviewControl _affixEffectPreview;

        // ─── UI 控件 (Tab 3: 单抽与数值分析) ───
        private ComboBox cbConsoleRarity;
        private Button btnGenerateConsole;
        private Button btnBatchConsole;
        private TextBox txtConsoleSummary;
        private TextBox txtConsoleDetails;
        private ListBox lstConsoleSkills;
        private EffectAnimationPreviewControl _consoleEffectPreview;
        private List<SkillRecord> _lastConsoleRecords = new List<SkillRecord>();

        public SkillGeneratorForm()
        {
            this.Text = "战团技能配表工作台 & 数值生成器 (v2.6 - 含像素特效实时动画预览)";
            this.Size = new Size(1380, 880);
            this.MinimumSize = new Size(1024, 650);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.Font = new Font("Microsoft YaHei", 9F, FontStyle.Regular, GraphicsUnit.Point, ((byte)(134)));

            // 初始化词缀配置
            AffixManager.Init();

            InitializeComponents();

            // 自动加载默认 active_skill.csv
            if (File.Exists(DefaultCsvPath))
            {
                LoadCsv(DefaultCsvPath);
            }
            else
            {
                InitEmptyTable();
            }
        }

        private void InitializeComponents()
        {
            tabControlMain = new TabControl();
            tabControlMain.Dock = DockStyle.Fill;
            tabControlMain.Font = new Font("Microsoft YaHei", 9.5F, FontStyle.Regular);

            // ========================================================
            // Tab 1: 技能配表工作台 (DataTable Editor)
            // ========================================================
            tabEditor = new TabPage("【技能配表工作台 (导表/编辑/新增)】");
            tabEditor.Padding = new Padding(6);

            // 顶部操作工具栏
            Panel pnlTopBar = new Panel();
            pnlTopBar.Dock = DockStyle.Top;
            pnlTopBar.Height = 84;
            pnlTopBar.BackColor = Color.FromArgb(245, 247, 250);
            pnlTopBar.BorderStyle = BorderStyle.FixedSingle;

            // 第一行：文件操作与新增操作按钮
            Panel pnlButtons = new Panel();
            pnlButtons.Dock = DockStyle.Top;
            pnlButtons.Height = 44;
            pnlButtons.Padding = new Padding(8, 6, 8, 4);

            Button btnLoadDefault = new Button();
            btnLoadDefault.Text = "载入原表 (active_skill.csv)";
            btnLoadDefault.Location = new Point(8, 7);
            btnLoadDefault.Size = new Size(170, 30);
            btnLoadDefault.BackColor = Color.FromArgb(235, 243, 255);
            btnLoadDefault.Click += (s, e) => LoadCsv(DefaultCsvPath);

            Button btnOpenCsv = new Button();
            btnOpenCsv.Text = "打开外部 CSV...";
            btnOpenCsv.Location = new Point(184, 7);
            btnOpenCsv.Size = new Size(115, 30);
            btnOpenCsv.Click += (s, e) => OpenExternalCsv();

            Button btnSaveDefault = new Button();
            btnSaveDefault.Text = "保存覆盖原表 (带.bak备份)";
            btnSaveDefault.Location = new Point(305, 7);
            btnSaveDefault.Size = new Size(170, 30);
            btnSaveDefault.BackColor = Color.FromArgb(220, 245, 225);
            btnSaveDefault.Font = new Font("Microsoft YaHei", 9F, FontStyle.Bold);
            btnSaveDefault.Click += (s, e) => SaveCsv(DefaultCsvPath);

            Button btnSaveAs = new Button();
            btnSaveAs.Text = "另存为新表...";
            btnSaveAs.Location = new Point(481, 7);
            btnSaveAs.Size = new Size(100, 30);
            btnSaveAs.Click += (s, e) => SaveAsCsv();

            Label lblSep1 = new Label();
            lblSep1.Text = "|";
            lblSep1.ForeColor = Color.DarkGray;
            lblSep1.Location = new Point(587, 12);
            lblSep1.AutoSize = true;

            Label lblRarity = new Label();
            lblRarity.Text = "生成阶位:";
            lblRarity.Location = new Point(602, 13);
            lblRarity.AutoSize = true;

            cbTableRarity = new ComboBox();
            cbTableRarity.DropDownStyle = ComboBoxStyle.DropDownList;
            cbTableRarity.Items.AddRange(new object[] {
                "全部随机 (T1 ~ T6)",
                "T1",
                "T2",
                "T3",
                "T4",
                "T5",
                "T6"
            });
            cbTableRarity.SelectedIndex = 0;
            cbTableRarity.Location = new Point(668, 9);
            cbTableRarity.Width = 135;

            Button btnAddGenerated = new Button();
            btnAddGenerated.Text = "+ 随机生成并新增";
            btnAddGenerated.Location = new Point(810, 7);
            btnAddGenerated.Size = new Size(130, 30);
            btnAddGenerated.BackColor = Color.FromArgb(255, 243, 205);
            btnAddGenerated.Font = new Font("Microsoft YaHei", 9F, FontStyle.Bold);
            btnAddGenerated.Click += (s, e) => AddGeneratedSkill(1);

            Button btnAddBatch = new Button();
            btnAddBatch.Text = "+ 批量生成 10 个";
            btnAddBatch.Location = new Point(946, 7);
            btnAddBatch.Size = new Size(115, 30);
            btnAddBatch.Click += (s, e) => AddGeneratedSkill(10);

            Button btnAddEmpty = new Button();
            btnAddEmpty.Text = "+ 新建空白行";
            btnAddEmpty.Location = new Point(1067, 7);
            btnAddEmpty.Size = new Size(95, 30);
            btnAddEmpty.Click += (s, e) => AddEmptySkill();

            Button btnCloneRow = new Button();
            btnCloneRow.Text = "克隆选中行";
            btnCloneRow.Location = new Point(1168, 7);
            btnCloneRow.Size = new Size(85, 30);
            btnCloneRow.Click += (s, e) => CloneSelectedSkill();

            Button btnDeleteRow = new Button();
            btnDeleteRow.Text = "删除选中行";
            btnDeleteRow.Location = new Point(1259, 7);
            btnDeleteRow.Size = new Size(85, 30);
            btnDeleteRow.BackColor = Color.FromArgb(255, 235, 235);
            btnDeleteRow.Click += (s, e) => DeleteSelectedSkill();

            pnlButtons.Controls.Add(btnLoadDefault);
            pnlButtons.Controls.Add(btnOpenCsv);
            pnlButtons.Controls.Add(btnSaveDefault);
            pnlButtons.Controls.Add(btnSaveAs);
            pnlButtons.Controls.Add(lblSep1);
            pnlButtons.Controls.Add(lblRarity);
            pnlButtons.Controls.Add(cbTableRarity);
            pnlButtons.Controls.Add(btnAddGenerated);
            pnlButtons.Controls.Add(btnAddBatch);
            pnlButtons.Controls.Add(btnAddEmpty);
            pnlButtons.Controls.Add(btnCloneRow);
            pnlButtons.Controls.Add(btnDeleteRow);

            // 第二行：搜索筛选与状态条
            Panel pnlSearch = new Panel();
            pnlSearch.Dock = DockStyle.Bottom;
            pnlSearch.Height = 38;
            pnlSearch.Padding = new Padding(8, 4, 8, 4);

            Label lblSearch = new Label();
            lblSearch.Text = "快速查找/筛选:";
            lblSearch.Location = new Point(8, 10);
            lblSearch.AutoSize = true;

            txtSearch = new TextBox();
            txtSearch.Location = new Point(100, 7);
            txtSearch.Width = 240;
            txtSearch.TextChanged += (s, e) => ApplySearchFilter();

            Button btnClearSearch = new Button();
            btnClearSearch.Text = "清空筛选";
            btnClearSearch.Location = new Point(346, 6);
            btnClearSearch.Size = new Size(75, 26);
            btnClearSearch.Click += (s, e) => { txtSearch.Clear(); ApplySearchFilter(); };

            lblStats = new Label();
            lblStats.Text = "总行数: 0 | 筛选: 0 | 路径: 未加载";
            lblStats.Location = new Point(435, 10);
            lblStats.AutoSize = true;
            lblStats.ForeColor = Color.FromArgb(60, 60, 60);

            lblStatusFeedback = new Label();
            lblStatusFeedback.Text = "就绪";
            lblStatusFeedback.Location = new Point(730, 10);
            lblStatusFeedback.AutoSize = true;
            lblStatusFeedback.Font = new Font("Microsoft YaHei", 9F, FontStyle.Bold);
            lblStatusFeedback.ForeColor = Color.DarkGreen;

            Button btnApplyRowEffect = new Button();
            btnApplyRowEffect.Text = "⚡ 写入当前行适配特效ID";
            btnApplyRowEffect.Location = new Point(980, 5);
            btnApplyRowEffect.Size = new Size(165, 27);
            btnApplyRowEffect.BackColor = Color.FromArgb(230, 244, 255);
            btnApplyRowEffect.Click += (s, e) => ApplyMatchedEffectToSelectedRow();

            Button btnBatchApplyEffects = new Button();
            btnBatchApplyEffects.Text = "🎨 全表智能刷新特效ID";
            btnBatchApplyEffects.Location = new Point(1152, 5);
            btnBatchApplyEffects.Size = new Size(165, 27);
            btnBatchApplyEffects.BackColor = Color.FromArgb(255, 240, 220);
            btnBatchApplyEffects.Click += (s, e) => BatchApplyMatchedEffectsToAllRows();

            pnlSearch.Controls.Add(lblSearch);
            pnlSearch.Controls.Add(txtSearch);
            pnlSearch.Controls.Add(btnClearSearch);
            pnlSearch.Controls.Add(lblStats);
            pnlSearch.Controls.Add(lblStatusFeedback);
            pnlSearch.Controls.Add(btnApplyRowEffect);
            pnlSearch.Controls.Add(btnBatchApplyEffects);

            pnlTopBar.Controls.Add(pnlButtons);
            pnlTopBar.Controls.Add(pnlSearch);

            // 中间分割面板：上方 DataGridView，下方详细规则解读 + 右侧特效预览
            SplitContainer splitEditor = new SplitContainer();
            splitEditor.Dock = DockStyle.Fill;
            splitEditor.Orientation = Orientation.Horizontal;
            splitEditor.SplitterDistance = 460;
            splitEditor.SplitterWidth = 6;

            // 表格主视图
            gridSkills = new DataGridView();
            gridSkills.Dock = DockStyle.Fill;
            gridSkills.BackgroundColor = Color.White;
            gridSkills.BorderStyle = BorderStyle.None;
            gridSkills.AllowUserToAddRows = false;
            gridSkills.AllowUserToDeleteRows = false;
            gridSkills.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
            gridSkills.MultiSelect = false;
            gridSkills.EditMode = DataGridViewEditMode.EditOnKeystrokeOrF2;
            gridSkills.RowHeadersWidth = 50;
            gridSkills.AlternatingRowsDefaultCellStyle.BackColor = Color.FromArgb(249, 251, 253);
            EnableDoubleBuffer(gridSkills);

            gridSkills.SelectionChanged += (s, e) => OnGridSelectionChanged();
            gridSkills.CellValueChanged += (s, e) => OnGridCellValueChanged();

            // 下方详情框 (左侧规则文本 + 右侧实时像素特效预览)
            GroupBox grpDetail = new GroupBox();
            grpDetail.Text = "【选中技能实时规则与四维数值分析 + 绑定像素特效实时预览】(可直接在上方表格双击编辑)";
            grpDetail.Dock = DockStyle.Fill;
            grpDetail.Padding = new Padding(8);

            _editorEffectPreview = new EffectAnimationPreviewControl();
            _editorEffectPreview.Dock = DockStyle.Right;
            _editorEffectPreview.Width = 430;

            txtRowDetail = new TextBox();
            txtRowDetail.Multiline = true;
            txtRowDetail.ReadOnly = true;
            txtRowDetail.Dock = DockStyle.Fill;
            txtRowDetail.ScrollBars = ScrollBars.Vertical;
            txtRowDetail.BackColor = Color.FromArgb(250, 252, 255);
            txtRowDetail.Font = new Font("Consolas", 9.5F, FontStyle.Regular);
            grpDetail.Controls.Add(txtRowDetail);
            grpDetail.Controls.Add(_editorEffectPreview);

            splitEditor.Panel1.Controls.Add(gridSkills);
            splitEditor.Panel2.Controls.Add(grpDetail);

            tabEditor.Controls.Add(splitEditor);
            tabEditor.Controls.Add(pnlTopBar);

            // ========================================================
            // Tab 2: 前后字段与随机组合设置 (Affix Configuration)
            // ========================================================
            tabAffixes = new TabPage("【前后字段与随机组合设置 (自定义词库)】");
            tabAffixes.Padding = new Padding(10);

            Panel pnlAffixTop = new Panel();
            pnlAffixTop.Dock = DockStyle.Top;
            pnlAffixTop.Height = 50;
            pnlAffixTop.BackColor = Color.FromArgb(246, 248, 250);
            pnlAffixTop.BorderStyle = BorderStyle.FixedSingle;

            Label lblAffixCat = new Label();
            lblAffixCat.Text = "当前编辑分类:";
            lblAffixCat.Location = new Point(14, 15);
            lblAffixCat.AutoSize = true;

            cbAffixCategory = new ComboBox();
            cbAffixCategory.DropDownStyle = ComboBoxStyle.DropDownList;
            cbAffixCategory.Items.AddRange(new object[] {
                "通用词库 (所有流派共享备用)",
                "勇气词库 (特征一：勇气·暴击)",
                "先机词库 (特征二：先机·必中·抢攻)",
                "坚韧词库 (特征三：坚韧·生命·恢复)",
                "魔力词库 (特征四：魔力·穿透·流失)"
            });
            cbAffixCategory.SelectedIndex = 0;
            cbAffixCategory.Location = new Point(108, 12);
            cbAffixCategory.Width = 270;
            cbAffixCategory.SelectedIndexChanged += (s, e) => OnAffixCategoryChanged();

            Label lblConnect = new Label();
            lblConnect.Text = "拼接方式:";
            lblConnect.Location = new Point(390, 15);
            lblConnect.AutoSize = true;

            cbConnectMode = new ComboBox();
            cbConnectMode.DropDownStyle = ComboBoxStyle.DropDownList;
            cbConnectMode.Items.AddRange(new object[] {
                "智能混合 (AB之C / ABCD 动宾与偏正)",
                "纯直接拼接 (如: 崩山猛击, 锁喉截杀)",
                "纯“之”字连接 (如: 毁灭之锤, 穿心之刺)"
            });
            cbConnectMode.SelectedIndex = AffixManager.ConnectMode;
            cbConnectMode.Location = new Point(455, 12);
            cbConnectMode.Width = 260;
            cbConnectMode.SelectedIndexChanged += (s, e) => {
                AffixManager.ConnectMode = cbConnectMode.SelectedIndex;
                AffixManager.SaveToFile();
            };

            Button btnSaveAffix = new Button();
            btnSaveAffix.Text = "💾 保存前后字段配置";
            btnSaveAffix.Location = new Point(725, 9);
            btnSaveAffix.Size = new Size(150, 30);
            btnSaveAffix.BackColor = Color.FromArgb(225, 245, 225);
            btnSaveAffix.Font = new Font("Microsoft YaHei", 9F, FontStyle.Bold);
            btnSaveAffix.Click += (s, e) => SaveCurrentAffixEdits();

            Button btnImportExcel = new Button();
            btnImportExcel.Text = "📥 从 Excel 同步词库";
            btnImportExcel.Location = new Point(885, 9);
            btnImportExcel.Size = new Size(150, 30);
            btnImportExcel.BackColor = Color.FromArgb(230, 240, 255);
            btnImportExcel.Font = new Font("Microsoft YaHei", 9F, FontStyle.Bold);
            btnImportExcel.Click += (s, e) => ImportFromExcel();

            Button btnResetAffix = new Button();
            btnResetAffix.Text = "↺ 恢复默认词库";
            btnResetAffix.Location = new Point(1045, 9);
            btnResetAffix.Size = new Size(120, 30);
            btnResetAffix.Click += (s, e) => ResetAffixDefaults();

            pnlAffixTop.Controls.Add(lblAffixCat);
            pnlAffixTop.Controls.Add(cbAffixCategory);
            pnlAffixTop.Controls.Add(lblConnect);
            pnlAffixTop.Controls.Add(cbConnectMode);
            pnlAffixTop.Controls.Add(btnSaveAffix);
            pnlAffixTop.Controls.Add(btnImportExcel);
            pnlAffixTop.Controls.Add(btnResetAffix);

            // 中间左右分栏编辑器
            SplitContainer splitAffix = new SplitContainer();
            splitAffix.Dock = DockStyle.Fill;
            splitAffix.Orientation = Orientation.Vertical;
            splitAffix.SplitterDistance = 640;
            splitAffix.SplitterWidth = 8;

            // 左侧：前字段
            GroupBox grpPrefix = new GroupBox();
            grpPrefix.Text = "【前字段列表 (前缀 / 修饰词 / 意象)】- 每行输入一个词，回车换行";
            grpPrefix.Dock = DockStyle.Fill;
            grpPrefix.Padding = new Padding(10);

            txtPrefixes = new TextBox();
            txtPrefixes.Multiline = true;
            txtPrefixes.ScrollBars = ScrollBars.Vertical;
            txtPrefixes.Dock = DockStyle.Fill;
            txtPrefixes.Font = new Font("Consolas", 10.5F, FontStyle.Regular);
            txtPrefixes.TextChanged += (s, e) => UpdateAffixCounts();

            lblPrefixCount = new Label();
            lblPrefixCount.Dock = DockStyle.Bottom;
            lblPrefixCount.Height = 26;
            lblPrefixCount.Text = "当前前字段: 0 个";
            lblPrefixCount.ForeColor = Color.DarkSlateGray;

            grpPrefix.Controls.Add(txtPrefixes);
            grpPrefix.Controls.Add(lblPrefixCount);

            // 右侧：后字段
            GroupBox grpSuffix = new GroupBox();
            grpSuffix.Text = "【后字段列表 (后缀 / 动作 / 战技 / 名词)】- 每行输入一个词，回车换行";
            grpSuffix.Dock = DockStyle.Fill;
            grpSuffix.Padding = new Padding(10);

            txtSuffixes = new TextBox();
            txtSuffixes.Multiline = true;
            txtSuffixes.ScrollBars = ScrollBars.Vertical;
            txtSuffixes.Dock = DockStyle.Fill;
            txtSuffixes.Font = new Font("Consolas", 10.5F, FontStyle.Regular);
            txtSuffixes.TextChanged += (s, e) => UpdateAffixCounts();

            lblSuffixCount = new Label();
            lblSuffixCount.Dock = DockStyle.Bottom;
            lblSuffixCount.Height = 26;
            lblSuffixCount.Text = "当前后字段: 0 个";
            lblSuffixCount.ForeColor = Color.DarkSlateGray;

            grpSuffix.Controls.Add(txtSuffixes);
            grpSuffix.Controls.Add(lblSuffixCount);

            splitAffix.Panel1.Controls.Add(grpPrefix);
            splitAffix.Panel2.Controls.Add(grpSuffix);

            // 底部：随机组合即时测试控制台 + 右侧像素特效预览
            Panel pnlAffixBottom = new Panel();
            pnlAffixBottom.Dock = DockStyle.Bottom;
            pnlAffixBottom.Height = 225;
            pnlAffixBottom.Padding = new Padding(0, 8, 0, 0);

            GroupBox grpTest = new GroupBox();
            grpTest.Text = "【随机组合即时测试与特效适配预览 (点击任意一行名字即可在右侧播放其适配特效)】";
            grpTest.Dock = DockStyle.Fill;
            grpTest.Padding = new Padding(8);

            _affixEffectPreview = new EffectAnimationPreviewControl();
            _affixEffectPreview.Dock = DockStyle.Right;
            _affixEffectPreview.Width = 420;

            Button btnTestMix = new Button();
            btnTestMix.Text = "🎲 立即随机组合测试 (生成 10 个名字并自动匹配像素特效)";
            btnTestMix.Dock = DockStyle.Top;
            btnTestMix.Height = 32;
            btnTestMix.BackColor = Color.FromArgb(255, 240, 200);
            btnTestMix.Font = new Font("Microsoft YaHei", 9.5F, FontStyle.Bold);
            btnTestMix.Click += (s, e) => RunAffixRandomTest();

            txtTestOutput = new TextBox();
            txtTestOutput.Multiline = true;
            txtTestOutput.ReadOnly = true;
            txtTestOutput.Dock = DockStyle.Fill;
            txtTestOutput.ScrollBars = ScrollBars.Vertical;
            txtTestOutput.BackColor = Color.White;
            txtTestOutput.Font = new Font("Consolas", 10F, FontStyle.Regular);
            txtTestOutput.MouseUp += (s, e) => OnAffixTestOutputClicked();
            txtTestOutput.KeyUp += (s, e) => OnAffixTestOutputClicked();

            grpTest.Controls.Add(txtTestOutput);
            grpTest.Controls.Add(btnTestMix);
            grpTest.Controls.Add(_affixEffectPreview);
            pnlAffixBottom.Controls.Add(grpTest);

            tabAffixes.Controls.Add(splitAffix);
            tabAffixes.Controls.Add(pnlAffixBottom);
            tabAffixes.Controls.Add(pnlAffixTop);

            // 加载当前词库分类内容并初始化一次预览
            LoadAffixCategoryToView(0);
            RunAffixRandomTest();

            // ========================================================
            // Tab 3: AI 单抽与数值分析 (Console & Analysis)
            // ========================================================
            tabConsole = new TabPage("【AI 单抽与数值预算分析 (Console)】");
            tabConsole.Padding = new Padding(6);

            Panel topPanelConsole = new Panel();
            topPanelConsole.Dock = DockStyle.Top;
            topPanelConsole.Height = 50;
            topPanelConsole.Padding = new Padding(12, 10, 12, 10);

            Label lblConsoleRarity = new Label();
            lblConsoleRarity.Text = "角色稀有度:";
            lblConsoleRarity.AutoSize = true;
            lblConsoleRarity.Location = new Point(14, 15);

            cbConsoleRarity = new ComboBox();
            cbConsoleRarity.DropDownStyle = ComboBoxStyle.DropDownList;
            cbConsoleRarity.Items.AddRange(new object[] {
                "全部随机 (T1 ~ T6)",
                "T1",
                "T2",
                "T3",
                "T4",
                "T5",
                "T6"
            });
            cbConsoleRarity.SelectedIndex = 0;
            cbConsoleRarity.Location = new Point(95, 12);
            cbConsoleRarity.Width = 140;

            btnGenerateConsole = new Button();
            btnGenerateConsole.Text = "随机生成单抽";
            btnGenerateConsole.Location = new Point(250, 10);
            btnGenerateConsole.Size = new Size(110, 28);
            btnGenerateConsole.Click += (s, e) => GenerateConsoleSingle();

            btnBatchConsole = new Button();
            btnBatchConsole.Text = "批量测试 10 个";
            btnBatchConsole.Location = new Point(370, 10);
            btnBatchConsole.Size = new Size(110, 28);
            btnBatchConsole.Click += (s, e) => GenerateConsoleBatch();

            Button btnClearConsole = new Button();
            btnClearConsole.Text = "清空结果";
            btnClearConsole.Location = new Point(490, 10);
            btnClearConsole.Size = new Size(80, 28);
            btnClearConsole.Click += (s, e) => {
                txtConsoleSummary.Clear();
                txtConsoleDetails.Clear();
                lstConsoleSkills.Items.Clear();
                _lastConsoleRecords.Clear();
            };

            Label lblConsoleTip = new Label();
            lblConsoleTip.Text = "💡 提示：右侧已集成高清像素特效实时动画预览器，单抽或10连后可点击右侧列表或文本直接切换预览！";
            lblConsoleTip.AutoSize = true;
            lblConsoleTip.ForeColor = Color.FromArgb(40, 100, 160);
            lblConsoleTip.Location = new Point(585, 15);

            topPanelConsole.Controls.Add(lblConsoleRarity);
            topPanelConsole.Controls.Add(cbConsoleRarity);
            topPanelConsole.Controls.Add(btnGenerateConsole);
            topPanelConsole.Controls.Add(btnBatchConsole);
            topPanelConsole.Controls.Add(btnClearConsole);
            topPanelConsole.Controls.Add(lblConsoleTip);

            // 右侧：绑定像素特效实时预览面板
            GroupBox grpConsolePreview = new GroupBox();
            grpConsolePreview.Text = "【绑定像素特效实时预览 (15 FPS 逐帧播放)】";
            grpConsolePreview.Dock = DockStyle.Right;
            grpConsolePreview.Width = 460;
            grpConsolePreview.Padding = new Padding(8);

            Panel pnlConsoleBatchList = new Panel();
            pnlConsoleBatchList.Dock = DockStyle.Top;
            pnlConsoleBatchList.Height = 152;
            pnlConsoleBatchList.Padding = new Padding(0, 0, 0, 6);

            Label lblBatchSelector = new Label();
            lblBatchSelector.Text = "▼ 当前生成技能与绑定特效列表 (点击切换预览):";
            lblBatchSelector.Dock = DockStyle.Top;
            lblBatchSelector.Height = 22;
            lblBatchSelector.ForeColor = Color.FromArgb(50, 60, 80);
            lblBatchSelector.Font = new Font("Microsoft YaHei", 9F, FontStyle.Bold);

            lstConsoleSkills = new ListBox();
            lstConsoleSkills.Dock = DockStyle.Fill;
            lstConsoleSkills.Font = new Font("Consolas", 9.5F, FontStyle.Regular);
            lstConsoleSkills.BackColor = Color.FromArgb(250, 252, 255);
            lstConsoleSkills.SelectedIndexChanged += (s, e) => OnConsoleSkillListSelected();

            pnlConsoleBatchList.Controls.Add(lstConsoleSkills);
            pnlConsoleBatchList.Controls.Add(lblBatchSelector);

            _consoleEffectPreview = new EffectAnimationPreviewControl();
            _consoleEffectPreview.Dock = DockStyle.Fill;

            grpConsolePreview.Controls.Add(_consoleEffectPreview);
            grpConsolePreview.Controls.Add(pnlConsoleBatchList);

            GroupBox grpSummary = new GroupBox();
            grpSummary.Text = "【生成结果概览】";
            grpSummary.Dock = DockStyle.Top;
            grpSummary.Height = 175;
            grpSummary.Padding = new Padding(10);

            txtConsoleSummary = new TextBox();
            txtConsoleSummary.Multiline = true;
            txtConsoleSummary.ReadOnly = true;
            txtConsoleSummary.Dock = DockStyle.Fill;
            txtConsoleSummary.ScrollBars = ScrollBars.Vertical;
            txtConsoleSummary.BackColor = Color.White;
            txtConsoleSummary.Font = new Font("Microsoft YaHei", 9.5F, FontStyle.Regular);
            txtConsoleSummary.MouseUp += (s, e) => OnConsoleTextClicked(txtConsoleSummary);
            txtConsoleSummary.KeyUp += (s, e) => OnConsoleTextClicked(txtConsoleSummary);
            grpSummary.Controls.Add(txtConsoleSummary);

            GroupBox grpDetails = new GroupBox();
            grpDetails.Text = "【随机字段详情与区间分析】";
            grpDetails.Dock = DockStyle.Fill;
            grpDetails.Padding = new Padding(10);

            txtConsoleDetails = new TextBox();
            txtConsoleDetails.Multiline = true;
            txtConsoleDetails.ReadOnly = true;
            txtConsoleDetails.Dock = DockStyle.Fill;
            txtConsoleDetails.ScrollBars = ScrollBars.Both;
            txtConsoleDetails.BackColor = Color.FromArgb(248, 249, 250);
            txtConsoleDetails.Font = new Font("Consolas", 9F, FontStyle.Regular);
            txtConsoleDetails.MouseUp += (s, e) => OnConsoleTextClicked(txtConsoleDetails);
            txtConsoleDetails.KeyUp += (s, e) => OnConsoleTextClicked(txtConsoleDetails);
            grpDetails.Controls.Add(txtConsoleDetails);

            tabConsole.Controls.Add(grpDetails);
            tabConsole.Controls.Add(grpSummary);
            tabConsole.Controls.Add(grpConsolePreview);
            tabConsole.Controls.Add(topPanelConsole);

            // 添加 Tab 页并设置主界面
            tabControlMain.TabPages.Add(tabEditor);
            tabControlMain.TabPages.Add(tabAffixes);
            tabControlMain.TabPages.Add(tabConsole);
            this.Controls.Add(tabControlMain);

            // Tab 3 初始生成一次演示
            GenerateConsoleSingle();
        }

        #region 配表加载、保存与导出逻辑 (CSV RFC4180)

        private void InitEmptyTable()
        {
            _csvHeaderLine1 = (string[])DefaultChineseHeaders.Clone();
            _csvHeaderLine2 = (string[])DefaultTypeHeaders.Clone();
            _csvHeaderLine3 = (string[])DefaultColumnNames.Clone();

            _skillTable = new DataTable("ActiveSkills");
            for (int i = 0; i < _csvHeaderLine3.Length; i++)
            {
                _skillTable.Columns.Add(_csvHeaderLine3[i], typeof(string));
            }
            gridSkills.DataSource = _skillTable;
            FormatGridColumns();
            UpdateStatsLabel();
        }

        private void LoadCsv(string filePath)
        {
            try
            {
                if (!File.Exists(filePath))
                {
                    MessageBox.Show(string.Format("未找到指定配表文件：\n{0}", filePath), "文件不存在", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }

                string content = File.ReadAllText(filePath, Encoding.UTF8);
                List<string[]> rows = ParseCsv(content);

                if (rows.Count < 3)
                {
                    MessageBox.Show("CSV 配表格式不正确，至少需要包含 3 行表头（中文名、类型定义、字段名）！", "格式错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }

                _csvHeaderLine1 = rows[0];
                _csvHeaderLine2 = rows[1];
                _csvHeaderLine3 = rows[2];

                DataTable dt = new DataTable("ActiveSkills");
                for (int i = 0; i < _csvHeaderLine3.Length; i++)
                {
                    string colName = _csvHeaderLine3[i];
                    dt.Columns.Add(colName, typeof(string));
                }

                for (int r = 3; r < rows.Count; r++)
                {
                    string[] rData = rows[r];
                    if (rData.Length == 0 || (rData.Length == 1 && string.IsNullOrEmpty(rData[0]))) continue;

                    DataRow dr = dt.NewRow();
                    for (int c = 0; c < _csvHeaderLine3.Length; c++)
                    {
                        dr[c] = (c < rData.Length) ? rData[c] : "";
                    }
                    dt.Rows.Add(dr);
                }

                _skillTable = dt;
                gridSkills.DataSource = _skillTable;
                _currentFilePath = filePath;
                _isDirty = false;

                FormatGridColumns();
                UpdateStatsLabel();
                lblStatusFeedback.Text = string.Format("已载入 {0} 条技能数据", _skillTable.Rows.Count);
                lblStatusFeedback.ForeColor = Color.DarkGreen;
            }
            catch (Exception ex)
            {
                MessageBox.Show(string.Format("载入 CSV 失败：\n{0}", ex.Message), "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void SaveCsv(string targetPath)
        {
            if (_skillTable == null) return;
            try
            {
                // 创建 .bak 备份
                if (File.Exists(targetPath))
                {
                    string bakPath = targetPath + ".bak";
                    File.Copy(targetPath, bakPath, true);
                }

                using (StreamWriter sw = new StreamWriter(targetPath, false, new UTF8Encoding(false)))
                {
                    // 写入第 1 行：中文说明表头
                    sw.WriteLine(string.Join(",", EscapeArray(_csvHeaderLine1)));
                    // 写入第 2 行：类型定义
                    sw.WriteLine(string.Join(",", EscapeArray(_csvHeaderLine2)));
                    // 写入第 3 行：英文字段名
                    sw.WriteLine(string.Join(",", EscapeArray(_csvHeaderLine3)));

                    // 写入全部数据行
                    foreach (DataRow row in _skillTable.Rows)
                    {
                        if (row.RowState == DataRowState.Deleted) continue;
                        List<string> fields = new List<string>();
                        for (int i = 0; i < _csvHeaderLine3.Length; i++)
                        {
                            string colName = _csvHeaderLine3[i];
                            string val = _skillTable.Columns.Contains(colName) ? row[colName].ToString() : "";
                            fields.Add(EscapeCsvField(val));
                        }
                        sw.WriteLine(string.Join(",", fields.ToArray()));
                    }
                }

                _currentFilePath = targetPath;
                _isDirty = false;
                lblStatusFeedback.Text = string.Format("保存成功！共导出 {0} 条技能 (已自动备份至 .bak)", _skillTable.Rows.Count);
                lblStatusFeedback.ForeColor = Color.DarkGreen;
                UpdateStatsLabel();
                MessageBox.Show(string.Format("已成功保存并导出配表：\n{0}\n\n共计写入 {1} 条技能。\n原文件已自动备份为 {2}.bak", targetPath, _skillTable.Rows.Count, Path.GetFileName(targetPath)), "导出成功", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show(string.Format("保存 CSV 失败：\n{0}", ex.Message), "保存错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void OpenExternalCsv()
        {
            OpenFileDialog dlg = new OpenFileDialog();
            dlg.Filter = "CSV 文件 (*.csv)|*.csv|所有文件 (*.*)|*.*";
            dlg.Title = "选择技能配表 CSV 文件";
            if (dlg.ShowDialog() == DialogResult.OK)
            {
                LoadCsv(dlg.FileName);
            }
        }

        private void SaveAsCsv()
        {
            SaveFileDialog dlg = new SaveFileDialog();
            dlg.Filter = "CSV 文件 (*.csv)|*.csv";
            dlg.Title = "另存为技能配表 CSV";
            dlg.FileName = "active_skill_exported.csv";
            if (dlg.ShowDialog() == DialogResult.OK)
            {
                SaveCsv(dlg.FileName);
            }
        }

        private static string[] EscapeArray(string[] arr)
        {
            string[] res = new string[arr.Length];
            for (int i = 0; i < arr.Length; i++)
            {
                res[i] = EscapeCsvField(arr[i]);
            }
            return res;
        }

        private static string EscapeCsvField(string val)
        {
            if (string.IsNullOrEmpty(val)) return "";
            if (val.IndexOfAny(new char[] { ',', '"', '\r', '\n' }) >= 0)
            {
                return "\"" + val.Replace("\"", "\"\"") + "\"";
            }
            return val;
        }

        private static List<string[]> ParseCsv(string text)
        {
            var rows = new List<string[]>();
            var curRow = new List<string>();
            var curField = new StringBuilder();
            bool inQuotes = false;
            for (int i = 0; i < text.Length; i++)
            {
                char c = text[i];
                if (inQuotes)
                {
                    if (c == '"')
                    {
                        if (i + 1 < text.Length && text[i + 1] == '"')
                        {
                            curField.Append('"');
                            i++;
                        }
                        else
                        {
                            inQuotes = false;
                        }
                    }
                    else
                    {
                        curField.Append(c);
                    }
                }
                else
                {
                    if (c == '"')
                    {
                        inQuotes = true;
                    }
                    else if (c == ',')
                    {
                        curRow.Add(curField.ToString());
                        curField.Length = 0;
                    }
                    else if (c == '\r')
                    {
                        // 忽略 \r
                    }
                    else if (c == '\n')
                    {
                        curRow.Add(curField.ToString());
                        curField.Length = 0;
                        rows.Add(curRow.ToArray());
                        curRow.Clear();
                    }
                    else
                    {
                        curField.Append(c);
                    }
                }
            }
            if (curField.Length > 0 || curRow.Count > 0)
            {
                curRow.Add(curField.ToString());
                rows.Add(curRow.ToArray());
            }
            return rows;
        }

        #endregion

        #region 表格新增、克隆、删除与操作

        private int GetNextSkillId()
        {
            int maxId = 1100000;
            if (_skillTable != null)
            {
                foreach (DataRow row in _skillTable.Rows)
                {
                    if (row.RowState == DataRowState.Deleted) continue;
                    int idVal;
                    if (int.TryParse(row["ID"].ToString(), out idVal))
                    {
                        if (idVal > maxId) maxId = idVal;
                    }
                }
            }
            return maxId + 1;
        }

        private void AddGeneratedSkill(int count)
        {
            if (_skillTable == null) InitEmptyTable();

            int tier = cbTableRarity.SelectedIndex; // 0 = 随机, 1..6 = T1..T6
            int firstNewIndex = -1;
            string lastSkillName = "";

            txtSearch.Clear(); // 清空筛选确保新行可见

            for (int k = 0; k < count; k++)
            {
                int nextId = GetNextSkillId();
                SkillRecord record = GeneratorEngine.Generate(tier, nextId);
                lastSkillName = record.SkillName;

                DataRow dr = _skillTable.NewRow();
                foreach (var kv in record.CsvData)
                {
                    if (_skillTable.Columns.Contains(kv.Key))
                    {
                        dr[kv.Key] = kv.Value;
                    }
                }
                _skillTable.Rows.Add(dr);

                if (firstNewIndex < 0) firstNewIndex = _skillTable.Rows.Count - 1;
            }

            _isDirty = true;
            UpdateStatsLabel();

            if (gridSkills.Rows.Count > 0)
            {
                int targetIdx = gridSkills.Rows.Count - 1;
                gridSkills.ClearSelection();
                gridSkills.Rows[targetIdx].Selected = true;
                gridSkills.FirstDisplayedScrollingRowIndex = targetIdx;
            }

            if (count == 1)
            {
                lblStatusFeedback.Text = string.Format("已新增技能: {0} (阶位: {1})", lastSkillName, GeneratorEngine.GetTierName(tier == 0 ? 4 : tier));
            }
            else
            {
                lblStatusFeedback.Text = string.Format("已批量生成并新增 {0} 个技能至表格末尾！", count);
            }
            lblStatusFeedback.ForeColor = Color.DarkBlue;
        }

        private void AddEmptySkill()
        {
            if (_skillTable == null) InitEmptyTable();
            int nextId = GetNextSkillId();

            txtSearch.Clear();

            DataRow dr = _skillTable.NewRow();
            dr["ID"] = nextId.ToString();
            dr["name"] = "新技能";
            dr["desc"] = "100% 概率造成 100% 的普通伤害。";
            dr["trigger_chance"] = "100";
            dr["times_limit"] = "999";
            dr["effect_type"] = "1";
            dr["param"] = "100";
            dr["need_hit"] = "1";
            dr["animation_id"] = "142";
            dr["speed"] = "0";
            dr["defense"] = "0";
            dr["dodge"] = "0";
            dr["authority"] = "0";
            _skillTable.Rows.Add(dr);

            _isDirty = true;
            UpdateStatsLabel();

            int targetIdx = gridSkills.Rows.Count - 1;
            gridSkills.ClearSelection();
            gridSkills.Rows[targetIdx].Selected = true;
            gridSkills.FirstDisplayedScrollingRowIndex = targetIdx;

            lblStatusFeedback.Text = string.Format("已新建空白技能 (ID: {0})，可直接在表格中编辑！", nextId);
            lblStatusFeedback.ForeColor = Color.DarkSlateBlue;
        }

        private void CloneSelectedSkill()
        {
            if (gridSkills.SelectedRows.Count == 0)
            {
                MessageBox.Show("请先在表格中点击选中一行要克隆的技能！", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            DataGridViewRow selRow = gridSkills.SelectedRows[0];
            DataRowView drv = selRow.DataBoundItem as DataRowView;
            if (drv == null) return;

            int nextId = GetNextSkillId();
            DataRow dr = _skillTable.NewRow();
            foreach (DataColumn col in _skillTable.Columns)
            {
                dr[col.ColumnName] = drv.Row[col.ColumnName];
            }
            dr["ID"] = nextId.ToString();
            dr["name"] = drv.Row["name"].ToString() + "·改";
            _skillTable.Rows.Add(dr);

            _isDirty = true;
            UpdateStatsLabel();

            int targetIdx = gridSkills.Rows.Count - 1;
            gridSkills.ClearSelection();
            gridSkills.Rows[targetIdx].Selected = true;
            gridSkills.FirstDisplayedScrollingRowIndex = targetIdx;

            lblStatusFeedback.Text = string.Format("已成功克隆技能为 ID: {0}", nextId);
            lblStatusFeedback.ForeColor = Color.DarkSlateBlue;
        }

        private void DeleteSelectedSkill()
        {
            if (gridSkills.SelectedRows.Count == 0)
            {
                MessageBox.Show("请先在表格中选择要删除的技能行！", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            DataGridViewRow selRow = gridSkills.SelectedRows[0];
            DataRowView drv = selRow.DataBoundItem as DataRowView;
            if (drv == null) return;

            string id = drv.Row["ID"].ToString();
            string name = drv.Row["name"].ToString();

            DialogResult res = MessageBox.Show(string.Format("确定要删除技能「{0}」(ID: {1}) 吗？\n删除后需点击保存才会生效。", name, id),
                "确认删除", MessageBoxButtons.YesNo, MessageBoxIcon.Question);

            if (res == DialogResult.Yes)
            {
                drv.Row.Delete();
                _isDirty = true;
                UpdateStatsLabel();
                lblStatusFeedback.Text = string.Format("已删除技能: {0} (ID: {1})", name, id);
                lblStatusFeedback.ForeColor = Color.Firebrick;
            }
        }

        #endregion

        #region 搜索、界面事件与详情联动

        private void ApplySearchFilter()
        {
            if (_skillTable == null) return;
            string q = txtSearch.Text.Trim().Replace("'", "''");
            if (string.IsNullOrEmpty(q))
            {
                _skillTable.DefaultView.RowFilter = "";
            }
            else
            {
                _skillTable.DefaultView.RowFilter = string.Format("ID LIKE '%{0}%' OR name LIKE '%{0}%' OR desc LIKE '%{0}%'", q);
            }
            UpdateStatsLabel();
        }

        private void FormatGridColumns()
        {
            if (gridSkills.Columns.Count == 0 || _csvHeaderLine1 == null) return;

            for (int i = 0; i < gridSkills.Columns.Count && i < _csvHeaderLine1.Length; i++)
            {
                string colName = gridSkills.Columns[i].Name;
                string zhName = _csvHeaderLine1[i];
                gridSkills.Columns[i].HeaderText = string.Format("{0}\n({1})", zhName, colName);

                // 核心字段自适应宽度
                if (colName == "ID") gridSkills.Columns[i].Width = 75;
                else if (colName == "name") gridSkills.Columns[i].Width = 110;
                else if (colName == "desc") gridSkills.Columns[i].Width = 320;
                else if (colName == "trigger_chance") gridSkills.Columns[i].Width = 75;
                else if (colName == "times_limit") gridSkills.Columns[i].Width = 70;
                else if (colName == "effect_type") gridSkills.Columns[i].Width = 75;
                else if (colName == "param") gridSkills.Columns[i].Width = 70;
                else if (colName == "param2") gridSkills.Columns[i].Width = 70;
                else if (colName == "need_hit") gridSkills.Columns[i].Width = 65;
                else if (colName == "turn_cond1" || colName == "turn_cond2") gridSkills.Columns[i].Width = 75;
                else if (colName == "self_bp_cond2") gridSkills.Columns[i].Width = 85;
                else if (colName == "ignore_dodge" || colName == "ignore_defense") gridSkills.Columns[i].Width = 75;
                else if (colName == "speed" || colName == "defense" || colName == "dodge" || colName == "authority") gridSkills.Columns[i].Width = 55;
                else if (colName == "buffer_id") gridSkills.Columns[i].Width = 70;
                else if (colName == "seal_turneffect") gridSkills.Columns[i].Width = 90;
                else if (colName == "seal_turn") gridSkills.Columns[i].Width = 70;
                else if (colName == "animation_id") gridSkills.Columns[i].Width = 70;
                else gridSkills.Columns[i].Width = 80;
            }
        }

        private void OnGridSelectionChanged()
        {
            if (gridSkills.SelectedRows.Count == 0)
            {
                txtRowDetail.Clear();
                return;
            }

            DataGridViewRow sel = gridSkills.SelectedRows[0];
            DataRowView drv = sel.DataBoundItem as DataRowView;
            if (drv == null || drv.Row == null) return;

            DataRow row = drv.Row;
            StringBuilder sb = new StringBuilder();

            string id = row["ID"].ToString();
            string name = row["name"].ToString();
            string desc = row["desc"].ToString();
            string chance = row["trigger_chance"].ToString();
            string times = row["times_limit"].ToString();
            string effType = row["effect_type"].ToString();
            string param = row["param"].ToString();
            string param2 = row["param2"].ToString();
            string needHit = row["need_hit"].ToString();
            string t1 = row["turn_cond1"].ToString();
            string t2 = row["turn_cond2"].ToString();
            string bp2 = row["self_bp_cond2"].ToString();
            string igDodge = row["ignore_dodge"].ToString();
            string igDef = row["ignore_defense"].ToString();
            string spd = row["speed"].ToString();
            string def = row["defense"].ToString();
            string ddg = row["dodge"].ToString();
            string dom = row["authority"].ToString();
            string buf = row["buffer_id"].ToString();
            string sealEff = row["seal_turneffect"].ToString();
            string sealT = row["seal_turn"].ToString();
            string sealC2 = row["seal_cond2"].ToString();
            string anim = row["animation_id"].ToString();

            int animIdVal = 0;
            int.TryParse(anim, out animIdVal);
            SkillEffectMatcher.VariantEntry ve;
            SkillEffectMatcher.FamilyEntry fe;
            int previewId;
            string previewCn;
            string previewFolder;
            string previewCat;
            int previewHitType = 1;
            string previewHitName = "水平震退";
            bool isExactBound = false;

            if (SkillEffectMatcher.TryGetById(animIdVal, out ve, out fe))
            {
                isExactBound = true;
                previewId = ve.AnimationId;
                previewCn = ve.CnName;
                previewFolder = ve.FolderName;
                previewCat = fe.CategoryCn;
                previewHitType = fe.HitReactionType;
                previewHitName = fe.HitReactionName;
            }
            else
            {
                string rowGenre = InferGenreFromRow(effType, igDodge, igDef);
                SkillEffectMatcher.ResolveSkillEffect(name, rowGenre, 4, desc, out previewId, out previewCn, out previewFolder, out previewCat, out previewHitType, out previewHitName);
            }

            sb.AppendLine(string.Format("【技能编号: {0} | 技能名称: {1}】", id, name));
            sb.AppendLine(string.Format("▶ 描述文本: {0}", desc));
            sb.AppendLine(string.Format("▶ 战斗参数: 发动几率={0}% | 释放上限={1}次 | 主参数={2}% (类型={3}: {4}) | 参数2={5} | 命中触发={6}",
                chance, (times == "0" || times == "999" ? "无限制" : times), param, effType, FormatEffectTypeDesc(effType), (string.IsNullOrEmpty(param2) ? "无" : param2), needHit == "1" ? "是" : "否"));
            sb.AppendLine(string.Format("▶ 触发窗口: 回合条件={0} | 战力门槛={1} | 必中(无视闪避)={2} | 破防(无视免伤)={3}",
                FormatTurnCondText(t1, t2), (string.IsNullOrEmpty(bp2) ? "无限制" : string.Format("己方战力低于{0}%", bp2)), igDodge == "1" ? "是" : "否", igDef == "1" ? "是" : "否"));
            sb.AppendLine(string.Format("▶ 四维增益: 先机(speed)=+{0} | 坚韧(defense)=+{1} | 勇气(dodge)=+{2} | 魔力(authority)=+{3} | 原表动画ID={4}",
                spd, def, ddg, dom, anim));
            if (isExactBound)
            {
                sb.AppendLine(string.Format("▶ 绑定特效: [{0}] {1} ({2}) | 受击效果: [{3}]{4} | 精灵表: {5}", previewId, previewCn, previewCat, previewHitType, previewHitName, previewFolder));
            }
            else
            {
                sb.AppendLine(string.Format("▶ 智能适配特效预览: [{0}] {1} ({2}) | 受击效果: [{3}]{4} | (原表ID={5}，可点击上方「⚡ 写入当前行适配特效ID」落盘)", previewId, previewCn, previewCat, previewHitType, previewHitName, anim));
            }
            if (!string.IsNullOrEmpty(buf) || !string.IsNullOrEmpty(sealEff) || !string.IsNullOrEmpty(sealC2))
            {
                sb.AppendLine(string.Format("▶ 机制状态: BUFF_ID={0} | 封印效果={1} (持续{2}回合, 判定门槛={3})",
                    (string.IsNullOrEmpty(buf) ? "无" : buf), (string.IsNullOrEmpty(sealEff) ? "无" : sealEff), (string.IsNullOrEmpty(sealT) ? "0" : sealT), (string.IsNullOrEmpty(sealC2) ? "无" : sealC2)));
            }

            txtRowDetail.Text = sb.ToString();

            if (_editorEffectPreview != null)
            {
                _editorEffectPreview.PlayByAnimationId(previewId, isExactBound ? "" : "智能适配预览");
            }
        }

        private static string InferGenreFromRow(string effType, string igDodge, string igDef)
        {
            if (effType == "10") return "坚韧";
            if (effType == "2") return "勇气";
            if (effType == "5" || effType == "6" || igDef == "1") return "魔力";
            if (effType == "13" || igDodge == "1") return "先机";
            return "勇气";
        }

        private void ApplyMatchedEffectToSelectedRow()
        {
            if (gridSkills.SelectedRows.Count == 0) return;
            DataGridViewRow sel = gridSkills.SelectedRows[0];
            DataRowView drv = sel.DataBoundItem as DataRowView;
            if (drv == null || drv.Row == null) return;

            DataRow row = drv.Row;
            string name = row["name"].ToString();
            string desc = row["desc"].ToString();
            string effType = row["effect_type"].ToString();
            string igDodge = row["ignore_dodge"].ToString();
            string igDef = row["ignore_defense"].ToString();

            int matchedId;
            string matchedCn, matchedFolder, matchedCat;
            SkillEffectMatcher.ResolveSkillEffect(name, InferGenreFromRow(effType, igDodge, igDef), 4, desc, out matchedId, out matchedCn, out matchedFolder, out matchedCat);

            if (_editorEffectPreview != null && _editorEffectPreview.CurrentAnimationId >= 1001)
            {
                matchedId = _editorEffectPreview.CurrentAnimationId;
                matchedCn = _editorEffectPreview.CurrentCnName;
            }

            row["animation_id"] = matchedId.ToString();
            _isDirty = true;
            lblStatusFeedback.Text = string.Format("已将「{0}」动画ID更新为 [{1}] {2}", name, matchedId, matchedCn);
            lblStatusFeedback.ForeColor = Color.DarkBlue;
            OnGridSelectionChanged();
        }

        private void BatchApplyMatchedEffectsToAllRows()
        {
            if (_skillTable == null || _skillTable.Rows.Count == 0) return;
            DialogResult res = MessageBox.Show(
                string.Format("确定要根据全表 {0} 条技能的【前缀(定色)+后缀(定型)】规则，批量刷新所有技能行的 animation_id (1001~1495) 吗？\n\n刷新后可在表格中逐行点击预览动画，点击「保存覆盖原表」即可生效。", _skillTable.Rows.Count),
                "确认全表智能刷新特效ID",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question);
            if (res != DialogResult.Yes) return;

            int updated = 0;
            foreach (DataRow row in _skillTable.Rows)
            {
                if (row.RowState == DataRowState.Deleted) continue;
                string name = row["name"].ToString();
                string desc = row["desc"].ToString();
                string effType = row["effect_type"].ToString();
                string igDodge = row["ignore_dodge"].ToString();
                string igDef = row["ignore_defense"].ToString();

                int matchedId;
                string matchedCn, matchedFolder, matchedCat;
                SkillEffectMatcher.ResolveSkillEffect(name, InferGenreFromRow(effType, igDodge, igDef), 4, desc, out matchedId, out matchedCn, out matchedFolder, out matchedCat);
                row["animation_id"] = matchedId.ToString();
                updated++;
            }

            _isDirty = true;
            UpdateStatsLabel();
            OnGridSelectionChanged();
            lblStatusFeedback.Text = string.Format("已全表刷新 {0} 条技能的像素特效ID！", updated);
            lblStatusFeedback.ForeColor = Color.DarkGreen;
        }

        private void OnGridCellValueChanged()
        {
            _isDirty = true;
            lblStatusFeedback.Text = "（有未保存修改）";
            lblStatusFeedback.ForeColor = Color.DarkOrange;
            OnGridSelectionChanged();
        }

        private static string FormatEffectTypeDesc(string eff)
        {
            if (eff == "1") return "普通伤害 (melee_damage)";
            if (eff == "2") return "暴击伤害 (critical_damage)";
            if (eff == "5") return "纯粹/真伤 (true_damage)";
            if (eff == "6") return "斩杀伤害 (execute_damage)";
            if (eff == "10") return "恢复总战力 (heal_init_bp)";
            if (eff == "13") return "先机直伤 (initiative_damage)";
            if (eff == "14") return "技能复制 (mirror_skill)";
            return "特殊机制效果";
        }

        private static string FormatTurnCondText(string t1, string t2)
        {
            int c1 = 0, c2 = 0;
            int.TryParse(t1, out c1);
            int.TryParse(t2, out c2);
            if (c1 > 0 && c2 > 0) return string.Format("第{0}~{1}回合", c1 + 1, c2);
            if (c1 > 0) return string.Format("第{0}回合起", c1 + 1);
            if (c2 > 0) return string.Format("前{0}回合内", c2);
            return "无限制 (开局可用)";
        }

        private void UpdateStatsLabel()
        {
            int total = (_skillTable != null) ? _skillTable.Rows.Count : 0;
            int view = (_skillTable != null) ? _skillTable.DefaultView.Count : 0;
            string pathText = string.IsNullOrEmpty(_currentFilePath) ? "未加载" : Path.GetFileName(_currentFilePath);
            string dirtyText = _isDirty ? " [已修改*]" : " [已保存]";
            lblStats.Text = string.Format("总行数: {0} | 显示: {1} | 文件: {2}{3}", total, view, pathText, dirtyText);
        }

        private static void EnableDoubleBuffer(DataGridView dgv)
        {
            try
            {
                typeof(DataGridView).InvokeMember("DoubleBuffered",
                    BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.SetProperty,
                    null, dgv, new object[] { true });
            }
            catch { }
        }

        #endregion

        #region Tab 2 前后字段与随机组合设置

        private void OnAffixCategoryChanged()
        {
            // 保存之前分类的内容
            SaveCurrentAffixEditsToMemory(_currentCategoryIndex);

            // 切换到新分类
            _currentCategoryIndex = cbAffixCategory.SelectedIndex;
            LoadAffixCategoryToView(_currentCategoryIndex);
        }

        private void LoadAffixCategoryToView(int categoryIndex)
        {
            AffixBank bank = AffixManager.GetBankByIndex(categoryIndex);
            txtPrefixes.Text = string.Join(Environment.NewLine, bank.Prefixes.ToArray());
            txtSuffixes.Text = string.Join(Environment.NewLine, bank.Suffixes.ToArray());
            UpdateAffixCounts();
        }

        private void SaveCurrentAffixEditsToMemory(int categoryIndex)
        {
            AffixBank bank = AffixManager.GetBankByIndex(categoryIndex);
            bank.Prefixes.Clear();
            string[] pLines = txtPrefixes.Text.Split(new string[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries);
            foreach (var l in pLines)
            {
                string s = l.Trim();
                if (!string.IsNullOrEmpty(s) && !bank.Prefixes.Contains(s)) bank.Prefixes.Add(s);
            }

            bank.Suffixes.Clear();
            string[] sLines = txtSuffixes.Text.Split(new string[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries);
            foreach (var l in sLines)
            {
                string s = l.Trim();
                if (!string.IsNullOrEmpty(s) && !bank.Suffixes.Contains(s)) bank.Suffixes.Add(s);
            }
        }

        private void SaveCurrentAffixEdits()
        {
            SaveCurrentAffixEditsToMemory(_currentCategoryIndex);
            AffixManager.ConnectMode = cbConnectMode.SelectedIndex;
            AffixManager.SaveToFile();
            MessageBox.Show(string.Format("已成功保存前后字段词库！\n配置文件已更新至：\n{0}", AffixManager.ConfigFilePath), "保存成功", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        private void ImportFromExcel()
        {
            try
            {
                string scriptPath = @"D:\123\import_excel_affixes.py";
                if (File.Exists(scriptPath))
                {
                    System.Diagnostics.ProcessStartInfo psi = new System.Diagnostics.ProcessStartInfo("python", "\"" + scriptPath + "\"");
                    psi.CreateNoWindow = true;
                    psi.UseShellExecute = false;
                    psi.WorkingDirectory = @"D:\123";
                    using (System.Diagnostics.Process proc = System.Diagnostics.Process.Start(psi))
                    {
                        proc.WaitForExit(10000);
                    }
                }
                AffixManager.LoadFromFile();
                LoadAffixCategoryToView(_currentCategoryIndex);
                cbConnectMode.SelectedIndex = AffixManager.ConnectMode;
                MessageBox.Show(string.Format("已成功从「游戏全量技能逆向拆解与三特征词库.xlsx」全量导入并同步至当前词库！\n\n▶ 勇气流: 前缀 {0} 个, 后缀 {1} 个\n▶ 先机流: 前缀 {2} 个, 后缀 {3} 个\n▶ 坚韧流: 前缀 {4} 个, 后缀 {5} 个\n▶ 魔力流: 前缀 {6} 个, 后缀 {7} 个\n▶ 通用词库: 前缀 {8} 个, 后缀 {9} 个",
                    AffixManager.Havoc.Prefixes.Count, AffixManager.Havoc.Suffixes.Count,
                    AffixManager.Precision.Prefixes.Count, AffixManager.Precision.Suffixes.Count,
                    AffixManager.Tenacity.Prefixes.Count, AffixManager.Tenacity.Suffixes.Count,
                    AffixManager.Utility.Prefixes.Count, AffixManager.Utility.Suffixes.Count,
                    AffixManager.Common.Prefixes.Count, AffixManager.Common.Suffixes.Count),
                    "Excel 词库同步成功", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show("导入失败: " + ex.Message, "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void ResetAffixDefaults()
        {
            DialogResult res = MessageBox.Show("确定要将前后字段重置为内置西幻奇幻默认词库吗？\n当前所做的自定义修改将被覆盖。", "确认重置", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            if (res == DialogResult.Yes)
            {
                AffixManager.ResetDefaults();
                LoadAffixCategoryToView(_currentCategoryIndex);
                cbConnectMode.SelectedIndex = AffixManager.ConnectMode;
                MessageBox.Show("已成功恢复默认西幻前后字段！", "已重置", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
        }

        private void UpdateAffixCounts()
        {
            string[] pLines = txtPrefixes.Text.Split(new string[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries);
            string[] sLines = txtSuffixes.Text.Split(new string[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries);
            lblPrefixCount.Text = string.Format("当前包含: {0} 个前字段", pLines.Length);
            lblSuffixCount.Text = string.Format("当前包含: {0} 个后字段 (10种受击反馈自动跟随便配特效: 1震退/2击飞/3后仰/4旋转/5掀飞/6炸散/7压缩/8颠簸/9聚拢/10旋转散开)", sLines.Length);
        }

        private void RunAffixRandomTest()
        {
            SaveCurrentAffixEditsToMemory(_currentCategoryIndex);
            AffixManager.ConnectMode = cbConnectMode.SelectedIndex;

            string genre = "通用";
            if (_currentCategoryIndex == 1) genre = "勇气";
            else if (_currentCategoryIndex == 2) genre = "先机";
            else if (_currentCategoryIndex == 3) genre = "坚韧";
            else if (_currentCategoryIndex == 4) genre = "魔力";

            StringBuilder sb = new StringBuilder();
            sb.AppendLine(string.Format("=== [分类: {0}] 自定义前后字段 10 连随机组合测试 (点击任意行可在右侧预览对应特效) ===", cbAffixCategory.Text));
            int firstAnimId = 0;
            for (int i = 1; i <= 10; i++)
            {
                string name = AffixManager.GenerateRandomName(genre);
                int animId, hitType;
                string effCn, effFolder, effCat, hitName;
                SkillEffectMatcher.ResolveSkillEffect(name, genre, 4, "", out animId, out effCn, out effFolder, out effCat, out hitType, out hitName);
                if (i == 1) firstAnimId = animId;
                sb.AppendLine(string.Format("  #{0:D2}:  【{1}】  ➔  特效: [{2}] {3} ({4}) | 受击: [{5}]{6}", i, name, animId, effCn, effCat, hitType, hitName));
            }

            txtTestOutput.Text = sb.ToString();
            if (_affixEffectPreview != null && firstAnimId >= 1001)
            {
                _affixEffectPreview.PlayByAnimationId(firstAnimId, "");
            }
        }

        private void OnAffixTestOutputClicked()
        {
            if (_affixEffectPreview == null || string.IsNullOrEmpty(txtTestOutput.Text)) return;
            int caret = txtTestOutput.SelectionStart;
            int lineIdx = txtTestOutput.GetLineFromCharIndex(caret);
            string[] lines = txtTestOutput.Lines;
            if (lineIdx >= 0 && lineIdx < lines.Length)
            {
                int aid = ExtractAnimationIdFromText(lines[lineIdx]);
                if (aid >= 1001)
                {
                    _affixEffectPreview.PlayByAnimationId(aid, "");
                }
            }
        }

        #endregion

        #region Tab 3 控制台单抽与分析

        private void GenerateConsoleSingle()
        {
            int tier = cbConsoleRarity.SelectedIndex;
            SkillRecord res = GeneratorEngine.Generate(tier);
            txtConsoleSummary.Text = res.SummaryText;
            txtConsoleDetails.Text = res.DetailText;

            _lastConsoleRecords.Clear();
            _lastConsoleRecords.Add(res);

            if (lstConsoleSkills != null)
            {
                lstConsoleSkills.BeginUpdate();
                lstConsoleSkills.Items.Clear();
                lstConsoleSkills.Items.Add(string.Format("#01 《{0}》({1}) ➔ [{2}] {3} ({4})", res.SkillName, res.TierName, res.AnimationId, res.EffectCnName, res.HitReactionName));
                lstConsoleSkills.SelectedIndex = 0;
                lstConsoleSkills.EndUpdate();
            }

            if (_consoleEffectPreview != null && res.AnimationId >= 1001)
            {
                _consoleEffectPreview.PlayByAnimationId(res.AnimationId, string.Format("《{0}》", res.SkillName));
            }
        }

        private void GenerateConsoleBatch()
        {
            StringBuilder sbSum = new StringBuilder();
            StringBuilder sbDet = new StringBuilder();

            _lastConsoleRecords.Clear();
            if (lstConsoleSkills != null)
            {
                lstConsoleSkills.BeginUpdate();
                lstConsoleSkills.Items.Clear();
            }

            int tier = cbConsoleRarity.SelectedIndex;
            for (int i = 1; i <= 10; i++)
            {
                SkillRecord res = GeneratorEngine.Generate(tier);
                _lastConsoleRecords.Add(res);

                sbSum.AppendLine(string.Format("===== 编号 #{0:D2} =====", i));
                sbSum.AppendLine(res.SummaryText);
                sbSum.AppendLine();

                sbDet.AppendLine(string.Format("==================== [#{0:D2}] {1} ({2}) ====================", i, res.SkillName, res.TierName));
                sbDet.AppendLine(res.DetailText);
                sbDet.AppendLine();

                if (lstConsoleSkills != null)
                {
                    lstConsoleSkills.Items.Add(string.Format("#{0:D2} 《{1}》({2}) ➔ [{3}] {4} ({5})", i, res.SkillName, res.TierName, res.AnimationId, res.EffectCnName, res.HitReactionName));
                }
            }

            txtConsoleSummary.Text = sbSum.ToString();
            txtConsoleDetails.Text = sbDet.ToString();

            if (lstConsoleSkills != null)
            {
                if (lstConsoleSkills.Items.Count > 0) lstConsoleSkills.SelectedIndex = 0;
                lstConsoleSkills.EndUpdate();
            }
        }

        private void OnConsoleSkillListSelected()
        {
            if (lstConsoleSkills == null || lstConsoleSkills.SelectedIndex < 0) return;
            int idx = lstConsoleSkills.SelectedIndex;
            if (idx >= 0 && idx < _lastConsoleRecords.Count)
            {
                SkillRecord rec = _lastConsoleRecords[idx];
                if (_consoleEffectPreview != null && rec.AnimationId >= 1001)
                {
                    _consoleEffectPreview.PlayByAnimationId(rec.AnimationId, string.Format("#{0:D2} 《{1}》", idx + 1, rec.SkillName));
                }

                // 同步滚动左侧文本框到对应编号
                if (_lastConsoleRecords.Count > 1)
                {
                    ScrollTextBoxToMarker(txtConsoleSummary, string.Format("===== 编号 #{0:D2} =====", idx + 1));
                    ScrollTextBoxToMarker(txtConsoleDetails, string.Format("[#{0:D2}]", idx + 1));
                }
            }
        }

        private static void ScrollTextBoxToMarker(TextBox tb, string marker)
        {
            if (tb == null || string.IsNullOrEmpty(tb.Text) || string.IsNullOrEmpty(marker)) return;
            int pos = tb.Text.IndexOf(marker, StringComparison.Ordinal);
            if (pos >= 0)
            {
                tb.SelectionStart = pos;
                tb.SelectionLength = 0;
                tb.ScrollToCaret();
            }
        }

        private void OnConsoleTextClicked(TextBox tb)
        {
            if (tb == null || string.IsNullOrEmpty(tb.Text) || _consoleEffectPreview == null) return;
            int caret = tb.SelectionStart;
            int lineIdx = tb.GetLineFromCharIndex(caret);
            string[] lines = tb.Lines;
            if (lineIdx >= 0 && lineIdx < lines.Length)
            {
                // 优先检查当前行是否直接带有 [1001~1604]
                int directId = ExtractAnimationIdFromText(lines[lineIdx]);
                if (directId >= 1001)
                {
                    _consoleEffectPreview.PlayByAnimationId(directId, "");
                    return;
                }

                // 向上回溯最近的 #01 ~ #10 块
                for (int r = lineIdx; r >= 0; r--)
                {
                    string ln = lines[r];
                    int hashPos = ln.IndexOf('#');
                    if (hashPos >= 0 && hashPos + 2 < ln.Length && char.IsDigit(ln[hashPos + 1]) && char.IsDigit(ln[hashPos + 2]))
                    {
                        int num = (ln[hashPos + 1] - '0') * 10 + (ln[hashPos + 2] - '0');
                        if (num >= 1 && num <= _lastConsoleRecords.Count)
                        {
                            SkillRecord rec = _lastConsoleRecords[num - 1];
                            _consoleEffectPreview.PlayByAnimationId(rec.AnimationId, string.Format("#{0:D2} 《{1}》", num, rec.SkillName));
                            return;
                        }
                    }
                }
            }
        }

        private static int ExtractAnimationIdFromText(string text)
        {
            if (string.IsNullOrEmpty(text)) return 0;
            int open = text.IndexOf('[');
            while (open >= 0)
            {
                int close = text.IndexOf(']', open + 1);
                if (close > open + 1 && close - open <= 6)
                {
                    int val;
                    if (int.TryParse(text.Substring(open + 1, close - open - 1), out val))
                    {
                        if (val >= 1001 && val <= 1604) return val;
                    }
                }
                open = text.IndexOf('[', open + 1);
            }
            return 0;
        }

        #endregion

        [System.Runtime.InteropServices.DllImport("kernel32.dll")]
        private static extern bool AttachConsole(int pid);

        [System.Runtime.InteropServices.DllImport("kernel32.dll")]
        private static extern bool FreeConsole();

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (_isDirty)
            {
                DialogResult res = MessageBox.Show("当前配表有未保存的修改，是否在退出前保存？", "未保存提示", MessageBoxButtons.YesNoCancel, MessageBoxIcon.Question);
                if (res == DialogResult.Yes)
                {
                    SaveCsv(_currentFilePath);
                }
                else if (res == DialogResult.Cancel)
                {
                    e.Cancel = true;
                    return;
                }
            }
            base.OnFormClosing(e);
        }

        [STAThread]
        public static void Main(string[] args)
        {
            if (args != null && args.Length > 0 && (args[0] == "/console" || args[0] == "-c" || args[0] == "--console"))
            {
                AttachConsole(-1);
                Console.OutputEncoding = Encoding.UTF8;
                int tier = 0;
                string genre = "";
                if (args.Length > 1 && int.TryParse(args[1], out tier)) { }
                if (args.Length > 2) { genre = args[2]; }
                SkillRecord res = GeneratorEngine.Generate(tier, genre);
                Console.WriteLine("=== 生成结果概览 ===");
                Console.WriteLine(res.SummaryText);
                Console.WriteLine();
                Console.WriteLine("=== 随机字段详情与区间分析 ===");
                Console.WriteLine(res.DetailText);
                return;
            }

            FreeConsole();
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new SkillGeneratorForm());
        }

        private static readonly string[] DefaultColumnNames = new string[] {
            "ID", "name", "desc", "turn_cond1", "turn_cond2",
            "self_bp_cond1", "self_bp_cond2", "enemy_bp_cond1", "enemy_bp_cond2", "turn_cond3",
            "cur_bp_cond", "trigger_chance", "times_limit", "effect_type", "param",
            "param2", "need_hit", "self_property", "enemy_property", "turn_fixed",
            "exhaust_turn", "ignore_dodge", "ignore_defense", "seal_turneffect", "seal_turn",
            "seal_cond1", "seal_cond2", "animation_id", "speed", "defense",
            "dodge", "authority", "buffer_id", "buffer_id2", "buffer_id3"
        };
        private static readonly string[] DefaultChineseHeaders = new string[] {
            "ID", "技能名", "描述", "战斗回合高于X时", "战斗回合低于X时",
            "己方战力高于X%时", "己方战力低于X%时", "敌方战力高于X%时", "敌方战力低于X%时", "上回合是否击中",
            "敌我战力高低判断", "Y发动概率", "次数限制", "技能效果", "Z参数",
            "参数2", "命中生效", "己方四维变化", "敌方四维变化", "修改回合数",
            "虚弱", "无法闪避", "无视防御", "封印技能效果", "封印回合",
            "封印x概率以上", "封印x概率以下", "动画id", "增加四维先攻", "增加四维防御",
            "增加四维闪避", "增加四维王者", "BUFF ID", "BUFF ID2", "BUFF ID3"
        };
        private static readonly string[] DefaultTypeHeaders = new string[] {
            "number", "string", "string", "number", "number",
            "number", "number", "number", "number", "number",
            "number", "number", "number", "number", "number",
            "number", "number", "string", "string", "number",
            "number", "boolean", "boolean", "number", "number",
            "number", "number", "number", "number", "number",
            "number", "number", "number", "number", "number"
        };
    }

    public class SkillRecord
    {
        public string TierName;
        public string SkillName;
        public string EffectDesc;
        public int HitReactionType = 1;
        public string HitReactionName = "水平震退";
        public int AnimationId = 1329;
        public string EffectCnName = "大红圆斩";
        public string EffectFolder = "fx2_slash_large_red";
        public string EffectCategory = "刀剑圆斩";
        public string SummaryText;
        public string DetailText;
        public Dictionary<string, string> CsvData = new Dictionary<string, string>();
    }

    public class SubEffectMeta
    {
        public string Name;
        public string Category;
        public string DescTemplate;
        public string CsvFields;
        public float[] TierParams;
        public int ChanceMin;
        public int ChanceMax;
        public string Unit;
        public int MinUnlockTier;

        public SubEffectMeta(string name, string category, string descTemplate, string csvFields,
            float[] tierParams, int chanceMin, int chanceMax, string unit, int minUnlockTier = 1)
        {
            Name = name;
            Category = category;
            DescTemplate = descTemplate;
            CsvFields = csvFields;
            TierParams = tierParams;
            ChanceMin = chanceMin;
            ChanceMax = chanceMax;
            Unit = unit;
            MinUnlockTier = minUnlockTier;
        }
    }

    #region 前后字段配置与随机组合词库引擎

    public class AffixBank
    {
        public List<string> Prefixes = new List<string>();
        public List<string> Suffixes = new List<string>();
    }

    public static class AffixManager
    {
        public static int ConnectMode = 0; // 0: 智能混合 (70%直接, 30%之), 1: 纯直接拼接, 2: 纯“之”字拼接
        public static AffixBank Common = new AffixBank();
        public static AffixBank Havoc = new AffixBank();
        public static AffixBank Precision = new AffixBank();
        public static AffixBank Tenacity = new AffixBank();
        public static AffixBank Utility = new AffixBank();

        // 高阶构词范式扩展库
        public static List<string> MonoActions = new List<string>();
        public static List<string> MonoObjects = new List<string>();
        public static List<string> MonoCarriers = new List<string>();
        public static List<string> MonoModifiers = new List<string>();
        public static List<string> MonoBeasts = new List<string>();

        public static List<string> EpicVerbs = new List<string>();
        public static List<string> EpicTargets = new List<string>();
        public static List<string> EpicRelics = new List<string>();

        public static List<string> ApexPrefixes = new List<string>();
        public static List<string> ApexActions = new List<string>();
        public static List<string> ApexFields = new List<string>();

        public const string ConfigFilePath = @"D:\123\skill_affixes.txt";
        private static Random _rand = new Random();

        static AffixManager()
        {
            Init();
        }

        public static void Init()
        {
            if (File.Exists(ConfigFilePath))
            {
                LoadFromFile();
            }
            else
            {
                ResetDefaults();
            }
        }

        public static AffixBank GetBankByIndex(int index)
        {
            switch (index)
            {
                case 1: return Havoc;
                case 2: return Precision;
                case 3: return Tenacity;
                case 4: return Utility;
                default: return Common;
            }
        }

        public static AffixBank GetBankByGenre(string genre)
        {
            if (genre.Contains("暴击") || genre.Contains("勇气")) return Havoc;
            if (genre.Contains("精准") || genre.Contains("先机")) return Precision;
            if (genre.Contains("恢复") || genre.Contains("坚韧")) return Tenacity;
            if (genre.Contains("机制") || genre.Contains("魔力")) return Utility;
            return Common;
        }

        public static bool TryParseSuffixHitReaction(string rawSuffix, out string cleanSuffix, out int hitReactionType, out string reactionName)
        {
            cleanSuffix = rawSuffix ?? "";
            hitReactionType = 1;
            reactionName = "水平震退";
            if (string.IsNullOrEmpty(rawSuffix)) return false;

            char[] seps = new char[] { ':', '：', '|', '=' };
            int idx = rawSuffix.IndexOfAny(seps);
            if (idx < 0) return false;

            cleanSuffix = rawSuffix.Substring(0, idx).Trim();
            string tag = rawSuffix.Substring(idx + 1).Trim().ToLowerInvariant();

            if (tag == "9" || tag.Contains("聚拢") || tag.Contains("吸附") || tag.Contains("黑洞") || tag.Contains("converge") || tag.Contains("pull"))
            {
                hitReactionType = 9; reactionName = "中心聚拢吸附"; return true;
            }
            if (tag == "10" || tag.Contains("旋转散开") || tag.Contains("集体旋转") || tag.Contains("散开") || tag.Contains("漩涡") || tag.Contains("swirl"))
            {
                hitReactionType = 10; reactionName = "集体旋转散开"; return true;
            }
            if (tag == "1" || tag.Contains("水平") || tag.Contains("震退") || tag.Contains("击退") || tag.Contains("knockback"))
            {
                hitReactionType = 1; reactionName = "水平震退"; return true;
            }
            if (tag == "2" || tag.Contains("垂直") || tag.Contains("击飞") || tag.Contains("浮空") || tag.Contains("popup") || tag.Contains("pop-up"))
            {
                hitReactionType = 2; reactionName = "垂直击飞"; return true;
            }
            if (tag == "3" || tag.Contains("抛物线") || tag.Contains("后仰") || tag.Contains("击倒") || tag.Contains("launch"))
            {
                hitReactionType = 3; reactionName = "抛物线后仰"; return true;
            }
            if (tag == "4" || tag.Contains("旋转") || tag.Contains("翻滚") || tag.Contains("四向") || tag.Contains("spin"))
            {
                hitReactionType = 4; reactionName = "四向旋转翻滚"; return true;
            }
            if (tag == "5" || tag.Contains("波浪") || tag.Contains("掀飞") || tag.Contains("wave"))
            {
                hitReactionType = 5; reactionName = "波浪状掀飞"; return true;
            }
            if (tag == "6" || tag.Contains("炸散") || tag.Contains("中心炸散") || tag.Contains("爆散") || tag.Contains("disperse"))
            {
                hitReactionType = 6; reactionName = "中心炸散复位"; return true;
            }
            if (tag == "7" || tag.Contains("手风琴") || tag.Contains("压缩") || tag.Contains("压制") || tag.Contains("squeeze"))
            {
                hitReactionType = 7; reactionName = "手风琴压缩"; return true;
            }
            if (tag == "8" || tag.Contains("地震") || tag.Contains("颠簸") || tag.Contains("震颤") || tag.Contains("tremor"))
            {
                hitReactionType = 8; reactionName = "地震颠簸"; return true;
            }

            return false;
        }

        public static string GenerateRandomName(string genre)
        {
            int hitReactionType;
            string reactionName;
            return GenerateRandomName(genre, 0, out hitReactionType, out reactionName);
        }

        public static string GenerateRandomName(string genre, out int hitReactionType, out string reactionName)
        {
            return GenerateRandomName(genre, 0, out hitReactionType, out reactionName);
        }

        public static string GenerateRandomName(string genre, int tier, out int hitReactionType, out string reactionName)
        {
            hitReactionType = 1;
            reactionName = "水平震退";

            // ─── 阶位构词规则 ───
            // 1. T1、T2：100% 用单字组合 (3字，如: 斩天剑、邪龙眼)
            // 2. T6：100% 用 6字 (宏大长句诗意式 + 极境战技风暴式，如: 撕裂天空之剑、究极斩击风暴)
            // 3. T3、T4、T5：四字始终占 75%，从单字更高过渡到多字更高：
            //    - T3: 四字 75%, 单字 20%, 六字 5%   (单字更高)
            //    - T4: 四字 75%, 单字 12.5%, 六字 12.5% (平分过渡)
            //    - T5: 四字 75%, 单字 5%, 六字 20%   (多字更高)
            if (tier == 1 || tier == 2)
            {
                return GenerateMonoName(out hitReactionType, out reactionName);
            }
            else if (tier == 6)
            {
                return GenerateSixCharName(out hitReactionType, out reactionName);
            }
            else if (tier == 3)
            {
                double roll = _rand.NextDouble();
                if (roll < 0.75) return GenerateFourCharName(genre, out hitReactionType, out reactionName);
                else if (roll < 0.95) return GenerateMonoName(out hitReactionType, out reactionName);
                else return GenerateSixCharName(out hitReactionType, out reactionName);
            }
            else if (tier == 4)
            {
                double roll = _rand.NextDouble();
                if (roll < 0.75) return GenerateFourCharName(genre, out hitReactionType, out reactionName);
                else if (roll < 0.875) return GenerateMonoName(out hitReactionType, out reactionName);
                else return GenerateSixCharName(out hitReactionType, out reactionName);
            }
            else if (tier == 5)
            {
                double roll = _rand.NextDouble();
                if (roll < 0.75) return GenerateFourCharName(genre, out hitReactionType, out reactionName);
                else if (roll < 0.80) return GenerateMonoName(out hitReactionType, out reactionName);
                else return GenerateSixCharName(out hitReactionType, out reactionName);
            }
            else
            {
                // tier 未指定 (默认/测试抽检)
                double roll = _rand.NextDouble();
                if (roll < 0.75) return GenerateFourCharName(genre, out hitReactionType, out reactionName);
                else if (roll < 0.875) return GenerateMonoName(out hitReactionType, out reactionName);
                else return GenerateSixCharName(out hitReactionType, out reactionName);
            }
        }

        public static string GenerateMonoName(out int hitReactionType, out string reactionName)
        {
            hitReactionType = 1;
            reactionName = "水平震退";

            if (MonoActions.Count == 0 || MonoObjects.Count == 0 || MonoCarriers.Count == 0)
            {
                return "斩天剑";
            }

            if (_rand.Next(100) < 50 && MonoModifiers.Count > 0 && MonoBeasts.Count > 0)
            {
                // 1B: 修饰(1) + 主体(1) + 核心部位(1) = 3字 (如: 邪龙眼、圣兽心、魔王角)
                string m = MonoModifiers[_rand.Next(MonoModifiers.Count)];
                string b = MonoBeasts[_rand.Next(MonoBeasts.Count)];
                string c = MonoCarriers[_rand.Next(MonoCarriers.Count)];
                if (c == "盾" || c == "塔") c = "矛";
                string name = m + b + c;

                if (c == "枪" || c == "矛" || c == "眼" || c == "心" || c == "瞳" || c == "矢") { hitReactionType = 3; reactionName = "抛物线后仰"; }
                else if (c == "骨" || c == "印") { hitReactionType = 7; reactionName = "手风琴压缩"; }
                else if (c == "爪" || c == "翼" || c == "轮" || c == "扇") { hitReactionType = 4; reactionName = "四向旋转翻滚"; }
                else if (c == "锤" || c == "斧") { hitReactionType = 8; reactionName = "地震颠簸"; }
                else if (c == "炮" || c == "珠") { hitReactionType = 6; reactionName = "中心炸散复位"; }
                else { hitReactionType = 1; reactionName = "水平震退"; }
                return name;
            }
            else
            {
                // 1A: 动词(1) + 宾语(1) + 兵器/载体(1) = 3字 (如: 斩天剑、破魔刃、断魂枪)
                string a = MonoActions[_rand.Next(MonoActions.Count)];
                string o = MonoObjects[_rand.Next(MonoObjects.Count)];
                string c = MonoCarriers[_rand.Next(MonoCarriers.Count)];
                if (c == "盾" || c == "塔") c = "刃";
                string name = a + o + c;

                if (c == "枪" || c == "矛" || c == "弓" || c == "矢") { hitReactionType = 3; reactionName = "抛物线后仰"; }
                else if (c == "印") { hitReactionType = 7; reactionName = "手风琴压缩"; }
                else if (c == "轮" || c == "链" || c == "爪") { hitReactionType = 4; reactionName = "四向旋转翻滚"; }
                else if (c == "锤" || c == "斧") { hitReactionType = 8; reactionName = "地震颠簸"; }
                else if (c == "炮") { hitReactionType = 6; reactionName = "中心炸散复位"; }
                else if (c == "拳") { hitReactionType = 2; reactionName = "垂直击飞"; }
                else { hitReactionType = 1; reactionName = "水平震退"; }
                return name;
            }
        }

        public static string GenerateSixCharName(out int hitReactionType, out string reactionName)
        {
            hitReactionType = 1;
            reactionName = "水平震退";

            bool pickEpic = (_rand.Next(100) < 50);
            if (pickEpic && EpicVerbs.Count > 0 && EpicTargets.Count > 0 && EpicRelics.Count > 0)
            {
                // 范式 3：宏大长句诗意式 (2+2+2=6字，如: 撕裂天空之剑、贯穿星辰之枪、毁灭世界之矛)
                string ev = EpicVerbs[_rand.Next(EpicVerbs.Count)];
                string et = EpicTargets[_rand.Next(EpicTargets.Count)];
                string er = EpicRelics[_rand.Next(EpicRelics.Count)];
                if (er.Contains("盾") || er.Contains("铠")) er = "之矛";
                string name = ev + et + er;

                if (er.Contains("枪") || er.Contains("矛") || er.Contains("箭")) { hitReactionType = 3; reactionName = "抛物线后仰"; }
                else if (er.Contains("锁") || er.Contains("牢")) { hitReactionType = 7; reactionName = "手风琴压缩"; }
                else if (er.Contains("火") || er.Contains("光") || er.Contains("核")) { hitReactionType = 6; reactionName = "中心炸散复位"; }
                else if (er.Contains("锤") || er.Contains("息") || er.Contains("印")) { hitReactionType = 8; reactionName = "地震颠簸"; }
                else if (er.Contains("爪") || er.Contains("歌") || er.Contains("门")) { hitReactionType = 5; reactionName = "波浪状掀飞"; }
                else { hitReactionType = 1; reactionName = "水平震退"; }
                return name;
            }
            else if (ApexPrefixes.Count > 0 && ApexActions.Count > 0 && ApexFields.Count > 0)
            {
                // 范式 4：极境战技风暴式 (2+2+2=6字，如: 究极斩击风暴、极限连刺骤雨、苍穹坠击陨星)
                string ap = ApexPrefixes[_rand.Next(ApexPrefixes.Count)];
                string aa = ApexActions[_rand.Next(ApexActions.Count)];
                string af = ApexFields[_rand.Next(ApexFields.Count)];
                string name = ap + aa + af;

                if (af.Contains("风暴") || af.Contains("旋涡")) { hitReactionType = 4; reactionName = "四向旋转翻滚"; }
                else if (af.Contains("骤雨") || af.Contains("射线") || aa.Contains("刺")) { hitReactionType = 3; reactionName = "抛物线后仰"; }
                else if (af.Contains("爆轰") || af.Contains("陨星") || af.Contains("裂变") || af.Contains("火海")) { hitReactionType = 6; reactionName = "中心炸散复位"; }
                else if (af.Contains("冲击") || af.Contains("狂潮") || af.Contains("辉光") || af.Contains("狂澜")) { hitReactionType = 5; reactionName = "波浪状掀飞"; }
                else if (af.Contains("震荡") || af.Contains("怒涛") || af.Contains("怒炎") || af.Contains("暗涌")) { hitReactionType = 8; reactionName = "地震颠簸"; }
                else if (af.Contains("结界") || af.Contains("领域")) { hitReactionType = 7; reactionName = "手风琴压缩"; }
                else { hitReactionType = 1; reactionName = "水平震退"; }
                return name;
            }
            else if (EpicVerbs.Count > 0 && EpicTargets.Count > 0 && EpicRelics.Count > 0)
            {
                string ev = EpicVerbs[_rand.Next(EpicVerbs.Count)];
                string et = EpicTargets[_rand.Next(EpicTargets.Count)];
                string er = EpicRelics[_rand.Next(EpicRelics.Count)];
                return ev + et + er;
            }

            return "究极斩击风暴";
        }

        public static string GenerateFourCharName(string genre, out int hitReactionType, out string reactionName)
        {
            hitReactionType = 1;
            reactionName = "水平震退";

            AffixBank genreBank = GetBankByGenre(genre);

            List<string> pList = new List<string>();
            if (genreBank.Prefixes.Count > 0) pList.AddRange(genreBank.Prefixes);
            else if (Common.Prefixes.Count > 0) pList.AddRange(Common.Prefixes);

            List<string> sList = new List<string>();
            if (genreBank.Suffixes.Count > 0) sList.AddRange(genreBank.Suffixes);
            else if (Common.Suffixes.Count > 0) sList.AddRange(Common.Suffixes);

            if (pList.Count == 0 && sList.Count == 0) return "修罗崩击";
            if (pList.Count == 0) pList.Add("狂暴");
            if (sList.Count == 0) sList.Add("崩击");

            for (int retry = 0; retry < 25; retry++)
            {
                string p = pList[_rand.Next(pList.Count)];
                string rawS = sList[_rand.Next(sList.Count)];
                string s;
                TryParseSuffixHitReaction(rawS, out s, out hitReactionType, out reactionName);

                string res;
                if (s.Length == 1)
                {
                    // 2字前缀 + "之" + 1字后缀 = 4字 (如: 疾风之斩, 烈焰之击)
                    res = p + "之" + s;
                }
                else if (s.Length == 2)
                {
                    // 2字前缀 + 2字后缀 = 4字 (如: 修罗崩击, 以太脉冲)
                    res = p + s;
                }
                else
                {
                    res = p + s;
                }

                if (res.Length == 4 && !HasAwkwardOverlap(res))
                {
                    return res;
                }
            }

            // 兜底直接组合为4字
            string fbRawS = sList[_rand.Next(sList.Count)];
            string fbS;
            TryParseSuffixHitReaction(fbRawS, out fbS, out hitReactionType, out reactionName);
            string fallback = pList[_rand.Next(pList.Count)] + (fbS.Length == 1 ? ("之" + fbS) : fbS);
            return fallback;
        }

        private static bool HasAwkwardOverlap(string name)
        {
            if (string.IsNullOrEmpty(name)) return false;
            for (int i = 0; i < name.Length; i++)
            {
                for (int j = i + 1; j < name.Length; j++)
                {
                    if (name[i] == name[j]) return true;
                }
            }
            return false;
        }

        public static void ResetDefaults()
        {
            ConnectMode = 0;

            // 1. 通用词库
            Common.Prefixes = new List<string>(new string[] {
                "狂暴", "疾风", "烈焰", "冰霜", "雷霆", "暗影", "圣光", "虚空", "以太", "深渊",
                "晨曦", "拂晓", "星界", "混沌", "奥术", "时空", "末日", "极光", "破晓", "暴风",
                "黑铁", "秘银", "巨龙", "嗜血", "碎岩", "绝影", "双刀", "残暴", "苍穹", "纯白"
            });
            Common.Suffixes = new List<string>(new string[] {
                "斩", "刺", "击", "刃", "破", "裂", "射击", "重击", "穿刺", "撕裂",
                "爆破", "冲击", "连击", "狂袭", "裁决", "判决", "贯穿", "礼赞", "庇护", "苏生",
                "吞噬", "低语", "突袭", "逆流", "射线", "风暴", "猛击", "狂攻", "锁链", "回响"
            });

            // 2. 暴击流 (物理/暴击/兵刃)
            Havoc.Prefixes = new List<string>(new string[] {
                "突牙", "狂暴", "裂刃", "嗜血", "旋风", "猩红", "碎颅", "斩风", "龙枪", "强袭",
                "破甲", "断钢", "残暴", "双刀", "重刃", "狂战", "猛犸", "怒斩", "巨龙", "暗刃",
                "碎骨", "狮心", "屠龙", "烈刃", "崩岩", "铁拳", "疾刃", "战吼", "暴烈", "死狂", "狼牙"
            });
            Havoc.Suffixes = new List<string>(new string[] {
                "斩", "连击", "撕裂", "突刺", "重击", "狂袭", "乱舞", "破", "劈砍", "旋斩",
                "贯穿", "冲锋", "碎裂击", "猛击", "突击", "裂击", "横扫", "绝击", "狂击", "刃",
                "爪", "血", "角", "牙", "斧", "矛", "威", "怒啸", "咆哮", "狂斩"
            });

            // 3. 先机流 (迅捷/刺客/射手)
            Precision.Prefixes = new List<string>(new string[] {
                "要害", "破魔", "神圣", "圣光", "贯通", "鹰眼", "秘银", "审判", "真理", "极光",
                "银月", "穿心", "迅捷", "断法", "苍穹", "拂晓", "天罚", "巡林", "狙击", "银矢",
                "圣剑", "金羽", "猎手", "穿甲", "裁断", "定点", "星芒", "天界", "惩戒", "白银", "冷酷"
            });
            Precision.Suffixes = new List<string>(new string[] {
                "射击", "穿刺", "裁决", "判决", "重刺", "贯穿", "制裁", "直击", "连弩", "穿透",
                "狙杀", "圣决", "光矢", "疾刺", "贯杀", "破甲击", "刺击", "绝罚", "爆射", "锐击",
                "之击", "神剑", "之矛", "之箭", "之光", "之矢", "之枪", "之眼", "之刃", "之准星"
            });

            // 4. 恢复流 (恢复/神术/生命)
            Tenacity.Prefixes = new List<string>(new string[] {
                "恩赐", "生命", "神圣", "圣佑", "晨曦", "天使", "祈愿", "治愈", "光辉", "纯白",
                "灵泉", "守望", "圣灵", "翡翠", "愈合", "圣盾", "大教堂", "白银", "神恩", "慈悲",
                "圣殿", "庇护", "复苏", "救赎", "甘霖", "大地", "圣歌", "坚韧", "纯洁", "暖阳"
            });
            Tenacity.Suffixes = new List<string>(new string[] {
                "礼赞", "祈福", "庇护", "之拥", "苏生", "甘霖", "祝祷", "治愈", "福音", "圣印",
                "灵光", "洗礼", "恩泽", "圣环", "守护", "之誓", "回响", "治愈术", "圣域", "之泉",
                "之翼", "之盾", "之光", "之泪", "之印", "之辉", "之歌", "之甘霖", "之结界", "之庇佑"
            });

            // 5. 机制流 (奥术/虚空/反噬)
            Utility.Prefixes = new List<string>(new string[] {
                "以太", "虚空", "暗影", "深渊", "魔化", "时空", "奥术", "混沌", "厄运", "灵魂",
                "末日", "星界", "狡黠", "蚀心", "冥界", "暗夜", "镜像", "裂隙", "幻影", "诡术",
                "死灵", "禁忌", "黑巫", "灾厄", "秘法", "幽暗", "命运", "黑炎", "蚀骨", "巫毒", "夜色", "维度"
            });
            Utility.Suffixes = new List<string>(new string[] {
                "爆破", "射线", "吞噬", "冲击", "窃取", "封印", "凝视", "逆流", "低语", "缠绕",
                "回响", "枷锁", "反噬", "突袭", "陷阱", "侵蚀", "突击", "风暴", "撕裂", "汲取",
                "湮灭", "折跃", "之噬", "之触", "之握", "之影", "之锁", "之眼", "之潮", "之歌", "之痕", "之契约"
            });

            SaveToFile();
        }

        public static void SaveToFile()
        {
            try
            {
                StringBuilder sb = new StringBuilder();
                sb.AppendLine("# ========================================================");
                sb.AppendLine("# 战团技能前后字段自定义词库配置文件 (skill_affixes.txt)");
                sb.AppendLine("# 格式说明：每个小节以 [节名] 开头，下方每行一个词条。");
                sb.AppendLine("# 用户可直接在游戏中工具界面编辑保存，也可直接在此文本文件中编辑！");
                sb.AppendLine("# ========================================================");
                sb.AppendLine();

                sb.AppendLine("[ConnectMode]");
                sb.AppendLine(ConnectMode.ToString());
                sb.AppendLine();

                WriteSection(sb, "Common_Prefixes", Common.Prefixes);
                WriteSection(sb, "Common_Suffixes", Common.Suffixes);

                WriteSection(sb, "Courage_Prefixes", Havoc.Prefixes);
                WriteSection(sb, "Courage_Suffixes", Havoc.Suffixes);

                WriteSection(sb, "Initiative_Prefixes", Precision.Prefixes);
                WriteSection(sb, "Initiative_Suffixes", Precision.Suffixes);

                WriteSection(sb, "Resilience_Prefixes", Tenacity.Prefixes);
                WriteSection(sb, "Resilience_Suffixes", Tenacity.Suffixes);

                WriteSection(sb, "Magic_Prefixes", Utility.Prefixes);
                WriteSection(sb, "Magic_Suffixes", Utility.Suffixes);

                WriteSection(sb, "Mono_Actions", MonoActions);
                WriteSection(sb, "Mono_Objects", MonoObjects);
                WriteSection(sb, "Mono_Carriers", MonoCarriers);
                WriteSection(sb, "Mono_Modifiers", MonoModifiers);
                WriteSection(sb, "Mono_Beasts", MonoBeasts);

                WriteSection(sb, "Epic_Verbs", EpicVerbs);
                WriteSection(sb, "Epic_Targets", EpicTargets);
                WriteSection(sb, "Epic_Relics", EpicRelics);

                WriteSection(sb, "Apex_Prefixes", ApexPrefixes);
                WriteSection(sb, "Apex_Actions", ApexActions);
                WriteSection(sb, "Apex_Fields", ApexFields);

                File.WriteAllText(ConfigFilePath, sb.ToString(), new UTF8Encoding(false));
            }
            catch { }
        }

        private static void WriteSection(StringBuilder sb, string sectionName, List<string> words)
        {
            sb.AppendLine("[" + sectionName + "]");
            foreach (var w in words)
            {
                if (!string.IsNullOrEmpty(w)) sb.AppendLine(w.Trim());
            }
            sb.AppendLine();
        }

        public static void LoadFromFile()
        {
            try
            {
                string[] lines = File.ReadAllLines(ConfigFilePath, Encoding.UTF8);
                string currentSection = "";

                Common.Prefixes.Clear(); Common.Suffixes.Clear();
                Havoc.Prefixes.Clear(); Havoc.Suffixes.Clear();
                Precision.Prefixes.Clear(); Precision.Suffixes.Clear();
                Tenacity.Prefixes.Clear(); Tenacity.Suffixes.Clear();
                Utility.Prefixes.Clear(); Utility.Suffixes.Clear();
                MonoActions.Clear(); MonoObjects.Clear(); MonoCarriers.Clear();
                MonoModifiers.Clear(); MonoBeasts.Clear();
                EpicVerbs.Clear(); EpicTargets.Clear(); EpicRelics.Clear();
                ApexPrefixes.Clear(); ApexActions.Clear(); ApexFields.Clear();

                foreach (var rawLine in lines)
                {
                    string line = rawLine.Trim();
                    if (string.IsNullOrEmpty(line) || line.StartsWith("#")) continue;

                    if (line.StartsWith("[") && line.EndsWith("]"))
                    {
                        currentSection = line.Substring(1, line.Length - 2);
                        continue;
                    }

                    if (currentSection == "ConnectMode")
                    {
                        int mode;
                        if (int.TryParse(line, out mode)) ConnectMode = mode;
                    }
                    else if (currentSection == "Common_Prefixes") Common.Prefixes.Add(line);
                    else if (currentSection == "Common_Suffixes") Common.Suffixes.Add(line);
                    else if (currentSection == "Havoc_Prefixes" || currentSection == "Courage_Prefixes") Havoc.Prefixes.Add(line);
                    else if (currentSection == "Havoc_Suffixes" || currentSection == "Courage_Suffixes") Havoc.Suffixes.Add(line);
                    else if (currentSection == "Precision_Prefixes" || currentSection == "Initiative_Prefixes") Precision.Prefixes.Add(line);
                    else if (currentSection == "Precision_Suffixes" || currentSection == "Initiative_Suffixes") Precision.Suffixes.Add(line);
                    else if (currentSection == "Tenacity_Prefixes" || currentSection == "Resilience_Prefixes") Tenacity.Prefixes.Add(line);
                    else if (currentSection == "Tenacity_Suffixes" || currentSection == "Resilience_Suffixes") Tenacity.Suffixes.Add(line);
                    else if (currentSection == "Utility_Prefixes" || currentSection == "Magic_Prefixes") Utility.Prefixes.Add(line);
                    else if (currentSection == "Utility_Suffixes" || currentSection == "Magic_Suffixes") Utility.Suffixes.Add(line);
                    else if (currentSection == "Mono_Actions") MonoActions.Add(line);
                    else if (currentSection == "Mono_Objects") MonoObjects.Add(line);
                    else if (currentSection == "Mono_Carriers") MonoCarriers.Add(line);
                    else if (currentSection == "Mono_Modifiers") MonoModifiers.Add(line);
                    else if (currentSection == "Mono_Beasts") MonoBeasts.Add(line);
                    else if (currentSection == "Epic_Verbs") EpicVerbs.Add(line);
                    else if (currentSection == "Epic_Targets") EpicTargets.Add(line);
                    else if (currentSection == "Epic_Relics") EpicRelics.Add(line);
                    else if (currentSection == "Apex_Prefixes") ApexPrefixes.Add(line);
                    else if (currentSection == "Apex_Actions") ApexActions.Add(line);
                    else if (currentSection == "Apex_Fields") ApexFields.Add(line);
                }
            }
            catch
            {
                ResetDefaults();
            }
        }
    }

    #endregion

    public static class GeneratorEngine
    {
        private static Random _rand = new Random();

        public static SkillRecord Generate(int chosenTier, int newId)
        {
            return Generate(chosenTier, "", newId);
        }

        public static SkillRecord Generate(int chosenTier, string chosenGenre = "", int newId = 0)
        {
            // 1. 确定阶位 T1 ~ T6
            int tier = chosenTier;
            if (tier <= 0 || tier > 6)
            {
                // 纺锤钻石分布随机
                int roll = _rand.Next(1, 101);
                if (roll <= 10) tier = 1;
                else if (roll <= 20) tier = 2;
                else if (roll <= 35) tier = 3;
                else if (roll <= 60) tier = 4;
                else if (roll <= 85) tier = 5;
                else tier = 6;
            }

            string tierName = GetTierName(tier);

            // 2. 确定技能类型 (勇气、坚韧、先机、魔力)
            string[] genres = new string[] { "勇气", "坚韧", "先机", "魔力" };
            string genre = "";
            if (!string.IsNullOrEmpty(chosenGenre))
            {
                if (chosenGenre.Contains("勇气") || chosenGenre.Contains("暴击")) genre = "勇气";
                else if (chosenGenre.Contains("先机") || chosenGenre.Contains("精准")) genre = "先机";
                else if (chosenGenre.Contains("坚韧") || chosenGenre.Contains("恢复")) genre = "坚韧";
                else if (chosenGenre.Contains("魔力") || chosenGenre.Contains("机制")) genre = "魔力";
                else genre = chosenGenre;
            }
            else
            {
                genre = genres[_rand.Next(genres.Length)];
            }

            // 3. 基础强度预算 W
            float budget = GetTierBudget(tier);

            // 4. 判定是否有额外效果 (根据稀有度梯队，T1 技能没有特效)
            float subEffectChance = (tier == 1) ? 0f : GetSubEffectChance(tier);
            bool hasSubEffect = (_rand.NextDouble() < subEffectChance);
            // 坚韧类保底携带回血效果
            if (genre == "坚韧") hasSubEffect = true;

            // 5. 纯净补偿逻辑：若高阶角色未抽中额外效果，启动预算返还
            bool isCompensated = false;
            float compParamBonus = 0f;
            float compChanceBonus = 0f;
            int compTimesBonus = 0;

            if (!hasSubEffect && tier >= 3)
            {
                isCompensated = true;
                float refundFactor = (tier == 3) ? 0.20f : (tier == 4 ? 0.30f : (tier == 5 ? 0.40f : 0.50f));
                compParamBonus = budget * refundFactor * 1.5f;   // 增加倍率
                compChanceBonus = budget * refundFactor * 0.12f; // 增加几率
                if (tier >= 5 && _rand.Next(100) < 60)
                {
                    compTimesBonus = 1; // 放宽1次
                }
            }

            // 6. 抽取倍率与概率 (正态分布与反向联动)
            float baseParamMin, baseParamMax, baseParamMean;
            GetParamRange(genre, tier, isCompensated, compParamBonus, out baseParamMin, out baseParamMax, out baseParamMean);
            float baseParam = SampleNormalClamped(baseParamMean, (baseParamMax - baseParamMin) * 0.18f, baseParamMin, baseParamMax);
            baseParam = (float)Math.Round(baseParam, 0);

            // 先机/精准伤害极限硬顶 200%，暴击流极限硬顶 350%
            if ((genre.Contains("精准") || genre.Contains("先机")) && baseParam > 200f) baseParam = 200f;
            if ((genre.Contains("暴击") || genre.Contains("勇气")) && baseParam > 350f) baseParam = 350f;

            float chanceMin, chanceMax, chanceMean;
            GetChanceRange(genre, tier, baseParam, budget, isCompensated, compChanceBonus, out chanceMin, out chanceMax, out chanceMean);
            float triggerChance = SampleNormalClamped(chanceMean, (chanceMax - chanceMin) * 0.20f, chanceMin, chanceMax);
            triggerChance = (float)Math.Round(triggerChance, 0);

            // 暴击技能自带暴击率
            int baseCrit = (genre == "勇气" || genre.Contains("暴击")) ? (15 + tier * 2) : 0;

            // 先机技能增加先机等级 (最低1先机，不占特效栏位)
            int iniBonus = 0;
            if (genre == "先机" || genre.Contains("精准"))
            {
                switch (tier)
                {
                    case 1: iniBonus = 1; break;
                    case 2: iniBonus = 2; break;
                    case 3: iniBonus = 3; break;
                    case 4: iniBonus = 5; break;
                    case 5: iniBonus = 7; break;
                    case 6: iniBonus = 10; break;
                    default: iniBonus = 1; break;
                }
            }

            // 魔力技能无视目标防御百分比 (不占特效栏位，随阶位递增)
            int ignoreDefPercent = GetIgnoreDefPercent(tier);

            // 7. 抽取附加效果 (T1 不抽取任何附加效果)
            string subEffectName = "", subCategory = "", subDesc = "", subCsvFields = "", subUnit = "";
            int subChance = 0;
            float subParam = 0f;
            if (hasSubEffect && tier >= 2)
            {
                GenerateSubEffect(genre, tier, out subEffectName, out subCategory, out subDesc, out subCsvFields, out subChance, out subParam, out subUnit);
            }
            else if (genre == "坚韧" || genre.Contains("恢复"))
            {
                // T1 坚韧类保底拥有基础总战力恢复
                subEffectName = "总战力恢复";
                subCategory = "战力治疗";
                subParam = 4f;
                subUnit = "%";
                subDesc = "恢复己方总战力4%";
                hasSubEffect = true;
            }

            // 8. 判定启动条件
            bool hasRage = (hasSubEffect && subEffectName == "自身已损反噬");
            int turnCond1, turnCond2, selfBpCond2;
            DetermineConditions(genre, tier, baseParam, hasRage, out turnCond1, out turnCond2, out selfBpCond2);

            // 9. 判定次数限制 (低阶不限制或很多次，高阶核弹限1次)
            int timesLimit = DetermineTimesLimit(genre, tier, baseParam, triggerChance, isCompensated, compTimesBonus);

            // 10. 四维属性投放与流派绑定 (勇气、坚韧、先机、魔力)
            int totalStatBudget = GetStatBudget(tier);
            int couragePoint, resiliencePoint, initiativePoint, magicPoint;
            AllocateStats(genre, totalStatBudget, out couragePoint, out resiliencePoint, out initiativePoint, out magicPoint);

            // 11. 羁绊槽位与稀有度预算
            int baseSynergySlots = 2; // 种族 + 职业
            int extraSynergySlots = (tier <= 3) ? 0 : (tier == 4 ? 1 : 2);
            int totalSynergySlots = baseSynergySlots + extraSynergySlots;
            int synergyBudget = GetSynergyBudget(tier);
            int slot1Tier = 0, slot2Tier = 0;
            if (extraSynergySlots >= 1)
            {
                slot1Tier = Math.Min(5, Math.Max(1, (int)Math.Round(SampleNormalClamped(tier - 1, 0.8f, 1, 5))));
                if (extraSynergySlots >= 2)
                {
                    int remain = synergyBudget - slot1Tier;
                    slot2Tier = Math.Min(5, Math.Max(1, remain));
                }
            }

            // 12. 严格从用户配置的前后字段中按阶位构词规则抽取并组合技能名称
            int hitReactionType;
            string reactionName;
            string skillName = AffixManager.GenerateRandomName(genre, tier, out hitReactionType, out reactionName);

            // 12.5 根据技能前缀(决定颜色与元素) + 后缀/载体(决定特效种类) 匹配高精像素特效与受击物理反馈 (1~10)
            int matchedAnimId;
            string matchedEffectCn;
            string matchedEffectFolder;
            string matchedEffectCategory;
            SkillEffectMatcher.ResolveSkillEffect(
                skillName,
                genre,
                tier,
                hasSubEffect ? subEffectName : "",
                out matchedAnimId,
                out matchedEffectCn,
                out matchedEffectFolder,
                out matchedEffectCategory,
                out hitReactionType,
                out reactionName);

            // 13. 组装自然语言技能描述
            string effectText = BuildEffectText(genre, triggerChance, baseParam, timesLimit, turnCond1, turnCond2, selfBpCond2, hasSubEffect, subDesc, iniBonus, ignoreDefPercent);

            // 14. 组装输出文本与实体记录 (清爽纯净，不输出底层CSV代码)
            SkillRecord record = new SkillRecord();
            record.TierName = tierName;
            record.SkillName = skillName;
            record.EffectDesc = effectText;
            record.HitReactionType = hitReactionType;
            record.HitReactionName = reactionName;
            record.AnimationId = matchedAnimId;
            record.EffectCnName = matchedEffectCn;
            record.EffectFolder = matchedEffectFolder;
            record.EffectCategory = matchedEffectCategory;

            StringBuilder sbSum = new StringBuilder();
            sbSum.AppendLine(string.Format("稀有度:   {0}", tierName));
            sbSum.AppendLine(string.Format("技能类型: {0}", genre));
            sbSum.AppendLine(string.Format("技能名字: 《{0}》", skillName));
            sbSum.AppendLine(string.Format("技能效果: {0}", effectText));
            sbSum.AppendLine(string.Format("绑定特效: [{0}] {1} ({2}) | 受击效果: [{3}]{4}", matchedAnimId, matchedEffectCn, matchedEffectCategory, hitReactionType, reactionName));
            record.SummaryText = sbSum.ToString();

            StringBuilder sbDet = new StringBuilder();
            sbDet.AppendLine(string.Format("1. 基础定位与总预算:"));
            sbDet.AppendLine(string.Format("   - 稀有度:   {0}", tierName));
            sbDet.AppendLine(string.Format("   - 技能类型: {0}", genre));
            sbDet.AppendLine(string.Format("   - 综合强度预算池 (W): {0:F1}", budget));
            sbDet.AppendLine();

            sbDet.AppendLine(string.Format("2. 技能核心数值与机制分析:"));
            sbDet.AppendLine(string.Format("   - 主伤害/回复倍率: {0}% | [区间: {1}% ~ {2}%, 均值: {3}%]", baseParam, baseParamMin, baseParamMax, baseParamMean));
            sbDet.AppendLine(string.Format("   - 发动概率: {0}% | [区间: {1}% ~ {2}%, 均值: {3}%]", triggerChance, chanceMin, chanceMax, chanceMean));
            sbDet.AppendLine(string.Format("   - 释放次数限制: {0}", (timesLimit == 0 ? "无限制" : timesLimit.ToString() + " 次")));
            sbDet.AppendLine(string.Format("   - 回合生效条件: {0}", FormatTurnCondDesc(turnCond1, turnCond2)));
            sbDet.AppendLine(string.Format("   - 战力生效门槛: {0}", (selfBpCond2 > 0 ? string.Format("己方战力低于 {0}% 时生效", selfBpCond2) : "无门槛")));
            sbDet.AppendLine();

            sbDet.AppendLine(string.Format("3. 附加效果与机制解析:"));
            if (hasSubEffect)
            {
                sbDet.AppendLine(string.Format("   - 效果类型: {0} [{1}]", subEffectName, subCategory));
                sbDet.AppendLine(string.Format("   - 效果描述: {0}", subDesc));
                sbDet.AppendLine(string.Format("   - 效果数值: {0}{1}", (int)subParam, subUnit));
            }
            else if (isCompensated)
            {
                sbDet.AppendLine(string.Format("   - 纯净补偿状态: 已激活！高阶角色未携带附加效果，基础倍率与概率全额返还"));
                sbDet.AppendLine(string.Format("   - 补偿增量: 主倍率 +{0:F0}%, 发动概率 +{1:F0}%, 次数 +{2}次", compParamBonus, compChanceBonus, compTimesBonus));
            }
            else
            {
                sbDet.AppendLine(string.Format("   - 基础技能: 低阶常规技能"));
            }
            sbDet.AppendLine();

            sbDet.AppendLine(string.Format("4. 四维属性投放倾向:"));
            sbDet.AppendLine(string.Format("   - 勇气: +{0} 点 | 坚韧: +{1} 点 | 先机: +{2} 点 | 魔力: +{3} 点", couragePoint, resiliencePoint, initiativePoint, magicPoint));
            sbDet.AppendLine();

            sbDet.AppendLine(string.Format("5. 羁绊槽位与稀有度预算扣减:"));
            sbDet.AppendLine(string.Format("   - 羁绊总槽位: {0} 个 (基础2个[种族+职业] + 额外解锁{1}个)", totalSynergySlots, extraSynergySlots));
            if (extraSynergySlots > 0)
            {
                sbDet.AppendLine(string.Format("   - 羁绊总预算分: {0} 分", synergyBudget));
                sbDet.AppendLine(string.Format("   - 额外槽位 1 稀有度: {0} 阶 (享受高阶正向抽取加成)", slot1Tier));
                if (extraSynergySlots >= 2)
                {
                    sbDet.AppendLine(string.Format("   - 额外槽位 2 稀有度: {0} 阶 (受总预算约束反向扣减降级)", slot2Tier));
                }
            }
            else
            {
                sbDet.AppendLine(string.Format("   - 额外槽位: 未解锁 (低阶角色仅有基础职业/种族标签)"));
            }
            sbDet.AppendLine();

            sbDet.AppendLine(string.Format("6. 像素特效高精适配 (前缀定色+后缀定型):"));
            sbDet.AppendLine(string.Format("   - 动画 ID (animation_id): {0}", matchedAnimId));
            sbDet.AppendLine(string.Format("   - 中文特征命名: {0} [{1}]", matchedEffectCn, matchedEffectCategory));
            sbDet.AppendLine(string.Format("   - 精灵表文件夹: {0} | 受击物理反馈: {1}", matchedEffectFolder, reactionName));

            record.DetailText = sbDet.ToString();

            // 15. 填充 35 个技术列 CSV 映射 (完整契合 active_skill.csv)
            record.CsvData["ID"] = newId > 0 ? newId.ToString() : "";
            record.CsvData["name"] = skillName;
            record.CsvData["desc"] = effectText;
            record.CsvData["turn_cond1"] = turnCond1 > 0 ? turnCond1.ToString() : "";
            record.CsvData["turn_cond2"] = turnCond2 > 0 ? turnCond2.ToString() : "";
            record.CsvData["self_bp_cond1"] = "";
            record.CsvData["self_bp_cond2"] = selfBpCond2 > 0 ? selfBpCond2.ToString() : "";
            record.CsvData["enemy_bp_cond1"] = "";
            record.CsvData["enemy_bp_cond2"] = "";
            record.CsvData["turn_cond3"] = "";
            record.CsvData["cur_bp_cond"] = "";
            record.CsvData["trigger_chance"] = ((int)triggerChance).ToString();
            record.CsvData["times_limit"] = timesLimit > 0 ? timesLimit.ToString() : "999";

            string effTypeStr = "1";
            if (genre == "勇气" || genre.Contains("暴击")) effTypeStr = "2";
            else if (genre == "先机" || genre.Contains("精准")) effTypeStr = "13";
            else if (genre == "坚韧" || genre.Contains("恢复")) effTypeStr = "10";
            record.CsvData["effect_type"] = effTypeStr;

            record.CsvData["param"] = ((int)baseParam).ToString();
            record.CsvData["param2"] = (hasSubEffect && subUnit == "%" && (subEffectName.Contains("反噬") || subEffectName.Contains("吸收"))) ? ((int)subParam).ToString() : "";
            record.CsvData["need_hit"] = "1";

            string selfProp = "";
            string enemyProp = "";
            string turnFixed = "";
            string exhaustTurn = "";
            string sealTurnEffect = "";
            string sealTurnVal = "";
            string sealCond2 = "";
            string bufferId = "";

            if (hasSubEffect)
            {
                if (subEffectName == "防御提升") selfProp = string.Format("0|{0}|0|0", (int)subParam);
                else if (subEffectName == "王者提升") selfProp = string.Format("0|0|0|{0}", (int)subParam);
                else if (subEffectName == "闪避提升") selfProp = string.Format("0|0|{0}|0", (int)subParam);
                else if (subEffectName == "先攻提升") selfProp = string.Format("{0}|0|0|0", (int)subParam);

                else if (subEffectName == "防御削弱") enemyProp = string.Format("0|-{0}|0|0", (int)subParam);
                else if (subEffectName == "王者削弱") enemyProp = string.Format("0|0|0|-{0}", (int)subParam);
                else if (subEffectName == "闪避削弱") enemyProp = string.Format("0|0|-{0}|0", (int)subParam);

                else if (subEffectName == "回合延展") turnFixed = string.Format("+{0}", (int)subParam);
                else if (subEffectName == "回合缩减") turnFixed = string.Format("-{0}", (int)subParam);

                else if (subEffectName == "虚弱压制") exhaustTurn = "1";

                else if (subEffectName == "封印暴击") { sealTurnEffect = "2"; sealTurnVal = (tier <= 3 ? "1" : (tier == 4 ? "2" : "3")); }
                else if (subEffectName == "封印恢复") { sealTurnEffect = "10"; sealTurnVal = (tier <= 3 ? "1" : (tier == 4 ? "2" : "3")); }
                else if (subEffectName == "封印先机") { sealTurnEffect = "13"; sealTurnVal = (tier <= 3 ? "1" : (tier == 4 ? "2" : "3")); }
                else if (subEffectName == "绝招封印") { sealTurnVal = (tier <= 3 ? "1" : (tier == 4 ? "2" : "3")); sealCond2 = ((int)subParam).ToString(); }
                else if (subEffectName == "全技能封印") { sealTurnVal = (tier <= 3 ? "1" : (tier == 4 ? "2" : "3")); sealCond2 = "101"; }

                else if (subEffectName == "流血伤害") bufferId = "10";
                else if (subEffectName == "重伤减疗") bufferId = "13";
                else if (subEffectName == "减伤虚弱") bufferId = "17";
                else if (subEffectName == "中毒伤害") bufferId = "7";
            }

            record.CsvData["self_property"] = selfProp;
            record.CsvData["enemy_property"] = enemyProp;
            record.CsvData["turn_fixed"] = turnFixed;
            record.CsvData["exhaust_turn"] = exhaustTurn;
            record.CsvData["ignore_dodge"] = "0";
            record.CsvData["ignore_defense"] = (genre.Contains("魔力") ? "1" : "0");
            record.CsvData["seal_turneffect"] = sealTurnEffect;
            record.CsvData["seal_turn"] = sealTurnVal;
            record.CsvData["seal_cond1"] = "";
            record.CsvData["seal_cond2"] = sealCond2;
            record.CsvData["animation_id"] = matchedAnimId.ToString();

            record.CsvData["speed"] = initiativePoint.ToString();     // 先机
            record.CsvData["defense"] = resiliencePoint.ToString();   // 坚韧
            record.CsvData["dodge"] = couragePoint.ToString();        // 勇气
            record.CsvData["authority"] = magicPoint.ToString();      // 魔力
            record.CsvData["buffer_id"] = bufferId;
            record.CsvData["buffer_id2"] = "";
            record.CsvData["buffer_id3"] = "";

            return record;
        }

        public static string GetTierName(int tier)
        {
            switch (tier)
            {
                case 1: return "T1";
                case 2: return "T2";
                case 3: return "T3";
                case 4: return "T4";
                case 5: return "T5";
                case 6: return "T6";
                default: return "T4";
            }
        }

        private static string GetGenreEffectType(string genre)
        {
            if (genre == "勇气") return "2 (critical_damage / 暴击伤害)";
            if (genre == "先机") return "13 (initiative_damage / 先机伤害)";
            if (genre == "坚韧") return "10 (heal_bp / 坚韧战力恢复)";
            if (genre == "魔力") return "1 (magic_damage / 魔力直伤)";
            return "1 (melee_damage / 普通伤害)";
        }

        private static float GetTierBudget(int tier)
        {
            switch (tier)
            {
                case 1: return 18f;
                case 2: return 24f;
                case 3: return 32f;
                case 4: return 48f;
                case 5: return 68f;
                case 6: return 92f;
                default: return 40f;
            }
        }

        private static float GetSubEffectChance(int tier)
        {
            switch (tier)
            {
                case 1: return 0.00f;
                case 2: return 0.15f;
                case 3: return 0.35f;
                case 4: return 0.60f;
                case 5: return 0.75f;
                case 6: return 0.85f;
                default: return 0.50f;
            }
        }

        private static void GetParamRange(string genre, int tier, bool isCompensated, float compBonus, out float min, out float max, out float mean)
        {
            int idx = Math.Max(0, Math.Min(5, tier - 1));

            if (genre.Contains("暴击") || genre.Contains("勇气"))
            {
                float[] mins = { 130f, 150f, 180f, 210f, 250f, 300f };
                float[] maxs = { 150f, 180f, 220f, 260f, 310f, 350f };
                min = mins[idx];
                max = maxs[idx];
                mean = (min + max) * 0.5f;
                if (isCompensated)
                {
                    min = Math.Min(340f, min + 30f);
                    max = Math.Min(350f, max + 40f);
                    mean = Math.Min(350f, mean + compBonus * 0.45f);
                }
            }
            else if (genre.Contains("精准") || genre.Contains("先机"))
            {
                float[] mins = { 120f, 130f, 140f, 145f, 150f, 160f };
                float[] maxs = { 135f, 145f, 155f, 160f, 175f, 190f };
                min = mins[idx];
                max = maxs[idx];
                mean = (min + max) * 0.5f;
                if (isCompensated)
                {
                    min += compBonus * 0.20f;
                    max += compBonus * 0.35f;
                    if (max > 200f) max = 200f;
                    if (min > 190f) min = 190f;
                    mean = (min + max) * 0.5f;
                }
            }
            else if (genre.Contains("恢复") || genre.Contains("坚韧"))
            {
                min = 100f;
                max = 100f;
                mean = 100f;
            }
            else // 机制流 / 魔力流
            {
                float[] mins = { 100f, 105f, 110f, 115f, 120f, 125f };
                float[] maxs = { 115f, 120f, 125f, 130f, 135f, 145f };
                min = mins[idx];
                max = maxs[idx];
                mean = (min + max) * 0.5f;
                if (isCompensated)
                {
                    min += compBonus * 0.25f;
                    max += compBonus * 0.50f;
                    mean += compBonus * 0.35f;
                }
            }
        }

        private static void GetChanceRange(string genre, int tier, float param, float budget, bool isCompensated, float compChanceBonus, out float min, out float max, out float mean)
        {
            float effectiveWeight = param;
            if (genre.Contains("恢复") || genre.Contains("坚韧"))
            {
                effectiveWeight = param * 5.5f;
            }
            else if (genre.Contains("机制") || genre.Contains("魔力"))
            {
                effectiveWeight = param * 0.65f;
            }

            float baseChance = (budget / effectiveWeight) * 100f;
            if (genre.Contains("精准") || genre.Contains("先机")) baseChance *= 1.10f;
            if (isCompensated) baseChance += compChanceBonus;

            // T1、T2 专属发动率按比例上调：T1 加 60% (x1.60 原概率)，T2 加 40% (x1.40 原概率)
            float tierChanceScale = 1.0f;
            if (tier == 1) tierChanceScale = 1.60f;
            else if (tier == 2) tierChanceScale = 1.40f;

            baseChance *= tierChanceScale;

            mean = (float)Math.Round(baseChance, 1);

            float hardMin = 8f;
            float hardMax = 38f;
            if (genre.Contains("精准") || genre.Contains("先机")) { hardMin = 15f; hardMax = 42f; }
            if (genre.Contains("暴击") || genre.Contains("勇气")) { hardMin = 12f; hardMax = 36f; }
            if (genre.Contains("恢复") || genre.Contains("坚韧")) { hardMin = 15f; hardMax = 38f; }
            if (genre.Contains("机制") || genre.Contains("魔力")) { hardMin = 12f; hardMax = 38f; }

            // 上下限阈值按比例同步上浮，防止被旧硬性上限截断
            if (tierChanceScale > 1.0f)
            {
                hardMin = (float)Math.Round(hardMin * tierChanceScale, 1);
                hardMax = (float)Math.Round(hardMax * tierChanceScale, 1);
            }

            if (mean < hardMin) mean = hardMin;
            if (mean > hardMax) mean = hardMax;

            min = Math.Max(hardMin, (float)Math.Round(mean * 0.75f, 1));
            max = Math.Min(hardMax, (float)Math.Round(mean * 1.25f, 1));

            if (min > max) { float t = min; min = max; max = t; }
        }

        private static void DetermineConditions(string genre, int tier, float param, bool hasRage, out int turnCond1, out int turnCond2, out int selfBpCond2)
        {
            turnCond1 = 0;
            turnCond2 = 0;
            selfBpCond2 = 0;

            if (hasRage)
            {
                selfBpCond2 = 50;
                if (tier >= 5) turnCond1 = 1; // 第2回合起方可发动
                return;
            }

            if (genre.Contains("恢复") || genre.Contains("坚韧"))
            {
                if (tier <= 2) selfBpCond2 = 80;
                else if (tier <= 4) selfBpCond2 = 70;
                else selfBpCond2 = 50;

                if (tier >= 5) turnCond1 = 1; // 第2回合起方可发动
                return;
            }

            // 勇气流高倍率爆发 (280%+) 附带残血限制
            if ((genre.Contains("暴击") || genre.Contains("勇气")) && param >= 280f)
            {
                selfBpCond2 = 50;
                if (tier >= 5) turnCond1 = 1;
                return;
            }

            int roll = _rand.Next(100);
            if (roll < 20)
            {
                if (tier <= 3) selfBpCond2 = 50;
                else if (tier <= 5) selfBpCond2 = 40;
                else selfBpCond2 = 30;
            }
        }

        private static string FormatTurnCondDesc(int t1, int t2)
        {
            if (t1 == 0 && t2 == 0) return "无回合限制 (入场即可发动)";
            if (t1 > 0 && t2 > 0) return string.Format("仅在第 {0} 至 {1} 回合期间可用", t1 + 1, t2);
            if (t1 > 0) return string.Format("第 {0} 回合起方可发动 (turn > {1})", t1 + 1, t1);
            return string.Format("仅前 {0} 回合内有效 (turn < {0})", t2);
        }

        private static int DetermineTimesLimit(string genre, int tier, float param, float chance, bool isCompensated, int compTimesBonus)
        {
            if (tier <= 2) return 0;
            if (tier == 3)
            {
                if (genre.Contains("恢复") || genre.Contains("坚韧")) return 3 + compTimesBonus;
                if (param >= 200f) return 4 + compTimesBonus;
                return 0;
            }
            else if (tier == 4)
            {
                if (genre.Contains("恢复") || genre.Contains("坚韧")) return 2 + compTimesBonus;
                if (param >= 240f) return 2 + compTimesBonus;
                if (genre.Contains("精准") || genre.Contains("先机")) return 0;
                return 3 + compTimesBonus;
            }
            else if (tier == 5)
            {
                if (genre.Contains("恢复") || genre.Contains("坚韧")) return 1;
                if (genre.Contains("精准") || genre.Contains("先机"))
                {
                    if (param >= 165f || isCompensated) return Math.Max(1, 2 + compTimesBonus);
                    return 0;
                }
                if (param >= 280f) return Math.Max(1, 1 + compTimesBonus);
                return Math.Max(1, 2 + compTimesBonus);
            }
            else // T6
            {
                if (genre.Contains("恢复") || genre.Contains("坚韧")) return 1;
                if (genre.Contains("精准") || genre.Contains("先机"))
                {
                    if (param >= 175f || isCompensated) return 1;
                    return 2;
                }
                if (param >= 300f) return 1; // 极限核弹斩杀限1次
                return Math.Max(1, 1 + (compTimesBonus > 0 ? 1 : 0));
            }
        }

        private static void GenerateSubEffect(string genre, int tier, out string name, out string category, out string desc, out string csvFields, out int chance, out float param, out string unit)
        {
            List<SubEffectMeta> allEffects = new List<SubEffectMeta>();

            if (genre == "勇气" || genre.Contains("暴击"))
            {
                allEffects.Add(new SubEffectMeta("自身已损反噬", "百分比反噬", "附带自身已损失战力{0}%伤害", "", new float[] { 8f, 11f, 15f, 20f, 26f, 35f }, 100, 100, "%", 2));
                allEffects.Add(new SubEffectMeta("敌方当前压制", "百分比反噬", "附带敌方当前战力{0}%伤害", "", new float[] { 3f, 4f, 5f, 7f, 9f, 12f }, 100, 100, "%", 2));
                allEffects.Add(new SubEffectMeta("敌方已损斩杀", "百分比反噬", "附带敌方已损失战力{0}%伤害", "", new float[] { 5f, 7f, 10f, 14f, 18f, 24f }, 100, 100, "%", 2));
            }
            else if (genre == "先机" || genre.Contains("精准"))
            {
                allEffects.Add(new SubEffectMeta("四维削弱", "属性弱化", "降低目标所有属性{0}%，持续2回合", "", new float[] { 10f, 14f, 18f, 22f, 28f, 35f }, 100, 100, "%", 2));
                allEffects.Add(new SubEffectMeta("虚弱压制", "虚弱机制", "降低目标造成的伤害{0}%，持续2回合", "", new float[] { 15f, 20f, 25f, 30f, 38f, 48f }, 100, 100, "%", 2));
            }
            else if (genre == "坚韧" || genre.Contains("恢复"))
            {
                allEffects.Add(new SubEffectMeta("总战力恢复", "战力治疗", "恢复己方总战力{0}%", "", new float[] { 4f, 6f, 8f, 11f, 14f, 18f }, 100, 100, "%", 2));
                allEffects.Add(new SubEffectMeta("当前战力自愈", "战力治疗", "恢复己方当前战力{0}%", "", new float[] { 8f, 12f, 16f, 22f, 28f, 36f }, 100, 100, "%", 2));
            }
            else // 魔力
            {
                allEffects.Add(new SubEffectMeta("最大流失", "持续流失", "目标2回合内每回合受到目标最大战力{0}%点流失伤害，持续2回合", "", new float[] { 1.5f, 2.0f, 2.6f, 3.2f, 4.0f, 5.0f }, 100, 100, "%", 2));
                allEffects.Add(new SubEffectMeta("固定流失", "持续流失", "目标2回合内每回合受到{0}*100%点流失伤害，持续2回合", "", new float[] { 3000f, 5000f, 8000f, 12000f, 18000f, 26000f }, 100, 100, "点", 2));
                allEffects.Add(new SubEffectMeta("已损流失", "持续流失", "目标2回合内每回合受到自身已损失战力{0}%点流失伤害，持续2回合", "", new float[] { 3.0f, 4.2f, 5.5f, 7.0f, 9.0f, 12.0f }, 100, 100, "%", 2));
                allEffects.Add(new SubEffectMeta("战力吸收", "吸血转化", "吸收本次伤害{0}%的战力", "", new float[] { 18f, 24f, 32f, 42f, 55f, 70f }, 100, 100, "%", 2));
            }

            List<SubEffectMeta> pool = new List<SubEffectMeta>();
            foreach (var meta in allEffects)
            {
                if (meta.MinUnlockTier <= tier)
                {
                    pool.Add(meta);
                }
            }

            if (pool.Count == 0)
            {
                pool.AddRange(allEffects);
            }

            SubEffectMeta chosen = pool[_rand.Next(pool.Count)];
            name = chosen.Name;
            category = chosen.Category;
            unit = chosen.Unit;

            int tIdx = Math.Max(0, Math.Min(5, tier - 1));
            float rawParam = chosen.TierParams[tIdx];
            param = (float)Math.Round(rawParam, 0);

            chance = _rand.Next(chosen.ChanceMin, chosen.ChanceMax + 1);
            desc = string.Format(chosen.DescTemplate, (int)param);
            csvFields = "";
        }

        private static readonly int[,] StatBudgetRanges = new int[,] { { 36, 44 }, { 54, 66 }, { 54, 66 }, { 54, 67 }, { 55, 68 }, { 62, 75 } };
        private const double StatPrimaryWeight = 0.693151578331;
        private const double StatSecondaryWeight = 0.107714114908;

        private static int GetStatBudget(int tier)
        {
            int index = Math.Max(0, Math.Min(5, tier - 1));
            return _rand.Next(StatBudgetRanges[index, 0], StatBudgetRanges[index, 1] + 1);
        }

        private static string GetStatBudgetDesc(int tier)
        {
            int index = Math.Max(0, Math.Min(5, tier - 1));
            return string.Format("30级：{0} ~ {1} 点", StatBudgetRanges[index, 0], StatBudgetRanges[index, 1]);
        }

        private static void AllocateStats(string genre, int total, out int courage, out int resilience, out int initiative, out int magic)
        {
            if (total <= 0)
            {
                courage = 0; resilience = 0; initiative = 0; magic = 0;
                return;
            }

            if (genre == "勇气" || genre.Contains("暴击"))
            {
                courage = (int)Math.Round(total * StatPrimaryWeight);
                magic = (int)Math.Round(total * StatSecondaryWeight);
                initiative = (int)Math.Round(total * (1.0 - StatPrimaryWeight - StatSecondaryWeight) / 2.0);
                resilience = total - courage - magic - initiative;
            }
            else if (genre == "先机" || genre.Contains("精准"))
            {
                initiative = (int)Math.Round(total * StatPrimaryWeight);
                courage = (int)Math.Round(total * StatSecondaryWeight);
                magic = (int)Math.Round(total * (1.0 - StatPrimaryWeight - StatSecondaryWeight) / 2.0);
                resilience = total - initiative - courage - magic;
            }
            else if (genre == "坚韧" || genre.Contains("恢复"))
            {
                resilience = (int)Math.Round(total * StatPrimaryWeight);
                courage = (int)Math.Round(total * StatSecondaryWeight);
                initiative = (int)Math.Round(total * (1.0 - StatPrimaryWeight - StatSecondaryWeight) / 2.0);
                magic = total - resilience - courage - initiative;
            }
            else // 魔力
            {
                magic = (int)Math.Round(total * StatPrimaryWeight);
                resilience = (int)Math.Round(total * StatSecondaryWeight);
                initiative = (int)Math.Round(total * (1.0 - StatPrimaryWeight - StatSecondaryWeight) / 2.0);
                courage = total - magic - resilience - initiative;
            }
            if (courage < 0) courage = 0;
            if (resilience < 0) resilience = 0;
            if (initiative < 0) initiative = 0;
            if (magic < 0) magic = 0;
        }

        private static int GetSynergyBudget(int tier)
        {
            switch (tier)
            {
                case 4: return 4;
                case 5: return 7;
                case 6: return 9;
                default: return 2;
            }
        }

        private static int GetIgnoreDefPercent(int tier)
        {
            switch (tier)
            {
                case 1: return 20;
                case 2: return 30;
                case 3: return 38;
                case 4: return 50;
                case 5: return 65;
                case 6: return 80;
                default: return 20;
            }
        }

        private static string BuildEffectText(string genre, float chance, float param, int times, int turnCond1, int turnCond2, int selfBpCond2, bool hasSub, string subDesc, int iniBonus, int ignoreDefPercent)
        {
            StringBuilder sb = new StringBuilder();

            // 1. 每场战斗限n次，
            if (times > 0)
            {
                sb.Append(string.Format("每场战斗限{0}次，", times));
            }

            // 2. 第n回合起，
            if (turnCond1 > 0 && turnCond2 > 0)
            {
                sb.Append(string.Format("第{0}至{1}回合期间，", turnCond1 + 1, turnCond2));
            }
            else if (turnCond1 > 0)
            {
                sb.Append(string.Format("第{0}回合起，", turnCond1 + 1));
            }
            else if (turnCond2 > 0)
            {
                sb.Append(string.Format("前{0}回合内，", turnCond2));
            }

            // 3. 己方战力低于n%时，
            if (selfBpCond2 > 0)
            {
                sb.Append(string.Format("己方战力低于{0}%时，", selfBpCond2));
            }

            // 4. n%概率发动，
            sb.Append(string.Format("{0}%概率发动，", (int)chance));

            // 5. 命中后造成n%的伤害
            int dmgParam = (genre == "坚韧" || genre.Contains("恢复")) ? 100 : (int)param;
            sb.Append(string.Format("命中后造成{0}%的伤害", dmgParam));

            // 6. 附带效果与流派专属效果
            string cleanSub = (hasSub && !string.IsNullOrEmpty(subDesc)) ? subDesc.TrimEnd(new char[] { '。', ' ', '\t' }) : "";

            if (genre == "坚韧" || genre.Contains("恢复"))
            {
                if (!string.IsNullOrEmpty(cleanSub))
                {
                    sb.Append("，" + cleanSub);
                }
            }
            else if (genre == "魔力")
            {
                sb.Append(string.Format("，无视目标{0}%的防御", ignoreDefPercent));
                if (!string.IsNullOrEmpty(cleanSub))
                {
                    sb.Append("，" + cleanSub);
                }
            }
            else if (genre == "先机" || genre.Contains("精准"))
            {
                if (!string.IsNullOrEmpty(cleanSub))
                {
                    sb.Append("，" + cleanSub);
                }
                sb.Append(string.Format("，先机加{0}", iniBonus));
            }
            else // 勇气
            {
                if (!string.IsNullOrEmpty(cleanSub))
                {
                    sb.Append("，" + cleanSub);
                }
                sb.Append("，有概率暴击");
            }

            sb.Append("。");
            return sb.ToString();
        }

        private static float SampleNormalClamped(float mean, float stdDev, float min, float max)
        {
            double u1 = 1.0 - _rand.NextDouble();
            double u2 = 1.0 - _rand.NextDouble();
            double randStdNormal = Math.Sqrt(-2.0 * Math.Log(u1)) * Math.Sin(2.0 * Math.PI * u2);
            double val = mean + stdDev * randStdNormal;

            if (val < min) val = min;
            if (val > max) val = max;
            return (float)val;
        }
    }

    /// <summary>
    /// 技能词条 -> 像素特效 (Super Pixel Effects Megapack 1) 高精双轴适配引擎
    /// 轴1：前缀/修饰词/宾语/流派 -> 决定特效颜色 (Color) 与元素亲和 (Element)
    /// 轴2：后缀/兵器载体/极境领域/子机制 -> 决定特效核心动作家族 (BaseKey) 与受击物理反馈 (HitReactionType 1~10)
    /// 静态产出唯一稳定的 animation_id (1001~1495) 与中文特征名
    /// </summary>
    public static class SkillEffectMatcher
    {
        public class VariantEntry
        {
            public int AnimationId;
            public string Color;
            public string CnName;
            public string FolderName;
        }

        public class FamilyEntry
        {
            public string BaseKey;
            public string CategoryCn;
            public string PureTitleCn;
            public string UserTag;
            public bool PlayOnCaster;
            public bool IsDisabled;
            public int HitReactionType;
            public string HitReactionName;
            public int DefaultHitReactionType;
            public string DefaultHitReactionName;
            public Dictionary<string, VariantEntry> Variants = new Dictionary<string, VariantEntry>();
        }

        private static bool _initialized = false;
        private static DateTime _lastJsonWriteTimeUtc = DateTime.MinValue;
        private static readonly Dictionary<string, FamilyEntry> _families = new Dictionary<string, FamilyEntry>();
        private static readonly List<FamilyEntry> _familyList = new List<FamilyEntry>();
        private static readonly Dictionary<int, VariantEntry> _byId = new Dictionary<int, VariantEntry>();
        private static readonly Dictionary<int, FamilyEntry> _familyById = new Dictionary<int, FamilyEntry>();

        public static List<FamilyEntry> GetAllFamilies()
        {
            EnsureInitialized();
            return _familyList;
        }

        public static bool TryGetById(int animationId, out VariantEntry variant, out FamilyEntry family)
        {
            EnsureInitialized();
            variant = null;
            family = null;
            if (animationId < 1001) return false;
            if (_byId.TryGetValue(animationId, out variant) && _familyById.TryGetValue(animationId, out family))
            {
                return true;
            }
            return false;
        }

        public static void EnsureInitialized()
        {
            if (!_initialized)
            {
                _initialized = true;
                _families.Clear();
                _familyList.Clear();
                _byId.Clear();
                _familyById.Clear();

            Reg("expfx1_epic_explosion_A", "[通用|对敌] 冲天爆破气柱", "通用", false, 2, "垂直击飞", "blue:1001:大蓝上升爆炸|green:1002:大绿上升爆炸|orange:1003:大橙上升爆炸|pink:1004:大粉上升爆炸|red:1005:大红上升爆炸|violet:1006:大紫上升爆炸|white:1007:大白上升爆炸|yellow:1008:大黄上升爆炸");
            Reg("expfx1_epic_explosion_B", "[通用|对敌] 史诗毁灭大爆炸", "通用", false, 6, "中心炸散复位", "blue:1009:巨蓝大爆炸|green:1010:巨绿大爆炸|orange:1011:巨橙大爆炸|pink:1012:巨粉大爆炸|red:1013:巨红大爆炸|violet:1014:巨紫大爆炸|white:1015:巨白大爆炸|yellow:1016:巨黄大爆炸");
            Reg("expfx1_stylized_explosion_A", "[通用|对敌] 气浪烟雾大爆炸", "通用", false, 5, "波浪状掀飞", "blue:1017:大蓝气浪烟雾爆炸|green:1018:大绿气浪烟雾爆炸|orange:1019:大橙气浪烟雾爆炸|pink:1020:大粉气浪烟雾爆炸|red:1021:大红气浪烟雾爆炸|violet:1022:大紫气浪烟雾爆炸|white:1023:大白气浪烟雾爆炸|yellow:1024:大黄气浪烟雾爆炸");
            Reg("expfx1_stylized_explosion_B", "[通用|对敌] 旋风球乱舞爆炸", "通用", false, 10, "集体旋转散开", "blue:1025:大蓝旋风球爆炸|green:1026:大绿旋风球爆炸|orange:1027:大橙旋风球爆炸|pink:1028:大粉旋风球爆炸|red:1029:大红旋风球爆炸|violet:1030:大紫旋风球爆炸|white:1031:大白旋风球爆炸|yellow:1032:大黄旋风球爆炸");
            Reg("expfx1_stylized_explosion_C", "[通用|对敌] 云朵升腾巨爆", "通用", false, 2, "垂直击飞", "blue:1033:巨蓝云朵上升爆炸|green:1034:巨绿云朵上升爆炸|orange:1035:巨橙云朵上升爆炸|pink:1036:巨粉云朵上升爆炸|red:1037:巨红云朵上升爆炸|violet:1038:巨紫云朵上升爆炸|white:1039:巨白云朵上升爆炸|yellow:1040:巨黄云朵上升爆炸");
            Reg("expfx1_symmetrical_explosion_A", "[通用|对敌] 密集烟雾对称爆", "通用", false, 6, "中心炸散复位", "blue:1041:大蓝密集烟雾爆炸|green:1042:大绿密集烟雾爆炸|orange:1043:大橙密集烟雾爆炸|pink:1044:大粉密集烟雾爆炸|red:1045:大红密集烟雾爆炸|violet:1046:大紫密集烟雾爆炸|white:1047:大白密集烟雾爆炸|yellow:1048:大黄密集烟雾爆炸");
            Reg("expfx1_symmetrical_explosion_B", "[通用|对敌] 闪光烟雾对称爆", "通用", false, 6, "中心炸散复位", "blue:1049:大蓝闪光烟雾爆炸|green:1050:大绿闪光烟雾爆炸|orange:1051:大橙闪光烟雾爆炸|pink:1052:大粉闪光烟雾爆炸|red:1053:大红闪光烟雾爆炸|violet:1054:大紫闪光烟雾爆炸|white:1055:大白闪光烟雾爆炸|yellow:1056:大黄闪光烟雾爆炸");
            Reg("expfx1_symmetrical_explosion_C", "[通用|对敌] 聚拢烟雾对称爆", "通用", false, 8, "地震颠簸", "blue:1057:大蓝聚拢烟雾爆炸|green:1058:大绿聚拢烟雾爆炸|orange:1059:大橙聚拢烟雾爆炸|pink:1060:大粉聚拢烟雾爆炸|red:1061:大红聚拢烟雾爆炸|violet:1062:大紫聚拢烟雾爆炸|white:1063:大白聚拢烟雾爆炸|yellow:1064:大黄聚拢烟雾爆炸");
            Reg("expfx1_symmetrical_explosion_D", "[通用|对敌] 分裂烟雾对称爆", "通用", false, 6, "中心炸散复位", "blue:1065:大蓝分裂烟雾爆炸|green:1066:大绿分裂烟雾爆炸|orange:1067:大橙分裂烟雾爆炸|pink:1068:大粉分裂烟雾爆炸|red:1069:大红分裂烟雾爆炸|violet:1070:大紫分裂烟雾爆炸|white:1071:大白分裂烟雾爆炸|yellow:1072:大黄分裂烟雾爆炸");
            Reg("fanfx1_magic_burst_A", "[通用|对敌] 奥术星星爆裂", "通用", false, 3, "抛物线后仰", "blue:1073:大蓝星星爆裂|green:1074:大绿星星爆裂|orange:1075:大橙星星爆裂|rainbow:1076:大彩虹星星爆裂|red:1077:大红星星爆裂|violet:1078:大紫星星爆裂|white:1079:大白星星爆裂|yellow:1080:大黄星星爆裂");
            Reg("fanfx1_magic_burst_B", "[通用|对敌] 璀璨星辰闪光爆裂", "通用", false, 3, "抛物线后仰", "blue:1081:巨蓝星星闪光爆裂|green:1082:巨绿星星闪光爆裂|orange:1083:巨橙星星闪光爆裂|rainbow:1084:巨彩虹星星闪光爆裂|red:1085:巨红星星闪光爆裂|violet:1086:巨紫星星闪光爆裂|white:1087:巨白星星闪光爆裂|yellow:1088:巨黄星星闪光爆裂");
            Reg("fanfx1_magic_puff_A", "[通用|对敌] 秘法星星烟雾爆炸", "通用", false, 8, "地震颠簸", "blue:1089:大蓝魔法星星烟雾爆炸|green:1090:大绿魔法星星烟雾爆炸|orange:1091:大橙魔法星星烟雾爆炸|red:1092:大红魔法星星烟雾爆炸|violet:1093:大紫魔法星星烟雾爆炸|white:1094:大白魔法星星烟雾爆炸|yellow:1095:大黄魔法星星烟雾爆炸");
            Reg("fanfx1_magic_puff_B", "[坚韧|对敌] 灵气烟雾升腾", "坚韧", false, 1, "水平震退", "blue:1096:大蓝烟雾上升|green:1097:大绿烟雾上升|orange:1098:大橙烟雾上升|red:1099:大红烟雾上升|violet:1100:大紫烟雾上升|white:1101:大白烟雾上升|yellow:1102:大黄烟雾上升");
            Reg("fanfx1_skull_puff", "[通用|对敌] 死灵骷髅烟雾爆炸", "通用", false, 8, "地震颠簸", "blue:1103:大蓝骷髅烟雾爆炸|green:1104:大绿骷髅烟雾爆炸|orange:1105:大橙骷髅烟雾爆炸|red:1106:大红骷髅烟雾爆炸|violet:1107:大紫骷髅烟雾爆炸|white:1108:大白骷髅烟雾爆炸|yellow:1109:大黄骷髅烟雾爆炸");
            Reg("fanfx1_spellcast_A", "[通用|对敌] 禁锢波纹眩晕星星", "通用", false, 10, "集体旋转散开", "blue:1110:大蓝波纹眩晕星星|green:1111:大绿波纹眩晕星星|orange:1112:大橙波纹眩晕星星|rainbow:1113:大彩虹波纹眩晕星星|red:1114:大红波纹眩晕星星|violet:1115:大紫波纹眩晕星星|yellow:1116:大黄波纹眩晕星星");
            Reg("fanfx1_spellcast_B", "[坚韧|自身] 祈愿波纹星星上升", "坚韧", true, 1, "水平震退", "blue:1117:大蓝波纹星星上升|green:1118:大绿波纹星星上升|orange:1119:大橙波纹星星上升|red:1120:大红波纹星星上升|violet:1121:大紫波纹星星上升|yellow:1122:大黄波纹星星上升");
            Reg("fanfx1_spellcast_C", "[魔力|对敌] 诅咒火焰波纹下降", "魔力", false, 8, "地震颠簸", "blue:1123:大蓝火焰波纹烟雾下降|green:1124:大绿火焰波纹烟雾下降|orange:1125:大橙火焰波纹烟雾下降|red:1126:大红火焰波纹烟雾下降|violet:1127:大紫火焰波纹烟雾下降|yellow:1128:大黄火焰波纹烟雾下降");
            Reg("fanfx1_spellcast_D", "[坚韧|自身] 金星波纹火焰升腾", "坚韧", true, 1, "水平震退", "blue:1129:大蓝金星波纹火焰上升|green:1130:大绿金星波纹火焰上升|orange:1131:大橙金星波纹火焰上升|red:1132:大红金星波纹火焰上升|violet:1133:大紫金星波纹火焰上升|yellow:1134:大黄金星波纹火焰上升");
            Reg("fanfx2_absorb", "[通用|对敌] 泡沫聚拢星星虹吸", "通用", false, 9, "中心聚拢吸附", "black:1135:大黑泡沫聚拢星星|blue:1136:大蓝泡沫聚拢星星|green:1137:大绿泡沫聚拢星星|orange:1138:大橙泡沫聚拢星星|pink:1139:大粉泡沫聚拢星星|red:1140:大红泡沫聚拢星星|violet:1141:大紫泡沫聚拢星星|white:1142:大白泡沫聚拢星星|yellow:1143:大黄泡沫聚拢星星");
            Reg("fanfx2_claw", "[通用|对敌] 流光裂空爪斩", "通用", false, 3, "抛物线后仰", "black:1144:大黑流星或爪击|blue:1145:大蓝流星或爪击|green:1146:大绿流星或爪击|orange:1147:大橙流星或爪击|pink:1148:大粉流星或爪击|red:1149:大红流星或爪击|violet:1150:大紫流星或爪击|white:1151:大白流星或爪击|yellow:1152:大黄流星或爪击");
            Reg("fanfx2_cure", "[坚韧|自身] 波浪金星治疗", "坚韧", true, 1, "水平震退", "blue:1153:大蓝波浪金星治疗|green:1154:大绿波浪金星治疗|orange:1155:大橙波浪金星治疗|pink:1156:大粉波浪金星治疗|red:1157:大红波浪金星治疗|violet:1158:大紫波浪金星治疗|yellow:1159:大黄波浪金星治疗");
            Reg("fanfx2_earth_spikes", "[通用|对敌] 大地冰锥尖刺突起", "通用", false, 4, "四向旋转翻滚", "black:1160:大黑冰锥地刺上升|blue:1161:大蓝冰锥地刺上升|brown:1162:大棕冰锥地刺上升|green:1163:大绿冰锥地刺上升|orange:1164:大橙冰锥地刺上升|red:1165:大红冰锥地刺上升|violet:1166:大紫冰锥地刺上升|yellow:1167:大黄冰锥地刺上升");
            Reg("fanfx2_fire_spell", "[通用|对敌] 冲天烈焰火柱", "通用", false, 6, "中心炸散复位", "black:1168:大黑火焰上升消散|blue:1169:大蓝火焰上升消散|gray:1170:大灰火焰上升消散|green:1171:大绿火焰上升消散|orange:1172:大橙火焰上升消散|pink:1173:大粉火焰上升消散|red:1174:大红火焰上升消散|violet:1175:大紫火焰上升消散|white:1176:大白火焰上升消散|yellow:1177:大黄火焰上升消散");
            Reg("fanfx2_ice_spell", "[通用|对敌] 史诗冰晶聚拢爆炸", "通用", false, 9, "中心聚拢吸附", "black:1178:大黑史诗冰晶聚拢冰锥爆炸|blue:1179:大蓝史诗冰晶聚拢冰锥爆炸|gray:1180:大灰史诗冰晶聚拢冰锥爆炸|green:1181:大绿史诗冰晶聚拢冰锥爆炸|orange:1182:大橙史诗冰晶聚拢冰锥爆炸|pink:1183:大粉史诗冰晶聚拢冰锥爆炸|red:1184:大红史诗冰晶聚拢冰锥爆炸|violet:1185:大紫史诗冰晶聚拢冰锥爆炸|yellow:1186:大黄史诗冰晶聚拢冰锥爆炸");
            Reg("fanfx2_poison", "[通用|对敌] 剧毒骷髅烟雾上升", "通用", false, 8, "地震颠簸", "black:1187:大黑骷髅烟雾上升|blue:1188:大蓝骷髅烟雾上升|brown:1189:大棕骷髅烟雾上升|gray:1190:大灰骷髅烟雾上升|green:1191:大绿骷髅烟雾上升|orange:1192:大橙骷髅烟雾上升|pink:1193:大粉骷髅烟雾上升|red:1194:大红骷髅烟雾上升|violet:1195:大紫骷髅烟雾上升|yellow:1196:大黄骷髅烟雾上升");
            Reg("fanfx2_shatter", "[通用|对敌] 镜面次元碎片爆炸", "通用", false, 9, "中心聚拢吸附", "black:1197:巨黑镜子碎片爆炸|blue:1198:巨蓝镜子碎片爆炸|gray:1199:巨灰镜子碎片爆炸|green:1200:巨绿镜子碎片爆炸|orange:1201:巨橙镜子碎片爆炸|pink:1202:巨粉镜子碎片爆炸|red:1203:巨红镜子碎片爆炸|violet:1204:巨紫镜子碎片爆炸|yellow:1205:巨黄镜子碎片爆炸");
            Reg("fanfx2_wind_spell", "[通用|对敌] 狂风聚拢爆裂", "通用", false, 9, "中心聚拢吸附", "black:1206:大黑狂风聚拢爆炸|blue:1207:大蓝狂风聚拢爆炸|brown:1208:大棕狂风聚拢爆炸|green:1209:大绿狂风聚拢爆炸|orange:1210:大橙狂风聚拢爆炸|pink:1211:大粉狂风聚拢爆炸|red:1212:大红狂风聚拢爆炸|violet:1213:大紫狂风聚拢爆炸|white:1214:大白狂风聚拢爆炸|yellow:1215:大黄狂风聚拢爆炸");
            Reg("fx1_electric_zap", "[通用|对敌] 疾电火花闪击", "通用", false, 1, "水平震退", "blue:1216:大灰蓝电火花|green:1217:大绿蓝电火花|orange:1218:大橙黄电火花|red:1219:大粉橙电火花|violet:1220:大紫黄电火花|white:1221:大灰黄电火花|yellow:1222:大黄粉电火花");
            Reg("fx1_explosion", "[通用|对敌] 毁灭蘑菇云轰炸", "通用", false, 6, "中心炸散复位", "blue:1223:大蓝蘑菇云|green:1224:大绿蘑菇云|orange:1225:大橙蘑菇云|red:1226:大红蘑菇云|violet:1227:大紫蘑菇云|yellow:1228:大黄蘑菇云");
            Reg("fx1_magic_puff", "[通用|对敌] 星辉烟团爆炸星星", "通用", false, 8, "地震颠簸", "black:1229:大灰烟团爆炸星星|blue:1230:大蓝烟团爆炸星星|green:1231:大绿烟团爆炸星星|orange:1232:大橙烟团爆炸星星|red:1233:大红烟团爆炸星星|violet:1234:大紫烟团爆炸星星|white:1235:大白烟团爆炸星星|yellow:1236:大黄烟团爆炸星星");
            Reg("fx2_bubble_appear", "[坚韧|自身] 圣洁泡泡护盾显现", "坚韧", true, 1, "水平震退", "blue:1237:大蓝泡泡出现与消散|green:1238:大绿泡泡出现与消散|orange:1239:大橙泡泡出现与消散|red:1240:大红泡泡出现与消散|violet:1241:大紫泡泡出现与消散|white:1242:大白泡泡出现与消散|yellow:1243:大黄泡泡出现与消散");

            Reg("fx2_claw", "[通用|对敌] 利爪撕裂", "通用", false, 7, "手风琴压缩", "black:1251:大黑爪击|blue:1252:大蓝爪击|green:1253:大绿爪击|orange:1254:大橙爪击|red:1255:大红爪击|violet:1256:大紫爪击|white:1257:大白爪击|yellow:1258:大黄爪击");
            Reg("fx2_electric_burst", "[通用|对敌] 八芒星圣裁雷光", "通用", false, 5, "波浪状掀飞", "blue:1259:大蓝八芒星电火花|green:1260:大绿八芒星电火花|orange:1261:大橙八芒星电火花|red:1262:大红八芒星电火花|violet:1263:大紫八芒星电火花|white:1264:大白八芒星电火花|yellow:1265:大黄八芒星电火花");
            Reg("fx2_explosion", "[通用|对敌] 巨型大爆炸", "通用", false, 6, "中心炸散复位", "blue:1266:大蓝大爆炸|green:1267:大绿大爆炸|orange:1268:大橙大爆炸|red:1269:大红大爆炸|violet:1270:大紫大爆炸|yellow:1271:大黄大爆炸");

            Reg("fx2_slash", "[通用|对敌] 刀剑圆斩", "通用", false, 1, "水平震退", "black:1278:大黑圆斩|blue:1279:大蓝圆斩|green:1280:大绿圆斩|orange:1281:大橙圆斩|red:1282:大红圆斩|violet:1283:大紫圆斩|white:1284:大白圆斩|yellow:1285:大黄圆斩");
            Reg("fx3_bite", "[通用|对敌] 狂暴利齿咬合", "通用", false, 8, "地震颠簸", "blue:1286:大蓝利齿咬合|green:1287:大绿利齿咬合|orange:1288:大橙利齿咬合|red:1289:大红利齿咬合|violet:1290:大紫利齿咬合|yellow:1291:大黄利齿咬合");
            Reg("fx3_impact_hit", "[通用|对敌] 重钧圆环打击", "通用", false, 2, "垂直击飞", "blue:1292:大蓝圆环打击|green:1293:大绿圆环打击|orange:1294:大橙圆环打击|red:1295:大红圆环打击|violet:1296:大紫圆环打击|yellow:1297:大黄圆环打击");

            Reg("fx3_magic_spawn", "[通用|对敌] 秘法聚合闪光", "通用", false, 9, "中心聚拢吸附", "blue:1304:大蓝魔法聚合闪光|green:1305:大绿魔法聚合闪光|orange:1306:大橙魔法聚合闪光|red:1307:大红魔法聚合闪光|violet:1308:大紫魔法聚合闪光|yellow:1309:大黄魔法聚合闪光");
            Reg("fx3_smoke_bomb", "[通用|对敌] 暗影孢子烟雾爆炸", "通用", false, 8, "地震颠簸", "black:1310:大黑孢子烟雾爆炸|blue:1311:大蓝孢子烟雾爆炸|brown:1312:大棕孢子烟雾爆炸|green:1313:大绿孢子烟雾爆炸|orange:1314:大橙孢子烟雾爆炸|red:1315:大红孢子烟雾爆炸|violet:1316:大紫孢子烟雾爆炸|white:1317:大白孢子烟雾爆炸|yellow:1318:大黄孢子烟雾爆炸");
            Reg("fx3_splatter", "[通用|对敌] 腐蚀烟雾泡沫爆炸", "通用", false, 8, "地震颠簸", "blue:1319:大蓝烟雾泡沫爆炸|gray:1320:大灰烟雾泡沫爆炸|green:1321:大绿烟雾泡沫爆炸|orange:1322:大橙烟雾泡沫爆炸|red:1323:大红烟雾泡沫爆炸|violet:1324:大紫烟雾泡沫爆炸|yellow:1325:大黄烟雾泡沫爆炸");
            Reg("fx3_toon_explosion", "[坚韧|自身] 守护正圆气浪爆", "坚韧", true, 1, "水平震退", "blue:1326:大蓝正圆爆炸|green:1327:大绿正圆爆炸|orange:1328:大橙正圆爆炸|red:1329:大红正圆爆炸|violet:1330:大紫正圆爆炸|white:1331:大白正圆爆炸|yellow:1332:大黄正圆爆炸");
            Reg("fx3_toon_impact", "[通用|对敌] 重压气泡爆裂", "通用", false, 5, "波浪状掀飞", "blue:1333:大蓝气泡爆炸|green:1334:大绿气泡爆炸|orange:1335:大橙气泡爆炸|red:1336:大红气泡爆炸|violet:1337:大紫气泡爆炸|yellow:1338:大黄气泡爆炸");
            Reg("fx3_warp", "[通用|对敌] 虚空带电跃迁爆炸", "通用", false, 5, "波浪状掀飞", "blue:1339:大蓝带电爆炸|green:1340:大绿带电爆炸|orange:1341:大橙带电爆炸|pink:1342:大粉带电爆炸|red:1343:大红带电爆炸|violet:1344:大紫带电爆炸|yellow:1345:大黄带电爆炸");
            Reg("impfx1_dust_impact_A", "[通用|对敌] 震地气浪烟雾爆炸", "通用", false, 5, "波浪状掀飞", "blue:1346:大蓝气浪烟雾爆炸|green:1347:大绿气浪烟雾爆炸|orange:1348:大橙气浪烟雾爆炸|red:1349:大红气浪烟雾爆炸|violet:1350:大紫气浪烟雾爆炸|white:1351:大白气浪烟雾爆炸|yellow:1352:大黄气浪烟雾爆炸");
            Reg("impfx1_dust_impact_B", "[通用|对敌] 裂地分散烟雾爆炸", "通用", false, 5, "波浪状掀飞", "blue:1353:大蓝分散气浪烟雾爆炸|green:1354:大绿分散气浪烟雾爆炸|orange:1355:大橙分散气浪烟雾爆炸|red:1356:大红分散气浪烟雾爆炸|violet:1357:大紫分散气浪烟雾爆炸|white:1358:大白分散气浪烟雾爆炸|yellow:1359:大黄分散气浪烟雾爆炸");
            Reg("impfx1_quick_impact_A", "[通用|对敌] 迅捷轻微气闪", "通用", false, 1, "水平震退", "blue:1360:大蓝轻微气体闪光|green:1361:大绿轻微气体闪光|orange:1362:大橙轻微气体闪光|red:1363:大红轻微气体闪光|violet:1364:大紫轻微气体闪光|white:1365:大白轻微气体闪光|yellow:1366:大黄轻微气体闪光");
            Reg("impfx1_quick_impact_B", "[通用|对敌] 极速锐芒闪光", "通用", false, 1, "水平震退", "blue:1367:大蓝闪光|green:1368:大绿闪光|orange:1369:大橙闪光|red:1370:大红闪光|violet:1371:大紫闪光|white:1372:大白闪光|yellow:1373:大黄闪光");
            Reg("impfx1_quick_impact_C", "[通用|对敌] 寒芒冰晶闪光", "通用", false, 1, "水平震退", "blue:1374:大蓝冰晶闪光|green:1375:大绿冰晶闪光|orange:1376:大橙冰晶闪光|red:1377:大红冰晶闪光|violet:1378:大紫冰晶闪光|white:1379:大白冰晶闪光|yellow:1380:大黄冰晶闪光");
            Reg("impfx1_quick_impact_D", "[通用|对敌] 疾闪命中闪光", "通用", false, 1, "水平震退", "blue:1381:大蓝击中闪光|green:1382:大绿击中闪光|orange:1383:大橙击中闪光|red:1384:大红击中闪光|violet:1385:大紫击中闪光|white:1386:大白击中闪光|yellow:1387:大黄击中闪光");
            Reg("impfx1_toon_impact_A", "[通用|对敌] 弥散羽毛闪光", "通用", false, 2, "垂直击飞", "blue:1388:大蓝弥散羽毛闪光|green:1389:大绿弥散羽毛闪光|orange:1390:大橙弥散羽毛闪光|red:1391:大红弥散羽毛闪光|violet:1392:大紫弥散羽毛闪光|white:1393:大白弥散羽毛闪光|yellow:1394:大黄弥散羽毛闪光");
            Reg("impfx1_toon_impact_B", "[通用|对敌] 要害刺状闪光", "通用", false, 1, "水平震退", "blue:1395:大蓝刺状闪光|green:1396:大绿刺状闪光|orange:1397:大橙刺状闪光|red:1398:大红刺状闪光|violet:1399:大紫刺状闪光|white:1400:大白刺状闪光|yellow:1401:大黄刺状闪光");
            Reg("impfx1_toon_impact_C", "[通用|对敌] 圆形气浪复合闪光", "通用", false, 3, "抛物线后仰", "blue:1402:大蓝圆形气浪复合闪光|green:1403:大绿圆形气浪复合闪光|orange:1404:大橙圆形气浪复合闪光|red:1405:大红圆形气浪复合闪光|violet:1406:大紫圆形气浪复合闪光|white:1407:大白圆形气浪复合闪光|yellow:1408:大黄圆形气浪复合闪光");
            Reg("impfx1_toon_impact_D", "[通用|对敌] 波纹羽毛闪光", "通用", false, 5, "波浪状掀飞", "blue:1409:大蓝波纹羽毛闪光|green:1410:大绿波纹羽毛闪光|orange:1411:大橙波纹羽毛闪光|red:1412:大红波纹羽毛闪光|violet:1413:大紫波纹羽毛闪光|white:1414:大白波纹羽毛闪光|yellow:1415:大黄波纹羽毛闪光");
            Reg("scifx1_explosion_A", "[通用|对敌] 坍缩泡沫收束爆炸", "通用", false, 3, "抛物线后仰", "blue:1416:大蓝泡沫爆炸后收束|green:1417:大绿泡沫爆炸后收束|orange:1418:大橙泡沫爆炸后收束|red:1419:大红泡沫爆炸后收束|violet:1420:大紫泡沫爆炸后收束|yellow:1421:大黄泡沫爆炸后收束");
            Reg("scifx1_explosion_B", "[通用|对敌] 激流带电爆裂", "通用", false, 5, "波浪状掀飞", "blue:1422:大蓝溅水带电爆炸|green:1423:大绿溅水带电爆炸|orange:1424:大橙溅水带电爆炸|red:1425:大红溅水带电爆炸|violet:1426:大紫溅水带电爆炸|yellow:1427:大黄溅水带电爆炸");
            Reg("scifx1_wormhole", "[通用|对敌] 异界时空虫洞", "通用", false, 9, "中心聚拢吸附", "blue:1428:大蓝虫洞出现与消散|green:1429:大绿虫洞出现与消散|orange:1430:大橙虫洞出现与消散|red:1431:大红虫洞出现与消散|violet:1432:大紫虫洞出现与消散|yellow:1433:大黄虫洞出现与消散");
            Reg("scifx1_zap_A", "[通用|对敌] 繁复电弧爆炸", "通用", false, 4, "四向旋转翻滚", "blue:1434:大蓝繁复电弧爆炸|green:1435:大绿繁复电弧爆炸|orange:1436:大橙繁复电弧爆炸|red:1437:大红繁复电弧爆炸|violet:1438:大紫繁复电弧爆炸|yellow:1439:大黄繁复电弧爆炸");
            Reg("scifx1_zap_B", "[通用|对敌] 双色高压电弧爆", "通用", false, 8, "地震颠簸", "blue:1440:大蓝双色电弧爆炸|green:1441:大绿双色电弧爆炸|orange:1442:大橙双色电弧爆炸|red:1443:大红双色电弧爆炸|violet:1444:大紫双色电弧爆炸|yellow:1445:大黄双色电弧爆炸");
            Reg("scifx2_black_hole", "[通用|对敌] 虚空引力黑洞", "通用", false, 9, "中心聚拢吸附", "blue:1446:大蓝黑洞出现与消散|green:1447:大绿黑洞出现与消散|orange:1448:大橙黑洞出现与消散|pink:1449:大粉黑洞出现与消散|red:1450:大红黑洞出现与消散|violet:1451:大紫黑洞出现与消散|white:1452:大白黑洞出现与消散|yellow:1453:大黄黑洞出现与消散");
            Reg("scifx2_buff", "[通用|自身] 战意科技增益上升", "通用", true, 1, "水平震退", "blue:1454:大蓝科技增益上升|green:1455:大绿科技增益上升|orange:1456:大橙科技增益上升|pink:1457:大粉科技增益上升|red:1458:大红科技增益上升|violet:1459:大紫科技增益上升|yellow:1460:大黄科技增益上升");
            Reg("scifx2_debuff", "[魔力|对敌] 虚弱压制力场下降", "魔力", false, 8, "地震颠簸", "blue:1461:大蓝科技就减益下降|green:1462:大绿科技就减益下降|orange:1463:大橙科技就减益下降|pink:1464:大粉科技就减益下降|red:1465:大红科技就减益下降|violet:1466:大紫科技就减益下降|yellow:1467:大黄科技就减益下降");
            Reg("scifx2_hex_shield", "[通用|自身] 多边形坚壁护盾", "通用", true, 1, "水平震退", "black:1468:大黑科技多边形护盾|blue:1469:大蓝科技多边形护盾|gray:1470:大灰科技多边形护盾|green:1471:大绿科技多边形护盾|orange:1472:大橙科技多边形护盾|pink:1473:大粉科技多边形护盾|red:1474:大红科技多边形护盾|violet:1475:大紫科技多边形护盾|white:1476:大白科技多边形护盾|yellow:1477:大黄科技多边形护盾");

            Reg("scifx2_warp", "[通用|对敌] 次元电弧气环爆炸", "通用", false, 8, "地震颠簸", "black:1487:大黑电弧气环爆炸|blue:1488:大蓝电弧气环爆炸|green:1489:大绿电弧气环爆炸|orange:1490:大橙电弧气环爆炸|pink:1491:大粉电弧气环爆炸|red:1492:大红电弧气环爆炸|violet:1493:大紫电弧气环爆炸|white:1494:大白电弧气环爆炸|yellow:1495:大黄电弧气环爆炸");
            }
            SyncFromEffectNamesJsonIfChanged();
        }

        private static void Reg(string baseKey, string categoryCn, string userTag, bool playOnCaster, int hitReactionType, string hitReactionName, string encodedVariants)
        {
            string pureTitle = categoryCn;
            int closeBracket = categoryCn.IndexOf(']');
            if (closeBracket >= 0 && closeBracket + 1 < categoryCn.Length)
            {
                pureTitle = categoryCn.Substring(closeBracket + 1).Trim();
            }

            int effHitType = playOnCaster ? 1 : hitReactionType;
            string effHitName = playOnCaster ? "水平震退" : hitReactionName;

            FamilyEntry fam = new FamilyEntry
            {
                BaseKey = baseKey,
                PureTitleCn = pureTitle,
                UserTag = string.IsNullOrEmpty(userTag) ? "通用" : userTag,
                PlayOnCaster = playOnCaster,
                IsDisabled = !string.IsNullOrEmpty(userTag) && userTag.Contains("禁用"),
                HitReactionType = effHitType,
                HitReactionName = effHitName,
                DefaultHitReactionType = hitReactionType,
                DefaultHitReactionName = hitReactionName,
                CategoryCn = string.Format("[{0}|{1}] {2}", string.IsNullOrEmpty(userTag) ? "通用" : userTag, playOnCaster ? "自身" : "对敌", pureTitle)
            };
            string[] items = encodedVariants.Split('|');
            for (int i = 0; i < items.Length; i++)
            {
                string[] parts = items[i].Split(':');
                if (parts.Length < 3) continue;
                string col = parts[0];
                int aid = int.Parse(parts[1]);
                string cn = parts[2];
                VariantEntry ve = new VariantEntry
                {
                    AnimationId = aid,
                    Color = col,
                    CnName = cn,
                    FolderName = string.Format("{0}_large_{1}", baseKey, col)
                };
                fam.Variants[col] = ve;
                _byId[aid] = ve;
                _familyById[aid] = fam;
            }
            _families[baseKey] = fam;
            _familyList.Add(fam);
        }

        public static void SyncFromEffectNamesJsonIfChanged()
        {
            try
            {
                string jsonPath = @"D:\123\effect_names.json";
                if (!File.Exists(jsonPath))
                {
                    string alt = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "effect_names.json");
                    if (File.Exists(alt)) jsonPath = alt;
                    else return;
                }

                DateTime writeUtc = File.GetLastWriteTimeUtc(jsonPath);
                if (writeUtc == _lastJsonWriteTimeUtc) return;
                _lastJsonWriteTimeUtc = writeUtc;

                string curFolder = "";
                string curCategory = "通用";
                bool curTargetSelf = false;
                bool hasTargetSelfField = false;

                string[] lines = File.ReadAllLines(jsonPath, Encoding.UTF8);
                for (int i = 0; i < lines.Length; i++)
                {
                    string line = lines[i].Trim();
                    if (line.StartsWith("\"folder\"", StringComparison.Ordinal))
                    {
                        curFolder = ExtractJsonStr(line);
                    }
                    else if (line.StartsWith("\"category\"", StringComparison.Ordinal))
                    {
                        curCategory = ExtractJsonStr(line);
                    }
                    else if (line.StartsWith("\"target_self\"", StringComparison.Ordinal))
                    {
                        curTargetSelf = line.IndexOf("true", StringComparison.OrdinalIgnoreCase) >= 0;
                        hasTargetSelfField = true;
                    }
                    else if (line.StartsWith("\"target_tag\"", StringComparison.Ordinal) && !hasTargetSelfField)
                    {
                        string ttag = ExtractJsonStr(line);
                        if (ttag.Contains("自身")) curTargetSelf = true;
                    }
                    else if (line == "}," || line == "}")
                    {
                        if (!string.IsNullOrEmpty(curFolder))
                        {
                            int largeIdx = curFolder.IndexOf("_large_", StringComparison.Ordinal);
                            if (largeIdx > 0)
                            {
                                string rawBase = curFolder.Substring(0, largeIdx);
                                if (rawBase == "scifx1_wormhole_appear" || rawBase == "scifx1_wormhole_disappear" || rawBase == "scifx1_wormhole_start" || rawBase == "scifx1_wormhole_stop")
                                    rawBase = "scifx1_wormhole";
                                else if (rawBase == "scifx2_black_hole_appear" || rawBase == "scifx2_black_hole_disappear")
                                    rawBase = "scifx2_black_hole";
                                else if (rawBase == "fx2_bubble_disappear")
                                    rawBase = "fx2_bubble_appear";
                                else if (rawBase == "fx2_bubble")
                                    rawBase = curFolder.EndsWith("_pop", StringComparison.Ordinal) ? "fx2_bubble_appear" : "fx2_bubble_appear";

                                FamilyEntry fam;
                                if (_families.TryGetValue(rawBase, out fam))
                                {
                                    string cleanCat = string.IsNullOrEmpty(curCategory) ? "通用" : curCategory.Trim();
                                    fam.UserTag = cleanCat;
                                    fam.IsDisabled = cleanCat.Contains("禁用");
                                    if (hasTargetSelfField)
                                    {
                                        fam.PlayOnCaster = curTargetSelf;
                                    }
                                    // 针对自身的特效：对敌人受击固定为普通击退 [1]水平震退
                                    if (fam.PlayOnCaster)
                                    {
                                        fam.HitReactionType = 1;
                                        fam.HitReactionName = "水平震退";
                                    }
                                    else
                                    {
                                        fam.HitReactionType = fam.DefaultHitReactionType > 0 ? fam.DefaultHitReactionType : 1;
                                        fam.HitReactionName = !string.IsNullOrEmpty(fam.DefaultHitReactionName) ? fam.DefaultHitReactionName : "水平震退";
                                    }
                                    fam.CategoryCn = string.Format("[{0}|{1}] {2}", fam.UserTag, fam.PlayOnCaster ? "自身" : "对敌", fam.PureTitleCn);
                                }
                            }
                        }
                        curFolder = "";
                        curCategory = "通用";
                        curTargetSelf = false;
                        hasTargetSelfField = false;
                    }
                }
            }
            catch { }
        }

        private static string ExtractJsonStr(string line)
        {
            int colon = line.IndexOf(':');
            if (colon < 0) return "";
            int q1 = line.IndexOf('"', colon + 1);
            if (q1 < 0) return "";
            int q2 = line.IndexOf('"', q1 + 1);
            if (q2 < 0) return "";
            return line.Substring(q1 + 1, q2 - q1 - 1);
        }

        public static bool IsFamilyAllowedForGenre(FamilyEntry fam, string genre)
        {
            if (fam == null || fam.IsDisabled) return false;

            bool isResilience = genre.Contains("坚韧") || genre.Contains("恢复");
            string normGenre = isResilience ? "坚韧"
                : (genre.Contains("先机") || genre.Contains("精准") ? "先机"
                : (genre.Contains("魔力") || genre.Contains("机制") ? "魔力" : "勇气"));

            if (TargetsCaster(fam))
            {
                // 针对自身的特效只会出现在坚韧里
                return isResilience;
            }

            // 针对敌方的特效：看第一词条标签
            if (string.IsNullOrEmpty(fam.UserTag) || fam.UserTag == "通用")
                return true;

            return fam.UserTag.Contains(normGenre);
        }

        private static uint StableHash(string value)
        {
            unchecked { uint hash=2166136261;foreach(char c in value){hash^=c;hash*=16777619;}return hash; }
        }
        public static bool TargetsCaster(FamilyEntry family)
        {
#if UNITY_5_3_OR_NEWER
            foreach(var variant in family.Variants.Values)return EffectTimingConfig.For(variant.AnimationId).playOnCaster;
#endif
            return family.PlayOnCaster;
        }
        private static FamilyEntry FallbackAllowedFamily(string skillName, string genre, bool preferSelfOnResilience)
        {
            bool isResilience = genre.Contains("坚韧") || genre.Contains("恢复");
            string normGenre = isResilience ? "坚韧"
                : (genre.Contains("先机") || genre.Contains("精准") ? "先机"
                : (genre.Contains("魔力") || genre.Contains("机制") ? "魔力" : "勇气"));

            List<FamilyEntry> primary = new List<FamilyEntry>();
            List<FamilyEntry> secondary = new List<FamilyEntry>();

            for (int i = 0; i < _familyList.Count; i++)
            {
                FamilyEntry f = _familyList[i];
                if (!IsFamilyAllowedForGenre(f, genre)) continue;

                if (isResilience)
                {
                    if (preferSelfOnResilience && TargetsCaster(f)) primary.Add(f);
                    else if (!preferSelfOnResilience && !TargetsCaster(f) && f.UserTag.Contains("坚韧")) primary.Add(f);
                    else secondary.Add(f);
                }
                else
                {
                    if (!string.IsNullOrEmpty(f.UserTag) && f.UserTag.Contains(normGenre)) primary.Add(f);
                    else secondary.Add(f);
                }
            }

            List<FamilyEntry> pool = primary.Count > 0 ? primary : secondary;
            if (pool.Count == 0) throw new InvalidOperationException("No allowed effect family for " + genre);

            uint hash = StableHash(skillName ?? "斩");
            return pool[(int)(hash % (uint)pool.Count)];
        }

        public static void ResolveSkillEffect(
            string skillName,
            string genre,
            int tier,
            string subEffectName,
            out int animationId,
            out string effectCnName,
            out string effectFolder,
            out string effectCategory)
        {
            int hitReactionType;
            string hitReactionName;
            ResolveSkillEffect(
                skillName,
                genre,
                tier,
                subEffectName,
                out animationId,
                out effectCnName,
                out effectFolder,
                out effectCategory,
                out hitReactionType,
                out hitReactionName);
        }

        public static void ResolveSkillEffect(
            string skillName,
            string genre,
            int tier,
            string subEffectName,
            out int animationId,
            out string effectCnName,
            out string effectFolder,
            out string effectCategory,
            out int hitReactionType,
            out string hitReactionName)
        {
            EnsureInitialized();
            if (string.IsNullOrEmpty(skillName)) skillName = "斩天剑";
            if (string.IsNullOrEmpty(genre)) genre = "勇气";
            if (string.IsNullOrEmpty(subEffectName)) subEffectName = "";

            string headPart;
            string midPart;
            if (skillName.Length == 3)
            {
                headPart = skillName.Substring(0, 1);
                midPart = skillName.Substring(1, 1);
            }
            else if (skillName.Length >= 6)
            {
                headPart = skillName.Substring(0, 2);
                midPart = skillName.Substring(2, 2);
            }
            else
            {
                headPart = skillName.Substring(0, Math.Min(2, skillName.Length));
                midPart = "";
            }
            string prefixPart = headPart + midPart;
            string tail2 = skillName.Length >= 2 ? skillName.Substring(skillName.Length - 2) : skillName;
            string tail1 = skillName.Length >= 1 ? skillName.Substring(skillName.Length - 1) : skillName;

            string elementTag;
            string targetColor = ResolveNameColor(headPart,midPart,skillName,genre,tier,subEffectName,out elementTag);
            string baseKey = ResolveBaseFamily(skillName, prefixPart, tail2, tail1, genre, tier, elementTag, subEffectName);

            FamilyEntry fam=ChooseCompatibleFamily(skillName,genre,tier,baseKey,targetColor);
            if (fam==null)
            {
                bool preferSelf = (fam != null && TargetsCaster(fam)) || MatchesTail(tail2, tail1, "壁垒", "屏障", "坚壁", "圣盾", "铁壁", "坚甲", "盾御", "圣铠", "格挡", "之盾", "之铠", "盾", "庇护", "护佑", "结界", "护持", "守卫", "护界", "圣障", "纯净", "恩赐", "愈合", "救赎", "慈悲", "慰藉", "甘霖", "圣泉", "圣雨", "洗礼", "祝福", "奉献", "圣威", "圣誓", "之冠", "祷言", "之心", "之歌", "心", "圣震", "圣辉", "灵气", "复苏", "唤醒", "战意", "鼓舞", "觉醒", "增幅");
                fam = FallbackAllowedFamily(skillName, genre, preferSelf);
            }

            VariantEntry chosen = PickColorVariant(fam, targetColor);
            animationId = chosen.AnimationId;
            effectCnName = chosen.CnName;
            effectFolder = chosen.FolderName;
            effectCategory = string.Format("[{0}|{1}] {2}",fam.UserTag,TargetsCaster(fam)?"自身":"对敌",fam.PureTitleCn);
            hitReactionType = TargetsCaster(fam) ? 1 : fam.HitReactionType;
            hitReactionName = TargetsCaster(fam) ? "水平震退" : fam.HitReactionName;
        }

        private static bool IsApexName(string name)
        {
            return name.Length>=6&&ContainsAny(name.Substring(2,2),"斩击","连刺","穿心","崩山","洗礼","侵蚀","乱舞","闪击","坠击","吞噬","强劈","贯穿","爆射","震裂","狂斩","破阵","突袭","轰鸣","撕裂","碾压","旋刃","裂地","突刺","飞星","绝杀","破霸","疾射","逆击","破空","碎骨");
        }
        private static FamilyEntry ChooseCompatibleFamily(string name,string genre,int tier,string baseKey,string color)
        {
            string[] keys=new[]{baseKey};
            switch(baseKey)
            {
                case "expfx1_epic_explosion_B": case "fx2_explosion": case "fx1_explosion":
                    keys=new[]{"expfx1_epic_explosion_B","fx2_explosion","fx1_explosion","expfx1_stylized_explosion_C"};break;
                case "expfx1_stylized_explosion_A": case "expfx1_symmetrical_explosion_A": case "expfx1_symmetrical_explosion_B": case "expfx1_symmetrical_explosion_D":
                    keys=new[]{"expfx1_stylized_explosion_A","expfx1_symmetrical_explosion_A","expfx1_symmetrical_explosion_B","expfx1_symmetrical_explosion_D"};break;
                case "fanfx1_magic_burst_A": case "fanfx1_magic_burst_B": case "fx3_magic_spawn":
                    keys=new[]{"fanfx1_magic_burst_A","fanfx1_magic_burst_B","fx3_magic_spawn"};break;
                case "fanfx1_magic_puff_A": case "fx1_magic_puff": case "fx3_smoke_bomb":
                    keys=new[]{"fanfx1_magic_puff_A","fx1_magic_puff","fx3_smoke_bomb"};break;
                case "scifx1_zap_A": case "scifx1_zap_B": case "fx1_electric_zap":
                    keys=new[]{"scifx1_zap_A","scifx1_zap_B","fx1_electric_zap"};break;
                case "impfx1_quick_impact_A": case "impfx1_quick_impact_B": case "impfx1_quick_impact_C": case "impfx1_quick_impact_D": case "impfx1_toon_impact_B":
                    keys=new[]{"impfx1_quick_impact_A","impfx1_quick_impact_B","impfx1_quick_impact_C","impfx1_quick_impact_D","impfx1_toon_impact_B"};break;
                case "fx3_impact_hit": case "impfx1_toon_impact_C": case "fx3_toon_impact":
                    keys=new[]{"fx3_impact_hit","impfx1_toon_impact_C","fx3_toon_impact"};break;
                case "impfx1_dust_impact_A": case "impfx1_dust_impact_B":
                    keys=new[]{"impfx1_dust_impact_A","impfx1_dust_impact_B"};break;
                case "fanfx2_poison":
                    keys=new[]{"fanfx2_poison","fx3_splatter"};break;
                case "fanfx1_spellcast_C":
                    keys=new[]{"fanfx1_spellcast_C","fanfx1_spellcast_A","fanfx1_skull_puff"};break;
                case "scifx2_debuff":
                    keys=new[]{"scifx2_debuff","fx3_toon_impact"};break;
                case "fanfx1_magic_puff_B":
                    if(MatchesTail(name.Substring(Math.Max(0,name.Length-2)),name.Substring(name.Length-1),"圣罚","圣击","灵光","回响","圣辉","耀光","圣震"))
                        keys=new[]{"fanfx1_magic_puff_B","fanfx1_magic_burst_A","fx2_electric_burst"};
                    break;
                case "fanfx1_spellcast_D":
                    keys=new[]{"fanfx1_spellcast_D","scifx2_buff"};break;
                case "fanfx2_absorb": case "scifx1_explosion_A": case "expfx1_symmetrical_explosion_C":
                    keys=new[]{"fanfx2_absorb","scifx1_explosion_A","expfx1_symmetrical_explosion_C"};break;
            }
            var allowed=new List<FamilyEntry>();var exact=new List<FamilyEntry>();
            FamilyEntry anchor;bool sameTarget=_families.TryGetValue(baseKey,out anchor)&&IsFamilyAllowedForGenre(anchor,genre);
            bool caster=sameTarget&&TargetsCaster(anchor);
            foreach(string key in keys)
            {
                FamilyEntry candidate;if(!_families.TryGetValue(key,out candidate)||!IsFamilyAllowedForGenre(candidate,genre))continue;
                if(sameTarget&&TargetsCaster(candidate)!=caster)continue;
                allowed.Add(candidate);if(candidate.Variants.ContainsKey(color))exact.Add(candidate);
            }
            var pool=exact.Count>0?exact:allowed;
            if(pool.Count==0)return null;
            return pool[(int)(StableHash(name+"|"+genre+"|"+tier+"|family")%(uint)pool.Count)];
        }
        private static string ResolveNameColor(string head,string middle,string name,string genre,int tier,string subEffect,out string element)
        {
            string context=head+middle;
            if(ContainsAny(context,"钢铁","坚钢","铁壁","坚甲","断钢","斩铁","金属","磐石","劫灰")){element="metal";return "gray";}
            if(ContainsAny(context,"大地","尘世","碎石","巨石","崩岩","沙","泥","尘")){element="earth";return "brown";}
            string color=ResolveColorAndElement(head,head,"",tier,subEffect,out element);
            if(string.IsNullOrEmpty(color))
            {
                string midElement;color=ResolveColorAndElement(middle,middle,"",tier,subEffect,out midElement);
                if(element=="none")element=midElement;
            }
            if(tier>=5&&ContainsAny(middle,"因果","万物","轮回","诸界","幻梦","命运","混沌")&&element!="fire"&&element!="ice"&&element!="lightning")
            {element="arcane";return "rainbow";}
            if(string.IsNullOrEmpty(color))color=ResolveColorAndElement("",name,"",tier,subEffect,out element);
            return string.IsNullOrEmpty(color)?GetGenreDefaultColor(genre):color;
        }

        private static string ResolveColorAndElement(
            string prefixPart,
            string fullName,
            string genre,
            int tier,
            string subEffectName,
            out string elementTag)
        {
            elementTag = "none";

            if (ContainsAny(prefixPart, "寒冰", "冰霜", "极寒", "冻结", "寒芒", "冰", "霜") || ContainsAny(fullName, "冰原"))
            {
                elementTag = "ice";
                if (ContainsAny(prefixPart, "极寒", "寒芒")) return "white";
                return "blue";
            }
            if (ContainsAny(prefixPart, "闪电", "雷霆", "苍雷", "迅雷", "天谴", "雷") || ContainsAny(fullName, "狂雷", "天劫", "轰顶"))
            {
                elementTag = "lightning";
                if (ContainsAny(prefixPart, "苍雷", "迅雷")) return "blue";
                return "yellow";
            }
            if (ContainsAny(prefixPart, "烈焰", "炽热", "焦热", "怒火", "龙炎", "灼热", "炽煌", "冥炎", "黑炎", "焚", "炽", "炎") || ContainsAny(fullName, "火海", "怒炎", "之火", "圣焰", "冥火"))
            {
                elementTag = "fire";
                if (ContainsAny(prefixPart, "黑炎", "冥炎") || ContainsAny(fullName, "冥火")) return "violet";
                if (ContainsAny(prefixPart, "熔岩", "焦热", "炽煌")) return "orange";
                return "red";
            }
            if (ContainsAny(prefixPart, "剧毒", "巫毒", "腐化", "腐蚀", "凋零", "毒", "蛇", "蛛", "蟒", "蜂") || subEffectName.Contains("中毒"))
            {
                elementTag = "poison";
                if (ContainsAny(prefixPart, "巫毒", "腐化", "凋零")) return "violet";
                return "green";
            }
            if (ContainsAny(prefixPart, "浴血", "嗜血", "猩红", "血") || subEffectName.Contains("流血"))
            {
                elementTag = "blood";
                return "red";
            }
            if (ContainsAny(prefixPart, "狂风", "暴风", "旋风", "疾风", "追风", "穿林", "飞燕", "风", "雀", "鹏") || ContainsAny(fullName, "风暴", "裂风"))
            {
                elementTag = "wind";
                if (ContainsAny(prefixPart, "暴风", "苍穹", "天空", "追风", "飞燕")) return "blue";
                return "green";
            }
            if (ContainsAny(prefixPart, "流水", "骤雨", "怒涛", "圣泉", "甘霖", "狂澜", "潮", "鲲", "蛟") || ContainsAny(fullName, "怒涛", "狂潮", "激流", "奔流"))
            {
                elementTag = "water";
                return "blue";
            }
            if (ContainsAny(prefixPart, "裂地", "碎石", "熔岩", "巨石", "崩岩", "崩山", "磐石", "大地", "天崩", "地"))
            {
                elementTag = "earth";
                if (ContainsAny(prefixPart, "熔岩")) return "red";
                return "orange";
            }

            if (tier >= 5 && ContainsAny(prefixPart, "极光", "幻梦", "因果", "轮回", "诸界", "万物", "时空", "次元", "元素", "重塑"))
            {
                elementTag = "arcane";
                return "rainbow";
            }
            if (ContainsAny(prefixPart, "极光", "幻梦", "蝶", "狐", "妖术", "妖"))
            {
                elementTag = "arcane";
                return "pink";
            }
            if (ContainsAny(prefixPart, "漆黑", "黑夜", "永夜", "死线", "刺杀", "暗杀", "锁喉", "抹喉", "夺命", "致命", "绝命", "孤影", "盲区", "潜行", "偷袭", "影缝", "碎颅", "冥府", "绝望", "劫灰", "幽域", "黑", "暗", "死"))
            {
                elementTag = "dark";
                return "black";
            }
            if (ContainsAny(prefixPart, "暗影", "混沌", "幻象", "奥术", "以太", "虚空", "深渊", "秘法", "灵能", "蚀魂", "湮灭", "禁断", "幽冥", "灾祸", "虹吸", "魔力", "邪能", "咒术", "烙印", "星界", "蚀刻", "魂能", "秘术", "恶魔", "痛苦", "灾厄", "幽暗", "冥界", "裂隙", "维度", "诡术", "死灵", "禁忌", "异界", "聚能", "崩解", "解离", "虚弱", "咒缚", "噬魂", "鬼神", "逆鳞", "瞬影", "影袭", "幻影", "匿踪", "绝影", "影遁", "潜雾", "迷踪", "邪", "魔", "鬼", "冥", "幻", "幽", "魂", "虚", "渊", "劫", "狱", "魄", "梦", "蝠", "枭", "扭曲", "支配"))
            {
                elementTag = "dark";
                return "violet";
            }
            if (ContainsAny(prefixPart, "净白", "纯洁", "纯白", "圣洁", "洗礼", "赎罪", "庇护", "守护", "固守", "不屈", "专注", "护持", "坚毅", "坚韧", "守望", "断钢", "斩铁", "破甲", "穿甲", "无影", "实体", "锐利", "锋锐", "白", "真", "灵", "道", "净化", "驱散"))
            {
                elementTag = "holy";
                return "white";
            }
            if (ContainsAny(prefixPart, "圣光", "圣堂", "神圣", "圣佑", "祈愿", "戒律", "祝福", "圣盾", "奉献", "恩赐", "光辉", "晨曦", "神恩", "圣殿", "圣灵", "圣域", "圣裁", "圣印", "崇高", "誓约", "虔信", "剑圣", "无双", "破晓", "鹰眼", "锐眼", "定点", "要害", "黎明", "极昼", "金刚", "究极", "圣", "神", "皇", "帝", "耀", "星", "麟", "凤", "雕", "鹰", "审判", "裁决", "救赎"))
            {
                elementTag = "holy";
                return "yellow";
            }
            if (ContainsAny(prefixPart, "回春", "抚慰", "活血", "治愈", "慈悲", "猎犬", "灵巧", "伺机", "敏锐", "唤醒"))
            {
                elementTag = "holy";
                return "green";
            }
            if (ContainsAny(prefixPart, "修罗", "罗刹", "死狂", "屠龙", "狂暴", "狂怒", "狂乱", "暴烈", "残暴", "凶暴", "毁灭", "极灭", "灭界", "灭世", "处决", "决斗", "强袭", "天灾", "献祭", "狂", "怒", "暴", "凶", "煞", "灭", "弑", "诛"))
            {
                elementTag = "fire";
                return "red";
            }
            if (ContainsAny(prefixPart, "霸王", "霸道", "巨力", "战意", "破军", "破城", "斗神", "战鬼", "刚勇", "豪胆", "狮心", "铁拳", "战吼", "开天", "刚猛", "刚刃", "强击", "坚钢", "铁壁", "坚牢", "坚壁", "震荡", "震天", "霸", "虎", "狮", "熊", "猿", "象", "獒"))
            {
                elementTag = "earth";
                return "orange";
            }
            if (ContainsAny(prefixPart, "苍穹", "星辰", "天空", "深空", "裂天", "旋天", "飞跃", "回旋", "穿刺", "迅捷", "连环", "破空", "贯穿", "贯通", "居合", "极速", "燕返", "绝速", "疾刃", "疾驰", "疾步", "超流", "极限", "天", "空", "月", "苍", "狼"))
            {
                return "blue";
            }

            return "";
        }

        private static string GetGenreDefaultColor(string genre)
        {
            if (genre.Contains("勇气") || genre.Contains("暴击")) return "red";
            if (genre.Contains("先机") || genre.Contains("精准")) return "blue";
            if (genre.Contains("坚韧") || genre.Contains("恢复")) return "green";
            if (genre.Contains("魔力") || genre.Contains("机制")) return "violet";
            return "blue";
        }

        private static string ResolveBaseFamily(
            string fullName,
            string prefixPart,
            string tail2,
            string tail1,
            string genre,
            int tier,
            string elementTag,
            string subEffectName)
        {
            bool isResilience = genre.Contains("坚韧") || genre.Contains("恢复");
            if(IsApexName(fullName))
            {
                string action=fullName.Substring(2,2);
                if(tail2=="风暴"||tail2=="旋涡"||tail2=="乱流")return ContainsAny(action,"斩","旋","乱舞")?"expfx1_stylized_explosion_B":"fanfx2_wind_spell";
                if(tail2=="陨星")return "expfx1_epic_explosion_A";
                if(tail2=="骤雨")return ContainsAny(action,"刺","射","贯穿")?"impfx1_toon_impact_A":"scifx1_explosion_B";
                if(tail2=="火海"||tail2=="怒炎")return "fanfx2_fire_spell";
                if(tail2=="冰原")return "fanfx2_ice_spell";
                if(tail2=="天劫"||tail2=="狂雷"||tail2=="轰顶")return "scifx1_zap_A";
                if(tail2=="射线"||tail2=="辉光")return isResilience&&action=="洗礼"?"fanfx2_cure":"fx2_electric_burst";
                if(tail2=="狂潮"||tail2=="怒涛"||tail2=="狂澜")return "scifx1_explosion_B";
                if(tail2=="裂变"||tail2=="极境"||tail2=="领域")return isResilience&&tail2=="领域"?"scifx2_buff":"scifx2_warp";
                if(tail2=="结界")return isResilience?"fx2_bubble_appear":"fanfx1_spellcast_A";
                if(tail2=="暗涌")return "scifx2_debuff";
                if(tail2=="爆轰"||tail2=="绝杀"||tail2=="崩灭"||tail2=="浩劫")return "expfx1_epic_explosion_B";
                if(tail2=="暴乱"||tail2=="狂宴"||tail2=="狂啸")return "expfx1_symmetrical_explosion_B";
                if(tail2=="冲击"||tail2=="震荡")return "impfx1_dust_impact_A";
            }

            // ── 1. 用户显式定性【坚韧】护盾 / 治疗 / 祈愿 / 圣堂光柱类 (仅限坚韧流派进入针对自身及护盾反震池) ──
            if (isResilience)
            {
                if(MatchesTail(tail2,tail1,"圣罚","圣击","灵光","回响","圣辉","耀光","圣震"))return "fanfx1_magic_puff_B";
                if (MatchesTail(tail2, tail1, "壁垒", "屏障", "坚壁", "圣盾", "铁壁", "坚甲", "盾御", "圣铠", "格挡", "之盾", "之铠", "盾"))
                    return "scifx2_hex_shield";
                if (MatchesTail(tail2, tail1, "庇护", "护佑", "结界", "护持", "守卫", "护界", "圣障", "纯净", "恩赐"))
                    return "fx2_bubble_appear";
                if (MatchesTail(tail2, tail1, "反震", "赎罪", "净除", "圣环"))
                    return "fx2_bubble_appear";
                if (MatchesTail(tail2, tail1, "固守", "磐石", "圣佑", "坚守"))
                    return "fx3_toon_explosion";
                if (MatchesTail(tail2, tail1, "愈合", "救赎", "慈悲", "慰藉", "甘霖", "圣泉", "圣雨", "洗礼"))
                    return "fanfx2_cure";
                if (MatchesTail(tail2, tail1, "祝福", "奉献", "圣威", "圣誓", "之冠"))
                    return "fanfx1_spellcast_D";
                if (MatchesTail(tail2, tail1, "祷言", "之心", "之歌", "心"))
                    return "fanfx1_spellcast_B";
                if (MatchesTail(tail2, tail1, "圣震", "圣辉"))
                    return "fanfx2_cure";
                if (MatchesTail(tail2, tail1, "灵气", "复苏", "唤醒"))
                    return "fanfx1_magic_puff_B";
                if (MatchesTail(tail2, tail1, "战意", "鼓舞", "觉醒", "增幅"))
                    return "scifx2_buff";
            }

            // ── 2. 近战刀剑 / 流光裂空爪斩 / 撕咬类 (无向右弹道，全部采用中心爆发斩击) ──
            if (MatchesTail(tail2, tail1, "之剑", "之刃", "之镰", "连斩", "重斩", "狂斩", "怒斩", "斩铁", "轮斩", "旋劈", "旋刃", "拔刀", "挥砍", "剑", "斩", "刃", "镰", "扇") || fullName.Contains("斩击"))
                return "fx2_slash";
            if (MatchesTail(tail2, tail1, "斩杀", "乱劈", "猛劈", "挑斩", "逆斩", "割裂", "裂劈", "劈裂", "截断", "之翼", "飞燕", "鹰击", "掠杀", "甩尾", "翼"))
                return "fanfx2_claw";
            if (MatchesTail(tail2, tail1, "之爪", "狂袭", "奇袭", "突袭", "疾掠", "撕裂", "穿心", "爪"))
                return "fx2_claw";
            if (MatchesTail(tail2, tail1, "索命", "封喉", "绞杀", "枭首", "牙", "角"))
                return "fx3_bite";

            // ── 3. 先机刺击 / 寒芒穿透 / 极速闪光类 (替代已禁用的手里剑/苦无/冰锥向右弹道) ──
            if (MatchesTail(tail2, tail1, "之枪", "之矛", "破绽", "要害", "挑刺", "破甲", "刺杀", "暗杀", "抹杀", "追命", "穿刺", "枪", "矛", "刺"))
                return "impfx1_toon_impact_B";
            if (MatchesTail(tail2, tail1, "之箭", "之弓", "飞刀", "突刺", "疾刺", "射击", "狙杀", "直击", "绝突", "瞬斩", "疾斩", "爆射", "弓", "矢"))
                return "impfx1_quick_impact_B";
            if (MatchesTail(tail2, tail1, "之戟", "贯穿", "穿透", "穿甲", "绝刺", "闪刺", "连刺", "疾射", "戟") || fullName.Contains("连刺") || fullName.Contains("贯穿"))
                return "impfx1_quick_impact_C";
            if (MatchesTail(tail2, tail1, "飞刃", "旋刺", "之轮", "连弩", "乱射", "骤雨", "轮"))
                return "impfx1_toon_impact_A";
            if (MatchesTail(tail2, tail1, "闪避", "残影", "影步", "疾闪", "瞬步", "影突", "影刃"))
                return "impfx1_quick_impact_D";
            if (MatchesTail(tail2, tail1, "潜行", "匿踪", "孤影", "盲区", "偷袭"))
                return "impfx1_quick_impact_A";
            if (MatchesTail(tail2, tail1, "破势", "破霸", "逆击", "截击"))
                return "impfx1_toon_impact_D";

            // ── 4. 勇气重锤 / 圆环重击 / 震地气浪类 (替代已禁用的横向重击/向下冲击/接地冲击波向右) ──
            if (MatchesTail(tail2, tail1, "之锤", "崩击", "碎击", "碎骨", "裂颅", "霸击", "强劈", "碎心", "裂魄", "锤", "斧"))
                return "fx3_impact_hit";
            if (MatchesTail(tail2, tail1, "踏击", "踏破", "坠击", "轰落", "震击", "强袭", "突霸", "破阵", "激突", "龙击") || fullName.Contains("坠击"))
                return "impfx1_dust_impact_A";
            if (MatchesTail(tail2, tail1, "扫荡", "突进", "飞踢", "挑击", "冲击", "激荡", "震荡"))
                return "impfx1_dust_impact_B";
            if (MatchesTail(tail2, tail1, "扫击", "猛攻", "撞击", "掌击", "肘击", "狂打", "狂攻", "连击", "闪击", "锐击", "音速", "伏击", "拳", "击"))
                return "impfx1_toon_impact_C";
            if (MatchesTail(tail2, tail1, "碾压", "碾碎", "碎压", "强压", "压杀", "塌陷", "镇压"))
                return "fx3_toon_impact";

            // ── 5. 大地尖刺 / 镜面破碎 / 冲天爆破类 ──
            if (MatchesTail(tail2, tail1, "裂地", "崩山", "断岳", "碎岳", "震裂", "崩裂"))
                return "fanfx2_earth_spikes";
            if (MatchesTail(tail2, tail1, "之镜", "碎裂", "裂空", "破空", "裂隙", "镜"))
                return "fanfx2_shatter";
            if (MatchesTail(tail2, tail1, "陨星", "飞星", "投掷"))
                return "expfx1_epic_explosion_A";

            // ── 6. 用户显式定性【魔力】诅咒波纹 / 禁锢封印 / 虚空黑洞(出现+消散) / 异界虫洞(出现+消散) / 剧毒死灵 / 奥术星辰类 ──
            if (MatchesTail(tail2, tail1, "烙印", "诅咒", "灾厄", "天罚"))
                return "fanfx1_spellcast_C";
            if (MatchesTail(tail2, tail1, "封印", "锁魂", "枷锁", "咒缚", "缠绕", "之印", "之锁", "之牢", "之符", "之誓", "之歌", "结界", "圣印", "链", "环", "阵", "印"))
                return "fanfx1_spellcast_A";
            if (MatchesTail(tail2, tail1, "虚弱", "暗涌", "压制", "沉沦"))
                return "scifx2_debuff";
            if (MatchesTail(tail2, tail1, "引力", "湮灭"))
                return "scifx2_black_hole";
            if (MatchesTail(tail2, tail1, "之门", "逆流", "折跃"))
                return "scifx1_wormhole";
            if (MatchesTail(tail2, tail1, "虹吸", "吞噬"))
                return "fanfx2_absorb";
            if (MatchesTail(tail2, tail1, "坍缩", "收束", "崩解"))
                return "scifx1_explosion_A";
            if (MatchesTail(tail2, tail1, "毒爆", "腐蚀", "侵蚀", "凋零"))
                return "fanfx2_poison";
            if (MatchesTail(tail2, tail1, "之雾", "潜雾", "迷雾", "烟幕"))
                return "fx3_smoke_bomb";
            if (MatchesTail(tail2, tail1, "反噬", "骨"))
                return "fanfx1_skull_puff";
            if (MatchesTail(tail2, tail1, "之眼", "凝视", "眼", "瞳"))
                return "fx3_magic_spawn";
            if (MatchesTail(tail2, tail1, "之核", "圣核", "之心", "珠", "心"))
                return "expfx1_symmetrical_explosion_C";
            if (MatchesTail(tail2, tail1, "圣击", "灵光", "回响", "杖", "魄"))
                return "fanfx1_magic_burst_A";
            if (MatchesTail(tail2, tail1, "之权", "之冠", "星辰", "诸界"))
                return "fanfx1_magic_burst_B";
            if (MatchesTail(tail2, tail1, "极境", "次元"))
                return "scifx2_warp";
            if (MatchesTail(tail2, tail1, "领域"))
                return isResilience ? "scifx2_buff" : "scifx2_warp";

            // ── 7. 寒冰 / 雷电 / 狂风 / 激流 / 烈焰元素爆发类 (禁用所有循环球体/循环落雷) ──
            if (MatchesTail(tail2, tail1, "冰原"))
                return "fanfx2_ice_spell";
            if (MatchesTail(tail2, tail1, "狂雷", "天劫", "轰顶"))
                return "scifx1_zap_A";
            if (MatchesTail(tail2, tail1, "轰鸣", "脉冲"))
                return "scifx1_zap_A";
            if (MatchesTail(tail2, tail1, "圣裁", "之裁", "耀光", "辉光", "射线", "贯日", "之光"))
                return "fx2_electric_burst";
            if (MatchesTail(tail2, tail1, "极光", "穿魂"))
                return "fx1_electric_zap";
            if (MatchesTail(tail2, tail1, "风暴", "裂风", "乱流", "之息"))
                return "fanfx2_wind_spell";
            if (MatchesTail(tail2, tail1, "旋风", "乱舞", "翻腾", "旋涡", "漩涡"))
                return "expfx1_stylized_explosion_B";
            if (MatchesTail(tail2, tail1, "激流", "奔流", "狂潮", "怒涛", "狂澜", "圣潮"))
                return "scifx1_explosion_B";
            if (MatchesTail(tail2, tail1, "之火", "圣焰", "灼烧", "冥火", "怒炎", "弹射", "炮"))
                return "fanfx2_fire_spell";
            if (MatchesTail(tail2, tail1, "焚尽", "献祭", "火海", "狂宴", "怒啸", "狂啸", "暴乱"))
                return "expfx1_symmetrical_explosion_B";

            // ── 8. 前缀元素亲和驱动 (ElementTag) ──
            if (elementTag == "ice")
                return "fanfx2_ice_spell";
            if (elementTag == "lightning")
                return tier >= 4 ? "scifx1_zap_A" : "scifx1_zap_B";
            if (elementTag == "wind")
                return tier >= 4 ? "fanfx2_wind_spell" : "expfx1_stylized_explosion_B";
            if (elementTag == "water")
                return (genre.Contains("坚韧") || genre.Contains("恢复")) ? "fanfx2_cure" : "scifx1_explosion_B";
            if (elementTag == "blood")
                return "fx3_splatter";
            if (elementTag == "poison")
                return "fanfx2_poison";

            // ── 9. 细分高能爆炸后缀 ──
            if (MatchesTail(tail2, tail1, "灭杀", "碎灭", "聚爆", "崩灭", "终结", "处刑", "绝杀"))
                return "expfx1_epic_explosion_B";
            if (MatchesTail(tail2, tail1, "灾变", "浩劫", "狂涌"))
                return "expfx1_stylized_explosion_C";
            if (MatchesTail(tail2, tail1, "裂变"))
                return "fx3_warp";
            if (MatchesTail(tail2, tail1, "爆轰", "暴轰", "爆裂", "震爆", "爆碎", "轰击"))
                return "fx2_explosion";
            if (MatchesTail(tail2, tail1, "爆破", "爆散", "破裂", "击碎", "飞弹"))
                return "fx1_explosion";
            if (MatchesTail(tail2, tail1, "迸发", "溃散", "爆鸣", "圣爆"))
                return "expfx1_stylized_explosion_A";
            if (MatchesTail(tail2, tail1, "溃灭", "裂解"))
                return "expfx1_symmetrical_explosion_D";

            // ── 10. 附加机制与四大流派定性标签兜底 ──
            if (subEffectName.Contains("中毒")) return "fanfx2_poison";
            if (subEffectName.Contains("流血")) return "fx3_splatter";
            if (subEffectName.Contains("封印")) return "fanfx1_spellcast_A";
            if (subEffectName.Contains("吸收")) return "fanfx2_absorb";

            if (genre.Contains("坚韧") || genre.Contains("恢复"))
                return "fanfx2_cure";
            if (genre.Contains("先机") || genre.Contains("精准"))
                return tier >= 5 ? "fanfx2_claw" : "impfx1_toon_impact_B";
            if (genre.Contains("魔力") || genre.Contains("机制"))
                return tier >= 5 ? "fanfx1_magic_burst_B" : "fanfx1_spellcast_C";
            return tier >= 5 ? "expfx1_epic_explosion_B" : "fx2_slash";
        }

        private static VariantEntry PickColorVariant(FamilyEntry fam, string targetColor)
        {
            VariantEntry ve;
            if (fam.Variants.TryGetValue(targetColor, out ve)) return ve;

            // 多级平滑颜色降级链
            string[] fallbacks = GetColorFallbackChain(targetColor);
            for (int i = 0; i < fallbacks.Length; i++)
            {
                if (fam.Variants.TryGetValue(fallbacks[i], out ve)) return ve;
            }

            // 任意可用变体兜底
            foreach (var kv in fam.Variants)
            {
                return kv.Value;
            }
            return null;
        }

        private static string[] GetColorFallbackChain(string color)
        {
            switch (color)
            {
                case "black": return new string[] { "black", "violet", "gray", "dark_brown", "red", "blue" };
                case "white": return new string[] { "white", "yellow", "light_blue", "blue", "gray" };
                case "pink": return new string[] { "pink", "violet", "red", "yellow" };
                case "rainbow": return new string[] { "rainbow", "pink", "violet", "yellow", "blue" };
                case "gray": return new string[] { "gray", "white", "blue", "black" };
                case "brown": return new string[] { "brown", "orange", "red", "yellow" };
                case "orange": return new string[] { "orange", "red", "yellow", "brown", "dark_brown" };
                case "red": return new string[] { "red", "orange", "violet", "yellow", "blue" };
                case "yellow": return new string[] { "yellow", "orange", "white", "light_brown", "blue" };
                case "green": return new string[] { "green", "blue", "yellow", "white" };
                case "violet": return new string[] { "violet", "blue", "red", "black" };
                case "blue":
                default: return new string[] { "blue", "dark_blue", "light_blue", "white", "violet" };
            }
        }

        private static bool ContainsAny(string text, params string[] keywords)
        {
            if (string.IsNullOrEmpty(text)) return false;
            for (int i = 0; i < keywords.Length; i++)
            {
                if (text.Contains(keywords[i])) return true;
            }
            return false;
        }

        private static bool MatchesTail(string tail2, string tail1, params string[] suffixes)
        {
            for (int i = 0; i < suffixes.Length; i++)
            {
                string s = suffixes[i];
                if (s.Length == 2 && tail2 == s) return true;
                if (s.Length == 1 && tail1 == s) return true;
            }
            return false;
        }
    }

    /// <summary>
    /// 像素特效实时逐帧预览播放器 (15 FPS, NearestNeighbor 零模糊像素渲染)
    /// 支持自动按 animation_id 加载对应 spritesheet.png + spritesheet.txt 并循环播放
    /// 支持暂停/单帧步进/FPS调速/背景切换/同族换色对比/全特效库浏览
    /// </summary>
    public class EffectAnimationPreviewControl : Panel
    {
        private sealed class DoubleBufferedCanvas : Panel
        {
            public DoubleBufferedCanvas()
            {
                this.DoubleBuffered = true;
                this.SetStyle(
                    ControlStyles.AllPaintingInWmPaint |
                    ControlStyles.UserPaint |
                    ControlStyles.OptimizedDoubleBuffer |
                    ControlStyles.ResizeRedraw,
                    true);
            }
        }

        private sealed class ComboItem
        {
            public string Text;
            public int AnimationId;
            public SkillEffectMatcher.FamilyEntry Family;
            public override string ToString() { return Text; }
        }

        private Label _lblTitleLine1;
        private Label _lblTitleLine2;
        private DoubleBufferedCanvas _canvas;
        private Button _btnPlayPause;
        private Button _btnPrevFrame;
        private Button _btnNextFrame;
        private Button _btnReplay;
        private ComboBox _cbFps;
        private ComboBox _cbBgMode;
        private ComboBox _cbColorVariants;
        private ComboBox _cbAllFamilies;
        private Timer _timer;

        private Bitmap _sheetBitmap;
        private readonly List<Rectangle> _frames = new List<Rectangle>();
        private int _curFrame = 0;
        private bool _isPlaying = true;
        private int _fps = 15;
        private int _bgMode = 0; // 0=深灰暗场, 1=透明棋盘格, 2=草地战场
        private bool _suppressComboEvents = false;

        public int CurrentAnimationId { get; private set; }
        public string CurrentCnName { get; private set; }
        public string CurrentFolderName { get; private set; }
        public string CurrentCategoryCn { get; private set; }
        public int CurrentHitReactionType { get; private set; }
        public string CurrentHitReactionName { get; private set; }
        private string _skillBadge = "";

        public EffectAnimationPreviewControl()
        {
            this.BorderStyle = BorderStyle.FixedSingle;
            this.BackColor = Color.FromArgb(28, 30, 36);

            // 顶部两行信息栏
            Panel pnlHeader = new Panel();
            pnlHeader.Dock = DockStyle.Top;
            pnlHeader.Height = 46;
            pnlHeader.BackColor = Color.FromArgb(36, 39, 48);
            pnlHeader.Padding = new Padding(8, 4, 8, 4);

            _lblTitleLine1 = new Label();
            _lblTitleLine1.Dock = DockStyle.Top;
            _lblTitleLine1.Height = 20;
            _lblTitleLine1.ForeColor = Color.FromArgb(255, 215, 90);
            _lblTitleLine1.Font = new Font("Microsoft YaHei", 9.5F, FontStyle.Bold);
            _lblTitleLine1.Text = "等待选择或生成技能特效...";
            _lblTitleLine1.AutoEllipsis = true;

            _lblTitleLine2 = new Label();
            _lblTitleLine2.Dock = DockStyle.Bottom;
            _lblTitleLine2.Height = 18;
            _lblTitleLine2.ForeColor = Color.FromArgb(190, 200, 215);
            _lblTitleLine2.Font = new Font("Consolas", 8.5F, FontStyle.Regular);
            _lblTitleLine2.Text = "文件夹: - | 帧: 0/0";
            _lblTitleLine2.AutoEllipsis = true;

            pnlHeader.Controls.Add(_lblTitleLine2);
            pnlHeader.Controls.Add(_lblTitleLine1);

            // 底部控制面板 (两行操作栏：第1行播放控制，第2行同族换色与全库切换)
            Panel pnlBottom = new Panel();
            pnlBottom.Dock = DockStyle.Bottom;
            pnlBottom.Height = 62;
            pnlBottom.BackColor = Color.FromArgb(36, 39, 48);
            pnlBottom.Padding = new Padding(4);

            Panel pnlRow1 = new Panel();
            pnlRow1.Dock = DockStyle.Top;
            pnlRow1.Height = 28;

            _btnPlayPause = CreateSmallButton("⏸ 暂停", 4, 2, 62, 24);
            _btnPlayPause.Click += (s, e) => TogglePlayPause();

            _btnPrevFrame = CreateSmallButton("|<", 70, 2, 32, 24);
            _btnPrevFrame.Click += (s, e) => StepFrame(-1);

            _btnNextFrame = CreateSmallButton(">|", 105, 2, 32, 24);
            _btnNextFrame.Click += (s, e) => StepFrame(1);

            _btnReplay = CreateSmallButton("🔁 重播", 141, 2, 58, 24);
            _btnReplay.Click += (s, e) => ReplayFromStart();

            _cbFps = new ComboBox();
            _cbFps.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbFps.Items.AddRange(new object[] { "8 FPS", "12 FPS", "15 FPS", "20 FPS", "24 FPS" });
            _cbFps.SelectedIndex = 2; // 15 FPS
            _cbFps.Location = new Point(204, 2);
            _cbFps.Width = 70;
            _cbFps.Font = new Font("Consolas", 8.5F);
            _cbFps.SelectedIndexChanged += (s, e) => OnFpsChanged();

            _cbBgMode = new ComboBox();
            _cbBgMode.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbBgMode.Items.AddRange(new object[] { "暗场底", "棋盘格", "草地底" });
            _cbBgMode.SelectedIndex = 0;
            _cbBgMode.Location = new Point(278, 2);
            _cbBgMode.Width = 72;
            _cbBgMode.Font = new Font("Microsoft YaHei", 8.5F);
            _cbBgMode.SelectedIndexChanged += (s, e) => { _bgMode = _cbBgMode.SelectedIndex; _canvas.Invalidate(); };

            pnlRow1.Controls.Add(_btnPlayPause);
            pnlRow1.Controls.Add(_btnPrevFrame);
            pnlRow1.Controls.Add(_btnNextFrame);
            pnlRow1.Controls.Add(_btnReplay);
            pnlRow1.Controls.Add(_cbFps);
            pnlRow1.Controls.Add(_cbBgMode);

            Panel pnlRow2 = new Panel();
            pnlRow2.Dock = DockStyle.Bottom;
            pnlRow2.Height = 28;

            Label lblColor = new Label();
            lblColor.Text = "换色:";
            lblColor.ForeColor = Color.FromArgb(200, 210, 225);
            lblColor.Font = new Font("Microsoft YaHei", 8.5F);
            lblColor.Location = new Point(4, 5);
            lblColor.AutoSize = true;

            _cbColorVariants = new ComboBox();
            _cbColorVariants.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbColorVariants.Location = new Point(40, 2);
            _cbColorVariants.Width = 150;
            _cbColorVariants.Font = new Font("Microsoft YaHei", 8.25F);
            _cbColorVariants.SelectedIndexChanged += (s, e) => OnColorVariantComboChanged();

            Label lblFam = new Label();
            lblFam.Text = "特效簇:";
            lblFam.ForeColor = Color.FromArgb(200, 210, 225);
            lblFam.Font = new Font("Microsoft YaHei", 8.5F);
            lblFam.Location = new Point(195, 5);
            lblFam.AutoSize = true;

            _cbAllFamilies = new ComboBox();
            _cbAllFamilies.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbAllFamilies.Location = new Point(242, 2);
            _cbAllFamilies.Width = 165;
            _cbAllFamilies.Font = new Font("Microsoft YaHei", 8.25F);
            _cbAllFamilies.SelectedIndexChanged += (s, e) => OnFamilyComboChanged();

            pnlRow2.Controls.Add(lblColor);
            pnlRow2.Controls.Add(_cbColorVariants);
            pnlRow2.Controls.Add(lblFam);
            pnlRow2.Controls.Add(_cbAllFamilies);

            pnlBottom.Controls.Add(pnlRow2);
            pnlBottom.Controls.Add(pnlRow1);

            // 中央双缓冲像素画布
            _canvas = new DoubleBufferedCanvas();
            _canvas.Dock = DockStyle.Fill;
            _canvas.BackColor = Color.FromArgb(22, 24, 30);
            _canvas.Paint += OnCanvasPaint;
            _canvas.MouseClick += (s, e) => ReplayFromStart();

            this.Controls.Add(_canvas);
            this.Controls.Add(pnlBottom);
            this.Controls.Add(pnlHeader);

            PopulateAllFamiliesDropdown();

            _timer = new Timer();
            _timer.Interval = 66; // 15 FPS
            _timer.Tick += OnTimerTick;
            _timer.Start();
        }

        private static Button CreateSmallButton(string text, int x, int y, int w, int h)
        {
            Button btn = new Button();
            btn.Text = text;
            btn.Location = new Point(x, y);
            btn.Size = new Size(w, h);
            btn.FlatStyle = FlatStyle.Flat;
            btn.FlatAppearance.BorderColor = Color.FromArgb(75, 82, 98);
            btn.BackColor = Color.FromArgb(52, 57, 70);
            btn.ForeColor = Color.White;
            btn.Font = new Font("Microsoft YaHei", 8.25F, FontStyle.Regular);
            return btn;
        }

        private void PopulateAllFamiliesDropdown()
        {
            _suppressComboEvents = true;
            _cbAllFamilies.Items.Clear();
            List<SkillEffectMatcher.FamilyEntry> fams = SkillEffectMatcher.GetAllFamilies();
            for (int i = 0; i < fams.Count; i++)
            {
                SkillEffectMatcher.FamilyEntry f = fams[i];
                _cbAllFamilies.Items.Add(new ComboItem
                {
                    Text = string.Format("{0} [{1}:{2}]", f.CategoryCn, f.HitReactionType, f.HitReactionName),
                    Family = f
                });
            }
            _suppressComboEvents = false;
        }

        public void PlayByAnimationId(int animationId, string skillBadge)
        {
            SkillEffectMatcher.VariantEntry ve;
            SkillEffectMatcher.FamilyEntry fe;
            if (!SkillEffectMatcher.TryGetById(animationId, out ve, out fe))
            {
                return;
            }

            if (!string.IsNullOrEmpty(skillBadge))
            {
                _skillBadge = skillBadge;
            }
            else if (CurrentAnimationId != animationId)
            {
                _skillBadge = "";
            }

            CurrentAnimationId = ve.AnimationId;
            CurrentCnName = ve.CnName;
            CurrentFolderName = ve.FolderName;
            CurrentCategoryCn = fe.CategoryCn;
            CurrentHitReactionType = fe.HitReactionType;
            CurrentHitReactionName = fe.HitReactionName;

            LoadSpritesheet(ve.FolderName);
            SyncDropdowns(fe, ve);
            UpdateHeaderLabels();
            _canvas.Invalidate();
        }

        private void SyncDropdowns(SkillEffectMatcher.FamilyEntry fe, SkillEffectMatcher.VariantEntry activeVe)
        {
            _suppressComboEvents = true;
            try
            {
                for (int i = 0; i < _cbAllFamilies.Items.Count; i++)
                {
                    ComboItem item = _cbAllFamilies.Items[i] as ComboItem;
                    if (item != null && item.Family != null && item.Family.BaseKey == fe.BaseKey)
                    {
                        _cbAllFamilies.SelectedIndex = i;
                        break;
                    }
                }

                _cbColorVariants.Items.Clear();
                int selIdx = 0;
                int idx = 0;
                foreach (var kv in fe.Variants)
                {
                    SkillEffectMatcher.VariantEntry v = kv.Value;
                    _cbColorVariants.Items.Add(new ComboItem
                    {
                        Text = string.Format("[{0}] {1} ({2})", v.AnimationId, v.CnName, v.Color),
                        AnimationId = v.AnimationId,
                        Family = fe
                    });
                    if (v.AnimationId == activeVe.AnimationId) selIdx = idx;
                    idx++;
                }
                if (_cbColorVariants.Items.Count > 0)
                {
                    _cbColorVariants.SelectedIndex = selIdx;
                }
            }
            finally
            {
                _suppressComboEvents = false;
            }
        }

        private void OnColorVariantComboChanged()
        {
            if (_suppressComboEvents) return;
            ComboItem item = _cbColorVariants.SelectedItem as ComboItem;
            if (item != null && item.AnimationId >= 1001)
            {
                PlayByAnimationId(item.AnimationId, _skillBadge);
            }
        }

        private void OnFamilyComboChanged()
        {
            if (_suppressComboEvents) return;
            ComboItem item = _cbAllFamilies.SelectedItem as ComboItem;
            if (item != null && item.Family != null)
            {
                foreach (var kv in item.Family.Variants)
                {
                    PlayByAnimationId(kv.Value.AnimationId, _skillBadge);
                    break;
                }
            }
        }

        private void LoadSpritesheet(string folderName)
        {
            _frames.Clear();
            _curFrame = 0;
            if (_sheetBitmap != null)
            {
                _sheetBitmap.Dispose();
                _sheetBitmap = null;
            }

            if (string.IsNullOrEmpty(folderName)) return;

            string pngPath = ResolveAssetPath(folderName + ".png");
            string txtPath = ResolveAssetPath(folderName + ".txt");

            if (!string.IsNullOrEmpty(pngPath) && File.Exists(pngPath))
            {
                try
                {
                    byte[] bytes = File.ReadAllBytes(pngPath);
                    using (MemoryStream ms = new MemoryStream(bytes))
                    {
                        using (Image img = Image.FromStream(ms))
                        {
                            _sheetBitmap = new Bitmap(img);
                        }
                    }
                }
                catch { }
            }

            if (!string.IsNullOrEmpty(txtPath) && File.Exists(txtPath))
            {
                try
                {
                    string[] lines = File.ReadAllLines(txtPath, Encoding.UTF8);
                    for (int i = 0; i < lines.Length; i++)
                    {
                        string line = lines[i].Trim();
                        if (string.IsNullOrEmpty(line)) continue;
                        int eq = line.IndexOf('=');
                        if (eq < 0) continue;
                        string right = line.Substring(eq + 1).Trim();
                        string[] nums = right.Split(new char[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                        if (nums.Length < 4) continue;
                        int x, y, w, h;
                        if (int.TryParse(nums[0], out x) &&
                            int.TryParse(nums[1], out y) &&
                            int.TryParse(nums[2], out w) &&
                            int.TryParse(nums[3], out h))
                        {
                            if (w > 0 && h > 0)
                            {
                                _frames.Add(new Rectangle(x, y, w, h));
                            }
                        }
                    }
                }
                catch { }
            }

            if (_frames.Count == 0 && _sheetBitmap != null && _sheetBitmap.Height > 0)
            {
                int fh = _sheetBitmap.Height;
                int count = Math.Max(1, _sheetBitmap.Width / fh);
                int fw = _sheetBitmap.Width / count;
                for (int i = 0; i < count; i++)
                {
                    _frames.Add(new Rectangle(i * fw, 0, fw, fh));
                }
            }
        }

        private static string ResolveAssetPath(string fileName)
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string p1 = Path.Combine(baseDir, @"LegionBattle\LegionBattle\Assets\Effects\Spritesheets\" + fileName);
            if (File.Exists(p1)) return p1;

            string p2 = @"D:\123\LegionBattle\LegionBattle\Assets\Effects\Spritesheets\" + fileName;
            if (File.Exists(p2)) return p2;

            return "";
        }

        private void OnTimerTick(object sender, EventArgs e)
        {
            if (!_isPlaying || _frames.Count == 0 || !this.IsHandleCreated) return;
            _curFrame = (_curFrame + 1) % _frames.Count;
            UpdateHeaderLabels();
            _canvas.Invalidate();
        }

        private void TogglePlayPause()
        {
            _isPlaying = !_isPlaying;
            _btnPlayPause.Text = _isPlaying ? "⏸ 暂停" : "▶ 播放";
            UpdateHeaderLabels();
        }

        private void StepFrame(int delta)
        {
            if (_frames.Count == 0) return;
            _isPlaying = false;
            _btnPlayPause.Text = "▶ 播放";
            _curFrame = (_curFrame + delta + _frames.Count) % _frames.Count;
            UpdateHeaderLabels();
            _canvas.Invalidate();
        }

        private void ReplayFromStart()
        {
            _curFrame = 0;
            _isPlaying = true;
            _btnPlayPause.Text = "⏸ 暂停";
            UpdateHeaderLabels();
            _canvas.Invalidate();
        }

        private void OnFpsChanged()
        {
            int[] fpsMap = new int[] { 8, 12, 15, 20, 24 };
            int idx = _cbFps.SelectedIndex;
            if (idx >= 0 && idx < fpsMap.Length)
            {
                _fps = fpsMap[idx];
                _timer.Interval = Math.Max(20, 1000 / _fps);
                UpdateHeaderLabels();
            }
        }

        private void UpdateHeaderLabels()
        {
            string badge = string.IsNullOrEmpty(_skillBadge) ? "" : (_skillBadge + " ➔ ");
            _lblTitleLine1.Text = string.Format("{0}[{1}] {2} ({3}) | 受击:[{4}]{5}",
                badge, CurrentAnimationId, CurrentCnName, CurrentCategoryCn, CurrentHitReactionType, CurrentHitReactionName);

            int fw = (_frames.Count > 0 && _curFrame < _frames.Count) ? _frames[_curFrame].Width : 0;
            int fh = (_frames.Count > 0 && _curFrame < _frames.Count) ? _frames[_curFrame].Height : 0;
            _lblTitleLine2.Text = string.Format("{0} | 帧: {1}/{2} | 尺寸: {3}x{4}px | {5} FPS",
                CurrentFolderName,
                (_frames.Count > 0 ? _curFrame + 1 : 0),
                _frames.Count,
                fw,
                fh,
                _fps);
        }

        private void OnCanvasPaint(object sender, PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            int cw = _canvas.ClientSize.Width;
            int ch = _canvas.ClientSize.Height;
            if (cw <= 0 || ch <= 0) return;

            // 1. 绘制背景
            if (_bgMode == 1)
            {
                // 棋盘格
                int cell = 16;
                using (Brush b1 = new SolidBrush(Color.FromArgb(38, 40, 48)))
                using (Brush b2 = new SolidBrush(Color.FromArgb(52, 55, 65)))
                {
                    for (int y = 0; y < ch; y += cell)
                    {
                        for (int x = 0; x < cw; x += cell)
                        {
                            bool even = ((x / cell) + (y / cell)) % 2 == 0;
                            g.FillRectangle(even ? b1 : b2, x, y, cell, cell);
                        }
                    }
                }
            }
            else if (_bgMode == 2)
            {
                // 战场草地暗绿底
                using (LinearGradientBrush br = new LinearGradientBrush(
                    new Rectangle(0, 0, cw, ch),
                    Color.FromArgb(34, 52, 38),
                    Color.FromArgb(24, 38, 28),
                    LinearGradientMode.Vertical))
                {
                    g.FillRectangle(br, 0, 0, cw, ch);
                }
            }
            else
            {
                // 默认深邃暗场底
                g.Clear(Color.FromArgb(22, 24, 30));
            }

            // 2. 绘制十字准星参考线
            using (Pen gridPen = new Pen(Color.FromArgb(40, 255, 255, 255), 1f))
            {
                g.DrawLine(gridPen, cw / 2, 0, cw / 2, ch);
                g.DrawLine(gridPen, 0, ch / 2, cw, ch / 2);
            }

            // 3. 绘制像素动画当前帧
            if (_sheetBitmap != null && _frames.Count > 0)
            {
                if (_curFrame >= _frames.Count) _curFrame = 0;
                Rectangle src = _frames[_curFrame];

                float availW = Math.Max(32f, cw - 24f);
                float availH = Math.Max(32f, ch - 28f);
                float scaleX = availW / Math.Max(1, src.Width);
                float scaleY = availH / Math.Max(1, src.Height);
                float scale = Math.Min(scaleX, scaleY);
                if (scale > 3.5f) scale = 3.5f;
                if (scale < 0.5f) scale = 0.5f;

                int drawW = Math.Max(1, (int)Math.Round(src.Width * scale));
                int drawH = Math.Max(1, (int)Math.Round(src.Height * scale));
                int drawX = (cw - drawW) / 2;
                int drawY = (ch - 6 - drawH) / 2;

                g.InterpolationMode = InterpolationMode.NearestNeighbor;
                g.PixelOffsetMode = PixelOffsetMode.Half;
                g.SmoothingMode = SmoothingMode.None;

                g.DrawImage(_sheetBitmap, new Rectangle(drawX, drawY, drawW, drawH), src, GraphicsUnit.Pixel);

                // 底部帧进度条
                int barH = 4;
                using (Brush bgBar = new SolidBrush(Color.FromArgb(45, 50, 62)))
                using (Brush fgBar = new SolidBrush(Color.FromArgb(95, 195, 255)))
                {
                    g.FillRectangle(bgBar, 0, ch - barH, cw, barH);
                    int fillW = (int)Math.Round((cw * (_curFrame + 1.0)) / _frames.Count);
                    g.FillRectangle(fgBar, 0, ch - barH, fillW, barH);
                }
            }
            else
            {
                using (Brush txtBrush = new SolidBrush(Color.FromArgb(140, 150, 165)))
                {
                    string msg = "未找到特效精灵表文件";
                    SizeF sz = g.MeasureString(msg, this.Font);
                    g.DrawString(msg, this.Font, txtBrush, (cw - sz.Width) / 2f, (ch - sz.Height) / 2f);
                }
            }
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                if (_timer != null)
                {
                    _timer.Stop();
                    _timer.Dispose();
                    _timer = null;
                }
                if (_sheetBitmap != null)
                {
                    _sheetBitmap.Dispose();
                    _sheetBitmap = null;
                }
            }
            base.Dispose(disposing);
        }
    }
}

