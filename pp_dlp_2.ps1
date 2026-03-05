# 1) 安裝模組
Install-Module -Name Microsoft.PowerApps.Administration.PowerShell

# 2) 登入
Add-PowerAppsAccount

# 3) 撈所有 app 的 connector references
$apps = Get-AdminPowerApp
foreach ($app in $apps) {
    $connectors = $app.Internal.properties.connectionReferences.PSObject.Properties |
        Select-Object -ExpandProperty Value |
        Select-Object -Property connectorName, id
    
    # 輸出 app 名稱 + 所有 connectors
    [PSCustomObject]@{
        AppName    = $app.Internal.properties.displayName
        Environment = $app.EnvironmentName
        Connectors = ($connectors.connectorName -join ", ")
    }
}