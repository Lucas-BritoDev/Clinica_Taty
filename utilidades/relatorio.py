import os
import pandas as pd
from datetime import datetime
from .banco import conectar_banco

def criar_dataframe_vacinas(clinica_id):
    conn = conectar_banco()
    df = pd.read_sql_query(f"""
        SELECT 
            v.id, 
            v.nome, 
            COALESCE(e.quantidade, 0) as quantidade
        FROM vacinas v
        LEFT JOIN estoque e ON v.id = e.vacina_id AND e.clinica_id = {clinica_id}
        ORDER BY v.nome ASC
    """, conn)
    conn.close()
    return df

def gerar_relatorio_texto(df, clinica_nome, data_relatorio):
    # Filtrar apenas vacinas que foram aplicadas (quantidade > 0)
    df_aplicadas = df[df["Quantidade Aplicada"] > 0].copy()
    
    if df_aplicadas.empty:
        return f"""
📊 Relatório de Vacinas Aplicadas 📊

------------------------------------------------------

🏥 Clínica: {clinica_nome}
📅 Data: {data_relatorio.strftime('%d/%m/%Y')}

------------------------------------------------------

⚠️ Nenhuma vacina foi aplicada nesta data.
"""
    
    # Criar o texto do relatório com emojis e separadores
    texto = f"""
📊 Relatório de Vacinas Aplicadas 📊

------------------------------------------------------

🏥 Clínica: {clinica_nome}
📅 Data: {data_relatorio.strftime('%d/%m/%Y')}

------------------------------------------------------

💉 Vacinas Aplicadas:
"""
    
    # Adicionar cada vacina aplicada com o lote
    for _, row in df_aplicadas.iterrows():
        texto += f"💉 {row['Vacina']} (Lote: {row['Lote']}): {row['Quantidade Aplicada']} doses \n"
    
    return texto

def gerar_alerta_estoque(clinica_nome, estoque_baixo, estoque_zerado):
    # Conectar ao banco para buscar os lotes
    conn = conectar_banco()
    
    # Função auxiliar para buscar lotes de uma vacina
    def buscar_lotes(vacina_nome):
        # Extrair o nome da vacina sem a quantidade (caso estoque_baixo inclua a quantidade)
        nome_vacina = vacina_nome.split(" (")[0]
        df_lotes = pd.read_sql_query("""
            SELECT l.numero, l.validade
            FROM lotes l
            JOIN vacinas v ON l.vacina_id = v.id
            WHERE v.nome = ?
            ORDER BY l.validade ASC
        """, conn, params=(nome_vacina,))
        if df_lotes.empty:
            return "Nenhum lote cadastrado 📦"
        return ", ".join([f"{row['numero']} (Validade: {row['validade']})" for _, row in df_lotes.iterrows()])
    
    texto = f"""
🚨 Alerta de Estoque de Vacinas 🚨

------------------------------------------------------

🏥 Clínica: {clinica_nome}
📅 Data: {datetime.now().strftime('%d/%m/%Y')}

------------------------------------------------------

"""
    
    if estoque_zerado:
        texto += "🔴 Estoque Esgotado 🔴\n"
        for vacina in estoque_zerado:
            lotes = buscar_lotes(vacina)
            texto += f"💉 {vacina}: {lotes}\n"
    
    if estoque_baixo:
        if estoque_zerado:
            texto += "\n"
        texto += "🟠 Estoque Baixo 🟠\n"
        for vacina in estoque_baixo:
            lotes = buscar_lotes(vacina)
            texto += f"💉 {vacina}: {lotes}\n"
    
    if not estoque_zerado and not estoque_baixo:
        texto += "✅ Nenhum problema de estoque no momento.\n"
    
    conn.close()
    return texto

def salvar_relatorio(df, clinica_nome, data_relatorio):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    diretorio = os.path.join(BASE_DIR, "utilidades", "relatorios")
    if not os.path.exists(diretorio):
        os.makedirs(diretorio)
    
    data_str = data_relatorio.strftime('%Y-%m-%d')
    timestamp = datetime.now().strftime('%H-%M-%S')
    nome_arquivo = f"Relatorio_{clinica_nome.replace(' ', '_')}_{data_str}_{timestamp}.xlsx"
    caminho = os.path.join(diretorio, nome_arquivo)
    
    df.to_excel(caminho, index=False)
    return caminho

def salvar_alerta(clinica_nome, data_relatorio, estoque_baixo, estoque_zerado):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    diretorio = os.path.join(BASE_DIR, "utilidades", "alertas")
    if not os.path.exists(diretorio):
        os.makedirs(diretorio)
    
    data_str = data_relatorio.strftime('%Y-%m-%d')
    timestamp = datetime.now().strftime('%H-%M-%S')
    nome_arquivo = f"ALERTA_{clinica_nome.replace(' ', '_')}_{data_str}_{timestamp}.xlsx"
    caminho = os.path.join(diretorio, nome_arquivo)
    
    dados = []
    for vacina in estoque_zerado:
        dados.append({"Vacina": vacina, "Status": "Esgotado"})
    for vacina in estoque_baixo:
        dados.append({"Vacina": vacina, "Status": "Estoque Baixo"})
    
    df = pd.DataFrame(dados)
    if not df.empty:
        df.to_excel(caminho, index=False)
    return caminho