# -*- coding: utf-8 -*-
"""Extrai e decodifica os icones de item/Pal do Palworld (texturas DXT5/BC3)
direto do IoStore, gerando miniaturas PNG. Sem FModel.

Estrutura do icone: textura 2D, quase sempre PF_DXT5 (BC3), com o mip principal
inline no proprio .uasset. Achamos o formato pelo name map, as dimensoes pelo
cabecalho do export, e o offset do mip por busca curta (o alinhamento certo
deixa o canal alfa "limpo").
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iostore, texture2ddecoder
from PIL import Image

POT = {16, 32, 64, 128, 256, 512, 1024, 2048}
BPP = {"bc1": 0.5, "bc3": 1.0, "bc7": 1.0, "bc4": 0.5, "bc5": 1.0, "bgra": 4.0}


def _name_map(b):
    Num = struct.unpack_from("<I", b, 44)[0]
    p = 44 + 8 + 8 + Num * 8
    hdr = p; q = p + Num * 2
    nomes = []
    for i in range(Num):
        b0 = b[hdr + i * 2]; b1 = b[hdr + i * 2 + 1]
        ln = ((b0 & 0x7f) << 8) | b1
        if b0 & 0x80:
            nomes.append(b[q:q + ln * 2].decode("utf-16-be", "replace")); q += ln * 2
        else:
            nomes.append(b[q:q + ln].decode("utf-8", "replace")); q += ln
    return nomes


def _formato(nomes):
    for n in nomes:
        if n in ("PF_DXT5", "PF_BC3"):
            return "bc3"
        if n in ("PF_DXT1", "PF_BC1"):
            return "bc1"
        if n == "PF_BC7":
            return "bc7"
        if n in ("PF_B8G8R8A8", "PF_R8G8B8A8"):
            return "bgra"
        if n == "PF_BC4":
            return "bc4"
        if n == "PF_BC5":
            return "bc5"
    return "bc3"


def _dims(b, hsize):
    exp = b[hsize:hsize + 120]
    for i in range(0, len(exp) - 8, 4):
        w = struct.unpack_from("<i", exp, i)[0]
        h = struct.unpack_from("<i", exp, i + 4)[0]
        if w in POT and h in POT:
            return w, h
    return 256, 256


def _decode(data, fmt, w, h):
    if fmt == "bc3":
        raw = texture2ddecoder.decode_bc3(data, w, h)
    elif fmt == "bc1":
        raw = texture2ddecoder.decode_bc1(data, w, h)
    elif fmt == "bc7":
        raw = texture2ddecoder.decode_bc7(data, w, h)
    elif fmt == "bc5":
        raw = texture2ddecoder.decode_bc5(data, w, h)
    elif fmt == "bc4":
        raw = texture2ddecoder.decode_bc4(data, w, h)
    elif fmt == "bgra":
        return Image.frombytes("RGBA", (w, h), data, "raw", "BGRA")
    else:
        return None
    return Image.frombytes("RGBA", (w, h), raw, "raw", "BGRA")


def _disc(img):
    """Descontinuidade nas bordas de bloco BC (4px) menos a de dentro.
    Alinhamento correto -> proximo de zero; offset errado -> alto."""
    g = list(img.convert("L").get_flattened_data())
    W = img.size[0]
    bord = dentro = nb = nd = 0
    for y in range(0, img.size[1], 6):
        base = y * W
        for x in range(1, W - 1):
            d = abs(g[base + x] - g[base + x + 1])
            if (x + 1) % 4 == 0:
                bord += d; nb += 1
            else:
                dentro += d; nd += 1
    return bord / max(1, nb) - dentro / max(1, nd)


def extrair_icone(t, chunk_idx, tam=40):
    """Devolve uma miniatura PIL (RGBA) do icone, ou None.

    O mip principal fica inline, logo apos o cabecalho da textura. Para os icones
    (256x256 DXT5) esse cabecalho tem 125 bytes; usamos isso como palpite e, se o
    resultado nao ficar alinhado, refinamos numa janela curta.
    """
    b = iostore.extrair(t, chunk_idx)
    hsize = struct.unpack_from("<I", b, 4)[0]
    fmt = _formato(_name_map(b))
    w, h = _dims(b, hsize)
    mip = int(w * h * BPP.get(fmt, 1.0))
    if mip <= 0 or hsize + mip > len(b):
        return None

    def dec(off):
        if off < hsize or off + mip > len(b):
            return None
        try:
            return _decode(b[off:off + mip], fmt, w, h)
        except Exception:
            return None

    img = dec(hsize + 125)
    if img is None or _disc(img) > 8:
        melhor = (1e9, img)
        for off in range(hsize + 90, min(hsize + 170, len(b) - mip)):
            cand = dec(off)
            if cand is None:
                continue
            g = list(cand.convert("L").get_flattened_data())
            m = sum(g[::13]) / len(g[::13])
            if sum((x - m) ** 2 for x in g[::13]) / len(g[::13]) < 60:
                continue
            d = _disc(cand)
            if d < melhor[0]:
                melhor = (d, cand)
            if d < 2:
                break
        img = melhor[1]
    if img is None:
        return None
    return img.resize((tam, tam), Image.LANCZOS)


# ------- mapeamento ItemID -> icone e geracao do cache -------
def _mapa_icones(idx):
    smap = {}
    for k in idx:
        n = k.split("/")[-1]
        if not n.endswith(".uasset"):
            continue
        for pref in ("T_itemicon_", "T_icon_item_"):
            if n.startswith(pref):
                stem = n[len(pref):-7]
                smap.setdefault(stem, k)
                if "_" in stem:
                    smap.setdefault(stem.split("_", 1)[1], k)
                if stem.count("_") >= 2:
                    smap.setdefault(stem.split("_", 2)[2], k)
    return smap


def resolver(smap, item_id):
    if item_id in smap:
        return smap[item_id]
    if item_id.startswith("Blueprint_"):        # esquema usa o icone do item que constroi
        base = item_id[len("Blueprint_"):]
        if base in smap:
            return smap[base]
    return None


def gerar_cache(ids, tam=40, callback=None):
    """Gera dados/icones/<ItemID>.png para os IDs dados. Retorna (ok, faltou)."""
    t = iostore.carregar()
    idx = iostore._dir_index(t)
    smap = _mapa_icones(idx)
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados", "icones")
    os.makedirs(outdir, exist_ok=True)
    ok = falta = 0
    for i, sid in enumerate(ids):
        alvo = os.path.join(outdir, sid + ".png")
        if os.path.exists(alvo):
            ok += 1; continue
        chave = resolver(smap, sid)
        if chave is None:
            falta += 1; continue
        try:
            img = extrair_icone(t, idx[chave], tam)
        except Exception:
            img = None
        if img is not None:
            img.save(alvo); ok += 1
        else:
            falta += 1
        if callback:
            callback(i + 1, len(ids))
    return ok, falta


if __name__ == "__main__":
    t = iostore.carregar()
    idx = iostore._dir_index(t)
    testes = ["T_itemicon_Ammo_MagnumBullet", "T_itemicon_Material_Wood",
              "T_itemicon_Material_Stone", "T_itemicon_Weapon_Katana"]
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados", "teste_icones")
    os.makedirs(outdir, exist_ok=True)
    for nome in testes:
        chave = next((k for k in idx if k.endswith(nome + ".uasset")), None)
        if not chave:
            print("nao achei", nome); continue
        img = extrair_icone(t, idx[chave], 96)
        if img:
            img.save(os.path.join(outdir, nome + ".png"))
            print("OK", nome)
        else:
            print("FALHOU", nome)
