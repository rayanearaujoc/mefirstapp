import streamlit as st
import sqlite3
import google.generativeai as genai
from collections import Counter
import plotly as px
from google.cloud import language_v2
import os
from PIL import Image


# Configuração do SQLite
conn = sqlite3.connect('me.db', check_same_thread=False)
cursor = conn.cursor()

# Criação das tabelas (se não existirem)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        mensagem TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
''')

conn.commit()

# Função para inserir usuário no banco de dados
def cadastrar_usuario(username, email):
    cursor.execute('''
        INSERT INTO usuarios (username, email)
        VALUES (?, ?)
    ''', (username, email))
    conn.commit()
    return cursor.lastrowid  # Retorna o ID do usuário inserido

# Função para buscar usuário pelo nome e email
def buscar_usuario(username, email):
    cursor.execute('''
        SELECT id FROM usuarios
        WHERE username = ? AND email = ?
    ''', (username, email))
    return cursor.fetchone()

# Função para salvar mensagem de chat no banco de dados
def salvar_chat(usuario_id, mensagem):
    cursor.execute('''
        INSERT INTO chats (usuario_id, mensagem)
        VALUES (?, ?)
    ''', (usuario_id, mensagem))
    conn.commit()

# Função para buscar mensagens de chat de um usuário específico
def buscar_chats(usuario_id):
    cursor.execute('''
        SELECT mensagem, timestamp
        FROM chats
        WHERE usuario_id = ?
        ORDER BY timestamp
    ''', (usuario_id,))
    return cursor.fetchall()

# Configuração do Streamlit
st.set_page_config(
    page_title="MeFirst",
    page_icon="💢",
    layout="wide",
    initial_sidebar_state="expanded"
)
image_path1 = 'imagemlayout.jpg'

API_KEY = os.getenv('API_KEY')
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

genai.configure(api_key=API_KEY)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS

# Criação do modelo Gemini
model = genai.GenerativeModel(
    'gemini-1.5-flash',
    generation_config=genai.GenerationConfig(
        max_output_tokens=1500,
        temperature=0.7,
    ))

# Função para gerar resposta com o modelo Gemini
def generate_gemini_response(prompt):
    response = model.generate_content(prompt)
    return response.text

image = Image.open('logo 1.png')

new_width = 300
new_height = 90
image = image.resize((new_width, new_height))

def main():
    st.sidebar.title("Menu")
    menu_options = ["Home", "ChatBot", "Meu Perfil", "Relatório"]
    st.session_state.page = st.sidebar.selectbox(
        "Navegação", 
        menu_options, 
        index=menu_options.index(st.session_state.get('page', 'Home'))
    )

    if st.session_state.page == "Home":
        home()
    elif st.session_state.page == "ChatBot":
        chatbot()
    elif st.session_state.page == "Meu Perfil":
        perfil()
    elif st.session_state.page == "Relatório":
        analise()



# Redimensionar a imagem
image = Image.open('logo 1.png')

new_width = 300
new_height = 90
image = image.resize((new_width, new_height))
    
def home():
    st.image(image)
    st.write("---")

    colum1, colum2 = st.columns(2)
    with colum1:
        with st.form(key="Usuario"):
            st.write("*Desabafe sem julgamentos, estamos aqui para te auxiliar na sua jornada de autoconhecimento*")
            user_name = st.text_input("Digite seu nome:")
            perfil = st.selectbox("Escolha um perfil", ["Pessoal", "Estudante", "Profissional"])
            email = st.text_input("Digite seu melhor e-mail:")
            inicio = st.form_submit_button("Iniciar Agora →", type="primary")

            if inicio:
                if user_name and email:
                    user_id = buscar_usuario(user_name, email)
                    if user_id:
                        st.session_state['user_id'] = user_id[0]
                        st.session_state['user_name'] = user_name
                    else:
                        st.session_state['user_id'] = cadastrar_usuario(user_name, email)
                        st.session_state['user_name'] = user_name
                    st.session_state['gemini_choice'] = perfil
                    st.session_state.page = "ChatBot"
                    st.rerun()
                else:
                    st.warning("Por favor, digite seu nome e e-mail antes de iniciar.")

    with colum2:
        st.image(image_path1, use_column_width=True)


def chatbot():
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("Usuário não encontrado. Por favor, inicie novamente.")
        return

    if st.button("Sair", type="primary"):
        if "messages" in st.session_state:
            # Salva mensagens no banco de dados
            for msg in st.session_state.messages:
                if msg["role"] == "Usuário":
                    salvar_chat(user_id, msg["content"])
        st.session_state.messages = []
        st.session_state.page = "Meu Perfil"
        st.rerun()

    user_name = st.session_state.get('user_name', 'usuário')
    st.title(f"Olá, :red[{user_name}]")

    # Inicializa o histórico de mensagens e prompts do usuário
    if "messages" not in st.session_state or not st.session_state.messages:
        st.session_state.messages = [{"role": "Bot", "content": "👋 Sinta-se à vontade para desabafar. Estou aqui para te escutar."}]
    
    if "user_prompts" not in st.session_state:
        st.session_state.user_prompts = []

    # Estilos CSS para as bolhas de chat
    st.markdown("""
        <style>
        .user-bubble {
            background-color: #d7d9fa;
            border-radius: 10px;
            padding: 10px;
            margin: 10px;
            max-width: 60%;
            text-align: left;
            float: right;
            clear: both;
            color: black;
            box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1);
        }
        .bot-bubble {
            background-color: #f2f2f2;
            border-radius: 10px;
            padding: 10px;
            margin: 10px;
            max-width: 60%;
            text-align: left;
            float: left;
            clear: both;
            color: black;
            box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    # Função para exibir mensagens de chat
    def display_chat(messages):
        for msg in messages:
            if msg["role"] == "Usuário":
                st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="bot-bubble">{msg["content"]}</div>', unsafe_allow_html=True)

    # Lida com a entrada do usuário
    prompt = st.chat_input("Digite algo")
    if prompt:
        st.session_state.messages.append({"role": "Usuário", "content": prompt})
        st.session_state.user_prompts.append(prompt)  # Adiciona o prompt à lista de prompts do usuário
        conversation_history = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages])

        gemini_choice = st.session_state.get('gemini_choice', 'Pessoal')
        
        if gemini_choice == "Pessoal":
            gemini_prompt = (
                "Você é um chatbot que simula um psicólogo. Seu objetivo é fazer com que o usuário se sinta ouvido e ajudado. "
                "Pergunte ao usuário como ele está se sentindo hoje e peça para ele falar sobre seus sentimentos e emoções. "
                "Envie mensagens de apoio e comandos de escrita que ajudem o usuário a trabalhar seus sentimentos. "
                "Mantenha uma conversa acolhedora e formal. Responda de forma concisa.\n\n"
                f"Histórico da conversa:\n{conversation_history}"
            )
        elif gemini_choice == "Estudante":
            gemini_prompt = (
                "Você é um chatbot que simula um psicólogo e está conversando com um estudante. "
                "Pergunte ao usuário como ele está se sentindo em relação aos estudos. "
                "Faça perguntas sobre como ele está lidando com as pressões acadêmicas e sociais. "
                "Envie mensagens de apoio e comandos de escrita que ajudem o usuário a refletir sobre suas experiências escolares. "
                "Mantenha uma conversa acolhedora e formal. Responda de forma concisa.\n\n"
                f"Histórico da conversa:\n{conversation_history}"
            )
        elif gemini_choice == "Profissional":
            gemini_prompt = (
                "Você é um chatbot que simula um psicólogo e está conversando com um profissional. "
                "Pergunte ao usuário como ele está se sentindo no trabalho e peça para ele falar sobre seus desafios e preocupações profissionais. "
                "Faça perguntas que ajudem a explorar como ele está lidando com o ambiente de trabalho e as expectativas. "
                "Envie mensagens de apoio e comandos de escrita que ajudem o usuário a refletir sobre suas experiências no trabalho. "
                "Mantenha uma conversa acolhedora e formal. Responda de forma concisa.\n\n"
                f"Histórico da conversa:\n{conversation_history}"
            )

        bot_response = generate_gemini_response(gemini_prompt)

        st.session_state.messages.append({"role": "Bot", "content": bot_response})

    # Exibe mensagens de chat
    display_chat(st.session_state.messages)

def perfil():
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("Usuário não encontrado. Por favor, inicie novamente.")
        return
    
    st.title("Meu Perfil")
    st.markdown("### Histórico de Chats:")
    
    # Busca todas as mensagens de chat do usuário no banco de dados
    all_user_messages = buscar_chats(user_id)
    
    if all_user_messages:
        with st.expander("Todos os Chats"):
            for i, msg in enumerate(all_user_messages):
                st.write(f"**Mensagem {i+1}:** {msg[0]}")
                st.write("---")
    else:
        st.write("Nenhum histórico de chats encontrado.")

    if st.button("Ver Insights dessas Conversas", type="primary"):
        st.session_state.page = "Relatório"
        st.session_state.all_user_messages = all_user_messages  # Armazena todas as mensagens para análise
        st.rerun()

    if st.button("Novo Chat"):
        st.session_state.page = "ChatBot"
        st.session_state.messages = []  # Reseta as mensagens para novo chat
        st.rerun()

def generate_summary_response(user_messages):
    user_text = "\n".join([msg["content"] for msg in user_messages])
    gemini_prompt_summary = (        
        "Você é um chatbot que simula um psicólogo. "
        "Seu objetivo é fazer um resumo das mensagens enviadas pelo usuário e fornecer uma recomendação personalizada baseada no que foi dito. "
        "O resumo deve ser claro e conciso, destacando os pontos principais mencionados pelo usuário. "
        "A recomendação deve ser prática e útil, ajudando o usuário a lidar com os problemas ou emoções que ele compartilhou. "
        "Mantenha um tom acolhedor e formal.\n\n"
        f"Mensagens do usuário:\n{user_text}\n\n"
        "Resumo:\n"
        "Recomendação:\n")
    
    summary_response = generate_gemini_response(gemini_prompt_summary)
    return summary_response

def analyze_text(user_messages):
    client = language_v2.LanguageServiceClient()
    topics = []
    sentiment_scores = []

    for message in user_messages:
        text_content = message["content"]
        document = language_v2.Document(content=text_content, type_=language_v2.Document.Type.PLAIN_TEXT)

        response_topics = client.analyze_entities(request={'document': document})
        topics.extend([entity.name for entity in response_topics.entities if entity.type_.name == 'OTHER'])

        response_sentiment = client.analyze_sentiment(request={'document': document})
        sentiment = response_sentiment.document_sentiment

        sentiment_analysis = "Neutro"
        if sentiment.score > 0.25:
            sentiment_analysis = "Positivo"
        elif sentiment.score < -0.25:
            sentiment_analysis = "Negativo"

        sentiment_scores.append((sentiment_analysis, sentiment.magnitude, sentiment.score))

    return sentiment_scores, topics

def analise():
    st.title(f"Seu :red[Relatório]")

    with st.spinner('Carregando seus resultados...'):
        # Verifica se há mensagens de chatbot na sessão
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Obtém todas as mensagens do usuário para análise
        if "all_user_messages" in st.session_state:
            user_messages = [{"content": msg[0]} for msg in st.session_state.all_user_messages]
        else:
            user_messages = [{"content": msg["content"]} for msg in st.session_state.messages if msg["role"] == "Usuário"]

        # Realiza a análise de sentimento e tópicos com base em todas as mensagens do usuário
        sentiment_scores, topics = analyze_text(user_messages)
        if len(sentiment_scores) > 0:
            col1, col2 = st.columns(2)

            with col1:
                summary_response = generate_summary_response(user_messages)
                st.write(f'{summary_response}')
                st.write("---")

            with col2:
                custom_colors = px.colors.qualitative.Bold.copy()
                custom_colors[2] = '#1f77b4'  # Substituindo roxo por azul

                st.markdown("#### Análise de Sentimento:")
                sentiment_data = {
                    'Sentimento': ['Positivo', 'Neutro', 'Negativo'],
                    'Frequência': [
                        sum(1 for s in sentiment_scores if s[0] == 'Positivo'),
                        sum(1 for s in sentiment_scores if s[0] == 'Neutro'),
                        sum(1 for s in sentiment_scores if s[0] == 'Negativo')
                    ]
                }

                fig_sentiment = px.pie(sentiment_data, names='Sentimento', values='Frequência', color_discrete_sequence=custom_colors)
                st.plotly_chart(fig_sentiment, use_container_width=True)
                unique_topics = list(set(topics))
                top_topics = unique_topics[:6]  # Limita a lista de tópicos a 6
                st.markdown("#### Gráfico de Frequências dos Tópicos:")
                topic_counts = Counter(topics).most_common(6)  # Limita os tópicos a 6

                # Extrai os dados para o gráfico de barras
                topics = [topic[0] for topic in topic_counts]
                counts = [topic[1] for topic in topic_counts]

                fig = px.bar(x=topics, y=counts, labels={'x': 'Tópico', 'y': 'Frequência'}, color_discrete_sequence=custom_colors)
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Principais Questões Levantadas"):
                    st.markdown("#### Tópicos Principais:")
                    for topic in top_topics:
                        st.write(f"- **{topic}**")

    st.write("---")

if __name__ == "__main__":
    main()