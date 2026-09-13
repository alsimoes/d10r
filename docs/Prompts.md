Quero que você implemente os itens:
1. Migrar para Python 3 (urgente)
2. Modernizar GUI (PySide6)
3. Adicionar testes (pytest)
4. Banco de dados (SQLite ao invés de INI)

## Persistência

O item 4 está implementado: a persistência é exclusivamente SQLite, em
`~/.d10r.sqlite3`, com SQLModel e validação Pydantic, conforme a
[issue #4](https://github.com/alsimoes/d10r/issues/4).

O INI `~/.d10r` deixou de ser persistência: é aceito apenas como entrada de uma
importação única, quando o banco ainda não existe, e é removido depois de o
banco ser verificado. Não é backend, formato de saída nem fallback, e não há
importação manual ou repetida.

Observações:
- coloque qualquer documentos que julgue necessário na pasta 'docs\';
- se precisar criar peguenos scripts de teste qua não farão parte do projeto mas sirvam para você validar conceito, use a pasta 'validations\';
