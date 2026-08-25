# -*- coding: utf-8 -*-
"""Descobre a que objeto do mundo cada container de itens pertence.

Cada bau, forno, fazenda etc. e uma entrada de MapObjectSaveData. Dentro do
ConcreteModel.ModuleMap existe um modulo "ItemContainer" cujo RawData comeca
com os 16 bytes do GUID do container. E assim que ligamos um container ao
objeto que o contem.

O que sobra sem objeto e: o armazem da guilda (tem GroupId preenchido), os
containers do proprio personagem (inventario, equipamento, armas, comida) e um
container de 1 slot para o equipamento de cada Pal.

Os nomes em portugues aqui sao traducao nossa. Os nomes oficiais do jogo estao
nos arquivos .locres, que estao comprimidos com Oodle dentro do .pak e nao
conseguimos ler. Ver LEIA-ME.md.
"""
import uuid

SWAP = [3, 2, 1, 0, 7, 6, 5, 4, 11, 10, 9, 8, 15, 14, 13, 12]
ZERO = "00000000-0000-0000-0000-000000000000"

# nome do MapObjectId -> rotulo em portugues
NOMES = {
    "TreasureBox": "Bau do mundo",
    "TreasureBox_RequiredLongHold": "Bau do mundo (trancado)",
    "TreasureBox_FishingJunk_RequiredLongHold": "Tralha de pesca",
    "TreasureBox_FishingJunk_RequiredLongHold2": "Tralha de pesca",
    "TreasureBox_Electric": "Bau eletrico",
    "TreasureBox_Fire": "Bau de fogo",
    "TreasureBox_Water": "Bau de agua",
    "TreasureBox_Oilrig": "Bau da plataforma",
    "ItemChest": "Caixa de madeira",
    "ItemChest_02": "Caixa de metal",
    "ItemChest_03": "Caixa refinada",
    "SupplyDrop": "Suprimento aereo",
    "CommonDropItem3D": "Item no chao",
    "CoolerPalFoodBox": "Caixa de comida refrigerada",
    "PalFoodBox": "Caixa de comida dos Pals",
    "BreedFarm": "Fazenda de criacao",
    "BlastFurnace": "Fornalha",
    "BlastFurnace2": "Fornalha melhorada",
    "BlastFurnace3": "Fornalha eletrica",
    "BlastFurnace4": "Fornalha avancada",
    "ElectricKitchen": "Cozinha eletrica",
    "HugeKitchen": "Cozinha grande",
    "Kitchen": "Cozinha",
    "OilPump02": "Bomba de oleo",
    "OilPump": "Bomba de oleo",
    "Farm": "Plantacao",
    "ProductionLine": "Linha de producao",
    "Workbench": "Bancada",
    "MedicineFacility": "Bancada de remedios",
    "PalEgg_Water": "Ovo (agua)",
    "PalEgg_Earth": "Ovo (terra)",
    "PalEgg_Fire": "Ovo (fogo)",
    "PalEgg_Leaf": "Ovo (planta)",
    "PalEgg_Electricity": "Ovo (eletrico)",
    "PalEgg_Ice": "Ovo (gelo)",
    "PalEgg_Dark": "Ovo (sombrio)",
    "PalEgg_Dragon": "Ovo (dragao)",
    "PalEgg": "Ovo",
}


def _guid(b):
    return str(uuid.UUID(bytes=bytes(b[i] for i in SWAP)))


def _rotulo_objeto(mapobj_id):
    if mapobj_id in NOMES:
        return NOMES[mapobj_id]
    for chave, rot in NOMES.items():                 # tenta o prefixo
        if mapobj_id.startswith(chave):
            return "%s (%s)" % (rot, mapobj_id[len(chave):].lstrip("_") or "?")
    return mapobj_id


