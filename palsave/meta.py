# -*- coding: utf-8 -*-
"""Le o nome do mundo e do jogador a partir do LevelMeta.sav.

O LevelMeta guarda um GVAS com /Script/Pal.PalWorldBaseInfoSaveGame, contendo
WorldName, HostPlayerName, HostPlayerLevel e InGameDay.

Dois caminhos, porque existem dois formatos de save:

  PlZ (zlib)  -> descomprime e le a estrutura exata do GVAS.
  PlM (Oodle) -> nao temos como descomprimir, mas o arquivo comprime muito mal
                 e quase todo byte vira literal no stream, entao as strings
                 aparecem legiveis. Ai vale a busca por marcador.

Isso e so para exibir rotulos; nada aqui e usado para gravar.
"""
import re, struct
from . import palz

TIPO = b"StrProperty\x00"
RUN8 = re.compile(rb"[\x20-\x7e]{2,120}\x00")
RUN16 = re.compile(rb"(?:[\x20-\x7e]\x00){2,120}\x00\x00")


def _fstring(buf, pos):
    """Le uma FString do GVAS. Tamanho negativo = UTF-16."""
    (n,) = struct.unpack_from("<i", buf, pos)
    pos += 4
    if n == 0:
        return "", pos
    if n < 0:
        n = -n
        return buf[pos:pos + n * 2 - 2].decode("utf-16-le", "replace"), pos + n * 2
    return buf[pos:pos + n - 1].decode("utf-8", "replace"), pos + n


def _exato(buf, marcador):
    """GVAS de verdade: nome, tipo, int64 tamanho, byte de guid, valor."""
    i = buf.find(marcador)
    if i < 0:
        return None
    j = buf.find(TIPO, i, i + 96)
    if j < 0:
        return None
    try:
        s, _ = _fstring(buf, j + len(TIPO) + 8 + 1)
    except Exception:
        return None
    return s.strip() or None


def _heuristico(buf, marcador):
    """Stream Oodle: pega a primeira string legivel depois do marcador."""
    i = buf.find(marcador)
    if i < 0:
        return None
    j = buf.find(TIPO, i, i + 96)
    if j < 0:
        return None
    trecho = buf[j + len(TIPO):j + len(TIPO) + 96]
    m8, m16 = RUN8.search(trecho), RUN16.search(trecho)
    if m16 and (not m8 or m16.start() <= m8.start()):
        s = m16.group()[:-2].decode("utf-16-le", "replace")
    elif m8:
        s = m8.group()[:-1].decode("utf-8", "replace")
    else:
        return None
    return s.strip() or None


def ler_meta(raw):
    """raw = bytes crus do blob do LevelMeta -> {'mundo':..., 'jogador':...}."""
    try:
        buf, _ = palz.decompress(raw)
        leitor = _exato
    except Exception:
        buf, leitor = raw, _heuristico
    return {"mundo": leitor(buf, b"WorldName\x00"),
            "jogador": leitor(buf, b"HostPlayerName\x00")}
