# -*- coding: utf-8 -*-
"""Leitura e edicao dos containers de item do Level.sav.

Layout de um slot (ItemContainerSaveData.Slots[].RawData), decodificado
por engenharia reversa do save v1.0.3:

    int32   indice do slot
    int32   quantidade
    int32   tamanho do nome (em bytes, incluindo o \0 final)
    bytes   StaticId em UTF-8 + \0
    52 bytes de cauda:
        [0:16]  zeros
        [16:32] GUID do item dinamico (durabilidade/municao) ou zeros
        [32:52] zeros

Layout de DynamicItemSaveData[].RawData:

    16 bytes zeros | 16 bytes GUID | int32 tam | StaticId+\0
    int32 0 | float durabilidade | int32 tem_arma
      se tem_arma: int32 municao | int32 0 | int32 5 "None\0" | int32 0
"""
import struct, copy, uuid, os
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS

SLOT_TAIL = 52
GUID_AT = 16          # posicao do GUID dentro da cauda do slot
ZERO_GUID = b"\x00" * 16


def _mk_slot_raw(index, count, static_id, guid=ZERO_GUID):
    nb = static_id.encode("utf-8") + b"\x00"
    tail = bytearray(SLOT_TAIL)
    tail[GUID_AT:GUID_AT + 16] = guid
    return struct.pack("<iii", index, count, len(nb)) + nb + bytes(tail)


def _parse_slot_raw(raw):
    idx, cnt, n = struct.unpack_from("<iii", raw, 0)
    sid = raw[12:12 + n].split(b"\x00")[0].decode("utf-8", "replace")
    tail = raw[12 + n:]
    guid = tail[GUID_AT:GUID_AT + 16] if len(tail) >= GUID_AT + 16 else ZERO_GUID
    return idx, cnt, sid, guid


def _bytes_of(prop):
    return bytes(prop["value"]["values"])


def _set_bytes(prop, data):
    prop["value"]["values"] = list(data)


class Slot(object):
    def __init__(self, node):
        self.node = node
        self.index, self.count, self.static_id, self.guid = _parse_slot_raw(_bytes_of(node["RawData"]))

    def write_back(self):
        _set_bytes(self.node["RawData"], _mk_slot_raw(self.index, self.count, self.static_id, self.guid))


class Container(object):
    def __init__(self, node):
        self.node = node
        self.guid = str(node["key"]["ID"]["value"])
        self.group_id = str(node["value"]["BelongInfo"]["value"]["GroupId"]["value"])
        self._values = node["value"]["Slots"]["value"]["values"]
        self.slots = [Slot(s) for s in self._values]

    @property
    def items(self):
        return {s.static_id: s.count for s in self.slots if s.static_id}

    def used_indices(self):
        return set(s.index for s in self.slots)

    def add_slot(self, static_id, count, guid=ZERO_GUID, capacity=42):
        used = self.used_indices()
        free = next((i for i in range(max(capacity, len(self.slots) + 1)) if i not in used), None)
        if free is None:
            raise RuntimeError("container cheio")
        node = copy.deepcopy(self._values[0]) if self._values else None
        if node is None:
            raise RuntimeError("container sem slot modelo (nao da pra criar do zero)")
        _set_bytes(node["RawData"], _mk_slot_raw(free, count, static_id, guid))
        self._values.append(node)
        s = Slot(node)
        self.slots.append(s)
        return s

    def remove_slot(self, slot):
        self._values.remove(slot.node)
        self.slots.remove(slot)


class LevelSave(object):
    def __init__(self, gvas):
        self.gvas = gvas
        self.ws = gvas.properties["worldSaveData"]["value"]
        self.containers = [Container(c) for c in self.ws["ItemContainerSaveData"]["value"]]
        self._dyn = self.ws.get("DynamicItemSaveData")
        self.dyn_values = self._dyn["value"]["values"] if self._dyn else []

    # ---------- itens dinamicos (durabilidade / municao) ----------
    def _dyn_index(self):
        out = {}
        for d in self.dyn_values:
            raw = _bytes_of(d["RawData"])
            n = struct.unpack_from("<i", raw, 32)[0]
            sid = raw[36:36 + n].split(b"\x00")[0].decode("utf-8", "replace")
            out.setdefault(sid, []).append((raw[16:32], raw[36 + n:]))
        return out

    def make_dynamic(self, static_id):
        """Cria uma entrada dinamica copiando o padrao de um item igual ja existente."""
        if not self.dyn_values:
            return ZERO_GUID
        idx = self._dyn_index()
        modelo = idx.get(static_id)
        if modelo:
            tail = modelo[0][1]
        else:
            return ZERO_GUID          # sem modelo: trata como item empilhavel comum
        g = uuid.uuid4().bytes
        nb = static_id.encode("utf-8") + b"\x00"
        raw = ZERO_GUID + g + struct.pack("<i", len(nb)) + nb + tail
        node = copy.deepcopy(self.dyn_values[0])
        _set_bytes(node["RawData"], raw)
        self.dyn_values.append(node)
        return g

    def uses_dynamic(self, static_id):
        return static_id in self._dyn_index()

    # ---------- edicao ----------
    def set_quantity(self, container, static_id, qty, capacity=42):
        """Define a quantidade de um item. 0 remove. Cria o slot se nao existir."""
        alvos = [s for s in container.slots if s.static_id == static_id]
        if qty <= 0:
            for s in alvos:
                container.remove_slot(s)
            return "removido"
        if alvos:
            alvos[0].count = int(qty)
            alvos[0].write_back()
            for s in alvos[1:]:
                container.remove_slot(s)
            return "alterado"
        guid = self.make_dynamic(static_id) if self.uses_dynamic(static_id) else ZERO_GUID
        container.add_slot(static_id, int(qty), guid, capacity)
        return "adicionado"

    def all_item_ids(self):
        out = set()
        for c in self.containers:
            for s in c.slots:
                if s.static_id:
                    out.add(s.static_id)
        return out

    # ---------- io ----------
    @staticmethod
    def from_bytes(data):
        return LevelSave(GvasFile.read(data, PALWORLD_TYPE_HINTS, {}, allow_nan=True))

    def to_bytes(self):
        return self.gvas.write({})
