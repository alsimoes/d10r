# Plano de consolidação do repositório `alsimoes/d10r`

Formato pensado para o **Phases Mode** do Traycer: cada fase tem objetivo, arquivos,
critérios de aceite e verificação. As decisões já tomadas estão em "Decisões fechadas" —
elas devem ser tratadas como restrições, não reabertas na etapa de *Intent Clarification*.

---

## 1. Estado atual (verificado)

| Item | Situação |
|---|---|
| Branch padrão | `master` (código de 2010, Python 2) |
| `development` | 4 commits (nov/2025): Python 3, PySide6, pytest. 4 à frente da `master`, 0 atrás |
| `original-code` | Mesmo commit da `master` |
| `modular` | 7 commits atrás da `master`, 0 à frente |
| `acumulativo` | 4 commits de 2010 (modo acumulativo), 4 à frente da `master`, 0 atrás |
| Tags | `0.1` (8cf4535) e `0.1beta` (48213dd), ambas dentro do histórico da `master` |
| Issues no fork | **Desativadas** (`has_issues: false`) |
| PR aberto | `ygormutti/d10r#22`, de `alsimoes:development` → `ygormutti:master` |
| Correções prontas | 3 commits no arquivo `d10r-correcoes.patch`, ainda não aplicados |

Consequência topológica que simplifica tudo: **`development` e `acumulativo` são
descendentes diretos da `master`**. Não há divergência, então a `master` avança por
*fast-forward*, sem merge nem reescrita de histórico.

## 2. Decisões fechadas

1. A `acumulativo` será **portada** para Python 3/PySide6 e integrada.
2. O PR #22 será **fechado** e não reenviado.
3. SQLite fica **fora de escopo**; vira issue, e o INI permanece.
4. Estado final: **apenas a `master`**, com todas as demais branches apagadas.

## 3. Estado-alvo

- `master` contém: migração Python 3/PySide6 + 3 correções + modo acumulativo portado.
- Suíte de testes verde, executável com `python -m pytest -q tests`.
- Documentação coerente com o código (README, `docs/`, `AGENTS.md`).
- Nenhuma outra branch remota. Tags `0.1` e `0.1beta` preservadas, mais tags de arquivo.
- PR #22 fechado; issue de SQLite registrada.

---

## 4. Papéis dos agentes e modelos sugeridos

O Traycer atua como *outer loop*: planeja, decompõe, reúne contexto e verifica o que os
agentes de código produzem, usando um conjunto de modelos especializados em vez de um só.
Sugestão de alocação por papel — ajuste conforme os modelos que você tem habilitados:

| Papel | Responsabilidade | Perfil de modelo sugerido |
|---|---|---|
| **Arquiteto / Planner** | Decompor as fases, decidir a estratégia do porte do modo acumulativo | Modelo de raciocínio forte (ex.: GPT-5.6-Sol, Opus, GLM 5.3, Deepseek V4.1 Pro) |
| **Scout / Contexto** | Mapear usos de `creditar_tudo`, `salvar_config`, `parse_config` antes de cada edição | Modelo rápido e barato (ex.: GPT-5.6-Luna, Haiku ou Deepseek V4.1 Flash) |
| **Implementador** | Editar código e testes (Claude Code, Cursor ou equivalente) | Modelo de codificação (ex.: GPT-5.3-Codex, Sonnet ou GLM 5.3 Flash) |
| **Crítico / Verificador** | Revisar cada fase contra o plano; **modelo diferente do implementador** | Modelo de raciocínio forte, de outra família se possível |
| **Operador Git** | Executar comandos destrutivos (ff, delete, tags) | **Humano**, não agente |

Duas regras que valem mais que a escolha dos modelos:

- **Crítico ≠ implementador.** Revisar com o mesmo modelo que escreveu tende a repetir o
  mesmo ponto cego. Essa é a razão de existir o passo de verificação entre fases.
- **Nenhum agente executa `push`, `push --delete` ou `git branch -D` em remoto.** As fases
  5 e 6 são de operação, feitas por você. O risco de uma limpeza automatizada errada é
  perda de histórico, e o ganho de automatizá-la é quase nulo.

Sobre o **YOLO Mode**: use nas fases 2 e 3, que são de código com testes cobrindo o
resultado. Evite nas fases 5 e 6.

---

## 5. Fases

### Fase 0 — Salvaguarda e preparação (operação, humano)

Sem alteração de código. Deixa o terreno pronto e impede perdas.

1. Criar tags de arquivo apontando para as pontas que serão apagadas:
   ```bash
   git fetch --all
   git tag arquivo/acumulativo origin/acumulativo
   git tag arquivo/development-pre-correcoes origin/development
   git push origin arquivo/acumulativo arquivo/development-pre-correcoes
   ```
