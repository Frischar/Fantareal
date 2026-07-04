param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$HuskarUIRoot = $env:HUSKARUI_ROOT,
    [string]$QtPrefix = '',
    [switch]$Build,
    [switch]$SkipRun,
    [string]$CMakePath = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe',
    [string]$NinjaPath = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe',
    [string]$VsVarsPath = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat',
    [string]$QmlFormatPath = ''
)

$ErrorActionPreference = 'Stop'

function Write-Step($message) {
    Write-Host "==> $message"
}

function Import-BatchEnvironment($batchPath) {
    if (-not (Test-Path -LiteralPath $batchPath)) {
        throw "Visual Studio vcvars64.bat not found: $batchPath"
    }

    $environment = & cmd.exe /d /s /c "call `"$batchPath`" >nul && set"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to load Visual Studio build environment: $batchPath"
    }

    foreach ($line in $environment) {
        if ($line -match '^([^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
        }
    }
}

Write-Step 'Checking required files'
$requiredFiles = @(
    'CMakeLists.txt',
    'cpp\main.cpp',
    'cpp\fantarealbridge.h',
    'cpp\fantarealbridge.cpp',
    'qml\FantarealApp.qml',
    'qml\Global.qml',
    'qml\controls\SettingField.qml',
    'qml\pages\HomePage.qml',
    'qml\pages\ChatPage.qml',
    'qml\pages\SettingsPage.qml',
    'qml\pages\RoutesPage.qml',
    'qml\pages\CardsPage.qml',
    'qml\pages\PresetPage.qml',
    'qml\pages\MemoryPage.qml',
    'qml\pages\WorldbookPage.qml',
    'qml\pages\WorkshopPage.qml',
    'qml\pages\PluginsPage.qml'
)
foreach ($relativePath in $requiredFiles) {
    $path = Join-Path $ProjectRoot $relativePath
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing required file: $path"
    }
}

Write-Step 'Running qmlformat parser check'
$resolvedQmlFormatPath = ''
if ($QmlFormatPath -and (Test-Path -LiteralPath $QmlFormatPath)) {
    $resolvedQmlFormatPath = $QmlFormatPath
} elseif ($QtPrefix) {
    $qtQmlFormatPath = Join-Path $QtPrefix 'bin\qmlformat.exe'
    if (Test-Path -LiteralPath $qtQmlFormatPath) {
        $resolvedQmlFormatPath = $qtQmlFormatPath
    }
}
if (-not $resolvedQmlFormatPath) {
    $qmlFormatCommand = Get-Command qmlformat.exe -ErrorAction SilentlyContinue
    if ($qmlFormatCommand) {
        $resolvedQmlFormatPath = $qmlFormatCommand.Source
    }
}
if ($resolvedQmlFormatPath) {
    Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'qml') -Recurse -Filter *.qml | ForEach-Object {
        & $resolvedQmlFormatPath $_.FullName > $null
        if ($LASTEXITCODE -ne 0) {
            throw "qmlformat failed: $($_.FullName)"
        }
    }
} else {
    Write-Host 'qmlformat.exe not found; skipping parser check.'
}

Write-Step 'Checking known HuskarUI API mistakes'
$badPatterns = @(
    'prefixIconSource',
    '\?\?',
    '\.slice\(',
    'HusButton\s*\{[^}]*iconSource',
    'Global\.accentPink'
)
foreach ($pattern in $badPatterns) {
    $matches = Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'qml') -Recurse -Filter *.qml |
        Select-String -Pattern $pattern
    if ($matches) {
        $matches | ForEach-Object { Write-Host $_.Line }
        throw "Known risky QML pattern found: $pattern"
    }
}

Write-Step 'Checking build environment'
if (-not (Test-Path -LiteralPath $CMakePath)) {
    throw "cmake.exe not found: $CMakePath"
}
if (-not (Test-Path -LiteralPath $NinjaPath)) {
    throw "ninja.exe not found: $NinjaPath"
}
if (-not $QtPrefix) {
    Write-Host 'QtPrefix not provided; skipping CMake configure. Pass -QtPrefix <Qt6 SDK prefix> to test configure.'
    Write-Host 'Static HuskarUI verification passed.'
    exit 0
}

if ($QtPrefix -match 'msvc') {
    Write-Step 'Loading Visual Studio x64 build environment'
    Import-BatchEnvironment $VsVarsPath
}

$buildDir = Join-Path $ProjectRoot 'build-verify'
if (Test-Path -LiteralPath $buildDir) {
    Remove-Item -LiteralPath $buildDir -Recurse -Force
}

$cmakeArgs = @(
    '-S', $ProjectRoot,
    '-B', $buildDir,
    '-G', 'Ninja',
    '-DCMAKE_BUILD_TYPE=Release',
    "-DCMAKE_MAKE_PROGRAM=$NinjaPath",
    "-DCMAKE_PREFIX_PATH=$QtPrefix",
    "-DHUSKARUI_ROOT=$HuskarUIRoot"
)

if ($QtPrefix -match 'msvc') {
    $cmakeArgs += @(
        '-DCMAKE_C_COMPILER=cl.exe',
        '-DCMAKE_CXX_COMPILER=cl.exe'
    )
}

& $CMakePath @cmakeArgs
if ($LASTEXITCODE -ne 0) {
    throw 'CMake configure failed.'
}

if ($Build) {
    Write-Step 'Building Release target'
    & $CMakePath --build $buildDir
    if ($LASTEXITCODE -ne 0) {
        throw 'CMake build failed.'
    }

    $exePath = Join-Path $buildDir 'FantarealHuskarUI.exe'
    if (-not (Test-Path -LiteralPath $exePath)) {
        throw "Build completed but executable was not found: $exePath"
    }

    Write-Step 'Running CTest'
    $env:PATH = (Join-Path $QtPrefix 'bin') + ';' + $env:PATH
    & $CMakePath --build $buildDir --target test
    if ($LASTEXITCODE -ne 0) {
        throw 'CTest failed.'
    }

    if (-not $SkipRun) {
        foreach ($page in @('chat', 'settings', 'routes', 'cards', 'memory', 'worldbook', 'preset')) {
            Write-Step "Running smoke test: $page"
            $logPath = Join-Path $buildDir 'FantarealHuskarUI.log'
            if (Test-Path -LiteralPath $logPath) {
                Remove-Item -LiteralPath $logPath -Force
            }

            $processInfo = [System.Diagnostics.ProcessStartInfo]::new($exePath)
            $processInfo.Arguments = "--page=$page"
            $processInfo.WorkingDirectory = Split-Path -Parent $exePath
            $processInfo.UseShellExecute = $false
            $processInfo.Environment['PATH'] = (Join-Path $QtPrefix 'bin') + ';' + (Join-Path $buildDir 'HuskarUI\bin') + ';' + $processInfo.Environment['PATH']
            $processInfo.Environment['QML_IMPORT_PATH'] = Join-Path $buildDir 'HuskarUI\qml'
            $processInfo.Environment['FANTAREAL_ROOT'] = (Resolve-Path (Join-Path $ProjectRoot '..')).Path

            $process = [System.Diagnostics.Process]::Start($processInfo)
            try {
                Start-Sleep -Seconds 5
                $process.Refresh()
                if ($process.HasExited) {
                    throw "Smoke test '$page' process exited early with code $($process.ExitCode)."
                }
                if (-not $process.MainWindowHandle -or $process.MainWindowTitle -ne 'Fantareal PC') {
                    throw "Smoke test '$page' did not create the expected main window. Title='$($process.MainWindowTitle)' Handle='$($process.MainWindowHandle)'"
                }
            } finally {
                if ($process -and -not $process.HasExited) {
                    $null = $process.CloseMainWindow()
                    Start-Sleep -Seconds 1
                    $process.Refresh()
                    if (-not $process.HasExited) {
                        $process.Kill()
                    }
                }
            }

            if (Test-Path -LiteralPath $logPath) {
                $runtimeProblems = Get-Content -Encoding UTF8 -LiteralPath $logPath |
                    Select-String -Pattern 'TypeError|ReferenceError|CRITICAL|FATAL|QML root object load failed'
                if ($runtimeProblems) {
                    $runtimeProblems | ForEach-Object { Write-Host $_.Line }
                    throw "Smoke test '$page' found runtime QML/C++ errors in $logPath"
                }
            }
        }
    }

    Write-Host "Static HuskarUI verification, CMake configure, Release build, and smoke test passed: $exePath"
    exit 0
}

Write-Host 'Static HuskarUI verification and CMake configure passed.'
