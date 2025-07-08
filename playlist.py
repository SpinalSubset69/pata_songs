class PlayList():
    def __init__(self):
        self.play_list_dic = dict()
        self.current_index_dic = dict()

    def add_to_playlist(self, connection_id, audio_name):
        # validate if key has values        
        if connection_id not in self.play_list_dic:
            self.play_list_dic[connection_id] = [audio_name]
            # Set current index for connection, since is a new playlist
            self.current_index_dic[connection_id] = 0
        else:
            old_values = self.play_list_dic[connection_id]
            old_values.append(audio_name)
            self.play_list_dic[connection_id] = old_values                    

    def get_next_song(self, connection_id):
        # Get play lsit and current index
        playlist = self.play_list_dic[connection_id]
        current_idx = self.current_index_dic[connection_id]

        if len(playlist) < current_idx:
            return ''

        song_name = playlist[current_idx]
        self.current_index_dic[connection_id] += 1
        
        return song_name
    
    def reset_play_list(self, connection_id):
        self.play_list_dic[connection_id] = []
        self.current_index_dic[connection_id] = 0

    def get_playlist_lenght(self, connection_id):
        return len(self.play_list_dic[connection_id])

    def get_current_playlist_index(self, connection_id):
        return self.current_index_dic[connection_id]
