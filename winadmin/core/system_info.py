"""
core/system_info.py — جلب معلومات النظام
يوفر دوال لقراءة بيانات الأداء، العمليات، الأقراص، الشبكة، الأمان، والخدمات.
يعمل بشكل متوافق مع Windows و Linux.
"""

import psutil
import platform
import os
import subprocess
import logging
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"


class SystemInfo:
    """جمع معلومات النظام بشكل موحّد."""

    # ── معلومات عامة ────────────────────────────────────────
    @staticmethod
    def get_system_overview() -> Dict:
        """معلومات عامة عن النظام."""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            return {
                "hostname": socket.gethostname(),
                "os": platform.platform(),
                "arch": platform.machine(),
                "processor": platform.processor() or "N/A",
                "python_ver": platform.python_version(),
                "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
                "uptime": str(uptime).split(".")[0],
                "cpu_count_physical": psutil.cpu_count(logical=False),
                "cpu_count_logical": psutil.cpu_count(logical=True),
            }
        except Exception as e:
            logger.error(f"خطأ في قراءة معلومات النظام: {e}")
            return {}

    # ── المعالج ─────────────────────────────────────────────
    @staticmethod
    def get_cpu_info() -> Dict:
        """معلومات المعالج والاستهلاك."""
        try:
            freq = psutil.cpu_freq()
            return {
                "percent": psutil.cpu_percent(interval=0.5),
                "per_cpu": psutil.cpu_percent(interval=0.5, percpu=True),
                "freq_current": freq.current if freq else 0,
                "freq_min": freq.min if freq else 0,
                "freq_max": freq.max if freq else 0,
                "count_physical": psutil.cpu_count(logical=False),
                "count_logical": psutil.cpu_count(logical=True),
            }
        except Exception as e:
            logger.error(f"خطأ في قراءة معلومات المعالج: {e}")
            return {"percent": 0, "per_cpu": [], "freq_current": 0}

    # ── الذاكرة ─────────────────────────────────────────────
    @staticmethod
    def get_memory_info() -> Dict:
        """معلومات الذاكرة العشوائية."""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                "total": mem.total,
                "used": mem.used,
                "available": mem.available,
                "percent": mem.percent,
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_percent": swap.percent,
            }
        except Exception as e:
            logger.error(f"خطأ في قراءة معلومات الذاكرة: {e}")
            return {"total": 0, "used": 0, "available": 0, "percent": 0}

    # ── الأقراص ─────────────────────────────────────────────
    @staticmethod
    def get_disk_info() -> List[Dict]:
        """معلومات الأقراص والتخزين."""
        disks = []
        try:
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "opts": part.opts,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                    })
                except (PermissionError, OSError):
                    continue
        except Exception as e:
            logger.error(f"خطأ في قراءة معلومات الأقراص: {e}")
        return disks

    # ── الشبكة ──────────────────────────────────────────────
    @staticmethod
    def get_network_info() -> Dict:
        """معلومات الشبكة وحركة البيانات."""
        try:
            net_io = psutil.net_io_counters()
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            interfaces = []
            for iface, addr_list in addrs.items():
                iface_info = {"name": iface, "addresses": []}
                for addr in addr_list:
                    iface_info["addresses"].append({
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast,
                    })
                if iface in stats:
                    s = stats[iface]
                    iface_info["speed"] = s.speed
                    iface_info["isup"] = s.isup
                interfaces.append(iface_info)

            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "interfaces": interfaces,
            }
        except Exception as e:
            logger.error(f"خطأ في قراءة معلومات الشبكة: {e}")
            return {"bytes_sent": 0, "bytes_recv": 0, "interfaces": []}

    # ── العمليات ─────────────────────────────────────────────
    @staticmethod
    def get_processes() -> List[Dict]:
        """قائمة العمليات الجارية مع استهلاك الموارد."""
        procs = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent',
                                          'memory_percent', 'status', 'create_time',
                                          'num_threads', 'exe']):
            try:
                info = proc.info
                info['cpu_percent'] = proc.cpu_percent(interval=0) or 0
                info['memory_percent'] = info.get('memory_percent') or 0
                info['memory_mb'] = (info['memory_percent'] / 100 * psutil.virtual_memory().total) / (1024 * 1024) if info['memory_percent'] else 0
                info['create_time_str'] = datetime.fromtimestamp(info['create_time']).strftime("%Y-%m-%d %H:%M") if info.get('create_time') else ""
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return procs

    @staticmethod
    def kill_process(pid: int) -> Tuple[bool, str]:
        """إيقاف عملية بالقوة."""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=5)
            return True, f"تم إيقاف العملية {proc.name()} (PID: {pid})"
        except psutil.NoSuchProcess:
            return False, f"العملية {pid} غير موجودة"
        except psutil.AccessDenied:
            return False, f"لا تملك صلاحية إيقاف العملية {pid}"
        except Exception as e:
            return False, f"خطأ في إيقاف العملية: {e}"

    # ── المستخدمون والجلسات ──────────────────────────────────
    @staticmethod
    def get_users() -> List[Dict]:
        """المستخدمون النشطون والجلسات."""
        users = []
        try:
            for user in psutil.users():
                users.append({
                    "name": user.name,
                    "terminal": user.terminal or "N/A",
                    "host": user.host or "localhost",
                    "started": datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M:%S") if user.started else "",
                    "pid": user.pid or 0,
                })
        except Exception as e:
            logger.error(f"خطأ في قراءة المستخدمين: {e}")

        # على Windows نحاول جلب معلومات إضافية عبر WMI
        if IS_WINDOWS:
            try:
                import wmi
                w = wmi.WMI()
                for sess in w.Win32_LogonSession():
                    try:
                        user = sess.Associate("Win32_UserAccount")
                        if user:
                            for u in user:
                                users.append({
                                    "name": u.Name,
                                    "terminal": sess.LogonId,
                                    "host": sess.LogonType,
                                    "started": sess.StartTime.strftime("%Y-%m-%d %H:%M:%S") if sess.StartTime else "",
                                    "pid": 0,
                                })
                    except Exception:
                        continue
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"لم يتم جلب جلسات WMI: {e}")

        return users

    # ── الخدمات (Windows) ────────────────────────────────────
    @staticmethod
    def get_services() -> List[Dict]:
        """قائمة خدمات النظام."""
        services = []
        try:
            if IS_WINDOWS:
                import wmi
                w = wmi.WMI()
                for svc in w.Win32_Service():
                    services.append({
                        "name": svc.Name,
                        "display_name": svc.DisplayName,
                        "status": svc.State,
                        "start_mode": svc.StartMode,
                        "pid": svc.ProcessId or 0,
                        "description": svc.Description or "",
                    })
            else:
                # على Linux نستخدم systemctl
                result = subprocess.run(["systemctl", "list-units", "--type=service",
                                        "--all", "--no-pager", "--no-legend"],
                                       capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        parts = line.split()
                        if len(parts) >= 4:
                            services.append({
                                "name": parts[0].replace(".service", ""),
                                "display_name": " ".join(parts[4:]) if len(parts) > 4 else parts[0],
                                "status": parts[2],
                                "start_mode": parts[1],
                                "pid": 0,
                                "description": "",
                            })
        except Exception as e:
            logger.error(f"خطأ في قراءة الخدمات: {e}")
        return services

    @staticmethod
    def control_service(name: str, action: str) -> Tuple[bool, str]:
        """التحكم بخدمة (start/stop/restart)."""
        try:
            if IS_WINDOWS:
                result = subprocess.run(["net", action, name],
                                       capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    return True, f"تم {action} للخدمة {name}"
                else:
                    return False, f"فشل {action} للخدمة {name}: {result.stderr}"
            else:
                result = subprocess.run(["systemctl", action, name],
                                       capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    return True, f"تم {action} للخدمة {name}"
                else:
                    return False, f"فشل {action}: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, f"انتهت المهلة أثناء {action} للخدمة {name}"
        except Exception as e:
            return False, f"خطأ: {e}"

    @staticmethod
    def set_service_start_mode(name: str, mode: str) -> Tuple[bool, str]:
        """تغيير نوع بدء الخدمة."""
        try:
            if IS_WINDOWS:
                mode_map = {"automatic": "auto", "manual": "demand", "disabled": "disabled"}
                sc_mode = mode_map.get(mode.lower(), mode.lower())
                result = subprocess.run(["sc", "config", name, "start=", sc_mode],
                                       capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    return True, f"تم تغيير نوع بدء {name} إلى {mode}"
                return False, f"فشل: {result.stderr}"
            else:
                result = subprocess.run(["systemctl", "enable" if mode == "automatic" else "disable", name],
                                       capture_output=True, text=True, timeout=15)
                return result.returncode == 0, "تم" if result.returncode == 0 else f"فشل: {result.stderr}"
        except Exception as e:
            return False, f"خطأ: {e}"

    # ── الأمان والصحة ──────────────────────────────────────
    @staticmethod
    def get_security_info() -> Dict:
        """معلومات الأمان والصحة."""
        info = {
            "defender_status": "غير متوفر",
            "pending_updates": [],
            "critical_services": [],
            "event_errors": [],
        }

        if IS_WINDOWS:
            # حالة Windows Defender
            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     "Get-MpComputerStatus | Select-Object -Property RealTimeProtectionEnabled, AntivirusEnabled, AntispywareEnabled | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0 and result.stdout.strip():
                    import json
                    data = json.loads(result.stdout)
                    info["defender_status"] = "مفعّل" if data.get("RealTimeProtectionEnabled") else "معطّل"
            except Exception:
                info["defender_status"] = "تعذرت القراءة"

            # التحديثات المعلقة
            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     "Get-WUList -IsInstalled 0 | Select-Object Title, KBArticleIDs | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=20
                )
                if result.returncode == 0 and result.stdout.strip():
                    import json
                    info["pending_updates"] = json.loads(result.stdout)
            except Exception:
                pass

            # قراءة Event Viewer
            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     "Get-EventLog -LogName System -EntryType Error -Newest 10 | Select-Object TimeGenerated, Source, EventID, Message | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=20
                )
                if result.returncode == 0 and result.stdout.strip():
                    import json
                    events = json.loads(result.stdout)
                    if isinstance(events, dict):
                        events = [events]
                    for ev in events:
                        info["event_errors"].append({
                            "time": ev.get("TimeGenerated", ""),
                            "source": ev.get("Source", ""),
                            "event_id": ev.get("EventID", 0),
                            "message": (ev.get("Message", "") or "")[:200],
                        })
            except Exception:
                pass

        # الخدمات الحرجة
        critical_names = ["EventLog", "DNS", "LanmanServer", "LanmanWorkstation",
                          "Winmgmt", "RpcSs", "Schedule", "Spooler"] if IS_WINDOWS else \
                         ["sshd", "cron", "systemd", "networking", "dbus"]
        for svc in SystemInfo.get_services():
            if svc["name"].lower() in [c.lower() for c in critical_names]:
                info["critical_services"].append(svc)

        return info

    # ── إدارة التخزين ──────────────────────────────────────
    @staticmethod
    def find_large_directories(path: str = "C:\\", min_size_mb: int = 500) -> List[Dict]:
        """البحث عن المجلدات الكبيرة."""
        large_dirs = []
        try:
            for entry in os.scandir(path):
                if entry.is_dir(follow_symlinks=False):
                    try:
                        total_size = 0
                        for root, dirs, files in os.walk(entry.path):
                            for f in files:
                                try:
                                    total_size += os.path.getsize(os.path.join(root, f))
                                except (OSError, PermissionError):
                                    continue
                            if total_size > min_size_mb * 1024 * 1024 * 10:
                                break  # حد أقصى لتسريع البحث
                        if total_size >= min_size_mb * 1024 * 1024:
                            large_dirs.append({
                                "path": entry.path,
                                "size_mb": round(total_size / (1024 * 1024), 1),
                                "size_gb": round(total_size / (1024 * 1024 * 1024), 2),
                            })
                    except (PermissionError, OSError):
                        continue
        except Exception as e:
            logger.error(f"خطأ في البحث عن المجلدات الكبيرة: {e}")
        return sorted(large_dirs, key=lambda x: x["size_mb"], reverse=True)

    @staticmethod
    def get_temp_dirs() -> List[str]:
        """مسارات الملفات المؤقتة."""
        temp_dirs = []
        if IS_WINDOWS:
            temp_dirs = [
                os.environ.get("TEMP", ""),
                os.environ.get("TMP", ""),
                os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Temp"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "INetCache"),
            ]
        else:
            temp_dirs = ["/tmp", "/var/tmp", os.path.expanduser("~/.cache")]
        return [d for d in temp_dirs if d and os.path.exists(d)]

    @staticmethod
    def clean_temp_files() -> Tuple[int, int]:
        """تنظيف الملفات المؤقتة. يعيد (عدد الملفات المحذوفة، حجم المفرغ بالبايت)."""
        deleted = 0
        freed = 0
        for temp_dir in SystemInfo.get_temp_dirs():
            try:
                for root, dirs, files in os.walk(temp_dir):
                    for f in files:
                        try:
                            fpath = os.path.join(root, f)
                            fsize = os.path.getsize(fpath)
                            os.remove(fpath)
                            deleted += 1
                            freed += fsize
                        except (PermissionError, OSError, FileNotFoundError):
                            continue
            except (PermissionError, OSError):
                continue
        return deleted, freed

    @staticmethod
    def get_installed_apps_size() -> List[Dict]:
        """حجم التطبيقات المثبتة."""
        apps = []
        if IS_WINDOWS:
            try:
                import wmi
                w = wmi.WMI()
                for app in w.Win32_Product():
                    try:
                        apps.append({
                            "name": app.Name,
                            "version": app.Version,
                            "size_mb": round((app.PackageSize or 0) / 1024, 1) if app.PackageSize else 0,
                            "install_date": str(app.InstallDate) if app.InstallDate else "",
                            "vendor": app.Vendor or "",
                        })
                    except Exception:
                        continue
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"لم يتم جلب التطبيقات عبر WMI: {e}")

            # طريقة بديلة عبر الريجستري
            if not apps:
                try:
                    result = subprocess.run(
                        ["powershell", "-Command",
                         "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
                         "Where-Object { $_.DisplayName } | "
                         "Select-Object DisplayName, DisplayVersion, EstimatedSize, Publisher | ConvertTo-Json"],
                        capture_output=True, text=True, timeout=20
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        import json
                        data = json.loads(result.stdout)
                        if isinstance(data, dict):
                            data = [data]
                        for item in data:
                            apps.append({
                                "name": item.get("DisplayName", ""),
                                "version": item.get("DisplayVersion", ""),
                                "size_mb": round((item.get("EstimatedSize", 0) or 0) / 1024, 1),
                                "install_date": "",
                                "vendor": item.get("Publisher", ""),
                            })
                except Exception:
                    pass
        else:
            try:
                result = subprocess.run(["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Installed-Size}\n"],
                                       capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            apps.append({
                                "name": parts[0],
                                "version": parts[1],
                                "size_mb": round(int(parts[2]) / 1024, 1) if parts[2].isdigit() else 0,
                                "install_date": "",
                                "vendor": "",
                            })
            except Exception:
                pass

        return sorted(apps, key=lambda x: x.get("size_mb", 0), reverse=True)

    # ── أدوات مساعدة ──────────────────────────────────────
    @staticmethod
    def bytes_to_human(n: float) -> str:
        """تحويل البايتات إلى صيغة مقروءة."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(n) < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} PB"
