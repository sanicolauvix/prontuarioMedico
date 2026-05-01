# Prontuario Medico - build_prontuario.ps1 v3
# UTF-8 BOM + CRLF -- NUNCA usar travessao Unicode em comentarios
#
# Baseado em build_prestanista.ps1 v40 -- alinhado em 2026-05-01
#
# Diferencas vs Prestanista:
#   - --source-packages inclui pdfplumber (extensoes C para ARM64)
#   - Fase-NomeApp: seta app_name = "Prontuario Medico" no strings.xml
#   - pastasMover: doc, temp, dados
#   - Logcat filtra: PRONTUARIO, KOIOS
#   - pyproject.toml removido em Fase-FletBuild (evita package com.koios.*)
#   - Modo 5: so flutter build (~2 min) para quando flet build OK e flutter falhou
#
# USO:
#   .\build_prontuario.ps1         -- menu interativo
#   .\build_prontuario.ps1 -modo 1 -- completo        (~20 min)
#   .\build_prontuario.ps1 -modo 2 -- so .py mudaram  (~5 min)
#   .\build_prontuario.ps1 -modo 3 -- assets/yaml     (~12 min)
#   .\build_prontuario.ps1 -modo 4 -- so instalar     (<1 min)
#   .\build_prontuario.ps1 -modo 5 -- so flutter build (~2 min)

param(
    [ValidateSet("1","2","3","4","5")]
    [string]$modo = ""
)

$ErrorActionPreference = "Stop"

# ==============================================================================
# CONFIGURACOES
# ==============================================================================
$projeto    = "C:\pessoal\python\prontuario"
$tempDir    = "C:\pessoal\python\_temp_build_exclusions_prontuario"

# Deteccao do Flutter 3.29.2 -- CRITICO: versao hardcoded no Flet 0.28.2
# NUNCA usar o flutter do PATH sem verificar a versao -- pode ser outra versao
$flutter = $null

$tentativa = "C:\Users\$env:USERNAME\flutter\3.29.2\bin\flutter.bat"
if (Test-Path $tentativa) { $flutter = $tentativa }

if (-not $flutter) {
    $tentativa = "C:\Users\$env:USERNAME\flutter\3.29.2\bin\flutter.exe"
    if (Test-Path $tentativa) { $flutter = $tentativa }
}

if (-not $flutter) {
    $encontrado = Get-ChildItem "C:\Users" -Directory -ErrorAction SilentlyContinue |
        ForEach-Object {
            $bat = "$($_.FullName)\flutter\3.29.2\bin\flutter.bat"
            $exe = "$($_.FullName)\flutter\3.29.2\bin\flutter.exe"
            if (Test-Path $bat) { $bat } elseif (Test-Path $exe) { $exe }
        } |
        Where-Object { $_ } |
        Select-Object -First 1
    if ($encontrado) { $flutter = $encontrado }
}

if (-not $flutter) {
    $noPath = Get-Command flutter -ErrorAction SilentlyContinue
    if ($noPath -and $noPath.Source -like "*3.29.2*") { $flutter = $noPath.Source }
}

if (-not $flutter) {
    $encontrado = Get-ChildItem "C:\" -Recurse -Filter "flutter.bat" `
                    -ErrorAction SilentlyContinue |
                  Where-Object { $_.FullName -like "*3.29.2*" } |
                  Select-Object -First 1
    if ($encontrado) { $flutter = $encontrado.FullName }
}

if (-not $flutter) {
    Write-Host "[ERRO] Flutter 3.29.2 nao encontrado." -ForegroundColor Red
    Write-Host "       Verifique se o Flutter esta instalado em C:\Users\$env:USERNAME\flutter\3.29.2" -ForegroundColor Yellow
    exit 1
}

Write-Host "  Flutter: $flutter" -ForegroundColor DarkGray
$adb    = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$pubPkg = "$env:LOCALAPPDATA\Pub\Cache\hosted\pub.dev\webview_flutter_android-4.10.13"

$gradlePadrao = "$projeto\build\flutter\android\app\build.gradle"
$appzipPadrao = "$projeto\build\flutter\app\app.zip"
$apkOrigemPad = "$projeto\build\flutter\build\app\outputs\flutter-apk\app-release.apk"
$apkDestino   = "$projeto\build\apk\Prontuario.apk"

$pastasMover          = @("doc", "temp", "dados")
$script:pastasMovidas = @()

$logDir         = "$projeto\logs"
$script:logFile = $null

