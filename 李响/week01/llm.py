
from openai import OpenAI

client = OpenAI(
    api_key="sk-6f04889b11624d61874f5e51e247692d",

    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
def text_classify_using_llm(text: str) -> str:
    completion = client.chat.completions.create(
        model="qwen-flash",
        messages=[
            {"role": "system", "content": """请根据输入的文本内容进行分类:[text]
            分类结果只能从下面选择
            Video-Play               
            FilmTele-Play            
            Music-Play              
            Radio-Listen             
            Alarm-Update             
            Travel-Query            
            HomeAppliance-Control    
            Weather-Query            
            Calendar-Query           
            TVProgram-Play            
            Audio-Play                
            Other  。"""},

        ]
    )
print("LLM:",text_classify_using_llm("帮我导航到小吃街"))
