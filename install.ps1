param(
    [switch]$SetupShell,
    [switch]$Update,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallHome = if ($env:MCP_SKELETON_HOME) { $env:MCP_SKELETON_HOME } else { Join-Path $env:USERPROFILE ".mcp-skeleton" }
$VenvDir = Join-Path $InstallHome "venv"
$CommandDir = Join-Path $InstallHome "bin"
$CommandPath = Join-Path $CommandDir "mcp-skeleton.cmd"
$ReadinessPath = Join-Path $InstallHome "install-readiness.json"

function Write-Info {
    param([string]$Message)
    Write-Host "[MCP-Skeleton] $Message" -ForegroundColor Cyan
}

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        return @("python3")
    }
    throw "Python 3.10+ was not found. Install Python from https://www.python.org/downloads/windows/ and retry."
}

function Invoke-Python {
    param([string[]]$Arguments)
    $Python = Get-PythonCommand
    $PythonArgs = @()
    if ($Python.Length -gt 1) {
        $PythonArgs = $Python[1..($Python.Length - 1)]
    }
    & $Python[0] @($PythonArgs + $Arguments)
}

function Write-CommandShim {
    New-Item -ItemType Directory -Force -Path $CommandDir | Out-Null
    $EntryPoint = Join-Path $VenvDir "Scripts\mcp-skeleton.exe"
    $Shim = "@echo off`r`n`"$EntryPoint`" %*`r`n"
    Set-Content -Path $CommandPath -Value $Shim -Encoding ASCII
}

function Write-ReadinessManifest {
    param([bool]$ShellConfigured)
    $PythonExe = Join-Path $VenvDir "Scripts\python.exe"
    $Manifest = [ordered]@{
        status = "ready"
        platform = "win32"
        installed_at = (Get-Date).ToUniversalTime().ToString("o")
        install_home = $InstallHome
        venv_dir = $VenvDir
        command_path = $CommandPath
        setup_shell = $ShellConfigured
        install_command_text = ".\install.ps1"
        update_command_text = ".\install.ps1 -Update"
        uninstall_command_text = ".\install.ps1 -Uninstall"
        path_setup_command_text = ".\install.ps1 -SetupShell"
        temporary_path_command_text = "`$env:PATH = `"$CommandDir;`$env:PATH`""
        self_check_command_text = "mcp-skeleton version"
        install_doctor_command_text = "mcp-skeleton doctor --install"
        recommended_first_command_text = "mcp-skeleton handoff"
        python_executable = $PythonExe
    }
    New-Item -ItemType Directory -Force -Path $InstallHome | Out-Null
    $Manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $ReadinessPath -Encoding UTF8
}

function Install-McpSkeleton {
    Write-Info "Creating virtual environment at $VenvDir"
    New-Item -ItemType Directory -Force -Path $InstallHome | Out-Null
    if (-not (Test-Path $VenvDir)) {
        Invoke-Python -Arguments @("-m", "venv", $VenvDir)
    }

    $PythonExe = Join-Path $VenvDir "Scripts\python.exe"
    Write-Info "Upgrading pip"
    & $PythonExe -m pip install --upgrade pip | Out-Null

    Write-Info "Installing MCP-Skeleton with context-metrics extras"
    & $PythonExe -m pip install -e "$RootDir[context-metrics]"
    if ($LASTEXITCODE -ne 0) {
        Write-Info "context-metrics install failed; retrying base install"
        & $PythonExe -m pip install -e "$RootDir"
    }

    Write-CommandShim
    Write-ReadinessManifest -ShellConfigured:$SetupShell.IsPresent

    Write-Info "Install complete"
    Write-Host ""
    Write-Host "Command:" -ForegroundColor Green
    Write-Host "  $CommandPath"
    Write-Host ""
    Write-Host "Copy/paste next:" -ForegroundColor Green
    Write-Host "  mcp-skeleton doctor --install"
    Write-Host "  mcp-skeleton handoff"
    Write-Host ""
    Write-Host "If mcp-skeleton is not found in this terminal, run:" -ForegroundColor Yellow
    Write-Host "  `$env:PATH = `"$CommandDir;`$env:PATH`""
}

function Setup-Path {
    $ProfilePath = $PROFILE.CurrentUserCurrentHost
    $ProfileDir = Split-Path -Parent $ProfilePath
    New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null
    $BlockStart = "# >>> MCP-Skeleton PATH >>>"
    $BlockEnd = "# <<< MCP-Skeleton PATH <<<"
    $Block = @"

$BlockStart
`$env:PATH = "$CommandDir;`$env:PATH"
$BlockEnd
"@
    $Existing = if (Test-Path $ProfilePath) { Get-Content $ProfilePath -Raw } else { "" }
    if ($Existing -notlike "*$BlockStart*") {
        Add-Content -Path $ProfilePath -Value $Block -Encoding UTF8
        Write-Info "Added MCP-Skeleton PATH block to $ProfilePath"
    } else {
        Write-Info "MCP-Skeleton PATH block already exists in $ProfilePath"
    }
}

function Uninstall-McpSkeleton {
    Write-Info "Removing $InstallHome"
    Remove-Item -Path $InstallHome -Recurse -Force -ErrorAction SilentlyContinue
    Write-Info "Uninstall complete. Remove the MCP-Skeleton PATH block from your PowerShell profile if you added it."
}

if ($Uninstall) {
    Uninstall-McpSkeleton
    exit 0
}

Install-McpSkeleton
if ($SetupShell) {
    Setup-Path
    Write-ReadinessManifest -ShellConfigured:$true
    Write-Host ""
    Write-Host "Restart PowerShell or run:" -ForegroundColor Yellow
    Write-Host "  `$env:PATH = `"$CommandDir;`$env:PATH`""
}

if ($Update) {
    Write-Info "Update complete"
}
