# HA-0002 — Integração do Sprint 2

Este runbook descreve, em ordem, as ações humanas ou delegadas ao Sol Senior para integrar
o modo acumulativo, a interface PySide6 pura e o CI do Sprint 2 no fork `alsimoes/d10r`.

## Pré-condições

- O contrato está em `sprint-2-acumulativo-pyside6-ci` nos artefatos do épico.
- A revisão técnica da Terra aprovou o código e deixou pendentes apenas este runbook, o CI
  do head final e o fechamento da issue #1 na integração.
- A branch de entrega é `feat/sprint-2`, criada a partir de `d0f37f1`.
- `origin` deve ser `https://github.com/alsimoes/d10r.git`.
- `upstream` (`https://github.com/ygormutti/d10r.git`) é somente leitura.
- A issue #4 registra a migração futura para SQLite e deve permanecer aberta.
- Luna e Terra fazem somente commits locais; push, PR, merge e fechamento de issues são
  responsabilidade do Sol Senior ou do responsável humano.

## Passo a passo

1. Confirmar o estado local antes de qualquer operação remota:
   - `git branch --show-current` deve retornar `feat/sprint-2`.
   - `git status --short` deve estar limpo.
   - `git remote get-url origin` deve retornar o fork `alsimoes/d10r`.
   - `git log --oneline --decorate -n 12` deve conter todos os commits do Sprint 2.
   - Parar se houver arquivo inesperado, conflito, rebase, merge ou destino divergente.

2. Executar os gates locais finais:
   - `$env:QT_QPA_PLATFORM = "offscreen"`
   - `.venv\Scripts\python -m pytest -q tests`
   - `.venv\Scripts\python -m compileall -q .`
   - `git diff --check 90c0efe..HEAD -- . ":(exclude)docs/d10r-correcoes.patch"`
   - Resultado esperado: 49 testes ou mais, zero falhas e nenhum erro estático.

3. Confirmar os invariantes de escopo:
   - `easygui.py` não existe e não há import executável de EasyGUI.
   - O workflow usa Ubuntu, Python 3.12 e `QT_QPA_PLATFORM=offscreen`.
   - SQLite não foi implementado; `docs/Prompts.md` referencia a issue #4.
   - Nenhum commit veio por merge ou cherry-pick de `upstream/acumulativo`.

4. Incluir este runbook na branch de entrega:
   - `git diff -- docs/human/0002-HA-sprint-2-integracao.md`
   - `git add docs/human/0002-HA-sprint-2-integracao.md`
   - `git commit -m "docs(human): add Sprint 2 integration runbook"`
   - Não criar commit duplicado se o arquivo já estiver rastreado no head aprovado.

5. Publicar somente a branch do fork, sem reescrever histórico:
   - Repetir `git remote get-url origin` e `git branch --show-current`.
   - `git push origin feat/sprint-2`
   - Nunca usar `--force` e nunca executar `git push upstream`.

6. Validar o CI do head publicado:
   - Confirmar que o workflow foi disparado pelo push e que o SHA corresponde ao head.
   - Aguardar pytest e compileall terminarem verdes.
   - Se falhar, registrar job, etapa, log e SHA; não fazer merge nem trocar runner sem
     arbitragem.

7. Abrir ou atualizar o pull request no próprio fork:
   - Origem: `alsimoes:feat/sprint-2`; destino: `alsimoes:master`.
   - Título sugerido: `Sprint 2: modo acumulativo, PySide6 puro e CI`.
   - O corpo deve listar modo acumulativo, remoção do EasyGUI, correções pequenas, CI,
     documentação, contagem de testes e as revisões da Terra e do Sol.
   - Incluir `Closes #1` para fechar a issue de remoção do EasyGUI somente após o merge.
   - Referenciar a issue #4 como trabalho futuro, sem fechá-la.

8. Conferir o PR antes do merge:
   - Estado mergeável e base/head corretos.
   - Diff limitado ao contrato e sem arquivo inesperado.
   - Check do GitHub Actions verde no SHA atual.
   - Revisão técnica final sem achado bloqueador ou alto.
   - Não fazer merge enquanto houver divergência ou check pendente.

9. Integrar conforme a política vigente do repositório:
   - Executar o merge sem force push nem alteração do upstream.
   - Registrar número do PR, horário e hash integrado.
   - Confirmar que `origin/master` contém o commit resultante.

10. Tratar as issues após confirmar o merge:
    - Verificar que a issue #1 foi fechada automaticamente por `Closes #1`.
    - Se não foi, comentar com o PR e o hash integrado e fechá-la manualmente.
    - Confirmar que a issue #4 permanece aberta e representa SQLite como escopo futuro.

11. Registrar a execução:
    - Preencher todos os campos de “Registro da execução” abaixo.
    - Se o PR já tiver sido integrado, publicar o registro em commit documental separado no
      `master`, após atualizar a cópia local por fast-forward.
    - Executar `git diff --check` e confirmar o status limpo depois do registro.

12. Não limpar branches neste runbook:
    - Preservar `feat/sprint-2` até confirmação explícita de que não haverá rollback.
    - Qualquer limpeza posterior exige listagem prévia, prova de integração e nova autorização.

## Restrições

- Escrever somente em `alsimoes/d10r`; `ygormutti/d10r` permanece estritamente somente leitura.
- Não usar force push, rebase destrutivo ou remoção automática de branches/tags.
- Não implementar SQLite, rótulos cosméticos do upstream ou mudanças do menu CLI.
- Não fechar a issue #1 antes de o PR estar integrado.
- Não fechar a issue #4 neste sprint.
- Diante de qualquer divergência entre SHA local, SHA do CI e SHA do PR, parar e registrar.

## Validação esperada

- Suíte Python 3.12 headless integralmente verde em ambiente local e no GitHub Actions.
- `compileall` e diff-check emendado verdes.
- PR integrado em `alsimoes/master` com a issue #1 fechada.
- Issue #4 aberta, documentação coerente e worktree final limpa.

## Registro da execução

- Responsável: André Simões (execução delegada ao agente Sol Senior)
- Data: 13/09/2026
- Pull request: https://github.com/alsimoes/d10r/pull/5
- Head validado: `60c39b791a578f734ec38a0e40133c04c32c822e`
- Commit integrado: `75fb13b2692ee057c1ff8838efbfe3b379032008`
- CI: push da branch, pull request e pós-merge aprovados —
  https://github.com/alsimoes/d10r/actions/runs/34740330673,
  https://github.com/alsimoes/d10r/actions/runs/34740375113 e
  https://github.com/alsimoes/d10r/actions/runs/34740419836
- Issue #1: fechada automaticamente pelo merge — https://github.com/alsimoes/d10r/issues/1
- Issue #4: aberta — https://github.com/alsimoes/d10r/issues/4
- Ocorrências e rollback: o primeiro CI do head final sinalizou actions baseadas em Node.js
  20; `checkout` e `setup-python` foram atualizadas para `v7` no commit `60c39b7` e as
  execuções seguintes terminaram sem anotações. O GitHub removeu automaticamente a branch
  remota `feat/sprint-2` após o merge; a branch local foi preservada. Rollback não foi
  necessário.
