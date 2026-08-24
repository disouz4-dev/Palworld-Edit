# -*- coding: utf-8 -*-
"""Compressao dos saves do Palworld.

Formatos:
  PlZ1 / PlZ2  -> zlib (1 = uma passada, 2 = duas). Suportado para ler e escrever.
  PlM1         -> Oodle Kraken (linkado estaticamente no exe do jogo). Nao suportado.
  CNK0         -> envelope extra da versao Xbox/GDK, com 12 bytes na frente.

Observacao sobre o CNK0: o jogo reserva um buffer do tamanho 'cmp' e grava o
stream comprimido nele, mas escreve o buffer inteiro no disco. Sobra lixo no
final do arquivo. Reproduzimos isso com zeros — o jogo ignora.
"""
import struct, zlib

class OodleNotSupported(Exception):
    pass

def decompress(raw):
    meta = {}
    off = 0
    if raw[8:12] == b"CNK0":
        meta["cnk"] = True
        meta["f0"], meta["f1"] = struct.unpack_from("<ii", raw, 0)
        off = 12
    else:
        meta["cnk"] = False
    unc, cmp_ = struct.unpack_from("<ii", raw, off)
    magic = raw[off + 8:off + 11]
    typ = raw[off + 11]
    if magic == b"PlM":
        raise OodleNotSupported("save comprimido com Oodle (PlM%c)" % typ)
    if magic != b"PlZ":
        raise ValueError("assinatura desconhecida: %r" % (raw[off + 8:off + 12],))
    meta["type"] = typ
    meta["cmp_field"] = cmp_
    d = zlib.decompressobj()
    data = d.decompress(raw[off + 12:])
    if typ == 0x32:
        data = zlib.decompress(data)
    if len(data) != unc:
        raise ValueError("tamanho descomprimido nao bate: %d != %d" % (len(data), unc))
    return data, meta

def compress(data, meta, level=6):
    typ = meta["type"]
    if typ == 0x32:
        inner = zlib.compress(data, level)
        body = zlib.compress(inner, level)
        cmp_field = len(inner)
    else:
        body = zlib.compress(data, level)
        cmp_field = len(body)
    out = b""
    if meta.get("cnk"):
        out += struct.pack("<ii", meta["f0"], meta["f1"]) + b"CNK0"
    out += struct.pack("<ii", len(data), cmp_field) + b"PlZ" + bytes([typ]) + body
    if meta.get("cnk") and len(body) < cmp_field:
        out += b"\x00" * (cmp_field - len(body))   # padding igual ao do jogo
    return out
