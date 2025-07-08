class YoutubeResult:
    def __init__(self, d=None):
        if d is not None:
            for key, value in d.items():
                setattr(self, key, value)

                if 'url_suffix' in key:
                    if 'list' in self.url_suffix:
                        self.url_suffix = self.url_suffix.split('&')[0]
