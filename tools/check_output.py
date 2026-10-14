"""Check that an inspection run's output matches the format we score.

    python tools/check_output.py results/ [--images data/val/bad]

Checks every results/<name>.json. With --images, also checks there is one result per image.
Exit code 0 = format OK. This checks the FORMAT only, not whether your verdicts are right.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

W, H = 1024, 768
VERDICTS = {"PASS", "FAIL", "UNKNOWN"}


def check_one(p: Path) -> list[str]:
    errs = []
    try:
        j = json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        return [f"not valid JSON ({e})"]
    if not isinstance(j, dict):
        return ["top level must be a JSON object"]
    img = j.get("image")
    if not isinstance(img, str) or not img.endswith(".jpg"):
        errs.append('"image" must be the input file name, e.g. "img_123456.jpg"')
    elif Path(img).stem != p.stem:
        errs.append(f'"image" is {img!r} but the file is {p.name} (must be <image stem>.json)')
    v = j.get("verdict")
    if v not in VERDICTS:
        errs.append(f'"verdict" must be one of {sorted(VERDICTS)}, got {v!r}')
    if "score" not in j:
        errs.append('"score" is missing (use null if you have none, e.g. for UNKNOWN)')
    elif j["score"] is not None and not isinstance(j["score"], (int, float)):
        errs.append('"score" must be a number or null')
    t = j.get("time_ms")
    if not isinstance(t, (int, float)) or t < 0:
        errs.append('"time_ms" must be a non-negative number')
    d = j.get("defects")
    if not isinstance(d, list):
        errs.append('"defects" must be a list (empty for PASS/UNKNOWN)')
        d = []
    for k, item in enumerate(d):
        b = item.get("bbox") if isinstance(item, dict) else None
        if not (isinstance(b, list) and len(b) == 4 and all(isinstance(x, (int, float)) for x in b)):
            errs.append(f"defects[{k}].bbox must be [x, y, width, height] in pixels")
            continue
        x, y, w, h = b
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > W or y + h > H:
            errs.append(f"defects[{k}].bbox {b} is not inside the {W}x{H} image")
        if not isinstance(item.get("size_mm"), (int, float)):
            errs.append(f"defects[{k}].size_mm must be a number")
    if v == "FAIL" and not d:
        errs.append("a FAIL with no defects cannot be checked against the defect position: "
                    "it will be scored as a miss")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("--images", type=Path, help="input image folder, to check nothing is missing")
    a = ap.parse_args()
    files = sorted(p for p in a.results.glob("*.json"))
    if not files:
        print(f"no .json files in {a.results}")
        return 1
    bad = 0
    for p in files:
        errs = check_one(p)
        if errs:
            bad += 1
            for e in errs:
                print(f"{p.name}: {e}")
    missing = []
    if a.images:
        have = {p.stem for p in files}
        missing = [p.name for p in sorted(a.images.glob("*.jpg")) if p.stem not in have]
        for m in missing:
            print(f"missing result for {m}")
    if not (a.results / "summary.csv").exists():
        print("note: results/summary.csv not found (required, but not used for scoring)")
    print(f"\n{len(files)} result files, {bad} with problems, {len(missing)} images without a result")
    return 0 if bad == 0 and not missing else 1


if __name__ == "__main__":
    sys.exit(main())