2. Ativar Issues em **Settings → Features → Issues** do fork (hoje estão desativadas; sem
   isso a issue do SQLite da fase 4 não pode ser criada).
3. Fechar o PR #22 com um comentário explicando que o trabalho seguirá consolidado na
   `master` do fork:
   ```bash
   gh pr close 22 --repo ygormutti/d10r --comment "Fechando: o trabalho será consolidado na master do fork antes de qualquer proposta ao upstream."
   ```

**Aceite:** tags no remoto, Issues ativas, PR #22 fechado.
**Observação:** as branches de 2010 continuam existindo em `ygormutti/d10r`, então nada é
definitivamente perdido mesmo sem as tags. Elas são conveniência, não seguro único.

---

### Fase 1 — Aplicar as correções pendentes

**Entrada:** `d10r-correcoes.patch` (3 commits).
**Base:** `development`.

```bash
git switch -c fix/cronometro-credito-dialogos origin/development
git am caminho/para/d10r-correcoes.patch
python -m pytest -q tests    # esperado: 25 passed
```

**Arquivos tocados:** `gui.py`, `gui_pyside.py`, `utils.py`, `data.py`, `d10r.py`,
`easygui.py`, `tests/` (inclui `tests/conftest.py` novo).

**Aceite:** 25 testes passam; `git am` sem conflito.
**Verificação do crítico:** confirmar que `gui.py` não redefine `CronometroDialogQt`, que
`main()` não captura mais `AttributeError`, e que `buttonbox` usa `ButtonBoxQt`.

---

### Fase 2 — Portar o modo acumulativo

A maior fase, e a única com risco real de regressão.

**Contexto de origem:** 4 commits de `origin/acumulativo`, em Python 2. Ver o diff com
`git diff origin/master origin/acumulativo`.

**O que a funcionalidade faz:**
- Nova chave `acumular` (booleano) na seção `__header__` do arquivo de configuração.
- `init()` pergunta ao usuário se as horas não cumpridas se acumulam de uma semana para a outra.
- `parse_config()` retorna 4 valores; `salvar_config()` e `creditar_tudo()` recebem `acumular`.
- Com `acumular=False`: o crédito é limitado a 1 semana e saldos positivos são zerados
  antes de creditar (só o excedente cumprido a mais é carregado adiante).
- `init()` passa a creditar na primeira execução e a gravar a data de hoje como timestamp.

**Adaptações obrigatórias no porte:**
- Sintaxe Python 3 (o original tem `print vezes`, que é debug e **deve ser removido**).
- Preservar as correções da fase 1: o parâmetro `hoje` de `creditar_tudo` e a contagem
  corrigida de `dias_x_entre` não existem no código de 2010.
- Compatibilidade retroativa: arquivos `~/.d10r` existentes não têm a chave `acumular`.
  Usar `parser.getboolean(HEADER, 'acumular', fallback=...)` ou equivalente, em vez de
  deixar estourar `NoSectionError`/`NoOptionError`.
- As mudanças de rótulo da GUI ("Progresso:", "Encerrar") são opcionais e aplicam-se ao
  `gui_pyside.py`, não ao `gui.py` Tkinter, que não existe mais.

**Testes exigidos (novos, em `tests/test_data.py`):**
- `acumular=True` credita N semanas de atraso.
- `acumular=False` credita no máximo 1 semana.
- `acumular=False` zera saldo positivo antes de creditar.
- `acumular=False` preserva saldo negativo (horas cumpridas a mais).
- `parse_config` lê um arquivo legado sem a chave `acumular` sem quebrar.
- Ida e volta `salvar_config` → `parse_config` com o novo campo.

**Aceite:** todos os testes anteriores continuam verdes; os novos passam; nenhum `print`
de debug no código.
**Verificação do crítico:** checar especificamente a interação entre `acumular=False` e o
`hoje` introduzido na fase 1, e se algum chamador de `parse_config`/`salvar_config` ficou
com a aridade antiga.

---

### Fase 3 — Documentação e higiene

Sem mudança de comportamento. Pode rodar em paralelo à fase 2 se o Traycer suportar
paralelismo, desde que em branch separada, já que toca arquivos diferentes.

1. **README** (hoje pede Python 2.6 e aponta para um link morto de download): reescrever
   com requisitos reais (Python 3, PySide6, pytest), instalação, execução e nota sobre
   o modo acumulativo. Manter a referência de autoria e a licença.
2. **`AGENTS.md`** (vazio): preencher com convenções do projeto — estrutura dos módulos,
   como rodar os testes, estilo de commit — ou remover o arquivo. Um arquivo vazio no
   repositório é ruído.