def _perfil(container):
    """Chuta que container do personagem e esse, pelo que tem dentro."""
    ids = list(container.items)
    txt = " ".join(ids)
    n = len(container.slots)
    if n == 1:
        return "Equipamento de Pal"
    if any(x in txt for x in ("Armor", "Shield", "Glider", "Accessory", "SphereModule")):
        return "Personagem: equipamento"
    if any(x in txt for x in ("Rifle", "Bow", "Launcher", "Gun", "Sword", "Spear",
                              "Axe", "Pickaxe", "MiningTool", "Detector", "Knife")):
        return "Personagem: armas"
    if any(x in txt for x in ("Sphere", "KeySphere", "Money", "SkillUnlock", "Pouch")):
        return "Personagem: essenciais"
    if n <= 3 and ids and all(any(f in i for f in ("Pizza", "Baked", "Salad", "Soup",
                                                  "Meat", "Bread", "Juice", "Cake"))
                              for i in ids):
        return "Personagem: comida rapida"
    return "Personagem: inventario"


def mapear(level):
    """LevelSave -> {guid do container: (rotulo, categoria)}.

    categoria: 'personagem', 'guilda', 'pal' ou 'mundo'.
    """
    conts = {c.guid: c for c in level.containers}
    out = {}

    mos = level.ws.get("MapObjectSaveData")
    if mos:
        for mo in mos["value"]["values"]:
            mm = mo["ConcreteModel"]["value"].get("ModuleMap")
            if not mm:
                continue
            for ent in mm["value"]:
                if "ItemContainer" not in str(ent["key"]):
                    continue
                b = bytes(ent["value"]["RawData"]["value"]["values"])
                if len(b) < 16:
                    continue
                g = _guid(b)
                if g in conts:
                    out[g] = (_rotulo_objeto(mo["MapObjectId"]["value"]), "mundo")

    for c in level.containers:
        if c.guid in out:
            continue
        if c.group_id != ZERO:
            out[c.guid] = ("Armazem da Guilda", "guilda")
        elif not c.slots:
            out[c.guid] = ("(container vazio)", "vazio")
        else:
            rot = _perfil(c)
            out[c.guid] = (rot, "pal" if rot == "Equipamento de Pal" else "personagem")

    # A MOCHILA VISIVEL (CommonContainer) e a que guarda o dinheiro (Money).
    # O maior container do jogador NAO e a mochila -- e o de itens-chave
    # (Essential, SlotNum ~230); por isso itens adicionados la ficavam invisiveis
    # no jogo (contavam peso, mas nao apareciam na aba do inventario comum).
    do_jogador = [c for c in level.containers if out[c.guid][1] == "personagem"]
    if do_jogador:
        def _slotnum(c):
            v = c.node["value"].get("SlotNum")
            if isinstance(v, dict):
                vv = v.get("value")
                return vv.get("value") if isinstance(vv, dict) else (vv or 0)
            return 0

        def _tem_money(c):
            return any(s.static_id == "Money" for s in c.slots)

        def _tem_chave(c):
            return any(s.static_id.startswith(("KeySphere", "SkillUnlock", "Blueprint",
                                               "TechnologyBook", "AncientTechnologyBook"))
                       for s in c.slots)

        principal = next((c for c in do_jogador if _tem_money(c)), None)
        if principal is None:
            # sem 'Money' a vista: escolhe a maior mochila "normal" (ignora o gigante essencial)
            normais = [c for c in do_jogador if _slotnum(c) <= 120] or do_jogador
            principal = max(normais, key=lambda c: _slotnum(c) or len(c.slots))
        out[principal.guid] = ("Personagem: INVENTARIO PRINCIPAL", "personagem")
        # rotula o container de itens-chave para nao confundir
        for c in do_jogador:
            if c.guid != principal.guid and (_slotnum(c) >= 150 or _tem_chave(c)):
                out[c.guid] = ("Personagem: Itens-chave (essenciais)", "personagem")
    return out


ORDEM = {"personagem": 0, "guilda": 1, "mundo": 2, "pal": 3, "vazio": 4}
