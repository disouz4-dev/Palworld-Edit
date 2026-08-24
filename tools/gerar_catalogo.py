# -*- coding: utf-8 -*-
"""Gera items.json: o catalogo de IDs de item usado pelo editor.

Duas fontes:
  1. Os saves legiveis (Level.sav) -> IDs 100%% confiaveis.
  2. Os nomes dos icones dentro do .utoc do jogo. Eles vem no formato
     "T_itemicon_<Categoria>_<IdReal>", entao tiramos o prefixo de categoria.
     Isso foi validado: nenhum nome cru de icone bate com um ID real, mas
     centenas batem depois de tirar o prefixo.
"""
import os, re, sys, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palsave import wgs, palz
from palsave.level import LevelSave
import paths

# caminho do jogo resolvido por env var / extracao_local.json (nunca fixo no codigo)
UTOC = paths.iostore_base() + ".utoc"
# save descoberto automaticamente (com fallback para o local padrao)
WGS_DIR = wgs.descobrir_save() or os.path.expandvars(
    r"%LOCALAPPDATA%\Packages\PocketpairInc.Palworld_ad4psfrxyesvt\SystemAppData\wgs")

# categorias que sao so rotulo do icone e devem ser removidas
TIRAR = ["BossDefeatReward", "Material", "Consume", "Essential", "Weapon",
         "Armor", "Food", "food", "Ammo", "Sphere", "Glider", "Head", "Body"]
# prefixos que fazem parte do ID de verdade
MANTER = ["Accessory", "Relic", "Blueprint", "SkillCard", "PalItem", "PalSphere"]


def do_save():
    ids = set()
    try:
        root = wgs.find_wgs_root(WGS_DIR)
    except Exception:
        return ids
    index = wgs.parse_index(root)
    for wid, partes in wgs.worlds(index).items():
        lvl = partes.get("Level-01") or partes.get("Level")
        if not lvl:
            continue
        try:
            _, raw = wgs.read_blob(root, lvl)
            data, _ = palz.decompress(raw)
            lv = LevelSave.from_bytes(data)
        except Exception:
            continue
        n = len(ids)
        ids |= lv.all_item_ids()
        # itens dinamicos tambem carregam IDs validos
        import struct
        for d in lv.dyn_values:
            rb = bytes(d["RawData"]["value"]["values"])
            ln = struct.unpack_from("<i", rb, 32)[0]
            ids.add(rb[36:36 + ln].split(b"\x00")[0].decode("utf-8", "replace"))
        print("   mundo %s: +%d IDs" % (wid[:8], len(ids) - n))
    return {i for i in ids if i}


def dos_icones():
    blob = open(UTOC, "rb").read()
    crus = set(m.decode() for m in re.findall(rb"T_itemicon_([A-Za-z0-9_]+)", blob))
    crus |= set(m.decode() for m in re.findall(rb"T_icon_item_([A-Za-z0-9_]+)", blob))
    out = set()
    for nome in crus:
        p = nome.split("_")[0]
        if p in MANTER:
            out.add(nome)
        elif p in TIRAR and "_" in nome:
            out.add(nome.split("_", 1)[1])
        else:
            out.add(nome)
    return {i for i in out if i}


if __name__ == "__main__":
    print("lendo os saves...")
    ver = do_save()
    print("   %d IDs confirmados" % len(ver))
    print("lendo os icones do jogo...")
    der = dos_icones() - ver
    print("   %d IDs derivados (fora os ja confirmados)" % len(der))
    json.dump({"verificados": sorted(ver), "derivados": sorted(der)},
              open(os.path.join(BASE, "items.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    print("items.json gravado: %d itens no total" % (len(ver) + len(der)))
