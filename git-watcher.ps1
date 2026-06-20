# git-watcher.ps1

# ?뚯씪 蹂寃쎌쓣 ?ㅼ떆媛꾩쑝濡?媛먯??섏뿬 ?먮룞?쇰줈 Git add, commit, push瑜??섑뻾?섎뒗 ?ㅽ겕由쏀듃?낅땲??

param(
    [switch]$StartBackground,
    [switch]$StopBackground,
    [switch]$Status
)

# ?ㅽ겕由쏀듃 ?묒뾽 寃쎈줈 吏??
$workDir = $PSScriptRoot

if (-not $workDir) { $workDir = Get-Location }

# ?곹깭 ?뺤씤 湲곕뒫

if ($Status) {
    $job = Get-Job -Name "git-watcher-job" -ErrorAction SilentlyContinue
    if ($job -and $job.State -eq "Running") {
        Write-Host "git-watcher is running as a PowerShell Job."
        exit 0
    }
    Write-Host "git-watcher is not running."
    exit 0
}

# 諛깃렇?쇱슫??媛먯떆??醫낅즺 湲곕뒫

if ($StopBackground) {
    $job = Get-Job -Name "git-watcher-job" -ErrorAction SilentlyContinue
    if ($job) {
        Stop-Job $job
        Remove-Job $job
        Write-Host "git-watcher Job stopped."
    } else {
        Write-Host "No active git-watcher Job found."
    }
    exit 0
}

# 諛깃렇?쇱슫???ㅽ뻾 湲곕뒫

if ($StartBackground) {
    $job = Get-Job -Name "git-watcher-job" -ErrorAction SilentlyContinue
    if ($job -and $job.State -eq "Running") {
        Write-Host "git-watcher is already running."
        exit 0
    }
    
    # Start-Job???쒖슜?섏뿬 諛깃렇?쇱슫???묒뾽 ?쒖옉
    
    $scriptPath = $MyInvocation.MyCommand.Path
    Start-Job -ScriptBlock {
        param($path, $script)
        Set-Location $path
        . $script
    } -ArgumentList $workDir, $scriptPath -Name "git-watcher-job"
    
    Write-Host "git-watcher started in background as a PowerShell Job."
    exit 0
}

# 媛먯떆??媛앹껜 ?앹꽦

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $workDir
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

# ?쒖쇅 ?꾪꽣 ?⑥닔 (.git, .venv, .agents ??蹂寃?臾댁떆)

function Should-Ignore($filePath) {
    if ($filePath -match '\\\.git\\' -or 
        $filePath -match '\\\.venv\\' -or 
        $filePath -match '\\\.agents\\') {
        return $true
    }
    return $false
}

# ?먮룞 而ㅻ컠 & ?몄떆 ?숆린???⑥닔

function Sync-Changes($action, $filePath) {
    if (Should-Ignore $filePath) { return }
    
    # ?붾컮?댁떛: ?뚯씪 蹂寃?吏곹썑 ?붿뒪???곌린媛 ?꾨즺?섍린瑜??좎떆 ?湲?    
    Start-Sleep -Seconds 3
    
    # git 蹂寃쎌궗???뺤씤
    
    $status = git status --porcelain
    if ($status) {
        $fileName = Split-Path $filePath -Leaf
        Write-Host "[$action] $fileName detected -> Syncing with Git"
        git add -A
        $currentTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        
        # ?먮룞 而ㅻ컠 ?ㅽ뻾
        
        git commit -m "Auto-commit: $currentTime [$action] $fileName"
        git push
    }
}

# ?뚯씪 ?쒖뒪???대깽???깅줉

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

# 猷⑦봽瑜??뚮ŉ ?대깽???湲?
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    # 由ъ냼???뺣━
    
    $watcher.Dispose()
    Unregister-Event -SourceIdentifier $onChange.Name -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier $onCreated.Name -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier $onDeleted.Name -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier $onRenamed.Name -ErrorAction SilentlyContinue
}
