"""
Remet des frames redessinées à une taille et une position cohérentes entre elles.

Chaque image de --input est recalée sur le sprite DS du même nom (--reference), qui sont
tous à la même échelle et alignés sur les pieds :
  - le personnage (zone non transparente) est mis à l'échelle de celui du sprite DS ;
  - ses pieds (bas) et son centre horizontal sont alignés sur ceux du sprite DS ;
  - toutes les sorties ont la même toile : taille du sprite DS x --scale.

Usage (depuis la racine du projet) :
    python tools/normalize_frames.py
    python tools/normalize_frames.py --input img/chorus_hd2 --output img/chorus_hd2_fixed --scale 8
    python tools/normalize_frames.py --fit height
"""

import argparse
import math
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ALPHA_THRESHOLD = 16  # pixels plus transparents que ça ignorés pour mesurer le personnage


def content_bbox(img):
    alpha = img.getchannel("A").point(lambda v: 255 if v > ALPHA_THRESHOLD else 0)
    return alpha.getbbox()


def main():
    parser = argparse.ArgumentParser(description="Recale des frames sur la taille et la position des sprites DS")
    parser.add_argument("--input", default="img/chorus_hd2", help="dossier des frames redessinées")
    parser.add_argument("--reference", default="img/chorus", help="dossier des sprites DS de référence (mêmes noms)")
    parser.add_argument("--output", default="img/chorus_hd2_fixed", help="dossier de sortie")
    parser.add_argument("--scale", type=int, default=8, help="facteur de la toile de sortie par rapport au sprite DS")
    parser.add_argument("--fit", default="both", choices=["both", "height", "width"],
                        help="dimension utilisée pour l'échelle : both = moyenne hauteur/largeur (défaut)")
    args = parser.parse_args()

    src = ROOT / args.input
    ref_dir = ROOT / args.reference
    dst = ROOT / args.output
    files = sorted(src.glob("*.png"))
    if not files:
        sys.exit("Aucun PNG dans " + str(src))
    dst.mkdir(parents=True, exist_ok=True)

    print("%-12s %8s  %s" % ("frame", "échelle", "remarques"))
    scales = {}
    for f in files:
        ref_path = ref_dir / f.name
        if not ref_path.exists():
            print("%-12s ignorée : pas de sprite de référence %s" % (f.name, ref_path.name))
            continue
        ref = Image.open(ref_path).convert("RGBA")
        img = Image.open(f).convert("RGBA")
        rb, ib = content_bbox(ref), content_bbox(img)
        if not rb or not ib:
            print("%-12s ignorée : image vide" % f.name)
            continue

        # Taille visée du personnage dans la toile de sortie
        target_w = (rb[2] - rb[0]) * args.scale
        target_h = (rb[3] - rb[1]) * args.scale
        sw = target_w / (ib[2] - ib[0])
        sh = target_h / (ib[3] - ib[1])
        s = {"both": math.sqrt(sw * sh), "height": sh, "width": sw}[args.fit]
        scales[f.name] = s

        notes = []
        # Un personnage coupé par le bord de la toile d'origine sera mal mesuré
        if ib[0] == 0 or ib[1] == 0 or ib[2] == img.width or ib[3] == img.height:
            notes.append("touche le bord de l'image d'origine (dessin coupé ?)")
        # Proportions différentes du sprite DS : la largeur et la hauteur ne demandent pas la même échelle
        if abs(sw / sh - 1) > 0.15:
            notes.append("proportions différentes du sprite DS (larg. x%.2f / haut. x%.2f)" % (sw, sh))

        crop = img.crop(ib)
        crop = crop.resize((max(1, round(crop.width * s)), max(1, round(crop.height * s))), Image.LANCZOS)

        canvas = Image.new("RGBA", (ref.width * args.scale, ref.height * args.scale), (0, 0, 0, 0))
        # Pieds sur la même ligne, centre horizontal sur celui du sprite DS
        cx = (rb[0] + rb[2]) / 2 * args.scale
        x = round(cx - crop.width / 2)
        y = rb[3] * args.scale - crop.height
        canvas.alpha_composite(crop, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))
        if x < 0 or y < 0 or x + crop.width > canvas.width:
            notes.append("dépasse de la toile de sortie, rogné")
        canvas.save(dst / f.name, optimize=True)

        print("%-12s %8.3f  %s" % (f.name, s, "; ".join(notes)))

    if scales:
        med = sorted(scales.values())[len(scales) // 2]
        print("\nÉchelle appliquée relative à la médiane (1.00 = déjà cohérente avec les autres) :")
        for name, s in scales.items():
            flag = "  <-- très différente" if abs(s / med - 1) > 0.2 else ""
            print("  %-12s x%.2f%s" % (name, s / med, flag))
    print("\n%d frames écrites dans %s (%dx%d)" % (len(scales), dst, ref.width * args.scale, ref.height * args.scale))


if __name__ == "__main__":
    main()
