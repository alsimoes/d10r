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


@pytest.mark.parametrize('timestamp, hoje, esperado', [
    # último crédito numa segunda, 14 dias depois: 2 semanas (antes creditava 1)
    (datetime.date(2024, 1, 1), datetime.date(2024, 1, 15), 2),
    # último crédito numa segunda, 7 dias depois: 1 semana (antes creditava 0)
    (datetime.date(2024, 1, 1), datetime.date(2024, 1, 8), 1),
    # último crédito num sábado, segunda seguinte: 1 semana (antes creditava 0)
    (datetime.date(2024, 1, 6), datetime.date(2024, 1, 8), 1),
    # mesma semana, antes da próxima segunda: nada a creditar
    (datetime.date(2024, 1, 2), datetime.date(2024, 1, 7), 0),
])
def test_creditar_tudo_semanas(timestamp, hoje, esperado):
    Atividade(nome='A1', pts=0.5, saldo=0)
    creditou = creditar_tudo(toth=10, inicio=1, timestamp=timestamp, hoje=hoje)
    assert creditou is bool(esperado)
    assert Atividade.all()[0].saldo == 5.0 * esperado


def test_creditar_tudo_confere_com_contagem_ingenua():
    # Conta as ocorrências do dia de início em (timestamp, hoje]
    base = datetime.date(2026, 1, 5)
    for inicio in range(1, 8):
        for desloc in range(7):
            timestamp = base + datetime.timedelta(desloc)
            for dias in range(1, 30):
                hoje = timestamp + datetime.timedelta(dias)
                esperado = sum(
                    1 for k in range(1, dias + 1)
                    if (timestamp + datetime.timedelta(k)).isoweekday() == inicio)
                Atividade.clear()
                Atividade(nome='A1', pts=1.0, saldo=0)
                creditar_tudo(toth=1, inicio=inicio, timestamp=timestamp, hoje=hoje)
                assert Atividade.all()[0].saldo == esperado, (inicio, timestamp, hoje)
