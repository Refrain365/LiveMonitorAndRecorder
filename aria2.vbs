Set fso = CreateObject("Scripting.FileSystemObject")
Set oShell = CreateObject("Wscript.Shell")

' 获取当前脚本所在目录
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)

' 构建aria2命令，设置工作目录为脚本所在目录
Dim strArgs
strArgs = "aria2c --enable-rpc --rpc-listen-all --dir=" & Chr(34) & scriptPath & Chr(34)

' 运行aria2，隐藏窗口
oShell.Run strArgs, 0, false