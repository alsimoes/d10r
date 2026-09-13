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
6. Prepare o commit do runbook e confirme o conteúdo antes de gravar:
   - `git status --short`
   - `git diff -- docs/human/0001-HA-sprint-1-integracao.md`
   - `git add docs/human/0001-HA-sprint-1-integracao.md`
   - Mensagem sugerida: `docs(human): add Sprint 1 integration runbook`
   - `git commit -m "docs(human): add Sprint 1 integration runbook"`
   - Se o runbook já estiver incluído em outro commit, não crie um commit duplicado.
7. Faça push somente da branch aprovada, usando a política de revisão do projeto:
   - Confirme novamente a branch: `git branch --show-current`.
   - Substitua `<remoto>` e `<branch-aprovada>` pelos valores confirmados pelo responsável humano.
   - `git push <remoto> <branch-aprovada>`
   - Verifique o resultado com `git status --short` e a página do remoto.
   - Não use `--force` sem autorização explícita e uma justificativa registrada.
8. Abra ou atualize o pull request para o destino definido pelo responsável humano:
   - Origem: `<branch-aprovada>`; destino: `<branch-destino-confirmada>`.
   - Título sugerido: `Sprint 1: estabilizar baseline Python 3 + PySide6`.
   - Texto sugerido:

     ```text
     ## Objetivo
     Integrar o Sprint 1 de estabilização Python 3 + PySide6.

     ## Entregas
     - Integração das correções aprovadas, incluindo e63800e.
     - Dependências de runtime e desenvolvimento declaradas.
     - Testes headless e documentação mínima de setup.
     - Runbook humano em docs/human/0001-HA-sprint-1-integracao.md.

     ## Validação
     - 32/32 testes aprovados em Python 3.12.10.
     - compileall aprovado.
     - git diff --check aprovado.
     - Terra Pleno aprovou a revalidação.
     - Sol Senior aprovou e encerrou o Sprint 1.

     ## Fora de escopo
     - Modo acumulativo.
     - SQLite.
     - Operações remotas ou limpeza automática de branches.
     ```

   - Anexe ou vincule a revisão final do Sprint 1 e confirme que o diff do PR contém somente o escopo aprovado.
9. Aguarde a revisão humana e os checks remotos antes de fazer merge:
   - Não faça merge enquanto houver review pendente, check falhando ou divergência de escopo.
   - Se houver falha, registre o nome do check, a mensagem de erro e a decisão tomada; não reescreva a branch silenciosamente.
   - Mensagem sugerida para solicitar revisão: `Sprint 1 está pronto para revisão humana; os checks locais e a validação Terra/Sol estão registrados no PR.`
   - Após aprovação e checks verdes, faça merge conforme a política do repositório e registre o hash resultante.
10. Após o merge, atualize as issues e registros do projeto com o resultado do Sprint 1:
   - Confirme primeiro o hash integrado e o estado `merged` do PR.
   - Comentário sugerido para a issue:

     ```text
     Sprint 1 aprovado e integrado.

     Resultado: 32/32 testes, compileall e diff-check aprovados; correções de lifecycle de threads, INI malformado e cancelamentos revalidadas.
     Revisões: Terra Pleno aprovou; Sol Senior encerrou o sprint.
     Fora deste sprint: modo acumulativo e SQLite.
     PR: <link-do-PR>
     Commit integrado: <hash>
     ```

   - Atualize o status da issue somente após confirmar que o PR foi integrado.
11. Só depois de confirmar que não há necessidade de rollback, remova branches locais ou remotas obsoletas, se isso fizer parte da política do projeto:
   - Verifique o PR integrado, o hash na branch de destino e a ausência de rollback pendente.
   - Liste antes de remover: `git branch --list` e `git branch -r`.
   - Para remover uma branch local já integrada: `git branch -d <branch-obsoleta>`.
   - Para remover uma branch remota, confirme explicitamente a autorização e o alvo: `git push <remoto> --delete <branch-obsoleta>`.
   - Nunca use `-D` ou delete remoto por conveniência; preserve branches se houver dúvida.
12. Registre neste arquivo ou no registro de entrega a data, o responsável, o pull request e o commit efetivamente integrado:
   - Preencha todos os campos da seção “Registro da execução”.
   - Inclua links para o PR, issue e revisão final.
   - Mensagem sugerida para o registro: `Sprint 1 integrado em <data> por <responsável>; PR <link>; commit <hash>; rollback: não necessário.`
   - Faça um último `git diff --check` antes de qualquer commit adicional no próprio runbook.

## Restrições

- Não incluir o modo acumulativo ou SQLite nesta integração.
- Não fazer push, merge, fechar issues ou excluir branches antes de confirmar o destino e a revisão humana.
- Não usar comandos destrutivos sem verificar o alvo exato e a possibilidade de recuperação.
- Substituir todos os placeholders (`<...>`) antes de executar comandos ou publicar textos.
- Se o estado remoto divergir do esperado, parar e registrar a divergência para decisão humana.

## Registro da execução

- Responsável: André Simões
- Data: 12/09/2026
- Pull request: _a preencher_
- Commit integrado: _a preencher_
- Observações: _a preencher_
