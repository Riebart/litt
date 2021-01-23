// This wrapper can be run by wscript to wrap the powershell script so that it does not show a window when invoked.

var littPath = WScript.arguments(0)

var wshShell = new ActiveXObject("WScript.Shell");

wshShell.Run(
    '%SystemRoot%\\system32\\WindowsPowerShell\\v1.0\\powershell.exe -File "' +
    littPath + '\\contrib\\scripts\\macro_tt_sw.ps1" "' +
    littPath + '\\tt"',
    0, false);
