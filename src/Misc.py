from operator import attrgetter

class PlaceholderCredits:

    @staticmethod
    def from_data(data: dict):
        if not data: return
        for k, v in data.items():
            name = v.get("name")
            link = v.get("link")
            user = v.get("user")
            return PlaceholderCredits(k, name=name, link=link, user=user)

    def __init__(self, type: str, name: str=None, link: str=None, user: str=None):
        self.type = type
        self.name = name
        self.link = link
        self.user = user

    def __str__(self):
        base = f"<PlaceholderCredits type={self.type} "
        ext = " ".join([f"{attr}={getattr(self, attr)}" for attr in ["name", "link", "user"] if getattr(self, attr)])
        return base + ext + ">"

    def to_dict(self):
        ret = {f"{self.type}": {}}
        if self.name:
            ret[self.type]["name"] = self.name
        if self.link:
            ret[self.type]["link"] = self.link
        if self.user:
            ret[self.type]["user"] = self.user
        return ret
        

class Comment:

    def __init__(self, data: dict):
        self.comment_key: str = data.get("comment_key")
        self.video_id: str = data.get("video_id")
        self.message: str = data.get("message")

class Org:

    def __init__(self, client: HolodexClient, name: str):
        self.client = client
        self.name = name

    def __repr__(self):
        return f'<Org name={self.name!r} members={len(self.members)}>'

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if not isinstance(other, Org):
            return False
        return self.name == other.name

    @property
    def members(self):
        return self.client.find_channels(org=self)

    @property
    def groups(self):
        allGroups = [v.group for v in self.members if v.group]
        return list(set(allGroups))

    async def fetch_videos(self, **kwargs):
        return await self.client.fetch_videos(org=self.name, **kwargs)

class Topic:

    @staticmethod
    def from_str(client: HolodexClient, name: str):
        return Topic(client, {"id": name})

    def __init__(self, client: HolodexClient, data: dict):
        self.client = client
        self.id: str = data["id"]
        self.count: int = data.get("count", None)
        self.approver_id: int = data.get("topic_approver_id", data.get("approver_id", None))

    def __repr__(self):
        return f'<Topic id={self.id!r}> count={self.count}>'

    def __str__(self):
        return self.id

    def __eq__(self, other):
        if not isinstance(other, Topic):
            return False
        return self.id == other.id

    async def fetch_videos(self, **kwargs):
        return await self.client.fetch_videos(topic=self.id, **kwargs)