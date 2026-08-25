# -*- coding: utf-8 -*-
"""Assistente de Pals: decide a funcao de cada Pal (base/trabalho vs combate/equipe
vs montaria) e as MELHORES passivas para ela, usando dados minerados de palworld.gg
(aptidoes de trabalho + stats em dados/pals_roles.json) e os elementos do Pal.

Nao aplica nada sozinho -- so recomenda. Quem aplica e a interface.
"""
import os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# elemento do Pal -> passiva de boost daquele elemento (a versao "_2_PAL", a boa)
ELEM_BOOST = {
    "Normal": "ElementBoost_Normal_2_PAL",
    "Fire": "ElementBoost_Fire_2_PAL",
    "Water": "ElementBoost_Aqua_2_PAL",
    "Electricity": "ElementBoost_Thunder_2_PAL",
    "Ice": "ElementBoost_Ice_2_PAL",
    "Leaf": "ElementBoost_Leaf_2_PAL",
    "Dragon": "ElementBoost_Dragon_2_PAL",
    "Dark": "ElementBoost_Dark_2_PAL",
    "Earth": "ElementBoost_Earth_2_PAL",
}

# nome do trabalho no palworld.gg -> nome do enum no save
WORK_ENUM = {
    "Kindling": "EmitFlame", "Watering": "Watering", "Planting": "Seeding",
    "Generating Electricity": "GenerateElectricity", "Handiwork": "Handcraft",
    "Gathering": "Collection", "Lumbering": "Deforest", "Mining": "Mining",
    "Medicine Production": "ProductMedicine", "Cooling": "Cool",
    "Transporting": "Transport", "Farming": "MonsterFarm",
}

# nomes dos tipos de trabalho -> rotulo curto PT (so para exibir)
WORK_PT = {
    "Kindling": "Fogo", "Watering": "Rega", "Planting": "Plantio",
    "Generating Electricity": "Eletricidade", "Handiwork": "Trab. manual",
    "Gathering": "Coleta", "Lumbering": "Lenha", "Mining": "Mineracao",
    "Medicine Production": "Remedios", "Cooling": "Refrigeracao",
    "Transporting": "Transporte", "Farming": "Fazenda",
}

_eng = None


