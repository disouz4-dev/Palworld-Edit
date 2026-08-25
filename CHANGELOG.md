# Changelog — Palworld Editor

Todas as mudanças notáveis por versão. As datas seguem AAAA-MM-DD.

## v1.6.10 — 2026-08-25
### Fim do aviso repetido de "itens fora do lugar"
- O editor nao mostra mais, a cada abertura, o aviso de itens no container de
  itens-chave (ele flagava itens legitimos como Lanterna/AutoMealPouch). A causa
  raiz ja estava corrigida; agora so remove, em silencio, slots realmente invalidos.
  _No more repeated "misplaced items" prompt on every launch._
_All notable changes per version._

## v1.6.9 — 2026-08-25
### Correção: condensação 4 estrelas não aplicava
- Se o save **não tinha nenhum Pal já condensado**, o editor não conseguia criar o
  campo de condensação (faltava um "molde") e a condensação **falhava em silêncio**
  (IVs e passivas aplicavam, mas nenhum Pal ficava com estrelas). Agora o molde de
  condensação é **criado do zero** quando necessário — a condensação 4★ sempre vale.
  _Fix: 4-star condensation now applies even when no pal was condensed yet._

## v1.6.8 — 2026-08-25
### Restaurar backup mais forte contra a nuvem
- Ao **restaurar um backup**, o editor agora marca o save restaurado como o **mais
  recente** (atualiza os filetimes do índice), para a sincronização da nuvem do Xbox
  **subir** o save restaurado em vez de reverter o local para a versão antiga/quebrada.
  _Restore now marks the save as newest so Xbox cloud sync uploads it instead of reverting._

## v1.6.7 — 2026-08-25
### Pontos de tecnologia / technology points
- Novo na tela **Personagem**: editar **Pontos de tecnologia** e **Pontos de
  tecnologia antiga**. Esses pontos ficam no save do JOGADOR, que é comprimido com
  **Oodle** — o editor lê com um Oodle opcional (aponte uma vez o `oodle-data-shared.dll`
  do FModel, ou um `oo2core_*.dll`) e **regrava como zlib**, que o jogo também lê.
  Sem Oodle, o resto do editor funciona normalmente. _New: edit Technology and Ancient
  Technology points (player save is Oodle-compressed; needs an Oodle DLL once to read)._

## v1.6.6 — 2026-08-25
### Ajustes no upgrade em massa
- **Condensação 4 estrelas e IVs altos (90-100) para TODOS** (base e combate precisam
  de stats altos). A diferença de poder entre início e fim de jogo vem naturalmente
  dos **stats-base** do Pal, não de nerfar o upgrade. _Condensation 4★ and high IVs are
  now universal; the power gap comes from base stats._
- **Modo automático respeita o local**: Pals na **equipe** viram **combate** (nunca
  recebem Artesão Transcendental nem outra passiva de trabalho); Pals nas **bases**
  viram **trabalho**; na caixa, decide pela análise. _Auto mode: party = combat (no
  work passives), bases = work._

## v1.6.5 — 2026-08-25
### Upgrade em massa proporcional ao tier / power scaled by tier
- O otimizador agora **escala o upgrade pela raridade/tier** de cada Pal: os de
  **início de jogo** (Lamball, Cattiva…) recebem menos (≈1 estrela, IVs ~55, almas
  baixas) e os de **fim de jogo/lendários** (Anubis, Shadowbeak, Frostallion) recebem
  o **máximo** (4 estrelas, IVs ~100, almas altas). Assim os fracos não ficam tão
  fortes quanto os lendários. _Mass upgrade now scales with each pal's rarity tier._
- Pals de **base** agora recebem **Insônia** (não dormem, trabalham 24h) no conjunto
  de passivas. _Base pals now get Insomniac (work 24h)._

## v1.6.4 — 2026-08-25
### Correção automática dos itens invisíveis / auto-repair of invisible items
- Ao abrir o save, se houver itens normais parados no container de **itens-chave**
  (deixados por um bug **já corrigido**), o editor **oferece movê-los para a mochila**
  uma única vez — assim o que só contava **peso** volta a **aparecer**. Sem botão
  permanente; os itens-chave de verdade não são tocados. _One-time auto-repair on load._
### Passivas com variedade por Pal / more varied passives
- A sugestão de combate agora **muda conforme o Pal**: tanques recebem build
  **defensiva** (Casca de Aço), Pals frágeis e fortes recebem **dano puro**
  (Brutamontes), rápidos ganham **mobilidade**, e todos recebem o **boost do próprio
  elemento** (Regente de Fogo/Gelo/Raio…). _Combat passives now vary by the pal's
  stats and element instead of being identical._

