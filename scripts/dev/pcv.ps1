# 质量门禁 - 本地全量（详细）
# 用法：在仓库根目录 PowerShell 执行：
#   scripts/dev/pcv.ps1
# 说明：
# - 运行 pre-commit 全量，打开详细与失败差异；
# - 将报告写入 pre-commit-report.txt；
# - 显示本次改动的 git diff。

param(
  [switch]$NoDiff
)

# 尝试启用 UTF-8 输出，避免中文乱码（兼容 Windows PowerShell）
chcp 65001 > $null 2>&1
$env:PYTHONUTF8 = "1"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = $utf8NoBom
# 在部分旧版 PowerShell 上可能不支持赋值 Console.OutputEncoding，失败可忽略
try { [Console]::OutputEncoding = $utf8NoBom } catch {}

Write-Host "[pcv] 切换到仓库根..." -ForegroundColor Cyan
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

Write-Host "[pcv] 运行 pre-commit（详细+失败显示差异）..." -ForegroundColor Cyan
$cmd = "pre-commit run --all-files -v --show-diff-on-failure"
& powershell -NoProfile -Command $cmd | Tee-Object -FilePath pre-commit-report.txt

if (-not $NoDiff) {
  Write-Host "[pcv] 展示 git diff（如有自动格式化/修复）..." -ForegroundColor Cyan
  git --no-pager diff --color
}

Write-Host "[pcv] 完成。报告：pre-commit-report.txt" -ForegroundColor Green
