class HolodexClient:

    def __init__(self, api_key: str = None, jwt: str = None, cls=None, cache: dict = None):
        self.api_key = api_key
        self.jwt = jwt
        self.cls = cls or Vtuber
        self.headers = None
        self.session = self.generate_session()

        self._vtubers = {}
        self._clippers = {}
        self._orgs = {}
        self._topics = {}
        self._videos: dict[str, BaseVideo] = {}
        self.mapping = {
            "vtuber": self._vtubers,
            "subber": self._clippers,
        }
        self.load_channels(cache or {})

    def get_headers(self):
        headers = {}
        if self.api_key:
            headers["X-APIKEY"] = self.api_key
        if self.jwt:
            headers["Authorization"] = f"BEARER {self.jwt}"
        return headers

    def generate_session(self):
        self.headers = self.get_headers()
        return aiohttp.ClientSession(headers=self.headers)
    
    async def request(self, method, endpoint, base=True, **kwargs):
        body = kwargs.pop("body", None)
        params = kwargs.pop("params", None)
        url = kwargs.pop("url", None) or fix_url(endpoint)
        if base:
            url = BASE_URL + url
        async with self.session.request(method, url, json=body, params=filter_params(params)) as r:
            await r.read()
        return r

    async def static(self, url, base=True, raw=False):
        if base:
            url = BASE_URL + url
        async with self.session.get(url) as r:
            await r.read()
        return await parse_type(r) if raw else r

    async def get(self, endpoint, body: dict = None, params: dict = None, raw=False):
        ret = await self.request("GET", endpoint, body=body, params=params)
        return await parse_type(ret) if raw else ret

    async def post(self, endpoint, body: dict = None, params: dict = None, raw=False):
        ret = await self.request("POST", endpoint, body=body, params=params)
        return await parse_type(ret) if raw else ret

    async def delete(self, endpoint, body: dict = None, params: dict = None, raw=False):
        ret = await self.request("DELETE", endpoint, body=body, params=params)
        return await parse_type(ret) if raw else ret

    @property
    def vtubers(self):
        return list(self._vtubers.values())

    @property
    def clippers(self):
        return list(self._clippers.values())

    @property
    def channels(self):
        return self.vtubers + self.clippers

    @property
    def orgs(self):
        return list(self._orgs.values())

    @property
    def topics(self):
        return list(self._topics.values())

    @property
    def videos(self):
        return list(self._videos.values())

    def load_channels(self, channels: dict):
        for channel_id, channel in channels.items():
            channel["id"] = channel_id
            ch = self.raw_channel(channel)
            self.write_channel(ch)

    def raw_channel(self, data, force_type=None):
        if force_type:
            data["type"] = force_type
        if data.get("type") == "vtuber":
            return self.cls(self, data)
        elif data.get("type") == "subber":
            return Clipper(self, data)

    def write_channel(self, channel):
        self.mapping[channel.type][channel.id] = channel
        if channel.type == "vtuber":
            self.insert_org(channel.org)

    def generate_channel(self, data):
        if not data:
            return None
        if not data.get("type"):
            data["type"] = "vtuber"
        return self.get_channel(data["id"]) or self.raw_channel(data)

    def get_channel(self, id: str):
        return get(self.channels, id=id)

    def find_channel(self, exact=False, **kwargs):
        j = self.find_channels(limit=1, exact=exact, **kwargs)
        if not j:
            return None
        return j[0]

    def lookup(self, name: str):
        return self.find_channel(name=name)

    def get_org(self, name: str):
        return get(self.orgs, name=name)

    def insert_org(self, org):
        if not org:
            return
        if not self.get_org(str(org)) and isinstance(org, Org):
            self._orgs[str(org)] = org

    def get_topic(self, name: str):
        if not name:
            return None
        return find(lambda t: t.id.lower() == name.lower(), self.topics)

    def gen_topic(self, name: str):
        if not name:
            return None
        return find(lambda t: t.id.lower() == name.lower(), self.topics) or Topic.from_str(self, name)

    def insert_topic(self, topic):
        if not topic:
            return
        if not self.get_topic(topic.id) and isinstance(topic, Topic):
            self._topics[topic.id] = topic

    def get_video(self, id: str):
        return get(self.videos, id=id)

    def insert_video(self, video):
        if not video:
            return
        if not self.get_video(str(video)) and isinstance(video, BaseVideo):
            self._videos[video.id] = video

    def find_channels(self, limit=None, exact=False, **kwargs):
        results = []
        l = 0
        pool = kwargs.pop("pool", self.channels)
        if not kwargs:
            return []
        for channel in pool:
            if limit and len(results) >= limit:
                break
            i = 0
            for k, v in kwargs.items():
                if (z := getattr(channel, k, None)) == v:
                    i += 1
                elif not exact and isinstance(v, str) and v.lower() in str(z).lower():
                    i += 1
            if i and i == len(kwargs):
                results.append(channel)
            # if (
            #     (channel.id == id if id else True)
            #     and (name.lower() in channel.name.lower() if name else True)
            #     and (org.lower() in channel.org.name.lower() if org else True)
            # ):
            #     results.append(channel)
        return results

    async def fetch_channel(self, channel_id: str):
        data = await self.get(f"channels/{channel_id}")
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            data = await data.json()
            if data.get("type") == "vtuber":
                return self.cls(self, data)
            elif data.get("type") == "subber":
                return Clipper(self, data)
        return data

    async def fetch_channels(
            self,
            limit: int = 25,
            offset: int = 0,
            type: ["vtuber", "subber"] = None,
            lang: str = None,
            order: ["asc", "desc"] = "asc",
            org: str = None,
            sort: str = None,
    ):
        params = {
            "limit": limit,
            "offset": offset,
            "type": type,
            "lang": lang,
            "order": order,
            "org": org,
            "sort": sort,
        }
        data = await self.get(f"channels", params=params)
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            channels = []
            data = await data.json()
            for channel in data:
                if channel.get("type") == "vtuber":
                    channels.append(self.cls(self, channel))
                elif channel.get("type") == "subber":
                    channels.append(Clipper(self, channel))
            return channels
        return data

    async def fetch_video(self, video_id: str):
        data = await self.get(f"videos/{video_id}")
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            data = await data.json()
            return BaseVideo.from_data(self, data)
        return data

    async def fetch_live(
            self,
            channel_id: str = None,
            id: str = None,
            include: list["clips", "refers", "sources", "simulcasts", "mentions", "description", "live_info", "channel_stats", "songs"] = None,
            limit: int = 25,
            max_upcoming_hours: int = None,
            offset: int = 0,
            mentioned_channel_id: str = None,
            type: ["stream", "clip", "placeholder"] = None,
            order: ["asc", "desc"] = "desc",
            org: str = None,
            sort: str = None,
            status: ["new", "upcoming", "live", "past", "missing"] = None,
            topic: str = None,
            paginated: bool = False,
    ):
        params = {
            "channel_id": channel_id,
            "id": id,
            "include": ",".join(include) if include else None,
            "limit": limit,
            "max_upcoming_hours": max_upcoming_hours,
            "mentioned_channel_id": mentioned_channel_id,
            "status": status,
            "topic": topic,
            "offset": offset,
            "type": type,
            "order": order,
            "org": org,
            "sort": sort,
            "paginated": paginated or None
        }
        data = await self.get(f"live", params=params)
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            videos = []
            data = await data.json()
            for video in data:
                videos.append(BaseVideo.from_data(self, video))
            return videos
        return data

    async def fetch_cached_live(self, *channel_ids):
        params = {"channels": ",".join(channel_ids)}
        data = await self.get(f"users/live", params=params)
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            videos = []
            data = await data.json()
            for video in data:
                videos.append(BaseVideo.from_data(self, video))
            return videos
        return data

    async def fetch_videos(
            self,
            channel_id: str = None,
            id: str = None,
            include: list["clips", "refers", "sources", "simulcasts", "mentions", "description", "live_info", "channel_stats", "songs"] = None,
            lang: str = None,
            limit: int = 25,
            max_upcoming_hours: int = None,
            offset: int = 0,
            mentioned_channel_id: str = None,
            type: ["stream", "clip", "placeholder"] = None,
            order: ["asc", "desc"] = "desc",
            org: str = None,
            sort: str = None,
            status: ["new", "upcoming", "live", "past", "missing"] = None,
            topic: str = None,
            after: datetime = None,
            before: datetime = None,
            paginated: bool = False,
    ):
        params = {
            "channel_id": channel_id,
            "id": id,
            "include": ",".join(include) if include else None,
            "limit": limit,
            "max_upcoming_hours": max_upcoming_hours,
            "mentioned_channel_id": mentioned_channel_id,
            "status": status,
            "topic": topic,
            "from": after.isoformat() if after else None,
            "to": before.isoformat() if before else None,
            "offset": offset,
            "type": type,
            "lang": lang,
            "order": order,
            "org": org,
            "sort": sort,
            "paginated": paginated or None
        }
        data = await self.get(f"videos", params=params)
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            videos = []
            data = await data.json()
            for video in data:
                videos.append(BaseVideo.from_data(self, video))
            return videos
        return data

    async def fetch_channel_videos(
        self,
        channel_id: str,
        video_type: ["clips", "videos", "collabs"],
        include: list["clips", "refers", "sources", "simulcasts", "mentions", "description", "live_info", "channel_stats", "songs"] = None,
        lang: str = None,
        limit: int = 25,
        offset: int = 0,
        paginated: bool = False,
    ):
        params = {
            "include": ",".join(include) if include else None,
            "limit": limit,
            "offset": offset,
            "lang": lang,
            "paginated": paginated or None
        }
        data = await self.get(f"channels/{channel_id}/{video_type}", params=params)
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            videos = []
            total = None
            data = await data.json()
            target = data
            if paginated:
                target = data.get("items")
                total = data.get("total")
            for video in target:
                videos.append(BaseVideo.from_data(self, video))
            return videos
        return data

    async def fetch_video_topic(self, video_id):
        data = await self.get(f"videos/{video_id}/topic")
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            data = await data.json()
            return Topic(self,data)
        return data

    async def edit_video_topic(self, video_id, topic_id):
        body = {"videoId": video_id, "topicId": topic_id}
        data = await self.post("topics/video", body)
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            data = await data.json()
        return data

    async def add_video_mention(self, video_id, channel_id):
        body = {"channel_id": channel_id}
        data = await self.post(f"videos/{video_id}/mentions", body)
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            data = await data.json()
        return data

    async def remove_video_mentions(self, video_id, *channel_ids):
        body = {"channel_ids": list(channel_ids)}
        data = await self.delete(f"videos/{video_id}/mentions", body)
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            data = await data.json()
        return data

    async def fetch_video_mentions(self, video_id):
        data = await self.get(f"videos/{video_id}/mentions")
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            data = await data.json()
        return data

    async def fetch_orgs(self):
        data = await self.static("/statics/orgs.json")
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            data = await data.json()
            return [Org(o) for o in data]
        return data

    async def fill_orgs(self):
        for o in await self.fetch_orgs():
            self.insert_org(o)

    async def fetch_topics(self):
        data = await self.static("/statics/topics.json")
        if data.status == 404:
            raise Exception(f"{await data.text()}")
        elif data.status == 200:
            data = await data.json()
            return [Topic(self, t) for t in data]
        return data

    async def fill_topics(self):
        for t in await self.fetch_topics():
            self.insert_topic(t)

    async def add_placeholder(
        self,
        channel_id: str,
        name: str,
        jp_name: str,
        link: str,
        thumbnail: str,
        duration: int,
        start_time: datetime,
        credits: PlaceholderCredits,
        type: ["scheduled-yt-stream", "external-stream", "event"] = "scheduled-yt-stream",
        certainty: ["likely", "certain"] = "certain",
        id: str = None
    ):
        if not self.api_key:
            raise ValueError("No API key provided.")
        body = {
            "channel_id": channel_id,
            "title": {
                "name": name,
                "jp_name": jp_name,
                "link": link,
                "thumbnail": thumbnail,
                "placeholderType": type,
                "certainty": certainty,
                "credits": credits.to_dict()
            },
            "liveTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration": duration
        }
        if id:
            body["id"] = id
        data = await self.post("videos/placeholder", body)
        if data.status == 200:
            base = await data.json()
            try:
                vdata = base[0]
                return BaseVideo.from_data(self, vdata)
            except:
                vdata = base.get("placeholder")
                if vdata and (msg := base.get("error")):
                    vid = BaseVideo.from_data(self, vdata)
                    err = ValueError(msg + f" (id {vid.id})")
                    err.placeholder = vid
                    raise err
        return data

    async def delete_placeholder(self, id):
        return await self.delete(f'videos/placeholder/{id}')
            
    async def notice(self, id):
        body = {"url": id}
        data = await self.post("external/notice", body, raw=True)
        try:
            return data.get('state', data)
        except:
            return data
