# dev-start.ps1 - one-shot post-reboot startup for sdc-multi-agent on Windows.
#
# What this fixes
# ---------------
# ollama/ollama:latest is 6.3 GB. With the default imagePullPolicy: Always,
# every pod restart re-pulls 6.3 GB from Docker Hub, which can wedge
# cri-dockerd and leave Ollama stuck in PodInitializing for 30+ minutes.
#
# The fix (already baked into k8s/ollama/deployment.yaml):
#   image: ollama/ollama:cached-local
#   imagePullPolicy: Never
#
# This script ensures the :cached-local tag exists inside minikube's docker
# daemon, then starts everything else. Idempotent - safe to run any time.
#
# Note: ASCII-only by design. Windows PowerShell 5.1 reads scripts as cp1252
# when there is no BOM, so unicode dashes/box characters break the parser.

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Write-Host "Project root: $ProjectRoot" -ForegroundColor Cyan

# 1. Ensure minikube is running
Write-Host "`n[1/5] Checking minikube status..." -ForegroundColor Cyan
$mkStatus = (minikube status --format '{{.Host}}' 2>$null)
if ($mkStatus -ne 'Running') {
    Write-Host "  minikube not running -- starting (this may take a minute)..." -ForegroundColor Yellow
    minikube start --cpus=6 --memory=12g --driver=docker
} else {
    Write-Host "  minikube already running." -ForegroundColor Green
}

# 2. Ensure ollama/ollama:cached-local tag exists
Write-Host "`n[2/5] Ensuring ollama/ollama:cached-local tag exists..." -ForegroundColor Cyan
$cachedExists = (minikube ssh "docker images ollama/ollama:cached-local --format '{{.ID}}' 2>/dev/null").Trim()
if (-not $cachedExists) {
    Write-Host "  cached-local tag missing -- checking for :latest..." -ForegroundColor Yellow
    $latestExists = (minikube ssh "docker images ollama/ollama:latest --format '{{.ID}}' 2>/dev/null").Trim()
    if (-not $latestExists) {
        Write-Host "  :latest also missing -- pulling from Docker Hub (~6 GB, one-time)..." -ForegroundColor Yellow
        minikube ssh "docker pull ollama/ollama:latest"
    }
    minikube ssh "docker tag ollama/ollama:latest ollama/ollama:cached-local"
    Write-Host "  tagged ollama/ollama:cached-local." -ForegroundColor Green
} else {
    Write-Host "  cached-local tag present (image $cachedExists)." -ForegroundColor Green
}

# 3. Apply manifests
Write-Host "`n[3/5] Applying manifests..." -ForegroundColor Cyan
kubectl apply -f "$ProjectRoot\k8s\namespace.yaml"
kubectl apply -f "$ProjectRoot\k8s\configmap.yaml"
kubectl apply -f "$ProjectRoot\k8s\ollama\"
kubectl apply -f "$ProjectRoot\k8s\chromadb\"
kubectl apply -f "$ProjectRoot\k8s\redis\"
kubectl apply -f "$ProjectRoot\k8s\sdc-agents\"

# 4. Wait for pods to be Ready
Write-Host "`n[4/5] Waiting for core pods to be Ready..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=ollama     -n sdc --timeout=120s
kubectl wait --for=condition=ready pod -l app=chromadb   -n sdc --timeout=60s
kubectl wait --for=condition=ready pod -l app=redis      -n sdc --timeout=30s
kubectl wait --for=condition=ready pod -l app=sdc-agents -n sdc --timeout=180s
Write-Host "  All pods Ready." -ForegroundColor Green

# 5. Start port-forwards in background
Write-Host "`n[5/5] Starting port-forwards..." -ForegroundColor Cyan
foreach ($port in 8000, 11434, 8001, 6379) {
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object {
            $proc = Get-Process -Id $_ -ErrorAction SilentlyContinue
            if ($proc -and $proc.Name -match 'kubectl') {
                Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
            }
        }
}

$logDir = "$env:TEMP\sdc-pf"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$forwards = @(
    @{svc='sdc-agents'; local=8000;  remote=8000},
    @{svc='ollama';     local=11434; remote=11434},
    @{svc='chromadb';   local=8001;  remote=8000},
    @{svc='redis';      local=6379;  remote=6379}
)
foreach ($f in $forwards) {
    Start-Process -NoNewWindow -FilePath 'kubectl' `
        -ArgumentList 'port-forward', '-n', 'sdc', "svc/$($f.svc)", "$($f.local):$($f.remote)" `
        -RedirectStandardOutput "$logDir\$($f.svc).log" `
        -RedirectStandardError  "$logDir\$($f.svc).err" | Out-Null
    Write-Host "  $($f.svc): localhost:$($f.local)" -ForegroundColor Green
}

Start-Sleep -Seconds 3
Write-Host "`n=== READY ===" -ForegroundColor Green
Write-Host "Operator Console: http://localhost:8000/console/"
Write-Host "Legacy chat UI:   http://localhost:8000/"
Write-Host "Ollama API:       http://localhost:11434"
Write-Host "ChromaDB API:     http://localhost:8001"
Write-Host "Redis:            redis://localhost:6379"
Write-Host ""
Write-Host "To open LangGraph Studio (visual graph view):"
Write-Host "  uvx --from 'langgraph-cli[inmem]' --with typing-extensions ``"
Write-Host "      --with-requirements requirements.txt --env-file .env.langgraph ``"
Write-Host "      langgraph dev"
