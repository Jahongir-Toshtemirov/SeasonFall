# SeasonFall for Android

Low-power **live wallpaper** (not a always-on overlay). Android only draws
while the home screen is visible, so it stays easy on battery and heat.

## Defaults (phone-friendly)

- ~24 FPS
- 12–60 particles (density slider)
- Simple Canvas shapes — no OpenGL, no network
- Pauses automatically when you open apps / turn the screen off

## Install

1. Download `SeasonFall-Android.apk` from [GitHub Releases](https://github.com/Jahongir-Toshtemirov/SeasonFall/releases).
2. Allow install from that source if Android asks.
3. Open **SeasonFall** → pick a season → **Set as live wallpaper**.

## Build locally

Needs JDK 17 + Android SDK:

```bash
cd android
gradle wrapper --gradle-version 8.9   # once
./gradlew assembleRelease
# APK: app/build/outputs/apk/release/app-release.apk
```
