package ru.brucelee3.app;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;

/** Срабатывает в конце отдыха или отрезка и показывает уведомление.
 *  Huawei Health пересылает его на часы, если для приложения включены уведомления.
 *  Повторы (по умолчанию 5 раз через 4 с) ставит сам себе, пока ты не возьмёшь телефон. */
public class AlertReceiver extends BroadcastReceiver {

    @Override
    @SuppressWarnings("deprecation")
    public void onReceive(Context c, Intent intent) {
        if (Build.VERSION.SDK_INT >= 33
                && c.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            return;
        }
        int id = intent.getIntExtra("id", 0);
        int left = intent.getIntExtra("left", 1);
        int gap = intent.getIntExtra("gap", 0);
        int n = intent.getIntExtra("n", 1);
        int total = intent.getIntExtra("total", 1);
        int prev = intent.getIntExtra("prev", 0);
        long t0 = intent.getLongExtra("t0", 0L);
        // Повтор: если после первого сигнала ты уже брал телефон — дальше не вибрируем.
        if (n > 1 && c.getSharedPreferences(MainActivity.PREFS, Context.MODE_PRIVATE).getLong("stop", 0L) >= t0) {
            return;
        }
        MainActivity.createChannel(c);
        String title = intent.getStringExtra("title");
        String text = intent.getStringExtra("text");
        if (title == null) title = "Брюс Ли 6.1";
        if (text == null) text = "";
        String shownTitle = n > 1 ? title + " · " + n + "/" + total : title;

        Intent open = new Intent(c, MainActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent content = PendingIntent.getActivity(c, 0, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            b = new Notification.Builder(c, MainActivity.CHANNEL_ID);
            b.setTimeoutAfter(120_000);
        } else {
            b = new Notification.Builder(c);
            b.setPriority(Notification.PRIORITY_HIGH);
            b.setVibrate(new long[]{0, 400, 200, 400});
            b.setDefaults(Notification.DEFAULT_SOUND);
        }
        b.setSmallIcon(R.drawable.ic_stat)
                .setContentTitle(shownTitle)
                .setContentText(text)
                .setStyle(new Notification.BigTextStyle().bigText(text))
                .setAutoCancel(true)
                .setShowWhen(true)
                .setWhen(System.currentTimeMillis())
                .setVisibility(Notification.VISIBILITY_PUBLIC)
                .setCategory(Notification.CATEGORY_ALARM)
                .setContentIntent(content);

        NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;
        // каждый сигнал — новое уведомление: часы вибрируют только на новое; прошлый повтор убираем из шторки
        int notifyId = 1000 + (int) (System.currentTimeMillis() % 100000);
        nm.notify(notifyId, b.build());
        if (prev != 0 && prev != notifyId) nm.cancel(prev);
        if (left > 1 && gap > 0) {
            MainActivity.setAlarm(c, System.currentTimeMillis() + gap,
                    MainActivity.alertIntent(c, id + MainActivity.CHAIN, id, title, text, left - 1, gap, n + 1, total, t0, notifyId));
        }
    }
}
