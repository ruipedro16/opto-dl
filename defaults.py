import os

DEFAULT_TIMEOUT: int = 15
DEFAULT_MAX_WORKERS: int = max(1, os.cpu_count() // 4)
DEFAULT_ENCRYPTED_AUDIO_FILENAME: str = "manifest [manifest].m4a"
DEFAULT_DECRYPTED_AUDIO_FILENAME: str = "OK_audio.m4a"
DEFAULT_ENCRYPTED_VIDEO_FILENAME: str = "manifest [manifest].mp4"
DEFAULT_DECRYPTED_VIDEO_FILENAME: str = "OK_video.mp4"
DEFAULT_MERGED_VIDEO_FILENAME: str = "Ficheiro_Final.mp4"
VIDEO_EXTENSIONS: list[str] = [".mp4", ".mkv"]  # TODO: add more if needed
