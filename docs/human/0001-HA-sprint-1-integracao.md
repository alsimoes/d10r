# HA-0001 — Integração do Sprint 1

Este runbook descreve as ações que devem ser executadas pelo responsável humano após a aprovação do Sprint 1.

## Pré-condições

- A revisão final do Sprint 1 está aprovada em `sprint-1-final-review`.
- A worktree dos agentes está limpa.
- Nenhuma operação remota ou destrutiva foi executada pelos agentes.
- O responsável humano confirmou a política de integração e o destino correto da branch.

## Passo a passo

1. Leia a revisão final e confirme que o escopo aprovado é apenas a estabilização Python 3 + PySide6.
2. Inspecione o estado local antes de qualquer alteração:
   - `git status --short`
   - `git log --oneline --decorate -n 12`
   - `git branch --show-current`
3. Confirme que os commits da entrega estão presentes, incluindo a remediação `e63800e`.
4. Confirme que a branch de integração e o destino remoto estão corretos; não prossiga se houver divergência não compreendida.
5. Execute a suíte final localmente, se desejar uma última verificação independente:
   - `$env:QT_QPA_PLATFORM = "offscreen"`
   - `python -m pytest -q tests`
   - `python -m compileall -q .`
   - `git diff --check`
6. Faça push somente da branch aprovada, usando a política de revisão do projeto.
7. Abra ou atualize o pull request para o destino definido pelo responsável humano; inclua a revisão final e o resultado dos testes.
8. Aguarde a revisão humana e os checks remotos antes de fazer merge.
9. Após o merge, atualize as issues e registros do projeto com o resultado do Sprint 1.
10. Só depois de confirmar que não há necessidade de rollback, remova branches locais ou remotas obsoletas, se isso fizer parte da política do projeto.
11. Registre neste arquivo ou no registro de entrega a data, o responsável, o pull request e o commit efetivamente integrado.

## Restrições

- Não incluir o modo acumulativo ou SQLite nesta integração.
- Não fazer push, merge, fechar issues ou excluir branches antes de confirmar o destino e a revisão humana.
- Não usar comandos destrutivos sem verificar o alvo exato e a possibilidade de recuperação.

## Registro da execução

- Responsável: André Simões
- Data: 12/09/2026
- Pull request: _a preencher_
- Commit integrado: _a preencher_
- Observações: _a preencher_
