param(
    [ValidateSet('validate', 'quality', 'fault', 'all')]
    [string]$Mode = 'all',
    [string]$RunName = 'candidate',
    [string]$CodeVersion = 'unrecorded',
    [string]$ModelName = 'qwen-flash',
    [string]$PromptVersion = 'current',
    [int]$Repeats = 1,
    [int]$DelayMs = 100,
    [string]$BaseUrl = 'http://localhost:8080/api/v1/diet',
    [long]$UserId = 910001,
    [string]$Cases = '',
    [string]$FaultCases = '',
    [string]$OutputDir = '',
    [int]$Timeout = 60
)

$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$scriptPath = Join-Path $PSScriptRoot 'run_evaluation.py'
$arguments = @(
    $scriptPath,
    '--mode', $Mode,
    '--run-name', $RunName,
    '--code-version', $CodeVersion,
    '--model-name', $ModelName,
    '--prompt-version', $PromptVersion,
    '--repeats', $Repeats,
    '--delay-ms', $DelayMs,
    '--base-url', $BaseUrl,
    '--user-id', $UserId,
    '--timeout', $Timeout
)

if ($Cases) {
    $arguments += @('--cases', $Cases)
}
if ($FaultCases) {
    $arguments += @('--fault-cases', $FaultCases)
}
if ($OutputDir) {
    $arguments += @('--output-dir', $OutputDir)
}

& python @arguments
exit $LASTEXITCODE
