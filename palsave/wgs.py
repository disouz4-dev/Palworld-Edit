# -*- coding: utf-8 -*-
"""Camada WGS: os saves do Palworld versao Xbox/GDK ficam em 'containers'.

Estrutura:
  wgs/<conta>/containers.index      indice: nome do save -> GUID da pasta + tamanho
  wgs/<conta>/<GUID>/container.N    aponta para o arquivo de dados
  wgs/<conta>/<GUID>/<GUID2>        o arquivo de dados em si (o save comprimido)
"""
import os, struct, io

def find_wgs_root(wgs_dir):
    """Retorna a pasta da conta (a que contem containers.index)."""
    for d in sorted(os.listdir(wgs_dir)):
        p = os.path.join(wgs_dir, d)
        if os.path.isfile(os.path.join(p, "containers.index")):
            return p
    raise FileNotFoundError("containers.index nao encontrado em %s" % wgs_dir)

def _guid_str(b):
    return "%08X%04X%04X%s" % (struct.unpack("<I", b[0:4])[0],
                               struct.unpack("<H", b[4:6])[0],
                               struct.unpack("<H", b[6:8])[0], b[8:].hex().upper())

def parse_index(root):
    """Le containers.index. Guarda o offset do campo 'tamanho' pra poder corrigir depois."""
    path = os.path.join(root, "containers.index")
    data = open(path, "rb").read()
    f = io.BytesIO(data)
    rd = lambda fmt: struct.unpack(fmt, f.read(struct.calcsize(fmt)))
    def rstr():
        (n,) = rd("<i")
        return f.read(n * 2).decode("utf-16-le") if n > 0 else ""

    ver, = rd("<i"); cnt, = rd("<i"); rd("<i")
    pkg = rstr(); rd("<q"); rd("<i"); rstr(); rd("<q")

    entries = []
    for _ in range(cnt):
        name = rstr(); rstr(); rstr()
        seq, = rd("<B")
        state, = rd("<i")
        cguid = f.read(16)
        ft, = rd("<q")
        rd("<q")
        size_off = f.tell()          # offset do int64 de tamanho — usado pra corrigir
        size, = rd("<q")
        entries.append(dict(name=name, seq=seq, state=state, folder=_guid_str(cguid),
                            filetime=ft, size=size, size_off=size_off))
    if f.tell() != len(data):
        raise ValueError("containers.index nao foi lido ate o fim (%d de %d)" % (f.tell(), len(data)))
    return dict(version=ver, pkg=pkg, entries=entries, raw=data, path=path)

def set_entry_size(index, entry, new_size):
    """Corrige o tamanho de uma entrada dentro dos bytes do indice (em memoria)."""
    b = bytearray(index["raw"])
    struct.pack_into("<q", b, entry["size_off"], new_size)
    index["raw"] = bytes(b)
    entry["size"] = new_size

def save_index(index):
    _atomic_write(index["path"], index["raw"])

def blob_files(root, entry):
    """[(nome_logico, caminho_do_arquivo_de_dados)] de uma entrada."""
    d = os.path.join(root, entry["folder"])
    cf = os.path.join(d, "container.%d" % entry["seq"])
    if not os.path.isfile(cf):
        cands = sorted(x for x in os.listdir(d) if x.startswith("container."))
        if not cands:
            return []
        cf = os.path.join(d, cands[0])
    raw = open(cf, "rb").read()
    _, n = struct.unpack_from("<ii", raw, 0)
    out, off = [], 8
    for _ in range(n):
        nm = raw[off:off + 128].decode("utf-16-le").rstrip("\x00"); off += 128
        for _i in range(2):
            g = raw[off:off + 16]; off += 16
            fp = os.path.join(d, _guid_str(g))
            if os.path.isfile(fp) and not any(fp == o[1] for o in out):
                out.append((nm, fp))
    return out

def read_blob(root, entry):
    fs = blob_files(root, entry)
    if not fs:
        raise FileNotFoundError("sem arquivo de dados para " + entry["name"])
    return fs[0][1], open(fs[0][1], "rb").read()

def write_blob(root, index, entry, data):
    """Grava o save e corrige o tamanho no indice."""
    fs = blob_files(root, entry)
    if not fs:
        raise FileNotFoundError("sem arquivo de dados para " + entry["name"])
    _atomic_write(fs[0][1], data)
    set_entry_size(index, entry, len(data))
    save_index(index)

def _atomic_write(path, data):
    tmp = path + ".tmp_editor"
    with open(tmp, "wb") as fh:
        fh.write(data); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)

def worlds(index):
    """Agrupa entradas por mundo. Retorna {id_do_mundo: {sufixo: entrada}}."""
    out = {}
    for e in index["entries"]:
        if "-" not in e["name"]:
            continue
        wid, _, rest = e["name"].partition("-")
        if len(wid) != 32:
            continue
        out.setdefault(wid, {})[rest] = e
    return out