# ==============================================================================
# HELPERS: LOG
# ==============================================================================
function Log([string]$msg, [string]$cor = "White") {
    $ts    = Get-Date -Format "HH:mm:ss"
    $linha = "[$ts] $msg"
    Write-Host $linha -ForegroundColor $cor
    if ($script:logFile) {
        $dir = Split-Path $script:logFile
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
        try {
            Add-Content -Path $script:logFile -Value $linha -Encoding UTF8 -ErrorAction Stop
        } catch {
            # log temporariamente bloqueado (VSCode/antivirus) -- ignora, nao falha o build
        }
    }
}
function LogOk([string]$m)    { Log "  OK  $m" "Green"    }
function LogAviso([string]$m) { Log "  AVISO  $m" "Yellow" }
function LogErro([string]$m)  { Log "  ERRO  $m" "Red"     }
function LogSec([string]$m)   { Log "       $m" "DarkGray" }

function Iniciar-Log([string]$nome) {
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
    $script:logFile = "$logDir\build_${nome}_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    "" | Out-File -FilePath $script:logFile -Encoding UTF8
    Log "=== BUILD $nome | $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" "Cyan"
}

# ==============================================================================
# HELPERS: BUSCA DE CAMINHOS
# ==============================================================================
function Buscar-Gradle {
    if (Test-Path $gradlePadrao) { return $gradlePadrao }
    $encontrado = Get-ChildItem -Path "$projeto\build" -Recurse `
                    -Filter "build.gradle" -ErrorAction SilentlyContinue |
                  Where-Object { $_.FullName -like "*\app\build.gradle" } |
                  Select-Object -First 1
    if ($encontrado) { return $encontrado.FullName }
    return $null
}

function Buscar-AppZip {
    if (Test-Path $appzipPadrao) { return $appzipPadrao }
    $encontrado = Get-ChildItem -Path "$projeto\build" -Recurse `
                    -Filter "app.zip" -ErrorAction SilentlyContinue |
                  Select-Object -First 1
    if ($encontrado) { return $encontrado.FullName }
    return $null
}

function Buscar-ApkOrigem {
    if (Test-Path $apkOrigemPad) { return $apkOrigemPad }
    $encontrado = Get-ChildItem -Path "$projeto\build" -Recurse `
                    -Filter "app-release.apk" -ErrorAction SilentlyContinue |
                  Select-Object -First 1
    if ($encontrado) { return $encontrado.FullName }
    return $null
}

# ==============================================================================
# FASES REUTILIZAVEIS
# ==============================================================================

function Fase-VerificarBuildAnterior {
    Log "--- Verificando build anterior ---"
    $g = Buscar-Gradle
    if (-not $g) {
        throw "Build anterior nao encontrado. Execute o Modo 1 primeiro.`nCaminho esperado: $gradlePadrao"
    }
    $z = Buscar-AppZip
    if (-not $z) {
        throw "app.zip nao encontrado. Execute o Modo 1 primeiro.`nCaminho esperado: $appzipPadrao"
    }
    LogOk "gradle : $g"
    LogOk "app.zip: $z"
}

