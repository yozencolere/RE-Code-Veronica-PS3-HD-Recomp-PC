# Lance la copie de test et va jusqu'a l'inventaire (input_comfort=1 dans l'ini de test).
param([hashtable]$Env = @{})
$d = 'C:\Users\julia\AppData\Local\Temp\claude\9519414f725d5b3e\2c32d903-e278-458a-815e-a4822472ed56\scratchpad'
$pil = "$d\pilote.ps1"
Get-Process CodeVeronicaPort* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like 'E:\Recomp\Test_CV\*' } | Stop-Process -Force
Start-Sleep 1
foreach ($k in $Env.Keys) { Set-Item "env:$k" $Env[$k] }
Start-Process 'E:\Recomp\Test_CV\bin\CodeVeronicaPort_US.exe' -WorkingDirectory 'E:\Recomp\Test_CV\bin' | Out-Null
Start-Sleep 30
& $pil -Touches start, start -Tenue 250 -Pause 2500 | Out-Null
& $pil -Touches croix -Tenue 250 -Pause 7000 | Out-Null    # liste des sauvegardes
& $pil -Touches croix -Tenue 250 -Pause 1500 | Out-Null    # Charger ?
& $pil -Touches croix -Tenue 250 -Pause 12000 | Out-Null   # Oui -> Chargement termine
& $pil -Touches croix -Tenue 250 -Pause 12000 | Out-Null   # OK -> en jeu
& $pil -Touches start -Tenue 250 -Pause 3000 | Out-Null    # inventaire
& $pil -Png "$d\inv_ecran.png"
