import base64
import os
import re
import requests
from markdown2 import markdown
from langchain.agents import load_tools
from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain_community.chat_models import ChatOpenAI
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

os.environ["OPENAI_API_KEY"] = "" # Open API keyを指定
os.environ["GOOGLE_CSE_ID"] = "" # Google API の Custom Search API の keyを指定
os.environ["GOOGLE_API_KEY"] = "" 

def remove_indent_using_lstrip(text):
    lines = text.splitlines()
    stripped_lines = [line.lstrip() for line in lines]
    return "\n".join(stripped_lines)
    
def search_keywords(keyword):

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)

    driver.get('https://related-keywords.com/') # ラッコキーワードからスクレイピング

    try:
        search_box = driver.find_element(By.CSS_SELECTOR, '.sc-7f8786d5-0.sc-bb4a78f4-1.bxlSfJ.jsoWmd')
        
    except Exception:
        print("CSS_SELECOTOR ERROR : Made change the css-serecters in related-keywords.com")
        exit()

    search_keyword = keyword
    search_box.send_keys(search_keyword)

    search_box.send_keys(Keys.RETURN)

    time.sleep(2)

    results = driver.find_elements(By.CSS_SELECTOR, '.sc-fa9073d3-0.sc-fa72331-4.kwALoV.cOMrnA')

    res_list = []
    for res in results:
        res_list.append(res.text + "<br>")            
    driver.quit()

    return "".join(res_list)

    #------------------------------------------------------------
def make_sentences(keyword):

    llm = ChatOpenAI(model_name = "gpt-4o") 
 
    # wordpressの吹き出しのタグ、srcに使用したい画像を指定
    fukidashi_left = '''<!-- wp:word-balloon/word-balloon-block -->
<div class="wp-block-word-balloon-word-balloon-block">[word_balloon id="unset" src="" size="M" position="L" radius="true" name="" balloon="talk" balloon_shadow="true"]<p>'''

    fukidashi_right = '''</p>[/word_balloon]</div>
<!-- /wp:word-balloon/word-balloon-block -->'''

    sentence = ""
    t = 0

    # ツールの読み込み
    tool_names = ["google-search"]
    tools = load_tools(tool_names, llm=llm)

    def OpenAIFunctionsAgent(tools=tools, llm=llm, verbose=False):
        agent_kwargs = {
            "extra_prompt_messages": [MessagesPlaceholder(variable_name="memory")]
        }
        memory = ConversationBufferMemory(memory_key="memory", return_messages=True)
        
        # 見出しを作成
        prompt = f"""
        「{keyword}」で検索を行う読者の疑問や悩んでいることを解決するブログ記事を作りたい。
        その際に、上記の{keyword}でGoogle検索、Bing検索を行い、ブログを読む読者の疑問や悩んでいることを解決する目次（見出し構成）だけを作ってください。
        なお、その際は以下のルールにもとづいてください。
        
        ----------secret------------
        """

        memory.save_context({"input": prompt}, {"ouput": "understand!"})
        return initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=True,
            agent_kwargs=agent_kwargs,
            memory=memory,
        )

    agent_chain = OpenAIFunctionsAgent(tools=tools, llm=llm, verbose=True)

    agent_chain.run(input=keyword)

    midashi = agent_chain.memory.chat_memory.messages[3].content

    # 本文の作成
    prompt2 = f"""
    {midashi}
    提案頂いた上記の見出しに忠実に、それぞれの見出しごとに本文を書いてください。
    なお、その際は以下のルールにもとづいてください。
    
    ----------secret------------
    
    """
    answer = agent_chain.run(input=prompt2)
    t = t + 1
    sentence = sentence + " \n " + answer

    while t < 8 and "<FIN>" not in sentence:
        answer = agent_chain.run(input="同じルールで続き書いてください。文章もしくは<FIN>以外（返事など）は書かないでください。")
        sentence = sentence + answer

    # 左の空白を削除
    sentence = remove_indent_using_lstrip(sentence)

    # リード文の作成
    prompt3 = f"""
    上記の内容についてのリード文（導入文）を作成してください。なお、その際は以下のルールにもとづいてください。
    
    ----------secret------------

    """

    lead_sentence = agent_chain.run(input=prompt3)

    #------まとめ分の作成-------------------------------------

    prompt4 = """
    上記の内容に対して、まとめ文を300文字程度で書いてください。なお、その際は以下のルールにもとづいてください。
    
    ----------secret------------


    """

    close_sentence = agent_chain.run(input=prompt4)
    
    fullsentence = f""" {lead_sentence}
    {sentence}
    {close_sentence}"""

    fullsentence = remove_indent_using_lstrip(fullsentence)
    
    # タイトルの作成
    prompt5 = f"""
    上記の内容に対して、「{keyword}」のキーワードでSEOに強くなるようにタイトルをつけてください。
    その際には、見出しタグを付けないでください。
    """
    title = agent_chain.run(input=prompt5)

    # 文章の整形（文末に改行を2つ挿入）
    fullsentence = re.sub(r'。(?!\n\n)', '。\n\n', fullsentence)
    fullsentence = re.sub(r'？(?!」)', '？\n\n', fullsentence)

    updated_html = markdown(fullsentence)
    updated_html = updated_html.replace("<p><character>", fukidashi_left)
    updated_html = updated_html.replace("</character></p>", fukidashi_right)

    # 余分なインデントを削除
    updated_html = remove_indent_using_lstrip(updated_html)

    upload(title=title, sentence=updated_html, is_post=True)

def upload(title, sentence, is_post = False):
    
    # wordpressのアカウント情報をいれる。
    MY_URL: str = "wordpress-url"
    MY_USER: str = "wordpress-id"
    MY_APP_PASSWORD: str = "wordpress-app-passwordwordpress-url"

    credentials = MY_USER + ':' + MY_APP_PASSWORD
    token = base64.b64encode(credentials.encode())
    headers = {'Authorization': 'Basic ' + token.decode('utf-8')}

    status = None
    if is_post:
        status = 'publish'
    else:
        status = 'draft'

    post = {
        'title': title,
        'content': sentence,
        'status': status,  # draft=下書き、publish=公開　省略時はdraftになる
    }
    res = requests.post(f"{MY_URL}/wp-json/wp/v2/posts/", headers=headers, json=post)
    if res.ok:
        print("投稿の追加 成功 code:{res.status_code}")
    else:
        print(f"投稿の追加 失敗 code:{res.status_code} reason:{res.reason} msg:{res.text}")