"""Gera os áudios neurais PT-BR da Academia Heurístika via edge-tts,
calcula a duração exata a partir dos quadros MPEG (sem depender de ffmpeg)
e grava o manifesto sincronizado em static/audio/academia_audio_manifest.json.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

import edge_tts

import academy_data

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "static" / "audio"
MANIFEST_PATH = AUDIO_DIR / "academia_audio_manifest.json"
TTS_RATE = "-2%"
INTER_CHAPTER_PAUSE_FRAMES = 15  # 15 * 0.024s = 0.360s em MPEG-2 24kHz
MIN_BYTES = 200_000
MIN_DURATION_SEC = 180.0

_BITRATES_V1_L1 = [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 0]
_BITRATES_V1_L2 = [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 0]
_BITRATES_V1_L3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
_BITRATES_V2_L1 = [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 0]
_BITRATES_V2_L23 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]

_SAMPLE_RATES = {
    3: [44100, 48000, 32000],  # MPEG 1
    2: [22050, 24000, 16000],  # MPEG 2
    0: [11025, 12000, 8000],   # MPEG 2.5
}


def _skip_id3v2(data: bytes) -> int:
    """Retorna o deslocamento inicial após eventual tag ID3v2."""
    if len(data) >= 10 and data[:3] == b"ID3":
        flags = data[5]
        size = (
            ((data[6] & 0x7F) << 21)
            | ((data[7] & 0x7F) << 14)
            | ((data[8] & 0x7F) << 7)
            | (data[9] & 0x7F)
        )
        offset = 10 + size + (10 if (flags & 0x10) else 0)
        return min(offset, len(data))
    return 0


def _parse_mpeg_frame_header(header: bytes) -> dict[str, Any] | None:
    """Decodifica um cabeçalho MPEG Audio de 4 bytes."""
    if len(header) < 4:
        return None
    b0, b1, b2, b3 = header[0], header[1], header[2], header[3]
    if b0 != 0xFF or (b1 & 0xE0) != 0xE0:
        return None

    ver_bits = (b1 >> 3) & 0x03
    layer_bits = (b1 >> 1) & 0x03
    bitrate_idx = (b2 >> 4) & 0x0F
    sr_idx = (b2 >> 2) & 0x03
    padding = (b2 >> 1) & 0x01
    channel_mode = (b3 >> 6) & 0x03

    if ver_bits == 1 or layer_bits == 0 or bitrate_idx in (0, 15) or sr_idx == 3:
        return None

    sample_rate = _SAMPLE_RATES[ver_bits][sr_idx]
    is_mpeg1 = ver_bits == 3

    if layer_bits == 3:  # Layer I
        bitrate_kbps = (_BITRATES_V1_L1 if is_mpeg1 else _BITRATES_V2_L1)[bitrate_idx]
        samples_per_frame = 384
        frame_size = ((12 * bitrate_kbps * 1000 // sample_rate) + padding) * 4
        unpadded_size = (12 * bitrate_kbps * 1000 // sample_rate) * 4
    elif layer_bits == 2:  # Layer II
        bitrate_kbps = (_BITRATES_V1_L2 if is_mpeg1 else _BITRATES_V2_L23)[bitrate_idx]
        samples_per_frame = 1152
        frame_size = (144 * bitrate_kbps * 1000 // sample_rate) + padding
        unpadded_size = 144 * bitrate_kbps * 1000 // sample_rate
    else:  # Layer III
        bitrate_kbps = (_BITRATES_V1_L3 if is_mpeg1 else _BITRATES_V2_L23)[bitrate_idx]
        samples_per_frame = 1152 if is_mpeg1 else 576
        coeff = 144 if is_mpeg1 else 72
        frame_size = (coeff * bitrate_kbps * 1000 // sample_rate) + padding
        unpadded_size = coeff * bitrate_kbps * 1000 // sample_rate

    if bitrate_kbps <= 0 or frame_size < 4:
        return None

    if layer_bits == 1:
        side_info_bytes = (32 if channel_mode != 3 else 17) if is_mpeg1 else (17 if channel_mode != 3 else 9)
    else:
        side_info_bytes = 0

    return {
        "version_bits": ver_bits,
        "layer_bits": layer_bits,
        "bitrate_kbps": bitrate_kbps,
        "sample_rate": sample_rate,
        "padding": padding,
        "channel_mode": channel_mode,
        "samples_per_frame": samples_per_frame,
        "frame_size": frame_size,
        "unpadded_size": unpadded_size,
        "side_info_bytes": side_info_bytes,
        "frame_duration": samples_per_frame / float(sample_rate),
    }


def _is_vbr_info_frame(data: bytes, pos: int, info: dict[str, Any]) -> bool:
    """Detecta quadros de metadados Xing/Info/VBRI que não contêm áudio real."""
    xing_pos = pos + 4 + info["side_info_bytes"]
    if xing_pos + 4 <= len(data) and data[xing_pos : xing_pos + 4] in (b"Xing", b"Info"):
        return True
    vbri_pos = pos + 36
    if vbri_pos + 4 <= len(data) and data[vbri_pos : vbri_pos + 4] == b"VBRI":
        return True
    return False


def analyze_mp3_stream(data: bytes) -> dict[str, Any]:
    """Calcula duração exata (segundos) e contagem de quadros direto do bitstream MP3."""
    pos = _skip_id3v2(data)
    end = len(data)
    if end >= 128 and data[end - 128 : end - 125] == b"TAG":
        end -= 128

    total_sec = 0.0
    audio_frames = 0
    first_header: bytes | None = None
    first_info: dict[str, Any] | None = None

    while pos + 4 <= end:
        if data[pos] != 0xFF or (data[pos + 1] & 0xE0) != 0xE0:
            pos += 1
            continue

        info = _parse_mpeg_frame_header(data[pos : pos + 4])
        if info is None or pos + info["frame_size"] > end:
            pos += 1
            continue

        # Valida sincronia no próximo quadro quando ainda há dados após o atual
        next_pos = pos + info["frame_size"]
        if next_pos + 4 <= end:
            if data[next_pos] != 0xFF or (data[next_pos + 1] & 0xE0) != 0xE0:
                if audio_frames == 0:
                    pos += 1
                    continue

        if first_header is None:
            first_header = data[pos : pos + 4]
            first_info = info

        if not _is_vbr_info_frame(data, pos, info):
            total_sec += info["frame_duration"]
            audio_frames += 1

        pos = next_pos

    return {
        "duration_seconds": total_sec,
        "frames": audio_frames,
        "first_header": first_header,
        "first_info": first_info,
    }


def make_silence_padding(first_header: bytes | None, first_info: dict[str, Any] | None, num_frames: int) -> tuple[bytes, float]:
    """Cria quadros MPEG Layer III silenciosos com exatamente os mesmos parâmetros do stream."""
    if not first_header or not first_info or num_frames <= 0:
        return b"", 0.0
    # Zera o bit de padding no byte 2 para usar unpadded_size uniforme
    b0, b1, b2, b3 = first_header[0], first_header[1], first_header[2] & 0xFD, first_header[3]
    clean_hdr = bytes([b0, b1, b2, b3])
    frame_bytes = clean_hdr + b"\x00" * (first_info["unpadded_size"] - 4)
    return frame_bytes * num_frames, num_frames * first_info["frame_duration"]


def _split_sentences_fallback(roteiro: str, rel_duration: float) -> list[dict[str, Any]]:
    """Fallback proporcional caso o serviço não retorne eventos SentenceBoundary."""
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", roteiro.strip()) if s.strip()]
    if not parts:
        parts = [roteiro.strip()]
    total_chars = max(1, sum(len(p) for p in parts))
    usable_start = 0.08
    usable_span = max(0.5, rel_duration - 0.16)
    cursor = usable_start
    result: list[dict[str, Any]] = []
    for p in parts:
        span = usable_span * (len(p) / total_chars)
        result.append({"rel_start": cursor, "rel_end": cursor + span, "texto": p})
        cursor += span
    return result


def _group_word_boundaries(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrupa WordBoundary em frases legíveis caso SentenceBoundary venha vazio."""
    if not words:
        return []
    grouped: list[dict[str, Any]] = []
    buf_words: list[str] = []
    seg_start = words[0]["offset"] / 10_000_000.0
    last_end = seg_start
    for w in words:
        txt = str(w.get("text", "")).strip()
        if not txt:
            continue
        w_start = w["offset"] / 10_000_000.0
        w_end = (w["offset"] + w.get("duration", 0)) / 10_000_000.0
        if not buf_words:
            seg_start = w_start
        buf_words.append(txt)
        last_end = max(w_end, w_start + 0.15)
        if txt.endswith((".", "!", "?")) or len(buf_words) >= 14:
            grouped.append({"rel_start": seg_start, "rel_end": last_end, "texto": " ".join(buf_words)})
            buf_words = []
    if buf_words:
        grouped.append({"rel_start": seg_start, "rel_end": last_end, "texto": " ".join(buf_words)})
    return grouped


