# Code Veronica recomp - installation des outils + generation + compilation (version US)
# Fichier volontairement en ASCII pur (PowerShell 5.1).
# Relancable sans risque : chaque etape deja faite est sautee.

$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'

$Build = $PSScriptRoot                                   # ...\Code_Veronica_PC\_build
$Root  = Split-Path -Parent $Build                       # ...\Code_Veronica_PC
$Tools = Join-Path (Split-Path -Parent $Root) 'Outils'   # ...\Recomp\Outils
$Game  = 'E:\CodeVeronica-PC-v1.1.5'
$Elf   = Join-Path $Game 'bin\eboot_cache\NPUB30467\EBOOT.elf'
$ElfSha1 = '93d060e5019d877df39cd091c28efff920b98e49'
$Logs  = Join-Path $Build 'logs'
$Dl    = Join-Path $Tools '_telechargements'
$Result = Join-Path $Logs 'RESULTAT.txt'

$VsDir   = Join-Path $Tools 'VS2022BuildTools'
$LlvmDir = Join-Path $Tools 'LLVM'
$CMakeDir = Join-Path $Tools 'CMake'
$NinjaDir = Join-Path $Tools 'Ninja'
$PyDir   = Join-Path $Tools 'Python312'
$VenvDir = Join-Path $Tools 'PyEnv'

$UrlVs     = 'https://aka.ms/vs/17/release/vs_BuildTools.exe'
$UrlLlvm   = 'https://github.com/llvm/llvm-project/releases/download/llvmorg-22.1.8/LLVM-22.1.8-win64.exe'
$UrlCMake  = 'https://github.com/Kitware/CMake/releases/download/v3.31.8/cmake-3.31.8-windows-x86_64.zip'
$UrlNinja  = 'https://github.com/ninja-build/ninja/releases/download/v1.12.1/ninja-win.zip'
$UrlPython = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe'

New-Item -ItemType Directory -Force -Path $Logs, $Tools, $Dl | Out-Null
$MainLog = Join-Path $Logs 'principal.log'
$script:Step = 'demarrage'

