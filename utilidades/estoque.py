from .banco import conectar_banco

def atualizar_estoque(clinica_id, dados):
    print(f"Iniciando atualização de estoque para clínica {clinica_id}")  # Log
    print(f"Dados recebidos: {dados}")  # Log
    
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Verificar se a clínica existe
        cursor.execute("SELECT id FROM clinicas WHERE id = ?", (clinica_id,))
        if not cursor.fetchone():
            print(f"Erro: Clínica com ID {clinica_id} não encontrada")
            return False

        atualizacoes = 0
        for vacina_id, aplicada in dados.items():
            print(f"Processando vacina {vacina_id}...")  # Log
            
            try:
                cursor.execute("SELECT id FROM vacinas WHERE id = ?", (vacina_id,))
                if not cursor.fetchone():
                    print(f"Erro: Vacina com ID {vacina_id} não encontrada")
                    continue

                cursor.execute("""
                    SELECT quantidade FROM estoque 
                    WHERE clinica_id = ? AND vacina_id = ?
                    """, (clinica_id, vacina_id))
                resultado = cursor.fetchone()
                estoque_atual = resultado[0] if resultado else 0
                
                print(f"Estoque atual para vacina {vacina_id}: {estoque_atual}")  # Log
                
                if aplicada > estoque_atual:
                    print(f"Erro: Quantidade aplicada ({aplicada}) maior que estoque ({estoque_atual}) para vacina {vacina_id}")
                    continue

                nova_quantidade = estoque_atual - aplicada
                if resultado:
                    cursor.execute("""
                        UPDATE estoque 
                        SET quantidade = ? 
                        WHERE clinica_id = ? AND vacina_id = ?
                        """, (nova_quantidade, clinica_id, vacina_id))
                    print(f"Vacina {vacina_id}: Estoque atualizado de {estoque_atual} para {nova_quantidade} (UPDATE)")
                else:
                    cursor.execute("""
                        INSERT INTO estoque (clinica_id, vacina_id, quantidade) 
                        VALUES (?, ?, ?)
                        """, (clinica_id, vacina_id, nova_quantidade))
                    print(f"Vacina {vacina_id}: Estoque criado com {nova_quantidade} (INSERT)")
                
                atualizacoes += 1
                
            except Exception as e:
                print(f"Erro ao processar vacina {vacina_id}: {str(e)}")
                continue

        if atualizacoes > 0:
            conn.commit()
            print(f"Commit realizado: {atualizacoes} vacinas atualizadas")
            return True
        else:
            print("Nenhuma atualização realizada")
            return False

    except Exception as e:
        if conn:
            conn.rollback()
            print(f"Rollback realizado devido a erro geral: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()
            print("Conexão com o banco fechada")

def alterar_estoque(clinica_id, vacina_id, quantidade, operacao="adicionar"):
    conn = conectar_banco()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT quantidade FROM estoque 
            WHERE clinica_id = ? AND vacina_id = ?
        """, (clinica_id, vacina_id))
        resultado = cursor.fetchone()
        
        atual = resultado[0] if resultado else 0
        
        if operacao == "adicionar":
            novo_estoque = atual + quantidade
        elif operacao == "remover":
            if quantidade > atual:
                return False, f"Não é possível remover {quantidade}. Estoque atual: {atual}"
            novo_estoque = atual - quantidade
        else:
            return False, "Operação inválida"
        
        if resultado:
            cursor.execute("""
                UPDATE estoque SET quantidade = ?
                WHERE clinica_id = ? AND vacina_id = ?
            """, (novo_estoque, clinica_id, vacina_id))
        else:
            cursor.execute("""
                INSERT INTO estoque (clinica_id, vacina_id, quantidade)
                VALUES (?, ?, ?)
            """, (clinica_id, vacina_id, novo_estoque))
        
        conn.commit()
        return True, f"Estoque atualizado para {novo_estoque} unidades"
    
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao alterar estoque: {e}"
    
    finally:
        conn.close()
