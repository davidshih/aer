Install-Module Microsoft.PowerApps.Administration.PowerShell -Scope CurrentUser
Add-PowerAppsAccount

$policies = Get-AdminDlpPolicy
$result = @()

foreach ($p in $policies) {
    $detail = Get-AdminDlpPolicy -PolicyName $p.PolicyName


    $raw = $null
    if ($detail.PSObject.Properties.Name -contains "Internal") {
        $raw = $detail.Internal.Content
    }

    if ($raw) {
        $j = $raw | ConvertFrom-Json
        $def = $j.properties.definition

   
        $business = @($def.apiGroups.hbi.apis | ForEach-Object { $_.name })
        $nonbiz   = @($def.apiGroups.lbi.apis | ForEach-Object { $_.name })
        $blocked  = @($def.apiGroups.blocked.apis | ForEach-Object { $_.name })

        $defaultGroup = $def.defaultApiGroup
    } else {

        $business = @()
        $nonbiz   = @()
        $blocked  = @()
        $defaultGroup = ""
    }

    $result += [pscustomobject]@{
        PolicyName    = $detail.displayName
        PolicyId      = $p.PolicyName
        DefaultGroup  = $defaultGroup
        BusinessCount = $business.Count
        NonBizCount   = $nonbiz.Count
        BlockedCount  = $blocked.Count
    }
}

$result | Export-Csv .\dlp_policies_summary.csv -NoTypeInformation -Encoding UTF8