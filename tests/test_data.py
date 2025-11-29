import pytest
import datetime
from data import Atividade, salvar_config, parse_config, creditar_tudo

# Fixture para limpar as atividades antes de cada teste
@pytest.fixture(autouse=True)
def clear_atividades():
    Atividade.clear()

def test_atividade_creditar_debitar():
    # Cria uma atividade com 10% de prioridade (pts=0.1) e saldo zero
    ativ = Atividade(nome="Estudar", pts=0.1, saldo=0)
    
    # Simula o crédito de horas para uma semana de 40 horas
    ativ.creditarh(toth=40)
    assert ativ.saldo == 4.0  # 10% de 40 horas

    # Debita 1.5 horas
    ativ.debitarh(1.5)
    assert ativ.saldo == 2.5

def test_salvar_e_parse_config(tmp_path, monkeypatch):
    # Usa um diretório temporário para o arquivo de configuração
    temp_config_file = tmp_path / "test_config.cfg"
    monkeypatch.setattr('data.CONFIG', str(temp_config_file))

    # Cria dados de exemplo
    Atividade(nome="Trabalho", pts=0.6, saldo=10)
    Atividade(nome="Academia", pts=0.4, saldo=5)
    toth = 20
    inicio = 1 # Segunda-feira
    timestamp = datetime.date(2024, 1, 1)

    # Salva a configuração
    salvar_config(toth, inicio, timestamp)

    # Limpa as atividades da memória para forçar a leitura do arquivo
    Atividade.clear()
    
    # Lê a configuração
    parsed_toth, parsed_inicio, parsed_timestamp = parse_config()

    # Verifica se os dados foram lidos corretamente
    assert parsed_toth == toth
    assert parsed_inicio == inicio
    assert parsed_timestamp == timestamp

    atividades_lidas = Atividade.all()
    assert len(atividades_lidas) == 2
    
    # Verifica os detalhes de uma das atividades
    trabalho = next(a for a in atividades_lidas if a.nome == "Trabalho")
    assert trabalho.pts == 0.6
    assert trabalho.saldo == 10

def test_creditar_tudo():
    # Testa a função que credita horas para todas as atividades
    Atividade(nome="A1", pts=0.5, saldo=0)
    Atividade(nome="A2", pts=0.5, saldo=2)
    
    # Simula a primeira execução
    creditar_tudo(toth=10, inicio=1, timestamp=0)
    
    atividades = Atividade.all()
    a1 = next(a for a in atividades if a.nome == "A1")
    a2 = next(a for a in atividades if a.nome == "A2")

    assert a1.saldo == 5.0 # 50% de 10
    assert a2.saldo == 7.0 # 2 (saldo inicial) + 5
