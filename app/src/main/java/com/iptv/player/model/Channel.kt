package com.iptv.player.model

data class Channel(
    val name: String,
    val url: String,
    val group: String = "",
    var logo: String? = null,
    var epg: String? = null
)

data class ChannelGroup(
    val name: String,
    val channels: MutableList<Channel>
)
