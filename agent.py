from __future__ import annotations
import argparse, json
from pathlib import Path
from downloader import download_audio
from transcriber import transcribe
from exporters.txt import write_txt
from exporters.srt import write_srt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--lang", default="es")
    ap.add_argument("--model", default="small", choices=["tiny","base","small","medium","large-v3"])
    ap.add_argument("--device", default="cuda", choices=["cuda","cpu"])
    args = ap.parse_args()

    meta = download_audio(args.url, out_dir="outputs")
    segs, info = transcribe(meta["audio_path"], lang=args.lang, model_size=args.model, device=args.device)

    base = Path("outputs") / meta["video_id"]
    base.parent.mkdir(exist_ok=True, parents=True)

    write_txt(segs, f"{base}.txt")
    write_srt(segs, f"{base}.srt")

    with open(f"{base}.json", "w", encoding="utf-8") as f:
        json.dump({"video": meta, "model": args.model, "info": {
            "language": getattr(info, "language", None),
            "duration": getattr(info, "duration", None)
        }, "segments": segs}, f, ensure_ascii=False, indent=2)

    print("OK")
    print("TXT:", f"{base}.txt")
    print("SRT:", f"{base}.srt")
    print("JSON:", f"{base}.json")

if __name__ == "__main__":
    main()
