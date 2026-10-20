# Android preview download

`ANMA-Cloud-0.1.1-preview.apk` is the signed, installable preview served by Django
at `/downloads/android/`. This directory is included in Git and the Docker image.
No signing keys or build tools belong here.

SHA-256: `7d39c55905c3284925f03fac58dc33b8ab7c1164193f2d6aec7d3a72bc90cbff`

Build instructions are in `android/README.md`. For an update, build and verify the
APK, copy it here, then update the download view, UI version and checksum together.
Deploy through the normal Git → GitHub → server workflow. Website UI changes are
also visible in the installed browser-backed app without rebuilding its APK.
