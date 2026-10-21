Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "C:\Projetos\agent-core-main\IniciadorDaemon.bat" & Chr(34), 0
Set WshShell = Nothing
