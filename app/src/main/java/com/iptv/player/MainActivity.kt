package com.iptv.player

import android.os.Bundle
import android.view.View
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.exoplayer2.MediaItem
import com.google.android.exoplayer2.SimpleExoPlayer
import com.google.android.exoplayer2.source.hls.HlsMediaSource
import com.google.android.exoplayer2.trackselection.DefaultTrackSelector
import com.google.android.exoplayer2.ui.PlayerView
import com.google.android.exoplayer2.upstream.DefaultHttpDataSource
import okhttp3.OkHttpClient
import okhttp3.Request
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {

    private lateinit var playerView: PlayerView
    private lateinit var loadingSpinner: ProgressBar
    private lateinit var errorText: TextView
    private lateinit var channelList: RecyclerView
    private var exoPlayer: SimpleExoPlayer? = null
    private var currentChannelUrl: String? = null
    private val client = OkHttpClient.Builder().build()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        playerView = findViewById(R.id.player_view)
        loadingSpinner = findViewById(R.id.loading_spinner)
        errorText = findViewById(R.id.error_text)
        channelList = findViewById(R.id.channel_list)

        channelList.layoutManager = LinearLayoutManager(this)

        // 直接使用构建时写入的地址
        loadChannelList(BuildConfig.BASE_URL)
    }

    private fun loadChannelList(playlistUrl: String) {
        loadingSpinner.visibility = View.VISIBLE
        errorText.visibility = View.GONE

        thread {
            try {
                val request = Request.Builder().url(playlistUrl).build()
                val response = client.newCall(request).execute()
                if (!response.isSuccessful) {
                    throw Exception("HTTP ${response.code}")
                }
                val content = response.body?.string() ?: ""
                val channels = parseTxtPlaylist(content)
                runOnUiThread {
                    loadingSpinner.visibility = View.GONE
                    if (channels.isEmpty()) {
                        errorText.text = "未找到任何频道，请检查网络或源地址"
                        errorText.visibility = View.VISIBLE
                    } else {
                        setupChannelList(channels)
                        // 默认播放第一个频道
                        if (channels.isNotEmpty()) {
                            playChannel(channels[0].url)
                        }
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
                runOnUiThread {
                    loadingSpinner.visibility = View.GONE
                    errorText.text = "加载频道列表失败: ${e.message}"
                    errorText.visibility = View.VISIBLE
                }
            }
        }
    }

    // 解析 TV.TXT 格式 (频道名,URL)
    private fun parseTxtPlaylist(content: String): List<Channel> {
        val lines = content.lines()
        val channels = mutableListOf<Channel>()
        for (line in lines) {
            val trimmed = line.trim()
            if (trimmed.isEmpty() || trimmed.startsWith("#")) continue
            val commaIndex = trimmed.indexOf(',')
            if (commaIndex > 0) {
                val name = trimmed.substring(0, commaIndex)
                val url = trimmed.substring(commaIndex + 1)
                if (url.startsWith("http")) {
                    channels.add(Channel(name, url))
                }
            }
        }
        return channels
    }

    private fun setupChannelList(channels: List<Channel>) {
        val adapter = ChannelAdapter(channels) { channel ->
            playChannel(channel.url)
        }
        channelList.adapter = adapter
    }

    private fun playChannel(url: String) {
        if (currentChannelUrl == url && exoPlayer?.isPlaying == true) return
        currentChannelUrl = url

        releasePlayer()
        val trackSelector = DefaultTrackSelector(this)
        exoPlayer = SimpleExoPlayer.Builder(this).setTrackSelector(trackSelector).build()
        playerView.player = exoPlayer

        val dataSourceFactory = DefaultHttpDataSource.Factory()
        // HLS 流媒体源处理
        val mediaSource = HlsMediaSource.Factory(dataSourceFactory)
            .createMediaSource(MediaItem.fromUri(url))
        exoPlayer?.setMediaSource(mediaSource)
        exoPlayer?.prepare()
        exoPlayer?.playWhenReady = true
    }

    private fun releasePlayer() {
        exoPlayer?.release()
        exoPlayer = null
        playerView.player = null
    }

    override fun onDestroy() {
        super.onDestroy()
        releasePlayer()
    }

    data class Channel(val name: String, val url: String)
}