function Fase-CorrigirPubspec {
    Log "--- Corrigindo cache webview_flutter_android ---"
    if (Test-Path "$pubPkg\pubspec.yaml") {
        (Get-Content "$pubPkg\pubspec.yaml") `
            -replace 'sdk: \^3\.9\.0','sdk: ^3.7.0' |
            Set-Content "$pubPkg\pubspec.yaml"
        LogOk "sdk: ^3.7.0"
    } else {
        LogAviso "webview_flutter_android nao encontrado no cache -- ignorando"
    }
}

function Fase-MoverPastas {
    Log "--- Movendo pastas pesadas ---"
    if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir | Out-Null }
    foreach ($pasta in $pastasMover) {
        $orig = "$projeto\$pasta"
        $dest = "$tempDir\$pasta"
        if (Test-Path $orig) {
            if (Test-Path $dest) { Remove-Item -Path $dest -Recurse -Force }
            Move-Item -Path $orig -Destination $dest -Force
            $script:pastasMovidas += $pasta
            LogSec "movida: $pasta"
        }
    }
    if ($script:pastasMovidas.Count -gt 0) {
        LogOk "movidas: $($script:pastasMovidas -join ', ')"
    } else {
        LogOk "nenhuma pasta para mover"
    }
}

function Fase-RestaurarPastas {
    if ($script:pastasMovidas.Count -eq 0) { return }
    Log "--- Restaurando pastas ---"
    Set-Location $projeto
    foreach ($pasta in $script:pastasMovidas) {
        $orig = "$tempDir\$pasta"
        $dest = "$projeto\$pasta"
        if (Test-Path $orig) {
            Move-Item -Path $orig -Destination $dest -Force
            LogSec "restaurada: $pasta"
        }
    }
    LogOk "pastas restauradas"
}

function Fase-LimparPycache {
    Log "--- Removendo __pycache__ do projeto fonte ---"
    $n = 0
    Get-ChildItem -Path $projeto -Recurse -Filter "__pycache__" -Directory |
        Where-Object { $_.FullName -notlike "*\build\*" } |
        ForEach-Object {
            Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            $n++
        }
    if ($n -gt 0) { LogOk "$n pasta(s) __pycache__ removida(s)" }
    else          { LogSec "nenhum __pycache__ encontrado" }
}

function Fase-FletBuild {
    Log "--- flet build apk (~12-15 min) ---"
    $ini = Get-Date

    # Pre-limpar build\apk -- flet tenta shutil.rmtree nessa pasta e falha se Windows tiver lock
    # Remover antes para evitar PermissionError dentro do flet build
    $apkDir = "$projeto\build\apk"
    if (Test-Path $apkDir) {
        $prevEA2 = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        Remove-Item $apkDir -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path $apkDir) {
            Rename-Item $apkDir "$apkDir.old" -ErrorAction SilentlyContinue
            LogSec "build\apk renomeado (lock do Windows -- flet nao vai falhar)"
        } else {
            LogSec "build\apk removido (previne PermissionError no flet build)"
        }
        $ErrorActionPreference = $prevEA2
    }

    # pyproject.toml com org= gera package com.koios.* errado -- remover antes do build
    # Sem pyproject.toml: package = com.flet.prontuario (correto)
    $pyproject = "$projeto\pyproject.toml"
    if (Test-Path $pyproject) {
        Remove-Item $pyproject -Force
        LogSec "pyproject.toml removido (evita package com.koios.*)"
    }

    # FIX UnicodeEncodeError: forcar UTF-8 antes do flet (rich usa Unicode)
    $prevEncoding = [Console]::OutputEncoding
    $prevInput    = [Console]::InputEncoding
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::InputEncoding  = [System.Text.Encoding]::UTF8
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8       = "1"

    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & flet build apk `
        --project Prontuario `
        --source-packages pdfplumber google-auth google-auth-httplib2 `
                          requests repath anthropic httpx `
        --permissions camera photo_library `
        -v
    $fletExit = $LASTEXITCODE
    $ErrorActionPreference = $prev

    [Console]::OutputEncoding = $prevEncoding
    [Console]::InputEncoding  = $prevInput

    $prevKill = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    Get-Process -Name "java","javaw" -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 3

    # Deletar .cxx logo apos flet build -- evita AccessDeniedException no flutter build
    $cxxDir = "$projeto\build\flutter\android\app\.cxx"
    if (Test-Path $cxxDir) {
        cmd /c "rd /s /q `"$cxxDir`"" 2>$null
        if (Test-Path $cxxDir) {
            Rename-Item -Path $cxxDir -NewName ".cxx_trash" -ErrorAction SilentlyContinue
            LogSec ".cxx renomeado para .cxx_trash"
        } else {
            LogSec ".cxx removido apos flet build"
        }
    }
    $cxxTrash = "$projeto\build\flutter\android\app\.cxx_trash"
    if (Test-Path $cxxTrash) { cmd /c "rd /s /q `"$cxxTrash`"" 2>$null }
    $ErrorActionPreference = $prevKill

    $g = Buscar-Gradle
    if (-not $g) {
        throw "flet build falhou: gradle nao encontrado. Ver $logDir"
    }
    $dur = [int]((Get-Date) - $ini).TotalSeconds
    LogOk "flet build OK em ${dur}s | gradle: $g"
}

function Fase-LimparSitePackages {
    Log "--- Limpando site-packages ---"
    $arm64Dirs = Get-ChildItem -Path "$projeto\build\apk" -Recurse `
                    -Filter "arm64-v8a" -Directory -ErrorAction SilentlyContinue
    $achouAlgo = $false
    foreach ($arm64 in $arm64Dirs) {
        $parent = $arm64.Parent.FullName
        $gcDir  = "$($arm64.FullName)\googleapiclient"
        if (Test-Path $gcDir) {
            $jsons = Get-ChildItem $gcDir -Recurse -Filter "*.json"
            if ($jsons.Count -gt 0) {
                $mb = [math]::Round(($jsons | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
                $jsons | Remove-Item -Force
                LogOk "Deletados $($jsons.Count) JSONs googleapiclient ($mb MB)"
                $achouAlgo = $true
            }
        }
        foreach ($arch in @("armeabi-v7a","x86_64","x86")) {
            $archDir = "$parent\$arch"
            if (Test-Path $archDir) {
                Remove-Item $archDir -Recurse -Force
                LogOk "Removida arquitetura: $arch"
                $achouAlgo = $true
            }
        }
    }
    if (-not $achouAlgo) { LogSec "nada para limpar em site-packages" }
}

function Fase-ReescreverAppZip {
    Log "--- Reescrevendo app.zip (py atualizados + sem .git/.pyc) ---"
    $z = Buscar-AppZip
    if (-not $z) { throw "app.zip nao encontrado. Execute o Modo 1 primeiro." }

    $script = @"
import zipfile, pathlib, os, sys, hashlib

projeto = r'$projeto'
z       = r'$z'
tmp     = z + '.tmp'

excluir = ['build/', 'logs/', '.git/', '__pycache__/']
novos = {}
for arq in pathlib.Path(projeto).rglob('*.py'):
    rel = arq.relative_to(projeto).as_posix()
    if any(e in rel for e in excluir):
        continue
    novos[rel] = str(arq)

n_py = 0; n_rem = 0
with zipfile.ZipFile(z, 'r') as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        nome = item.filename
        if '.git/' in nome or '__pycache__' in nome or nome.endswith('.pyc'):
            n_rem += 1
            continue
        if nome in novos:
            zout.write(novos[nome], nome)
            del novos[nome]
            n_py += 1
        else:
            zout.writestr(item, zin.read(nome))
    for rel, caminho in novos.items():
        zout.write(caminho, rel)
        n_py += 1

os.replace(tmp, z)

sha256 = hashlib.sha256(open(z, 'rb').read()).hexdigest()
open(z + '.hash', 'w').write(sha256)

mb = round(os.path.getsize(z) / 1048576, 1)
print(f'OK {n_py} .py atualizados | {n_rem} entradas removidas | {mb} MB | hash={sha256[:16]}...')
sys.exit(0)
"@

    $saida = python -c $script 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Fase-ReescreverAppZip falhou: $saida" }
    $saida | ForEach-Object {
        if ($_ -like "OK*") { LogOk $_ } else { LogSec $_ }
    }
}

function Fase-NomeApp {
    Log "--- Configurando nome do app ---"
    $stringsXml = "$projeto\build\flutter\android\app\src\main\res\values\strings.xml"
    if (Test-Path $stringsXml) {
        $xml = Get-Content $stringsXml -Raw -Encoding UTF8
        $xml = $xml -replace '<string name="app_name">[^<]*</string>', '<string name="app_name">Prontuario Medico</string>'
        $xml | Set-Content $stringsXml -Encoding UTF8 -NoNewline
        LogOk "app_name = Prontuario Medico"
    } else {
        LogAviso "strings.xml nao encontrado -- nome padrao sera usado"
    }
}

function Fase-InjetarDeepLink {
    Log "--- Injetando deep link no AndroidManifest.xml ---"
    $manifest = "$projeto\build\flutter\android\app\src\main\AndroidManifest.xml"
    if (-not (Test-Path $manifest)) {
        LogAviso "AndroidManifest.xml nao encontrado -- pulando deep link"
        return
    }

    $xml = Get-Content $manifest -Raw -Encoding UTF8
    if ($xml -match "com.googleusercontent.apps") {
        LogOk "Deep link ja configurado no manifest"
        return
    }

    $secretsPath = "$projeto\client_secrets_android.json"
    if (-not (Test-Path $secretsPath)) { $secretsPath = "$projeto\client_secrets.json" }
    if (-not (Test-Path $secretsPath)) {
        LogAviso "client_secrets*.json nao encontrado -- deep link nao configurado"
        return
    }
    $secrets  = Get-Content $secretsPath -Raw | ConvertFrom-Json
    $clientId = $secrets.installed.client_id
    $base     = $clientId -replace "\.apps\.googleusercontent\.com", ""
    $scheme   = "com.googleusercontent.apps.$base"
    LogSec "Redirect scheme: ${scheme}"

    $intentFilter = @"

        <intent-filter>
            <action android:name="android.intent.action.VIEW" />
            <category android:name="android.intent.category.DEFAULT" />
            <category android:name="android.intent.category.BROWSABLE" />
            <data android:scheme="${scheme}" />
        </intent-filter>
"@

    $xml = $xml -replace "(<activity[^>]*MainActivity[^>]*>)([\s\S]*?)(</activity>)", "`$1`$2$intentFilter`n        `$3"
    $xml | Set-Content $manifest -Encoding UTF8 -NoNewline
    LogOk "Deep link injetado: ${scheme}:/"
}

function Fase-LockPortrait {
    Log "--- Bloqueando orientacao retrato ---"
    $manifest = "$projeto\build\flutter\android\app\src\main\AndroidManifest.xml"
    if (-not (Test-Path $manifest)) {
        LogAviso "AndroidManifest.xml nao encontrado -- pulando lock portrait"
        return
    }
    $xml = Get-Content $manifest -Raw -Encoding UTF8
    if ($xml -match "screenOrientation") {
        LogOk "screenOrientation ja configurado"
        return
    }
    $xml = $xml -replace '(<activity[^>]*MainActivity[^>]*)(>)', '$1 android:screenOrientation="portrait"$2'
    $xml | Set-Content $manifest -Encoding UTF8 -NoNewline
    LogOk "Orientacao travada em portrait"
}

function Fase-InjetarCamera {
    Log "--- Injetando suporte a camera nativa (image_picker) ---"
    $pubspec  = "$projeto\build\flutter\pubspec.yaml"
    $mainDart = "$projeto\build\flutter\lib\main.dart"

    if (Test-Path $pubspec) {
        $pub = Get-Content $pubspec -Raw -Encoding UTF8
        if ($pub -notmatch "image_picker") {
            $pub = $pub -replace "(dependencies:\r?\n)", "`$1  image_picker: ^1.1.2`n"
            $pub | Set-Content $pubspec -Encoding UTF8 -NoNewline
            LogOk "image_picker adicionado ao pubspec.yaml"
        } else {
            LogOk "image_picker ja presente no pubspec.yaml"
        }
    } else {
        LogAviso "pubspec.yaml nao encontrado -- pulando"
        return
    }

    if (Test-Path $mainDart) {
        $dart = Get-Content $mainDart -Raw -Encoding UTF8
        if ($dart -match "_setupCameraWatcher") {
            LogOk "camera watcher ja presente no main.dart"
            return
        }

        $dart = $dart -replace "(import 'dart:io';)", "`$1`nimport 'dart:convert';"
        $dart = $dart -replace "(import 'package:window_manager/window_manager\.dart';)", "`$1`nimport 'package:image_picker/image_picker.dart';"

        $cameraCode = @"

// -- Camera watcher: comunicacao via arquivo com Python --
bool _cameraInProgress = false;

void _setupCameraWatcher() {
  if (defaultTargetPlatform != TargetPlatform.android) return;
  final picker = ImagePicker();
  Timer.periodic(const Duration(milliseconds: 500), (timer) async {
    if (_cameraInProgress) return;
    try {
      final reqFile = File(path.join(appDir, '_camera_request.json'));
      if (!await reqFile.exists()) return;
      _cameraInProgress = true;
      await reqFile.delete();
      final resFile = File(path.join(appDir, '_camera_result.json'));
      try {
        final XFile? photo = await picker.pickImage(
          source: ImageSource.camera,
          maxWidth: 1920, maxHeight: 1920, imageQuality: 85,
        );
        if (photo != null) {
          await resFile.writeAsString(jsonEncode({'ok': true, 'path': photo.path}));
        } else {
          await resFile.writeAsString(jsonEncode({'ok': false, 'reason': 'cancelled'}));
        }
      } catch (e) {
        await resFile.writeAsString(jsonEncode({'ok': false, 'reason': e.toString()}));
      }
      _cameraInProgress = false;
    } catch (e) {
      _cameraInProgress = false;
      debugPrint('Camera watcher error: `$e');
    }
  });
}