## v1.6.3 — 2026-08-25
### Correções importantes / Important fixes
- **Itens agora vão para a mochila visível certa.** O app estava mirando o container
  de **itens-chave** (Essential, o maior) em vez da mochila comum, então os itens
  adicionados **contavam peso mas não apareciam** no inventário. Agora a mochila
  principal é identificada pelo slot de **dinheiro (Money)**; o container de
  itens-chave aparece separado. _Items now go to the real visible backpack (found by
  the Money slot), not the key-items container._
- **Respeita a capacidade real (`SlotNum`)** de cada inventário/baú: não cria mais
  "slots fantasma" fora do limite (causa de itens invisíveis) e avisa quando o
  container está **cheio**. Vale para o inventário e para **baús**. _Respects each
  container's real capacity; no more phantom slots; warns when full._
- **Editor individual de Pal** agora **injeta** os campos que faltam (condensação,
  talentos, passivas) — antes a condensação/passivas não aplicavam em Pals que nunca
  foram condensados. _Single-pal editor now injects missing fields (condensation etc.)._

## v1.6.2 — 2026-08-24
### Importante: nuvem do Xbox / Xbox cloud sync
- Diagnóstico: quando as mudanças **não aparecem no jogo**, o editor **está gravando
  certo no arquivo local** (confirmado byte a byte nos dados reais) — quem desfaz é a
  **sincronização de save na nuvem** do Xbox/Game Pass, que restaura o save antigo ao
  abrir o jogo. Agora o app **explica isso ao salvar** e ensina o passo a passo
  (abrir o jogo **offline**). _The editor writes the local save correctly; Xbox cloud
  sync can restore the old save — the app now explains the offline workaround._
- A lista de mundos agora mostra a **data da última jogada** e abre por padrão o
  **mundo jogado mais recentemente** (evita editar o mundo errado). _World list shows
  last-played date and defaults to the most recent world._

## v1.6.1 — 2026-08-24
### Correções / Fixes
- O botão **APLICAR otimização** do otimizador em massa agora fica **sempre visível**
  (o rodapé estava sendo empurrado para fora da janela pela tabela). _Fix: the mass
  optimizer's APLICAR button was pushed off-screen; the footer is now pinned._

## v1.6.0 — 2026-08-24
### Assistente de Pals (passivas por função) / Pal advisor
- **Sugestão de passivas agora é por Pal**, não mais igual para todos. Usa dados
  minerados do palworld.gg (aptidões de trabalho + stats de 284 Pals em
  `dados/pals_roles.json`) e o **elemento** do Pal para escolher o boost certo
  (Regente de Fogo, Regente de Raio, Dragão Divino, etc.).
  _Passive suggestions are now per-pal, using mined work/stats + the pal's element._
- Cada Pal é classificado em **Combate (equipe)**, **Trabalho (base)** ou **Montaria**,
  com rótulo de força de combate e as melhores aptidões mostradas.

### Modificação / otimização em massa / Mass optimizer
- Novo botão **"Otimizar / modificar em massa"** na Caixa de Pals:
  - Escolha o **local** (equipe, caixa, bases ou todos) e a **função**.
  - Modo **Automático**: olha a sua caixa, decide quais Pals são melhores para
    **base** e quais para **combate**, e quando um Pal é bom nos dois, **divide as
    cópias** (foco maior em base). Mostra o plano antes de aplicar.
  - Aplica de uma vez, por Pal: **passivas por função**, **IVs altos (90-100)**,
    **condensação 4 estrelas**, **almas** (Estátua do Poder) e **aptidões de
    trabalho reforçadas**. Com confirmação e backup automático.
  _New mass optimizer: pick location + role (or auto base-vs-combat split favoring
  base) and apply passives/IVs/condensation/souls/work-aptitudes to every pal at once._

### Correções / Fixes
- **Condensação** agora funciona mesmo em Pals que nunca foram condensados (o campo
  `Rank` era ausente e não era criado — agora é injetado). Mostrada como
  **estrelas 0-4**. _Condensation now works even when the pal had no Rank field._
- A sugestão também aplica a condensação 4★ corretamente.

### Dados / Data
- Adicionado `dados/pals_roles.json` (stats + aptidões de trabalho de 284 Pals,
  minerado de palworld.gg) — versionado junto com o app.

## v1.5.0 — 2026-08-24
- **Breeding**: escolha o Pal que quer criar e veja os pares que o geram (só os seus
  Pals ou todos), com aviso quando precisar trocar o sexo de um deles.
- Todos os **ícones** inclusos (1209 itens + 284 Pals) — o app já vem completo.
- Instalação **por usuário** com atalho no Menu Iniciar, entrada em
  Adicionar/Remover programas e **desinstalador**.
- **Verificar atualização** e **localizar o save** automaticamente.
- Gravação segura por **copy-on-write** (validada no jogo, não corrompe).
