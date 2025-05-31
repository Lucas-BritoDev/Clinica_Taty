import streamlit as st
import pandas as pd
import os
import re
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

from utilidades.banco import conectar_banco, verificar_estrutura_banco
from utilidades.clinicas import carregar_clinicas
from utilidades.relatorio import criar_dataframe_vacinas, gerar_relatorio_texto, gerar_alerta_estoque, salvar_relatorio, salvar_alerta
from utilidades.email import enviar_email, verificar_credenciais_email, get_smtp_settings
from utilidades.estoque import atualizar_estoque, alterar_estoque

# Configuração inicial
load_dotenv()
st.set_page_config(page_title="Relatório de Vacinas", layout="centered")

# Verificar estrutura do banco na inicialização
if not verificar_estrutura_banco():
    st.error("Erro crítico: Não foi possível verificar a estrutura do banco de dados. Verifique os logs.")
    st.stop()

# Inicialização do session_state
def inicializar_session_state():
    if 'email_provider' not in st.session_state:
        st.session_state.email_provider = os.getenv("EMAIL_PROVIDER", "gmail")
    if 'dados' not in st.session_state:
        st.session_state.dados = {}
    if 'lotes' not in st.session_state:
        st.session_state.lotes = {}
    if 'df_relatorio' not in st.session_state:
        st.session_state.df_relatorio = pd.DataFrame()
    if 'clinica_id' not in st.session_state:
        st.session_state.clinica_id = None
    if 'clinica_nome' not in st.session_state:
        st.session_state.clinica_nome = ""
    if 'data_relatorio' not in st.session_state:
        st.session_state.data_relatorio = None
    if 'estoque_baixo' not in st.session_state:
        st.session_state.estoque_baixo = []
    if 'estoque_zerado' not in st.session_state:
        st.session_state.estoque_zerado = []
    if 'email_remetente' not in st.session_state:
        st.session_state.email_remetente = os.getenv("EMAIL_REMETENTE", "")
    if 'email_senha' not in st.session_state:
        st.session_state.email_senha = os.getenv("EMAIL_SENHA", "")
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = "🏠 Introdução"

# Função para validar e-mails
def validar_emails(emails):
    if not emails or not isinstance(emails, str):
        return False, "Nenhum e-mail fornecido"
    
    padrao = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    emails_lista = [e.strip() for e in emails.split(",") if e.strip()]
    
    if not emails_lista:
        return False, "Nenhum e-mail válido fornecido"
    
    invalidos = [e for e in emails_lista if not re.match(padrao, e)]
    if invalidos:
        return False, f"E-mails inválidos: {', '.join(invalidos)}"
    
    return True, emails_lista

# CSS customizado
st.markdown("""
    <style>
    :root {
        --text-color: var(--text-color, #000000);
        --background-color: var(--background-color, #ffffff);
        --card-background: var(--background-color, #ffffff);
        --border-color: #e0e0e0;
        --shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        --danger-color: #dc3545;
        --warning-color: #ffca2c;
        --success-color: #28a745;
        --text-muted: #666;
    }

    [data-theme="dark"] {
        --text-color: #ffffff;
        --background-color: #1a1c23;
        --card-background: #2c2f36;
        --border-color: #444;
        --shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
        --danger-color: #ff6666;
        --warning-color: #ffca2c;
        --success-color: #28a745;
        --text-muted: #aaaaaa;
    }

    .main { padding: 2rem; }
    h1, h2, h3, h4, h5, h6 { color: var(--text-color); }
    .stButton>button {
        background-color: #6C6CF4;
        color: white;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #4f4fc4;
        transition: 0.3s;
    }
    .stock-info {
        font-size: 0.9em;
        color: var(--text-muted);
        margin-left: 5px;
    }
    .section {
        margin-bottom: 2rem;
    }
    .email-list {
        max-height: 150px;
        overflow-y: auto;
        border: 1px solid var(--border-color);
        padding: 10px;
        border-radius: 5px;
        margin-top: 5px;
        background-color: var(--card-background);
    }
    .estoque-baixo {
        color: var(--warning-color);
        font-weight: bold;
    }
    .estoque-zerado {
        color: var(--danger-color);
        font-weight: bold;
    }
    .alert-icon {
        margin-right: 5px;
        vertical-align: middle;
    }
    .stock-section {
        margin-bottom: 2rem;
    }
    .stock-section h3 {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 1rem;
    }
    .stock-cards {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1rem;
    }
    .stock-card {
        background-color: var(--card-background);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
        box-shadow: var(--shadow);
        transition: transform 0.2s;
    }
    .stock-card:hover {
        transform: translateY(-2px);
    }
    .stock-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 0.5rem;
    }
    .stock-card-header h4 {
        margin: 0;
        font-size: 1.1rem;
        color: var(--text-color);
    }
    .stock-card-body {
        color: var(--text-muted);
        font-size: 0.9rem;
    }
    .stock-card-body p {
        margin: 0.3rem 0;
    }
    .stock-card-body .lotes {
        font-style: italic;
    }
    .historico-item {
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        background-color: var(--card-background);
    }
    .date-filter {
        margin-bottom: 20px;
        padding: 10px;
        background-color: var(--card-background);
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .date-filter .stDateInput {
        flex: 1;
    }
    .date-filter-button-container {
        display: flex;
        justify-content: center;
        margin-top: 10px;
    }
    .date-filter-button-container .stButton>button {
        width: 200px;
    }
    .config-form {
        background-color: var(--card-background);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid var(--border-color);
    }
    .remove-warning {
        color: var(--danger-color);
        background-color: rgba(220, 53, 69, 0.1);
        border: 1px solid var(--danger-color);
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 15px;
    }
    .lote-input {
        display: flex;
        gap: 10px;
        align-items: flex-end;
        margin-bottom: 5px;
    }
    .lote-container {
        border: 1px solid var(--border-color);
        border-radius: 5px;
        padding: 8px;
        margin-top: 5px;
        background-color: var(--card-background);
    }
    /* New styles for the Introdução page */
    .header-banner {
        background: linear-gradient(90deg, #6C6CF4 0%, #4f4fc4 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-card {
        background-color: var(--card-background);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
        box-shadow: var(--shadow);
        text-align: center;
        transition: transform 0.2s;
        min-height: 150px; /* Ensure cards have enough height */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .feature-card:hover {
        transform: translateY(-5px);
    }
    .feature-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    .highlight-text {
        color: #6C6CF4;
        font-weight: bold;
    }
    .footer-note {
        text-align: center;
        color: var(--text-muted);
        margin-top: 3rem;
        font-size: 0.9rem;
    }
    /* Ensure text in feature-card fits */
    .feature-card h4 {
        font-size: 1rem;
        word-wrap: break-word;
        white-space: normal;
        margin-bottom: 0.5rem;
    }
    .feature-card p {
        font-size: 0.9rem;
        word-wrap: break-word;
        white-space: normal;
    }
    </style>
""", unsafe_allow_html=True)

