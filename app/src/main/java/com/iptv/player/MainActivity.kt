package com.iptv.player

import android.os.Bundle
import android.view.GestureDetector
import android.view.MotionEvent
import android.view.View
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.exoplayer2.ExoPlayer
import com.google.android.exoplayer2.MediaItem
import com.google.android.exoplayer2.PlaybackException
import com.google.android.exoplayer2.Player
import com.iptv.player.databinding.ActivityMainBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var player: ExoPlayer
    private var channels = listOf<Channel>()
    private var currentChannelIndex = 0
    private var channelAdapter: ChannelAdapter? = null
    private var gestureDetector: GestureDetector? = null
    private var isChannelListVisible = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 全屏沉浸
        window.decorView.systemUiVisibility = (
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        or View.SYSTEM_UI_FLAG_FULLSCREEN
                        or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                )

        initPlayer()
        setupGesture()
        loadPlaylist()
    }

    private fun initPlayer() {
        player = ExoPlayer.Builder(this).build()
        binding.playerView.player = player
        player.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                when (playbackState) {
                    Player.STATE_ENDED -> {
                        // 自动播放下一个
                        nextChannel()
                    }
                    Player.STATE_BUFFERING -> {
                        // 可显示缓冲提示
                    }
                    Player.STATE_READY -> {
                        // 隐藏加载提示
                    }
                }
            }

            override fun onPlayerError(error: PlaybackException) {
                // 播放失败，自动切换下一个
                nextChannel()
            }
        })
    }

    private fun setupGesture() {
        gestureDetector = GestureDetector(this, object : GestureDetector.SimpleOnGestureListener() {
            override fun onSingleTapConfirmed(e: MotionEvent): Boolean {
                toggleChannelList()
                return true
            }

            override fun onScroll(
                e1: MotionEvent?,
                e2: MotionEvent,
                distanceX: Float,
                distanceY: Float
            ): Boolean {
                if (e1 != null && kotlin.math.abs(e2.y - e1.y) > 100) {
                    if (e2.y > e1.y) {
                        // 向下滑动 -> 下一个频道
                        nextChannel()
                    } else {
                        // 向上滑动 -> 上一个频道
                        previousChannel()
                    }
                    return true
                }
                return false
            }
        })
        binding.root.setOnTouchListener { _, event ->
            gestureDetector?.onTouchEvent(event)
            true
        }
    }

    private fun toggleChannelList() {
        if (isChannelListVisible) {
            hideChannelList()
        } else {
            showChannelList()
        }
    }

    private fun showChannelList() {
        if (channels.isEmpty()) return
        if (channelAdapter == null) {
            channelAdapter = ChannelAdapter(channels) { channel ->
                val index = channels.indexOfFirst { it.url == channel.url }
                if (index != -1) {
                    currentChannelIndex = index
                    playChannel(currentChannelIndex)
                }
                hideChannelList()
            }
            binding.channelListView.layoutManager = LinearLayoutManager(this)
            binding.channelListView.adapter = channelAdapter
        }
        binding.channelListView.visibility = View.VISIBLE
        isChannelListVisible = true
        // 滚动到当前频道位置
        binding.channelListView.scrollToPosition(currentChannelIndex)
    }

    private fun hideChannelList() {
        binding.channelListView.visibility = View.GONE
        isChannelListVisible = false
    }

    private fun playChannel(index: Int) {
        if (index < 0 || index >= channels.size) return
        currentChannelIndex = index
        val channel = channels[currentChannelIndex]
        val mediaItem = MediaItem.Builder()
            .setUri(channel.url)
            .setMimeType("application/x-mpegURL") // 强制HLS
            .build()
        player.setMediaItem(mediaItem)
        player.prepare()
        player.play()
        showToastChannelName(channel.name)
    }

    private fun showToastChannelName(name: String) {
        binding.toastChannelName.text = name
        binding.toastChannelName.visibility = View.VISIBLE
        binding.toastChannelName.postDelayed({
            binding.toastChannelName.visibility = View.GONE
        }, 1500)
    }

    private fun nextChannel() {
        if (channels.isEmpty()) return
        val newIndex = (currentChannelIndex + 1) % channels.size
        playChannel(newIndex)
    }

    private fun previousChannel() {
        if (channels.isEmpty()) return
        val newIndex = (currentChannelIndex - 1 + channels.size) % channels.size
        playChannel(newIndex)
    }

    private fun loadPlaylist() {
        lifecycleScope.launch {
            try {
                val playlistUrl = BuildConfig.PLAYLIST_URL
                val fetched = withContext(Dispatchers.IO) {
                    PlaylistParser.fetchPlaylist(playlistUrl)
                }
                channels = fetched
                if (channels.isNotEmpty()) {
                    playChannel(0)
                } else {
                    showToastChannelName("未获取到频道列表")
                }
            } catch (e: Exception) {
                e.printStackTrace()
                showToastChannelName("加载失败: ${e.message}")
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        player.release()
    }
}
