## Estrutura

- `d10r.py`: fluxo principal e regras de interação.
- `data.py`: modelo `Atividade`, facade de persistência e regras de crédito.
- `storage.py`: schema SQLite v1, modelos SQLModel, snapshots Pydantic,
  repositório transacional e importação única do INI legado.
- `gui.py`: facade estável usada pelo fluxo principal.
- `gui_pyside.py`: diálogos e widgets PySide6, incluindo os wrappers da facade.
- `utils.py`: cronômetro, formatação e contagem de semanas.
- `tests/`: suíte pytest headless.

A persistência é exclusivamente SQLite, em `~/.d10r.sqlite3`. O INI `~/.d10r` é
apenas entrada de uma importação única e é removido depois dela: não é backend,
formato de saída nem fallback. Ao mexer em persistência, mantenha as aridades
públicas de `parse_config`, `salvar_config` e `creditar_tudo`, e injete os
caminhos nos testes — nenhum teste pode escrever no perfil real.

## Testes

No Windows, após instalar `requirements-dev.txt`, execute:

    $env:QT_QPA_PLATFORM = "offscreen"
    .venv\Scripts\python -m pytest -q tests
    .venv\Scripts\python -m compileall -q .

O workflow do GitHub Actions executa os mesmos gates em `windows-latest` com
Python 3.12, mais `git diff --check`. Windows é o único ambiente suportado e
validado; Linux e macOS não participam do aceite.

## Estilo de commits

Use commits focados, pequenos e imperativos, com prefixo convencional (`feat:`,
`fix:`, `test:`, `docs:` ou `ci:`). Não misture frentes do contrato no mesmo
commit e não altere `master` ou o upstream durante a implementação.
