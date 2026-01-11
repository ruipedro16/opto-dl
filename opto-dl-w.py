#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from subprocess import run

if __name__ == "__main__":
    urls: list[str] = sys.argv[1:]

    for url in urls:

        fields = url.replace("https://", "").replace("http://", "").split("/")

        run(
            [
                "./opto-dl,py",
                "-v",
                "--url",
                url,
                "-o",
                f"data/{fields[2]}.mp4",
            ]
        )
