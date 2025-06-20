Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Ensure Python is installed before this is run
try {
    $versionOutput = python -V 2>&1
    Write-Host "Python found: $versionOutput"
} catch {
    Write-Host "Python is not installed or not in PATH. Exiting." -ForegroundColor Red
    exit 1
}

$venvPath = ".\.venv"
$mutexFile = ".setup.lock"

# Only do setup if mutex file doesn't exist
if (!(Test-Path $mutexFile)) {
    Write-Host "Performing initial setup..."

    # Create virtual environment if not present
    if (!(Test-Path -Path $venvPath)) {
        python -m venv $venvPath
    }

    # Activate virtual environment
    & "$venvPath\Scripts\Activate.ps1"

    # Install required packages
    pip install --upgrade pip
    pip install -r requirements.txt

    # Create mutex file to skip future setup
    New-Item -Path $mutexFile -ItemType File -Force | Out-Null
} else {
    Write-Host "Setup already done. Skipping to execution..."
    & "$venvPath\Scripts\Activate.ps1"
}

# Specify the path to the Python script
$pythonScript = "sigicom_noise_uploader.py"

# Start the Python script and wait for it to complete
$process = Start-Process python.exe -ArgumentList $pythonScript -Wait -PassThru

# Check the exit code
if ($process.ExitCode -eq 0) {
    Write-Host "Python script finished successfully."
} else {
    Write-Host "Python script failed. Check Logs."
    Write-Host "ERROR"
    Start-Sleep -Seconds 20
}
