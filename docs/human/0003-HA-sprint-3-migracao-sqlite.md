# HA-0003 — Migração para SQLite do Sprint 3

Este runbook descreve, em ordem, as ações humanas ou delegadas ao Sol Senior para integrar
a migração da persistência para SQLite (`~/.d10r.sqlite3`) e o corte definitivo do INI no
fork `alsimoes/d10r`, além do procedimento manual de primeira execução com backup.

## Aviso crítico de remoção automática

A partir desta versão, o INI legado (`~/.d10r`) é apenas uma **entrada transitória de
parâmetros**: na primeira execução, ele é importado uma única vez e **removido
automaticamente** assim que o banco SQLite íntegro é promovido. Não há fallback: se o INI
sumir sem backup e o banco for perdido, a configuração não pode ser recuperada do INI.

**Faça backup manual do `~/.d10r` antes da primeira execução da versão nova.**

## Pré-condições

- O contrato está em `sprint-3-sqlite` nos artefatos do épico (brief, tech plan e tickets
  01–07), com a revisão da matriz (Terra, ticket 01) e os pareceres dos tickets 02–06
  aprovados.
- A branch de entrega é `feat/sprint-3-sqlite`, criada a partir de `dda34cf`.
- `origin` deve ser `https://github.com/alsimoes/d10r.git`.
- `upstream` (`https://github.com/ygormutti/d10r.git`) é somente leitura.
- A issue #4 registra esta migração e só pode ser fechada após o merge e a comprovação.
- Luna e Terra fazem somente commits locais; push, PR, merge e fechamento de issues são
  responsabilidade do Sol Senior ou do responsável humano.
- O único ambiente suportado e validado é Windows 11 (`windows-latest`).

## Passo a passo (integração — delegada ao Sol Senior)

1. Confirmar o estado local antes de qualquer operação remota:
   - `git branch --show-current` deve retornar `feat/sprint-3-sqlite`.
   - `git status --short` deve estar limpo.
   - `git remote get-url origin` deve retornar o fork `alsimoes/d10r`.
   - `git log --oneline --decorate -n 12` deve conter os commits do Sprint 3
     (`efb123a`..`cf98c81`, mais o runbook).
   - Parar se houver arquivo inesperado, conflito, rebase, merge ou destino divergente.

2. Executar os gates locais finais:
   - `$env:QT_QPA_PLATFORM = "offscreen"`
   - `.venv\Scripts\python -m pytest -q tests`
   - `.venv\Scripts\python -m compileall -q .`
   - `git diff --check 90c0efe..HEAD -- . ":(exclude)docs/d10r-correcoes.patch"`
   - Resultado esperado: 266 testes ou mais, zero falhas e nenhum erro estático.

3. Confirmar os invariantes de escopo:
   - `data.DATABASE` aponta para `~/.d10r.sqlite3`; `data.CONFIG` não existe.
   - `d10r.menu_cfg` e `import shutil` não existem; nenhum caminho de runtime lê, grava,
     seleciona ou copia INI.
   - `storage.py` implementa schema v1, repositório transacional e importação única.
   - O workflow usa `windows-latest`, `fetch-depth: 0` e diff-check contra
     `origin/master...HEAD` excluindo `docs/d10r-correcoes.patch`.
   - `gui.escolher_arquivo` permanece sem chamador (limpeza futura documentada).

4. Incluir este runbook na branch de entrega:
   - `git add docs/human/0003-HA-sprint-3-migracao-sqlite.md`
   - `git commit -m "docs(human): add Sprint 3 SQLite migration runbook"`
   - Não criar commit duplicado se o arquivo já estiver rastreado no head aprovado.

5. Publicar somente a branch do fork, sem reescrever histórico:
   - Repetir `git remote get-url origin` e `git branch --show-current`.
   - `git push origin feat/sprint-3-sqlite`
   - Nunca usar `--force` e nunca executar `git push upstream`.

6. Validar o CI Windows do head publicado (primeira execução remota deste runner):
   - Confirmar que o workflow foi disparado pelo push e que o SHA corresponde ao head.
   - Aguardar instalação, pytest, compileall e diff-check terminarem verdes.
   - Atenção aos dois passos de maior risco: o diff-check (depende de `origin/master` no
     checkout e de `shell: bash` no runner Windows) e o teste de banco bloqueado, que
     executa pela primeira vez em CI.
   - Se falhar, registrar job, etapa, log e SHA; não fazer merge nem trocar runner sem
     arbitragem. Correções voltam à Luna como fixup delimitado.

7. Abrir ou atualizar o pull request no próprio fork:
   - Origem: `alsimoes:feat/sprint-3-sqlite`; destino: `alsimoes:master`.
   - Título sugerido: `Sprint 3: migração para SQLite com corte definitivo do INI`.
   - O corpo deve listar schema v1 SQLModel/Pydantic, repositório transacional, importação
     única com remoção automática, facade runtime, CI Windows, documentação, contagem de
     testes e os pareceres da Terra e do Sol.
   - Incluir `Closes #4` para fechar a issue da migração somente após o merge.

