param(
  [string]$Root = ".",
  [string]$OutFile = "PROJECT_TREE.md",
  [string[]]$Exclude = @('.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.pytest_cache', '.mypy_cache', '.vscode', '.idea', 'build', 'dist', 'pip-wheel-metadata')
)

function Write-Tree {
  param($Path, $Prefix = "")
  $items = Get-ChildItem -LiteralPath $Path -Force | Where-Object {
    $name = $_.Name
    # Exclude exact names
    if ($Exclude -contains $name) { return $false }
    # Exclude patterns (egg-info, .egg-info folders, etc.)
    foreach ($pat in $Exclude) {
      if ($pat -like "*egg-info*" -and $name -like "*egg-info*") { return $false }
    }
    return $true
  } | Sort-Object @{Expression = { -not $_.PSIsContainer }}, Name

  $count = $items.Count
  for ($i=0; $i -lt $count; $i++) {
    $item = $items[$i]
    $isLast = ($i -eq $count - 1)
      # Use ASCII-safe markers to avoid encoding issues in PowerShell
      if ($isLast) {
        $marker = "- "
      } else {
        $marker = "|- "
      }
    $line = "$Prefix$marker$item"
    $line | Out-File -FilePath $script:out -Append -Encoding utf8
    if ($item.PSIsContainer) {
        if ($isLast) {
          $newPrefix = $Prefix + "    "
        } else {
          $newPrefix = $Prefix + "|  "
        }
        Write-Tree -Path $item.FullName -Prefix $newPrefix
    }
  }
}

# prepare output
$script:out = Join-Path (Get-Location) $OutFile
if (Test-Path $script:out) { Remove-Item $script:out -Force }
"# Project tree for $((Resolve-Path $Root).ProviderPath)" | Out-File $script:out -Encoding utf8
"Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $script:out -Append -Encoding utf8
'' | Out-File $script:out -Append -Encoding utf8
Add-Content -Path $script:out -Value '```'

Push-Location $Root
try {
  Write-Tree -Path (Get-Location).Path -Prefix ""
} finally {
  Pop-Location
}

Add-Content -Path $script:out -Value '```'
Write-Host "Wrote $script:out"