"@
        $dart = $dart -replace "(void main\(List<String> args\) async \{)", "$cameraCode`$1"
        $dart = $dart -replace '(\s*)(return "";)', "`$1if (appDir.isNotEmpty) { _setupCameraWatcher(); }`n`$1`$2"
        $dart | Set-Content $mainDart -Encoding UTF8 -NoNewline
        LogOk "camera watcher injetado no main.dart"
    } else {
        LogAviso "main.dart nao encontrado -- pulando"
    }
}

function Fase-FlutterBuild {
    Log "--- Corrigindo gradle + flutter build arm64 ---"
    $g = Buscar-Gradle
    if (-not $g) { throw "gradle nao encontrado. Execute o Modo 1 primeiro." }

    (Get-Content $g) `
        -replace 'minSdkVersion flutter\.minSdkVersion','minSdkVersion 24' |
        Set-Content $g
    LogOk "minSdkVersion 24 em $g"

    $gc = Get-Content $g -Raw
    if ($gc -notmatch "arm64-v8a") {
        $gc = $gc -replace "(ndk \{[^}]*\})", "ndk {`n            abiFilters `"arm64-v8a`"`n        }"
        if ($gc -match "arm64-v8a") {
            $gc | Set-Content $g -NoNewline
            LogOk "abiFilters arm64-v8a adicionado ao build.gradle"
        } else {
            $gc = $gc -replace "(defaultConfig \{)", "`$1`n        ndk {`n            abiFilters `"arm64-v8a`"`n        }"
            $gc | Set-Content $g -NoNewline
            LogOk "abiFilters arm64-v8a inserido em defaultConfig"
        }
    } else {
        LogOk "abiFilters arm64-v8a ja presente"
    }

    Log "--- flutter clean ---"
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    Set-Location "$projeto\build\flutter"
    & $flutter clean 2>&1 | Out-Null
    Set-Location $projeto
    $ErrorActionPreference = $prev
    LogOk "flutter clean concluido"

    Log "--- Encerrando processos Java residuais ---"
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    Get-Process -Name "java","javaw" -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 3
    $ErrorActionPreference = $prev

    Log "--- Limpando residuos do Gradle ---"
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    cmd /c "rd /s /q `"$projeto\build\flutter\build`"" 2>$null
    LogSec "build\flutter\build removido"
    cmd /c "rd /s /q `"$projeto\build\flutter\android\app\.cxx`"" 2>$null
    LogSec "android\app\.cxx removido"
    Start-Sleep -Seconds 2
    $ErrorActionPreference = $prev
    LogOk "residuos do Gradle limpos"

    $androidDir = Split-Path (Split-Path $g)
    $ini = Get-Date
    Set-Location $androidDir

    $env:SERIOUS_PYTHON_SITE_PACKAGES = "$projeto\build\site-packages"

    Fase-NomeApp
    Fase-InjetarDeepLink
    Fase-LockPortrait
    Fase-InjetarCamera

    # FIX CRITICO: pub get apos InjetarCamera -- registra image_picker_android
    Log "--- flutter pub get (registrar image_picker_android) ---"
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    Set-Location "$projeto\build\flutter"
    & $flutter pub get 2>&1 | ForEach-Object { Write-Host $_ }
    Set-Location $androidDir
    $ErrorActionPreference = $prev
    LogOk "flutter pub get concluido"

    LogSec "SERIOUS_PYTHON_SITE_PACKAGES: $env:SERIOUS_PYTHON_SITE_PACKAGES"

    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $flutter build apk --target-platform android-arm64 --no-version-check `
        --android-skip-build-dependency-validation 2>&1 | ForEach-Object {
            if ($_ -notmatch "SDK XML versions|NativeCommandError") {
                Write-Host $_
            }
        }
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $prev

    $apkGerado = Buscar-ApkOrigem
    if (-not $apkGerado) {
        throw "flutter build falhou (exit $exitCode). Ver $logDir\flutter_build.log"
    }
    $dur = [int]((Get-Date) - $ini).TotalSeconds
    LogOk "flutter build OK em ${dur}s | APK: $apkGerado"
    Set-Location $projeto
}

function Fase-CopiarInstalar {
    Log "--- Copiando APK ---"
    $origem = Buscar-ApkOrigem
    if (-not $origem) {
        # flutter build output nao existe (ex: flutter clean rodou sem rebuild)
        # se o APK final ja existe em build\apk, usa direto sem copiar
        if (Test-Path $apkDestino) {
            LogSec "APK flutter nao encontrado -- usando build\apk existente"
        } else {
            LogAviso "APK nao encontrado -- execute Modo 1 primeiro"
            return
        }
    } else {
        $destPai = Split-Path $apkDestino
        if (-not (Test-Path $destPai)) { New-Item -ItemType Directory -Path $destPai | Out-Null }
        Copy-Item $origem $apkDestino -Force
        $mb = [math]::Round((Get-Item $apkDestino).Length / 1MB, 1)
        if ($mb -gt 80) { LogAviso "APK: $mb MB (acima de 80 MB -- investigar)" }
        else            { LogOk    "APK: $mb MB | $apkDestino" }
    }

    Log "--- Instalando no dispositivo ---"
    $prevAdb = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $devOut  = & $adb devices 2>&1
    $devices = $devOut | Select-String "device$"
    if ($devices) {
        Log "  Instalando (preservando dados do app)..."
        $instOut = & $adb install -r $apkDestino 2>&1
        $adbExit = $LASTEXITCODE
        $ErrorActionPreference = $prevAdb
        $instOut | ForEach-Object { Log "  $_" }
        if ($adbExit -eq 0) {
            LogOk "APK instalado no dispositivo"

            Log "--- Abrindo app ---"
            $ErrorActionPreference = "Continue"
            $pkg = & $adb shell pm list packages 2>&1 |
                   Where-Object { $_ -match "prontuario" } |
                   ForEach-Object { ($_ -replace "package:", "").Trim() } |
                   Select-Object -First 1
            if ($pkg) {
                & $adb shell monkey -p $pkg -c android.intent.category.LAUNCHER 1 2>&1 | Out-Null
                LogOk "App aberto: $pkg"
            } else {
                LogAviso "Package nao encontrado -- abra o app manualmente"
            }

            Log "--- Aguardando 30s para capturar logcat ---"
            $ErrorActionPreference = $prevAdb
            Write-Host ""
            Write-Host "  >>> APP ABERTO NO CELULAR -- aguardando 30 segundos... <<<" -ForegroundColor Cyan
            Write-Host ""
            Start-Sleep -Seconds 30
            $logcatFile = "$logDir\logcat_$(Get-Date -Format yyyyMMdd_HHmmss).log"
            $ErrorActionPreference = "Continue"
            & $adb logcat -v time -d 2>&1 |
                Select-String -Pattern "PRONTUARIO|prontuario|KOIOS|koios|python|flet|serious|FATAL|AndroidRuntime|crash|exception|sqlite" `
                              -CaseSensitive:$false |
                Out-File $logcatFile -Encoding UTF8
            $ErrorActionPreference = $prevAdb
            LogOk "Logcat salvo em: $logcatFile"
            Write-Host ""
            Write-Host "=== LOGCAT ===" -ForegroundColor Cyan
            Get-Content $logcatFile
        } else {
            $ErrorActionPreference = $prevAdb
            LogAviso "adb install com erro -- verifique manualmente"
        }
    } else {
        $ErrorActionPreference = $prevAdb
        LogAviso "Nenhum dispositivo ADB conectado -- instalacao pulada"
    }
}

