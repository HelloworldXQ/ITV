package com.example.tvplayer.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.tv.material3.*
import com.example.tvplayer.R
import com.example.tvplayer.data.Channel
import com.example.tvplayer.data.PlaylistParser
import com.example.tvplayer.ui.components.ChannelCard
import kotlinx.coroutines.launch

@OptIn(ExperimentalTvMaterial3Api::class)
@Composable
fun PlaylistScreen(
    onChannelSelected: (Int) -> Unit,
    isTv: Boolean,
    viewModel: PlaylistViewModel = viewModel()
) {
    val channels by viewModel.channels.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val scope = rememberCoroutineScope()
    
    // 加载频道列表
    LaunchedEffect(Unit) {
        viewModel.loadChannels()
    }
    
    Box(modifier = Modifier.fillMaxSize()) {
        if (isLoading) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                if (isTv) {
                    TvCircularProgressIndicator()
                } else {
                    CircularProgressIndicator()
                }
            }
        } else if (channels.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "加载失败或暂无频道",
                        fontSize = 18.sp,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Button(
                        onClick = {
                            scope.launch {
                                viewModel.loadChannels()
                            }
                        }
                    ) {
                        Text("重试")
                    }
                }
            }
        } else {
            // 频道网格
            if (isTv) {
                TvLazyVerticalGrid(
                    columns = GridCells.Fixed(6),
                    contentPadding = PaddingValues(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(channels) { channel ->
                        ChannelCard(
                            channel = channel,
                            onClick = { onChannelSelected(channel.id) },
                            isTv = true
                        )
                    }
                }
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(channels) { channel ->
                        ChannelCard(
                            channel = channel,
                            onClick = { onChannelSelected(channel.id) },
                            isTv = false
                        )
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalTvMaterial3Api::class)
@Composable
fun PlaylistViewModel(channelsState: MutableState<List<Channel>> = mutableStateOf(emptyList())) {
    val channels = remember { channelsState }
    val isLoading = remember { mutableStateOf(true) }
    
    fun loadChannels() {
        // 实际应在 ViewModel 中实现，此处简化
        // 从 PlaylistParser 加载
    }
}
