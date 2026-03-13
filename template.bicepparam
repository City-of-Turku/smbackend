using 'template.bicep'

var prefix = readEnvironmentVariable('RESOURCE_PREFIX')
var sanitizedPrefix = replace(prefix, '-', '')

// Set true for production, false for test. Controls SKUs (app plan, DB, storage) and app settings.
param isProduction = false
param apiImageName = 'api'
param uiImageName = 'ui'
param tileserverImageName = 'tileserver'
param apiInternalUrl = '${prefix}-api.azurewebsites.net'
param apiUrl = isProduction ? 'https://palvelukartta-api.turku.fi' : 'https://testipalvelukartta-api.turku.fi'
param apiWebAppName = '${prefix}-api'
param uiWebAppName = '${prefix}-ui'
param tileserverWebAppName = '${prefix}-tileserver'
param tileserverUrl = isProduction ? 'https://maptiles.turku.fi' : 'https://maptiles-testi.turku.fi'
param appInsightsName = '${prefix}-appinsights'
param cacheName = '${prefix}-cache'
param containerRegistryName = '${sanitizedPrefix}registry'
param dbName = 'palvelukartta'
param dbServerName = '${prefix}-db'
param dbAdminUsername = 'turkuadmin'
param dbUsername = 'palvelukartta'
param keyvaultName = '${sanitizedPrefix}-kv'
param serverfarmPlanName = 'serviceplan'
param storageAccountName = '${sanitizedPrefix}store'
param apiOutboundIpName = isProduction ? 'turku-prod-servicemap-outbound-ip' : 'turku-test-servicemap-outbound-ip'
param natGatewayName = '${prefix}-nat'
param vnetName =  '${prefix}-vnet'
param workspaceName = '${prefix}-workspace'
