# Roteiro de Testes Manuais PySide6

## Objetivo
Validar visualmente e funcionalmente todos os componentes e diálogos migrados para PySide6.

## Passos

1. **Janela Principal**
   - Executar `python gui_pyside.py`.
   - Verificar se a janela principal abre corretamente, com label, entrada, spinbox e botão.

2. **Diálogo de Cronômetro**
   - Descomentar o bloco de teste do `CronometroDialogQt`.
   - Executar e validar exibição dos labels e botões.

3. **Diálogo de Hora**
   - Descomentar o bloco de teste do `HoraSpinDialogQt`.
   - Executar, preencher valores e validar retorno.

4. **Diálogo de Prioridade**
   - Descomentar o bloco de teste do `PrioridadeDialogQt`.
   - Reordenar itens, clicar OK e validar retorno.

5. **Caixa de Escolha**
   - Descomentar o bloco de teste do `ChoiceBoxQt`.
   - Selecionar opção e validar retorno.

6. **Entrada de Texto**
   - Descomentar o bloco de teste do `TextEntryBoxQt`.
   - Digitar texto e validar retorno.

7. **Seleção de Arquivo**
   - Descomentar o bloco de teste do `file_open_dialog`.
   - Selecionar arquivo e validar retorno.

8. **Mensagem**
   - Descomentar o bloco de teste do `show_message`.
   - Validar exibição da mensagem.

## Observações
- Se algum componente não funcionar, registrar o erro para correção.
- Após validação manual, seguir para testes automatizados.
