# Example script to show how to collect input via VisualBasic modules
# and a text input box to automate some tt actions via macros.

param
(
    [Parameter(Mandatory=$true)]
    [String]$ttLocation
)

$passphrase=$(powershell -Command '[System.Reflection.Assembly]::LoadWithPartialName(\"Microsoft.VisualBasic\") | Out-Null; [Microsoft.VisualBasic.Interaction]::InputBox(\"Enter the description or alias:\", \"Description or alias\", \"\")');

if ($passphease -eq "")
{
    python3.exe "$ttLocation" sw
}
else
{
    python3.exe "$ttLocation" sw "$passphrase"
}
