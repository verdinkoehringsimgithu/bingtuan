using System;
using System.Collections.Generic;
using System.IO;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;

namespace LegionBattle.Data.Importers
{
    /// <summary>
    /// 轻量级 CSV 数据表导入解析器（完全零依赖，兼容各种 CSV 换行和编码）
    /// </summary>
    public static class CsvTableReader
    {
        public static List<string[]> ReadCsvLines(string filePath)
        {
            var rows = new List<string[]>();
            if (!File.Exists(filePath)) return rows;

            using var reader = new StreamReader(filePath);
            string line;
            while ((line = reader.ReadLine()) != null)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                rows.Add(ParseCsvRow(line));
            }
            return rows;
        }

        public static string[] ParseCsvRow(string line)
        {
            var result = new List<string>();
            bool inQuotes = false;
            var current = new System.Text.StringBuilder();

            for (int i = 0; i < line.Length; i++)
            {
                char c = line[i];
                if (c == '\"')
                {
                    inQuotes = !inQuotes;
                }
                else if (c == ',' && !inQuotes)
                {
                    result.Add(current.ToString().Trim());
                    current.Clear();
                }
                else
                {
                    current.Append(c);
                }
            }
            result.Add(current.ToString().Trim());
            return result.ToArray();
        }

        public static int ParseInt(string s, int defaultVal = 0)
        {
            return int.TryParse(s, out int v) ? v : defaultVal;
        }

        public static float ParseFloat(string s, float defaultVal = 0f)
        {
            return float.TryParse(s, out float v) ? v : defaultVal;
        }

        public static long ParseLong(string s, long defaultVal = 0)
        {
            return long.TryParse(s, out long v) ? v : defaultVal;
        }
    }
}
