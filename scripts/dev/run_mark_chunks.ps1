param(
  [string]$Start,
  [string]$End,
  [int]$StationId,
  [int]$DeviceId,
  [int]$StepMin = 10
)

$ErrorActionPreference = 'Stop'

$startDt = [datetime]::Parse($Start)
$endDt   = [datetime]::Parse($End)
$step    = [timespan]::FromMinutes($StepMin)

$t = $startDt
while ($t -lt $endDt) {
  $sStr = $t.ToString('yyyy-MM-ddTHH:mm:ssZ')
  $eStr = ($t + $step).ToString('yyyy-MM-ddTHH:mm:ssZ')
  if ([datetime]::Parse($eStr) -gt $endDt) { $eStr = $endDt.ToString('yyyy-MM-ddTHH:mm:ssZ') }
  Write-Host "[Chunk] $sStr -> $eStr"
  python -m app.cli.main quality:mark-window --start $sStr --end $eStr --station-id $StationId --device-id $DeviceId
  if ($LASTEXITCODE -ne 0) { throw "chunk failed $sStr -> $eStr" }
  $t = $t + $step
}