function Resumo-Final([string]$titulo, [datetime]$ini) {
    $dur = [int]((Get-Date) - $ini).TotalSeconds
    $min = [int]($dur / 60); $seg = $dur % 60
    Log ""
    Log "=================================================" "Cyan"
    Log "  $titulo -- CONCLUIDO em ${min}m${seg}s" "Cyan"
    Log "  APK : $apkDestino" "Cyan"
    Log "  Log : $script:logFile" "Cyan"
    Log "=================================================" "Cyan"
    Log ""
    Log "Proximo build -- escolha o modo correto:" "DarkGray"
    Log "  Editou .py               -> .\build_prontuario.ps1 -modo 2" "DarkGray"
    Log "  Mudou assets/pubspec     -> .\build_prontuario.ps1 -modo 3" "DarkGray"
    Log "  Novo pacote / primeiro   -> .\build_prontuario.ps1 -modo 1" "DarkGray"
    Log "  Flet OK, flutter falhou  -> .\build_prontuario.ps1 -modo 5" "DarkGray"
}

# ==============================================================================
# MENU INTERATIVO
# ==============================================================================
function Mostrar-Menu {
    Write-Host ""
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host "   PRONTUARIO MEDICO  --  BUILD v3" -ForegroundColor Cyan
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [1]  COMPLETO             ~20 min" -ForegroundColor White
    Write-Host "       Primeiro build / novo pacote pip / novo Flet" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  [2]  SO ARQUIVOS .PY      ~5 min" -ForegroundColor Green
    Write-Host "       Editou main.py, app.py, telas/, utils/, shared/" -ForegroundColor DarkGray
    Write-Host "       Nao mudou assets/, requirements, Flet" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  [3]  ASSETS / PUBSPEC     ~12 min" -ForegroundColor Yellow
    Write-Host "       Alterou assets/ ou pubspec.yaml" -ForegroundColor DarkGray
    Write-Host "       Sem pacote pip novo" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  [4]  SO INSTALAR E ABRIR  <1 min" -ForegroundColor Magenta
    Write-Host "       Celular conectado -- APK ja gerado" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  [5]  SO FLUTTER BUILD     ~2 min" -ForegroundColor Cyan
    Write-Host "       flet build OK, flutter falhou -- retoma daqui" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  [0]  Cancelar" -ForegroundColor DarkGray
    Write-Host ""
    $esc = Read-Host "Escolha [1/2/3/4/5/0]"
    return $esc
}