class Perfil(object):
    def __init__(self, roles, elems):
        self.roles = roles            # {especie: {"work":{..}, "stats":{..}}}
        self.elems = elems            # {especie: [elementos]}
        # distribuicao de combate para dar rotulo Forte/Medio/Fraco
        cs = sorted(self._combate_bruto(e) for e in roles) or [0]
        self._c_lo, self._c_hi = cs[0], cs[-1]
        n = len(cs)
        self._c_p60 = cs[int(n * 0.60)] if n else 0
        self._c_p85 = cs[int(n * 0.85)] if n else 0

    # ---- pontuacoes ----
    @staticmethod
    def _norm(esp):
        for pre in ("BOSS_", "Boss_"):
            if esp.startswith(pre):
                return esp[len(pre):]
        return esp

    def _stats(self, esp):
        return self.roles.get(self._norm(esp), {}).get("stats", {})

    def _combate_bruto(self, esp):
        s = self._stats(esp)
        atk = max(s.get("Melee Attack", 0), s.get("Shot Attack", 0))
        return atk * 1.0 + s.get("Defense", 0) * 0.4 + s.get("HP", 0) * 0.4

    def works(self, esp):
        return self.roles.get(self._norm(esp), {}).get("work", {})

    def base_nivel(self, esp):
        w = self.works(esp)
        return max(w.values()) if w else 0

    def analisar(self, esp):
        """Retorna resumo do Pal para exibir e decidir a funcao."""
        w = self.works(esp)
        base_max = max(w.values()) if w else 0
        base_sum = sum(w.values())
        comb = self._combate_bruto(esp)
        if comb >= self._c_p85:
            comb_lbl = "Forte"
        elif comb >= self._c_p60:
            comb_lbl = "Medio"
        else:
            comb_lbl = "Fraco"
        bom_base = base_max >= 3
        bom_combate = comb >= self._c_p60
        # funcao sugerida
        if bom_base and not bom_combate:
            papel = "trabalho"
        elif bom_combate and not bom_base:
            papel = "combate"
        elif bom_base and bom_combate:
            papel = "ambos"
        else:
            papel = "combate"       # fraco em tudo: por padrao vira combate
        melhores = sorted(w.items(), key=lambda kv: -kv[1])[:3]
        return {
            "papel": papel,
            "bom_base": bom_base, "bom_combate": bom_combate,
            "base_max": base_max, "base_sum": base_sum,
            "combate": comb, "combate_lbl": comb_lbl,
            "works": [(WORK_PT.get(k, k), v) for k, v in melhores],
        }

    def _boost_elemento(self, esp):
        for e in self.elems.get(self._norm(esp), []):
            if e in ELEM_BOOST:
                return ELEM_BOOST[e]
        return "ElementBoost_Normal_2_PAL"

    def passivas(self, esp, papel):
        """As 4 melhores passivas (IDs internos) para o Pal naquela funcao.
        No combate, varia conforme os stats do Pal (tanque / dano / mobilidade)."""
        boost = self._boost_elemento(esp)
        if papel == "trabalho":
            return ["CraftSpeed_up3", "Rare", "Legend", "PAL_ALLAttack_up3"]
        if papel == "montaria":
            return ["Legend", "MoveSpeed_up_3", boost, "PAL_ALLAttack_up3"]
        # combate: escolhe o perfil pelas caracteristicas reais do Pal
        s = self._stats(esp)
        atk = max(s.get("Melee Attack", 0), s.get("Shot Attack", 0))
        tank = s.get("Defense", 0) + s.get("HP", 0)
        vel = s.get("Sprinting Speed", 0)
        if atk and tank:
            if tank >= atk * 1.9:            # resistente -> build defensiva
                return ["Legend", "Deffence_up3", boost, "PAL_ALLAttack_up3"]
            if atk >= tank * 1.15:           # frágil e forte -> dano puro
                return ["Legend", "PAL_ALLAttack_up3", boost, "Noukin"]
        if vel >= 1400:                      # muito veloz -> mobilidade + dano
            return ["Legend", "PAL_ALLAttack_up3", boost, "MoveSpeed_up_3"]
        return ["Legend", "PAL_ALLAttack_up3", boost, "Rare"]   # equilibrado

    def aptidoes_enum(self, esp, rank=3):
        """{enum_do_save: rank} para as aptidoes que o Pal JA tem (para reforca-las)."""
        out = {}
        for work in self.works(esp):
            e = WORK_ENUM.get(work)
            if e:
                out[e] = rank
        return out

    def almas(self, papel):
        """{qual_alma: valor} conforme a funcao (valores conservadores, sem overpower)."""
        if papel == "trabalho":
            return {"trabalho": 10, "hp": 10}
        if papel == "montaria":
            return {"sp": 10, "hp": 10, "atk": 10}
        return {"atk": 10, "hp": 10}          # combate

    def plano(self, individuos):
        """individuos: lista de (especie, id_unico). Agrupa por especie e, para os
        Pals bons em base E combate, divide as copias -- a maioria para base.
        Retorna lista de dicts por individuo: {especie, papel}."""
        from collections import defaultdict
        por_esp = defaultdict(list)
        for esp, uid in individuos:
            por_esp[esp].append(uid)
        plano = {}
        for esp, uids in por_esp.items():
            a = self.analisar(esp)
            if a["papel"] == "ambos" and len(uids) >= 2:
                # foco maior em base: ceil(n*0.6) vao para base, resto combate
                nbase = max(1, (len(uids) * 3 + 4) // 5)   # ~60%
                for i, uid in enumerate(uids):
                    plano[uid] = "trabalho" if i < nbase else "combate"
            else:
                papel = "trabalho" if a["papel"] in ("trabalho", "ambos") else "combate"
                for uid in uids:
                    plano[uid] = papel
        return plano


def carregar():
    global _eng
    if _eng is None:
        roles = json.load(open(os.path.join(BASE, "dados", "pals_roles.json"), encoding="utf-8"))
        try:
            elems = {k: v.get("elements", [])
                     for k, v in json.load(open(os.path.join(BASE, "dados", "breeding.json"),
                                                 encoding="utf-8"))["pals"].items()}
        except Exception:
            elems = {}
        _eng = Perfil(roles, elems)
    return _eng
