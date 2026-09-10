"""فحص مواصفات الجهاز وتقييم جاهزيته للبرمجة والجرافيكس والألعاب والأعمال المكتبية.

الفحص يعمل في خيط مستقل حتى لا تتجمد واجهة WinAdmin أثناء جمع معلومات العتاد.
"""

import platform
import subprocess
import psutil
from PyQt5.QtCore import QThread, pyqtSignal


class HardwareAssessment:
    """محلل محلي لمواصفات الجهاز وإنتاج توصيات عملية."""

    @staticmethod
    def _gpu_info():
        gpus = []
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion | ConvertTo-Json -Compress"],
                    capture_output=True, text=True, timeout=8,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode == 0 and result.stdout.strip():
                    import json
                    data = json.loads(result.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        ram = item.get("AdapterRAM") or 0
                        gpus.append({
                            "name": item.get("Name") or "غير معروف",
                            "vram_gb": round(ram / (1024 ** 3), 1) if ram else 0,
                            "driver": item.get("DriverVersion") or "—",
                        })
            except Exception:
                pass
        return gpus

    @staticmethod
    def collect():
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(psutil.disk_partitions(all=False)[0].mountpoint) if psutil.disk_partitions(all=False) else None
        cpu_name = platform.processor() or platform.uname().processor or "غير معروف"
        physical = psutil.cpu_count(logical=False) or 0
        logical = psutil.cpu_count(logical=True) or 0
        freq = psutil.cpu_freq()
        gpus = HardwareAssessment._gpu_info()
        gpu_text = gpus[0]["name"] if gpus else "غير متوفر / لم يتم التعرف عليه"
        vram = max((g.get("vram_gb", 0) for g in gpus), default=0)

        specs = {
            "hostname": platform.node(),
            "os": platform.platform(),
            "architecture": platform.machine(),
            "cpu": cpu_name,
            "physical_cores": physical,
            "logical_cores": logical,
            "frequency_ghz": round((freq.max or freq.current) / 1000, 2) if freq else 0,
            "ram_gb": round(mem.total / (1024 ** 3), 1),
            "ram_available_gb": round(mem.available / (1024 ** 3), 1),
            "disk_gb": round(disk.total / (1024 ** 3), 1) if disk else 0,
            "disk_free_gb": round(disk.free / (1024 ** 3), 1) if disk else 0,
            "gpu": gpu_text,
            "vram_gb": vram,
        }
        return HardwareAssessment.analyze(specs)

    @staticmethod
    def analyze(s):
        ram = s["ram_gb"]
        cores = s["logical_cores"]
        vram = s["vram_gb"]
        cpu = s["cpu"].lower()
        gpu = s["gpu"].lower()

        scores = {"برمجة وتطوير البرمجيات": 0, "تصميم وجرافيكس": 0, "تحرير الفيديو": 0,
                  "الأعمال المكتبية": 0, "الذكاء الاصطناعي المحلي": 0, "الألعاب": 0}

        if ram >= 16:
            scores["برمجة وتطوير البرمجيات"] += 40
            scores["تصميم وجرافيكس"] += 30
            scores["تحرير الفيديو"] += 30
            scores["الذكاء الاصطناعي المحلي"] += 25
        elif ram >= 8:
            scores["برمجة وتطوير البرمجيات"] += 25
            scores["الأعمال المكتبية"] += 35
        else:
            scores["الأعمال المكتبية"] += 20

        if cores >= 8:
            scores["برمجة وتطوير البرمجيات"] += 25
            scores["تحرير الفيديو"] += 25
            scores["الذكاء الاصطناعي المحلي"] += 25
        elif cores >= 4:
            scores["برمجة وتطوير البرمجيات"] += 18
        else:
            scores["الأعمال المكتبية"] += 15

        if vram >= 8:
            scores["تصميم وجرافيكس"] += 35
            scores["تحرير الفيديو"] += 30
            scores["الألعاب"] += 35
            scores["الذكاء الاصطناعي المحلي"] += 40
        elif vram >= 4:
            scores["تصميم وجرافيكس"] += 25
            scores["تحرير الفيديو"] += 20
            scores["الألعاب"] += 22
            scores["الذكاء الاصطناعي المحلي"] += 25
        elif any(x in gpu for x in ("nvidia", "amd", "radeon", "geforce")):
            scores["الألعاب"] += 15
            scores["تصميم وجرافيكس"] += 12

        if "intel" in cpu and "core" in cpu:
            scores["برمجة وتطوير البرمجيات"] += 15
        if s["disk_free_gb"] < 30:
            scores["الأعمال المكتبية"] -= 5

        for key in scores:
            scores[key] = max(0, min(100, scores[key]))

        recommendations = []
        if ram < 8:
            recommendations.append("رفع الذاكرة RAM إلى 8GB على الأقل، ويفضل 16GB للبرمجة والتطوير.")
        elif ram < 16:
            recommendations.append("رفع RAM إلى 16GB سيحسن تشغيل IDEs والمتصفحات والآلات الافتراضية.")
        if s["disk_free_gb"] < 30:
            recommendations.append("مساحة القرص الحرة منخفضة؛ نظّف الملفات المؤقتة واترك مساحة كافية للنظام.")
        if vram < 4:
            recommendations.append("الجرافيكس ثلاثي الأبعاد والذكاء الاصطناعي المحلي سيستفيدان من بطاقة رسومية بذاكرة 4GB VRAM أو أكثر.")
        if cores < 4:
            recommendations.append("المعالج محدود نسبيًا؛ معالج متعدد الأنوية سيحسن البناء والتجميع وتشغيل الأدوات المتوازية.")
        if not recommendations:
            recommendations.append("مواصفات الجهاز متوازنة. حافظ على تحديث التعريفات والنظام، وراقب درجات الحرارة واستهلاك الموارد.")

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best = ranked[:3]
        return {
            "specs": s,
            "scores": scores,
            "best_uses": best,
            "recommendations": recommendations,
        }


class HardwareAssessmentWorker(QThread):
    """ينفذ الفحص خارج خيط واجهة Qt."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.finished.emit(HardwareAssessment.collect())
        except Exception as exc:
            self.error.emit(str(exc))
