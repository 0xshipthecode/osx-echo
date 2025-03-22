#!/usr/bin/env python

# copied from https://github.com/andrewferguson/pyanybar under MIT License
# to remove bug with unicode

import socket

colors = [
    "white",
    "red",
    "orange",
    "yellow",
    "green",
    "cyan",
    "blue",
    "purple",
    "black",
    "question",
    "exclamation",
    "none",
    "filled",
    "hollow",
]


class AnyBar:
    def __init__(self, port=1738, address="localhost"):
        self.port = port
        self.address = address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def change(self, color, text=None):
        if color not in colors:
            raise ValueError(
                "Color is not valid. It must be one of the "
                "following: {}".format(", ".join(colors))
            )

        if text is None:
            self.socket.sendto(color.encode("utf-8"), (self.address, self.port))
        else:
            message = "{} {}".format(color, text).encode("utf-8")
            self.socket.sendto(message, (self.address, self.port))
