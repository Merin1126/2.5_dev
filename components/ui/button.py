from typing import Callable, Literal
import customtkinter as ctk
from config.settings import Color

class Button(ctk.CTkButton):
    def __init__(
        self,
        master,
        text: str = "Button",
        textColor: str | tuple = Color.TEXT_WHITE,
        fontFamily: str = "Arial",
        fontSize: int = 14,
        fontWeight: Literal["normal", "bold"] = "bold",
        width: int = 300,
        height: int = 40,
        cornerRadius: int = 16,
        command: Callable = lambda: print("Button pressed!"),
        **kwargs,
    ) -> None:
        
        # 自动帮你把字体和字号打包好
        font = ctk.CTkFont(family=fontFamily, size=fontSize, weight=fontWeight)
        kwargs.setdefault("text_color", textColor)
        kwargs.setdefault("fg_color", Color.PRIMARY)
        kwargs.setdefault("hover_color", Color.PRIMARY_HOVER)

        super().__init__(
            master=master,
            width=width,
            height=height,
            corner_radius=cornerRadius,
            text=text,
            font=font,
            command=command,
            **kwargs,
        )