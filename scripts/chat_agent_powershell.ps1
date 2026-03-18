# Interactive chat with CDSS AI assistance (POST /agent).
# Run the local API first, then run this script to have a conversation.
#
# Usage (from repo root in PowerShell):
#   # Terminal 1: start API
#   $env:PYTHONPATH = "src"; python scripts/run_api_local.py
#
#   # Terminal 2: chat (default http://localhost:8080)
#   .\scripts\chat_agent_powershell.ps1
#
#   # Or if API is on another port:
#   $env:BASE_URL = "http://localhost:8081"; .\scripts\chat_agent_powershell.ps1
#
# Type a message and press Enter. Empty line to exit.

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL.TrimEnd('/') } else { "http://localhost:8080" }
$agentUrl = "$baseUrl/agent"

Write-Host "CDSS AI Assistant — sending to: $agentUrl"
Write-Host "Type a message and press Enter. Empty line to exit."
Write-Host ("-" * 60)

while ($true) {
    $input = Read-Host "You"
    if ([string]::IsNullOrWhiteSpace($input)) {
        Write-Host "Bye."
        break
    }

    try {
        $body = @{ message = $input } | ConvertTo-Json
        $response = Invoke-RestMethod -Uri $agentUrl -Method Post -Body $body -ContentType "application/json" -TimeoutSec 60
    } catch {
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $reader.BaseStream.Position = 0
            $errBody = $reader.ReadToEnd()
            try {
                $errJson = $errBody | ConvertFrom-Json
                Write-Host "Error:" $errJson.error -ForegroundColor Red
            } else {
                Write-Host "Error:" $errBody -ForegroundColor Red
            }
        } else {
            Write-Host "Error: Cannot reach agent server." $_.Exception.Message -ForegroundColor Red
            Write-Host "  Start API with: `$env:PYTHONPATH = 'src'; python scripts/run_api_local.py"
        }
        continue
    }

    # Unwrap Lambda-style response (body as string) when present; otherwise response is the payload (local API)
    $data = $response
    if ($response.statusCode -ne $null) {
        if ($response.body) {
            if ($response.body -is [string]) {
                $data = $response.body | ConvertFrom-Json
            } else {
                $data = $response.body
            }
        }
        if ($response.statusCode -ne 200) {
            $errMsg = if ($data.error) { $data.error } else { $data }
            Write-Host "Error:" $errMsg -ForegroundColor Red
            continue
        }
    }

    $intent = $data.intent
    $payload = $data.data
    if (-not $payload -and $data.PSObject.Properties['data']) { $payload = $data.data }
    $reply = if ($payload -and $payload.reply) { $payload.reply } else { $null }
    $disclaimer = $data.safety_disclaimer
    $source = $data.source
    $durationMs = $data.duration_ms

    if ($intent) { Write-Host "[$intent] " -NoNewline }
    if ($reply) {
        Write-Host $reply
    } elseif ($payload) {
        Write-Host ($payload | ConvertTo-Json -Depth 5)
    } else {
        Write-Host "(No reply text)"
    }
    if ($disclaimer) { Write-Host "  — $disclaimer" -ForegroundColor DarkGray }
    if ($source -or $durationMs) { Write-Host "  (source=$source, $durationMs ms)" -ForegroundColor DarkGray }
    Write-Host ""
}
