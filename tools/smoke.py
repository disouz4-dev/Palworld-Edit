# -*- coding: utf-8 -*-
import sys, os, time, importlib.util
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0,BASE)
spec=importlib.util.spec_from_file_location("ed", os.path.join(BASE,"PalSaveEditor.pyw"))
ed=importlib.util.module_from_spec(spec); spec.loader.exec_module(ed)
app=ed.App()
t0=time.time()
while time.time()-t0<120 and app.level is None:
    app.update(); time.sleep(0.15)
assert app.level, "nao carregou"
print("carregou. mundo:", app.cb_mundo.get())
assert isinstance(app.tela, ed.TelaInicio), "deveria abrir no inicio"
print("tela inicial OK")
# navega itens
app.mostrar("itens"); app.update()
t=app.tela; print("itens: containers=%d, modo TODOS itens=%d" % (len(t.map_cont), len(t.map_item)))
t.var_b.set("madeira"); app.update()
print("busca 'madeira':", list(t.map_item.values())[:4])
# personagem
app.mostrar("personagem"); app.update()
print("personagem: atributos=%d nivel=%s" % (len(app.tela.mapa), app.tela.v_nivel.get()))
# pals
app.mostrar("pals"); app.update()
tp=app.tela; print("pals na lista:", len(tp.map))
tp.v_b.set("pengu"); app.update()
print("busca pal 'pengu':", [tp.tv.item(i,"text") for i in list(tp.map)[:3]])
# seleciona 1 pal e abre painel
first=list(tp.map)[0]; tp.tv.selection_set(first); tp.sel(); app.update()
print("pal selecionado:", tp.atual.especie, "painel montado:", bool(tp.ed.winfo_children()))
print("presets:", list(tp.PRESETS))
# breeding
app.mostrar("breeding"); app.update(); print("breeding OK:", isinstance(app.tela, ed.TelaBreeding))
app.mostrar("inicio"); app.update()
app.destroy(); print("OK TOTAL")
