using System.Collections;
using UnityEngine;

namespace LegionBattle.Battle
{
    /// <summary>
    /// 战斗受击震屏控制器
    /// 震屏强度与持续时间根据本次造成伤害与受击方总战力之比动态计算，以造成 50% 总战力伤害为最大震级
    /// </summary>
    public class CameraShakeController : MonoBehaviour
    {
        private static CameraShakeController _instance;
        public static CameraShakeController Instance => _instance;

        private Vector3 originalLocalPos;
        private Coroutine shakeCoroutine;
        public const float MaximumDuration = .38f;
        public Vector3 RestWorldPosition => transform.parent==null?originalLocalPos:transform.parent.TransformPoint(originalLocalPos);

        private void Awake()
        {
            _instance = this;
            originalLocalPos = transform.localPosition;
        }

        private void OnDestroy()
        {
            if (_instance == this) _instance = null;
        }

        private void OnDisable() { ResetShake(); }
        public void ResetShake()
        {
            if(shakeCoroutine!=null){StopCoroutine(shakeCoroutine);shakeCoroutine=null;}
            transform.localPosition=originalLocalPos;
        }
        public static Vector3 DamageOffset(float elapsed,int damage,int defenderMaxBP)
        {
            if(elapsed<0||damage<=0||defenderMaxBP<=0)return Vector3.zero;
            float ratio=Mathf.Clamp01(damage/(defenderMaxBP*.50f));
            float intensity=Mathf.Lerp(.06f,.50f,ratio),duration=Mathf.Lerp(.12f,MaximumDuration,ratio);
            return Offset(elapsed,intensity,duration);
        }
        private static Vector3 Offset(float elapsed,float intensity,float duration)
        {
            if(elapsed<0||elapsed>=duration||duration<=0)return Vector3.zero;
            float decay=Mathf.Pow(1-elapsed/duration,2);
            return new Vector3(Mathf.Sin(elapsed*113+1.3f),Mathf.Sin(elapsed*151+.7f),0)*intensity*decay;
        }
        public static void SampleByDamage(float elapsed,int damage,int defenderMaxBP)
        {
            var instance=Ensure();if(instance==null)return;
            instance.ResetShake();
            instance.transform.localPosition=instance.originalLocalPos+DamageOffset(elapsed,damage,defenderMaxBP);
        }

        /// <summary>
        /// 确保主摄像机挂载了震屏控制器
        /// </summary>
        public static CameraShakeController Ensure()
        {
            Camera cam = Camera.main;
            if (cam == null) cam = FindObjectOfType<Camera>();
            if(_instance!=null&&cam!=null&&_instance.gameObject==cam.gameObject)return _instance;
            if (cam != null)
            {
                _instance = cam.GetComponent<CameraShakeController>();
                if (_instance == null)
                {
                    _instance = cam.gameObject.AddComponent<CameraShakeController>();
                }
            }
            return _instance;
        }

        /// <summary>
        /// 根据造成伤害与受击方最大战力之比触发动态震屏
        /// </summary>
        /// <param name="damage">本次命中造成的实际伤害</param>
        /// <param name="defenderMaxBP">受击方军团最大战力</param>
        public static void ShakeByDamage(int damage, int defenderMaxBP)
        {
            if (damage <= 0 || defenderMaxBP <= 0) return;

            // 核心算法：以造成对方 50% 最大战力为最大震级 (50% 伤害 -> ratio = 1.0)
            float damageRatio = (float)damage / (defenderMaxBP * 0.50f);
            float normalized = Mathf.Clamp01(damageRatio);

            // 最小轻度震动 0.06，最大震撼震动 0.50
            float intensity = Mathf.Lerp(0.06f, 0.50f, normalized);
            // 最小持续时间 0.12s，最大持续时间 0.38s
            float duration = Mathf.Lerp(0.12f, MaximumDuration, normalized);

            Ensure();
            if (_instance != null)
            {
                _instance.TriggerShake(intensity, duration);
            }
        }

        public void TriggerShake(float intensity, float duration)
        {
            if (shakeCoroutine != null)
            {
                StopCoroutine(shakeCoroutine);
            }
            shakeCoroutine = StartCoroutine(CoShake(intensity, duration));
        }

        private IEnumerator CoShake(float intensity, float duration)
        {
            float elapsed = 0f;
            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                transform.localPosition = originalLocalPos + Offset(elapsed,intensity,duration);
                yield return null;
            }

            transform.localPosition = originalLocalPos;
            shakeCoroutine = null;
        }
    }
}
