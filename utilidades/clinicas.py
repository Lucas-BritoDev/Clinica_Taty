import pandas as pd
from .banco import conectar_banco

def carregar_clinicas():
    try:
        conn = conectar_banco()
        query = "SELECT id, nome FROM clinicas ORDER BY nome ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Erro ao carregar clínicas: {e}")
        return pd.DataFrame(columns=['id', 'nome'])