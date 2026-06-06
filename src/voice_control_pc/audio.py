"""Audio device helpers."""

from __future__ import annotations

import wave
from pathlib import Path

from voice_control_pc.models import AudioSettings


def list_input_devices() -> list[dict[str, str | int]]:
    try:
        import pyaudio
    except ImportError as error:
        raise RuntimeError("PyAudio не установлен") from error

    audio = pyaudio.PyAudio()
    devices: list[dict[str, str | int]] = []
    try:
        for index in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(index)
            if int(info.get("maxInputChannels", 0)) > 0:
                devices.append(
                    {
                        "index": index,
                        "name": str(info.get("name", f"device-{index}")),
                        "channels": int(info.get("maxInputChannels", 0)),
                    }
                )
    finally:
        audio.terminate()
    return devices


def record_microphone_to_wav(
    output_path: Path,
    settings: AudioSettings,
    duration_seconds: int | None = None,
    device_index: int | None = None,
) -> Path:
    try:
        import pyaudio
    except ImportError as error:
        raise RuntimeError("PyAudio не установлен") from error

    audio = pyaudio.PyAudio()
    sample_format = _resolve_sample_format(pyaudio, settings.sample_format)
    duration = duration_seconds if duration_seconds is not None else settings.max_seconds
    input_device_index = device_index if device_index is not None else settings.device_index

    frames: list[bytes] = []
    stream = audio.open(
        format=sample_format,
        channels=settings.channels,
        rate=settings.sample_rate,
        input=True,
        frames_per_buffer=settings.chunk_size,
        input_device_index=input_device_index,
    )

    try:
        total_chunks = int(settings.sample_rate / settings.chunk_size * duration)
        for _ in range(total_chunks):
            frames.append(stream.read(settings.chunk_size, exception_on_overflow=False))
    finally:
        stream.stop_stream()
        stream.close()
        sample_width = audio.get_sample_size(sample_format)
        audio.terminate()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(settings.channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(settings.sample_rate)
        wav_file.writeframes(b"".join(frames))

    return output_path


def _resolve_sample_format(pyaudio_module, sample_format: str):
    format_map = {
        "int16": pyaudio_module.paInt16,
        "int24": pyaudio_module.paInt24,
        "int32": pyaudio_module.paInt32,
        "float32": pyaudio_module.paFloat32,
    }
    if sample_format not in format_map:
        raise ValueError(f"Unsupported audio sample format: {sample_format}")
    return format_map[sample_format]
