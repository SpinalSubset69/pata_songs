from typing import Dict, List, Optional
from audio_track import AudioTrack


class PlayList:
    def __init__(self):
        self.play_list_dic: Dict[int, List[AudioTrack]] = {}
        self.current_index_dic: Dict[int, int] = {}

    def add_to_playlist(self, connection_id: int, track: AudioTrack):
        self.play_list_dic.setdefault(connection_id, []).append(track)
        self.current_index_dic.setdefault(connection_id, 0)

    def get_next_song(self, connection_id: int) -> Optional[AudioTrack]:
        playlist = self.play_list_dic.get(connection_id, [])
        idx = self.current_index_dic.get(connection_id, 0)

        if idx >= len(playlist):
            return None

        song = playlist[idx]
        self.current_index_dic[connection_id] = idx + 1
        return song

    def reset_play_list(self, connection_id: int):
        self.play_list_dic[connection_id] = []
        self.current_index_dic[connection_id] = 0

    def get_playlist_length(self, connection_id: int) -> int:
        return len(self.play_list_dic.get(connection_id, []))

    def get_current_playlist_index(self, connection_id: int) -> int:
        return self.current_index_dic.get(connection_id, 0)
