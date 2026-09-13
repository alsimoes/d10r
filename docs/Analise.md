# Análise do Projeto d10r

## Arquitetura atual

- `d10r.py` coordena a configuração inicial, o crédito semanal, a escolha de
  atividades e o registro de tempo.
- `data.py` contém `Atividade`, a persistência INI e a lógica de crédito
  acumulativo ou não acumulativo.
- `gui.py` é a facade estável consumida por `d10r.py`.
- `gui_pyside.py` implementa os diálogos PySide6 e os wrappers da facade.
- `utils.py` contém o cronômetro, a formatação e a contagem de semanas.

## Interface

Os diálogos atuais são PySide6 e podem ser executados em modo headless. A
facade preserva as funções `notificar`, `perguntar`, `entrar`, `escolher`,
`menu` e `escolher_arquivo`. O diálogo de prioridades usa os botões
**Subir**/**Descer**; não há dependência de arrastar e soltar.

## Fluxo da primeira execução

1. O usuário cadastra pelo menos duas atividades.
2. Ordena as prioridades com Subir/Descer.
3. Define as horas semanais e escolhe se horas não cumpridas se acumulam.
4. O sistema credita exatamente uma semana e salva a data da execução.

## Persistência e crédito

O arquivo INI em `~/.d10r` guarda atividades, prioridades, saldos, dia de
início, último crédito e a opção `acumular`. Arquivos legados sem essa chave
usam `True`. No modo não acumulativo, o atraso é limitado a uma semana e apenas
saldos positivos são zerados antes do crédito; saldos negativos são preservados.

## Histórico

As referências a Python 2.6 e Tkinter descrevem somente a implementação
histórica do projeto original. A implementação atual exige Python 3.12 e usa
PySide6.

## Próximas possibilidades

- Melhorar o isolamento do caminho de configuração.
- Expandir a cobertura de cenários de interação.
- Avaliar SQLite quando a issue #4 for priorizada; a persistência atual continua
  sendo INI.