async def synthesize_chapter(roteiro: str, voice: str, rate: str = TTS_RATE) -> dict[str, Any]:
    """Sintetiza um capítulo via edge-tts com retentativas e extrai legendas sincronizadas."""
    last_err: Exception | None = None
    for attempt in range(1, 4):
        try:
            comm = edge_tts.Communicate(roteiro, voice, rate=rate, boundary="SentenceBoundary")
            audio = bytearray()
            sentences: list[dict[str, Any]] = []
            async for chunk in comm.stream():
                ctype = chunk.get("type")
                if ctype == "audio":
                    audio.extend(chunk["data"])
                elif ctype == "SentenceBoundary":
                    txt = str(chunk.get("text", "")).strip()
                    if txt:
                        rel_start = chunk["offset"] / 10_000_000.0
                        rel_end = (chunk["offset"] + chunk.get("duration", 0)) / 10_000_000.0
                        sentences.append({
                            "rel_start": rel_start,
                            "rel_end": max(rel_end, rel_start + 0.35),
                            "texto": txt,
                        })
            stream_bytes = bytes(audio)
            stream_info = analyze_mp3_stream(stream_bytes)
            if not stream_bytes or stream_info["duration_seconds"] <= 0:
                raise RuntimeError("Stream MP3 vazio retornado pelo edge-tts.")

            if not sentences:
                # Fallback 1: WordBoundary
                word_comm = edge_tts.Communicate(roteiro, voice, rate=rate, boundary="WordBoundary")
                word_events: list[dict[str, Any]] = []
                async for wchunk in word_comm.stream():
                    if wchunk.get("type") == "WordBoundary":
                        word_events.append(wchunk)
                sentences = _group_word_boundaries(word_events)
            if not sentences:
                # Fallback 2: divisão proporcional por sentenças
                sentences = _split_sentences_fallback(roteiro, stream_info["duration_seconds"])

            return {
                "audio_bytes": stream_bytes,
                "duration_seconds": stream_info["duration_seconds"],
                "frames": stream_info["frames"],
                "first_header": stream_info["first_header"],
                "first_info": stream_info["first_info"],
                "sentences": sentences,
            }
        except Exception as exc:
            last_err = exc
            if attempt < 3:
                await asyncio.sleep(1.2 * attempt)
    raise RuntimeError(f"Falha ao sintetizar capítulo após 3 tentativas: {last_err}") from last_err


