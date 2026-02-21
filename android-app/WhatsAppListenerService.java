package com.yourname.whatsappautobot;

import android.app.Notification;
import android.app.RemoteInput;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.util.Log;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * WhatsApp Notification Listener Service
 * ========================================
 * This service:
 *   1. Intercepts ALL WhatsApp notifications
 *   2. Extracts the sender name and message text
 *   3. Sends them to your RAG server (POST /reply)
 *   4. Takes the AI reply and auto-sends it back via RemoteInput
 *
 * How it works:
 *   - Android's NotificationListenerService gives us access to all notifications
 *   - WhatsApp notifications contain a "RemoteInput" action (the quick reply button)
 *   - We extract the message, get an AI reply, then inject it into the RemoteInput
 *   - The reply is sent silently through WhatsApp's own reply mechanism
 *
 * Setup:
 *   1. Install the app on your phone
 *   2. Go to Settings → Notifications → Notification Access → Enable "WA RAG Bot Listener"
 *   3. Open the app → Enter your server URL → Enable the bot
 */
public class WhatsAppListenerService extends NotificationListenerService {

    private static final String TAG = "WABotListener";

    // WhatsApp package names
    private static final String WHATSAPP_PACKAGE = "com.whatsapp";
    private static final String WHATSAPP_BUSINESS_PACKAGE = "com.whatsapp.w4b";

    // SharedPreferences keys (shared with MainActivity)
    private static final String PREFS_NAME = "WABotPrefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String KEY_BOT_ENABLED = "bot_enabled";

    // Thread pool for async network requests (don't block the notification thread)
    private final ExecutorService executor = Executors.newFixedThreadPool(3);

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        // Only process WhatsApp notifications
        String packageName = sbn.getPackageName();
        if (!WHATSAPP_PACKAGE.equals(packageName) && !WHATSAPP_BUSINESS_PACKAGE.equals(packageName)) {
            return;
        }

        // Check if bot is enabled
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        boolean botEnabled = prefs.getBoolean(KEY_BOT_ENABLED, false);
        if (!botEnabled) {
            return;
        }

        // Get the server URL
        String serverUrl = prefs.getString(KEY_SERVER_URL, "");
        if (serverUrl.isEmpty()) {
            Log.w(TAG, "Server URL not configured!");
            return;
        }

        // Extract notification details
        Notification notification = sbn.getNotification();
        if (notification == null) return;

        Bundle extras = notification.extras;
        if (extras == null) return;

        // Get sender name and message text
        String senderName = extras.getString(Notification.EXTRA_TITLE, "");
        CharSequence messageChars = extras.getCharSequence(Notification.EXTRA_TEXT);
        String messageText = messageChars != null ? messageChars.toString() : "";

        // Skip empty messages, group messages, and system notifications
        if (senderName.isEmpty() || messageText.isEmpty()) return;
        if (senderName.contains("messages") || senderName.contains("Message")) return; // Summary notifications
        if (messageText.contains("📷") || messageText.contains("🎵")) return; // Media messages

        // Find the reply action (RemoteInput) in the notification
        Notification.Action replyAction = findReplyAction(notification);
        if (replyAction == null) {
            Log.d(TAG, "No reply action found for: " + senderName);
            return;
        }

        Log.i(TAG, "📩 Message from " + senderName + ": " + messageText);

