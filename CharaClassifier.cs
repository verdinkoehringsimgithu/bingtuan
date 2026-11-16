using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

namespace LegionBattle.CharaClassifier
{
    public struct StandardizeResult
    {
        public bool WasOpaque;
        public bool WasNonStandardDim;
        public bool WasFloating;
        public bool WasRescaled;
        public bool Success;
        public string ErrorMessage;
    }

    public static class SpriteStandardizer
    {
        public static Bitmap Standardize(Bitmap src, ref StandardizeResult info)
        {
            int w = src.Width;
            int h = src.Height;

            if (w != 128 || h != 192)
            {
                info.WasNonStandardDim = true;
            }

            // Step 1: Clone to 32bpp ARGB
            Bitmap copy = new Bitmap(w, h, PixelFormat.Format32bppArgb);
            using (Graphics g = Graphics.FromImage(copy))
            {
                g.DrawImage(src, 0, 0, w, h);
            }

            // Step 2: Flood-fill background if opaque
            bool removedBg = MakeTransparent(copy, 18);
            if (removedBg)
            {
                info.WasOpaque = true;
            }

            // If already 128x192, 192x192 (48x48 cell), 96x96 (24x24 cell), or 364x336 (91x84 cell), keep 100% native
            if ((w == 128 && h == 192) || (w == 192 && h == 192) || (w == 96 && h == 96) || (w == 364 && h == 336))
            {
                return copy;
            }

            // If 128x128 (4 rows of 32x32), ground feet to y=47, zero horizontal shift
            if (w == 128 && h == 128)
            {
                Bitmap result128 = new Bitmap(128, 192, PixelFormat.Format32bppArgb);
                using (Graphics g = Graphics.FromImage(result128))
                {
                    g.InterpolationMode = InterpolationMode.NearestNeighbor;
                    g.PixelOffsetMode = PixelOffsetMode.Half;
                    for (int row = 0; row < 4; row++)
                    {
                        g.DrawImage(copy, new Rectangle(0, row * 48 + 16, 128, 32), new Rectangle(0, row * 32, 128, 32), GraphicsUnit.Pixel);
                    }
                }
                copy.Dispose();
                return result128;
            }

            // If 128..132 x 191..194, trim border to 128x192 without shifting internal pixels
            if (w >= 128 && w <= 132 && h >= 191 && h <= 194)
            {
                Bitmap resultTrim = new Bitmap(128, 192, PixelFormat.Format32bppArgb);
                using (Graphics g = Graphics.FromImage(resultTrim))
                {
                    g.InterpolationMode = InterpolationMode.NearestNeighbor;
                    g.PixelOffsetMode = PixelOffsetMode.Half;
                    g.DrawImage(copy, new Rectangle(0, 0, 128, 192), new Rectangle(0, 0, Math.Min(128, w), Math.Min(192, h)), GraphicsUnit.Pixel);
                }
                copy.Dispose();
                return resultTrim;
            }

            // Check if 3-frame sheet (e.g. 96w)
            bool is3Frame = (w % 3 == 0) && (w % 4 != 0 || w == 96 || w == 72 || w == 144);
            int srcCols = is3Frame ? 3 : 4;
            int cw = Math.Max(1, w / srcCols);
            int ch = Math.Max(1, h / 4);

            int targetFrameW = 32;
            int targetFrameH = 48;
            Bitmap result = new Bitmap(targetFrameW * 4, targetFrameH * 4, PixelFormat.Format32bppArgb);

            BitmapData srcData = copy.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
            int stride = srcData.Stride;
            byte[] srcBytes = new byte[Math.Abs(stride) * h];
            Marshal.Copy(srcData.Scan0, srcBytes, 0, srcBytes.Length);
            copy.UnlockBits(srcData);

            using (Graphics g = Graphics.FromImage(result))
            {
                g.InterpolationMode = InterpolationMode.NearestNeighbor;
                g.PixelOffsetMode = PixelOffsetMode.Half;
                g.SmoothingMode = SmoothingMode.None;

                for (int row = 0; row < 4; row++)
                {
                    Rectangle[] bboxes = new Rectangle[srcCols];
                    bool[] hasBbox = new bool[srcCols];

                    for (int col = 0; col < srcCols; col++)
                    {
                        int cellX = col * cw;
                        int cellY = row * ch;
                        Rectangle bbox = FindCellBbox(srcBytes, w, h, stride, cellX, cellY, cw, ch);
                        if (bbox.Width > 0 && bbox.Height > 0)
                        {
                            bboxes[col] = bbox;
                            hasBbox[col] = true;
                        }
                    }

                    int[] frameOrder = is3Frame ? new int[] { 0, 1, 2, 1 } : new int[] { 0, 1, 2, 3 };

                    // 2-frame or 1-frame fallback
                    if (is3Frame)
                    {
                        if (hasBbox[1] && !hasBbox[0] && !hasBbox[2])
                        {
                            frameOrder = new int[] { 1, 1, 1, 1 };
                        }
                        else if (hasBbox[0] && hasBbox[1] && !hasBbox[2])
                        {
                            frameOrder = new int[] { 0, 1, 0, 1 };
                        }
                    }

                    float scale = Math.Min(32.0f / cw, 48.0f / ch);
                    if (scale > 1.0f) scale = 1.0f;

                    for (int dstCol = 0; dstCol < 4; dstCol++)
                    {
                        int srcCol = frameOrder[dstCol];
                        if (srcCol >= srcCols || !hasBbox[srcCol]) continue;

                        Rectangle srcCellRect = new Rectangle(srcCol * cw, row * ch, cw, ch);
                        int scaledW = (int)Math.Round(cw * scale);
                        int scaledH = (int)Math.Round(ch * scale);
                        if (scaledW < 1) scaledW = 1;
                        if (scaledH < 1) scaledH = 1;

                        int dstX = dstCol * targetFrameW + (targetFrameW - scaledW) / 2;
                        int dstY = row * targetFrameH + (targetFrameH - scaledH);

                        g.DrawImage(copy, new Rectangle(dstX, dstY, scaledW, scaledH), srcCellRect, GraphicsUnit.Pixel);
                    }
                }
            }

            copy.Dispose();
            return result;
        }

        public static StandardizeResult StandardizeFile(string srcPath, string destPath)
        {
            StandardizeResult res = new StandardizeResult();
            try
            {
                byte[] bytes = File.ReadAllBytes(srcPath);
                using (MemoryStream ms = new MemoryStream(bytes))
                using (Bitmap raw = new Bitmap(ms))
                {
                    using (Bitmap std = Standardize(raw, ref res))
                    {
                        string dir = Path.GetDirectoryName(destPath);
                        if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);

                        string tempPath = destPath + ".tmp_" + Guid.NewGuid().ToString("N");
                        std.Save(tempPath, ImageFormat.Png);

                        if (File.Exists(destPath)) File.Delete(destPath);
                        File.Move(tempPath, destPath);
                    }
                }
                res.Success = true;
            }
            catch (Exception ex)
            {
                res.Success = false;
                res.ErrorMessage = ex.Message;
            }
            return res;
        }

        public static Dictionary<string, int> BatchStandardize(string baseDir, Action<int, int, string> progressCallback)
        {
            Dictionary<string, int> stats = new Dictionary<string, int>();
            stats["total"] = 0;
            stats["opaque"] = 0;
            stats["dim"] = 0;
            stats["float"] = 0;
            stats["rescale"] = 0;

            List<string> allFiles = new List<string>();
            string[] subdirs = new string[] { "", "1", "2", "3", "4", "5", "6", "SP", "不合格" };
            foreach (var sub in subdirs)
            {
                string p = string.IsNullOrEmpty(sub) ? baseDir : Path.Combine(baseDir, sub);
                if (Directory.Exists(p))
                {
                    allFiles.AddRange(Directory.GetFiles(p, "*.png", SearchOption.TopDirectoryOnly));
                }
            }

            int total = allFiles.Count;
            for (int i = 0; i < total; i++)
            {
                string file = allFiles[i];
                StandardizeResult res = StandardizeFile(file, file);
                if (res.Success)
                {
                    stats["total"]++;
                    if (res.WasOpaque) stats["opaque"]++;
                    if (res.WasNonStandardDim) stats["dim"]++;
                    if (res.WasFloating) stats["float"]++;
                    if (res.WasRescaled) stats["rescale"]++;
                }
                if (progressCallback != null)
                {
                    progressCallback(i + 1, total, file);
                }
            }

            return stats;
        }

