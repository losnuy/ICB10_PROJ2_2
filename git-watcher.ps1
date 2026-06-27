# git-watcher.ps1

# 파일 변경을 실시간으로 감지하여 자동으로 Git add, commit, push를 수행하는 스크립트입니다.

param(
    [switch]$StartBackground,
    [switch]$StopBackground,
    [switch]$Status
)

# 스크립트 작업 경로 지정
$workDir = $PSScriptRoot

if (-not $workDir) { $workDir = Get-Location }

# 상태 확인 기능
if ($Status) {
    $job = Get-Job -Name "git-watcher-job" -ErrorAction SilentlyContinue
    if ($job -and $job.State -eq "Running") {
        Write-Host "git-watcher가 PowerShell Job으로 실행 중입니다."
        exit 0
    }
    Write-Host "git-watcher가 실행 중이 아닙니다."
    exit 0
}

# 백그라운드 감시자 종료 기능
if ($StopBackground) {
    $job = Get-Job -Name "git-watcher-job" -ErrorAction SilentlyContinue
    if ($job) {
        Stop-Job $job
        Remove-Job $job
        Write-Host "git-watcher Job이 중단되었습니다."
    } else {
        Write-Host "실행 중인 git-watcher Job을 찾을 수 없습니다."
    }
    exit 0
}

# 백그라운드 실행 기능
if ($StartBackground) {
    $job = Get-Job -Name "git-watcher-job" -ErrorAction SilentlyContinue
    if ($job -and $job.State -eq "Running") {
        Write-Host "git-watcher가 이미 실행 중입니다."
        exit 0
    }
    
    # Start-Job을 사용하여 백그라운드 작업 시작
    $scriptPath = $MyInvocation.MyCommand.Path
    Start-Job -ScriptBlock {
        param($path, $script)
        Set-Location $path
        . $script
    } -ArgumentList $workDir, $scriptPath -Name "git-watcher-job"
    
    Write-Host "git-watcher를 PowerShell Job 백그라운드에서 실행했습니다."
    exit 0
}

# 감시자 객체 생성
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $workDir
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

# 제외 필터 함수 (.git, .venv, .agents 등 변경 무시)
function Should-Ignore($filePath) {
    if ($filePath -match '\\\.git\\' -or 
        $filePath -match '\\\.venv\\' -or 
        $filePath -match '\\\.agents\\') {
        return $true
    }
    return $false
}

# 자동 커밋 & 푸시 동기화 함수
function Sync-Changes($action, $filePath) {
    if (Should-Ignore $filePath) { return }
    
    # 디바운싱: 파일 변경 직후 디스크 쓰기가 완료되기를 잠시 대기
    Start-Sleep -Seconds 3
    
    # git 변경사항 확인
    $status = git status --porcelain
    if ($status) {
        $fileName = Split-Path $filePath -Leaf
        Write-Host "[$action] $fileName 감지됨 -> Git 동기화 진행"
        git add -A
        $currentTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        
        # 자동 커밋 실행
        git commit -m "Auto-commit: $currentTime [$action] $fileName"
        git push
    }
}

# 파일 시스템 이벤트 등록
$onChange = Register-ObjectEvent $watcher "Changed" -Action {
    Sync-Changes "Modify" $Event.SourceEventArgs.FullPath
}
$onCreated = Register-ObjectEvent $watcher "Created" -Action {
    Sync-Changes "Create" $Event.SourceEventArgs.FullPath
}
$onDeleted = Register-ObjectEvent $watcher "Deleted" -Action {
    Sync-Changes "Delete" $Event.SourceEventArgs.FullPath
}
$onRenamed = Register-ObjectEvent $watcher "Renamed" -Action {
    Sync-Changes "Rename" $Event.SourceEventArgs.FullPath
}

# 루프를 돌며 이벤트 대기
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    # 리소스 정리
    $watcher.Dispose()
    Unregister-Event -SourceIdentifier $onChange.Name -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier $onCreated.Name -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier $onDeleted.Name -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier $onRenamed.Name -ErrorAction SilentlyContinue
}
