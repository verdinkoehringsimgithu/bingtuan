using System;
using System.Collections.Generic;
using UnityEngine;

namespace HexTerrainStudio
{
    [Serializable]
    public class HexMapData
    {
        public string mapName = "HexMap_01";
        public int columns = 35;
        public int rows = 31;
        public float hexRadius = 2.5f;
        public List<HexTileData> tiles = new List<HexTileData>();

        public HexTileData GetTile(int col, int row)
        {
            if (tiles == null) return null;
            return tiles.Find(t => t.col == col && t.row == row);
        }
    }

    [Serializable]
    public class HexTileData
    {
        public int col;
        public int row;
        public float x;
        public float y;
        public float z;

        // Layer 1: Base
        public bool hasBase = true;
        public string basePrefab = "Hexagon";
        public string baseMaterial = "Hexagon";

        // Layer 2: Hill (Yama1, Yama2, Yama3)
        public bool hasHill = false;
        public string hillPrefab = "";
        public float hillRotY = 0f;

        // Faction Data (100 Factions)
        public int factionId = -1; // -1 = Neutral, 0~99 = Faction
        public bool isCapital = false;

        // Layer 3: Mountain & Attachments
        public List<HexAttachmentData> attachments = new List<HexAttachmentData>();
    }

    [Serializable]
    public class HexAttachmentData
    {
        public string prefabName;
        public string attachedLayer = "Base"; // "Base" or "Hill"
        public float localX;
        public float localY;
        public float localZ;
        public float worldX;
        public float worldY;
        public float worldZ;
        public float rotX;
        public float rotY;
        public float rotZ;
        public float rotW = 1f;
        public float scaleX = 1f;
        public float scaleY = 1f;
        public float scaleZ = 1f;
    }
}
