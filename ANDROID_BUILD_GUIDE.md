# Android App Build Guide

## Your Bot Server
- **URL**: https://whatsapp-rag-bot-4tnp.onrender.com
- **Status**: ✅ Live and responding

---

## Step 1: Install Android Studio
1. Download from: https://developer.android.com/studio
2. Install and open Android Studio
3. Create a new **Empty Activity** project:
   - **Name**: WhatsApp RAG Bot
   - **Package name**: `com.yourname.whatsappautobot` (change `yourname`)
   - **Language**: Java
   - **Minimum SDK**: API 26 (Android 8.0)
   - **Target SDK**: API 35 (Android 15)

---

## Step 2: Import Project Files

In your Android Studio project, copy these files from the repo:

### Java Files (to `app/src/main/java/com/yourname/whatsappautobot/`)
- [WhatsAppListenerService.java](../android-app/WhatsAppListenerService.java)
- [MainActivity.java](../android-app/MainActivity.java)

### Layout Files (to `app/src/main/res/layout/`)
- [activity_main.xml](../android-app/activity_main.xml) → Replace existing `activity_main.xml`

### Manifest File (replace entire file)
- [AndroidManifest.xml](../android-app/AndroidManifest.xml) → Replace `app/src/main/AndroidManifest.xml`

---

## Step 3: Verify Build Settings

In Android Studio:
1. **File** → **Project Structure** → **Project**
   - Gradle Plugin: 8.1.0+ (or latest)
   - Gradle Version: 8.0+ (or latest)

2. **File** → **Project Structure** → **app** → **Build**
   - **compileSdk**: 35+
   - **minSdk**: 26
   - **targetSdk**: 35

3. Make sure `build.gradle` (Module: app) has:
   ```gradle
   dependencies {
       implementation 'androidx.appcompat:appcompat:1.6.1'
       implementation 'androidx.constraintlayout:constraintlayout:2.1.4'
   }
   ```

---

## Step 4: Sync and Build

1. Click **File** → **Sync Now**
2. Wait for gradle sync to complete (bottom status bar)
3. If errors appear, update dependencies or SDK as suggested

---

## Step 5: Build APK

### Option A: Debug APK (for testing on your phone)
1. **Build** → **Build APK(s)**
2. APK location: `app/build/outputs/apk/debug/app-debug.apk`
3. Wait for build to complete

### Option B: Signed Release APK (for production)
1. **Build** → **Generate Signed Bundle / APK**
2. Create a new keystore:
   - **Key store path**: `C:\Users\<username>\android.jks`
   - **Key alias**: `whatsapp-bot`
   - **Password**: (set your own, remember it!)
3. Choose **APK** (not Bundle)
4. Release configuration
5. APK location: `app/release/app-release.apk`

---

## Step 6: Install on Your Phone

### Method 1: Via Android Studio (Recommended)
1. **Run** → **Run 'app'**
2. Select your connected phone
3. App installs automatically

### Method 2: Manual Install
1. Transfer APK to your phone (USB cable or email)
2. Tap the APK file to install
3. Grant install permissions when prompted

### Method 3: ADB Command
```bash
adb install app\build\outputs\apk\debug\app-debug.apk
```

---

## Step 7: Configure on Your Phone

1. **Open the WhatsApp RAG Bot app**
2. **Grant Notification Access**:
   - Tap "Grant Notification Access" button
   - Opens Settings → Notifications → Notification Access
   - Find and enable "WhatsApp RAG Bot Listener"
   - Go back to the app
3. **Enter Server URL** (pre-filled with Render URL):
   - `https://whatsapp-rag-bot-4tnp.onrender.com/reply`
4. **Toggle "Enable Bot" ON**
5. **Tap "Save Settings"**

---

## Step 8: Test!

1. Ask a friend to send you a WhatsApp message
2. Watch the bot auto-reply! 🎉
3. Check Android logcat for debug logs:
   - **View** → **Tool Windows** → **Logcat**
   - Filter by tag: `WABotListener`

---

## Troubleshooting

### App Won't Install
- ✓ Enable "Install from unknown sources" in phone Settings
- ✓ Check phone has Android 8.0+ (API 26)
- ✓ Delete old app version first

### App Crashes on Startup
- ✓ Check Android Studio Logcat for errors
- ✓ Ensure package name matches in files
- ✓ Verify all imports in Java files are correct
- ✓ Check `compileSdk` is 35+

### Notification Access Not Working
- ✓ Go to **Settings** → **Apps** → **WhatsApp RAG Bot** → **Permissions** → **Notification Access**
- ✓ Enable the toggle
- ✓ Restart the app

### Bot Not Replying
- ✓ Verify notification access is enabled
- ✓ Check "Enable Bot" toggle is ON in the app
- ✓ Confirm server URL is correct: `https://whatsapp-rag-bot-4tnp.onrender.com/reply`
- ✓ Check logcat for error messages

### Logcat Shows "Server URL not configured"
- ✓ Make sure you clicked "Save Settings"
- ✓ Check URL field isn't empty
- ✓ Make sure it starts with `https://` or `http://`

---

## Useful Links

- **Android Studio**: https://developer.android.com/studio
- **Android Docs**: https://developer.android.com/docs
- **Logcat Debug Guide**: https://developer.android.com/studio/debug/logcat
- **Your Bot Server**: https://whatsapp-rag-bot-4tnp.onrender.com

---

## What's Next?

✅ **App is built and installed**

**Options:**
1. **Train the bot** to sound like you:
   - Export WhatsApp chats
   - Run ingestion script
   - Set `DISABLE_RAG = false` on Render

2. **Customize the prompt** in `server/main.py`:
   - Change SYSTEM_PROMPT for different personality
   - Modify tone, language, slang

3. **Monitor logs** in Render:
   - Render Dashboard → Logs
   - See all bot responses and errors

---

**Happy auto-replying!** 🤖✨
