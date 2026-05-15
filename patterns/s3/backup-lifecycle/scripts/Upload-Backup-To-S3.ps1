<#
.SYNOPSIS
    Generic S3 Backup Upload Script with Retention Tagging

.DESCRIPTION
    Automates backup file uploads to S3 with intelligent retention tagging.

    Features:
    - Automatic weekly vs monthly detection (first week of month = monthly)
    - S3 object tagging for lifecycle policy differentiation
    - Local file cleanup after successful upload
    - CloudWatch metrics for monitoring
    - Detailed logging with error handling

    Designed for use with CloudFormation lifecycle policies (backup-lifecycle-stack.yaml)

.PARAMETER BackupPath
    Local directory containing backup files (default: I:\Backup)

.PARAMETER S3Bucket
    Target S3 bucket (default: s3://mh-edw-backup)

.PARAMETER FilePattern
    File pattern to match (default: *.bak)

.PARAMETER LookbackHours
    How far back to search for recent backups (default: 48 hours)

.PARAMETER MetricNamespace
    CloudWatch metric namespace (default: Backups)

.PARAMETER MetricDimension
    CloudWatch dimension name for server identification (default: hostname)

.EXAMPLE
    # EDW SQL Server backups
    .\Upload-Backup-To-S3.ps1 -BackupPath "I:\Backup" -S3Bucket "s3://mh-edw-backup" -FilePattern "*.bak"

.EXAMPLE
    # RDS automated backups export
    .\Upload-Backup-To-S3.ps1 -BackupPath "D:\RDSExport" -S3Bucket "s3://mh-rds-backups" -FilePattern "*.sql"

.NOTES
    Version: 1.0
    Author: Platform Engineering
    Requires: AWS CLI v2+, Windows Event Log source registration

    Git Repository: https://github.com/MH-PlatformDigitalTools/infrastructure
    Related: backup-lifecycle-stack.yaml, governance.md
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$BackupPath = "I:\Backup",

    [Parameter(Mandatory=$false)]
    [string]$S3Bucket = "s3://mh-edw-backup",

    [Parameter(Mandatory=$false)]
    [string]$FilePattern = "*.bak",

    [Parameter(Mandatory=$false)]
    [int]$LookbackHours = 48,

    [Parameter(Mandatory=$false)]
    [string]$LogPath = "C:\Scripts\Logs",

    [Parameter(Mandatory=$false)]
    [string]$MetricNamespace = "Backups",

    [Parameter(Mandatory=$false)]
    [string]$MetricDimension = $env:COMPUTERNAME,

    [Parameter(Mandatory=$false)]
    [switch]$WhatIf
)

# Initialize logging
if (-not (Test-Path $LogPath)) {
    New-Item -Path $LogPath -ItemType Directory -Force | Out-Null
}

$LogFile = Join-Path $LogPath "backup-upload-$(Get-Date -Format 'yyyy-MM-dd').log"
$dayOfMonth = (Get-Date).Day
$currentDate = Get-Date

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('INFO', 'WARN', 'ERROR', 'SUCCESS')]
        [string]$Level = 'INFO'
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "$timestamp [$Level] $Message"

    # Write to log file
    $logEntry | Out-File -FilePath $LogFile -Append -Encoding UTF8

    # Write to console with color
    switch ($Level) {
        'ERROR'   { Write-Host $logEntry -ForegroundColor Red }
        'WARN'    { Write-Host $logEntry -ForegroundColor Yellow }
        'SUCCESS' { Write-Host $logEntry -ForegroundColor Green }
        default   { Write-Host $logEntry }
    }
}