def mostrar_pagina_introducao():
    # Header with gradient banner
    st.markdown("""
        <div class="header-banner">
            <h1>📊 Relatório Diário de Vacinas</h1>
            <p>Gerencie suas vacinas com eficiência e precisão</p>
        </div>
    """, unsafe_allow_html=True)

    # Main content with improved layout
    st.markdown("<h3 style='text-align: center;'><span class='highlight-text'>Bem-vindo(a) ao Sistema</span></h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("""
            <div class='section'>
                <h4>💉 Sistema de Gestão de Vacinas</h4>
                <p>Este sistema facilita o registro e envio de relatórios de vacinas aplicadas por clínicas, garantindo organização e controle.</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class='section'>
                <h4>🎯 Benefícios</h4>
                <ul>
                    <li><span class='highlight-text'>Controle preciso</span> do estoque</li>
                    <li><span class='highlight-text'>Relatórios</span> automatizados</li>
                    <li><span class='highlight-text'>Comunicação</span> eficiente</li>
                    <li><span class='highlight-text'>Alertas</span> de estoque baixo</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Feature cards
    st.markdown("### <span class='highlight-text'>Funcionalidades Principais</span>", unsafe_allow_html=True)
    cols = st.columns(4, gap="medium")
    
    features = [
        ("📝", "Registro", "Por clínica e data"),
        ("📊", "Relatórios", "Geração em Excel"),
        ("⚠️", "Alertas", "Monitoramento de estoque"),
        ("⚙️", "Configurações", "E-mail personalizado")
    ]
    
    for idx, (icon, title, desc) in enumerate(features):
        with cols[idx]:
            st.markdown(f"""
                <div class="feature-card">
                    <div class="feature-icon">{icon}</div>
                    <h4>{title}</h4>
                    <p>{desc}</p>
                </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # Call to action
    st.markdown("<h3 style='text-align: center;'>Pronto para começar?</h3>", unsafe_allow_html=True)
    if st.button("🚀 Comece Agora", use_container_width=True):
        st.session_state["pagina_atual"] = "📝 Registro de Vacinas"
        st.rerun()
    
    # Configuration section in an expander
    with st.expander("⚙️ Configurações Avançadas", expanded=False):
        st.markdown("### 📧 Configuração de E-mail")
        
        with st.form(key="email_config_form", clear_on_submit=False):
            st.markdown('<div class="config-form">', unsafe_allow_html=True)
            
            provedores = {
                "gmail": "Gmail",
                "outlook": "Outlook/Hotmail",
                "yahoo": "Yahoo Mail",
                "outro": "Outro Provedor"
            }
            
            provedor_atual = st.session_state.get('email_provider', 'gmail')
            provedor = st.selectbox(
                "Provedor de e-mail",
                options=list(provedores.keys()),
                format_func=lambda x: provedores[x],
                index=list(provedores.keys()).index(provedor_atual) if provedor_atual in provedores else 0
            )
            
            if provedor == "outro":
                servidor_smtp = st.text_input(
                    "Servidor SMTP",
                    value=st.session_state.get('smtp_server', ''),
                    help="Exemplo: smtp.example.com"
                )
                porta_smtp = st.number_input(
                    "Porta SMTP",
                    value=int(st.session_state.get('smtp_port', 587)),
                    min_value=1,
                    max_value=65535,
                    help="Porta padrão: 587 (TLS) ou 465 (SSL)"
                )
                usar_ssl = st.checkbox(
                    "Usar SSL (em vez de TLS)",
                    value=st.session_state.get('use_ssl', False),
                    help="Marque para usar SSL, desmarque para usar TLS"
                )
            
            email = st.text_input(
                "E-mail remetente",
                value="",
                placeholder="seu.email@exemplo.com",
                help="Digite o e-mail que será usado para enviar os relatórios"
            )
            
            senha = st.text_input(
                "Senha",
                value="",
                type="password",
                placeholder="********",
                help="Digite a senha do e-mail remetente ou senha de app (recomendado)"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                testar = st.form_submit_button("🔍 Testar conexão")
            with col2:
                salvar = st.form_submit_button("💾 Salvar configurações")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            if testar:
                smtp_config = {}
                if provedor == "outro":
                    smtp_config = {
                        'server': servidor_smtp,
                        'port': porta_smtp,
                        'use_ssl': usar_ssl
                    }
                
                with st.spinner("Testando conexão com o servidor de e-mail..."):
                    sucesso, mensagem = verificar_credenciais_email(email, senha, provedor, smtp_config)
                    
                    if sucesso:
                        st.success(f"✅ Conexão bem sucedida com o servidor {provedor}!")
                    else:
                        st.error(f"❌ Falha na conexão: {mensagem}")
            
            if salvar:
                if not email or not senha:
                    st.error("E-mail e senha são obrigatórios!")
                elif provedor == "outro" and (not servidor_smtp or not porta_smtp):
                    st.error("Servidor SMTP e porta são obrigatórios para provedores personalizados!")
                else:
                    st.session_state.email_remetente = email
                    st.session_state.email_senha = senha
                    st.session_state.email_provider = provedor
                    
                    if provedor == "outro":
                        st.session_state.smtp_server = servidor_smtp
                        st.session_state.smtp_port = porta_smtp
                        st.session_state.use_ssl = usar_ssl
                    
                    try:
                        with open(".env", "r") as f:
                            linhas = f.readlines()
                        
                        linhas = [l for l in linhas if not l.startswith(("EMAIL_REMETENTE=", "EMAIL_SENHA=", "EMAIL_PROVIDER=", 
                                                                        "SMTP_SERVER=", "SMTP_PORT=", "SMTP_SSL="))]
                        
                        linhas.append(f"EMAIL_REMETENTE={email}\n")
                        linhas.append(f"EMAIL_SENHA={senha}\n")
                        linhas.append(f"EMAIL_PROVIDER={provedor}\n")
                        
                        if provedor == "outro":
                            linhas.append(f"SMTP_SERVER={servidor_smtp}\n")
                            linhas.append(f"SMTP_PORT={porta_smtp}\n")
                            linhas.append(f"SMTP_SSL={'True' if usar_ssl else 'False'}\n")
                        
                        with open(".env", "w") as f:
                            f.writelines(linhas)
                        
                        st.success("✅ Configurações salvas com sucesso!")
                    except Exception as e:
                        st.warning(f"Configurações aplicadas para esta sessão, mas não foi possível salvar no arquivo .env: {str(e)}")
        
        st.markdown("### 📤 E-mails Padrão para Relatórios e Alertas")
        st.info("Configure os e-mails padrão que serão preenchidos automaticamente no formulário de envio de relatórios.")
        
        with st.form(key="email_default_form", clear_on_submit=False):
            st.markdown('<div class="config-form">', unsafe_allow_html=True)
            
            emails_relatorio = st.text_area(
                "📧 E-mails padrão para relatório (separados por vírgula)",
                value=os.getenv("EMAIL_DESTINATARIO", ""),
                help="Digite os e-mails para onde enviar o relatório completo por padrão"
            )
            
            emails_alerta = st.text_area(
                "⚠️ E-mails padrão para alertas (separados por vírgula)",
                value=os.getenv("EMAIL_ALERTA", ""),
                help="Digite os e-mails para onde enviar alertas de estoque por padrão"
            )
            
            salvar_emails_padrao = st.form_submit_button("💾 Salvar E-mails Padrão")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            if salvar_emails_padrao:
                valido_relatorio, _ = validar_emails(emails_relatorio) if emails_relatorio else (True, [])
                valido_alerta, _ = validar_emails(emails_alerta) if emails_alerta else (True, [])
                
                if not valido_relatorio:
                    st.error("E-mails de relatório inválidos!")
                elif not valido_alerta:
                    st.error("E-mails de alerta inválidos!")
                else:
                    try:
                        with open(".env", "r") as f:
                            linhas = f.readlines()
                        
                        linhas = [l for l in linhas if not l.startswith(("EMAIL_DESTINATARIO=", "EMAIL_ALERTA="))]
                        
                        linhas.append(f"EMAIL_DESTINATARIO={emails_relatorio}\n")
                        linhas.append(f"EMAIL_ALERTA={emails_alerta}\n")
                        
                        with open(".env", "w") as f:
                            f.writelines(linhas)
                        
                        st.success("✅ E-mails padrão salvos com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar e-mails padrão: {str(e)}")
    
    if not st.session_state.email_remetente or not st.session_state.email_senha:
        st.warning("""
        ⚠️ **Importante:** Configure seu email antes de utilizar o sistema.
        Acesse a seção de Configurações Avançadas para definir o email remetente.
        """)
    
    # Footer note
    st.markdown("""
        <div class="footer-note">
            Desenvolvido para simplificar a gestão de vacinas com eficiência e segurança.
        </div>
    """, unsafe_allow_html=True)

def carregar_lotes_por_vacina(vacina_id):
    conn = conectar_banco()
    df_lotes = pd.read_sql_query(f'''
        SELECT id, numero, validade
        FROM lotes
        WHERE vacina_id = {vacina_id}
        ORDER BY validade ASC
    ''', conn)
    conn.close()
    # Convert the 'validade' column from string to datetime
    df_lotes['validade'] = pd.to_datetime(df_lotes['validade'])
    return df_lotes

def mostrar_pagina_registro():
    inicializar_session_state()
    st.title("📝 Registro de Vacinas")
    st.divider()
    
    if not verificar_estrutura_banco():
        st.error("Erro na estrutura do banco de dados. Por favor, verifique os logs.")
        return
    
    if not st.session_state.email_remetente or not st.session_state.email_senha:
        st.warning("""
        ⚠️ **Email não configurado!** 
        Por favor, configure suas credenciais de email antes de utilizar esta funcionalidade.
        """)
        if st.button("Ir para Configurações"):
            st.session_state["pagina_atual"] = "⚙️ Configurações"
            st.rerun()
        return
    
    st.markdown("### 1. Informações básicas")
    col1, col2 = st.columns(2)
    
    with col1:
        df_clinicas = carregar_clinicas()
        if df_clinicas.empty:
            st.warning("Nenhuma clínica encontrada no banco de dados.")
            return
        clinica_nome = st.selectbox("Selecione a clínica", df_clinicas["nome"].tolist())
    
    with col2:
        data_relatorio = st.date_input("Data do relatório", value=datetime.now() - timedelta(days=1), format="DD/MM/YYYY")
    
    clinica_data = df_clinicas[df_clinicas["nome"] == clinica_nome].iloc[0]
    clinica_id = int(clinica_data["id"])
    st.divider()
    
    st.markdown("### 2. Quantidade aplicada por vacina e lote")
    conn = conectar_banco()
    df_vacinas = pd.read_sql_query(f'''
        SELECT 
            v.id, 
            v.nome, 
            COALESCE(e.quantidade, 0) as quantidade
        FROM vacinas v
        LEFT JOIN estoque e ON v.id = e.vacina_id AND e.clinica_id = {clinica_id}
        ORDER BY v.nome ASC
    ''', conn)
    conn.close()

    dados = {}
    registros = []
    
    for _, row in df_vacinas.iterrows():
        vacina_id = row['id']
        estoque = int(row['quantidade'])
        
        with st.container():
            st.markdown(f"#### {row['nome']}")
            
            if estoque == 0:
                icon = "🔴"
                classe = "estoque-zerado"
                alert_text = "ESGOTADO"
            elif estoque < 5:
                icon = "🟠"
                classe = "estoque-baixo"
                alert_text = f"BAIXO ({estoque})"
            else:
                icon = "🟢"
                classe = ""
                alert_text = f"Disponível: {estoque}"
            
            st.markdown(
                f"<div style='margin-bottom: 10px;'>"
                f"{f'<span class=\"alert-icon\">{icon}</span>' if icon else ''}"
                f"<span class=\"{classe}\">{alert_text}</span>"
                f"</div>", 
                unsafe_allow_html=True
            )
            
            df_lotes = carregar_lotes_por_vacina(vacina_id)
            
            if df_lotes.empty:
                st.warning(f"Não há lotes cadastrados para esta vacina. Cadastre lotes na página 'Controle de Estoque'.")
                aplicada = st.number_input(
                    "Quantidade aplicada",
                    min_value=0,
                    max_value=estoque,
                    step=1,
                    key=f"vacina_{vacina_id}"
                )
                dados[vacina_id] = aplicada
                registros.append({
                    "Vacina": row['nome'],
                    "Lote": "Sem lote",
                    "Quantidade Aplicada": aplicada,
                    "Estoque Atualizado": max(estoque - aplicada, 0)
                })
            else:
                total_aplicado = 0
                for _, lote in df_lotes.iterrows():
                    lote_id = lote['id']
                    lote_numero = lote['numero']
                    lote_validade = lote['validade']
                    
                    with st.container():
                        st.markdown(f'<div class="lote-container">', unsafe_allow_html=True)
                        st.markdown(f"**Lote:** {lote_numero} (Validade: {lote_validade.strftime('%d/%m/%Y')})")
                        aplicada = st.number_input(
                            "Quantidade aplicada",
                            min_value=0,
                            max_value=estoque,
                            step=1,
                            key=f"vacina_{vacina_id}_lote_{lote_id}"
                        )
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        total_aplicado += aplicada
                        if aplicada > 0:
                            registros.append({
                                "Vacina": row['nome'],
                                "Lote": lote_numero,
                                "Quantidade Aplicada": aplicada,
                                "Estoque Atualizado": max(estoque - total_aplicado, 0)
                            })
                
                dados[vacina_id] = total_aplicado
            
            st.divider()
    
    st.divider()
    
    st.markdown("### 3. Gerar relatório")
    if st.button("📄 Gerar Relatório", use_container_width=True):
        df_relatorio = pd.DataFrame(registros)
        if df_relatorio.empty:
            st.warning("⚠️ Nenhuma vacina registrada.")
            return
        
        st.session_state.update({
            'df_relatorio': df_relatorio,
            'dados': dados,
            'clinica_id': clinica_id,
            'clinica_nome': clinica_nome,
            'data_relatorio': data_relatorio,
            'estoque_baixo': [],
            'estoque_zerado': []
        })
        st.success("Relatório gerado com sucesso!")
    
    if not st.session_state.df_relatorio.empty:
        st.divider()
        st.markdown("### 4. Visualização e envio")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Pré-visualização do relatório**")
            st.dataframe(st.session_state.df_relatorio, height=300)
        
        with col2:
            st.markdown("**Pré-visualização do e-mail**")
            corpo_email = gerar_relatorio_texto(
                st.session_state.df_relatorio, 
                st.session_state.clinica_nome, 
                st.session_state.data_relatorio
            )
            st.text_area(
                "Corpo do e-mail",
                value=corpo_email,
                height=300,
                label_visibility="collapsed",
                disabled=True,
                key="email_preview"
            )
        
        st.markdown("### 5. Configuração do envio")
        
        col1, col2 = st.columns(2)
        with col1:
            emails_relatorio = st.text_area(
                "📧 E-mails para relatório (separados por vírgula)",
                value=os.getenv("EMAIL_DESTINATARIO", ""),
                help="Digite os e-mails para onde enviar o relatório completo"
            )
        
        with col2:
            emails_alerta = st.text_area(
                "⚠️ E-mails para alertas (separados por vírgula)",
                value=os.getenv("EMAIL_ALERTA", ""),
                help="Digite os e-mails para onde enviar alertas de estoque baixo"
            )
        
        if emails_relatorio or emails_alerta:
            valido_relatorio, lista_relatorio = validar_emails(emails_relatorio) if emails_relatorio else (True, [])
            valido_alerta, lista_alerta = validar_emails(emails_alerta) if emails_alerta else (True, [])
            
            if not valido_relatorio:
                st.warning(f"E-mails de relatório inválidos: {lista_relatorio}")
            if not valido_alerta:
                st.warning(f"E-mails de alerta inválidos: {lista_alerta}")
            
            if valido_relatorio and lista_relatorio:
                st.markdown("**E-mails que receberão o relatório completo:**")
                st.markdown(f'<div class="email-list">{"<br>".join(lista_relatorio)}</div>', unsafe_allow_html=True)
            
            if valido_alerta and lista_alerta:
                st.markdown("**E-mails que receberão alertas de estoque:**")
                st.markdown(f'<div class="email-list">{"<br>".join(lista_alerta)}</div>', unsafe_allow_html=True)
        
        if st.button("✉️ Confirmar e Enviar Relatório", use_container_width=True, key="enviar_relatorio"):
            valido_relatorio, lista_relatorio = validar_emails(emails_relatorio) if emails_relatorio else (True, [])
            valido_alerta, lista_alerta = validar_emails(emails_alerta) if emails_alerta else (True, [])
            
            if not valido_relatorio or not valido_alerta:
                st.error("Verifique os e-mails informados")
                st.stop()
            
            with st.spinner("Enviando relatório, atualizando estoque e enviando alertas..."):
                arquivo_relatorio = salvar_relatorio(
                    st.session_state.df_relatorio, 
                    st.session_state.clinica_nome, 
                    st.session_state.data_relatorio
                )
                
                erros = []
                
                if lista_relatorio:
                    corpo_email = gerar_relatorio_texto(
                        st.session_state.df_relatorio, 
                        st.session_state.clinica_nome, 
                        st.session_state.data_relatorio
                    )
                    
                    for email in lista_relatorio:
                        sucesso, msg = enviar_email(
                            email,
                            f"Relatório de Vacinas - {st.session_state.clinica_nome} - {st.session_state.data_relatorio.strftime('%d/%m/%Y')}",
                            corpo_email,
                            arquivo_relatorio
                        )
                        if not sucesso:
                            erros.append(f"{email} (relatório): {msg}")
                
                dados_validos = {
                    int(vacina_id): int(qtd) 
                    for vacina_id, qtd in st.session_state.dados.items() 
                    if qtd > 0
                }
                
                estoque_atualizado = False
                if dados_validos:
                    if atualizar_estoque(st.session_state.clinica_id, dados_validos):
                        estoque_atualizado = True
                    else:
                        erros.append("Falha ao atualizar o estoque. Verifique os logs do servidor.")
                
                estoque_baixo = []
                estoque_zerado = []
                if estoque_atualizado:
                    conn = conectar_banco()
                    df_vacinas = pd.read_sql_query(f'''
                        SELECT 
                            v.id, 
                            v.nome, 
                            COALESCE(e.quantidade, 0) as quantidade
                        FROM vacinas v
                        LEFT JOIN estoque e ON v.id = e.vacina_id AND e.clinica_id = {st.session_state.clinica_id}
                        ORDER BY v.nome ASC
                    ''', conn)
                    conn.close()
                    
                    for _, row in df_vacinas.iterrows():
                        estoque = int(row['quantidade'])
                        if estoque == 0:
                            estoque_zerado.append(row['nome'])
                        elif estoque < 5:
                            estoque_baixo.append(f"{row['nome']} ({estoque})")
                
                arquivo_alerta = None
                if estoque_baixo or estoque_zerado:
                    arquivo_alerta = salvar_alerta(
                        st.session_state.clinica_nome,
                        st.session_state.data_relatorio,
                        estoque_baixo,
                        estoque_zerado
                    )
                
                if lista_alerta and (estoque_baixo or estoque_zerado):
                    corpo_alerta = gerar_alerta_estoque(
                        st.session_state.clinica_nome,
                        estoque_baixo,
                        estoque_zerado
                    )
                    
                    for email in lista_alerta:
                        sucesso, msg = enviar_email(
                            email,
                            f"ALERTA: Estoque de Vacinas - {st.session_state.clinica_nome}",
                            corpo_alerta,
                            arquivo_alerta
                        )
                        if not sucesso:
                            erros.append(f"{email} (alerta): {msg}")
                
                if not erros:
                    if dados_validos and not estoque_atualizado:
                        st.error("⚠️ Relatório enviado, mas falha ao atualizar o estoque.")
                    else:
                        st.success("✅ Relatório enviado, estoque atualizado e alertas enviados com sucesso!")
                    
                    time.sleep(2)
                    st.session_state.clear()
                    st.rerun()
                else:
                    st.error("Ocorreram erros durante o processo:")
                    for erro in erros:
                        st.error(erro)

def mostrar_historico(pasta, prefixo="", tipo="relatório", data_inicio=None, data_fim=None, limite=None, contexto="todos"):
    print(f"Procurando {tipo}s na pasta: {pasta}")
    
    if not os.path.exists(pasta):
        st.info(f"Pasta {pasta} não existe. Nenhum {tipo} encontrado.")
        print(f"Pasta {pasta} não existe")
        return

    arquivos_na_pasta = os.listdir(pasta)
    print(f"Arquivos encontrados na pasta {pasta}: {len(arquivos_na_pasta)}")
    
    if len(arquivos_na_pasta) > 0:
        print(f"Exemplos de arquivos: {arquivos_na_pasta[:3]}")
    else:
        print("Nenhum arquivo encontrado na pasta")

    arquivos = []
    for arquivo in os.listdir(pasta):
        if prefixo and not arquivo.startswith(prefixo):
            print(f"Ignorando arquivo {arquivo} - não começa com {prefixo}")
            continue
        if not prefixo and arquivo.startswith("ALERTA_"):
            print(f"Ignorando arquivo {arquivo} - começa com ALERTA_")
            continue
        if arquivo.endswith(".xlsx"):
            try:
                nome_sem_ext = os.path.splitext(arquivo)[0]
                partes = nome_sem_ext.split('_')
                
                print(f"Processando arquivo: {arquivo}, partes: {partes}")
                
                data_str = partes[-2] if prefixo else partes[-1] if len(partes) == 2 else partes[-2]
                print(f"Tentando extrair data de: {data_str}")
                data = datetime.strptime(data_str, '%Y-%m-%d').date()
                
                if data_inicio and data_fim:
                    if not (data_inicio <= data <= data_fim):
                        print(f"Arquivo {arquivo} fora do período: {data_inicio} - {data_fim}")
                        continue
                
                if prefixo:
                    nome_clinica = ' '.join(partes[1:-2])
                else:
                    nome_clinica = ' '.join(partes[:-2]) if len(partes) > 2 else ' '.join(partes[:-1])
                
                timestamp = partes[-1] if len(partes) > 2 else None
                
                arquivos.append({
                    "data": data,
                    "timestamp": timestamp,
                    "arquivo": arquivo,
                    "clinica": nome_clinica,
                    "caminho": os.path.join(pasta, arquivo)
                })
                print(f"Arquivo {arquivo} adicionado à lista")
            except Exception as e:
                print(f"Erro ao processar arquivo {arquivo}: {e}")
                continue
    
    print(f"Total de arquivos processados: {len(arquivos)}")
    
    arquivos.sort(key=lambda x: (x["data"], x["timestamp"] if x["timestamp"] else ""), reverse=True)
    
    relatorios_por_data = {}
    for item in arquivos:
        if item["data"] not in relatorios_por_data:
            relatorios_por_data[item["data"]] = []
        relatorios_por_data[item["data"]].append(item)
    
    if limite and contexto == "ultimos_5":
        relatorios_por_data = dict(list(relatorios_por_data.items())[:5])
    
    if not relatorios_por_data:
        st.info(f"Nenhum {tipo} encontrado para o período selecionado.")
        return
    
    for data, relatorios in relatorios_por_data.items():
        st.markdown(f"### 📅 {data.strftime('%d/%m/%Y')}")
        
        for idx, item in enumerate(relatorios):
            with st.container():
                st.markdown(f"""
                <div class="historico-item">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>{item['clinica']}</strong><br>
                            <small>Horário: {item['timestamp'].replace('-', ':') if item['timestamp'] else 'Sem horário'}</small>
                        </div>
                        <div>
                """, unsafe_allow_html=True)
                
                with open(item['caminho'], "rb") as f:
                    st.download_button(
                        "⬇️ Baixar",
                        f.read(),
                        file_name=item['arquivo'],
                        key=f"{contexto}_{item['arquivo']}_{idx}"
                    )
                
                st.markdown("""
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

def mostrar_pagina_historico():
    st.title("📚 Histórico de Relatórios")
    st.divider()
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    diretorio_relatorios = os.path.join(BASE_DIR, "utilidades", "relatorios")
    diretorio_alertas = os.path.join(BASE_DIR, "utilidades", "alertas")
    
    print(f"Diretório base: {BASE_DIR}")
    print(f"Diretório de relatórios: {diretorio_relatorios}")
    print(f"Diretório de alertas: {diretorio_alertas}")
    
    if not os.path.exists(diretorio_relatorios):
        os.makedirs(diretorio_relatorios)
        print(f"Diretório de relatorios criado: {diretorio_relatorios}")
    if not os.path.exists(diretorio_alertas):
        os.makedirs(diretorio_alertas)
        print(f"Diretório de alertas criado: {diretorio_alertas}")
    
    tab1, tab2 = st.tabs(["📑 Relatórios Completos", "⚠️ Alertas de Estoque"])
    
    with tab1:
        st.markdown("### Relatórios de Vacinas Enviados")
        
        st.markdown('<div class="date-filter">', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            data_inicio = st.date_input("Data inicial", value=datetime.now() - timedelta(days=30), format="DD/MM/YYYY", key="rel_data_inicio")
        with col2:
            data_fim = st.date_input("Data final", value=datetime.now(), format="DD/MM/YYYY", key="rel_data_fim")
        
        st.markdown('<div class="date-filter-button-container">', unsafe_allow_html=True)
        if st.button("🔍 Filtrar Relatórios", key="filtrar_relatorios"):
            st.session_state.filtrar_relatorios = True
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        mostrar_historico(diretorio_relatorios, prefixo="", tipo="relatório", data_inicio=data_inicio, data_fim=data_fim, contexto="relatorios")
    
    with tab2:
        st.markdown("### Alertas de Estoque Enviados")
        
        st.markdown('<div class="date-filter">', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            data_inicio_alertas = st.date_input("Data inicial", value=datetime.now() - timedelta(days=30), format="DD/MM/YYYY", key="alerta_data_inicio")
        with col2:
            data_fim_alertas = st.date_input("Data final", value=datetime.now(), format="DD/MM/YYYY", key="alerta_data_fim")
        
        st.markdown('<div class="date-filter-button-container">', unsafe_allow_html=True)
        if st.button("🔍 Filtrar Alertas", key="filtrar_alertas"):
            st.session_state.filtrar_alertas = True
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        mostrar_historico(diretorio_alertas, prefixo="ALERTA_", tipo="alerta", data_inicio=data_inicio_alertas, data_fim=data_fim_alertas, contexto="alertas")

def mostrar_pagina_estoque():
    st.title("📦 Controle de Estoque")
    st.divider()
    
    if not verificar_estrutura_banco():
        st.error("Erro na estrutura do banco de dados. Por favor, verifique os logs.")
        return
    
    if "estoque_modo" not in st.session_state:
        st.session_state.estoque_modo = "visualizar"
    if "estoque_item_selecionado" not in st.session_state:
        st.session_state.estoque_item_selecionado = None
    if "estoque_confirmando_exclusao" not in st.session_state:
        st.session_state.estoque_confirmando_exclusao = False
    if "lote_confirmando_exclusao" not in st.session_state:
        st.session_state.lote_confirmando_exclusao = False
    if "lote_selecionado" not in st.session_state:
        st.session_state.lote_selecionado = None
    
    # Carregar clínicas e vacinas com lotes
    conn = conectar_banco()
    df_clinicas = pd.read_sql_query("SELECT id, nome FROM clinicas ORDER BY nome ASC", conn)
    df_vacinas = pd.read_sql_query("SELECT id, nome FROM vacinas ORDER BY nome ASC", conn)
    df_lotes = pd.read_sql_query("SELECT id, vacina_id, numero, validade FROM lotes ORDER BY vacina_id, validade ASC", conn)
    # Convert the 'validade' column from string to datetime
    df_lotes['validade'] = pd.to_datetime(df_lotes['validade'])
    conn.close()
    
    # Criar um mapeamento de vacinas e lotes para exibição
    vacina_lote_map = {}
    for _, vacina in df_vacinas.iterrows():
        vacina_id = vacina['id']
        vacina_nome = vacina['nome']
        lotes = df_lotes[df_lotes['vacina_id'] == vacina_id]
        if lotes.empty:
            vacina_lote_map[vacina_id] = f"{vacina_nome} (Sem lotes)"
        else:
            lotes_str = "; ".join([f"{lote['numero']} (Validade: {lote['validade'].strftime('%d/%m/%Y')})" for _, lote in lotes.iterrows()])
            vacina_lote_map[vacina_id] = f"{vacina_nome} - Lotes: {lotes_str}"
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("➕ Adicionar Nova Vacina", key="btn_add_vacina"):
            st.session_state.estoque_modo = "adicionar_vacina"
    with col2:
        if st.button("🔄 Ajustar Estoque", key="btn_ajustar_estoque"):
            st.session_state.estoque_modo = "ajustar_estoque"
    with col3:
        if st.button("❌ Remover Vacina", key="btn_remover_vacina"):
            st.session_state.estoque_modo = "remover_vacina"
    with col4:
        if st.button("📋 Gerenciar Lotes", key="btn_gerenciar_lotes"):
            st.session_state.estoque_modo = "gerenciar_lotes"
    
    st.divider()
    
    if st.session_state.estoque_modo == "adicionar_vacina":
        st.markdown("### ➕ Adicionar Nova Vacina")
        with st.form("form_nova_vacina"):
            nome_vacina = st.text_input("Nome da Vacina", key="nova_vacina_nome")
            numero_lote = st.text_input("Número do Lote", help="Exemplo: LOTE001")
            validade_lote = st.date_input("Data de Validade do Lote", min_value=datetime.now(), format="DD/MM/YYYY")
            quantidade_inicial = st.number_input("Quantidade Inicial", min_value=0, step=1)
            clinica_id = st.selectbox(
                "Selecione a Clínica",
                options=df_clinicas["id"].tolist(),
                format_func=lambda x: df_clinicas[df_clinicas["id"] == x]["nome"].iloc[0],
                key="nova_vacina_clinica_id"
            )
            enviar = st.form_submit_button("Adicionar")
            
            if enviar:
                if not nome_vacina:
                    st.error("O nome da vacina é obrigatório.")
                elif not numero_lote:
                    st.error("O número do lote é obrigatório.")
                elif not validade_lote:
                    st.error("A data de validade é obrigatória.")
                else:
                    conn = conectar_banco()
                    cursor = conn.cursor()
                    try:
                        # Inserir a vacina
                        cursor.execute("INSERT INTO vacinas (nome) VALUES (?)", (nome_vacina,))
                        vacina_id = cursor.lastrowid
                        
                        # Inserir o lote
                        cursor.execute(
                            "INSERT INTO lotes (vacina_id, numero, validade) VALUES (?, ?, ?)",
                            (vacina_id, numero_lote, validade_lote)
                        )
                        
                        # Inserir a quantidade inicial no estoque
                        cursor.execute(
                            "INSERT INTO estoque (clinica_id, vacina_id, quantidade) VALUES (?, ?, ?)",
                            (clinica_id, vacina_id, quantidade_inicial)
                        )
                        
                        conn.commit()
                        st.success(f"✅ Vacina '{nome_vacina}' com lote '{numero_lote}' adicionada com sucesso! Estoque inicial: {quantidade_inicial} unidades.")
                        st.session_state.estoque_modo = "visualizar"
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Erro ao adicionar vacina: {str(e)}")
                    finally:
                        conn.close()
        
        # Adicionar botão "Voltar"
        if st.button("⬅️ Voltar", key="voltar_adicionar_vacina"):
            st.session_state.estoque_modo = "visualizar"
            st.rerun()
    
    elif st.session_state.estoque_modo == "ajustar_estoque":
        st.markdown("### 🔄 Ajustar Estoque")
        
        col1, col2 = st.columns(2)
        with col1:
            clinica_id = st.selectbox(
                "Selecione a Clínica",
                options=df_clinicas["id"].tolist(),
                format_func=lambda x: df_clinicas[df_clinicas["id"] == x]["nome"].iloc[0],
                key="ajuste_clinica_id"
            )
        with col2:
            vacina_id = st.selectbox(
                "Selecione a Vacina",
                options=df_vacinas["id"].tolist(),
                format_func=lambda x: vacina_lote_map[x],
                key="ajuste_vacina_id"
            )
        
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT quantidade FROM estoque WHERE clinica_id = ? AND vacina_id = ?",
            (clinica_id, vacina_id)
        )
        resultado = cursor.fetchone()
        estoque_atual = resultado[0] if resultado else 0
        conn.close()
        
        st.markdown(f"**Estoque atual:** {estoque_atual} unidades")
        
        with st.form("form_ajuste_estoque"):
            col1, col2 = st.columns(2)
            with col1:
                operacao = st.radio(
                    "Operação",
                    options=["adicionar", "remover"],
                    format_func=lambda x: {"adicionar": "Adicionar", "remover": "Remover"}[x],
                    horizontal=True
                )
            with col2:
                quantidade = st.number_input("Quantidade", min_value=1, value=1)
            
            nova_quantidade = (
                estoque_atual + quantidade if operacao == "adicionar" 
                else max(0, estoque_atual - quantidade)
            )
            descricao = (
                f"Adicionar {quantidade} → {estoque_atual} + {quantidade} = {nova_quantidade}"
                if operacao == "adicionar" 
                else f"Remover {quantidade} → {estoque_atual} - {quantidade} = {nova_quantidade}"
            )
            
            confirmar = st.form_submit_button("Confirmar Ajuste")
            
            if confirmar:
                conn = conectar_banco()
                try:
                    sucesso, mensagem = alterar_estoque(
                        clinica_id, 
                        vacina_id, 
                        quantidade,
                        operacao
                    )
                    if sucesso:
                        st.success(f"✅ {mensagem}")
                        st.session_state.estoque_modo = "visualizar"
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {mensagem}")
                except Exception as e:
                    st.error(f"Erro ao atualizar estoque: {str(e)}")
                finally:
                    conn.close()
        
        # Adicionar botão "Voltar"
        if st.button("⬅️ Voltar", key="voltar_ajustar_estoque"):
            st.session_state.estoque_modo = "visualizar"
            st.rerun()
    
    elif st.session_state.estoque_modo == "remover_vacina":
        st.markdown("### ❌ Remover Vacina")
        
        vacina_id = st.selectbox(
            "Selecione a Vacina para Remover",
            options=df_vacinas["id"].tolist(),
            format_func=lambda x: vacina_lote_map[x],
            key="remover_vacina_id"
        )
        
        st.session_state.estoque_item_selecionado = vacina_id
        nome_vacina = df_vacinas[df_vacinas["id"] == vacina_id]["nome"].iloc[0]
        
        if not st.session_state.estoque_confirmando_exclusao:
            if st.button(f"Remover '{nome_vacina}'"):
                st.session_state.estoque_confirmando_exclusao = True
                st.rerun()
        else:
            st.markdown(f"""
            <div class="remove-warning">
                <h4>⚠️ Confirmação de Exclusão</h4>
                <p>Você está prestes a excluir permanentemente a vacina <strong>"{nome_vacina}"</strong>.</p>
                <p>Esta ação também removerá todos os registros de estoque e lotes relacionados a esta vacina em todas as clínicas.</p>
                <p>Esta ação não pode ser desfeita!</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("❌ Cancelar"):
                    st.session_state.estoque_confirmando_exclusao = False
                    st.session_state.estoque_item_selecionado = None
                    st.rerun()
            with col2:
                if st.button("⚠️ Excluir Permanentemente", type="primary"):
                    conn = conectar_banco()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("BEGIN TRANSACTION")
                        cursor.execute("DELETE FROM estoque WHERE vacina_id = ?", (vacina_id,))
                        cursor.execute("DELETE FROM lotes WHERE vacina_id = ?", (vacina_id,))
                        cursor.execute("DELETE FROM vacinas WHERE id = ?", (vacina_id,))
                        cursor.execute("COMMIT")
                        st.success(f"✅ Vacina '{nome_vacina}' e seus lotes removidos com sucesso!")
                        st.session_state.estoque_confirmando_exclusao = False
                        st.session_state.estoque_item_selecionado = None
                        st.session_state.estoque_modo = "visualizar"
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        cursor.execute("ROLLBACK")
                        st.error(f"Erro ao remover vacina: {str(e)}")
                    finally:
                        conn.close()
        
        # Adicionar botão "Voltar"
        if st.button("⬅️ Voltar", key="voltar_remover_vacina"):
            st.session_state.estoque_confirmando_exclusao = False
            st.session_state.estoque_item_selecionado = None
            st.session_state.estoque_modo = "visualizar"
            st.rerun()
    
    elif st.session_state.estoque_modo == "gerenciar_lotes":
        st.markdown("### 📋 Gerenciar Lotes")
        
        vacina_id = st.selectbox(
            "Selecione a Vacina",
            options=df_vacinas["id"].tolist(),
            format_func=lambda x: vacina_lote_map[x],
            key="gerenciar_lotes_vacina_id"
        )
        
        nome_vacina = df_vacinas[df_vacinas["id"] == vacina_id]["nome"].iloc[0]
        st.subheader(f"Lotes da Vacina: {nome_vacina}")
        
        # Carregar lotes existentes
        conn = conectar_banco()
        df_lotes = pd.read_sql_query(f"""
            SELECT id, numero, validade
            FROM lotes
            WHERE vacina_id = {vacina_id}
            ORDER BY validade ASC
        """, conn)
        # Convert the 'validade' column from string to datetime
        df_lotes['validade'] = pd.to_datetime(df_lotes['validade'])
        conn.close()
        
        if df_lotes.empty:
            st.info("Nenhum lote cadastrado para esta vacina.")
        else:
            st.markdown("**Lotes Existentes**")
            for idx, lote in df_lotes.iterrows():
                with st.container():
                    st.markdown(f'<div class="lote-container">', unsafe_allow_html=True)
                    st.markdown(f"**Lote:** {lote['numero']} (Validade: {lote['validade'].strftime('%d/%m/%Y')})")
                    if st.button("❌ Remover", key=f"remover_lote_{lote['id']}"):
                        st.session_state.lote_selecionado = lote['id']
                        st.session_state.lote_confirmando_exclusao = True
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            
            if st.session_state.lote_confirmando_exclusao and st.session_state.lote_selecionado:
                lote = df_lotes[df_lotes['id'] == st.session_state.lote_selecionado].iloc[0]
                st.markdown(f"""
                <div class="remove-warning">
                    <h4>⚠️ Confirmação de Exclusão</h4>
                    <p>Você está prestes a excluir permanentemente o lote <strong>"{lote['numero']}"</strong> da vacina <strong>"{nome_vacina}"</strong>.</p>
                    <p>Esta ação não pode be desfeita!</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("❌ Cancelar", key="cancelar_remocao_lote"):
                        st.session_state.lote_confirmando_exclusao = False
                        st.session_state.lote_selecionado = None
                        st.rerun()
                with col2:
                    if st.button("⚠️ Excluir Permanentemente", type="primary", key="confirmar_remocao_lote"):
                        conn = conectar_banco()
                        cursor = conn.cursor()
                        try:
                            cursor.execute("DELETE FROM lotes WHERE id = ?", (st.session_state.lote_selecionado,))
                            conn.commit()
                            st.success(f"✅ Lote '{lote['numero']}' removido com sucesso!")
                            st.session_state.lote_confirmando_exclusao = False
                            st.session_state.lote_selecionado = None
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao remover lote: {str(e)}")
                        finally:
                            conn.close()
        
        # Formulário para cadastrar novo lote
        st.markdown("**Cadastrar Novo Lote**")
        with st.form("form_novo_lote", clear_on_submit=True):
            numero_lote = st.text_input("Número do Lote", help="Exemplo: LOTE001")
            validade_lote = st.date_input("Data de Validade", min_value=datetime.now(), format="DD/MM/YYYY")
            enviar = st.form_submit_button("Adicionar Lote")
            
            if enviar:
                if not numero_lote:
                    st.error("O número do lote é obrigatório.")
                elif not validade_lote:
                    st.error("A data de validade é obrigatória.")
                else:
                    conn = conectar_banco()
                    cursor = conn.cursor()
                    try:
                        # Verificar se o lote já existe para a vacina
                        cursor.execute(
                            "SELECT COUNT(*) FROM lotes WHERE vacina_id = ? AND numero = ?",
                            (vacina_id, numero_lote)
                        )
                        if cursor.fetchone()[0] > 0:
                            st.error(f"O lote '{numero_lote}' já existe para esta vacina.")
                        else:
                            # Inserir o novo lote
                            cursor.execute(
                                "INSERT INTO lotes (vacina_id, numero, validade) VALUES (?, ?, ?)",
                                (vacina_id, numero_lote, validade_lote)
                            )
                            conn.commit()
                            st.success(f"✅ Lote '{numero_lote}' cadastrado com sucesso!")
                            st.session_state.lote_confirmando_exclusao = False
                            st.session_state.lote_selecionado = None
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar lote: {str(e)}")
                        st.error(f"Detalhes: vacina_id={vacina_id}, numero_lote={numero_lote}, validade_lote={validade_lote}")
                    finally:
                        conn.close()
        
        # Adicionar botão "Voltar"
        if st.button("⬅️ Voltar", key="voltar_gerenciar_lotes"):
            st.session_state.lote_confirmando_exclusao = False
            st.session_state.lote_selecionado = None
            st.session_state.estoque_modo = "visualizar"
            st.rerun()
    
    else:
        st.markdown("### 📈 Visão Geral do Estoque")
        
        clinica_id = st.selectbox(
            "Filtrar por Clínica",
            options=df_clinicas["id"].tolist(),
            format_func=lambda x: df_clinicas[df_clinicas["id"] == x]["nome"].iloc[0],
            key="view_clinica_id"
        )
        
        conn = conectar_banco()
        df_estoque = pd.read_sql_query(f'''
            SELECT 
                v.id as vacina_id,
                v.nome as vacina_nome,
                COALESCE(e.quantidade, 0) as quantidade,
                l.numero as lote_numero,
                l.validade as lote_validade
            FROM vacinas v
            LEFT JOIN estoque e ON v.id = e.vacina_id AND e.clinica_id = {clinica_id}
            LEFT JOIN lotes l ON v.id = l.vacina_id
            ORDER BY v.nome ASC, l.validade ASC
        ''', conn)
        # Convert the 'lote_validade' column from string to datetime
        df_estoque['lote_validade'] = pd.to_datetime(df_estoque['lote_validade'])
        conn.close()
        
        nome_clinica = df_clinicas[df_clinicas["id"] == clinica_id]["nome"].iloc[0]
        st.subheader(f"Estoque da Clínica: {nome_clinica}")
        
        # Group by vaccine to properly aggregate lots
        df_estoque_grouped = df_estoque.groupby(['vacina_id', 'vacina_nome', 'quantidade']).agg({
            'lote_numero': lambda x: [i for i in x if pd.notna(i)],
            'lote_validade': lambda x: [i for i in x if pd.notna(i)]
        }).reset_index()

        # Create a formatted lot string
        df_estoque_grouped['lotes'] = df_estoque_grouped.apply(
            lambda row: '; '.join(
                f"{num} (Validade: {val.strftime('%d/%m/%Y')})" for num, val in zip(row['lote_numero'], row['lote_validade'])
            ) if row['lote_numero'] else 'Sem lotes',
            axis=1
        )

        # Separate into out of stock, low stock, and sufficient stock
        estoque_zerado = df_estoque_grouped[df_estoque_grouped['quantidade'] == 0].sort_values(by='vacina_nome')
        estoque_baixo = df_estoque_grouped[(df_estoque_grouped['quantidade'] > 0) & (df_estoque_grouped['quantidade'] < 5)].sort_values(by='vacina_nome')
        estoque_suficiente = df_estoque_grouped[df_estoque_grouped['quantidade'] >= 5].sort_values(by='vacina_nome')

        # Display Out of Stock Section
        if not estoque_zerado.empty:
            st.markdown('<div class="stock-section">', unsafe_allow_html=True)
            st.markdown('<h3><span class="alert-icon">🔴</span>Estoque Esgotado</h3>', unsafe_allow_html=True)
            st.markdown('<div class="stock-cards">', unsafe_allow_html=True)
            
            for _, row in estoque_zerado.iterrows():
                st.markdown(f"""
                <div class="stock-card">
                    <div class="stock-card-header">
                        <span class="alert-icon">🔴</span>
                        <h4>{row['vacina_nome']}</h4>
                    </div>
                    <div class="stock-card-body">
                        <p><strong>Quantidade:</strong> {row['quantidade']} unidades</p>
                        <p class="lotes"><strong>Lotes:</strong> {row['lotes']}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Display Low Stock Section
        if not estoque_baixo.empty:
            st.markdown('<div class="stock-section">', unsafe_allow_html=True)
            st.markdown('<h3><span class="alert-icon">🟠</span>Estoque Baixo</h3>', unsafe_allow_html=True)
            st.markdown('<div class="stock-cards">', unsafe_allow_html=True)
            
            for _, row in estoque_baixo.iterrows():
                st.markdown(f"""
                <div class="stock-card">
                    <div class="stock-card-header">
                        <span class="alert-icon">🟠</span>
                        <h4>{row['vacina_nome']}</h4>
                    </div>
                    <div class="stock-card-body">
                        <p><strong>Quantidade:</strong> {row['quantidade']} unidades</p>
                        <p class="lotes"><strong>Lotes:</strong> {row['lotes']}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Display Sufficient Stock Section
        if not estoque_suficiente.empty:
            st.markdown('<div class="stock-section">', unsafe_allow_html=True)
            st.markdown('<h3><span class="alert-icon">🟢</span>Estoque Suficiente</h3>', unsafe_allow_html=True)
            st.markdown('<div class="stock-cards">', unsafe_allow_html=True)
            
            for _, row in estoque_suficiente.iterrows():
                st.markdown(f"""
                <div class="stock-card">
                    <div class="stock-card-header">
                        <span class="alert-icon">🟢</span>
                        <h4>{row['vacina_nome']}</h4>
                    </div>
                    <div class="stock-card-body">
                        <p><strong>Quantidade:</strong> {row['quantidade']} unidades</p>
                        <p class="lotes"><strong>Lotes:</strong> {row['lotes']}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # If no vaccines are registered
        if estoque_zerado.empty and estoque_baixo.empty and estoque_suficiente.empty:
            st.info("ℹ️ Nenhuma vacina registrada no estoque desta clínica.")

paginas = {
    "🏠 Introdução": mostrar_pagina_introducao,
    "📝 Registro de Vacinas": mostrar_pagina_registro,
    "📦 Controle de Estoque": mostrar_pagina_estoque,
    "📁 Histórico de Relatórios": mostrar_pagina_historico
}

inicializar_session_state()
escolha = st.sidebar.radio("Navegar", list(paginas.keys()), index=list(paginas.keys()).index(st.session_state.pagina_atual))
st.session_state.pagina_atual = escolha
paginas[escolha]()