param(
    [string]$Repository = "saitatter/thumbforge-krita-plugin"
)

$ErrorActionPreference = "Stop"

$body = @{
    required_status_checks = @{
        strict = $true
        contexts = @("test")
    }
    enforce_admins = $false
    required_pull_request_reviews = @{
        required_approving_review_count = 1
        dismiss_stale_reviews = $true
    }
    restrictions = $null
    required_linear_history = $true
    allow_force_pushes = $false
    allow_deletions = $false
} | ConvertTo-Json -Depth 8

$tmp = New-TemporaryFile
try {
    Set-Content -LiteralPath $tmp -Value $body -Encoding UTF8
    gh api `
        --method PUT `
        -H "Accept: application/vnd.github+json" `
        -H "X-GitHub-Api-Version: 2022-11-28" `
        "/repos/$Repository/branches/main/protection" `
        --input $tmp
}
finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

Write-Host "Protected main branch for $Repository"
