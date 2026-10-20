# ANMA Cloud for Android — preview

An installable Android launcher for the existing ANMA Cloud website, using Google's
Android Browser Helper (Trusted Web Activity / Custom Tabs). The Django server,
accounts, Home Assistant connections and dashboard remain the source of truth.

## Install and try

1. Copy `release/android/ANMA-Cloud-0.1.1-preview.apk` to your Android phone.
2. Open it and allow installation from that file manager if Android asks.
3. Open **ANMA Cloud**. Use an updated Chrome or another TWA-compatible browser.
4. Sign in with the same Google account or email/password used on the website.

Requires Android 6.0 or newer and an Internet connection. The app shares website
sessions with its selected browser; it does not collect or store passwords itself.
Google authentication stays in the browser. No native Google OAuth client or
credentials are embedded in the APK. Signing out also affects the shared browser
session. An existing browser login may sign you in without another password prompt.

This preview is not a Play Store release. Device installation, Google sign-in,
back navigation and browser-specific behavior still need a physical-device check.

## Full-screen domain verification

Until the website publishes Digital Asset Links, Android opens the site with a
Custom Tab toolbar. This is an intentional safe fallback, not an authentication
error. The website UI and accounts are the same in either mode.

Publish the generated `release/android/assetlinks.json` at exactly:

`https://cloud.anma-electric.com.ua/.well-known/assetlinks.json`

It must be an HTTPS 200 response with JSON content type, without login or redirects.
The file contains only the package name and public certificate fingerprint. This
build does not deploy changes to the website. After verification, supported
browsers can show the Cloud domain without browser chrome. External origins such
as Google sign-in may show browser controls normally.

## Build on Windows

Install JDK 17, then from the repository root run:

```powershell
./android/prepare-tools.ps1
./android/build-apk.ps1
```

Downloads come from official Google/Gradle repositories; SDK archive checksums are
checked against Google's repository metadata, and Gradle against its SHA-256.
The SDK license is included in the downloaded distribution. Tools and caches stay
under ignored `android/.local/`; no global SDK changes are needed.

The preview signing key is generated locally in `.local/preview.keystore`. Keep
it for upgrades; losing it means a future differently signed APK cannot replace
this installation. It is a development key, not a production release key. Before
a public release, use a protected release signing key and update Digital Asset Links.

The build runs Android Lint and verifies the APK signature. The APK contains no
Home Assistant tokens, OAuth secrets, Django environment files or database.

References: [TWA quick start](https://developer.chrome.com/docs/android/trusted-web-activity/quick-start),
[Android Browser Helper](https://github.com/GoogleChrome/android-browser-helper).
