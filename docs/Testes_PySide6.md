# Testes PySide6

## Suíte automatizada

Os testes de GUI rodam sem servidor gráfico:

    $env:QT_QPA_PLATFORM = "offscreen"
    .venv\Scripts\python -m pytest -q tests

O CI roda em `windows-latest` — o único ambiente suportado deste sprint — e
repete os mesmos quatro passos: instalação declarada, suíte completa,
`python -m compileall -q .` e `git diff --check`.

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

## Verificação manual da persistência

Os testes automatizados cobrem estes casos com caminhos temporários; para
conferir à mão, **faça backup de `~/.d10r` e `~/.d10r.sqlite3` antes**, porque a
importação remove o INI.

1. Sem `~/.d10r` e sem `~/.d10r.sqlite3`: o questionário inicial deve começar
   direto, sem oferecer procura ou seleção de arquivo, e deve restar apenas o
   banco.
2. Com um `~/.d10r` válido e sem banco: os saldos, prioridades, dia de início e
   o modo acumulativo devem aparecer iguais, e o `~/.d10r` deve ter desaparecido
   ao final.
3. Repetindo a execução: nada é reimportado e o `~/.d10r` não reaparece.
4. Com um `~/.d10r.sqlite3` corrompido (por exemplo, truncado): o programa deve
   avisar e encerrar sem apagar nem ler qualquer `~/.d10r` presente.
5. Cancelando o questionário inicial: deve restar apenas o banco vazio, e a
   execução seguinte deve oferecer o questionário novamente.
