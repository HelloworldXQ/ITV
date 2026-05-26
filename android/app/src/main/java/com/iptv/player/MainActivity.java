package com.iptv.player;

import android.os.Bundle;
import android.widget.ArrayAdapter;
import android.widget.ListView;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.exoplayer2.util.Log;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.lang.reflect.Type;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends AppCompatActivity {
    private ListView listView;
    private ArrayAdapter<String> adapter;
    private List<Channel> channels = new ArrayList<>();
    private ExecutorService executor = Executors.newSingleThreadExecutor();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        listView = findViewById(R.id.channel_list);
        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, new ArrayList<>());
        listView.setAdapter(adapter);

        // 从 BuildConfig 中读取 URL（构建时注入）
        String m3uUrl = BuildConfig.M3U_URL;
        loadChannels(m3uUrl);

        listView.setOnItemClickListener((parent, view, position, id) -> {
            Channel ch = channels.get(position);
            PlayerActivity.start(this, ch.getName(), ch.getUrl());
        });
    }

    private void loadChannels(String m3uUrl) {
        executor.execute(() -> {
            try {
                URL url = new URL(m3uUrl);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setConnectTimeout(10000);
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                String line;
                String currentName = null;
                List<Channel> temp = new ArrayList<>();
                while ((line = reader.readLine()) != null) {
                    if (line.startsWith("#EXTINF")) {
                        int idx = line.lastIndexOf(",");
                        if (idx != -1) {
                            currentName = line.substring(idx + 1).trim();
                        }
                    } else if (line.startsWith("http") && currentName != null) {
                        temp.add(new Channel(currentName, line));
                        currentName = null;
                    }
                }
                reader.close();
                channels.clear();
                channels.addAll(temp);
                runOnUiThread(() -> {
                    List<String> names = new ArrayList<>();
                    for (Channel ch : channels) names.add(ch.getName());
                    adapter.clear();
                    adapter.addAll(names);
                    adapter.notifyDataSetChanged();
                });
            } catch (Exception e) {
                e.printStackTrace();
            }
        });
    }

    static class Channel {
        private String name;
        private String url;
        public Channel(String name, String url) { this.name = name; this.url = url; }
        public String getName() { return name; }
        public String getUrl() { return url; }
    }
}
