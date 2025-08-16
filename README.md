# unistall
Windows Uninstaller GUI Tool
Overview
The Windows Uninstaller GUI Tool (uninstall.py) is a lightweight Python script that provides a graphical interface for uninstalling programs on Windows systems. Using only built-in Python libraries (winreg, tkinter, ctypes, subprocess, shlex, threading, time, traceback), it scans the Windows registry to list installed programs, displays their details, and executes uninstall commands. Designed for simplicity and reliability, it supports both standard and quiet uninstalls, with options for dry runs and administrator elevation attempts. The UI and messages are in Chinese, while code comments are in English for clarity.
This tool is ideal for users, administrators, and IT professionals who need an intuitive way to manage software uninstallation without external dependencies, offering a balance of usability and robust error handling.
Features
Program Listing

Registry Scanning: Queries HKEY_LOCAL_MACHINE and HKEY_CURRENT_USER registry paths (SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall, SOFTWARE\WOW6432Node\...) to retrieve installed programs.
Program Details: Collects DisplayName, UninstallString, QuietUninstallString, Publisher, Version, InstallLocation, and registry key path.
Deduplication: Ensures unique entries by combining display name and uninstall string to avoid duplicates.
Sorting: Lists programs alphabetically by name for easy navigation.

Uninstallation

Standard Uninstall: Executes UninstallString from the registry to launch the program's uninstaller.
Quiet Uninstall: Prioritizes QuietUninstallString for silent uninstalls when available.
MSI Handling: Converts MSI /I (install) commands to /X (uninstall) for compatibility.
Command Parsing: Uses shlex.split to separate executable and arguments, with fallback for quoted paths.
Administrator Elevation: Attempts to run uninstall commands with elevated privileges using ShellExecuteW with runas when requested.
Threaded Execution: Runs uninstall commands in a separate thread to keep the GUI responsive.

User Interface

Tkinter GUI: Provides a clean interface with a listbox for program selection, search bar, and buttons for actions.
Search Functionality: Filters programs by name, publisher, or version in real-time.
Details Pane: Displays selected program details (name, publisher, version, install location, uninstall commands).
Log Pane: Shows timestamped logs of actions, errors, and command outputs in a scrollable text area.
Buttons:
Refresh List: Rescans registry to update program list.
Show Details: Displays selected program’s registry data and uninstall commands.
Dry Run: Simulates uninstallation by showing commands without executing them.
Uninstall: Executes uninstall commands for selected programs.
Uninstall with Admin: Attempts uninstallation with elevated privileges.


Multi-Selection: Supports selecting multiple programs using Ctrl/Shift for batch uninstalls.

Error Handling

Registry Errors: Gracefully handles missing keys, permissions issues, or invalid values.
Command Execution: Captures and logs subprocess errors, including stdout/stderr, with fallback to shell execution for complex commands.
Privilege Checks: Detects admin status using ctypes.windll.shell32.IsUserAnAdmin and logs warnings if elevation is needed.
Thread Safety: Uses daemon threads to prevent UI freezes during uninstallation.
Exception Logging: Logs detailed tracebacks for debugging.

Technical Details
Core Components

Registry Access: Uses winreg to enumerate uninstall keys and extract program metadata.
Command Execution:
subprocess.Popen for direct execution with output capture.
ShellExecuteW via ctypes for elevated execution.
shlex.split for parsing uninstall commands, with naive fallback for robustness.


GUI Framework: Built with tkinter for cross-version compatibility, using Listbox, ScrolledText, PanedWindow, and Button widgets.
Threading: Employs threading.Thread for non-blocking uninstall operations.
Dependencies: None beyond Python standard libraries, ensuring portability.

Design Principles

Lightweight: No external package dependencies, compatible with Python 3.6+.
User-Friendly: Chinese UI with clear prompts and confirmation dialogs.
Robust: Comprehensive error handling for registry access, command execution, and GUI interactions.
Flexible: Supports both interactive and batch uninstalls with dry-run simulation.

