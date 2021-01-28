git add events.json config.json
powershell.exe -Command "& { git -c commit.gpgsign=false commit -m \"$(date)\" }"