# ==============================================================================
# PONTO DE ENTRADA
# ==============================================================================
Set-Location $projeto

if (-not $modo) {
    $modo = Mostrar-Menu
    if ($modo -eq "0" -or $modo -eq "") {
        Write-Host "Cancelado." -ForegroundColor DarkGray
        exit 0
    }
    if ($modo -notin @("1","2","3","4","5")) {
        Write-Host "[ERRO] Opcao invalida: $modo" -ForegroundColor Red
        exit 1
    }
}

# ==============================================================================
# MODO 1 -- COMPLETO
# ==============================================================================
if ($modo -eq "1") {
    Iniciar-Log "MODO1_COMPLETO"
    $inicio = Get-Date
    Log "MODO 1 -- COMPLETO (~20 min)" "Cyan"

    Fase-CorrigirPubspec
    Fase-LimparPycache
    Fase-MoverPastas

    try {
        Fase-FletBuild
        Fase-LimparSitePackages
        Fase-ReescreverAppZip
        Fase-FlutterBuild
        Fase-CopiarInstalar
    } finally {
        Fase-RestaurarPastas
    }

    Resumo-Final "MODO 1 (COMPLETO)" $inicio
}

# ==============================================================================
# MODO 2 -- SO ARQUIVOS .PY
# ==============================================================================
elseif ($modo -eq "2") {
    Iniciar-Log "MODO2_SO_PY"
    $inicio = Get-Date
    Log "MODO 2 -- SO ARQUIVOS .PY (~5 min)" "Green"

    Fase-VerificarBuildAnterior
    Fase-LimparPycache
    Fase-ReescreverAppZip
    Fase-FlutterBuild
    Fase-CopiarInstalar

    Resumo-Final "MODO 2 (SO .PY)" $inicio
}

