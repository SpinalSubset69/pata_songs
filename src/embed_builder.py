from typing import Literal

from discord import Color, Embed


class EmbedBuilder():
    def __init__(self) -> None:
        self.title: Literal[''] = ''
        self.description: Literal['']   = ''
        self.url: Literal['']= ''
        self.color: Color = Color.green()        

    def set_title(self, title) :
        if not title == '':
            self.title = title
        
        return self
    
    def set_description(self, description) :
        if not description == '':
            self.description = description
        
        return self
    
    def set_url(self, url) :
        if not url == '':
            self.url = url
        
        return self
    
    def set_color(self, color) :
        if not color == '':
            self.color = color
        
        return self
    
    def build(self) -> Embed:
        embed = Embed()        
        
        if self.title != '':
            embed.title = self.title
        
        if self.url != '':
            embed.url = self.url
        
        if self.description != '':
            embed.description = self.description     
                
        embed.color = self.color

        embed.set_author(name="Pata Song\'s Bot", icon_url="https://i.pinimg.com/736x/ef/36/7a/ef367a19d45c7340bd85ca53a46353ca.jpg")

        return embed   
        