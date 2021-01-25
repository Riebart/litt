' WScript host VBScript file to gather input and invoke the tt command
' without showing a console dialog on the screen.

Dim ttPyPath
Dim ttCommand
Dim ttArgs

ttPyPath = WScript.Arguments(0)
ttCommand = WScript.Arguments(1)

ttArgs = InputBox("Enter task description")
If ttArgs <> "" Then
    If InStr(ttArgs, "--") = 0 Then
        ttArgs = """" & ttArgs & """"
    End If
End If

' MsgBox("python3.exe """  & ttPyPath & """ """ & ttCommand & """ " & ttArgs)

Set WshShell = WScript.CreateObject("WScript.Shell")
WshShell.Run "python3.exe """  & ttPyPath & """ """ & ttCommand & """ " & ttArgs, 0, false
