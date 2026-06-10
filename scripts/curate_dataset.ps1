param(
    [string]$SourceDir = "G:\Copiya\dataset",
    [string]$OutputRoot = "G:\Copiya\VKR_Module_Project\data\dataset_curated",
    [double]$TrainRatio = 0.8,
    [double]$ValRatio = 0.1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceDir)) {
    throw "Source directory not found: $SourceDir"
}

$audioDir = Join-Path $OutputRoot "audio"
$duplicatesDir = Join-Path $OutputRoot "duplicates"
New-Item -ItemType Directory -Force -Path $audioDir | Out-Null
New-Item -ItemType Directory -Force -Path $duplicatesDir | Out-Null

Get-ChildItem -LiteralPath $audioDir -File | Remove-Item -Force
Get-ChildItem -LiteralPath $duplicatesDir -File | Remove-Item -Force

$shell = New-Object -ComObject Shell.Application
$shellFolder = $shell.Namespace($SourceDir)

function Get-VoiceMeta {
    param([string]$FileName)

    if ($FileName -match '^speechma_audio_([^_]+)') {
        $voice = $matches[1]
        return @{
            source = "speechma"
            voice = $voice
        }
    }

    if ($FileName -match '^luvvoice') {
        return @{
            source = "luvvoice"
            voice = "unknown"
        }
    }

    return @{
        source = "unknown"
        voice = "unknown"
    }
}

$files = Get-ChildItem -LiteralPath $SourceDir -File | Where-Object { $_.Extension -ieq ".mp3" } | Sort-Object Name
$uniqueRows = New-Object System.Collections.Generic.List[object]
$duplicateRows = New-Object System.Collections.Generic.List[object]
$seenHashes = @{}

foreach ($file in $files) {
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    $duration = $shellFolder.GetDetailsOf($shellFolder.ParseName($file.Name), 27)
    $meta = Get-VoiceMeta -FileName $file.Name

    if ($seenHashes.ContainsKey($hash)) {
        $dupIndex = $duplicateRows.Count + 1
        $dupName = "dup_{0:d4}_{1}" -f $dupIndex, $file.Name
        $dupPath = Join-Path $duplicatesDir $dupName
        Copy-Item -LiteralPath $file.FullName -Destination $dupPath -Force

        $duplicateRows.Add([PSCustomObject]@{
            duplicate_id = "dup_{0:d4}" -f $dupIndex
            original_name = $file.Name
            duplicate_path = "data/dataset_curated/duplicates/$($file.Name)"
            hash = $hash
            duplicate_of = $seenHashes[$hash].id
            source = $meta.source
            voice = $meta.voice
            duration = $duration
        })
        continue
    }

    $index = $uniqueRows.Count + 1
    $newName = "cmd_{0:d4}{1}" -f $index, $file.Extension.ToLowerInvariant()
    $newPath = Join-Path $audioDir $newName
    Copy-Item -LiteralPath $file.FullName -Destination $newPath -Force

    $row = [PSCustomObject]@{
        id = "cmd_{0:d4}" -f $index
        split = ""
        audio_path = "data/dataset_curated/audio/$newName"
        original_name = $file.Name
        source = $meta.source
        voice = $meta.voice
        language = "ru"
        transcript_asr = ""
        text = ""
        intent = ""
        canonical_text = ""
        hash = $hash
        duration = $duration
    }

    $uniqueRows.Add($row)
    $seenHashes[$hash] = $row
}

$trainCount = [int][math]::Floor($uniqueRows.Count * $TrainRatio)
$valCount = [int][math]::Floor($uniqueRows.Count * $ValRatio)
$testCount = $uniqueRows.Count - $trainCount - $valCount

for ($i = 0; $i -lt $uniqueRows.Count; $i++) {
    if ($i -lt $trainCount) {
        $uniqueRows[$i].split = "train"
    }
    elseif ($i -lt ($trainCount + $valCount)) {
        $uniqueRows[$i].split = "val"
    }
    else {
        $uniqueRows[$i].split = "test"
    }
}

$manifestJsonl = Join-Path $OutputRoot "dataset_manifest.jsonl"
$manifestCsv = Join-Path $OutputRoot "dataset_manifest.csv"
$duplicatesJsonl = Join-Path $OutputRoot "duplicates_manifest.jsonl"
$summaryJson = Join-Path $OutputRoot "summary.json"

if (Test-Path -LiteralPath $manifestJsonl) { Remove-Item -LiteralPath $manifestJsonl -Force }
if (Test-Path -LiteralPath $duplicatesJsonl) { Remove-Item -LiteralPath $duplicatesJsonl -Force }

foreach ($row in $uniqueRows) {
    Add-Content -LiteralPath $manifestJsonl -Value ($row | ConvertTo-Json -Compress -Depth 4) -Encoding UTF8
}

foreach ($row in $duplicateRows) {
    Add-Content -LiteralPath $duplicatesJsonl -Value ($row | ConvertTo-Json -Compress -Depth 4) -Encoding UTF8
}

$uniqueRows | Export-Csv -LiteralPath $manifestCsv -NoTypeInformation -Encoding UTF8

$summary = [PSCustomObject]@{
    source_dir = [System.IO.Path]::GetFullPath($SourceDir)
    output_root = [System.IO.Path]::GetFullPath($OutputRoot)
    original_files = $files.Count
    unique_files = $uniqueRows.Count
    duplicate_files = $duplicateRows.Count
    split_counts = @{
        train = ($uniqueRows | Where-Object { $_.split -eq "train" }).Count
        val = ($uniqueRows | Where-Object { $_.split -eq "val" }).Count
        test = ($uniqueRows | Where-Object { $_.split -eq "test" }).Count
    }
    voices = @($uniqueRows | Group-Object voice | Sort-Object Count -Descending | ForEach-Object {
        [PSCustomObject]@{
            voice = $_.Name
            count = $_.Count
        }
    })
    sources = @($uniqueRows | Group-Object source | Sort-Object Count -Descending | ForEach-Object {
        [PSCustomObject]@{
            source = $_.Name
            count = $_.Count
        }
    })
}

$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
Write-Output ($summary | ConvertTo-Json -Depth 6)
