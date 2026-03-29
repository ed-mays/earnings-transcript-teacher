#Requires -Version 5.1
# setup.ps1 — one-time setup for Earnings Transcript Teacher (Windows)
# Run from the repo root: .\setup.ps1
#
# Prerequisites (must be installed manually before running this script):
#   - Python 3.10+     https://www.python.org/downloads/
#                      Check "Add Python to PATH" during installation.
#   - Docker Desktop   https://www.docker.com/products/docker-desktop/
#
# The database runs in Docker using the official pgvector image,
# so there is no need to install PostgreSQL or pgvector separately.

$ErrorActionPreference = "Stop"

$CONTAINER = "earnings_teacher_db"
$DB_NAME   = "earnings_teacher"
$DB_USER   = "postgres"
$DB_PASS   = "postgres"
$DB_PORT   = "5432"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Ok($msg)   { Write-Host "  " -NoNewline; Write-Host "[OK]" -ForegroundColor Green -NoNewline; Write-Host "  $msg" }
function Warn($msg) { Write-Host "  " -NoNewline; Write-Host " [!]" -ForegroundColor Yellow -NoNewline; Write-Host "  $msg" }
function Fail($msg) { Write-Host "`n  " -NoNewline; Write-Host " [X]" -ForegroundColor Red -NoNewline; Write-Host "  $msg`n"; exit 1 }
function Step($msg) { Write-Host "`n$msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host " Earnings Transcript Teacher - Setup (Windows)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# ── 1. Python 3.10+ ───────────────────────────────────────────────────────────
Step "Checking prerequisites..."

$pythonCmd = $null
foreach ($cmd in @("python", "py", "python3")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $pythonCmd = $cmd
        break
    }
}
if (-not $pythonCmd) {
    Fail "Python not found.`n`n       Install Python 3.10+ from: https://www.python.org/downloads/`n       During installation, check 'Add Python to PATH'."
}

$pyVersion = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
$parts = $pyVersion.Split('.')
if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 10)) {
    Fail "Python 3.10+ required (found $pyVersion).`n       Install from: https://www.python.org/downloads/"
}
Ok "Python $pyVersion"

# ── 2. Docker ─────────────────────────────────────────────────────────────────
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "Docker not found.`n`n       Install Docker Desktop: https://www.docker.com/products/docker-desktop/`n       After installing, start Docker Desktop and re-run this script."
}

docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Fail "Docker is installed but not running.`n       Start Docker Desktop and re-run this script."
}
Ok "Docker Desktop running"

# ── 3. Virtual environment ────────────────────────────────────────────────────
Step "Setting up Python environment..."

if (-not (Test-Path ".venv")) {
    & $pythonCmd -m venv .venv
    Ok "Created .venv"
} else {
    Ok "Virtual environment already exists"
}

# ── 4. Python dependencies ────────────────────────────────────────────────────
Write-Host ""
Write-Host "  Installing dependencies (this may take a minute)..."
& .venv\Scripts\pip install --quiet --upgrade pip
& .venv\Scripts\pip install --quiet -r requirements.txt
Ok "Dependencies installed"

# ── 5. Database container ─────────────────────────────────────────────────────
Step "Setting up database..."

$existing = docker ps -a --filter "name=^${CONTAINER}$" --format "{{.Names}}" 2>$null
if ($existing -eq $CONTAINER) {
    $running = docker ps --filter "name=^${CONTAINER}$" --format "{{.Names}}" 2>$null
    if ($running -ne $CONTAINER) {
        docker start $CONTAINER | Out-Null
        Ok "Started existing container '$CONTAINER'"
    } else {
        Ok "Container '$CONTAINER' already running"
    }
} else {
    docker run -d `
        --name $CONTAINER `
        -p "${DB_PORT}:5432" `
        -e POSTGRES_PASSWORD=$DB_PASS `
        pgvector/pgvector:pg16 | Out-Null
    Ok "Started new container '$CONTAINER' (pgvector/pgvector:pg16)"
}

# Wait for Postgres to accept connections
Write-Host "  Waiting for Postgres..." -NoNewline
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    docker exec $CONTAINER pg_isready -U $DB_USER 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 1
}
Write-Host ""
if (-not $ready) {
    Fail "Postgres did not become ready in time.`n       Check logs with: docker logs $CONTAINER"
}
Ok "Postgres ready"

# ── 6. Create database ────────────────────────────────────────────────────────
$dbExists = docker exec $CONTAINER psql -U $DB_USER -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>$null
if ($dbExists -eq "1") {
    Ok "Database '$DB_NAME' already exists"
} else {
    docker exec $CONTAINER createdb -U $DB_USER $DB_NAME | Out-Null
    Ok "Created database '$DB_NAME'"
}

# ── 7. Schema ─────────────────────────────────────────────────────────────────
$tableExists = docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -tAc `
    "SELECT EXISTS(SELECT FROM pg_tables WHERE schemaname='public' AND tablename='calls')" 2>$null

if ($tableExists -eq "f") {
    docker exec $CONTAINER python migrate.py | Out-Null
    Ok "Database schema applied"
} else {
    Ok "Schema already applied - skipping"
}

# ── 8. Environment variables ──────────────────────────────────────────────────
Step "Checking environment variables..."

if (Test-Path "set_env.ps1") {
    Ok "set_env.ps1 already exists"
} else {
    Copy-Item "set_env.ps1.template" "set_env.ps1"
    Warn "Created set_env.ps1 from template - fill in your API keys before running the app"
    Write-Host ""
    Write-Host "  Open set_env.ps1 and replace the placeholder values:"
    Write-Host ""
    Write-Host "    API_NINJAS_KEY      - transcript downloads  (api-ninjas.com)"
    Write-Host "    VOYAGE_API_KEY      - semantic embeddings   (voyageai.com)"
    Write-Host "    PERPLEXITY_API_KEY  - Feynman chat          (perplexity.ai)"
    Write-Host "    ANTHROPIC_API_KEY   - LLM-based ingestion   (console.anthropic.com)"
    Write-Host ""
    Write-Host "  The DATABASE_URL in set_env.ps1 is already set to point at the Docker"
    Write-Host "  container and does not need to be changed."
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host " Setup complete!" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  To get started:"
Write-Host ""
Write-Host "    .venv\Scripts\Activate.ps1"
Write-Host "    . .\set_env.ps1"
Write-Host "    python main.py AAPL --save    # ingest a transcript"
Write-Host "    streamlit run app.py          # launch the web UI"
Write-Host ""
Write-Host "  The database runs in Docker. To stop it when not in use:"
Write-Host "    docker stop $CONTAINER"
Write-Host "  To start it again later:"
Write-Host "    docker start $CONTAINER"
Write-Host ""
