"""
Agrandit en haute qualité les frames du guy (PNG avec transparence) avec Real-ESRGAN.

Usage (depuis la racine du projet) :
    python tools/upscaler/upscale.py
    python tools/upscaler/upscale.py --input img/chorus --output img/chorus_hd --scale 8

Au premier lancement, l'exécutable Real-ESRGAN (ncnn/Vulkan, ~45 Mo) est téléchargé
dans tools/upscaler/bin/. Tout tourne en local sur le GPU, aucune API n'est nécessaire.

Real-ESRGAN ne gère pas la transparence : l'image est agrandie sur fond uni, le masque
de transparence est agrandi à part, puis les deux sont recombinés.
"""

import argparse
import io
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BIN_DIR = Path(__file__).resolve().parent / "bin"
EXE = BIN_DIR / "realesrgan-ncnn-vulkan.exe"
RELEASE_URL = (
    "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/"
    "realesrgan-ncnn-vulkan-20220424-windows.zip"
)
MODEL_FACTOR = 4  # tous les modèles utilisés ici agrandissent x4


def ensure_binary():
    if EXE.exists():
        return
    print("Téléchargement de Real-ESRGAN (~45 Mo)...")
    data = urllib.request.urlopen(RELEASE_URL).read()
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if name.endswith((".exe", ".dll")) or name.startswith("models/"):
                target = BIN_DIR / name
                if name.endswith("/"):
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
    print("Real-ESRGAN installé dans", BIN_DIR)


def run_esrgan(src_dir, dst_dir, model):
    cmd = [str(EXE), "-i", str(src_dir), "-o", str(dst_dir), "-n", model, "-s", str(MODEL_FACTOR), "-f", "png"]
    result = subprocess.run(cmd, cwd=BIN_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit("Real-ESRGAN a échoué :\n" + result.stderr)


def main():
    parser = argparse.ArgumentParser(description="Upscale haute qualité des frames du guy")
    parser.add_argument("--input", default="img/chorus", help="dossier des PNG d'origine")
    parser.add_argument("--output", default="img/chorus_hd", help="dossier des PNG agrandis")
    parser.add_argument("--scale", type=int, default=8, help="facteur d'agrandissement final")
    parser.add_argument("--prescale", type=int, default=2,
                        help="pré-agrandissement pixel par pixel avant l'IA (aide sur les très petits sprites)")
    parser.add_argument("--model", default="realesrgan-x4plus-anime",
                        help="modèle Real-ESRGAN (realesrgan-x4plus-anime, realesr-animevideov3-x4, realesrgan-x4plus)")
    parser.add_argument("--background", default="#ffffff",
                        help="couleur de fond pendant l'agrandissement (celle du contour du sprite)")
    args = parser.parse_args()

    src = (ROOT / args.input).resolve()
    dst = (ROOT / args.output).resolve()
    files = sorted(src.glob("*.png"))
    if not files:
        sys.exit("Aucun PNG trouvé dans " + str(src))

    ensure_binary()
    dst.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_in = Path(tmp) / "in"
        tmp_out = Path(tmp) / "out"
        tmp_in.mkdir()
        tmp_out.mkdir()

        # Sépare chaque frame en couleur (sur fond uni) + masque de transparence
        sizes = {}
        for f in files:
            img = Image.open(f).convert("RGBA")
            sizes[f.name] = img.size
            pre = (img.width * args.prescale, img.height * args.prescale)
            color = Image.new("RGBA", img.size, args.background)
            color.alpha_composite(img)
            color.convert("RGB").resize(pre, Image.NEAREST).save(tmp_in / ("c_" + f.name))
            img.getchannel("A").convert("RGB").resize(pre, Image.NEAREST).save(tmp_in / ("a_" + f.name))

        print("Agrandissement de %d frames avec %s..." % (len(files), args.model))
        run_esrgan(tmp_in, tmp_out, args.model)

        # Recombine couleur + transparence à la taille finale
        for f in files:
            w, h = sizes[f.name]
            final = (w * args.scale, h * args.scale)
            color = Image.open(tmp_out / ("c_" + f.name)).convert("RGB").resize(final, Image.LANCZOS)
            alpha = Image.open(tmp_out / ("a_" + f.name)).convert("L").resize(final, Image.LANCZOS)
            # Nettoie le halo : quasi transparent -> transparent, quasi opaque -> opaque
            alpha = alpha.point(lambda v: 0 if v < 16 else 255 if v > 239 else v)
            out = color.convert("RGBA")
            out.putalpha(alpha)
            out.save(dst / f.name, optimize=True)

    print("%d frames écrites dans %s (%dx%d chacune)" % (
        len(files), dst, sizes[files[0].name][0] * args.scale, sizes[files[0].name][1] * args.scale))


if __name__ == "__main__":
    main()
