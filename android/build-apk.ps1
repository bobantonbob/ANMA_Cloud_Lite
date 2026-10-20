$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$env:ANDROID_HOME = Join-Path $root '.local/sdk'
$env:GRADLE_USER_HOME = Join-Path $root '.local/gradle-cache'
$env:ANDROID_USER_HOME = Join-Path $root '.local/android-user'
$env:JAVA_HOME = Split-Path (Split-Path (Get-Command java).Source)
$key = Join-Path $root '.local/preview.keystore'
if (!(Test-Path $key)) {
    & "$env:JAVA_HOME/bin/keytool.exe" -genkeypair -keystore $key -storepass android -keypass android -alias anma-preview -keyalg RSA -keysize 2048 -validity 3650 -dname 'CN=ANMA Cloud Preview, O=ANMA Electric, C=UA'
    if ($LASTEXITCODE -ne 0) { throw 'Could not create preview signing key' }
}
& "$root/.local/gradle-8.9/bin/gradle.bat" -p $root --console=plain :app:assembleDebug :app:lintDebug
if ($LASTEXITCODE -ne 0) { throw 'Android build or lint failed' }
$out = Join-Path (Split-Path $root) 'release/android'
New-Item -ItemType Directory -Force $out | Out-Null
Copy-Item "$root/app/build/outputs/apk/debug/app-debug.apk" "$out/ANMA-Cloud-0.1.1-preview.apk"
$verification = & "$env:ANDROID_HOME/build-tools/35.0.0/apksigner.bat" verify --verbose --print-certs "$out/ANMA-Cloud-0.1.1-preview.apk"
if ($LASTEXITCODE -ne 0) { throw 'APK signature verification failed' }
$verification | Write-Output
$certLine = $verification | Where-Object { $_ -match '^Signer #1 certificate SHA-256 digest:' }
$digest = ($certLine -split ': ', 2)[1].Trim().ToUpperInvariant()
if ($digest -notmatch '^[0-9A-F]{64}$') { throw 'Could not determine signing fingerprint' }
$fingerprint = ([regex]::Matches($digest, '..').Value) -join ':'
$statement = @{
    relation = @('delegate_permission/common.handle_all_urls')
    target = @{
        namespace = 'android_app'
        package_name = 'ua.com.anmaelectric.cloud'
        sha256_cert_fingerprints = @($fingerprint)
    }
}
ConvertTo-Json -InputObject @($statement) -Depth 5 | Set-Content "$out/assetlinks.json" -Encoding utf8
$checksum = Get-FileHash "$out/ANMA-Cloud-0.1.1-preview.apk" -Algorithm SHA256
"$($checksum.Hash.ToLowerInvariant())  ANMA-Cloud-0.1.1-preview.apk" | Set-Content "$out/SHA256SUMS.txt" -Encoding ascii
$checksum
