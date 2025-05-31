import sqlite3
from sqlite3 import Error
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def conectar_banco():
    try:
        conn = sqlite3.connect("vacinas.db")
        conn.execute("PRAGMA foreign_keys = ON")
        logging.info("Conexão com o banco de dados estabelecida com sucesso")
        return conn
    except Error as e:
        logging.error(f"Erro ao conectar ao banco: {e}")
        print(f"Erro ao conectar ao banco: {e}")
        raise

def verificar_estrutura_banco():
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        logging.info("Verificando estrutura do banco de dados")
        
        # Verificar tabelas essenciais
        for tabela in ['vacinas', 'clinicas', 'estoque', 'lotes']:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabela}'")
            if not cursor.fetchone():
                logging.warning(f"Tabela '{tabela}' não encontrada")
                if tabela == 'vacinas':
                    cursor.execute("""
                        CREATE TABLE vacinas (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nome TEXT NOT NULL
                        )
                    """)
                    logging.info("Tabela 'vacinas' criada com sucesso")
                elif tabela == 'clinicas':
                    cursor.execute("""
                        CREATE TABLE clinicas (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nome TEXT NOT NULL UNIQUE
                        )
                    """)
                    logging.info("Tabela 'clinicas' criada com sucesso")
                elif tabela == 'estoque':
                    cursor.execute("""
                        CREATE TABLE estoque (
                            clinica_id INTEGER NOT NULL,
                            vacina_id INTEGER NOT NULL,
                            quantidade INTEGER DEFAULT 0,
                            PRIMARY KEY (clinica_id, vacina_id),
                            FOREIGN KEY (clinica_id) REFERENCES clinicas(id) ON DELETE CASCADE,
                            FOREIGN KEY (vacina_id) REFERENCES vacinas(id) ON DELETE CASCADE
                        )
                    """)
                    logging.info("Tabela 'estoque' criada com sucesso")
                elif tabela == 'lotes':
                    cursor.execute("""
                        CREATE TABLE lotes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            vacina_id INTEGER NOT NULL,
                            numero TEXT NOT NULL,
                            validade DATE NOT NULL,
                            FOREIGN KEY (vacina_id) REFERENCES vacinas(id) ON DELETE CASCADE
                        )
                    """)
                    conn.commit()
                    logging.info("Tabela 'lotes' criada com sucesso")
                    print("Tabela 'lotes' criada com sucesso!")
                else:
                    logging.error(f"Tabela essencial '{tabela}' não existe")
                    raise Exception(f"Tabela '{tabela}' não existe no banco de dados")
        
        # Verificar se a tabela estoque tem ON DELETE CASCADE
        cursor.execute("PRAGMA foreign_key_list(estoque)")
        foreign_keys = cursor.fetchall()
        has_cascade = any(fk for fk in foreign_keys if fk[2] == 'vacina_id' and fk[5] == 'CASCADE')
        
        if not has_cascade:
            logging.info("Atualizando esquema do banco para incluir ON DELETE CASCADE")
            print("Atualizando esquema do banco para incluir ON DELETE CASCADE...")
            cursor.execute("ALTER TABLE estoque RENAME TO estoque_antigo")
            
            cursor.execute("""
                CREATE TABLE estoque (
                    clinica_id INTEGER NOT NULL,
                    vacina_id INTEGER NOT NULL,
                    quantidade INTEGER DEFAULT 0,
                    PRIMARY KEY (clinica_id, vacina_id),
                    FOREIGN KEY (clinica_id) REFERENCES clinicas(id) ON DELETE CASCADE,
                    FOREIGN KEY (vacina_id) REFERENCES vacinas(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                INSERT INTO estoque (clinica_id, vacina_id, quantidade)
                SELECT clinica_id, vacina_id, quantidade
                FROM estoque_antigo
            """)
            
            cursor.execute("DROP TABLE estoque_antigo")
            conn.commit()
            logging.info("Esquema do banco atualizado com sucesso")
            print("Esquema atualizado com sucesso!")
        
        conn.close()
        logging.info("Verificação da estrutura do banco concluída com sucesso")
        return True
    except Exception as e:
        logging.error(f"Problema na estrutura do banco: {e}")
        print(f"Problema na estrutura do banco: {e}")
        return False