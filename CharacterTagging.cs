using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace LegionBattle.CharaClassifier
{
    public class CharacterTag { public string id; public string category; public string name; public long used; }
    public class CharacterLabel
    {
        public string id, path, fingerprint, race, job, gender;
        public int rarity;
        public List<string> identities = new List<string>();
        public bool jobLocked;
    }
    public class CharacterLabelDocument
    {
        public int version = 4;
        public List<CharacterTag> tags = new List<CharacterTag>();
        public List<CharacterLabel> characters = new List<CharacterLabel>();
        public List<CharacterResourceGroup> groups = new List<CharacterResourceGroup>();
        public string search = "", tier = "全部", filter = "全部", selected = "";
    }
    public class CharacterResourceGroup
    {
        public string id, name;
        public List<string> members = new List<string>();
    }
    public class CharacterCard
    {
        public string file, name, tier, meta;
        public CharacterLabel label;
        public CharacterResourceGroup group;
        public string conflicts = "";
    }
    public class CharacterLabelStore
    {
        public readonly string Root, FilePath;
        public CharacterLabelDocument Data;
        public List<CharacterCard> Cards = new List<CharacterCard>();
        public readonly Stack<string> Undo = new Stack<string>();
        public static readonly string[] Genders = { "男", "女", "无", "双" };
        private readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = 32 * 1024 * 1024 };
        public CharacterLabelStore(string root)
        {
            Root = Path.GetFullPath(root); FilePath = Path.Combine(Root, "character_bond_labels.json");
            Data = ReadNewest(); Scan();
        }
        private CharacterLabelDocument Parse(string text)
        {
            var d = json.Deserialize<CharacterLabelDocument>(text);
            if (d == null || d.version < 1 || d.version > 4 || d.tags == null || d.characters == null) throw new InvalidDataException("人物标签文件格式无效");
            d.version = 4;
            if (d.groups == null) d.groups = new List<CharacterResourceGroup>();
            if (d.tags.Any(t => t == null || String.IsNullOrWhiteSpace(t.id) || String.IsNullOrWhiteSpace(t.name) || !new[] { "race", "identity", "job" }.Contains(t.category)) || d.tags.Select(t => t.id).Distinct().Count() != d.tags.Count) throw new InvalidDataException("词条数据无效");
            if (d.characters.Any(c => c == null || String.IsNullOrEmpty(c.id) || c.identities == null) || d.characters.Select(c => c.id).Distinct().Count() != d.characters.Count) throw new InvalidDataException("人物标识无效");
            foreach (var c in d.characters)
            {
                if (c.rarity < 0 || c.rarity > 6) throw new InvalidDataException("人物阶级无效");
                if (!String.IsNullOrEmpty(c.gender) && !Genders.Contains(c.gender)) throw new InvalidDataException("性别标记无效");
                if (!String.IsNullOrEmpty(c.race) && !d.tags.Any(t => t.id == c.race && t.category == "race")) throw new InvalidDataException("种族引用无效");
                if (!String.IsNullOrEmpty(c.job) && !d.tags.Any(t => t.id == c.job && t.category == "job")) throw new InvalidDataException("职业引用无效");
                if (c.identities.Any(id => !d.tags.Any(t => t.id == id && t.category == "identity"))) throw new InvalidDataException("身份引用无效");
            }
            var memberIds = new HashSet<string>();
            foreach (var g in d.groups)
            {
                if (g == null || String.IsNullOrEmpty(g.id) || String.IsNullOrEmpty(g.name) || g.members == null || !g.members.Contains(g.id) || !d.characters.Any(c => c.id == g.id)) throw new InvalidDataException("人物动作分组无效");
                foreach (var id in g.members) if (!memberIds.Add(id) || !d.characters.Any(c => c.id == id)) throw new InvalidDataException("人物动作资源引用无效");
            }
            return d;
        }
        private CharacterLabelDocument ReadNewest()
        {
            var files = new[] { FilePath, FilePath + ".bak" }.Where(File.Exists).OrderByDescending(File.GetLastWriteTimeUtc).ToList();
            foreach (var p in files) try { return Parse(File.ReadAllText(p, Encoding.UTF8)); } catch { }
            if (files.Count > 0) throw new InvalidDataException("人物标签与备份都无法读取。为保护资料，未覆盖文件。");
            return new CharacterLabelDocument();
        }
        private static string Fingerprint(string file)
        {
            using (var hash = SHA256.Create()) using (var stream = File.OpenRead(file)) return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "");
        }
        private void Scan()
        {
            var byId = Data.characters.ToDictionary(c => c.id);
            var seen = new HashSet<string>();
            foreach (var file in Directory.GetFiles(Root, "*.png", SearchOption.AllDirectories).OrderBy(f => f, StringComparer.OrdinalIgnoreCase))
            {
                if (String.Equals(Path.GetFileName(file), "GroundShadow.png", StringComparison.OrdinalIgnoreCase)) continue;
                var relative = file.Substring(Root.TrimEnd(Path.DirectorySeparatorChar).Length + 1);
                // Only the classified folders and top-level pending sprites are character inputs.
                var first = relative.Split(Path.DirectorySeparatorChar)[0];
                if (relative.Contains(Path.DirectorySeparatorChar) && !new[] { "1", "2", "3", "4", "5", "6", "SP", "不合格" }.Contains(first)) continue;
                string meta = File.Exists(file + ".meta") ? File.ReadAllText(file + ".meta") : "";
                var guid = Regex.Match(meta, @"(?m)^guid:\s*([a-fA-F0-9]{32})\s*$");
                string id = guid.Success ? "unity:" + guid.Groups[1].Value.ToLowerInvariant() : null, fingerprint = null;
                CharacterLabel c = null;
                if (id != null) byId.TryGetValue(id, out c);
                else
                {
                    fingerprint = Fingerprint(file);
                    c = Data.characters.FirstOrDefault(x => x.path == relative && x.fingerprint == fingerprint);
                    if (c == null)
                    {
                        var matches = Data.characters.Where(x => x.fingerprint == fingerprint && !seen.Contains(x.id) && !File.Exists(Path.Combine(Root, x.path ?? ""))).ToList();
                        if (matches.Count == 1) c = matches[0];
                    }
                    id = c != null ? c.id : "local:" + Guid.NewGuid().ToString("N");
                }
                if (!seen.Add(id)) throw new InvalidDataException("素材ID重复，请检查：" + relative);
                if (c == null) { c = new CharacterLabel { id = id }; Data.characters.Add(c); byId[id] = c; }
                c.path = relative; c.fingerprint = fingerprint;
                Cards.Add(new CharacterCard { file = file, name = Path.GetFileNameWithoutExtension(file), tier = TierOf(c), meta = meta, label = c });
            }
            GroupCards();
            Cards = Cards.OrderBy(c => c.tier, StringComparer.Ordinal).ThenBy(c => c.name, StringComparer.CurrentCultureIgnoreCase).ToList();
            RefreshGroups();
        }
        private static string MotionBase(string name)
        {
            var match = Regex.Match(name, @"^(.+)_(?:pose\d+|walk)$", RegexOptions.IgnoreCase);
            return match.Success ? match.Groups[1].Value : null;
        }
        private void GroupCards()
        {
            var raw = Cards.ToList();
            foreach (var candidates in raw.Where(c => MotionBase(c.name) != null).GroupBy(c => MotionBase(c.name), StringComparer.OrdinalIgnoreCase))
            {
                var members = candidates.ToList();
                if (members.Count < 2 || !members.Any(c => c.name.EndsWith("_walk", StringComparison.OrdinalIgnoreCase)) || !members.Any(c => Regex.IsMatch(c.name, @"_pose\d+$", RegexOptions.IgnoreCase))) continue;
                var group = Data.groups.FirstOrDefault(g => g.members.Any(id => members.Any(c => c.label.id == id)));
                if (group == null)
                {
                    var first = members.First(c => c.name.EndsWith("_walk", StringComparison.OrdinalIgnoreCase));
                    group = new CharacterResourceGroup { id = first.label.id, name = candidates.Key }; Data.groups.Add(group);
                }
                foreach (var member in members) if (!Data.groups.Any(g => g.members.Contains(member.label.id))) group.members.Add(member.label.id);
                if (!group.members.Contains(group.id)) group.members.Add(group.id);
            }
            var grouped = new HashSet<string>(); var result = new List<CharacterCard>();
            foreach (var group in Data.groups)
            {
                var members = raw.Where(c => group.members.Contains(c.label.id)).ToList(); if (members.Count == 0) continue;
                var preview = members.FirstOrDefault(c => c.name.EndsWith("_walk", StringComparison.OrdinalIgnoreCase)) ?? members.FirstOrDefault(c => c.label.id == group.id) ?? members[0];
                var card = new CharacterCard { file = preview.file, meta = preview.meta, name = group.name, group = group, label = Data.characters.Single(c => c.id == group.id) };
                MergeNonConflicting(card); result.Add(card);
                foreach (var id in group.members) grouped.Add(id);
                if (group.members.Contains(Data.selected)) Data.selected = group.id;
            }
            result.AddRange(raw.Where(c => !grouped.Contains(c.label.id))); Cards = result;
        }
        private List<CharacterLabel> LabelsFor(CharacterCard card)
        {
            return card.group == null ? new List<CharacterLabel> { card.label } : Data.characters.Where(c => card.group.members.Contains(c.id)).ToList();
        }
        private void MergeNonConflicting(CharacterCard card)
        {
            var members = LabelsFor(card); var races = members.Select(c => c.race).Where(s => !String.IsNullOrEmpty(s)).Distinct().ToList();
            var genders = members.Select(c => c.gender).Where(s => !String.IsNullOrEmpty(s)).Distinct().ToList();
            var tiers = members.Select(TierOf).Distinct().ToList(); var notes = new List<string>();
            if (races.Count == 1) foreach (var c in members) c.race = races[0]; else if (races.Count > 1) notes.Add("种族");
            if (genders.Count == 1) foreach (var c in members) c.gender = genders[0]; else if (genders.Count > 1) notes.Add("性别");
            if (tiers.Count > 1) notes.Add("阶级");
            var identities = members.SelectMany(c => c.identities).Distinct().ToList(); foreach (var c in members) c.identities = identities.ToList();
            if (identities.Count > 1) notes.Add("身份");
            card.conflicts = String.Join("、", notes); card.tier = TierOf(card.label);
        }
        private void RefreshGroups()
        {
            foreach (var card in Cards) { if (card.group != null) MergeNonConflicting(card); else { card.tier = TierOf(card.label); card.conflicts = card.label.identities.Count > 1 ? "身份" : ""; } }
        }
        public string DescribeResources(CharacterCard card)
        {
            Func<string, string> tag = id => { var item = Data.tags.FirstOrDefault(t => t.id == id); return item == null ? "未填" : item.name; };
            return String.Join("\r\n\r\n", LabelsFor(card).Select(c => c.path + "\r\n种族：" + tag(c.race) + "；性别：" + (c.gender ?? "未填") + "；阶级：" + TierOf(c) + "\r\n身份：" + String.Join("、", c.identities.Select(tag)))) +
                (String.IsNullOrEmpty(card.conflicts) ? "" : "\r\n\r\n待统一：" + card.conflicts + "。原标记均保留；在主界面选择对应标记可统一全部动作素材。");
        }
        public string Snapshot() { return json.Serialize(Data); }
        public void Save()
        {
            RefreshGroups();
            string text = Snapshot(); Parse(text);
            string temp = FilePath + ".tmp";
            using (var stream = new FileStream(temp, FileMode.Create, FileAccess.Write, FileShare.None))
            using (var writer = new StreamWriter(stream, new UTF8Encoding(false))) { writer.Write(text); writer.Flush(); stream.Flush(true); }
            if (File.Exists(FilePath))
            {
                bool valid = false; try { Parse(File.ReadAllText(FilePath, Encoding.UTF8)); valid = true; } catch { }
                if (valid) File.Replace(temp, FilePath, FilePath + ".bak", true);
                else File.Replace(temp, FilePath, null, true); // Preserve valid recovery backup.
            }
            else File.Move(temp, FilePath);
        }
        private void Restore(string text)
        {
            Data = Parse(text); var map = Data.characters.ToDictionary(c => c.id);
            foreach (var card in Cards) { card.label = map[card.label.id]; card.group = Data.groups.FirstOrDefault(g => g.id == card.label.id); card.tier = TierOf(card.label); }
            RefreshGroups();
        }
        public void Change(Action action)
        {
            string before = Snapshot();
            try {
                action(); Save(); Undo.Push(before);
                if (Undo.Count > 50) { var recent = Undo.Take(50).Reverse().ToArray(); Undo.Clear(); foreach (var item in recent) Undo.Push(item); }
            }
            catch { Restore(before); throw; }
        }
        public void Revert()
        {
            if (Undo.Count == 0) return;
            string before = Snapshot(), previous = Undo.Peek();
            try { Restore(previous); Save(); Undo.Pop(); } catch { Restore(before); throw; }
        }
        public CharacterTag AddTag(string category, string name)
        {
            if (category != "race" && category != "identity") throw new ArgumentException("请选择种族或身份词条");
            name = (name ?? "").Trim(); if (name.Length == 0) throw new ArgumentException("请输入词条名称");
            var t = Data.tags.FirstOrDefault(x => x.category == category && x.name == name);
            if (t == null) { t = new CharacterTag { id = Guid.NewGuid().ToString("N"), category = category, name = name }; Data.tags.Add(t); }
            return t;
        }
        public void Apply(IEnumerable<CharacterCard> cards, CharacterTag tag, bool remove)
        {
            foreach (var card in cards)
            {
                foreach (var c in LabelsFor(card)) {
                if (tag.category == "race") { if (!remove) c.race = tag.id; else if (c.race == tag.id) c.race = null; }
                if (tag.category == "identity") { if (remove) c.identities.Remove(tag.id); else c.identities = new List<string> { tag.id }; }
                }
            }
            tag.used = DateTime.UtcNow.Ticks;
        }
        public bool Has(CharacterCard c, string id) { return c.label.race == id || c.label.job == id || c.label.identities.Contains(id); }
        public void SetGender(IEnumerable<CharacterCard> cards, string gender)
        {
            if (!String.IsNullOrEmpty(gender) && !Genders.Contains(gender)) throw new ArgumentException("请选择男、女、无、双");
            foreach (var card in cards) foreach (var label in LabelsFor(card)) label.gender = String.IsNullOrEmpty(gender) ? null : gender;
        }
        private static string TierOf(CharacterLabel label)
        {
            if (label.rarity > 0) return label.rarity.ToString(CultureInfo.InvariantCulture);
            string path = (label.path ?? "").Replace('/', Path.DirectorySeparatorChar).Replace('\\', Path.DirectorySeparatorChar);
            return path.Contains(Path.DirectorySeparatorChar) ? path.Split(Path.DirectorySeparatorChar)[0] : "待分类";
        }
        public void SetTier(IEnumerable<CharacterCard> cards, int rarity)
        {
            if (rarity < 1 || rarity > 6) throw new ArgumentException("阶级范围为1～6");
            foreach (var card in cards) { foreach (var label in LabelsFor(card)) label.rarity = rarity; card.tier = TierOf(card.label); }
        }
        public void CopyTraits(IEnumerable<CharacterCard> cards, string race, string gender, string[] identities)
        {
            if (identities.Length > 1) throw new ArgumentException("上一人物有多个身份，请先为其选定一个身份。");
            foreach (var card in cards) foreach (var label in LabelsFor(card)) { label.race = race; label.gender = gender; label.identities = identities.ToList(); }
        }
        public void Rename(CharacterTag old, string name)
        {
            old = Data.tags.Single(t => t.id == old.id);
            name = (name ?? "").Trim(); if (name.Length == 0) throw new ArgumentException("请输入名称");
            var target = Data.tags.FirstOrDefault(t => t.category == old.category && t.name == name && t.id != old.id);
            if (target == null) { old.name = name; return; }
            foreach (var c in Data.characters)
            {
                if (c.race == old.id) c.race = target.id;
                if (c.job == old.id) c.job = target.id;
                if (c.identities.Remove(old.id) && !c.identities.Contains(target.id)) c.identities.Add(target.id);
            }
            Data.tags.Remove(old);
        }
        public static Bitmap LoadPortrait(CharacterCard card)
        {
            using (var source = new Bitmap(card.file))
            {
                int cols = source.Width == 72 || source.Width == 144 || (source.Width == 96 && source.Height > 96) ? 3 : 4;
                Rectangle frame = new Rectangle(0, 0, Math.Max(1, source.Width / cols), Math.Max(1, source.Height / 4));
                var rect = Regex.Match(card.meta ?? "", @"name:\s*[^\r\n]*_down_0[^\r\n]*\r?\n\s*rect:\s*\r?\n\s*serializedVersion:[^\r\n]*\r?\n\s*x:\s*([\d.]+)\s*\r?\n\s*y:\s*([\d.]+)\s*\r?\n\s*width:\s*([\d.]+)\s*\r?\n\s*height:\s*([\d.]+)");
                if (rect.Success)
                {
                    int x = (int)float.Parse(rect.Groups[1].Value, CultureInfo.InvariantCulture), y = (int)float.Parse(rect.Groups[2].Value, CultureInfo.InvariantCulture);
                    int w = (int)float.Parse(rect.Groups[3].Value, CultureInfo.InvariantCulture), h = (int)float.Parse(rect.Groups[4].Value, CultureInfo.InvariantCulture);
                    frame = new Rectangle(x, source.Height - y - h, w, h);
                }
                frame.Intersect(new Rectangle(0, 0, source.Width, source.Height));
                if (frame.Width == 0 || frame.Height == 0) throw new InvalidDataException("角色帧超出图片边界");
                using (var cell = source.Clone(frame, PixelFormat.Format32bppArgb))
                {
                    int minX = cell.Width, minY = cell.Height, maxX = -1, maxY = -1;
                    for (int y = 0; y < cell.Height; y++) for (int x = 0; x < cell.Width; x++) if (cell.GetPixel(x, y).A > 8) { minX = Math.Min(minX, x); minY = Math.Min(minY, y); maxX = Math.Max(maxX, x); maxY = Math.Max(maxY, y); }
                    return maxX < 0 ? new Bitmap(1, 1) : cell.Clone(new Rectangle(minX, minY, maxX - minX + 1, maxY - minY + 1), PixelFormat.Format32bppArgb);
                }
            }
        }
    }

    public class CharacterGallery : ScrollableControl
    {
        public List<CharacterCard> Cards = new List<CharacterCard>();
        public HashSet<string> Selected = new HashSet<string>();
        public Action SelectionChanged;
        private int anchor = -1;
        private readonly Dictionary<string, Bitmap> cache = new Dictionary<string, Bitmap>();
        private readonly Queue<string> order = new Queue<string>();
        public const int CellWidth = 140, CellHeight = 150;
        public int Columns { get { return Math.Max(1, (ClientSize.Width - SystemInformation.VerticalScrollBarWidth) / CellWidth); } }
        public CharacterGallery()
        {
            DoubleBuffered = true; AutoScroll = true; BackColor = Color.FromArgb(29, 34, 44); ForeColor = Color.White; TabStop = true;
        }
        public void SetCards(List<CharacterCard> cards) { Cards = cards; anchor = -1; AutoScrollPosition = Point.Empty; LayoutCards(); }
        private void LayoutCards() { AutoScrollMinSize = new Size(0, ((Cards.Count + Columns - 1) / Columns) * CellHeight); Invalidate(); }
        protected override void OnResize(EventArgs e) { base.OnResize(e); LayoutCards(); }
        protected override void OnScroll(ScrollEventArgs e) { base.OnScroll(e); Invalidate(); }
        public void Reveal(string id)
        {
            int index = Cards.FindIndex(c => c.label.id == id);
            if (index >= 0) AutoScrollPosition = new Point(0, index / Columns * CellHeight);
        }
        protected override void OnMouseDown(MouseEventArgs e)
        {
            base.OnMouseDown(e); Focus(); if (e.Button != MouseButtons.Left) return;
            int col = e.X / CellWidth; if (col >= Columns) return;
            int index = (e.Y - AutoScrollPosition.Y) / CellHeight * Columns + col;
            if (index < 0 || index >= Cards.Count) return;
            if ((ModifierKeys & Keys.Shift) != 0 && anchor >= 0)
            { if ((ModifierKeys & Keys.Control) == 0) Selected.Clear(); for (int i = Math.Min(index, anchor); i <= Math.Max(index, anchor); i++) Selected.Add(Cards[i].label.id); }
            else { if ((ModifierKeys & Keys.Control) == 0) Selected.Clear(); string id = Cards[index].label.id; if (!Selected.Add(id)) Selected.Remove(id); anchor = index; }
            Invalidate(); if (SelectionChanged != null) SelectionChanged();
        }
        public void ChooseAll() { foreach (var c in Cards) Selected.Add(c.label.id); Invalidate(); if (SelectionChanged != null) SelectionChanged(); }
        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            int first = Math.Max(0, -AutoScrollPosition.Y / CellHeight), last = Math.Min((Cards.Count + Columns - 1) / Columns, first + ClientSize.Height / CellHeight + 2);
            for (int row = first; row < last; row++) for (int col = 0; col < Columns; col++)
            {
                int index = row * Columns + col; if (index >= Cards.Count) break; var c = Cards[index];
                // GDI text and GDI+ sprites share viewport coordinates; TextRenderer does not inherit Graphics transforms.
                Rectangle box = new Rectangle(col * CellWidth + 4, row * CellHeight + AutoScrollPosition.Y + 4, CellWidth - 8, CellHeight - 8);
                using (var brush = new SolidBrush(Selected.Contains(c.label.id) ? Color.FromArgb(50, 85, 112) : Color.FromArgb(39, 46, 59))) e.Graphics.FillRectangle(brush, box);
                using (var pen = new Pen(Selected.Contains(c.label.id) ? Color.FromArgb(100, 205, 245) : Color.FromArgb(57, 65, 79), 2)) e.Graphics.DrawRectangle(pen, box);
                Bitmap image;
                if (!cache.TryGetValue(c.file, out image))
                {
                    try { image = CharacterLabelStore.LoadPortrait(c); } catch { image = new Bitmap(1, 1); }
                    cache[c.file] = image; order.Enqueue(c.file);
                    while (order.Count > 220) { string old = order.Dequeue(); cache[old].Dispose(); cache.Remove(old); }
                }
                DrawSprite(e.Graphics, image, new Rectangle(box.X + 8, box.Y + 7, box.Width - 16, 94));
                TextRenderer.DrawText(e.Graphics, c.name, Font, new Rectangle(box.X + 5, box.Y + 102, box.Width - 10, 20), Color.White, TextFormatFlags.EndEllipsis | TextFormatFlags.HorizontalCenter | TextFormatFlags.NoPrefix);
                string state = "T" + c.tier + " · " + (String.IsNullOrEmpty(c.label.gender) ? "性别未填" : c.label.gender) + (String.IsNullOrEmpty(c.label.race) ? " · 种族未填" : " · 种族已填");
                TextRenderer.DrawText(e.Graphics, state, Font, new Rectangle(box.X + 2, box.Y + 122, box.Width - 4, 18), Color.LightSteelBlue, TextFormatFlags.HorizontalCenter | TextFormatFlags.EndEllipsis);
            }
        }
        public static void DrawSprite(Graphics g, Bitmap image, Rectangle target)
        {
            float scale = Math.Min(target.Width / (float)image.Width, target.Height / (float)image.Height);
            int width = Math.Max(1, (int)(image.Width * scale)), height = Math.Max(1, (int)(image.Height * scale));
            g.InterpolationMode = InterpolationMode.NearestNeighbor; g.PixelOffsetMode = PixelOffsetMode.Half;
            g.DrawImage(image, new Rectangle(target.X + (target.Width - width) / 2, target.Bottom - height, width, height), new Rectangle(0, 0, image.Width, image.Height), GraphicsUnit.Pixel);
        }
        protected override void Dispose(bool disposing) { if (disposing) foreach (var image in cache.Values) image.Dispose(); base.Dispose(disposing); }
    }

    public class CharacterTaggingForm : Form
    {
        public readonly CharacterLabelStore Store;
        public readonly CharacterGallery Gallery = new CharacterGallery();
        private readonly TextBox search = new TextBox();
        private readonly ComboBox tier = new ComboBox(), filter = new ComboBox();
        private readonly Label status = new Label(), detail = new Label();
        private readonly Panel preview = new Panel();
        private Bitmap portrait;
        private readonly CheckBox autoNext = new CheckBox();
        private readonly Dictionary<string, FlowLayoutPanel> tagPanels = new Dictionary<string, FlowLayoutPanel>();
        private readonly Dictionary<string, TextBox> tagSearch = new Dictionary<string, TextBox>();
        private readonly FlowLayoutPanel genderPanel = new FlowLayoutPanel();
        private readonly FlowLayoutPanel rarityPanel = new FlowLayoutPanel();
        private readonly Button resources = new Button();
        private readonly Button identityReview = new Button();
        public const string MultipleIdentityFilter = "多个身份／待检查";
        private bool updating;
        private string lastSingleId, previousSingleId;
        private readonly Timer stateTimer = new Timer { Interval = 500 };
        public CharacterTaggingForm(string root)
        {
            Store = new CharacterLabelStore(root);
            Text = "人物总览 · 人物资料与词条"; Font = new Font("Microsoft YaHei", 9); Size = new Size(1480, 930); MinimumSize = new Size(1080, 740); WindowState = FormWindowState.Maximized; StartPosition = FormStartPosition.CenterScreen;
            var top = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 78, Padding = new Padding(8), WrapContents = true };
            search.Width = 200; search.Text = Store.Data.search ?? ""; top.Controls.Add(new Label { Text = "搜索人物", AutoSize = true, Margin = new Padding(4, 7, 3, 0) }); top.Controls.Add(search);
            tier.DropDownStyle = ComboBoxStyle.DropDownList; tier.Width = 85; tier.Items.AddRange(new object[] { "全部", "1", "2", "3", "4", "5", "6", "SP", "待分类", "不合格" }); tier.SelectedItem = Store.Data.tier; if (tier.SelectedIndex < 0) tier.SelectedIndex = 0; top.Controls.Add(tier);
            filter.DropDownStyle = ComboBoxStyle.DropDownList; filter.Width = 160; top.Controls.Add(filter);
            identityReview.AutoSize = true; identityReview.Height = 29; identityReview.Click += delegate { filter.SelectedItem = MultipleIdentityFilter; }; top.Controls.Add(identityReview);
            top.Controls.Add(Button("全选当前结果", delegate { Gallery.ChooseAll(); }));
            top.Controls.Add(Button("撤销标注", delegate { Safe(delegate { Store.Revert(); RebuildFilter(); RefreshView(); }); }));
            top.Controls.Add(Button("沿用上一人物词条", CopyPrevious));
            top.Controls.Add(Button("选择图库", ChooseRoot));
            top.Controls.Add(Button("原阶级分类工具", delegate { new ClassifierForm(null).Show(); }));
            top.Controls.Add(Button("导出CSV", Export));
            autoNext.Text = "单人标注后下一位"; autoNext.AutoSize = true; top.Controls.Add(autoNext);
            var right = new Panel { Dock = DockStyle.Right, Width = 420, Padding = new Padding(10), BackColor = Color.FromArgb(245, 247, 250) };
            var content = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 0, Margin = Padding.Empty };
            content.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            var summary = new Panel(); var description = new Panel { Dock = DockStyle.Fill }; detail.Dock = DockStyle.Fill; detail.AutoEllipsis = true; preview.Dock = DockStyle.Right; preview.Width = 135;
            resources.Dock = DockStyle.Bottom; resources.Height = 27; resources.Click += delegate { var selected = Selected(); if (selected.Count == 1) MessageBox.Show(this, Store.DescribeResources(selected[0]), "动作素材与人物标记"); };
            description.Controls.Add(detail); description.Controls.Add(resources);
            preview.BackColor = Color.FromArgb(29, 34, 44); preview.Paint += delegate(object sender, PaintEventArgs e) { if (portrait != null) CharacterGallery.DrawSprite(e.Graphics, portrait, preview.ClientRectangle); };
            summary.Controls.Add(description); summary.Controls.Add(preview); AddRow(content, summary, 80);
            AddRow(content, new Label { Text = "性别 · 固有资料", Font = new Font(Font, FontStyle.Bold), TextAlign = ContentAlignment.BottomLeft }, 24);
            AddRow(content, genderPanel, 42);
            foreach (var category in new[] { "race", "identity" }) BuildSection(content, category);
            AddRow(content, new Label { Text = "Ctrl 多选 · Shift 连选 · 右键词条可移除或改名\n每人一个身份，点击词条替换；修改自动保存。", TextAlign = ContentAlignment.MiddleLeft }, 36);
            AddRow(content, new Label { Text = "阶级标记", Font = new Font(Font, FontStyle.Bold), TextAlign = ContentAlignment.BottomLeft }, 24);
            AddRow(content, rarityPanel, 36);
            right.Controls.Add(content); Gallery.Dock = DockStyle.Fill;
            status.Dock = DockStyle.Bottom; status.Height = 30; status.Padding = new Padding(8, 5, 0, 0);
            Controls.Add(Gallery); Controls.Add(right); Controls.Add(top); Controls.Add(status);
            Gallery.SelectionChanged = OnSelection;
            search.TextChanged += delegate { RefreshView(); }; tier.SelectedIndexChanged += delegate { RefreshView(); }; filter.SelectedIndexChanged += delegate { if (!updating) RefreshView(); };
            stateTimer.Tick += delegate { stateTimer.Stop(); Safe(delegate { SaveView(); Store.Save(); }); };
            FormClosing += delegate(object sender, FormClosingEventArgs e) { stateTimer.Stop(); try { SaveView(); Store.Save(); } catch (Exception ex) { e.Cancel = true; MessageBox.Show("保存失败，请重试：" + ex.Message); } };
            RebuildFilter(); RefreshView();
            if (!String.IsNullOrEmpty(Store.Data.selected)) { Gallery.Selected.Add(Store.Data.selected); Gallery.Reveal(Store.Data.selected); OnSelection(); }
            Shown += delegate { Safe(delegate { Store.Save(); }); };
        }
        private static Button Button(string text, Action action) { var b = new Button { Text = text, AutoSize = true, Height = 29 }; b.Click += delegate { action(); }; return b; }
        private List<CharacterCard> Selected() { return Store.Cards.Where(c => Gallery.Selected.Contains(c.label.id)).ToList(); }
        private void Safe(Action action) { try { action(); } catch (Exception ex) { MessageBox.Show(this, ex.Message, "操作未完成", MessageBoxButtons.OK, MessageBoxIcon.Warning); } }
        private void SaveView() { Store.Data.search = search.Text; Store.Data.tier = (string)tier.SelectedItem; Store.Data.filter = filter.SelectedItem == null ? "全部" : filter.SelectedItem.ToString(); Store.Data.selected = Selected().Select(c => c.label.id).FirstOrDefault() ?? ""; }
        private void Mutate(Action action, bool advance)
        {
            if (Selected().Count == 0) { MessageBox.Show("请先点击选择人物"); return; }
            Safe(delegate {
                int index = Gallery.Cards.FindIndex(c => Gallery.Selected.Contains(c.label.id)); string next = index >= 0 && index + 1 < Gallery.Cards.Count ? Gallery.Cards[index + 1].label.id : null;
                bool move = advance && (autoNext.Checked || (string)filter.SelectedItem == MultipleIdentityFilter) && Selected().Count == 1;
                SaveView(); Store.Change(action); RebuildFilter(); RefreshView();
                if (move && next != null && Gallery.Cards.Any(c => c.label.id == next)) { Gallery.Selected.Clear(); Gallery.Selected.Add(next); Gallery.Reveal(next); }
                OnSelection();
            });
        }
        private static void AddRow(TableLayoutPanel parent, Control control, float height)
        {
            int row = parent.RowCount++; parent.RowStyles.Add(new RowStyle(height < 0 ? SizeType.Percent : SizeType.Absolute, height < 0 ? 100 : height));
            control.Dock = DockStyle.Fill; control.Margin = new Padding(3); parent.Controls.Add(control, 0, row);
        }
        private void BuildSection(TableLayoutPanel parent, string category)
        {
            string title = category == "race" ? "种族 · 固有资料" : "身份 / 所属";
            AddRow(parent, new Label { Text = title, Font = new Font(Font, FontStyle.Bold), TextAlign = ContentAlignment.BottomLeft }, 24);
            var inputRow = new Panel();
            var input = new TextBox { Dock = DockStyle.Fill }; tagSearch[category] = input;
            var add = Button("新增并应用", delegate {
                if (Selected().Count > 0) Mutate(delegate { var tag = Store.AddTag(category, input.Text); Store.Apply(Selected(), tag, false); }, true);
                else Safe(delegate { Store.Change(delegate { Store.AddTag(category, input.Text); }); RebuildFilter(); RefreshView(); });
                input.Clear();
            }); add.Dock = DockStyle.Right; add.Width = 104; add.AutoSize = false; inputRow.Controls.Add(input); inputRow.Controls.Add(add); AddRow(parent, inputRow, 32);
            input.TextChanged += delegate { RebuildChips(); };
            var chips = new FlowLayoutPanel { AutoScroll = true, WrapContents = true }; tagPanels[category] = chips; AddRow(parent, chips, category == "identity" ? -1 : 78);
        }
        private void RebuildChips()
        {
            var selected = Selected();
            genderPanel.SuspendLayout(); foreach (Control c in genderPanel.Controls.Cast<Control>().ToArray()) c.Dispose(); genderPanel.Controls.Clear();
            foreach (string value in CharacterLabelStore.Genders)
            {
                string gender = value; int matches = selected.Count(c => c.label.gender == gender);
                var button = Button(gender + " (" + Store.Cards.Count(c => c.label.gender == gender) + ")", delegate { Mutate(delegate { Store.SetGender(Selected(), gender); }, true); });
                button.AutoSize = false; button.Width = 62; button.Height = 27;
                button.BackColor = matches == 0 ? Color.White : matches == selected.Count ? Color.LightBlue : Color.LightGoldenrodYellow;
                genderPanel.Controls.Add(button);
            }
            var clearGender = Button("清除标记", delegate { Mutate(delegate { Store.SetGender(Selected(), null); }, false); }); clearGender.AutoSize = false; clearGender.Width = 78; clearGender.Height = 27; genderPanel.Controls.Add(clearGender);
            genderPanel.ResumeLayout();
            rarityPanel.SuspendLayout(); foreach (Control c in rarityPanel.Controls.Cast<Control>().ToArray()) c.Dispose(); rarityPanel.Controls.Clear();
            Color[] tierColors = { Color.WhiteSmoke, Color.Honeydew, Color.AliceBlue, Color.Lavender, Color.LemonChiffon, Color.MistyRose };
            for (int i = 1; i <= 6; i++)
            {
                int rarity = i; int matches = selected.Count(c => c.tier == rarity.ToString());
                var button = Button(rarity + "阶", delegate { Mutate(delegate { Store.SetTier(Selected(), rarity); }, true); });
                button.AutoSize = false; button.Width = 57; button.Height = 27;
                button.BackColor = matches == 0 ? tierColors[i - 1] : matches == selected.Count ? Color.LightBlue : Color.LightGoldenrodYellow;
                rarityPanel.Controls.Add(button);
            }
            rarityPanel.ResumeLayout();
            foreach (var pair in tagPanels)
            {
                var panel = pair.Value; panel.SuspendLayout(); foreach (Control c in panel.Controls.Cast<Control>().ToArray()) c.Dispose(); panel.Controls.Clear();
                foreach (var t in Store.Data.tags.Where(t => t.category == pair.Key && t.name.IndexOf(tagSearch[pair.Key].Text.Trim(), StringComparison.CurrentCultureIgnoreCase) >= 0).OrderByDescending(t => t.used).ThenBy(t => t.name))
                {
                    var tag = t; int count = Store.Cards.Count(c => Store.Has(c, tag.id)), matches = selected.Count(c => Store.Has(c, tag.id));
                    var b = Button(tag.name + " (" + count + ")", delegate { Mutate(delegate { Store.Apply(Selected(), tag, false); }, true); });
                    b.BackColor = matches == 0 ? Color.White : matches == selected.Count ? Color.LightBlue : Color.LightGoldenrodYellow;
                    var menu = new ContextMenuStrip(); menu.Items.Add("从所选人物移除", null, delegate { Mutate(delegate { Store.Apply(Selected(), tag, true); }, false); });
                    menu.Items.Add("改名 / 合并同名词条", null, delegate { string name = Prompt("新的词条名称（已有同名则合并）", tag.name); if (name != null) Safe(delegate { Store.Change(delegate { Store.Rename(tag, name); }); RebuildFilter(); RefreshView(); }); });
                    b.ContextMenuStrip = menu; b.Disposed += delegate { menu.Dispose(); }; panel.Controls.Add(b);
                }
                panel.ResumeLayout();
            }
        }
        public static string Prompt(string title, string value)
        {
            using (var f = new Form { Text = title, Width = 430, Height = 155, StartPosition = FormStartPosition.CenterParent, FormBorderStyle = FormBorderStyle.FixedDialog, MinimizeBox = false, MaximizeBox = false })
            {
                var input = new TextBox { Left = 15, Top = 15, Width = 385, Text = value }; f.Controls.Add(input);
                var ok = new Button { Text = "确定", Left = 230, Top = 55, DialogResult = DialogResult.OK }; f.Controls.Add(ok);
                f.Controls.Add(new Button { Text = "取消", Left = 320, Top = 55, DialogResult = DialogResult.Cancel }); f.AcceptButton = ok; f.CancelButton = f.Controls[2] as Button;
                return f.ShowDialog() == DialogResult.OK ? input.Text : null;
            }
        }
        private void RebuildFilter()
        {
            updating = true; string old = filter.SelectedItem == null ? Store.Data.filter : filter.SelectedItem.ToString(); filter.Items.Clear();
            filter.Items.AddRange(new object[] { "全部", "未填种族", "未标记性别", "未填身份", MultipleIdentityFilter });
            foreach (var gender in CharacterLabelStore.Genders) filter.Items.Add("性别：" + gender);
            foreach (var t in Store.Data.tags.Where(t => t.category != "job")) filter.Items.Add((t.category == "race" ? "种族：" : "身份：") + t.name);
            filter.SelectedItem = old; if (filter.SelectedIndex < 0) filter.SelectedIndex = 0; updating = false;
        }
        private void RefreshView()
        {
            if (updating) return;
            string mode = filter.SelectedItem == null ? "全部" : filter.SelectedItem.ToString(); string tierValue = tier.SelectedItem == null ? "全部" : tier.SelectedItem.ToString();
            var tag = Store.Data.tags.FirstOrDefault(t => t.category != "job" && (t.category == "race" ? "种族：" : "身份：") + t.name == mode);
            var cards = Store.Cards.Where(c => (tierValue == "全部" || c.tier == tierValue) && (c.name.IndexOf(search.Text.Trim(), StringComparison.CurrentCultureIgnoreCase) >= 0) &&
                (tag != null ? Store.Has(c, tag.id) : mode == MultipleIdentityFilter ? c.label.identities.Count > 1 : mode.StartsWith("性别：") ? c.label.gender == mode.Substring(3) : mode == "未标记性别" ? String.IsNullOrEmpty(c.label.gender) : mode == "未填种族" ? String.IsNullOrEmpty(c.label.race) : mode == "未填身份" ? c.label.identities.Count == 0 : true)).ToList();
            Point scroll = Gallery.AutoScrollPosition; Gallery.SetCards(cards); Gallery.AutoScrollPosition = new Point(0, -scroll.Y);
            Gallery.Selected.RemoveWhere(id => !cards.Any(c => c.label.id == id)); OnSelection(); stateTimer.Stop(); stateTimer.Start();
        }
        private string NameOf(string id) { var found = Store.Data.tags.FirstOrDefault(t => t.id == id); return found == null ? "未填" : found.name; }
        private void OnSelection()
        {
            updating = true; var selected = Selected();
            resources.Visible = selected.Count == 1 && (selected[0].group != null || selected[0].label.identities.Count > 1);
            if (resources.Visible) resources.Text = selected[0].group == null ? "多个身份待确认 · 查看资料" : selected[0].group.members.Count + "套动作 · " + (String.IsNullOrEmpty(selected[0].conflicts) ? "查看素材" : "标记待统一");
            if (portrait != null) { portrait.Dispose(); portrait = null; }
            if (selected.Count == 1)
            {
                var c = selected[0]; detail.Text = c.name + " · " + c.tier + "阶 · " + (String.IsNullOrEmpty(c.label.gender) ? "性别未标记" : c.label.gender) + "\n" + NameOf(c.label.race) + " / " + String.Join("、", c.label.identities.Select(NameOf));
                if (lastSingleId != c.label.id) { previousSingleId = lastSingleId; lastSingleId = c.label.id; }
                try { portrait = CharacterLabelStore.LoadPortrait(c); } catch (Exception ex) { detail.Text += "\n预览失败：" + ex.Message; }
            }
            else detail.Text = selected.Count == 0 ? "点击人物即可编辑\n可先输入词条建立词库" : "已选 " + selected.Count + " 人\n蓝色：全部拥有 · 黄色：部分拥有";
            preview.Invalidate(); RebuildChips();
            int multiple = Store.Cards.Count(c => c.label.identities.Count > 1); identityReview.Text = "检查多身份 (" + multiple + ")";
            status.Text = String.Format("图库 {0} 人 · 当前 {1} 人 · 已选 {2} 人 · 已填种族 {3}/{0} · {4}", Store.Cards.Count, Gallery.Cards.Count, selected.Count, Store.Cards.Count(c => !String.IsNullOrEmpty(c.label.race)), Store.Root);
            updating = false; stateTimer.Stop(); stateTimer.Start();
        }
        private void ChooseRoot()
        {
            using (var dialog = new FolderBrowserDialog { Description = "选择包含1～6等阶级目录的人物图库", SelectedPath = Store.Root }) if (dialog.ShowDialog(this) == DialogResult.OK)
                Safe(delegate { SaveView(); Store.Save(); if (Path.GetFullPath(dialog.SelectedPath) != Store.Root) System.Diagnostics.Process.Start(Application.ExecutablePath, "\"" + dialog.SelectedPath.TrimEnd('\\') + "\""); });
        }
        private void CopyPrevious()
        {
            var source = Store.Cards.FirstOrDefault(c => c.label.id == previousSingleId);
            if (source == null) { MessageBox.Show("先选择一个已填写人物，再选择需要沿用词条的人物。"); return; }
            string race = source.label.race, gender = source.label.gender; var identities = source.label.identities.ToArray();
            Mutate(delegate { Store.CopyTraits(Selected(), race, gender, identities); }, true);
        }
        private static string Csv(string value) { return "\"" + (value ?? "").Replace("\"", "\"\"") + "\""; }
        private void Export()
        {
            using (var dialog = new SaveFileDialog { Filter = "CSV表格|*.csv", FileName = "人物羁绊分类.csv" }) if (dialog.ShowDialog(this) == DialogResult.OK)
                Safe(delegate { File.WriteAllText(dialog.FileName, ExportCsv(), new UTF8Encoding(true)); });
        }
        public string ExportCsv()
        {
            var text = new StringBuilder("人物ID,名称,阶级,相对路径,种族,性别,身份,动作素材,资料待统一\r\n");
            foreach (var c in Store.Cards) text.AppendLine(String.Join(",", new[] { c.label.id, c.name, c.tier, c.label.path, NameOf(c.label.race), c.label.gender ?? "", String.Join("；", c.label.identities.Select(NameOf)), c.group == null ? c.label.path : String.Join("；", Store.Data.characters.Where(label => c.group.members.Contains(label.id)).Select(label => label.path)), c.conflicts }.Select(Csv)));
            return text.ToString();
        }
        protected override void Dispose(bool disposing) { if (disposing) { stateTimer.Dispose(); if (portrait != null) portrait.Dispose(); } base.Dispose(disposing); }
        public static string DefaultRoot()
        {
            string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "LegionBattle/LegionBattle/Assets/Characters");
            if (Directory.Exists(path)) return path;
            path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "CHARA"); if (Directory.Exists(path)) return path;
            throw new DirectoryNotFoundException("找不到人物图库，请在启动参数中指定图库目录。");
        }
    }
}
