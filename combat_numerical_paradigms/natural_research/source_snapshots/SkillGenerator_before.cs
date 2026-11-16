using System;
using System.Collections.Generic;
using System.Data;
using System.Drawing;
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

        // ─── UI 控件 (Tab 2: 前后字段设置) ───
        private ComboBox cbAffixCategory;
        private ComboBox cbConnectMode;
        private TextBox txtPrefixes;
        private TextBox txtSuffixes;
        private Label lblPrefixCount;
        private Label lblSuffixCount;
        private TextBox txtTestOutput;
        private int _currentCategoryIndex = 0;

        // ─── UI 控件 (Tab 3: 单抽与数值分析) ───
        private ComboBox cbConsoleRarity;
        private Button btnGenerateConsole;
        private Button btnBatchConsole;
        private TextBox txtConsoleSummary;
        private TextBox txtConsoleDetails;

        public SkillGeneratorForm()
        {
            this.Text = "战团技能配表工作台 & 数值生成器 (v2.5 - 前后字段自定义与随机组合引擎)";
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
            lblStatusFeedback.Location = new Point(920, 10);
            lblStatusFeedback.AutoSize = true;
            lblStatusFeedback.Font = new Font("Microsoft YaHei", 9F, FontStyle.Bold);
            lblStatusFeedback.ForeColor = Color.DarkGreen;

            pnlSearch.Controls.Add(lblSearch);
            pnlSearch.Controls.Add(txtSearch);
            pnlSearch.Controls.Add(btnClearSearch);
            pnlSearch.Controls.Add(lblStats);
            pnlSearch.Controls.Add(lblStatusFeedback);

            pnlTopBar.Controls.Add(pnlButtons);
            pnlTopBar.Controls.Add(pnlSearch);

            // 中间分割面板：上方 DataGridView，下方详细规则解读
            SplitContainer splitEditor = new SplitContainer();
            splitEditor.Dock = DockStyle.Fill;
            splitEditor.Orientation = Orientation.Horizontal;
            splitEditor.SplitterDistance = 530;
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

            // 下方详情框
            GroupBox grpDetail = new GroupBox();
            grpDetail.Text = "【选中技能实时规则与四维数值分析】(可直接在上方表格任意单元格内双击或按F2直接编辑修改)";
            grpDetail.Dock = DockStyle.Fill;
            grpDetail.Padding = new Padding(8);

            txtRowDetail = new TextBox();
            txtRowDetail.Multiline = true;
            txtRowDetail.ReadOnly = true;
            txtRowDetail.Dock = DockStyle.Fill;
            txtRowDetail.ScrollBars = ScrollBars.Vertical;
            txtRowDetail.BackColor = Color.FromArgb(250, 252, 255);
            txtRowDetail.Font = new Font("Consolas", 9.5F, FontStyle.Regular);
            grpDetail.Controls.Add(txtRowDetail);

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

            // 底部：随机组合即时测试控制台
            Panel pnlAffixBottom = new Panel();
            pnlAffixBottom.Dock = DockStyle.Bottom;
            pnlAffixBottom.Height = 150;
            pnlAffixBottom.Padding = new Padding(0, 8, 0, 0);

            GroupBox grpTest = new GroupBox();
            grpTest.Text = "【随机组合即时测试与效果验证】";
            grpTest.Dock = DockStyle.Fill;
            grpTest.Padding = new Padding(8);

            Button btnTestMix = new Button();
            btnTestMix.Text = "🎲 立即随机组合测试 (生成 10 个名字)";
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

            grpTest.Controls.Add(txtTestOutput);
            grpTest.Controls.Add(btnTestMix);
            pnlAffixBottom.Controls.Add(grpTest);

            tabAffixes.Controls.Add(splitAffix);
            tabAffixes.Controls.Add(pnlAffixBottom);
            tabAffixes.Controls.Add(pnlAffixTop);

            // 加载当前词库分类内容
            LoadAffixCategoryToView(0);

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
            btnClearConsole.Click += (s, e) => { txtConsoleSummary.Clear(); txtConsoleDetails.Clear(); };

            topPanelConsole.Controls.Add(lblConsoleRarity);
            topPanelConsole.Controls.Add(cbConsoleRarity);
            topPanelConsole.Controls.Add(btnGenerateConsole);
            topPanelConsole.Controls.Add(btnBatchConsole);
            topPanelConsole.Controls.Add(btnClearConsole);

            GroupBox grpSummary = new GroupBox();
            grpSummary.Text = "【生成结果概览】";
            grpSummary.Dock = DockStyle.Top;
            grpSummary.Height = 170;
            grpSummary.Padding = new Padding(10);

            txtConsoleSummary = new TextBox();
            txtConsoleSummary.Multiline = true;
            txtConsoleSummary.ReadOnly = true;
            txtConsoleSummary.Dock = DockStyle.Fill;
            txtConsoleSummary.ScrollBars = ScrollBars.Vertical;
            txtConsoleSummary.BackColor = Color.White;
            txtConsoleSummary.Font = new Font("Microsoft YaHei", 9.5F, FontStyle.Regular);
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
            grpDetails.Controls.Add(txtConsoleDetails);

            tabConsole.Controls.Add(grpDetails);
            tabConsole.Controls.Add(grpSummary);
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

            sb.AppendLine(string.Format("【技能编号: {0} | 技能名称: {1}】", id, name));
            sb.AppendLine(string.Format("▶ 描述文本: {0}", desc));
            sb.AppendLine(string.Format("▶ 战斗参数: 发动几率={0}% | 释放上限={1}次 | 主参数={2}% (类型={3}: {4}) | 参数2={5} | 命中触发={6}",
                chance, (times == "0" || times == "999" ? "无限制" : times), param, effType, FormatEffectTypeDesc(effType), (string.IsNullOrEmpty(param2) ? "无" : param2), needHit == "1" ? "是" : "否"));
            sb.AppendLine(string.Format("▶ 触发窗口: 回合条件={0} | 战力门槛={1} | 必中(无视闪避)={2} | 破防(无视免伤)={3}",
                FormatTurnCondText(t1, t2), (string.IsNullOrEmpty(bp2) ? "无限制" : string.Format("己方战力低于{0}%", bp2)), igDodge == "1" ? "是" : "否", igDef == "1" ? "是" : "否"));
            sb.AppendLine(string.Format("▶ 四维增益: 先机(speed)=+{0} | 坚韧(defense)=+{1} | 勇气(dodge)=+{2} | 魔力(authority)=+{3} | 动画ID={4}",
                spd, def, ddg, dom, anim));
            if (!string.IsNullOrEmpty(buf) || !string.IsNullOrEmpty(sealEff) || !string.IsNullOrEmpty(sealC2))
            {
                sb.AppendLine(string.Format("▶ 机制状态: BUFF_ID={0} | 封印效果={1} (持续{2}回合, 判定门槛={3})",
                    (string.IsNullOrEmpty(buf) ? "无" : buf), (string.IsNullOrEmpty(sealEff) ? "无" : sealEff), (string.IsNullOrEmpty(sealT) ? "0" : sealT), (string.IsNullOrEmpty(sealC2) ? "无" : sealC2)));
            }

            txtRowDetail.Text = sb.ToString();
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
            lblSuffixCount.Text = string.Format("当前包含: {0} 个后字段 (支持绑定受击效果: 斩:震退/1, 挑:击飞/2, 轰:后仰/3, 旋:旋转/4, 浪:掀飞/5, 爆:炸散/6, 压:压缩/7, 震:颠簸/8)", sLines.Length);
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
            sb.AppendLine(string.Format("=== [分类: {0}] 自定义前后字段 10 连随机组合测试 ===", cbAffixCategory.Text));
            for (int i = 1; i <= 10; i++)
            {
                string name = AffixManager.GenerateRandomName(genre);
                sb.AppendLine(string.Format("  #{0:D2}:  【{1}】", i, name));
            }

            txtTestOutput.Text = sb.ToString();
        }

        #endregion

        #region Tab 3 控制台单抽与分析

        private void GenerateConsoleSingle()
        {
            int tier = cbConsoleRarity.SelectedIndex;
            SkillRecord res = GeneratorEngine.Generate(tier);
            txtConsoleSummary.Text = res.SummaryText;
            txtConsoleDetails.Text = res.DetailText;
        }

        private void GenerateConsoleBatch()
        {
            StringBuilder sbSum = new StringBuilder();
            StringBuilder sbDet = new StringBuilder();

            int tier = cbConsoleRarity.SelectedIndex;
            for (int i = 1; i <= 10; i++)
            {
                SkillRecord res = GeneratorEngine.Generate(tier);
                sbSum.AppendLine(string.Format("===== 编号 #{0:D2} =====", i));
                sbSum.AppendLine(res.SummaryText);
                sbSum.AppendLine();

                sbDet.AppendLine(string.Format("==================== [#{0:D2}] {1} ({2}) ====================", i, res.SkillName, res.TierName));
                sbDet.AppendLine(res.DetailText);
                sbDet.AppendLine();
            }

            txtConsoleSummary.Text = sbSum.ToString();
            txtConsoleDetails.Text = sbDet.ToString();
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
                string name = m + b + c;

                if (c == "枪" || c == "眼" || c == "心" || c == "瞳" || c == "矢") { hitReactionType = 3; reactionName = "抛物线后仰"; }
                else if (c == "盾" || c == "骨" || c == "心" || c == "印") { hitReactionType = 7; reactionName = "手风琴压缩"; }
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
                string name = a + o + c;

                if (c == "枪" || c == "弓" || c == "矢") { hitReactionType = 3; reactionName = "抛物线后仰"; }
                else if (c == "盾" || c == "印" || c == "塔") { hitReactionType = 7; reactionName = "手风琴压缩"; }
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
                // 范式 3：宏大长句诗意式 (2+2+2=6字，如: 撕裂天空之剑、贯穿星辰之枪、守护终末之盾)
                string ev = EpicVerbs[_rand.Next(EpicVerbs.Count)];
                string et = EpicTargets[_rand.Next(EpicTargets.Count)];
                string er = EpicRelics[_rand.Next(EpicRelics.Count)];
                string name = ev + et + er;

                if (er.Contains("枪") || er.Contains("箭")) { hitReactionType = 3; reactionName = "抛物线后仰"; }
                else if (er.Contains("盾") || er.Contains("锁") || er.Contains("牢") || er.Contains("铠")) { hitReactionType = 7; reactionName = "手风琴压缩"; }
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

            // 13. 组装自然语言技能描述
            string effectText = BuildEffectText(genre, triggerChance, baseParam, timesLimit, turnCond1, turnCond2, selfBpCond2, hasSubEffect, subDesc, iniBonus, ignoreDefPercent);

            // 14. 组装输出文本与实体记录 (清爽纯净，不输出底层CSV代码)
            SkillRecord record = new SkillRecord();
            record.TierName = tierName;
            record.SkillName = skillName;
            record.EffectDesc = effectText;
            record.HitReactionType = hitReactionType;
            record.HitReactionName = reactionName;

            StringBuilder sbSum = new StringBuilder();
            sbSum.AppendLine(string.Format("稀有度:   {0}", tierName));
            sbSum.AppendLine(string.Format("技能类型: {0}", genre));
            sbSum.AppendLine(string.Format("技能名字: 《{0}》", skillName));
            sbSum.AppendLine(string.Format("技能效果: {0}", effectText));
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

            string animId = "142";
            if (genre == "勇气" || genre.Contains("暴击")) animId = "166";
            else if (genre == "先机" || genre.Contains("精准")) animId = "150";
            else if (genre == "坚韧" || genre.Contains("恢复")) animId = "32";
            else if (genre == "魔力") animId = "171";
            record.CsvData["animation_id"] = animId;

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

        private static int GetStatBudget(int tier)
        {
            switch (tier)
            {
                case 1: return 0;
                case 2: return _rand.Next(1, 3);
                case 3: return _rand.Next(3, 5);
                case 4: return _rand.Next(5, 8);
                case 5: return _rand.Next(8, 12);
                case 6: return _rand.Next(12, 17);
                default: return 5;
            }
        }

        private static string GetStatBudgetDesc(int tier)
        {
            switch (tier)
            {
                case 1: return "0 点";
                case 2: return "1 ~ 2 点";
                case 3: return "3 ~ 4 点";
                case 4: return "5 ~ 7 点";
                case 5: return "8 ~ 11 点";
                case 6: return "12 ~ 16 点";
                default: return "0 ~ 16 点";
            }
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
                courage = (int)Math.Round(total * 0.60);
                magic = (int)Math.Round(total * 0.20);
                initiative = (int)Math.Round(total * 0.10);
                resilience = total - courage - magic - initiative;
            }
            else if (genre == "先机" || genre.Contains("精准"))
            {
                initiative = (int)Math.Round(total * 0.60);
                courage = (int)Math.Round(total * 0.20);
                magic = (int)Math.Round(total * 0.10);
                resilience = total - initiative - courage - magic;
            }
            else if (genre == "坚韧" || genre.Contains("恢复"))
            {
                resilience = (int)Math.Round(total * 0.60);
                courage = (int)Math.Round(total * 0.20);
                initiative = (int)Math.Round(total * 0.10);
                magic = total - resilience - courage - initiative;
            }
            else // 魔力
            {
                magic = (int)Math.Round(total * 0.60);
                resilience = (int)Math.Round(total * 0.20);
                initiative = (int)Math.Round(total * 0.10);
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
}
