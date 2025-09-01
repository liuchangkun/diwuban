# 一键恢复（只读/低风险）
# 作用：重启后快速恢复知识与项目现状，对齐仓库事实与导航
# 步骤：更新知识图谱 → 刷新最近变更 → 连接自检 → （可选）pre-commit 全量体检
# 说明：不会写入数据库；pre-commit 可能对代码/文档做自动修复（按项目策略），如不希望修改，可注释该步骤。

param(
    [switch]$SkipPreCommit
)

$ErrorActionPreference = 'Stop'
$PSStyle.OutputRendering = 'PlainText'

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host "[RESTORE] $Name ..." -ForegroundColor Cyan
    try {
        & $Action
        Write-Host "[RESTORE] $Name OK" -ForegroundColor Green
        return @{ name = $Name; ok = $true }
    }
    catch {
        Write-Host "[RESTORE] $Name FAILED: $($_.Exception.Message)" -ForegroundColor Red
        return @{ name = $Name; ok = $false; error = $_.Exception.Message }
    }
}

$results = @()

# 1) 知识图谱更新
$results += Invoke-Step -Name '更新知识图谱 (kg_update.py)' -Action {
    python scripts/tools/kg_update.py | Out-Host
}

# 2) 最近变更刷新（导航）
$results += Invoke-Step -Name '刷新最近变更 (memory_index.py)' -Action {
    python scripts/tools/memory_index.py | Out-Host
}

# 3) 连接自检（只读）
$results += Invoke-Step -Name '数据库连通性自检 (db-ping --verbose)' -Action {
    python -m app.cli.main db-ping --verbose | Out-Host
}

# 4) pre-commit 全量体检（可选，可能自动修复）
if (-not $SkipPreCommit) {
    if (Get-Command pre-commit -ErrorAction SilentlyContinue) {
        $results += Invoke-Step -Name 'pre-commit run --all-files（可能修改文件）' -Action {
            pre-commit run --all-files -v --show-diff-on-failure | Out-Host
        }
    }
    else {
        Write-Host '[RESTORE] pre-commit 未安装，跳过此步骤' -ForegroundColor Yellow
        $results += @{ name = 'pre-commit'; ok = $false; error = 'pre-commit 未安装' }
    }
}
else {
    Write-Host '[RESTORE] 跳过 pre-commit（按参数指定）' -ForegroundColor Yellow
}

# 总结
Write-Host "`n[RESTORE] 完成。步骤结果：" -ForegroundColor Cyan
$results | ForEach-Object {
    $status = if ($_.ok) { 'OK' } else { 'FAILED' }
    Write-Host (" - {0}: {1}" -f $_.name, $status)
}

