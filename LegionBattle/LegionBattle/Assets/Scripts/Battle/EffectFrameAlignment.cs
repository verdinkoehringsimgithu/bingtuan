using UnityEngine;

namespace LegionBattle.Battle
{
    // Canvas padding varies between frames. Keep the visible silhouette at the fixed anchor.
    public static class EffectFrameAlignment
    {
        public static Vector2 Pivot(Color32[] pixels,int textureWidth,Rect rect)
        {
            int x0=Mathf.RoundToInt(rect.x),y0=Mathf.RoundToInt(rect.y);
            int width=Mathf.RoundToInt(rect.width),height=Mathf.RoundToInt(rect.height);
            int minX=width,minY=height,maxX=-1,maxY=-1;
            for(int y=0;y<height;y++)for(int x=0;x<width;x++)
                if(pixels[(y0+y)*textureWidth+x0+x].a>0){minX=Mathf.Min(minX,x);minY=Mathf.Min(minY,y);maxX=Mathf.Max(maxX,x);maxY=Mathf.Max(maxY,y);}
            return maxX<0?new Vector2(.5f,.5f):new Vector2((minX+maxX+1)/(2f*width),(minY+maxY+1)/(2f*height));
        }
    }
}
