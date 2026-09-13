# Análise do Projeto d10r

## Arquitetura atual

- `d10r.py` coordena a configuração inicial, o crédito semanal, a escolha de
  atividades e o registro de tempo.
- `data.py` contém `Atividade`, a facade de persistência e a lógica de crédito
  acumulativo ou não acumulativo.
- `storage.py` contém o schema SQLite v1, os modelos SQLModel, os snapshots
  Pydantic, o repositório transacional e a importação única do INI legado.
- `gui.py` é a facade estável consumida por `d10r.py`.
- `gui_pyside.py` implementa os diálogos PySide6 e os wrappers da facade.
- `utils.py` contém o cronômetro, a formatação e a contagem de semanas.

## Interface

Os diálogos atuais são PySide6 e podem ser executados em modo headless. A
facade preserva as funções `notificar`, `perguntar`, `entrar`, `escolher`,
`menu` e `escolher_arquivo`. O diálogo de prioridades usa os botões
**Subir**/**Descer**; não há dependência de arrastar e soltar.

`escolher_arquivo` continua na facade, mas nenhum fluxo do programa o invoca: o
menu que permitia procurar, selecionar e copiar um arquivo de configuração foi
removido junto com o INI como backend.

## Fluxo da primeira execução

Sem banco e sem INI, o schema v1 é criado vazio e o questionário começa
automaticamente; não há diálogo de procurar ou selecionar arquivo.

1. O usuário cadastra pelo menos duas atividades.
2. Ordena as prioridades com Subir/Descer.
3. Define as horas semanais e escolhe se horas não cumpridas se acumulam.
4. O sistema credita exatamente uma semana e salva a data da execução.

Cancelar o questionário encerra o programa e deixa apenas o banco v1 vazio,
pronto para uma nova tentativa.

## Persistência e crédito

A persistência é exclusivamente SQLite, em `~/.d10r.sqlite3`, com schema
versionado (`schema_version`), configuração singleton (`app_config`) e
atividades (`activity`). Configuração e atividades são substituídas juntas, numa
única transação: uma falha preserva integralmente o snapshot anterior.

O INI `~/.d10r` não é backend, formato de saída nem fallback. Ele é aceito
apenas como entrada de uma importação única, quando o banco ainda não existe, e
é removido pelo caminho exato depois de o banco ser gravado, verificado e
relido. Arquivos legados sem a chave `acumular` importam como `True`.

A ordem de decisão na inicialização é explícita: banco corrompido gera erro sem
consultar nem apagar o INI; banco válido vence e um INI coexistente é removido
sem ser lido; falha antes da promoção preserva o INI; falha ao removê-lo gera
erro e é retentada no próximo início, sem reimportar.

No modo não acumulativo, o atraso é limitado a uma semana e apenas saldos
positivos são zerados antes do crédito; saldos negativos são preservados.

## Histórico

As referências a Python 2.6 e Tkinter descrevem somente a implementação
histórica do projeto original. A implementação atual exige Python 3.12 e usa
PySide6.

## Próximas possibilidades

- Expandir a cobertura de cenários de interação.
- Evoluir o schema além da v1, se necessário, com ferramenta de migração
  dedicada; hoje `create_all()` só roda no bootstrap e não atualiza banco
  existente.
- Limpar temporários órfãos de importação deixados por um término anormal do
  processo, único resíduo conhecido e aceito.
