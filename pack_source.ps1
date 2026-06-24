# pack_source.ps1
# 用于打包 CloudLingoStudio 源代码，自动排除虚拟环境、缓存、构建产物和敏感文件

$ProjectPath = "D:\trans\2\CloudLingoStudio"
$OutputDir = "D:\trans\2"
$ZipName = "CloudLingoStudio_source.zip"
$ZipPath = Join-Path $OutputDir $ZipName

$ExcludeDirs = @(
    ".venv",
    "venv",
    "__pycache__",
    "build",
    "dist",
    ".git",
    ".idea",
    ".vscode"
)

$ExcludeFiles = @(
    ".env",
    "config.json",
    "secrets.json",
    "*.log",
    "*.pyc",
    "*.pyo",
    "*.tmp"
)

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}

$TempDir = Join-Path $OutputDir "CloudLingoStudio_source_temp"

if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}

New-Item -ItemType Directory -Path $TempDir | Out-Null

Get-ChildItem -Path $ProjectPath -Force | ForEach-Object {
    $Name = $_.Name
    $FullName = $_.FullName

    if ($_.PSIsContainer -and ($ExcludeDirs -contains $Name)) {
        return
    }

    $ShouldExcludeFile = $false
    foreach ($Pattern in $ExcludeFiles) {
        if ($Name -like $Pattern) {
            $ShouldExcludeFile = $true
            break
        }
    }

    if ($ShouldExcludeFile) {
        return
    }

    Copy-Item -Path $FullName -Destination $TempDir -Recurse -Force
}

Compress-Archive -Path "$TempDir\*" -DestinationPath $ZipPath -Force

Remove-Item $TempDir -Recurse -Force

Write-Host "源码已打包完成：" $ZipPath
