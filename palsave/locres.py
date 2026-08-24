# -*- coding: utf-8 -*-
"""Leitor de arquivos .locres (a localizacao da Unreal Engine).

Os textos oficiais do Palworld em todos os idiomas estao em
Localization/Game/<idioma>/Game.locres, dentro do Pal-WinGDK.pak. Boa parte
desses arquivos esta gravada sem compressao no .pak, entao da pra achar cada um
pela assinatura e ler direto, sem precisar do Oodle.

Formato da versao 3 (Optimized_CityHash64_UTF16):

    16 bytes  assinatura
    uint8     versao
    int64     offset da tabela de textos
    uint32    quantidade de textos
    uint32    quantidade de namespaces
    para cada namespace:
        uint32 hash, FString nome, uint32 qtd de chaves
        para cada chave:
            uint32 hash, FString chave, uint32 hash do original, int32 indice
    na tabela de textos:
        uint32 quantidade
        para cada: FString texto, uint32 contador de referencias

FString: int32 tamanho; negativo = UTF-16 (tamanho em caracteres),
positivo = UTF-8 (tamanho em bytes). Sempre inclui o \\0 final.
"""
import struct, os, re

MAGIC = bytes([0x0E, 0x14, 0x74, 0x75, 0x67, 0x4A, 0x03, 0xFC,
               0x4A, 0x15, 0x90, 0x9D, 0xC3, 0x37, 0x7F, 0x1B])


class _Leitor(object):
    def __init__(self, buf, pos=0):
        self.b = buf
        self.p = pos

    def u32(self):
        v, = struct.unpack_from("<I", self.b, self.p); self.p += 4; return v

    def i32(self):
        v, = struct.unpack_from("<i", self.b, self.p); self.p += 4; return v

    def i64(self):
        v, = struct.unpack_from("<q", self.b, self.p); self.p += 8; return v

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ""
        if n < 0:
            n = -n
            s = self.b[self.p:self.p + n * 2 - 2].decode("utf-16-le", "replace")
            self.p += n * 2
        else:
            s = self.b[self.p:self.p + n - 1].decode("utf-8", "replace")
            self.p += n
        return s


def ler(buf, pos=0):
    """Le um .locres a partir de 'pos'. Devolve ({namespace: {chave: texto}}, versao)."""
    if buf[pos:pos + 16] != MAGIC:
        raise ValueError("nao e um .locres")
    r = _Leitor(buf, pos + 16)
    versao = buf[r.p]; r.p += 1
    if versao < 1 or versao > 3:
        raise ValueError("versao %d nao suportada" % versao)
    off_textos = r.i64()
    if versao >= 3:
        r.u32()                          # quantidade de textos (redundante)

    # tabela de textos
    t = _Leitor(buf, pos + off_textos)
    textos = []
    for _ in range(t.u32()):
        textos.append(t.fstring())
        if versao >= 2:
            t.u32()                      # contador de referencias

    # namespaces e chaves
    out = {}
    for _ in range(r.u32()):
        if versao >= 2:
            r.u32()                      # hash do namespace
        ns = r.fstring()
        d = out.setdefault(ns, {})
        for _k in range(r.u32()):
            if versao >= 2:
                r.u32()                  # hash da chave
            chave = r.fstring()
            r.u32()                      # hash do texto original
            idx = r.i32()
            if 0 <= idx < len(textos):
                d[chave] = textos[idx]
    return out, versao


def achar_blocos(caminho):
    """Offsets de todos os .locres gravados sem compressao dentro do .pak."""
    offs = []
    with open(caminho, "rb") as f:
        base, resto = 0, b""
        while True:
            buf = f.read(8 << 20)
            if not buf:
                break
            dados = resto + buf
            desloc = base - len(resto)
            i = 0
            while True:
                j = dados.find(MAGIC, i)
                if j < 0:
                    break
                offs.append(desloc + j)
                i = j + 1
            resto = dados[-16:]
            base += len(buf)
    return offs
