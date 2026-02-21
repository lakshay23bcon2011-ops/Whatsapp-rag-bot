package com.yourname.whatsappautobot;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

/**
 * Main Settings Activity
 * =======================
 * Provides a simple settings UI to:
 *   1. Enter your server URL
 *   2. Enable/disable the bot
 *   3. Grant notification access permission
 *   4. Test the server connection
 *
 * All settings are saved to SharedPreferences and read by WhatsAppListenerService.
 */
public class MainActivity extends AppCompatActivity {

    // SharedPreferences keys (must match WhatsAppListenerService)
    private static final String PREFS_NAME = "WABotPrefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String KEY_BOT_ENABLED = "bot_enabled";

    private EditText editServerUrl;
    private Switch switchBotEnabled;
    private Button btnGrantAccess;
    private Button btnSaveSettings;
    private Button btnTestConnection;
    private TextView txtStatus;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Find views
        editServerUrl = findViewById(R.id.editServerUrl);
        switchBotEnabled = findViewById(R.id.switchBotEnabled);
        btnGrantAccess = findViewById(R.id.btnGrantAccess);
        btnSaveSettings = findViewById(R.id.btnSaveSettings);
        btnTestConnection = findViewById(R.id.btnTestConnection);
        txtStatus = findViewById(R.id.txtStatus);

        // Load saved settings
        loadSettings();

        // ─── Button: Grant Notification Access ───
        btnGrantAccess.setOnClickListener(v -> {
            // Opens Android's system settings for Notification Access
            // User must manually enable "WA RAG Bot Listener" here
            Intent intent = new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS);
            startActivity(intent);
            Toast.makeText(this, "Enable 'WA RAG Bot Listener' in the list", Toast.LENGTH_LONG).show();
        });

        // ─── Button: Save Settings ───
        btnSaveSettings.setOnClickListener(v -> {
            saveSettings();
            Toast.makeText(this, "Settings saved! ✅", Toast.LENGTH_SHORT).show();
            updateStatus();
        });

        // ─── Button: Test Connection ───
        btnTestConnection.setOnClickListener(v -> {
            String serverUrl = editServerUrl.getText().toString().trim();
            if (serverUrl.isEmpty()) {
                Toast.makeText(this, "Enter a server URL first!", Toast.LENGTH_SHORT).show();
                return;
            }
            testConnection(serverUrl);
        });

        // Initial status update
        updateStatus();
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateStatus();
    }

    /**
     * Load saved settings from SharedPreferences.
     */
    private void loadSettings() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        String savedUrl = prefs.getString(KEY_SERVER_URL, "http://192.168.1.5:8000");
        boolean botEnabled = prefs.getBoolean(KEY_BOT_ENABLED, false);

        editServerUrl.setText(savedUrl);
        switchBotEnabled.setChecked(botEnabled);
    }

    /**
     * Save current settings to SharedPreferences.
     */
    private void saveSettings() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        SharedPreferences.Editor editor = prefs.edit();

        String serverUrl = editServerUrl.getText().toString().trim();
        boolean botEnabled = switchBotEnabled.isChecked();

        editor.putString(KEY_SERVER_URL, serverUrl);
        editor.putBoolean(KEY_BOT_ENABLED, botEnabled);
        editor.apply();
    }

    /**
     * Check if notification listener permission is granted.
     */
    private boolean isNotificationAccessGranted() {
        String enabledListeners = Settings.Secure.getString(
                getContentResolver(),
                "enabled_notification_listeners"
        );
        return enabledListeners != null &&
                enabledListeners.contains(getPackageName());
    }

    /**
     * Update the status display at the bottom.
     */
    private void updateStatus() {
        StringBuilder status = new StringBuilder();

        // Check notification access
        boolean hasAccess = isNotificationAccessGranted();
        status.append("📋 Notification Access: ").append(hasAccess ? "✅ Granted" : "❌ Not Granted").append("\n");

        // Check settings
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        String serverUrl = prefs.getString(KEY_SERVER_URL, "");
        boolean botEnabled = prefs.getBoolean(KEY_BOT_ENABLED, false);

        status.append("🌐 Server URL: ").append(serverUrl.isEmpty() ? "❌ Not Set" : serverUrl).append("\n");
        status.append("🤖 Bot Status: ").append(botEnabled ? "✅ Enabled" : "⏸️ Disabled").append("\n");

        // Overall readiness
        if (hasAccess && !serverUrl.isEmpty() && botEnabled) {
            status.append("\n🟢 BOT IS ACTIVE — Listening for WhatsApp messages!");
        } else {
            status.append("\n🔴 BOT IS NOT ACTIVE");
            if (!hasAccess) status.append("\n   → Grant notification access");
            if (serverUrl.isEmpty()) status.append("\n   → Enter server URL");
            if (!botEnabled) status.append("\n   → Enable the bot toggle");
        }

        txtStatus.setText(status.toString());
    }

    /**
     * Test the server connection by calling /health endpoint.
     * Runs on a background thread.
     */
    private void testConnection(String serverUrl) {
        txtStatus.setText("🔄 Testing connection...");

        new Thread(() -> {
            try {
                // Build health check URL
                String healthUrl = serverUrl;
                if (healthUrl.endsWith("/reply")) {
                    healthUrl = healthUrl.replace("/reply", "/health");
                } else if (!healthUrl.endsWith("/health")) {
                    healthUrl = healthUrl.endsWith("/") ? healthUrl + "health" : healthUrl + "/health";
                }

                java.net.URL url = new java.net.URL(healthUrl);
                java.net.HttpURLConnection conn = (java.net.HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(5000);
                conn.setReadTimeout(5000);

                int responseCode = conn.getResponseCode();
                conn.disconnect();

                String result;
                if (responseCode == 200) {
                    result = "✅ Server is reachable! (HTTP 200)";
                } else {
                    result = "⚠️ Server returned HTTP " + responseCode;
                }

                runOnUiThread(() -> {
                    Toast.makeText(this, result, Toast.LENGTH_LONG).show();
                    updateStatus();
                });

            } catch (Exception e) {
                runOnUiThread(() -> {
                    Toast.makeText(this,
                            "❌ Connection failed: " + e.getMessage(),
                            Toast.LENGTH_LONG).show();
                    updateStatus();
                });
            }
        }).start();
    }
}