# ==============================================================================
# MODO 3 -- ASSETS / PUBSPEC
# ==============================================================================
elseif ($modo -eq "3") {
    Iniciar-Log "MODO3_ASSETS"
    $inicio = Get-Date
    Log "MODO 3 -- ASSETS / PUBSPEC (~12 min)" "Yellow"

    Fase-VerificarBuildAnterior
    Fase-LimparPycache
    Fase-CorrigirPubspec
    Fase-MoverPastas

    try {
        Fase-FletBuild
        Fase-LimparSitePackages
        Fase-ReescreverAppZip
        Fase-FlutterBuild
        Fase-CopiarInstalar
    } finally {
        Fase-RestaurarPastas
    }

    Resumo-Final "MODO 3 (ASSETS/PUBSPEC)" $inicio
}

# ==============================================================================
# MODO 4 -- SO INSTALAR E ABRIR
# ==============================================================================
elseif ($modo -eq "4") {
    Iniciar-Log "MODO4_INSTALAR"
    $inicio = Get-Date
    Log "MODO 4 -- SO INSTALAR E ABRIR" "Magenta"

    if (-not (Test-Path $apkDestino)) {
        $apkOrigem = Buscar-ApkOrigem
        if ($apkOrigem) {
            $destPai = Split-Path $apkDestino
            if (-not (Test-Path $destPai)) { New-Item -ItemType Directory -Path $destPai | Out-Null }
            Copy-Item $apkOrigem $apkDestino -Force
            LogOk "APK copiado: $apkDestino"
        } else {
            throw "APK nao encontrado em $apkDestino -- execute o Modo 1 primeiro"
        }
    }

    $mb = [math]::Round((Get-Item $apkDestino).Length / 1MB, 1)
    LogOk "APK: $mb MB | $apkDestino"

    Fase-CopiarInstalar

    Resumo-Final "MODO 4 (INSTALAR)" $inicio
}

# ==============================================================================
# MODO 5 -- SO FLUTTER BUILD (flet build OK, flutter falhou)
# ==============================================================================
elseif ($modo -eq "5") {
    Iniciar-Log "MODO5_FLUTTER_BUILD"
    $inicio = Get-Date
    Log "MODO 5 -- SO FLUTTER BUILD (~2 min)" "Cyan"

    Fase-VerificarBuildAnterior
    Fase-FlutterBuild
    Fase-CopiarInstalar

    Resumo-Final "MODO 5 (FLUTTER BUILD)" $inicio
}
