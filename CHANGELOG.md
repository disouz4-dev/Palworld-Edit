# Changelog — Palworld Editor

Todas as mudanças notáveis por versão. As datas seguem AAAA-MM-DD.
_All notable changes per version._

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