Requirements

Python: Version 3.6 or higher (uses subprocess, winreg, tkinter, ctypes).
Operating System: Windows (tested on Windows 10/11, compatible with older versions supporting Python).
Permissions: Admin privileges required for some uninstallers; script detects and attempts elevation if requested.
No External Dependencies: Uses only Python standard libraries.

Installation
Prerequisites

Verify Python:python --version

Install Python if needed from python.org.
Admin Privileges: Some uninstalls require admin rights; run the script as administrator for full functionality:python uninstall.py



Setup

Download the Script:curl -O <script_url>/uninstall.py

Or clone the repository:git clone <repository_url>


Run the Script:python uninstall.py

Or run as administrator:runas /user:Administrator "python uninstall.py"



Usage
Basic Execution
Run the script to launch the GUI:
python uninstall.py


Select Programs: Click or use Ctrl/Shift to select multiple programs in the listbox.
Search: Type in the search bar to filter programs by name, publisher, or version.
View Details: Click "查看详情" or double-click a program to see its registry data.
Dry Run: Click "模拟（Dry run）" to preview uninstall commands.
Uninstall: Click "执行卸载" for standard uninstall or "卸载所选（含管理员尝试）" to attempt elevated uninstall.
Logs: View real-time logs in the bottom pane for command outputs and errors.

Example Workflow

Launch the script; the GUI shows all installed programs.
Search for "Python" to filter Python-related entries.
Select "Python 3.9.5" and click "查看详情" to see its uninstall command (e.g., msiexec /X{...}).
Click "模拟（Dry run）" to verify the command.
Click "执行卸载" to uninstall, or "卸载所选（含管理员尝试）" if admin rights are needed.
Monitor logs for success or errors (e.g., "返回码: 0" for success).

Example Log Output
[2025-08-16 05:53:01] 开始扫描已安装程序（读取注册表）...
[2025-08-16 05:53:02] 扫描完成：找到 45 个条目。
[2025-08-16 05:53:10] 开始卸载: Python 3.9.5
[2025-08-16 05:53:10] 执行命令: C:\Windows\System32\msiexec.exe /X{1234-5678}
[2025-08-16 05:53:15] Python 3.9.5 返回码：0
[2025-08-16 05:53:16] 全部卸载任务完成。

Troubleshooting
Common Issues

No Programs Listed:
Ensure registry paths exist (HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall).
Run as admin to access all registry keys:runas /user:Administrator "python uninstall.py"




Uninstall Fails:
Check logs for error codes or messages.
Some programs require admin rights; use "卸载所选（含管理员尝试）".
Verify the uninstall command in the details pane.


GUI Unresponsive:
Ensure no modal dialogs (e.g., UAC prompts) are hidden.
Check for exceptions in the log pane.


Invalid Command Parsing:
Complex uninstall strings may fail; logs show fallback to shell execution.



Debugging Tips

Check the log pane for detailed errors and tracebacks.
Manually test uninstall commands in Command Prompt:msiexec /X{product-code}


Enable verbose logging by modifying log() to write to a file:with open("uninstall.log", "a") as f:
    f.write(f"[{ts}] {msg}\n")



Future Enhancements

Batch Quiet Uninstall: Automatically use QuietUninstallString for all selected programs.
Progress Indicators: Show real-time uninstall progress for each program.
Registry Cleanup: Remove orphaned registry keys after uninstall.
Export/Import: Save program list to JSON/CSV for analysis.
Custom Filters: Add advanced search options (e.g., by install date).

Contributing

Fork the repository.
Create a feature branch:git checkout -b feature/new-feature


Commit changes:git commit -m "Add new feature"


Push to the branch:git push origin feature/new-feature


Open a pull request with a detailed description.

License
MIT License. See the LICENSE file for details.
Acknowledgments

Built with Python standard libraries for maximum compatibility.
Inspired by the need for a simple, dependency-free Windows uninstaller.
UI in Chinese for accessibility, with English comments for maintainability.