function Say([string]$Text) {
    $line = ('[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $Text)
    Write-Host $line
    Add-Content -Path $MainLog -Value $line -Encoding ASCII
}

function Finish([string]$Status, [string]$Detail) {
    $lines = @(
        ('STATUT : ' + $Status),
        ('ETAPE  : ' + $script:Step),
        ('DETAIL : ' + $Detail),
        ('DATE   : ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    )
    Set-Content -Path $Result -Value $lines -Encoding ASCII
    Say ('==== ' + $Status + ' ==== etape: ' + $script:Step + ' ' + $Detail)
    Write-Host ''
    Write-Host 'Tu peux fermer cette fenetre et prevenir Claude.'
    Read-Host 'Appuie sur Entree pour fermer'
    if ($Status -eq 'OK') { exit 0 } else { exit 1 }
}

function Invoke-Logged {
    param([string]$Name, [string]$Exe, [string[]]$ArgList, [string]$WorkDir, [int[]]$OkCodes = @(0))
    $log = Join-Path $Logs ($Name + '.log')
    $err = Join-Path $Logs ($Name + '.err.log')
    Say ('--> ' + $Name + ' (journal: ' + $log + ')')
    $quoted = @()
    foreach ($a in $ArgList) {
        if (($a -match '\s') -and ($a -notmatch '^".*"$')) { $quoted += ('"' + $a + '"') } else { $quoted += $a }
    }
    $p = Start-Process -FilePath $Exe -ArgumentList $quoted -WorkingDirectory $WorkDir -NoNewWindow -Wait -PassThru `
            -RedirectStandardOutput $log -RedirectStandardError $err
    $code = $p.ExitCode
    Say ('    code de sortie: ' + $code)
    if ($OkCodes -notcontains $code) {
        throw ($Name + ' a echoue (code ' + $code + '). Voir ' + $log + ' et ' + $err)
    }
}

function Download([string]$Url, [string]$Dest) {
    if ((Test-Path $Dest) -and ((Get-Item $Dest).Length -gt 100000)) { Say ('deja telecharge: ' + $Dest); return }
    Say ('telechargement: ' + $Url)
    $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
    if (Test-Path $curl) {
        & $curl -L --fail --silent --show-error --retry 3 -o $Dest $Url
        if ($LASTEXITCODE -ne 0) { throw ('telechargement echoue (curl code ' + $LASTEXITCODE + '): ' + $Url) }
    } else {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $Url -OutFile $Dest -UseBasicParsing
    }
    if (-not (Test-Path $Dest)) { throw ('fichier absent apres telechargement: ' + $Dest) }
    Say ('    taille: ' + (Get-Item $Dest).Length + ' octets')
}

function Expand-Zip([string]$Zip, [string]$Dest) {
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    $tar = Join-Path $env:SystemRoot 'System32\tar.exe'
    if (Test-Path $tar) {
        & $tar -xf $Zip -C $Dest
        if ($LASTEXITCODE -ne 0) { throw ('extraction echouee (tar code ' + $LASTEXITCODE + '): ' + $Zip) }
    } else {
        Expand-Archive -Path $Zip -DestinationPath $Dest -Force
    }
}

try {
    Say '=================== nouveau lancement ==================='
    Say ('racine sources : ' + $Root)
    Say ('outils         : ' + $Tools)

    # ------------------------------------------------------------ etat machine
    $script:Step = 'etat de la machine'
    $os  = Get-CimInstance Win32_OperatingSystem
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $ramGb = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
    Say ('Windows: ' + $os.Caption + ' ' + $os.Version + ' | RAM: ' + $ramGb + ' Go | CPU: ' + $cpu.Name + ' (' + $cpu.NumberOfLogicalProcessors + ' threads)')
    $freeC = [math]::Round((Get-PSDrive -Name C).Free / 1GB, 1)
    $toolsDrive = (Split-Path -Qualifier $Tools).TrimEnd(':')
    $freeT = [math]::Round((Get-PSDrive -Name $toolsDrive).Free / 1GB, 1)
    Say ('espace libre C: ' + $freeC + ' Go | ' + $toolsDrive + ': ' + $freeT + ' Go')
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (Test-Path $vswhere) {
        $found = & $vswhere -all -prerelease -products * -format value -property installationPath
        foreach ($f in $found) { Say ('Visual Studio deja present: ' + $f) }
    } else { Say 'vswhere absent (aucun Visual Studio recent detecte)' }

    $vcvars = Join-Path $VsDir 'VC\Auxiliary\Build\vcvars64.bat'
    if (-not (Test-Path $vcvars)) {
        if ($freeC -lt 6) { throw ('pas assez de place sur C: (' + $freeC + ' Go libres). Visual Studio Build Tools met le SDK Windows sur C: meme installe ailleurs ; il faut au moins 6 Go libres.') }
        if ($freeT -lt 25) { throw ('pas assez de place sur ' + $toolsDrive + ': (' + $freeT + ' Go libres, 25 Go demandes).') }
    }

    # ------------------------------------------------------------ sources
    $script:Step = 'extraction des sources'
    if (-not (Test-Path (Join-Path $Root 'projects\code_veronica\CMakeLists.txt'))) {
        $zip = Join-Path $Build 'sources_v1.5.3.zip'
        if (-not (Test-Path $zip)) { throw ('archive des sources absente: ' + $zip) }
        Say 'extraction des sources v1.5.3'
        Expand-Zip $zip $Root
    } else { Say 'sources deja en place' }
    if (-not (Test-Path (Join-Path $Root 'tools\cv_make_spu_us.py'))) { throw 'tools\cv_make_spu_us.py absent apres extraction' }

    # ------------------------------------------------------------ executable du jeu
    $script:Step = 'verification de EBOOT.elf (US)'
    if (-not (Test-Path $Elf)) { throw ('EBOOT.elf introuvable: ' + $Elf + ' (lance le jeu une fois avec la version US pour le recreer)') }
    $sha = (Get-FileHash -Path $Elf -Algorithm SHA1).Hash.ToLower()
    if ($sha -ne $ElfSha1) { throw ('EBOOT.elf inattendu (SHA-1 ' + $sha + ')') }
    Say 'EBOOT.elf US conforme'

    # ------------------------------------------------------------ Visual Studio Build Tools
    $script:Step = 'installation Visual Studio Build Tools 2022'
    if (-not (Test-Path $vcvars)) {
        $exe = Join-Path $Dl 'vs_BuildTools.exe'
        Download $UrlVs $exe
        Say 'installation de Visual Studio Build Tools (10 a 30 minutes, une fenetre de progression Microsoft apparait)'
        Invoke-Logged 'install_vs_buildtools' $exe @('--installPath', $VsDir, '--add', 'Microsoft.VisualStudio.Workload.VCTools', '--includeRecommended', '--passive', '--wait', '--norestart', '--nocache') $Dl @(0, 3010)
        if (-not (Test-Path $vcvars)) { throw ('vcvars64.bat absent apres installation: ' + $vcvars) }
    } else { Say 'Visual Studio Build Tools deja installe' }

    # ------------------------------------------------------------ LLVM
    $script:Step = 'installation LLVM'
    $clang = Join-Path $LlvmDir 'bin\clang-cl.exe'
    if (-not (Test-Path $clang)) {
        $exe = Join-Path $Dl 'LLVM-22.1.8-win64.exe'
        Download $UrlLlvm $exe
        # NSIS : /D= doit etre le dernier argument, sans guillemets.
        Invoke-Logged 'install_llvm' $exe @('/S', ('/D=' + $LlvmDir)) $Dl
        if (-not (Test-Path $clang)) { throw ('clang-cl.exe absent apres installation: ' + $clang) }
    } else { Say 'LLVM deja installe' }

    # ------------------------------------------------------------ CMake
    $script:Step = 'installation CMake'
    $cmake = Join-Path $CMakeDir 'bin\cmake.exe'
    if (-not (Test-Path $cmake)) {
        $zip = Join-Path $Dl 'cmake-3.31.8-windows-x86_64.zip'
        Download $UrlCMake $zip
        Expand-Zip $zip $Tools
        $unpacked = Join-Path $Tools 'cmake-3.31.8-windows-x86_64'
        if (-not (Test-Path $unpacked)) { throw ('dossier CMake attendu absent: ' + $unpacked) }
        Rename-Item -Path $unpacked -NewName 'CMake'
        if (-not (Test-Path $cmake)) { throw ('cmake.exe absent: ' + $cmake) }
    } else { Say 'CMake deja installe' }

    # ------------------------------------------------------------ Ninja
    $script:Step = 'installation Ninja'
    $ninja = Join-Path $NinjaDir 'ninja.exe'
    if (-not (Test-Path $ninja)) {
        $zip = Join-Path $Dl 'ninja-win.zip'
        Download $UrlNinja $zip
        Expand-Zip $zip $NinjaDir
        if (-not (Test-Path $ninja)) { throw ('ninja.exe absent: ' + $ninja) }
    } else { Say 'Ninja deja installe' }

    # ------------------------------------------------------------ Python
    $script:Step = 'installation Python 3.12'
    $venvPy = Join-Path $VenvDir 'Scripts\python.exe'
    if (-not (Test-Path $venvPy)) {
        $basePy = Join-Path $PyDir 'python.exe'
        if (-not (Test-Path $basePy)) {
            $exe = Join-Path $Dl 'python-3.12.10-amd64.exe'
            Download $UrlPython $exe
            Invoke-Logged 'install_python' $exe @('/quiet', 'InstallAllUsers=0', ('TargetDir=' + $PyDir), 'PrependPath=0', 'Include_launcher=0', 'Include_test=0', 'Include_doc=0', 'Include_tcltk=0', 'Shortcuts=0', 'AssociateFiles=0') $Dl @(0, 3010)
        }
        if (-not (Test-Path $basePy)) {
            # Python 3.12.10 deja installe ailleurs : l'installeur ne le duplique pas. On le reutilise.
            Say 'python.exe absent du dossier cible ; recherche d''un Python 3.12 existant'
            $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
            if ($pyLauncher) {
                $existing = & $pyLauncher.Source -3.12 -c 'import sys;print(sys.executable)'
                if (($LASTEXITCODE -eq 0) -and $existing -and (Test-Path $existing)) { $basePy = $existing }
            }
        }
        if (-not (Test-Path $basePy)) { throw 'aucun Python 3.12 utilisable (voir install_python.log)' }
        Say ('Python de base: ' + $basePy)
        Invoke-Logged 'python_venv' $basePy @('-m', 'venv', $VenvDir) $Tools
        if (-not (Test-Path $venvPy)) { throw ('environnement Python absent: ' + $venvPy) }
    } else { Say 'environnement Python deja cree' }

    $script:Step = 'paquets Python'
    $stamp = Join-Path $VenvDir 'paquets_ok.txt'
    if (-not (Test-Path $stamp)) {
        Invoke-Logged 'pip_install' $venvPy @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', (Join-Path $Root 'requirements.txt')) $Root
        Set-Content -Path $stamp -Value 'ok' -Encoding ASCII
    } else { Say 'paquets Python deja installes' }

    # ------------------------------------------------------------ generation du code du jeu
    $script:Step = 'generation du code PPU (US)'
    $diag = Join-Path $Root 'projects\code_veronica\codex_diag_us'
    $recomp = Join-Path $Root 'src\recomp_us'
    if (-not (Test-Path (Join-Path $recomp 'ppu_recomp.h'))) {
        Invoke-Logged 'gen_ppu_loader' $venvPy @('tools\ppu_loader.py', $Elf, '--output', $diag) $Root
        Invoke-Logged 'gen_ppu_lifter' $venvPy @('tools\ppu_lifter.py', $Elf, '--functions', (Join-Path $diag 'EBOOT.functions.json'), '--hle-stubs', (Join-Path $diag 'EBOOT.imports.json'), '--patches', 'projects\code_veronica\patches.json', '--title-id', 'NPUB30467', '-j', '6', '-o', $recomp) $Root
        if (-not (Test-Path (Join-Path $recomp 'ppu_recomp.h'))) { throw 'ppu_recomp.h absent apres generation' }
    } else { Say 'code PPU deja genere' }

    $script:Step = 'generation du code SPU'
    $spu = Join-Path $Root 'projects\code_veronica\spu'
    if (-not (Test-Path (Join-Path $spu 'spu_workloads.c'))) {
        Invoke-Logged 'gen_spu' $venvPy @('tools\cv_make_spu_us.py', $Elf, '--out', $spu) $Root
        if (-not (Test-Path (Join-Path $spu 'spu_workloads.c'))) { throw 'spu_workloads.c absent apres generation' }
    } else { Say 'code SPU deja genere' }

    # ------------------------------------------------------------ compilation
    $script:Step = 'compilation (version US)'
    $jobs = 6
    if ($ramGb -lt 24) { $jobs = 3 }
    $env:CV_SRC    = $Root
    $env:CV_TOOLS  = $Tools
    $env:CV_PYTHON = $venvPy
    $env:CV_JOBS   = [string]$jobs
    Say ('compilation avec ' + $jobs + ' taches en parallele (longue : compter 20 a 60 minutes la premiere fois)')
    Invoke-Logged 'compilation_us' (Join-Path $env:SystemRoot 'System32\cmd.exe') @('/d', '/c', (Join-Path $Build 'build_us.cmd')) $Root

    $out = Join-Path $Root 'projects\code_veronica\build-release\bin\CodeVeronicaPort_US.exe'
    if (-not (Test-Path $out)) { throw ('executable absent apres compilation: ' + $out) }
    $script:Step = 'termine'
    Finish 'OK' ('executable: ' + $out + ' (' + (Get-Item $out).Length + ' octets)')
}
catch {
    Say ('ERREUR: ' + $_.Exception.Message)
    Finish 'ECHEC' $_.Exception.Message
}
