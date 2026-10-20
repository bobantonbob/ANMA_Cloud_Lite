$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$cache = Join-Path $root '.local'
New-Item -ItemType Directory -Force $cache | Out-Null
function Get-Archive($name, $url, $hash, $algorithm) {
    $file = Join-Path $cache $name
    if (!(Test-Path $file)) { Invoke-WebRequest -Uri $url -OutFile $file }
    if ((Get-FileHash $file -Algorithm $algorithm).Hash -ne $hash) { throw "Checksum mismatch: $name" }
    return $file
}
$platform = Get-Archive 'platform.zip' 'https://dl.google.com/android/repository/platform-35_r02.zip' '0bb560a90a7a2cbd0dd8348224d518b638fe7949' 'SHA1'
$build = Get-Archive 'build-tools.zip' 'https://dl.google.com/android/repository/build-tools_r35_windows.zip' 'af059bb67cf7786f45ee0db85e2d24985df1b4b6' 'SHA1'
$platformTools = Get-Archive 'platform-tools.zip' 'https://dl.google.com/android/repository/platform-tools_r37.0.1-win.zip' 'e03e78b1d80b396f1c3358e31251cb31740e1110' 'SHA1'
$gradle = Get-Archive 'gradle.zip' 'https://services.gradle.org/distributions/gradle-8.9-bin.zip' 'd725d707bfabd4dfdc958c624003b3c80accc03f7037b5122c4b1d0ef15cecab' 'SHA256'
$sdk = Join-Path $cache 'sdk'
if (!(Test-Path "$sdk/platform-tools/adb.exe")) { Expand-Archive $platformTools $sdk -Force }
if (!(Test-Path "$sdk/platforms/android-35/android.jar")) {
    Expand-Archive $platform "$cache/platform" -Force
    New-Item -ItemType Directory -Force "$sdk/platforms" | Out-Null
    $folder = Get-ChildItem "$cache/platform" -Directory | Select-Object -First 1
    Move-Item -LiteralPath $folder.FullName -Destination "$sdk/platforms/android-35"
}
if (!(Test-Path "$sdk/build-tools/35.0.0/aapt2.exe")) {
    Expand-Archive $build "$cache/build-tools" -Force
    New-Item -ItemType Directory -Force "$sdk/build-tools" | Out-Null
    $folder = Get-ChildItem "$cache/build-tools" -Directory | Select-Object -First 1
    Move-Item -LiteralPath $folder.FullName -Destination "$sdk/build-tools/35.0.0"
}
if (!(Test-Path "$cache/gradle-8.9/bin/gradle.bat")) { Expand-Archive $gradle $cache -Force }
Write-Output 'Verified Android 35 build tools, platform and Gradle are ready.'
