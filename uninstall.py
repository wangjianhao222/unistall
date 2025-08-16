# uninstaller.py
# Simple Windows uninstaller GUI using registry uninstall strings.
# Works without extra packages (uses built-in winreg, tkinter, ctypes).
# Comments are in English for clarity; UI and messages shown in Chinese.

import sys
import os
import subprocess
import shlex
import ctypes
import threading
import time
import traceback
from tkinter import *
from tkinter import ttk, messagebox, scrolledtext
import winreg

# Registry locations to search for uninstall information
REG_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

def is_admin():
    """Return True if running with admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def read_reg_value(key, name):
    try:
        return winreg.QueryValueEx(key, name)[0]
    except Exception:
        return None

def gather_installed_programs():
    """
    Scan registry uninstall keys and return a list of dictionaries:
    { 'name', 'uninstall', 'quiet_uninstall', 'publisher', 'version', 'install_location', 'key_path' }
    """
    apps = []
    seen = set()
    for root, path in REG_PATHS:
        try:
            base = winreg.OpenKey(root, path)
        except FileNotFoundError:
            continue
        try:
            sub_count = winreg.QueryInfoKey(base)[0]
        except Exception:
            continue
        for i in range(sub_count):
            try:
                sub_name = winreg.EnumKey(base, i)
                sub = winreg.OpenKey(base, sub_name)
            except OSError:
                continue
            try:
                display = read_reg_value(sub, "DisplayName")
                if not display:
                    # Some entries don't have DisplayName -> ignore
                    continue
                # Deduplicate by display name + uninstall string
                uninstall = read_reg_value(sub, "UninstallString")
                quiet = read_reg_value(sub, "QuietUninstallString")
                publisher = read_reg_value(sub, "Publisher")
                version = read_reg_value(sub, "DisplayVersion")
                install_loc = read_reg_value(sub, "InstallLocation")
                key_id = f"{display}|{uninstall}"
                if key_id in seen:
                    continue
                seen.add(key_id)
                apps.append({
                    'name': display,
                    'uninstall': uninstall,
                    'quiet_uninstall': quiet,
                    'publisher': publisher,
                    'version': version,
                    'install_location': install_loc,
                    'reg_key': f"{root}\\{path}\\{sub_name}"
                })
            except Exception:
                continue
    # Sort by name
    apps.sort(key=lambda x: (x['name'] or "").lower())
    return apps

def normalize_msi_command(cmd):
    """
    If uninstall string uses msiexec with /I (install) convert to /X (uninstall).
    This is heuristic but useful for many MSI entries.
    """
    if not cmd:
        return None
    low = cmd.lower()
    if "msiexec" in low:
        # replace " /i " or "/i" with "/x"
        # Use simple replacements; we won't attempt full safe parsing.
        cmd = cmd.replace("/I", "/X").replace("/i", "/X")
    return cmd

def parse_exec(cmd):
    """
    Try to split command string into (exe, args).
    Use shlex.split for basic handling of quoted paths.
    """
    if not cmd:
        return (None, None)
    try:
        parts = shlex.split(cmd, posix=False)
        exe = parts[0]
        args = " ".join(parts[1:]) if len(parts) > 1 else ""
        return exe, args
    except Exception:
        # fallback: naive
        if cmd.startswith('"'):
            end = cmd.find('"', 1)
            if end > 1:
                exe = cmd[1:end]
                args = cmd[end+1:].strip()
                return exe, args
        split = cmd.split(" ", 1)
        exe = split[0]
        args = split[1] if len(split) > 1 else ""
        return exe, args

def run_as_admin(exe, args):
    """
    Attempt to launch exe with elevated privileges using ShellExecuteW "runas".
    Returns handle/result from ShellExecute; does not capture output.
    """
    try:
        params = args or ""
        # ShellExecuteW returns >32 on success
        r = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        return r
    except Exception as e:
        return None

class UninstallerGUI:
    def __init__(self, root):
        self.root = root
        root.title("简易 Windows 卸载器")
        root.geometry("900x600")
        self.apps = []
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self):
        # Top frame: buttons
        top = Frame(self.root)
        top.pack(fill=X, padx=6, pady=6)

        self.refresh_btn = Button(top, text="刷新列表", command=self.refresh_list)
        self.refresh_btn.pack(side=LEFT, padx=4)

        self.details_btn = Button(top, text="查看详情", command=self.show_details)
        self.details_btn.pack(side=LEFT, padx=4)

        self.dryrun_btn = Button(top, text="模拟（Dry run）", command=lambda: self.uninstall(selected_only=True, dry_run=True))
        self.dryrun_btn.pack(side=LEFT, padx=4)

        self.uninstall_btn = Button(top, text="执行卸载", command=lambda: self.uninstall(selected_only=True, dry_run=False))
        self.uninstall_btn.pack(side=LEFT, padx=4)

        self.uninstall_all_btn = Button(top, text="卸载所选（含管理员尝试）", command=lambda: self.uninstall(selected_only=True, dry_run=False, try_elevate=True))
        self.uninstall_all_btn.pack(side=LEFT, padx=4)

        self.admin_label = Label(top, text=f"当前权限: {'管理员' if is_admin() else '普通用户'}")
        self.admin_label.pack(side=RIGHT, padx=8)

        # Middle: list of apps and details
        middle = PanedWindow(self.root, orient=HORIZONTAL)
        middle.pack(fill=BOTH, expand=True, padx=6, pady=6)

        left_frame = Frame(middle)
        right_frame = Frame(middle)
        middle.add(left_frame, width=420)
        middle.add(right_frame, width=480)

        # Search box
        search_frame = Frame(left_frame)
        search_frame.pack(fill=X, pady=4)
        Label(search_frame, text="搜索：").pack(side=LEFT)
        self.search_var = StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_list())
        Entry(search_frame, textvariable=self.search_var).pack(side=LEFT, fill=X, expand=True, padx=4)

        # Listbox
        self.app_list = Listbox(left_frame, selectmode=EXTENDED)
        self.app_list.pack(fill=BOTH, expand=True)
        self.app_list.bind("<Double-Button-1>", lambda e: self.show_details())

        # Right: details and log
        details_label = Label(right_frame, text="程序详情 / 卸载命令")
        details_label.pack(anchor=W)
        self.details_text = scrolledtext.ScrolledText(right_frame, height=12)
        self.details_text.pack(fill=X, pady=4)

        log_label = Label(right_frame, text="日志")
        log_label.pack(anchor=W)
        self.log_text = scrolledtext.ScrolledText(right_frame)
        self.log_text.pack(fill=BOTH, expand=True, pady=4)

    def log(self, msg):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(END, f"[{ts}] {msg}\n")
        self.log_text.see(END)

    def refresh_list(self):
        self.log("开始扫描已安装程序（读取注册表）...")
        self.apps = gather_installed_programs()
        self.populate_list()
        self.log(f"扫描完成：找到 {len(self.apps)} 个条目。")

    def populate_list(self):
        self.app_list.delete(0, END)
        for app in self.apps:
            display = app['name']
            if app.get('publisher'):
                display += f" — {app.get('publisher')}"
            if app.get('version'):
                display += f" ({app.get('version')})"
            self.app_list.insert(END, display)
        self.filter_list()

    def filter_list(self):
        q = self.search_var.get().lower().strip()
        self.app_list.delete(0, END)
        for app in self.apps:
            combined = " ".join(filter(None, [app.get('name',''), app.get('publisher',''), app.get('version','')])).lower()
            if q == "" or q in combined:
                display = app['name']
                if app.get('publisher'):
                    display += f" — {app.get('publisher')}"
                if app.get('version'):
                    display += f" ({app.get('version')})"
                self.app_list.insert(END, display)

    def get_selected_apps(self):
        sel = list(self.app_list.curselection())
        if not sel:
            messagebox.showinfo("提示", "请先选择要卸载的程序（单击选择，或按住 Ctrl/Shift 多选）。")
            return []
        # Need to map listbox indices back to apps considering current filter
        indices = []
        q = self.search_var.get().lower().strip()
        for i, app in enumerate(self.apps):
            combined = " ".join(filter(None, [app.get('name',''), app.get('publisher',''), app.get('version','')])).lower()
            if q == "" or q in combined:
                indices.append(i)
        selected_apps = [self.apps[indices[k]] for k in sel if k < len(indices)]
        return selected_apps

    def show_details(self):
        selected = self.get_selected_apps()
        if not selected:
            return
        # Show details for first selected
        app = selected[0]
        lines = []
        lines.append(f"名称: {app.get('name')}")
        lines.append(f"发布者: {app.get('publisher')}")
        lines.append(f"版本: {app.get('version')}")
        lines.append(f"安装目录: {app.get('install_location')}")
        lines.append(f"注册表键: {app.get('reg_key')}")
        lines.append("")
        lines.append("卸载命令（UninstallString）:")
        lines.append(str(app.get('uninstall') or "（无）"))
        lines.append("")
        lines.append("静默卸载（QuietUninstallString）:")
        lines.append(str(app.get('quiet_uninstall') or "（无）"))
        self.details_text.delete("1.0", END)
        self.details_text.insert(END, "\n".join(lines))

    def uninstall(self, selected_only=True, dry_run=False, try_elevate=False):
        apps = self.get_selected_apps()
        if not apps:
            return
        # Build list of commands
        commands = []
        for app in apps:
            cmd = app.get('quiet_uninstall') or app.get('uninstall')
            if not cmd:
                self.log(f"跳过 {app['name']}：没有可用的卸载命令。")
                continue
            cmd = normalize_msi_command(cmd)
            commands.append((app, cmd))
        if not commands:
            messagebox.showinfo("信息", "没有可执行的卸载命令。")
            return

        # Show summary and confirm
        summary = "将要执行以下操作：\n\n"
        for app, cmd in commands:
            summary += f"{app['name']}\n  {cmd}\n\n"
        summary += "是否继续？（这将立即运行卸载命令）"
        if dry_run:
            # just show and return
            messagebox.showinfo("模拟（Dry run）", summary)
            self.log("Dry run: 以下命令会被执行（未实际运行）:")
            for a, c in commands:
                self.log(f"DRY: {a['name']} -> {c}")
            return

        if not messagebox.askyesno("确认卸载", summary):
            self.log("用户取消卸载。")
            return

        # Execute each command in a thread to keep UI responsive
        t = threading.Thread(target=self._execute_commands, args=(commands, try_elevate))
        t.daemon = True
        t.start()

    def _execute_commands(self, commands, try_elevate):
        for app, cmd in commands:
            try:
                self.log(f"开始卸载: {app['name']}")
                exe, args = parse_exec(cmd)
                if not exe:
                    # fallback: run via shell
                    self.log(f"无法解析可执行文件，使用 shell 执行: {cmd}")
                    proc = subprocess.Popen(cmd, shell=True)
                    proc.wait()
                    self.log(f"{app['name']} 返回码：{proc.returncode}")
                    continue

                # If not admin and try_elevate requested, attempt runas
                if not is_admin():
                    self.log("当前不是管理员，某些卸载可能失败。")
                    # If try_elevate, attempt ShellExecute 'runas'
                    if try_elevate:
                        self.log(f"尝试以管理员方式运行: {exe} {args}")
                        r = run_as_admin(exe, args)
                        if r and int(r) > 32:
                            self.log(f"已以管理员方式启动卸载（ShellExecute 返回 {r}）。")
                            # We won't be able to capture its output; just continue.
                            continue
                        else:
                            self.log("尝试以管理员方式启动失败，改为普通模式执行。")

                # Execute directly and capture output
                self.log(f"执行命令: {exe} {args}")
                try:
                    # Use subprocess to capture output (may require admin)
                    proc = subprocess.Popen([exe] + shlex.split(args, posix=False), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                    out, err = proc.communicate()
                    out_text = out.decode(errors='ignore') if out else ""
                    err_text = err.decode(errors='ignore') if err else ""
                    self.log(f"{app['name']} 返回码：{proc.returncode}")
                    if out_text.strip():
                        self.log(f"stdout: {out_text.strip()[:1000]}")
                    if err_text.strip():
                        self.log(f"stderr: {err_text.strip()[:1000]}")
                except Exception as e:
                    # Some uninstallers require shell=True or different invocation
                    self.log(f"直接执行失败（尝试 shell=True）：{e}")
                    try:
                        proc = subprocess.Popen(cmd, shell=True)
                        proc.wait()
                        self.log(f"{app['name']}（shell） 返回码：{proc.returncode}")
                    except Exception as e2:
                        self.log(f"执行卸载命令失败：{e2}")
                        self.log(traceback.format_exc())
            except Exception as e:
                self.log(f"卸载 {app['name']} 时出错: {e}")
                self.log(traceback.format_exc())
        self.log("全部卸载任务完成。若卸载需要管理员权限，请以管理员身份重新运行本程序。")
        # Refresh list after short delay
        time.sleep(1)
        self.refresh_list()

def main():
    if sys.platform != "win32":
        messagebox.showerror("错误", "本脚本只能在 Windows 上运行。")
        return
    root = Tk()
    app = UninstallerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