        // Process asynchronously — don't block the notification thread
        executor.execute(() -> processMessage(serverUrl, senderName, messageText, replyAction));
    }

    /**
     * Find the RemoteInput reply action in a WhatsApp notification.
     * This is the "Reply" button that appears in the notification shade.
     */
    private Notification.Action findReplyAction(Notification notification) {
        if (notification.actions == null) return null;

        for (Notification.Action action : notification.actions) {
            if (action.getRemoteInputs() != null && action.getRemoteInputs().length > 0) {
                // Found an action with RemoteInput — this is the reply action
                return action;
            }
        }
        return null;
    }

    /**
     * Process a message: send to server → get reply → auto-send via WhatsApp.
     * Runs on a background thread.
     */
    private void processMessage(String serverUrl, String senderName, String messageText, Notification.Action replyAction) {
        try {
            // Step 1: Create a simple contact ID from the sender name
            // In production, you'd use the phone number for more reliable matching
            String contactId = senderName.toLowerCase()
                    .replaceAll("[^a-z0-9]", "_")
                    .replaceAll("_+", "_")
                    .replaceAll("^_|_$", "");

            // Step 2: Send message to RAG server
            String reply = callServer(serverUrl, contactId, senderName, messageText);

            if (reply != null && !reply.isEmpty()) {
                // Step 3: Send reply via WhatsApp's RemoteInput
                sendReply(replyAction, reply);
                Log.i(TAG, "✅ Auto-replied to " + senderName + ": " + reply);
            } else {
                Log.w(TAG, "⚠️ Empty reply from server for: " + senderName);
            }

        } catch (Exception e) {
            Log.e(TAG, "❌ Error processing message from " + senderName, e);
        }
    }

    /**
     * Call the RAG server's /reply endpoint.
     * Returns the AI-generated reply text, or null on error.
     */
    private String callServer(String serverUrl, String contactId, String contactName, String message) {
        HttpURLConnection connection = null;
        try {
            // Ensure URL ends with /reply
            if (!serverUrl.endsWith("/reply")) {
                serverUrl = serverUrl.endsWith("/") ? serverUrl + "reply" : serverUrl + "/reply";
            }

            URL url = new URL(serverUrl);
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
            connection.setDoOutput(true);
            connection.setConnectTimeout(10000);  // 10 second timeout
            connection.setReadTimeout(15000);      // 15 second timeout

            // Build JSON request body
            JSONObject requestBody = new JSONObject();
            requestBody.put("contact_id", contactId);
            requestBody.put("contact_name", contactName);
            requestBody.put("message", message);

            // Send request
            OutputStream os = connection.getOutputStream();
            os.write(requestBody.toString().getBytes("UTF-8"));
            os.flush();
            os.close();

            // Read response
            int responseCode = connection.getResponseCode();
            if (responseCode == 200) {
                BufferedReader reader = new BufferedReader(
                        new InputStreamReader(connection.getInputStream(), "UTF-8"));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                reader.close();

                // Parse JSON response
                JSONObject jsonResponse = new JSONObject(response.toString());
                return jsonResponse.getString("reply");
            } else {
                Log.e(TAG, "Server returned HTTP " + responseCode);
                return null;
            }

        } catch (Exception e) {
            Log.e(TAG, "Server call failed: " + e.getMessage(), e);
            return null;
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    /**
     * Send a reply through WhatsApp using the notification's RemoteInput.
     * This is the same mechanism Android uses for "quick reply" from notifications.
     */
    private void sendReply(Notification.Action action, String replyText) {
        try {
            // Get the RemoteInput key
            RemoteInput[] remoteInputs = action.getRemoteInputs();
            if (remoteInputs == null || remoteInputs.length == 0) {
                Log.e(TAG, "No RemoteInputs found!");
                return;
            }

            // Create an Intent with the reply text injected into the RemoteInput
            Intent intent = new Intent();
            Bundle bundle = new Bundle();

            for (RemoteInput remoteInput : remoteInputs) {
                bundle.putCharSequence(remoteInput.getResultKey(), replyText);
            }

            RemoteInput.addResultsToIntent(remoteInputs, intent, bundle);

            // Fire the PendingIntent — this sends the reply through WhatsApp
            action.actionIntent.send(this, 0, intent);

            Log.i(TAG, "📤 Reply sent successfully!");

        } catch (Exception e) {
            Log.e(TAG, "Failed to send reply: " + e.getMessage(), e);
        }
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // Not needed for our use case
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        executor.shutdown();
    }
}
