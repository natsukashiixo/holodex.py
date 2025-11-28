'''
This file contains BaseChannel and its subclasses: 
Vtuber(BaseChannel)
Clipper(BaseChannel)
'''

class BaseChannel:

    @staticmethod
    def from_data(client, data: dict):
        if (j := data.get("type")) == "vtuber":
            return client.cls(client, data)
        elif j == "subber":
            return Clipper(client, data)
        else:
            raise ValueError(f"Invalid Channel Type {j}")

    def __init__(self, client: HolodexClient, data: dict):
        self.client = client
        self.id: str = data["id"]
        if not self.id.startswith("UC"):
            raise ValueError("Invalid channel ID")
        self.name: str = data.get("name")
        self.type: ["vtuber", "subber"] = data.get("type")
        self.description: str = data.get("description", "")
        self._photo: str | None = data.get("photo")
        self.thumbnail: str | None = data.get("thumbnail")
        self.banner: str | None = data.get("banner")
        if self.banner and "=w" not in self.banner:
            self.banner += "=w10000"
        self.view_count: int | None = parse_int(data.get("view_count"))
        self.subscriber_count: int | None = parse_int(data.get("subscriber_count"))
        self.video_count: int | None = parse_int(data.get("video_count"))
        self.published_at: datetime | None = parse_time(data.get("published_at"))
        self.updated_at: datetime | None = parse_time(data.get("updated_at"))
        self.crawled_at: datetime | None = parse_time(data.get("crawled_at"))
        self.created_at: datetime | None = parse_time(data.get("created_at"))
        self.yt_uploads_id: str | None = data.get("yt_uploads_id")
        self.twitter: str | None = data.get("twitter")
        if self.twitter:
            self.twitter = self.twitter.replace("@", "")
        self.inactive: bool = data.get("inactive", False)
        self.yt_handle: list = data.get("yt_handle", [])
        self.yt_name_history: list = data.get("yt_name_history", [])

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<BaseChannel id={self.id} name={self.name!r}'

    def __eq__(self, other):
        if not isinstance(other, BaseChannel):
            return False
        return self.id == other.id

    def __ne__(self, other):
        if not isinstance(other, BaseChannel):
            return True
        return self.id != other.id

    def __hash__(self):
        return hash(self.id)

    @property
    def photo(self):
        return f'https://holodex.net/statics/channelimg/{self.id}.png'

    @property
    def url(self):
        return f'https://holodex.net/channel/{self.id}'

    @property
    def hyperlink(self):
        return f'[{ed(str(self))}]({self.url})'

    @property
    def twitter_url(self):
        if self.twitter:
            return f'https://twitter.com/{self.twitter}'
        return None

    @property
    def twitter_hyperlink(self):
        if self.twitter:
            return f'[@{ed(self.twitter)}]({self.twitter_url})'
        return None

    @property
    def yt_url(self):
        return f'https://youtube.com/channel/{self.id}'

    @property
    def yt_hyperlink(self):
        return f'[{ed(self.name)}]({self.yt_url})'

    @property
    def handle(self):
        return self.yt_handle[0] if self.yt_handle else None

    @property
    def handle_url(self):
        if self.handle:
            return f'https://www.youtube.com/{self.handle}'
        return None

    @property
    def handle_hyperlink(self):
        if self.handle:
            return f'[{ed(self.handle)}]({self.handle_url})'
        return None

    # @handle.setter
    # def handle(self, value):
    #     if value not in self.yt_handle and value:
    #         self.yt_handle = [value] + self.yt_handle
    #     elif value is None:
    #         raise ValueError("Cannot unset handle.")

    @property
    def info(self):
        return f'{self.hyperlink} - ID {self.id}'

    def format_created(self, style: str | list = "f", separator: str = "", timestamp=None) -> str | None:
        timestamp = timestamp or self.created
        if not timestamp:
            return None
        if isinstance(style, str):
            style = [style]
        return separator.join([fdt(timestamp, style=s) for s in style])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "photo": self.photo,
            "yt_handle": self.yt_handle,
            "twitter": self.twitter,
            "twitter_id": self.twitter_id,
            "inactive": self.inactive,
            "type": self.type
        }

    async def fetch_videos(self, **kwargs):
        return await self.client.fetch_channel_videos(self.id, "videos", **kwargs)

class Vtuber(BaseChannel):

    def __init__(self, client: HolodexClient, data: dict):
        super().__init__(client, data)
        if self.type != "vtuber":
            raise TypeError("Channel is not a vtuber.")
        self.english_name: str | None = data.get("english_name")
        self.org: Org | None = data.get("org")
        self.suborg: str | None = data.get("suborg")
        self.group: str | None = data.get("group") or (data.get("suborg", "") or "")[2:]
        self.clip_count: int | None = parse_int(data.get("clip_count"))
        self.comments_crawled_at: datetime | None = parse_time(data.get("comments_crawled_at"))
        self.top_topics: list = [Topic.from_str(client, t) for t in data.get("top_topics", []) or []]
        self.twitch: str | None = data.get("twitch")
        self.twitter_id: int | None = parse_int(data.get("twitter_id"))

        self.transform()

    def transform(self):
        if isinstance(self.org, str):
            self.org = self.client.get_org(self.org) or Org(self.client, self.org)

    def __str__(self):
        return self.english_name or self.name

    def __repr__(self):
        return f'<Vtuber id={self.id} name={self.name!r} english_name={self.english_name!r}>'

    @property
    def full_org(self):
        return self.org.name + f'{f" {self.group}" if self.group else ""}'

    @property
    def twitch_url(self):
        if self.twitch:
            return f'https://twitch.tv/{self.twitch}'
        return None

    @property
    def twitch_hyperlink(self):
        if self.twitch:
            return f'[{ed(self.twitch)}]({self.twitch_url})'
        return

    def convert_dict(self):
        return {
            "name": self.name,
            "display": self.english_name,
            "org": self.org.name if self.org else None,
            "group": self.group,
            "image": self.photo,
            "brand": self.handle,
            "twitter": self.twitter,
            "twitter_id": self.twitter_id,
            "twitch": self.twitch,
            "inactive": self.inactive,
        }

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "english_name": self.english_name,
            "org": self.org,
            "group": self.group,
            "photo": self.photo,
            "yt_handle": self.yt_handle,
            "twitter": self.twitter,
            "twitch": self.twitch,
            "inactive": self.inactive,
            "type": self.type
        }

    async def fetch_clips(self, **kwargs):
        return await self.client.fetch_channel_videos(self.id, "clips", **kwargs)

    async def fetch_collabs(self, **kwargs):
        return await self.client.fetch_channel_videos(self.id, "collabs", **kwargs)

    async def add_placeholder(self, *args, **kwargs):
        return await self.client.add_placeholder(self.id, *args, **kwargs)

class Clipper(BaseChannel):

    def __init__(self, client: HolodexClient, data: dict):
        super().__init__(client, data)
        if self.type != "subber":
            raise TypeError("Channel is not a clipper.")
        self.lang: str | None = data.get("lang")

    def __repr__(self):
        return f'<Clipper id={self.id} name={self.name!r}>'