        private static Rectangle FindCellBbox(byte[] bytes, int totalW, int totalH, int stride, int cx, int cy, int cw, int ch)
        {
            int minX = int.MaxValue;
            int minY = int.MaxValue;
            int maxX = int.MinValue;
            int maxY = int.MinValue;

            int limitX = Math.Min(totalW, cx + cw);
            int limitY = Math.Min(totalH, cy + ch);

            for (int y = cy; y < limitY; y++)
            {
                int rowOffset = y * stride;
                for (int x = cx; x < limitX; x++)
                {
                    byte a = bytes[rowOffset + x * 4 + 3];
                    if (a > 10)
                    {
                        if (x < minX) minX = x;
                        if (x > maxX) maxX = x;
                        if (y < minY) minY = y;
                        if (y > maxY) maxY = y;
                    }
                }
            }

            if (minX == int.MaxValue) return Rectangle.Empty;

            return new Rectangle(minX, minY, maxX - minX + 1, maxY - minY + 1);
        }

        private static bool MakeTransparent(Bitmap bmp, int tolerance)
        {
            int w = bmp.Width;
            int h = bmp.Height;

            BitmapData bmpData = bmp.LockBits(new Rectangle(0, 0, w, h),
                ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);

            int stride = bmpData.Stride;
            IntPtr scan0 = bmpData.Scan0;
            int totalBytes = Math.Abs(stride) * h;
            byte[] raw = new byte[totalBytes];
            Marshal.Copy(scan0, raw, 0, totalBytes);

            int[] cornerIdxs = new int[] {
                0,
                (w - 1) * 4,
                (h - 1) * stride,
                (h - 1) * stride + (w - 1) * 4
            };

            bool needsRemoval = false;
            foreach (int idx in cornerIdxs)
            {
                if (raw[idx + 3] == 255)
                {
                    needsRemoval = true;
                    break;
                }
            }

            if (!needsRemoval)
            {
                bmp.UnlockBits(bmpData);
                return false;
            }

            int bgB = raw[cornerIdxs[0]];
            int bgG = raw[cornerIdxs[0] + 1];
            int bgR = raw[cornerIdxs[0] + 2];

            bool[] visited = new bool[w * h];
            Queue<int> queue = new Queue<int>();

            for (int x = 0; x < w; x++)
            {
                SeedIfBg(x, 0, w, h, stride, raw, bgR, bgG, bgB, tolerance, visited, queue);
                SeedIfBg(x, h - 1, w, h, stride, raw, bgR, bgG, bgB, tolerance, visited, queue);
            }
            for (int y = 0; y < h; y++)
            {
                SeedIfBg(0, y, w, h, stride, raw, bgR, bgG, bgB, tolerance, visited, queue);
                SeedIfBg(w - 1, y, w, h, stride, raw, bgR, bgG, bgB, tolerance, visited, queue);
            }

            int cw = w / 4;
            int ch = h / 4;
            for (int r = 0; r < 4; r++)
            {
                for (int c = 0; c < 4; c++)
                {
                    int cx = c * cw;
                    int cy = r * ch;
                    for (int x = cx; x < Math.Min(w, cx + cw); x++)
                    {
                        SeedIfBg(x, cy, w, h, stride, raw, bgR, bgG, bgB, tolerance, visited, queue);
                        SeedIfBg(x, Math.Min(h - 1, cy + ch - 1), w, h, stride, raw, bgR, bgG, bgB, tolerance, visited, queue);
                    }
                    for (int y = cy; y < Math.Min(h, cy + ch); y++)
                    {
                        SeedIfBg(cx, y, w, h, stride, raw, bgR, bgG, bgB, tolerance, visited, queue);
                        SeedIfBg(Math.Min(w - 1, cx + cw - 1), y, w, h, stride, raw, bgR, bgG, bgB, tolerance, visited, queue);
                    }
                }
            }

            int[] dx = new int[] { -1, 1, 0, 0 };
            int[] dy = new int[] { 0, 0, -1, 1 };

            while (queue.Count > 0)
            {
                int node = queue.Dequeue();
                int nx = node % w;
                int ny = node / w;

                int p = ny * stride + nx * 4;
                raw[p + 3] = 0; // Alpha = 0

                for (int i = 0; i < 4; i++)
                {
                    int adjX = nx + dx[i];
                    int adjY = ny + dy[i];
                    if (adjX >= 0 && adjX < w && adjY >= 0 && adjY < h)
                    {
                        int adjNode = adjY * w + adjX;
                        if (!visited[adjNode])
                        {
                            int ap = adjY * stride + adjX * 4;
                            byte aa = raw[ap + 3];
                            bool isBackground = (aa < 200) ||
                                (Math.Abs(raw[ap + 2] - bgR) <= tolerance &&
                                 Math.Abs(raw[ap + 1] - bgG) <= tolerance &&
                                 Math.Abs(raw[ap] - bgB) <= tolerance);

                            if (isBackground)
                            {
                                visited[adjNode] = true;
                                queue.Enqueue(adjNode);
                            }
                        }
                    }
                }
            }

            Marshal.Copy(raw, 0, scan0, totalBytes);
            bmp.UnlockBits(bmpData);
            return true;
        }