async def build_all_module_audios() -> dict[str, Any]:
    """Sintetiza os 4 módulos (20 capítulos), concatena os MP3s e grava o manifesto."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    manifest_modules: dict[str, Any] = {}

    for mod in academy_data.MODULOS_EDUCACIONAIS:
        num = mod["numero"]
        video = mod["video_aula"]
        voice = video["audio_voz"]
        audio_url = video["audio_url"]
        out_path = AUDIO_DIR / Path(audio_url).name
        chapters = video["capitulos"]

        print(f"\n=== Módulo {num} ({voice}) ===")
        mod_stream = bytearray()
        cumulative_sec = 0.0
        cap_manifest: list[dict[str, Any]] = []

        for idx, cap in enumerate(chapters):
            roteiro = cap["roteiro"].strip()
            word_count = len(roteiro.split())
            res = await synthesize_chapter(roteiro, voice, rate=TTS_RATE)
            chap_start = cumulative_sec
            chap_dur = res["duration_seconds"]

            legendas: list[dict[str, Any]] = []
            for s in res["sentences"]:
                abs_ini = round(chap_start + s["rel_start"], 3)
                abs_fim = round(min(chap_start + chap_dur, chap_start + s["rel_end"]), 3)
                if abs_fim <= abs_ini:
                    abs_fim = round(abs_ini + 0.35, 3)
                legendas.append({
                    "inicio": abs_ini,
                    "fim": abs_fim,
                    "texto": academy_data.format_subtitle_text(s["texto"]),
                })

            mod_stream.extend(res["audio_bytes"])
            cumulative_sec += chap_dur

            # Pausa silenciosa limpa entre capítulos (não após o último)
            pause_sec = 0.0
            if idx < len(chapters) - 1:
                pad_bytes, pause_sec = make_silence_padding(
                    res["first_header"], res["first_info"], INTER_CHAPTER_PAUSE_FRAMES
                )
                mod_stream.extend(pad_bytes)
                cumulative_sec += pause_sec

            cap_manifest.append({
                "index": idx,
                "titulo": cap["titulo"],
                "tempo_inicio": round(chap_start, 3),
                "duracao_segundos": round(chap_dur, 3),
                "pausa_apos_segundos": round(pause_sec, 3),
                "palavras": word_count,
                "legendas": legendas,
            })
            print(
                f"  Cap {idx + 1}: inicio={chap_start:6.2f}s | dur={chap_dur:5.2f}s | "
                f"palavras={word_count:3d} | legendas={len(legendas):2d}"
            )

        final_bytes = bytes(mod_stream)
        out_path.write_bytes(final_bytes)
        verified = analyze_mp3_stream(final_bytes)
        verified_dur = verified["duration_seconds"]
        size_bytes = out_path.stat().st_size

        print(
            f"-> Gravado {out_path.relative_to(BASE_DIR)} | {size_bytes:,} bytes | "
            f"duração real MPEG={verified_dur:.2f}s (soma={cumulative_sec:.2f}s)"
        )

        if size_bytes <= MIN_BYTES:
            raise RuntimeError(f"MP3 {out_path} abaixo do tamanho mínimo ({size_bytes} bytes).")
        if verified_dur < MIN_DURATION_SEC:
            raise RuntimeError(
                f"MP3 {out_path} abaixo de {MIN_DURATION_SEC}s ({verified_dur:.2f}s). Expanda o roteiro!"
            )

        manifest_modules[num] = {
            "numero": num,
            "audio_url": audio_url,
            "audio_file": str(out_path.relative_to(BASE_DIR)).replace("\\", "/"),
            "audio_voz": voice,
            "bytes": size_bytes,
            "duracao_segundos": round(verified_dur, 3),
            "frames": verified["frames"],
            "capitulos": cap_manifest,
        }

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rate": TTS_RATE,
        "inter_chapter_pause_frames": INTER_CHAPTER_PAUSE_FRAMES,
        "modules": manifest_modules,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nManifesto salvo em {MANIFEST_PATH.relative_to(BASE_DIR)}")
    return manifest


def main() -> None:
    manifest = asyncio.run(build_all_module_audios())
    print("\n=== RESUMO FINAL DE ÁUDIO ===")
    for num, info in sorted(manifest["modules"].items()):
        sub_count = sum(len(c["legendas"]) for c in info["capitulos"])
        status = "OK (>=185s)" if info["duracao_segundos"] >= 185.0 else "ATENÇÃO (<185s)"
        print(
            f"Mód {num}: {info['duracao_segundos']:6.2f}s | {info['bytes']:>9,} bytes | "
            f"{sub_count:2d} legendas | {info['audio_voz']} | {status}"
        )


if __name__ == "__main__":
    main()
