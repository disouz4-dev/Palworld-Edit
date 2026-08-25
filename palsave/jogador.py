# -*- coding: utf-8 -*-
"""Save do JOGADOR (Players/*.sav): pontos de tecnologia e tecnologia antiga.

O arquivo e comprimido com Oodle (PlM1). Lemos com um Oodle opcional (ver
palsave/oodle.py) e, ao gravar, reescrevemos como zlib (PlZ), que o jogo tambem
le -- assim nao precisamos do compressor Oodle, so do descompressor.
"""
import struct
from palsave import wgs, palz, oodle
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS


def entrada_jogador(index, wid):
    """A entrada 'Players-...' do mundo 'wid' (a 1a que aparecer)."""
    for e in index["entries"]:
        nome = e["name"]
        if nome.startswith(wid) and "-Players-" in ("-" + nome[len(wid):]):
            return e
    # fallback: qualquer '...-Players-...'
    for e in index["entries"]:
        if e["name"].startswith(wid) and "Players" in e["name"]:
            return e
    return None


def ler(root, entry, oodle_path=None):
    """Retorna (gvas, meta) do save do jogador. meta guarda como recomprimir."""
    _, raw = wgs.read_blob(root, entry)
    try:
        data, meta = palz.decompress(raw)            # ja e zlib? (ex.: gravado por nos)
        meta["origem"] = "zlib"
        g = GvasFile.read(data, PALWORLD_TYPE_HINTS, {})
        return g, meta
    except palz.OodleNotSupported:
        pass
    # Oodle
    off = 12 if raw[8:12] == b"CNK0" else 0
    meta = {"cnk": off == 12, "type": 0x31, "origem": "oodle"}
    if off == 12:
        meta["f0"], meta["f1"] = struct.unpack_from("<ii", raw, 0)
    unc, cmp_ = struct.unpack_from("<ii", raw, off)
    comp = raw[off + 12:off + 12 + cmp_]
    data = oodle.decompress(comp, unc, oodle_path)
    g = GvasFile.read(data, PALWORLD_TYPE_HINTS, {})
    return g, meta


def _sd(g):
    p = g.properties
    sd = p.get("SaveData") or p.get("PlayerSaveData")
    return sd["value"] if sd else p


def pontos(g):
    sd = _sd(g)
    def val(k):
        v = sd.get(k)
        return (v.get("value", 0) if isinstance(v, dict) else 0) if v else 0
    return val("TechnologyPoint"), val("bossTechnologyPoint")


def set_pontos(g, tech=None, antiga=None):
    sd = _sd(g)
    if tech is not None and "TechnologyPoint" in sd:
        sd["TechnologyPoint"]["value"] = max(0, int(tech))
    if antiga is not None and "bossTechnologyPoint" in sd:
        sd["bossTechnologyPoint"]["value"] = max(0, int(antiga))


def gravar(root, index, entry, g, meta):
    """Grava o save do jogador de volta, SEMPRE como zlib (PlZ1)."""
    data = g.write({})
    mz = {"type": 0x31, "cnk": meta.get("cnk", False)}
    if mz["cnk"]:
        mz["f0"], mz["f1"] = meta.get("f0", 0), meta.get("f1", 0)
    blob = palz.compress(data, mz)
    wgs.write_blob(root, index, entry, blob)
