# Testes PySide6

## Suíte automatizada

Os testes de GUI rodam sem servidor gráfico:

    $env:QT_QPA_PLATFORM = "offscreen"
    .venv\Scripts\python -m pytest -q tests

O CI instala as bibliotecas Qt do Ubuntu, executa a suíte completa e verifica
`python -m compileall -q .`.

## Cobertura dos diálogos

- Cronômetro: finalização, pausa, limite de saldo e encerramento por X/Esc;
- entrada de horas: valores e cancelamento;
- prioridades: reordenação por Subir/Descer e cancelamento;
- escolha: primeira opção pré-selecionada e cancelamento;
- botões: retorno do botão e bloqueio de Esc/X sem escolha;
- texto e inteiro: retorno, limite de inteiro e cancelamento;
- arquivo e mensagem: retorno/cancelamento e delegação aos widgets PySide6.

Para uma verificação manual, execute o fluxo principal com `python d10r.py` em
um ambiente com display e confirme os botões, mensagens e escolhas acima.
