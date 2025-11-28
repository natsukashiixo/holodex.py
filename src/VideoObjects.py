

'''
This file contains BaseVideo and its subclasses: 
Streamable(BaseVideo) 
Clip(BaseVideo)
Stream(Streamable)
Placeholder(Streamable)

BaseVideo holds general metadata.
Streamable holds the topic of any non-clips. 
Clip holds info about sources and other clips of the same source. 
Stream holds info about live stream specific data like clips referencing the stream, song count, song list and more. 
Placeholder holds info about potential future streams, external streams and other events. 
'''

class BaseVideo:

    @staticmethod
    def from_data(client, data: dict):
        if (j := data.get("type")) == "stream":
            return Stream(client, data)
        elif j == "clip":
            return Clip(client, data)
        elif j == "placeholder":
            return Placeholder(client, data)
        else:
            raise ValueError(f"Invalid Video Type {j}")

    @staticmethod
    def from_youtube(client, model):
        data = {

        }
        return None

    def __init__(self, client: HolodexClient, data: dict):
        self.client = client
        self._data = data
        self.id: str = data["id"]
        if not len(self.id) == 11:
            raise ValueError("Invalid Video ID")
        self.title: str = data.get("title")
        self.type: ["stream", "clip", "placeholder"] = data.get("type")
        self.published_at: datetime | None = parse_time(data.get("published_at"))
        self.available_at: datetime = parse_time(data.get("available_at"))
        self.duration: int = parse_int(data.get("duration"))
        self.status: ["new", "upcoming", "live", "past", "missing"] = data.get("status")
        self.start_scheduled: datetime | None = parse_time(data.get("start_scheduled"))
        self.start_actual: datetime | None = parse_time(data.get("start_actual"))
        self.end_actual: datetime | None = parse_time(data.get("end_actual"))
        self.description: str = data.get("description")
        self.channel_id: str = data.get("channel_id")
        self.recommendations: list[BaseVideo] = [BaseVideo.from_data(client, video) for video in data.get("recommendations", [])]
        self.refers: list[BaseVideo] = [BaseVideo.from_data(client, video) for video in data.get("refers", [])]
        self.mentions: list[Vtuber] = [self.client.generate_channel(vtuber) for vtuber in data.get("mentions", [])]
        self.lang: str = data.get("lang")

        self.channel: Vtuber | Clipper = self.client.generate_channel(data.get("channel"))

    def __str__(self):
        return self.title

    def __repr__(self):
        return f'<BaseVideo id={self.id} type={self.type} channel={self.channel}>'

    def __eq__(self, other):
        if not isinstance(other, BaseVideo):
            return False
        return self.id == other.id

    def __ne__(self, other):
        if not isinstance(other, BaseVideo):
            return True
        return self.id != other.id

    def __hash__(self):
        return hash(self.id)

    @property
    def thumbnail(self):
        return f"https://i.ytimg.com/vi/{self.id}/hqdefault.jpg"

    @property
    def max_thumbnail(self):
        return f"https://i.ytimg.com/vi/{self.id}/maxresdefault.jpg"

    @property
    def url(self):
        return f'https://holodex.net/watch/{self.id}'

    @property
    def hyperlink(self):
        return f'[{ed(str(self))}]({self.url})'

    @property
    def yt_url(self):
        return f'https://youtube.com/watch?v={self.id}'

    @property
    def yt_hyperlink(self):
        return f'[{ed(str(self))}]({self.yt_url})'

    async def fetch_mentions(self):
        r = await self.client.fetch_video_mentions(self.id)
        if isinstance(r, list):
            return [self.client.generate_channel(c) for c in r]

    async def add_mention(self, channel):
        if not isinstance(channel, BaseChannel):
            raise TypeError(f"Channel {c} must be of type BaseChannel, not {type(c)}.")
        return await self.client.add_video_mention(self.id, channel.id)

    async def remove_mentions(self, *channels):
        chs = []
        for c in channels:
            if not isinstance(c, BaseChannel):
                raise TypeError(f"Channel {c} must be of type BaseChannel, not {type(c)}.")
            chs.append(c.id)
        return await self.client.remove_video_mentions(self.id, *chs)

    async def remove_mention(self, channel):
        return await self.remove_mentions(self.id, channel)

    async def is_members(self):
        data = await self.client.static("https://youtube.com/watch?v=" + self.id, base=False)
        # if data.status != 200: raise
        page = await data.text()
        soup = BeautifulSoup(page, "html.parser")
        j = soup.find_all("script")
        k = (list(filter(lambda x: "playabilityStatus" in str(x), j)))
        pattern = re.compile(r"var ytInitialPlayerResponse = (.*?);$", re.MULTILINE | re.DOTALL)
        var = pattern.search(k[0].text)
        raw = var.group(1)
        final = loads(raw)
        reason = final.get("playabilityStatus", {}).get("reason", "")
        return "get access to members-only content" in reason

