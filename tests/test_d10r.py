import pytest
from d10r import calcula_prioridades

def test_calcula_prioridades():
    # Lista de atividades ordenadas da mais para a menos prioritária
    atividades_ordenadas = ["Trabalho", "Estudar", "Academia", "Lazer"]
    
    prioridades = calcula_prioridades(atividades_ordenadas)
    
    # A pontuação deve ser:
    # Trabalho (mais prioritário) -> 4 pontos
    # Estudar -> 3 pontos
    # Academia -> 2 pontos
    # Lazer (menos prioritário) -> 1 ponto
    
    assert prioridades["Trabalho"] == 4
    assert prioridades["Estudar"] == 3
    assert prioridades["Academia"] == 2
    assert prioridades["Lazer"] == 1
    assert len(prioridades) == 4