3. **`docs/Analise.md`**: atualizar as seções que descrevem Tkinter/Python 2.6 como estado
   atual e corrigir a afirmação de que a ordenação de prioridades é "arrastar e soltar"
   (são botões Subir/Descer).
4. **`docs/Prompts.md`**: marcar o item SQLite como adiado, referenciando a issue da fase 4.
5. **`docs/Testes_PySide6.md`**: revisar o roteiro manual, que cita blocos comentados hoje
   inexistentes ou alterados.
6. **Código morto em `gui_pyside.py`**: remover a `MainWindow` de exemplo e o bloco
   `if __name__ == '__main__'` de testes manuais comentados, ou movê-los para
   `validations/`, pasta já prevista no `docs/Prompts.md`.
7. **Dependências**: adicionar `requirements.txt` (ou `pyproject.toml`) com `PySide6` e
   `pytest`. Hoje não há nada declarado.

**Aceite:** nenhuma menção a Python 2.6 ou Tkinter como estado atual; testes seguem verdes;
`python -m pytest -q tests` documentado no README.

---

### Fase 4 — Consolidar na `master`

```bash
git switch master
git merge --ff-only <branch-da-fase-3>   # deve ser fast-forward
python -m pytest -q tests
git push origin master
```

Se o `--ff-only` falhar, **pare**: significa que algo divergiu e o plano precisa ser
revisto, não forçado com `--force`.

Depois do push:
- Criar a issue do SQLite (requer o passo 2 da fase 0), descrevendo o objetivo, o formato
  atual em INI e a necessidade de migração dos arquivos existentes.
- Opcional, e recomendado: workflow mínimo do GitHub Actions rodando
  `pytest` com `QT_QPA_PLATFORM=offscreen`, para que a suíte não dependa de alguém lembrar
  de executá-la.

**Aceite:** `master` no GitHub com o código final e testes verdes; issue criada.

---

### Fase 5 — Apagar as branches (operação, humano)

Executar **somente após** a fase 4 estar publicada e verificada.

```bash
git push origin --delete development
git push origin --delete acumulativo
git push origin --delete modular
git push origin --delete original-code
git fetch --prune
git branch -D fix/cronometro-credito-dialogos  # e demais locais
```

Nenhuma delas é a branch padrão, então o GitHub permite a exclusão direta pela interface,
em **Branches → ícone de lixeira**, se preferir.

**Pré-checagem obrigatória, para cada branch:**
```bash
git rev-list --left-right --count origin/master...origin/<branch>
```
O número à direita deve ser `0` (nada exclusivo), **ou** o conteúdo exclusivo deve estar
coberto por uma tag de arquivo da fase 0. Para `acumulativo`, o conteúdo foi portado, não
mesclado: é a tag `arquivo/acumulativo` que a torna descartável.

**Aceite:** `git ls-remote --heads origin` lista apenas `master`.

---

### Fase 6 — Verificação final

Checklist, idealmente com um agente crítico que não participou das fases 2 e 3:

- [ ] `git ls-remote` mostra só `refs/heads/master` e as tags esperadas.
- [ ] Clone limpo: `git clone` → `pip install -r requirements.txt` → `pytest -q tests` verde.
- [ ] Execução manual seguindo `docs/Testes_PySide6.md`: escolher atividade, cronômetro,
      débito manual, cancelamento.
- [ ] Arquivo `~/.d10r` de antes da mudança ainda abre (compatibilidade retroativa).
- [ ] Nenhuma issue ou PR aberto por engano; PR #22 fechado.
- [ ] README reflete o estado real do projeto.

---

## 6. Riscos

| Risco | Mitigação |
|---|---|
| Porte do acumulativo desfaz correções da fase 1 | Fases 1 e 2 separadas, com os testes da fase 1 rodando na fase 2 |
| Agente executa limpeza de branches cedo demais | Fase 5 é humana, com pré-checagem por branch |
| `--ff-only` falha e alguém força o push | Regra explícita de parar; o histórico é o único registro real |
| Arquivo `~/.d10r` existente quebra com a nova chave | Teste de compatibilidade retroativa obrigatório na fase 2 |
| Issue do SQLite não pode ser criada | Ativar Issues na fase 0, antes da fase 4 |

## 7. Fontes

- https://docs.traycer.ai/extension/tasks/phases
- https://docs.traycer.ai/extension/tasks
- https://traycer.ai/blog/multi-model-architecture
- https://api.github.com/repos/alsimoes/d10r (campo `has_issues`)
- https://github.com/ygormutti/d10r/pull/22
- Topologia das branches: `git rev-list --left-right --count` e `git merge-base` sobre o clone
