## Estrutura

- `d10r.py`: fluxo principal e regras de interação.
- `data.py`: modelo `Atividade` e persistência INI.
- `gui.py`: facade estável usada pelo fluxo principal.
- `gui_pyside.py`: diálogos e widgets PySide6, incluindo os wrappers da facade.
- `utils.py`: cronômetro, formatação e contagem de semanas.
- `tests/`: suíte pytest headless.

## Testes

No Windows, após instalar `requirements-dev.txt`, execute:

    $env:QT_QPA_PLATFORM = "offscreen"
    .venv\Scripts\python -m pytest -q tests
    .venv\Scripts\python -m compileall -q .

O workflow do GitHub Actions executa os mesmos gates em Ubuntu com Python 3.12.

## Estilo de commits

Use commits focados, pequenos e imperativos, com prefixo convencional (`feat:`,
`fix:`, `test:`, `docs:` ou `ci:`). Não misture frentes do contrato no mesmo
commit e não altere `master` ou o upstream durante a implementação.