        private static void SeedIfBg(int x, int y, int w, int h, int stride, byte[] raw, int bgR, int bgG, int bgB, int tolerance, bool[] visited, Queue<int> queue)
        {
            int node = y * w + x;
            if (visited[node]) return;

            int p = y * stride + x * 4;
            byte a = raw[p + 3];
            bool isBackground = (a < 200) ||
                (Math.Abs(raw[p + 2] - bgR) <= tolerance &&
                 Math.Abs(raw[p + 1] - bgG) <= tolerance &&
                 Math.Abs(raw[p] - bgB) <= tolerance);

            if (isBackground)
            {
                visited[node] = true;
                queue.Enqueue(node);
            }
        }
    }

    public class ClassifyHistoryItem
    {
        public string FileName;
        public string SourcePath;
        public string DestPath;
        public string Tag;
        public string OldTag;
    }

    public class ClassifierForm : Form
    {
        private string charaDir;
        private string csvPath;
        private string jsonPath;

        private List<string> pendingFiles = new List<string>();
        private int currentIndex = 0;
        private string currentCategoryKey = ""; // "" = 待处理, "1".."6", "SP", "不合格", "ALL"
        private Stack<ClassifyHistoryItem> history = new Stack<ClassifyHistoryItem>();
        private Dictionary<string, int> tagStats = new Dictionary<string, int>();

        private Bitmap currentFullBitmap = null;
        private Bitmap[] walkFrames = new Bitmap[4];
        private int currentFrame = 0;
        private Timer animTimer;

        // UI Controls
        private Label lblFileName;
        private Label lblProgress;
        private Label lblStats;
        private CheckBox chkAutoFix;

        private FlowLayoutPanel flowReviewTabs;
        private Dictionary<string, Button> tabButtons = new Dictionary<string, Button>();

        private Panel previewPanel;
        private PictureBox picWalk;
        private Panel panelDir;
        private Button[] dirButtons = new Button[4];
        private Button btnAutoRotate;
        private int currentDirectionRow = 0;
        private bool autoRotate = false;
        private PictureBox picSheet;

        private Button btn1;
        private Button btn2;
        private Button btn3;
        private Button btn4;
        private Button btn5;
        private Button btn6;
        private Button btnSP;
        private Button btnReject;

        private Button btnPrev;
        private Button btnNext;
        private Button btnUndo;
        private Button btnFixCurrent;
        private Button btnBatchFix;

        public ClassifierForm(string targetDir)
        {
            InitializeData(targetDir);
            InitializeUI();
            
            // 优先检查待分类文件，若待分类有文件则默认进入“待分类”，否则进入“重审 1”
            int unclassified = 0;
            if (Directory.Exists(charaDir))
            {
                unclassified = Directory.GetFiles(charaDir, "*.png", SearchOption.TopDirectoryOnly).Length;
            }
            if (unclassified > 0)
            {
                SelectCategoryTab("");
            }
            else
            {
                SelectCategoryTab("1");
            }
        }

        private void InitializeData(string targetDir)
        {
            if (!string.IsNullOrEmpty(targetDir) && Directory.Exists(targetDir))
            {
                charaDir = Path.GetFullPath(targetDir);
            }
            else if (Directory.Exists(@"D:\123\CHARA"))
            {
                charaDir = @"D:\123\CHARA";
            }
            else if (Directory.Exists("CHARA"))
            {
                charaDir = Path.GetFullPath("CHARA");
            }
            else
            {
                charaDir = AppDomain.CurrentDomain.BaseDirectory;
            }

            csvPath = Path.Combine(charaDir, "chara_classification.csv");
            jsonPath = Path.Combine(charaDir, "chara_classification.json");

            string[] tags = new string[] { "1", "2", "3", "4", "5", "6", "SP", "不合格" };
            foreach (var t in tags)
            {
                tagStats[t] = 0;
            }

            RefreshDirectoryStats();
        }

        private void RefreshDirectoryStats()
        {
            string[] tags = new string[] { "1", "2", "3", "4", "5", "6", "SP", "不合格" };
            foreach (var t in tags)
            {
                string sub = Path.Combine(charaDir, t);
                if (Directory.Exists(sub))
                {
                    tagStats[t] = Directory.GetFiles(sub, "*.png", SearchOption.TopDirectoryOnly).Length;
                }
                else
                {
                    tagStats[t] = 0;
                }
            }
        }

        private void InitializeUI()
        {
            this.Text = "角色行走图分类与重审工具";
            this.Size = new Size(880, 740);
            this.MinimumSize = new Size(840, 700);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.Font = new Font("Microsoft YaHei", 9.5F, FontStyle.Regular);
            this.BackColor = Color.FromArgb(245, 246, 248);
            this.KeyPreview = true;
            this.KeyDown += ClassifierForm_KeyDown;

            // 顶部信息与重审导航区
            Panel topPanel = new Panel();
            topPanel.Dock = DockStyle.Top;
            topPanel.Height = 115;
            topPanel.Padding = new Padding(14, 8, 14, 6);
            topPanel.BackColor = Color.White;

            lblFileName = new Label();
            lblFileName.Font = new Font("Microsoft YaHei", 12F, FontStyle.Bold);
            lblFileName.ForeColor = Color.FromArgb(33, 37, 41);
            lblFileName.Location = new Point(14, 8);
            lblFileName.AutoSize = true;

            lblProgress = new Label();
            lblProgress.Font = new Font("Microsoft YaHei", 9.5F, FontStyle.Regular);
            lblProgress.ForeColor = Color.FromArgb(108, 117, 125);
            lblProgress.Location = new Point(14, 34);
            lblProgress.AutoSize = true;

            // 重审模式快捷切换栏
            flowReviewTabs = new FlowLayoutPanel();
            flowReviewTabs.Location = new Point(12, 58);
            flowReviewTabs.Size = new Size(840, 32);
            flowReviewTabs.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            flowReviewTabs.FlowDirection = FlowDirection.LeftToRight;
            flowReviewTabs.WrapContents = false;

            CreateTabButton("", "待分类");
            CreateTabButton("1", "重审 1");
            CreateTabButton("2", "重审 2");
            CreateTabButton("3", "重审 3");
            CreateTabButton("4", "重审 4");
            CreateTabButton("5", "重审 5");
            CreateTabButton("6", "重审 6");
            CreateTabButton("SP", "SP");
            CreateTabButton("不合格", "不合格");

            lblStats = new Label();
            lblStats.Font = new Font("Consolas", 9.0F, FontStyle.Regular);
            lblStats.ForeColor = Color.FromArgb(90, 95, 102);
            lblStats.Location = new Point(14, 94);
            lblStats.AutoSize = true;

            topPanel.Controls.Add(lblFileName);
            topPanel.Controls.Add(lblProgress);
            topPanel.Controls.Add(flowReviewTabs);
            topPanel.Controls.Add(lblStats);

            // 底部操作按钮栏
            Panel bottomPanel = new Panel();
            bottomPanel.Dock = DockStyle.Bottom;
            bottomPanel.Height = 110;
            bottomPanel.Padding = new Padding(14, 8, 14, 10);
            bottomPanel.BackColor = Color.White;

            // 主分类与重审按钮
            FlowLayoutPanel flowButtons = new FlowLayoutPanel();
            flowButtons.Dock = DockStyle.Top;
            flowButtons.Height = 48;
            flowButtons.FlowDirection = FlowDirection.LeftToRight;
            flowButtons.WrapContents = false;

            btn1 = CreateTagButton("1", Color.FromArgb(238, 238, 238), Color.Black);
            btn2 = CreateTagButton("2", Color.FromArgb(220, 245, 220), Color.FromArgb(0, 100, 0));
            btn3 = CreateTagButton("3", Color.FromArgb(220, 235, 252), Color.FromArgb(0, 70, 180));
            btn4 = CreateTagButton("4", Color.FromArgb(243, 225, 250), Color.FromArgb(110, 30, 150));
            btn5 = CreateTagButton("5", Color.FromArgb(255, 243, 205), Color.FromArgb(160, 100, 0));
            btn6 = CreateTagButton("6", Color.FromArgb(254, 225, 225), Color.FromArgb(180, 20, 20));
            btnSP = CreateTagButton("SP", Color.FromArgb(220, 248, 248), Color.FromArgb(0, 120, 130));
            btnReject = CreateTagButton("不合格", Color.FromArgb(240, 240, 240), Color.FromArgb(120, 120, 120));

            btn1.Click += (s, e) => ApplyClassification("1");
            btn2.Click += (s, e) => ApplyClassification("2");
            btn3.Click += (s, e) => ApplyClassification("3");
            btn4.Click += (s, e) => ApplyClassification("4");
            btn5.Click += (s, e) => ApplyClassification("5");
            btn6.Click += (s, e) => ApplyClassification("6");
            btnSP.Click += (s, e) => ApplyClassification("SP");
            btnReject.Click += (s, e) => ApplyClassification("不合格");

            flowButtons.Controls.AddRange(new Control[] {
                btn1, btn2, btn3, btn4, btn5, btn6, btnSP, btnReject
            });

            // 辅助与标准化操作栏
            Panel utilPanel = new Panel();
            utilPanel.Dock = DockStyle.Bottom;
            utilPanel.Height = 42;

            chkAutoFix = new CheckBox();
            chkAutoFix.Text = "自动标准化";
            chkAutoFix.Checked = true;
            chkAutoFix.AutoSize = true;
            chkAutoFix.Location = new Point(4, 10);
            chkAutoFix.Font = new Font("Microsoft YaHei", 9.5F);
            chkAutoFix.TabStop = false;

            btnFixCurrent = new Button();
            btnFixCurrent.Text = "修复当前";
            btnFixCurrent.Size = new Size(88, 30);
            btnFixCurrent.Location = new Point(115, 5);
            btnFixCurrent.BackColor = Color.FromArgb(235, 245, 255);
            btnFixCurrent.FlatStyle = FlatStyle.Flat;
            btnFixCurrent.FlatAppearance.BorderColor = Color.FromArgb(180, 210, 240);
            btnFixCurrent.TabStop = false;
            btnFixCurrent.Click += (s, e) => FixCurrentFile();

            btnBatchFix = new Button();
            btnBatchFix.Text = "全量标准化";
            btnBatchFix.Size = new Size(95, 30);
            btnBatchFix.Location = new Point(208, 5);
            btnBatchFix.BackColor = Color.FromArgb(230, 250, 235);
            btnBatchFix.FlatStyle = FlatStyle.Flat;
            btnBatchFix.FlatAppearance.BorderColor = Color.FromArgb(160, 220, 180);
            btnBatchFix.TabStop = false;
            btnBatchFix.Click += (s, e) => RunBatchFixFromUI();

            btnUndo = new Button();
            btnUndo.Text = "撤销";
            btnUndo.Size = new Size(76, 30);
            btnUndo.Location = new Point(bottomPanel.ClientSize.Width - 100, 5);
            btnUndo.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            btnUndo.BackColor = Color.FromArgb(240, 240, 240);
            btnUndo.FlatStyle = FlatStyle.Flat;
            btnUndo.FlatAppearance.BorderColor = Color.FromArgb(200, 200, 200);
            btnUndo.TabStop = false;
            btnUndo.Click += (s, e) => UndoLast();

            btnNext = new Button();
            btnNext.Text = "下一张";
            btnNext.Size = new Size(76, 30);
            btnNext.Location = new Point(bottomPanel.ClientSize.Width - 182, 5);
            btnNext.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            btnNext.BackColor = Color.FromArgb(240, 240, 240);
            btnNext.FlatStyle = FlatStyle.Flat;
            btnNext.FlatAppearance.BorderColor = Color.FromArgb(200, 200, 200);
            btnNext.TabStop = false;
            btnNext.Click += (s, e) => NextFile();

            btnPrev = new Button();
            btnPrev.Text = "上一张";
            btnPrev.Size = new Size(76, 30);
            btnPrev.Location = new Point(bottomPanel.ClientSize.Width - 264, 5);
            btnPrev.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            btnPrev.BackColor = Color.FromArgb(240, 240, 240);
            btnPrev.FlatStyle = FlatStyle.Flat;
            btnPrev.FlatAppearance.BorderColor = Color.FromArgb(200, 200, 200);
            btnPrev.TabStop = false;
            btnPrev.Click += (s, e) => PrevFile();

            utilPanel.Controls.Add(chkAutoFix);
            utilPanel.Controls.Add(btnFixCurrent);
            utilPanel.Controls.Add(btnBatchFix);
            utilPanel.Controls.Add(btnPrev);
            utilPanel.Controls.Add(btnNext);
            utilPanel.Controls.Add(btnUndo);

            bottomPanel.Controls.Add(utilPanel);
            bottomPanel.Controls.Add(flowButtons);

            // 中间展示区
            previewPanel = new Panel();
            previewPanel.Dock = DockStyle.Fill;
            previewPanel.Padding = new Padding(20);
            previewPanel.BackColor = Color.FromArgb(235, 238, 242);
            previewPanel.Resize += PreviewPanel_Resize;

            picWalk = new PictureBox();
            picWalk.Size = new Size(250, 330);
            picWalk.BackColor = Color.FromArgb(250, 250, 250);
            picWalk.BorderStyle = BorderStyle.FixedSingle;
            picWalk.Paint += PicWalk_Paint;

            // 方向切换工具栏 (正面/向左/向右/背面/巡转)
            panelDir = new Panel();
            panelDir.Size = new Size(250, 34);
            panelDir.BackColor = Color.Transparent;

            string[] dirNames = new string[] { "正面", "向左", "向右", "背面" };
            int btnW = 46;
            int btnH = 30;
            int margin = 4;
            for (int i = 0; i < 4; i++)
            {
                int r = i;
                Button b = new Button();
                b.Text = dirNames[i];
                b.Size = new Size(btnW, btnH);
                b.Location = new Point(i * (btnW + margin), 2);
                b.Font = new Font("Microsoft YaHei", 9.0F);
                b.FlatStyle = FlatStyle.Flat;
                b.TabStop = false;
                b.Click += (s, e) => SetDirection(r);
                dirButtons[i] = b;
                panelDir.Controls.Add(b);
            }

            btnAutoRotate = new Button();
            btnAutoRotate.Text = "巡转";
            btnAutoRotate.Size = new Size(btnW, btnH);
            btnAutoRotate.Location = new Point(4 * (btnW + margin), 2);
            btnAutoRotate.Font = new Font("Microsoft YaHei", 9.0F);
            btnAutoRotate.FlatStyle = FlatStyle.Flat;
            btnAutoRotate.TabStop = false;
            btnAutoRotate.Click += (s, e) => ToggleAutoRotate();
            panelDir.Controls.Add(btnAutoRotate);
            UpdateDirButtonStyles();

            picSheet = new PictureBox();
            picSheet.Size = new Size(280, 400);
            picSheet.BackColor = Color.FromArgb(250, 250, 250);
            picSheet.BorderStyle = BorderStyle.FixedSingle;
            picSheet.Paint += PicSheet_Paint;

            previewPanel.Controls.Add(picWalk);
            previewPanel.Controls.Add(panelDir);
            previewPanel.Controls.Add(picSheet);

            this.Controls.Add(previewPanel);
            this.Controls.Add(bottomPanel);
            this.Controls.Add(topPanel);

            animTimer = new Timer();
            animTimer.Interval = 160;
            animTimer.Tick += AnimTimer_Tick;
            animTimer.Start();
        }

        private void CreateTabButton(string key, string label)
        {
            Button btn = new Button();
            btn.Text = label;
            btn.Size = new Size(88, 28);
            btn.Margin = new Padding(2, 0, 2, 0);
            btn.BackColor = Color.FromArgb(245, 245, 245);
            btn.ForeColor = Color.FromArgb(60, 60, 60);
            btn.Font = new Font("Microsoft YaHei", 9.0F);
            btn.FlatStyle = FlatStyle.Flat;
            btn.FlatAppearance.BorderColor = Color.FromArgb(210, 210, 210);
            btn.TabStop = false;
            btn.Click += (s, e) => SelectCategoryTab(key);

            tabButtons[key] = btn;
            flowReviewTabs.Controls.Add(btn);
        }

        private void SelectCategoryTab(string key)
        {
            currentCategoryKey = key;

            // 更新选项卡样式
            foreach (var kv in tabButtons)
            {
                if (kv.Key == key)
                {
                    kv.Value.BackColor = Color.FromArgb(0, 120, 215);
                    kv.Value.ForeColor = Color.White;
                    kv.Value.FlatAppearance.BorderColor = Color.FromArgb(0, 90, 180);
                }
                else
                {
                    kv.Value.BackColor = Color.FromArgb(245, 245, 245);
                    kv.Value.ForeColor = Color.FromArgb(60, 60, 60);
                    kv.Value.FlatAppearance.BorderColor = Color.FromArgb(210, 210, 210);
                }
            }

            LoadCategoryFiles(key);
        }

        private void UpdateTabButtonLabels()
        {
            int unclassified = 0;
            if (Directory.Exists(charaDir))
            {
                unclassified = Directory.GetFiles(charaDir, "*.png", SearchOption.TopDirectoryOnly).Length;
            }

            if (tabButtons.ContainsKey(""))
            {
                tabButtons[""].Text = string.Format("待分类({0})", unclassified);
            }

            string[] tags = new string[] { "1", "2", "3", "4", "5", "6", "SP", "不合格" };
            foreach (var t in tags)
            {
                if (tabButtons.ContainsKey(t))
                {
                    tabButtons[t].Text = string.Format("{0}({1})", t == "SP" || t == "不合格" ? t : "重审 " + t, tagStats[t]);
                }
            }
        }

        private void PreviewPanel_Resize(object sender, EventArgs e)
        {
            int totalW = previewPanel.ClientSize.Width;
            int totalH = previewPanel.ClientSize.Height;
            int spacing = 30;
            int walkW = 250;
            int walkH = 330;
            int sheetW = 280;

            int startX = Math.Max(20, (totalW - (walkW + spacing + sheetW)) / 2);
            int walkY = Math.Max(10, (totalH - (walkH + 42)) / 2);
            int sheetY = walkY;

            picWalk.Location = new Point(startX, walkY);
            if (panelDir != null)
            {
                panelDir.Location = new Point(startX, walkY + walkH + 8);
            }
            picSheet.Location = new Point(startX + walkW + spacing, sheetY);
        }

        private Button CreateTagButton(string text, Color bg, Color textCol)
        {
            Button btn = new Button();
            btn.Text = text;
            btn.Size = new Size(82, 42);
            btn.Margin = new Padding(3, 0, 3, 0);
            btn.BackColor = bg;
            btn.ForeColor = textCol;
            btn.Font = new Font("Microsoft YaHei", 10.5F, FontStyle.Bold);
            btn.FlatStyle = FlatStyle.Flat;
            btn.FlatAppearance.BorderColor = Color.FromArgb(180, 180, 180);
            btn.TabStop = false;
            return btn;
        }

        private void LoadCategoryFiles(string categoryKey)
        {
            pendingFiles.Clear();
            currentIndex = 0;

            if (categoryKey == "")
            {
                if (Directory.Exists(charaDir))
                {
                    pendingFiles.AddRange(Directory.GetFiles(charaDir, "*.png", SearchOption.TopDirectoryOnly));
                }
            }
            else
            {
                string subDir = Path.Combine(charaDir, categoryKey);
                if (Directory.Exists(subDir))
                {
                    pendingFiles.AddRange(Directory.GetFiles(subDir, "*.png", SearchOption.TopDirectoryOnly));
                }
            }

            LoadCurrentFile();
        }

        private void LoadCurrentFile()
        {
            DisposeBitmaps();
            RefreshDirectoryStats();
            UpdateTabButtonLabels();

            string catTitle = string.IsNullOrEmpty(currentCategoryKey) ? "待处理" : "重审 " + currentCategoryKey;

            if (pendingFiles.Count == 0 || currentIndex >= pendingFiles.Count)
            {
                lblFileName.Text = string.Format("[{0}] 当前分类无图片", catTitle);
                lblProgress.Text = "当前列表为空或已完成";
                UpdateStatsText();
                picWalk.Invalidate();
                picSheet.Invalidate();
                return;
            }

            string filePath = pendingFiles[currentIndex];
            string fileName = Path.GetFileName(filePath);

            try
            {
                byte[] bytes = File.ReadAllBytes(filePath);
                using (MemoryStream ms = new MemoryStream(bytes))
                using (Bitmap raw = new Bitmap(ms))
                {
                    currentFullBitmap = new Bitmap(raw);
                }

                bool isMini = fileName.ToLowerInvariant().StartsWith("mini_") || IsFileTaggedMini(fileName);
                string tagBadge = isMini ? "  [迷你角色]" : "";
                lblFileName.Text = string.Format("{0} ({1}x{2}){3}", fileName, currentFullBitmap.Width, currentFullBitmap.Height, tagBadge);
                lblFileName.ForeColor = isMini ? Color.FromArgb(210, 80, 0) : Color.FromArgb(33, 37, 41);
                lblProgress.Text = string.Format("[{0}] 当前: {1} / {2}", catTitle, currentIndex + 1, pendingFiles.Count);
                UpdateStatsText();

                if (!HasRowContent(currentFullBitmap, currentDirectionRow))
                {
                    for (int r = 0; r < 4; r++)
                    {
                        if (HasRowContent(currentFullBitmap, r))
                        {
                            currentDirectionRow = r;
                            break;
                        }
                    }
                }

                UpdateWalkFrames();
                UpdateDirButtonStyles();
            }
            catch (Exception ex)
            {
                lblFileName.Text = fileName + " [读取异常: " + ex.Message + "]";
            }

            currentFrame = 0;
            picWalk.Invalidate();
            picSheet.Invalidate();
        }

        private void SetDirection(int row)
        {
            currentDirectionRow = Math.Max(0, Math.Min(3, row));
            UpdateWalkFrames();
            UpdateDirButtonStyles();
        }

        private void ToggleAutoRotate()
        {
            autoRotate = !autoRotate;
            UpdateDirButtonStyles();
        }

        private void UpdateDirButtonStyles()
        {
            for (int i = 0; i < 4; i++)
            {
                if (dirButtons[i] == null) continue;
                if (i == currentDirectionRow)
                {
                    dirButtons[i].BackColor = Color.FromArgb(0, 120, 215);
                    dirButtons[i].ForeColor = Color.White;
                    dirButtons[i].FlatAppearance.BorderColor = Color.FromArgb(0, 90, 180);
                }
                else
                {
                    dirButtons[i].BackColor = Color.FromArgb(245, 245, 245);
                    dirButtons[i].ForeColor = Color.FromArgb(60, 60, 60);
                    dirButtons[i].FlatAppearance.BorderColor = Color.FromArgb(210, 210, 210);
                }
            }
            if (btnAutoRotate != null)
            {
                if (autoRotate)
                {
                    btnAutoRotate.BackColor = Color.FromArgb(40, 167, 69);
                    btnAutoRotate.ForeColor = Color.White;
                    btnAutoRotate.FlatAppearance.BorderColor = Color.FromArgb(30, 130, 50);
                    btnAutoRotate.Text = "巡转中";
                }
                else
                {
                    btnAutoRotate.BackColor = Color.FromArgb(245, 245, 245);
                    btnAutoRotate.ForeColor = Color.FromArgb(60, 60, 60);
                    btnAutoRotate.FlatAppearance.BorderColor = Color.FromArgb(210, 210, 210);
                    btnAutoRotate.Text = "巡转";
                }
            }
        }

        private bool HasRowContent(Bitmap bmp, int row)
        {
            if (bmp == null || row < 0 || row >= 4) return false;
            int fw = Math.Max(1, bmp.Width / 4);
            int fh = Math.Max(1, bmp.Height / 4);
            for (int col = 0; col < 4; col++)
            {
                Rectangle r = new Rectangle(col * fw, row * fh, fw, fh);
                if (!IsCellEmpty(bmp, r)) return true;
            }
            return false;
        }

        private void UpdateWalkFrames()
        {
            if (currentFullBitmap == null) return;
            int fw = Math.Max(1, currentFullBitmap.Width / 4);
            int fh = Math.Max(1, currentFullBitmap.Height / 4);
            int r = Math.Max(0, Math.Min(3, currentDirectionRow));

            for (int i = 0; i < 4; i++)
            {
                if (walkFrames[i] != null)
                {
                    walkFrames[i].Dispose();
                    walkFrames[i] = null;
                }
                Rectangle srcRect = new Rectangle(i * fw, r * fh, fw, fh);
                Bitmap frame = new Bitmap(fw, fh, currentFullBitmap.PixelFormat);
                using (Graphics g = Graphics.FromImage(frame))
                {
                    g.DrawImage(currentFullBitmap, new Rectangle(0, 0, fw, fh), srcRect, GraphicsUnit.Pixel);
                }
                walkFrames[i] = frame;
            }
            picWalk.Invalidate();
            picSheet.Invalidate();
        }

        private bool IsCellEmpty(Bitmap bmp, Rectangle rect)
        {
            if (rect.Width <= 0 || rect.Height <= 0) return true;
            int limitX = Math.Min(bmp.Width, rect.Right);
            int limitY = Math.Min(bmp.Height, rect.Bottom);
            for (int y = rect.Top; y < limitY; y += 2)
            {
                for (int x = rect.Left; x < limitX; x += 2)
                {
                    Color c = bmp.GetPixel(x, y);
                    if (c.A > 20) return false;
                }
            }
            return true;
        }

        private void AnimTimer_Tick(object sender, EventArgs e)
        {
            if (walkFrames[0] != null)
            {
                currentFrame = (currentFrame + 1) % 4;
                if (autoRotate && currentFrame == 0)
                {
                    int nextRow = 0;
                    if (currentDirectionRow == 0) nextRow = 1;
                    else if (currentDirectionRow == 1) nextRow = 3;
                    else if (currentDirectionRow == 3) nextRow = 2;
                    else nextRow = 0;
                    currentDirectionRow = nextRow;
                    UpdateWalkFrames();
                    UpdateDirButtonStyles();
                }
                picWalk.Invalidate();
                picSheet.Invalidate();
            }
        }

        private void PicWalk_Paint(object sender, PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.InterpolationMode = InterpolationMode.NearestNeighbor;
            g.PixelOffsetMode = PixelOffsetMode.Half;

            DrawCheckerBoard(g, picWalk.ClientRectangle);

            if (walkFrames != null && walkFrames[currentFrame] != null)
            {
                Bitmap frame = walkFrames[currentFrame];

                float maxFitScale = Math.Min(
                    (float)(picWalk.Width - 30) / frame.Width,
                    (float)(picWalk.Height - 50) / frame.Height
                );
                float scale = Math.Min(5.0f, maxFitScale);
                if (scale < 1.0f) scale = 1.0f;

                int dw = (int)Math.Round(frame.Width * scale);
                int dh = (int)Math.Round(frame.Height * scale);

                int fixedGroundY = picWalk.Height - 35;
                int dy = fixedGroundY - dh;
                int dx = (picWalk.Width - dw) / 2;

                g.DrawImage(frame, new Rectangle(dx, dy, dw, dh));

                using (Pen centerPen = new Pen(Color.FromArgb(100, 160, 160, 160), 1))
                {
                    centerPen.DashStyle = DashStyle.Dot;
                    int centerX = picWalk.Width / 2;
                    g.DrawLine(centerPen, centerX, 15, centerX, fixedGroundY + 15);
                }

                using (Pen guidePen = new Pen(Color.FromArgb(200, 0, 120, 215), 1))
                {
                    guidePen.DashStyle = DashStyle.Dash;
                    g.DrawLine(guidePen, 15, fixedGroundY, picWalk.Width - 15, fixedGroundY);
                }
            }
        }

        private void PicSheet_Paint(object sender, PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.InterpolationMode = InterpolationMode.NearestNeighbor;
            g.PixelOffsetMode = PixelOffsetMode.Half;

            DrawCheckerBoard(g, picSheet.ClientRectangle);

            if (currentFullBitmap != null)
            {
                float scale = Math.Min(
                    (float)(picSheet.Width - 20) / currentFullBitmap.Width,
                    (float)(picSheet.Height - 20) / currentFullBitmap.Height
                );
                if (scale < 1f) scale = 1f;

                int dw = (int)(currentFullBitmap.Width * scale);
                int dh = (int)(currentFullBitmap.Height * scale);
                int dx = (picSheet.Width - dw) / 2;
                int dy = (picSheet.Height - dh) / 2;

                g.DrawImage(currentFullBitmap, new Rectangle(dx, dy, dw, dh));

                int fw = currentFullBitmap.Width / 4;
                int fh = currentFullBitmap.Height / 4;
                int hx = dx + (int)(currentFrame * fw * scale);
                int hy = dy + (int)(currentDirectionRow * fh * scale);
                int hw = (int)(fw * scale);
                int hh = (int)(fh * scale);

                using (Pen p = new Pen(Color.FromArgb(220, 20, 60), 2))
                {
                    g.DrawRectangle(p, hx, hy, hw, hh);
                }
            }
        }

        private void DrawCheckerBoard(Graphics g, Rectangle rect)
        {
            int size = 10;
            using (SolidBrush b1 = new SolidBrush(Color.FromArgb(248, 248, 248)))
            using (SolidBrush b2 = new SolidBrush(Color.FromArgb(232, 234, 238)))
            {
                for (int y = rect.Top; y < rect.Bottom; y += size)
                {
                    for (int x = rect.Left; x < rect.Right; x += size)
                    {
                        bool isEven = ((x / size) + (y / size)) % 2 == 0;
                        g.FillRectangle(isEven ? b1 : b2, x, y, size, size);
                    }
                }
            }
        }

        private void ApplyClassification(string targetTag)
        {
            if (pendingFiles.Count == 0 || currentIndex >= pendingFiles.Count) return;

            string srcPath = pendingFiles[currentIndex];
            string fileName = Path.GetFileName(srcPath);

            string srcFolder = Path.GetFileName(Path.GetDirectoryName(srcPath));
            string oldTag = tagStats.ContainsKey(srcFolder) ? srcFolder : null;

            // 重审模式优化：如果重新选定的分类与当前所在分类完全一致，直接跳到下一张
            if (oldTag == targetTag)
            {
                NextFile();
                return;
            }

            string destDir = Path.Combine(charaDir, targetTag);
            if (!Directory.Exists(destDir))
            {
                Directory.CreateDirectory(destDir);
            }
            string destPath = Path.Combine(destDir, fileName);

            DisposeBitmaps();

            try
            {
                if (chkAutoFix.Checked)
                {
                    StandardizeResult res = SpriteStandardizer.StandardizeFile(srcPath, destPath);
                    if (!res.Success)
                    {
                        if (File.Exists(destPath)) File.Delete(destPath);
                        File.Move(srcPath, destPath);
                    }
                    else if (!string.Equals(srcPath, destPath, StringComparison.OrdinalIgnoreCase))
                    {
                        if (File.Exists(srcPath)) File.Delete(srcPath);
                    }
                }
                else
                {
                    if (File.Exists(destPath)) File.Delete(destPath);
                    File.Move(srcPath, destPath);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("移动文件失败: " + ex.Message, "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            ClassifyHistoryItem item = new ClassifyHistoryItem()
            {
                FileName = fileName,
                SourcePath = srcPath,
                DestPath = destPath,
                Tag = targetTag,
                OldTag = oldTag
            };
            history.Push(item);

            SaveClassificationRecord(fileName, targetTag, destPath);

            if (oldTag != null && tagStats.ContainsKey(oldTag) && tagStats[oldTag] > 0)
            {
                tagStats[oldTag]--;
            }
            if (tagStats.ContainsKey(targetTag))
            {
                tagStats[targetTag]++;
            }

            pendingFiles.RemoveAt(currentIndex);
            LoadCurrentFile();
        }

        private void UndoLast()
        {
            if (history.Count == 0)
            {
                MessageBox.Show("没有可撤销的操作。", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            ClassifyHistoryItem item = history.Pop();
            DisposeBitmaps();

            try
            {
                if (File.Exists(item.DestPath))
                {
                    if (File.Exists(item.SourcePath))
                    {
                        File.Delete(item.SourcePath);
                    }
                    File.Move(item.DestPath, item.SourcePath);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("撤销移动失败: " + ex.Message, "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            if (tagStats.ContainsKey(item.Tag) && tagStats[item.Tag] > 0)
            {
                tagStats[item.Tag]--;
            }

            if (!string.IsNullOrEmpty(item.OldTag) && tagStats.ContainsKey(item.OldTag))
            {
                tagStats[item.OldTag]++;
                SaveClassificationRecord(item.FileName, item.OldTag, item.SourcePath);
            }
            else
            {
                RemoveClassificationRecord(item.FileName);
            }

            // 如果当前在被撤销文件所在的分类列表中，重新加回
            string currentSub = currentCategoryKey == "" ? Path.GetFullPath(charaDir) : Path.Combine(charaDir, currentCategoryKey);
            string srcSub = Path.GetDirectoryName(item.SourcePath);
            if (string.Equals(currentSub, srcSub, StringComparison.OrdinalIgnoreCase))
            {
                pendingFiles.Insert(currentIndex, item.SourcePath);
            }

            LoadCurrentFile();
        }

        private void PrevFile()
        {
            if (pendingFiles.Count == 0) return;
            currentIndex = (currentIndex - 1 + pendingFiles.Count) % pendingFiles.Count;
            LoadCurrentFile();
        }

        private void NextFile()
        {
            if (pendingFiles.Count == 0) return;
            currentIndex = (currentIndex + 1) % pendingFiles.Count;
            LoadCurrentFile();
        }

        private void FixCurrentFile()
        {
            if (pendingFiles.Count == 0 || currentIndex >= pendingFiles.Count) return;
            string srcPath = pendingFiles[currentIndex];

            DisposeBitmaps();
            StandardizeResult res = SpriteStandardizer.StandardizeFile(srcPath, srcPath);
            if (res.Success)
            {
                LoadCurrentFile();
                MessageBox.Show("当前图片标准化修复成功！", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            else
            {
                MessageBox.Show("修复失败: " + res.ErrorMessage, "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
                LoadCurrentFile();
            }
        }

        private void RunBatchFixFromUI()
        {
            DialogResult dr = MessageBox.Show(
                "是否对 CHARA 图库执行全量标准化修复？\n\n修复内容：\n1. 实心背景泛洪透明化\n2. 统一转换为 128*192 规格\n3. 脚底贴合 y=47 地平线 (消除浮空)\n4. 横向中心对齐 (消除左右晃动)\n5. 超大角色等比例防裁切微缩",
                "全量标准化确认",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question
            );

            if (dr != DialogResult.Yes) return;

            Cursor.Current = Cursors.WaitCursor;
            DisposeBitmaps();

            var stats = SpriteStandardizer.BatchStandardize(charaDir, null);

            Cursor.Current = Cursors.Default;

            string msg = string.Format(
                "全量修复标准化完成！\n\n处理总数: {0} 张\n透明底修复: {1} 张\n规格统一: {2} 张\n接地重定线: {3} 张\n防裁切微缩: {4} 张",
                stats["total"], stats["opaque"], stats["dim"], stats["float"], stats["rescale"]
            );

            MessageBox.Show(msg, "完成报告", MessageBoxButtons.OK, MessageBoxIcon.Information);
            LoadCategoryFiles(currentCategoryKey);
        }

        private bool IsFileTaggedMini(string fileName)
        {
            if (string.IsNullOrEmpty(fileName)) return false;
            if (fileName.ToLowerInvariant().StartsWith("mini_")) return true;
            try
            {
                string tagsPath = Path.Combine(charaDir, "chara_tags.json");
                if (File.Exists(tagsPath))
                {
                    string text = File.ReadAllText(tagsPath, Encoding.UTF8);
                    if (text.Contains(fileName) && text.Contains("迷你角色")) return true;
                }
            }
            catch { }
            return false;
        }

        private void SaveClassificationRecord(string fileName, string tag, string fullPath)
        {
            string relPath = Path.Combine(tag, fileName);
            string timeStr = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            bool isMini = IsFileTaggedMini(fileName);
            string charaTag = isMini ? "迷你角色" : "";
            string newLine = string.Format("{0},{1},{2},{3},{4}", fileName, tag, relPath, timeStr, charaTag);

            List<string> lines = new List<string>();
            bool found = false;

            if (File.Exists(csvPath))
            {
                try
                {
                    string[] existing = File.ReadAllLines(csvPath, Encoding.UTF8);
                    if (existing.Length > 0)
                    {
                        string header = existing[0];
                        if (!header.Contains("Tag"))
                        {
                            header = "FileName,Rarity,RelativePath,Time,Tag";
                        }
                        lines.Add(header);
                        for (int i = 1; i < existing.Length; i++)
                        {
                            string l = existing[i].Trim();
                            if (string.IsNullOrEmpty(l)) continue;
                            string[] parts = l.Split(',');
                            if (parts.Length > 0 && string.Equals(parts[0].Trim(), fileName, StringComparison.OrdinalIgnoreCase))
                            {
                                lines.Add(newLine);
                                found = true;
                            }
                            else
                            {
                                lines.Add(l);
                            }
                        }
                    }
                }
                catch { }
            }
            else
            {
                lines.Add("FileName,Rarity,RelativePath,Time,Tag");
            }

            if (!found)
            {
                lines.Add(newLine);
            }

            try
            {
                File.WriteAllLines(csvPath, lines.ToArray(), Encoding.UTF8);
            }
            catch { }

            UpdateJsonRecord(fileName, tag);
            if (isMini)
            {
                UpdateTagsJsonRecord(fileName);
            }
        }

        private void UpdateTagsJsonRecord(string fileName)
        {
            try
            {
                string tagsPath = Path.Combine(charaDir, "chara_tags.json");
                Dictionary<string, string> dict = new Dictionary<string, string>();
                if (File.Exists(tagsPath))
                {
                    string content = File.ReadAllText(tagsPath, Encoding.UTF8);
                    string[] lines = content.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
                    foreach (var line in lines)
                    {
                        string trimmed = line.Trim().TrimEnd(',');
                        int colonIdx = trimmed.IndexOf(':');
                        if (colonIdx > 0)
                        {
                            string k = trimmed.Substring(0, colonIdx).Trim().Trim('"');
                            string v = trimmed.Substring(colonIdx + 1).Trim().Trim('"');
                            if (!string.IsNullOrEmpty(k)) dict[k] = v;
                        }
                    }
                }
                dict[fileName] = "迷你角色";
                StringBuilder sb = new StringBuilder();
                sb.AppendLine("{");
                int idx = 0;
                foreach (var kv in dict)
                {
                    idx++;
                    sb.AppendFormat("  \"{0}\": \"{1}\"{2}\n", kv.Key, kv.Value, idx == dict.Count ? "" : ",");
                }
                sb.AppendLine("}");
                File.WriteAllText(tagsPath, sb.ToString(), Encoding.UTF8);
            }
            catch { }
        }

        private void RemoveClassificationRecord(string fileName)
        {
            if (File.Exists(csvPath))
            {
                try
                {
                    string[] lines = File.ReadAllLines(csvPath, Encoding.UTF8);
                    List<string> remain = new List<string>();
                    for (int i = 0; i < lines.Length; i++)
                    {
                        if (i == 0) { remain.Add(lines[i]); continue; }
                        string[] parts = lines[i].Split(',');
                        if (parts.Length > 0 && string.Equals(parts[0].Trim(), fileName, StringComparison.OrdinalIgnoreCase))
                        {
                            continue;
                        }
                        remain.Add(lines[i]);
                    }
                    File.WriteAllLines(csvPath, remain.ToArray(), Encoding.UTF8);
                }
                catch { }
            }

            if (File.Exists(jsonPath))
            {
                try
                {
                    Dictionary<string, string> dict = LoadJsonDict();
                    if (dict.ContainsKey(fileName))
                    {
                        dict.Remove(fileName);
                        SaveJsonDict(dict);
                    }
                }
                catch { }
            }
        }

        private Dictionary<string, string> LoadJsonDict()
        {
            Dictionary<string, string> dict = new Dictionary<string, string>();
            if (File.Exists(jsonPath))
            {
                string content = File.ReadAllText(jsonPath, Encoding.UTF8);
                string[] lines = content.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
                foreach (var line in lines)
                {
                    string trimmed = line.Trim().TrimEnd(',');
                    int colonIdx = trimmed.IndexOf(':');
                    if (colonIdx > 0)
                    {
                        string k = trimmed.Substring(0, colonIdx).Trim().Trim('"');
                        string v = trimmed.Substring(colonIdx + 1).Trim().Trim('"');
                        if (!string.IsNullOrEmpty(k)) dict[k] = v;
                    }
                }
            }
            return dict;
        }

        private void SaveJsonDict(Dictionary<string, string> dict)
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("{");
            int idx = 0;
            foreach (var kv in dict)
            {
                idx++;
                sb.AppendFormat("  \"{0}\": \"{1}\"{2}\n", kv.Key, kv.Value, idx == dict.Count ? "" : ",");
            }
            sb.AppendLine("}");
            File.WriteAllText(jsonPath, sb.ToString(), Encoding.UTF8);
        }

        private void UpdateJsonRecord(string fileName, string tag)
        {
            try
            {
                Dictionary<string, string> dict = LoadJsonDict();
                dict[fileName] = tag;
                SaveJsonDict(dict);
            }
            catch { }
        }

        private void UpdateStatsText()
        {
            int unclassified = 0;
            if (Directory.Exists(charaDir))
            {
                unclassified = Directory.GetFiles(charaDir, "*.png", SearchOption.TopDirectoryOnly).Length;
            }

            lblStats.Text = string.Format("待分类: {0} | 1: {1} | 2: {2} | 3: {3} | 4: {4} | 5: {5} | 6: {6} | SP: {7} | 不合格: {8}",
                unclassified,
                tagStats["1"], tagStats["2"], tagStats["3"], tagStats["4"],
                tagStats["5"], tagStats["6"], tagStats["SP"], tagStats["不合格"]);
        }

        private void ClassifierForm_KeyDown(object sender, KeyEventArgs e)
        {
            switch (e.KeyCode)
            {
                case Keys.D1:
                case Keys.NumPad1:
                    ApplyClassification("1");
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.D2:
                case Keys.NumPad2:
                    ApplyClassification("2");
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.D3:
                case Keys.NumPad3:
                    ApplyClassification("3");
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.D4:
                case Keys.NumPad4:
                    ApplyClassification("4");
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.D5:
                case Keys.NumPad5:
                    ApplyClassification("5");
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.D6:
                case Keys.NumPad6:
                    ApplyClassification("6");
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.S:
                    ApplyClassification("SP");
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.Delete:
                case Keys.X:
                    ApplyClassification("不合格");
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.Z:
                case Keys.Back:
                    UndoLast();
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.Left:
                case Keys.PageUp:
                case Keys.Q:
                    PrevFile();
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.Right:
                case Keys.PageDown:
                case Keys.E:
                case Keys.Space:
                    NextFile();
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.Down:
                    SetDirection(0);
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.Up:
                    SetDirection(3);
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.A:
                    SetDirection(1);
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.D:
                    SetDirection(2);
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.W:
                    SetDirection(3);
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.R:
                    ToggleAutoRotate();
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
                case Keys.F5:
                    LoadCategoryFiles(currentCategoryKey);
                    e.Handled = true; e.SuppressKeyPress = true;
                    break;
            }
        }

        protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
        {
            if (keyData == Keys.Left)
            {
                PrevFile();
                return true;
            }
            if (keyData == Keys.Right)
            {
                NextFile();
                return true;
            }
            return base.ProcessCmdKey(ref msg, keyData);
        }

        private void DisposeBitmaps()
        {
            if (currentFullBitmap != null)
            {
                currentFullBitmap.Dispose();
                currentFullBitmap = null;
            }
            for (int i = 0; i < walkFrames.Length; i++)
            {
                if (walkFrames[i] != null)
                {
                    walkFrames[i].Dispose();
                    walkFrames[i] = null;
                }
            }
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (animTimer != null) animTimer.Stop();
            DisposeBitmaps();
            base.OnFormClosing(e);
        }

        [STAThread]
        public static void Main(string[] args)
        {
            if (args != null && args.Length > 0)
            {
                string cmd = args[0].ToLowerInvariant();
                if (cmd == "/fix" || cmd == "-f" || cmd == "--fix")
                {
                    string targetDir = args.Length > 1 ? args[1] : null;
                    RunConsoleBatchFix(targetDir);
                    return;
                }
                if (cmd == "/stats" || cmd == "-s" || cmd == "/console" || cmd == "-c")
                {
                    string targetDir = args.Length > 1 ? args[1] : null;
                    PrintStats(targetDir);
                    return;
                }
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            string target = (args != null && args.Length > 0) ? args[0] : null;
            if (target == "--classify") Application.Run(new ClassifierForm(args.Length > 1 ? args[1] : null));
            else
            {
                try { Application.Run(new CharacterTaggingForm(String.IsNullOrEmpty(target) ? CharacterTaggingForm.DefaultRoot() : target)); }
                catch (Exception ex) { MessageBox.Show(ex.Message, "人物工具启动失败", MessageBoxButtons.OK, MessageBoxIcon.Error); }
            }
        }

        [System.Runtime.InteropServices.DllImport("kernel32.dll")]
        private static extern bool AttachConsole(int dwProcessId);

        private static void RunConsoleBatchFix(string targetDir)
        {
            AttachConsole(-1);
            Console.OutputEncoding = Encoding.UTF8;
            string dir = (!string.IsNullOrEmpty(targetDir) && Directory.Exists(targetDir)) ? targetDir : @"D:\123\CHARA";
            if (!Directory.Exists(dir))
            {
                Console.WriteLine("CHARA 目录不存在: " + dir);
                return;
            }

            Console.WriteLine("开始全量标准化修复: " + dir);
            var stats = SpriteStandardizer.BatchStandardize(dir, (curr, total, f) => {
                if (curr % 100 == 0 || curr == total)
                {
                    Console.WriteLine(string.Format("处理进度: {0} / {1} ({2})", curr, total, Path.GetFileName(f)));
                }
            });

            Console.WriteLine("\n=== 修复完成报告 ===");
            Console.WriteLine("处理总数: " + stats["total"] + " 张");
            Console.WriteLine("背景透明化: " + stats["opaque"] + " 张");
            Console.WriteLine("规格统一: " + stats["dim"] + " 张");
            Console.WriteLine("接地重定线: " + stats["float"] + " 张");
            Console.WriteLine("等比防裁切: " + stats["rescale"] + " 张");
        }

        private static void PrintStats(string targetDir)
        {
            AttachConsole(-1);
            Console.OutputEncoding = Encoding.UTF8;
            string dir = (!string.IsNullOrEmpty(targetDir) && Directory.Exists(targetDir)) ? targetDir : @"D:\123\CHARA";
            if (!Directory.Exists(dir))
            {
                Console.WriteLine("CHARA 目录不存在: " + dir);
                return;
            }

            string csv = Path.Combine(dir, "chara_classification.csv");
            int pending = Directory.GetFiles(dir, "*.png", SearchOption.TopDirectoryOnly).Length;

            Dictionary<string, int> counts = new Dictionary<string, int>();
            string[] tags = new string[] { "1", "2", "3", "4", "5", "6", "SP", "不合格" };
            foreach (var t in tags) counts[t] = 0;

            if (File.Exists(csv))
            {
                string[] lines = File.ReadAllLines(csv, Encoding.UTF8);
                for (int i = 1; i < lines.Length; i++)
                {
                    string[] parts = lines[i].Split(',');
                    if (parts.Length >= 2)
                    {
                        string tag = parts[1].Trim();
                        if (counts.ContainsKey(tag)) counts[tag]++;
                    }
                }
            }

            Console.WriteLine("=== 角色行走图分类统计 ===");
            Console.WriteLine("待处理未分类: " + pending + " 张");
            foreach (var t in tags)
            {
                Console.WriteLine(string.Format("  {0}: {1} 张", t, counts[t]));
            }
        }
    }
}