function Send-CloudWatchMetric {
    param(
        [string]$MetricName,
        [double]$Value,
        [string]$Unit = 'Count'
    )

    try {
        $timestamp = (Get-Date).ToUniversalTime().ToString("o")

        aws cloudwatch put-metric-data `
            --namespace "$MetricNamespace" `
            --metric-name "$MetricName" `
            --value $Value `
            --unit $Unit `
            --dimensions "Server=$MetricDimension" `
            --timestamp $timestamp `
            --no-cli-pager 2>&1 | Out-Null

        Write-Log "CloudWatch metric sent: $MetricName = $Value" -Level INFO
    } catch {
        Write-Log "CloudWatch metric failed (non-critical): $($_.Exception.Message)" -Level WARN
    }
}

function Get-FileSizeGB {
    param([System.IO.FileInfo]$File)
    return [math]::Round($File.Length / 1GB, 2)
}

function Test-S3Bucket {
    param([string]$Bucket)

    $bucketName = $Bucket -replace '^s3://', ''
    try {
        aws s3 ls "s3://$bucketName" --max-items 1 2>&1 | Out-Null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

# ============================================================================
# Main Script
# ============================================================================

Write-Log "========================================" -Level INFO
Write-Log "S3 Backup Upload Script Started" -Level INFO
Write-Log "========================================" -Level INFO
Write-Log "Server: $MetricDimension" -Level INFO
Write-Log "Backup Path: $BackupPath" -Level INFO
Write-Log "S3 Bucket: $S3Bucket" -Level INFO
Write-Log "File Pattern: $FilePattern" -Level INFO
Write-Log "Lookback: $LookbackHours hours" -Level INFO
Write-Log "Day of Month: $dayOfMonth" -Level INFO

if ($WhatIf) {
    Write-Log "WhatIf mode: No files will be uploaded or deleted" -Level WARN
}

# Validate prerequisites
if (-not (Test-Path $BackupPath)) {
    Write-Log "ERROR: Backup path does not exist: $BackupPath" -Level ERROR
    Send-CloudWatchMetric -MetricName "UploadErrors" -Value 1
    exit 1
}

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Log "ERROR: AWS CLI not found. Install AWS CLI v2 first." -Level ERROR
    exit 1
}

if (-not (Test-S3Bucket -Bucket $S3Bucket)) {
    Write-Log "ERROR: Cannot access S3 bucket: $S3Bucket" -Level ERROR
    Write-Log "Check AWS credentials and bucket permissions" -Level ERROR
    Send-CloudWatchMetric -MetricName "UploadErrors" -Value 1
    exit 1
}

# Determine retention type
$isMonthlyBackup = $dayOfMonth -le 7

if ($isMonthlyBackup) {
    Write-Log "*** MONTHLY BACKUP DETECTED (first week of month) ***" -Level WARN
    Write-Log "Files will be tagged for 13-month retention (Glacier)" -Level WARN
    $retentionTag = "Retention=Monthly"
} else {
    Write-Log "Weekly backup - 90-day retention" -Level INFO
    $retentionTag = "Retention=Weekly"
}

# Find recent backup files
Write-Log "Searching for backup files..." -Level INFO
$cutoffTime = $currentDate.AddHours(-$LookbackHours)

try {
    $backupFiles = Get-ChildItem -Path (Join-Path $BackupPath $FilePattern) -File -ErrorAction Stop |
        Where-Object { $_.LastWriteTime -gt $cutoffTime } |
        Sort-Object LastWriteTime -Descending
} catch {
    Write-Log "ERROR: Failed to read backup directory: $($_.Exception.Message)" -Level ERROR
    Send-CloudWatchMetric -MetricName "UploadErrors" -Value 1
    exit 1
}

if ($backupFiles.Count -eq 0) {
    Write-Log "ERROR: No backup files found in last $LookbackHours hours" -Level ERROR
    Write-Log "Expected pattern: $FilePattern in $BackupPath" -Level ERROR
    Send-CloudWatchMetric -MetricName "UploadErrors" -Value 1
    exit 1
}

Write-Log "Found $($backupFiles.Count) backup file(s) to process" -Level SUCCESS

# Upload files
$successCount = 0
$failCount = 0
$totalSizeGB = 0

foreach ($file in $backupFiles) {
    $fileSizeGB = Get-FileSizeGB -File $file
    $totalSizeGB += $fileSizeGB

    Write-Log "----------------------------------------" -Level INFO
    Write-Log "Processing: $($file.Name)" -Level INFO
    Write-Log "  Size: $fileSizeGB GB" -Level INFO
    Write-Log "  Modified: $($file.LastWriteTime)" -Level INFO
    Write-Log "  Tag: $retentionTag" -Level INFO

    if ($WhatIf) {
        Write-Log "  [WhatIf] Would upload to: $S3Bucket/$($file.Name)" -Level WARN
        $successCount++
        continue
    }

    # Upload to S3
    $s3Key = "$S3Bucket/$($file.Name)"
    $uploadStartTime = Get-Date

    try {
        Write-Log "  Uploading to S3..." -Level INFO

        $uploadOutput = aws s3 cp `
            $file.FullName `
            $s3Key `
            --storage-class STANDARD `
            --tagging $retentionTag `
            2>&1

        if ($LASTEXITCODE -eq 0) {
            $uploadDuration = ((Get-Date) - $uploadStartTime).TotalSeconds
            Write-Log "  Upload completed in $([math]::Round($uploadDuration, 1)) seconds" -Level SUCCESS

            # Verify in S3
            $verifyOutput = aws s3 ls $s3Key 2>&1

            if ($LASTEXITCODE -eq 0) {
                Write-Log "  Verified in S3" -Level SUCCESS

                # Delete local file
                try {
                    Remove-Item -Path $file.FullName -Force -ErrorAction Stop
                    Write-Log "  Deleted local copy" -Level SUCCESS
                    $successCount++

                    # Send success metrics
                    Send-CloudWatchMetric -MetricName "FilesUploaded" -Value 1
                    Send-CloudWatchMetric -MetricName "BytesUploaded" -Value $file.Length -Unit Bytes

                } catch {
                    Write-Log "  WARNING: Upload succeeded but failed to delete local file: $($_.Exception.Message)" -Level WARN
                    $successCount++
                }
            } else {
                Write-Log "  ERROR: Upload succeeded but verification failed" -Level ERROR
                Write-Log "  Keeping local copy for safety" -Level WARN
                $failCount++
            }
        } else {
            Write-Log "  ERROR: Upload failed (exit code: $LASTEXITCODE)" -Level ERROR
            Write-Log "  AWS Output: $uploadOutput" -Level ERROR
            $failCount++
            Send-CloudWatchMetric -MetricName "UploadErrors" -Value 1
        }

    } catch {
        Write-Log "  ERROR: Upload exception: $($_.Exception.Message)" -Level ERROR
        $failCount++
        Send-CloudWatchMetric -MetricName "UploadErrors" -Value 1
    }
}

# Summary
Write-Log "========================================" -Level INFO
Write-Log "Upload Complete" -Level INFO
Write-Log "========================================" -Level INFO
Write-Log "Total Files: $($backupFiles.Count)" -Level INFO
Write-Log "Successful: $successCount" -Level SUCCESS
Write-Log "Failed: $failCount" -Level $(if ($failCount -gt 0) { "ERROR" } else { "INFO" })
Write-Log "Total Size: $([math]::Round($totalSizeGB, 2)) GB" -Level INFO
Write-Log "Retention: $(if ($isMonthlyBackup) { '13 months (Monthly)' } else { '90 days (Weekly)' })" -Level INFO

# Final status
if ($failCount -gt 0) {
    Write-Log "Script completed with errors" -Level ERROR
    exit 1
} elseif ($successCount -eq 0 -and -not $WhatIf) {
    Write-Log "Script completed but no files were uploaded" -Level WARN
    exit 1
} else {
    Write-Log "Script completed successfully" -Level SUCCESS
    exit 0
}