8. Conferir o PR antes do merge:
   - Estado mergeável e base/head corretos.
   - Diff limitado ao contrato e sem arquivo inesperado.
   - Checks do GitHub Actions verdes no SHA atual (push e pull_request).
   - Revisão técnica final sem achado bloqueador ou alto.
   - Não fazer merge enquanto houver divergência ou check pendente.

9. Integrar conforme a política vigente do repositório:
   - Executar o merge sem force push nem alteração do upstream.
   - Registrar número do PR, horário e hash integrado.
   - Confirmar que `origin/master` contém o commit resultante.

10. Tratar as issues após confirmar o merge e o CI pós-merge verde:
    - Verificar que a issue #4 foi fechada automaticamente por `Closes #4`.
    - Se não foi, comentar com o PR, o hash integrado e a evidência da migração e
      fechá-la manualmente.

11. Registrar a execução:
    - Preencher todos os campos de “Registro da execução” abaixo.
    - Publicar o registro em commit documental separado no `master`, após atualizar a
      cópia local por fast-forward.
    - Executar `git diff --check` e confirmar o status limpo depois do registro.

12. Não limpar branches, bancos ou backups neste runbook:
    - Preservar `feat/sprint-3-sqlite` até confirmação explícita de que não haverá
      rollback.
    - Preservar o backup manual do INI e o banco `~/.d10r.sqlite3`.
    - A única remoção autorizada pelo contrato é a do INI de entrada exato, feita pelo
      próprio aplicativo após a importação validada. Qualquer outra remoção exige
      autorização humana separada.

## Primeira execução da versão nova (ação humana)

1. **Backup manual obrigatório antes da primeira execução:**
   - `Copy-Item ~\.d10r ~\.d10r.backup-pre-sqlite` (ou equivalente).
2. Executar o aplicativo normalmente na máquina de uso real (Windows 11).
3. O comportamento esperado na primeira execução:
   - O INI é importado uma única vez; o banco `~/.d10r.sqlite3` é criado e promovido; o
     `~/.d10r` é removido automaticamente.
   - Atividades, saldos, créditos e a opção de acumular devem aparecer exatamente como
     antes.
4. Verificação pós-execução:
   - `Test-Path ~\.d10r` deve retornar `False`.
   - `Test-Path ~\.d10r.sqlite3` deve retornar `True`.
   - Executar o aplicativo de novo: deve abrir direto com os dados, sem questionário de
     primeira configuração.
5. Roteiro manual completo de persistência (5 casos) em `docs/Testes_PySide6.md`.

## Rollback (se a migração apresentar problema na máquina real)

1. Fechar o aplicativo.
2. Remover o banco: `Remove-Item ~\.d10r.sqlite3` (e, se existir, algum temporário
   remanescente `~\.d10r-import-*.sqlite3` de uma tentativa interrompida — remover
   **somente** os seus, pelo caminho exato).
3. Restaurar o INI: `Copy-Item ~\.d10r.backup-pre-sqlite ~\.d10r`.
4. Voltar para a versão anterior do aplicativo (o INI volta a ser o formato operacional).
5. Reportar a ocorrência para avaliação antes de nova tentativa.

## Riscos residuais aceitos (conhecidos e cobertos por teste)

- Temporário órfão `~/.d10r-import-*.sqlite3` após término anormal (SIGKILL/energia) no
  meio da importação: o aplicativo nunca o reutiliza nem o apaga; remoção manual pelo
  caminho exato, se confirmado que é órfão.
- Coexistência persistente se a remoção do INI falhar de forma permanente (arquivo
  travado por outro processo): o aplicativo não inicia até a remoção passar; destravar o
  arquivo e reiniciar resolve.
- Sem concorrência multi-instância e sem WAL: fora do escopo do schema v1.

## Restrições

- Escrever somente em `alsimoes/d10r`; `ygormutti/d10r` permanece estritamente somente
  leitura.
- Não usar force push, rebase destrutivo ou remoção automática de branches/tags.
- Não avaliar Linux ou macOS (fora do aceite do sprint).
- Não fechar a issue #4 antes de o PR estar integrado com CI pós-merge verde.
- Diante de qualquer divergência entre SHA local, SHA do CI e SHA do PR, parar e
  registrar.

## Validação esperada

- Suíte Python 3.12 headless integralmente verde no Windows local e no GitHub Actions
  `windows-latest`.
- `compileall` e diff-check emendado verdes.
- PR integrado em `alsimoes/master` com a issue #4 fechada.
- Primeira execução real: INI importado e removido, banco criado, dados preservidos.
- Worktree final limpa e branches/bancos/backups preservados.

## Registro da execução

- Responsável: André Simões (integração delegada ao agente Sol Senior; primeira execução
  manual é ação humana)
- Data: ____
- Pull request: ____
- Head validado: ____
- Commit integrado: ____
- CI (push, PR, pós-merge, registro): ____
- Issue #4: ____
- Primeira execução real (humano): backup feito em ____, INI removido em ____,
  verificação pós-execução: ____
- Ocorrências e rollback: ____
