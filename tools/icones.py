# -*- coding: utf-8 -*-
"""Extrai e decodifica os icones de item/Pal do Palworld (texturas DXT5/BC3)
direto do IoStore, gerando miniaturas PNG. Sem FModel.

Estrutura do icone: textura 2D, quase sempre PF_DXT5 (BC3), com o mip principal
inline no proprio .uasset. Achamos o formato pelo name map, as dimensoes pelo
cabecalho do export, e o offset do mip por busca curta (o alinhamento certo
deixa o canal alfa "limpo").
"""
import os, sys, struct, re
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
        # icones dos tipos de trabalho (usados pelos tickets de aptidao)
        if n.startswith("T_icon_skill_pal_WorkRank_"):
            stem = n[len("T_icon_skill_pal_WorkRank_"):-7]
            smap.setdefault("WorkRank_" + stem, k)
    return smap


_CI_CACHE = {}


def _cand_variantes(item_id):
    """Nomes candidatos para casar com uma textura, do mais especifico ao generico."""
    cands = []
    def add(x):
        if x and x not in cands:
            cands.append(x)

    _SUF = ("_Tier_00", "_Tier_01", "_Default", "_01", "_1")
    add(item_id)
    for suf in _SUF:                             # arma pura: Spear -> Spear_Tier_00
        add(item_id + suf)
    # tira sufixos comuns (NPC, tier, _fix, _G1, numero final, etc.), acumulando
    sufixos = [r"_NPC$", r"_Steal$", r"_High$", r"_fix$", r"_Default\d*$",
               r"_Triple$", r"_Tier_\d+$", r"_G\d+$", r"_\d+$"]
    cur = item_id
    for _ in range(6):
        mudou = False
        for pat in sufixos:
            y = re.sub(pat, "", cur)
            if y != cur:
                add(y); cur = y; mudou = True
        if not mudou:
            break

    # troca o numero final por _01/_00, com ou sem underscore
    # (GrapplingGun2 -> GrapplingGun; TreasureMap02 -> TreasureMap01)
    for base in list(cands):
        m = re.search(r"^(.*?)_?(\d+)$", base)
        if m and m.group(1):
            add(m.group(1))
            for nn in ("01", "1", "00", "0"):
                add(m.group(1) + "_" + nn)
                add(m.group(1) + nn)

    # reducao por prefixo: vai tirando o ultimo segmento e testando bases de arma
    partes = item_id.split("_")
    for k in range(len(partes) - 1, 0, -1):
        p = "_".join(partes[:k])
        add(p)
        for suf in _SUF:
            add(p + suf)
    return cands


def resolver(smap, item_id):
    ci = _CI_CACHE.get(id(smap))
    if ci is None:
        ci = {k.lower(): v for k, v in smap.items()}
        _CI_CACHE[id(smap)] = ci

    def achar(x):
        return smap.get(x) or ci.get(x.lower())

    for c in _cand_variantes(item_id):
        r = achar(c)
        if r:
            return r
    if item_id.startswith("WorkSuitability_AddTicket_"):   # ticket -> icone do tipo de trabalho
        r = achar("WorkRank_" + item_id[len("WorkSuitability_AddTicket_"):])
        if r:
            return r
    if item_id.startswith("Blueprint_"):        # esquema de construcao: icone generico
        for g in ("Blueprint_Building", "Blueprint"):
            r = achar(g)
            if r:
                return r
    if item_id.startswith("SkillCard_"):        # card sem match exato: card generico
        return (achar("SkillCard_Fire") or achar("SkillCard_Grass")
                or next((v for k, v in smap.items() if k.startswith("SkillCard_")), None))
    # ultimo recurso: casa por "termina em" nos dois sentidos
    il = item_id.lower()
    for k, v in smap.items():                    # item termina no nome da textura (CaveMushroom->Mushroom)
        kl = k.lower()
        if len(kl) >= 5 and il.endswith(kl):
            return v
    for c in _cand_variantes(item_id):           # textura termina num candidato bom
        if len(c) < 5:
            continue
        cl = c.lower()
        for k, v in smap.items():
            if k.lower().endswith(cl):
                return v
    tok = item_id.split("_")[-1]
    if len(tok) >= 5:
        for k, v in smap.items():
            if tok.lower() in k.lower():
                return v
    return None


def gerar_cache(ids, tam=40, callback=None):
    """Gera dados/icones/<ItemID>.png para os IDs dados. Retorna (ok, faltou)."""
    t = iostore.carregar()
    idx = iostore._dir_index(t)
    smap = _mapa_icones(idx)
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados", "icones")
    os.makedirs(outdir, exist_ok=True)
    dir_pals = os.path.join(os.path.dirname(outdir), "icones_pals")
    ok = falta = 0
    for i, sid in enumerate(ids):
        alvo = os.path.join(outdir, sid + ".png")
        if os.path.exists(alvo):
            ok += 1; continue
        chave = resolver(smap, sid)
        if chave is None:
            # SkillUnlock_<Pal>: usa o icone do proprio Pal, que ja temos
            if sid.startswith("SkillUnlock_"):
                pi = os.path.join(dir_pals, sid[len("SkillUnlock_"):] + ".png")
                if os.path.exists(pi):
                    try:
                        import shutil; shutil.copy2(pi, alvo); ok += 1
                    except Exception:
                        falta += 1
                    if callback:
                        callback(i + 1, len(ids))
                    continue
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


# ------- icones de Pal (ficam num .ubulk separado, 128x128) -------
def _mapa_pals(idx):
    m = {}
    for k in idx:
        n = k.split("/")[-1]
        if n.startswith("T_") and n.endswith("_icon_normal.uasset"):
            m.setdefault(n[2:-len("_icon_normal.uasset")], k)
    return m


def resolver_pal(pmap, especie):
    if especie in pmap:
        return pmap[especie]
    e2 = especie.replace("BOSS_", "").replace("Boss_", "")
    return pmap.get(e2)


def extrair_pal(t, idx, uasset_key, tam=40):
    b = iostore.extrair(t, idx[uasset_key])
    hsize = struct.unpack_from("<I", b, 4)[0]
    fmt = _formato(_name_map(b))
    w, h = _dims(b, hsize)
    mip = int(w * h * BPP.get(fmt, 1.0))
    ub = uasset_key[:-7] + ".ubulk"
    if ub in idx:                       # pixels ficam no .ubulk
        data = iostore.extrair(t, idx[ub])[:mip]
    else:                               # ou inline, logo apos o cabecalho
        data = b[hsize + 125:hsize + 125 + mip]
    if len(data) < mip:
        return None
    try:
        img = _decode(data, fmt, w, h)
    except Exception:
        return None
    return img.resize((tam, tam), Image.LANCZOS) if img else None


def gerar_cache_pals(especies, tam=40, callback=None):
    t = iostore.carregar()
    idx = iostore._dir_index(t)
    pmap = _mapa_pals(idx)
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados", "icones_pals")
    os.makedirs(outdir, exist_ok=True)
    ok = falta = 0
    for i, esp in enumerate(especies):
        alvo = os.path.join(outdir, esp + ".png")
        if os.path.exists(alvo):
            ok += 1; continue
        key = resolver_pal(pmap, esp)
        if not key:
            falta += 1; continue
        try:
            img = extrair_pal(t, idx, key, tam)
        except Exception:
            img = None
        if img is not None:
            img.save(alvo); ok += 1
        else:
            falta += 1
        if callback:
            callback(i + 1, len(especies))
    return ok, falta