class Streamable(BaseVideo):

    def __init__(self, client: HolodexClient, data: dict):
        super().__init__(client, data)
        self.topic_id: str = data.get("topic_id")
        self.topic = self.client.gen_topic(self.topic_id)

    def __repr__(self):
        return f'<Streamable id={self.id} topic={self.topic} channel={self.channel}>'

    async def fetch_topic(self):
        return await self.client.fetch_video_topic(self.id)

    async def set_topic(self, topic: str | None):
        return await self.client.edit_video_topic(self.id, topic)

class Clip(BaseVideo):

    def __init__(self, client: HolodexClient, data: dict):
        super().__init__(client, data)
        self.sources: list[Stream] = [Stream(client, source) for source in data.get("sources", [])]
        self.same_source_clips: list[Clip] = [Clip.from_data(client, clip) for clip in data.get("same_source_clips", [])]

    def __repr__(self):
        return f'<Clip id={self.id} channel={self.channel}> sources={self.sources}>'

class Stream(Streamable):

    def __init__(self, client: HolodexClient, data: dict):
        super().__init__(client, data)
        self.clips: list[Clip] = [Clip(self.client, clip) for clip in data.get("clips", [])]
        self.simulcasts: list[Stream] = [Stream(self.client, simulcast) for simulcast in data.get("simulcasts", [])]
        self.song_count: int = parse_int(data.get("song_count")) or parse_int(data.get("songcount"))
        self.songs: list = data.get("songs")
        self.live_viewers: int | None = parse_int(data.get("live_viewers"))
        self.comments: list[Comment] = [Comment(comment) for comment in data.get("comments", [])]
        if not self.channel and data.get("channel"):
            self.channel = self.client.generate_channel(data["channel"])

    def __repr__(self):
        return f'<Stream id={self.id} topic={self.topic} channel={self.channel}>'

class Placeholder(Streamable):

    def __init__(self, client: HolodexClient, data: dict):
        super().__init__(client, data)
        self._thumbnail = data.get("thumbnail")
        self.jp_name = data.get("jp_name")
        self.link = data.get("link") or f'https://holodex.net/watch/{self.id}'
        self.placeholder_type = data.get("placeholderType")
        self.certainty = data.get("certainty")
        self.credits = PlaceholderCredits.from_data(data.get("credits"))
        if not self.channel and data.get("channel"):
            self.channel = self.client.generate_channel(data["channel"])

    @property
    def thumbnail(self):
        return self._thumbnail

    @property
    def url(self):
        return self.link

    @property
    def name(self):
        return self.title

    @property
    def yt_url(self):
        return None

    def __repr__(self):
        return f'<Placeholder id={self.id} type={self.type} channel={self.channel}>'

    async def edit(
        self,
        title: str = None,
        jp_name: str = None,
        link: str = None,
        thumbnail: str = None,
        duration: int = None,
        start_time: datetime = None,
        credits: PlaceholderCredits = None,
        type: ["scheduled-yt-stream", "external-stream", "event"] = None,
        certainty: ["likely", "certain"] = None
    ):
        return await self.client.add_placeholder(
            self.channel.id,
            title or self.title,
            jp_name or self.jp_name,
            link or self.link,
            thumbnail or self.thumbnail,
            duration or self.duration,
            start_time or self.start_scheduled or self.available_at,
            credits or self.credits,
            type=type or self.placeholder_type,
            certainty=certainty or self.certainty,
            id=self.id
        )

    async def delete(self):
        return await self.client.delete_placeholder(self.id)
