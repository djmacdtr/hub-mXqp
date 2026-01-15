import pandas as pd

from pathlib import Path
'''
由于在实际操作过程中遇到问题：运行fastapi时填写文件路径：Week01/homework/dataset.csv，成功运行；
但后续编写main函数直接运行脚本时，却提示找不到csv文件文件。
经过排查发现原因：python xxx.py 和 uvicorn xxx:app 启动时的“当前工作目录不一样”
所以同一个相对路径，在两种启动方式下指向了不同的位置。
解决方案：使用 Path(__file__).resolve().parent 获取当前脚本所在目录， 然后再拼接上 dataset.csv
从而确保无论在哪种启动方式下， 都能正确找到数据集文件。
'''
BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset.csv"
# 读取数据集
# read_csv 函数用于读取csv文件， sep参数指定分隔符， header=None表示没有表头， nrows=10000表示只读取前0000行 , 全部读取使用 nrows=None
dataset = pd.read_csv(DATASET_PATH, sep="\t", header=None, nrows=None)
# 输出类别分布 dataset[1]表示第二列， value_counts() 统计每个类别的数量
print(dataset[1].value_counts())

import jieba

# 对文本进行分词处理， jieba.lcut(x) 对每个文本进行分词， 返回一个列表， " ".join() 将列表转换为字符串， 空格分隔
input_sententce = dataset[0].apply(lambda x: " ".join(jieba.lcut(x))) # 这里使用空格连接分词结果， 因为 sklearn 的 CountVectorizer 默认使用空格分词


from sklearn.feature_extraction.text import CountVectorizer
# 创建一个词频统计器
vector = CountVectorizer()
# 统计词表 这一步是构建词典，相当于java中的索引建立 Map<String, Integer> vocab = new HashMap<>();
vector.fit(input_sententce.values)
# 将文本转换为特征向量， 每行表示一个样本， 每列表示一个词在该样本中的出现次数
input_feature = vector.transform(input_sententce.values) # (样本数, 词表大小) 的稀疏矩阵 ，这是稀疏矩阵，因为大多数词在一句话里不会出现。


from sklearn.neighbors import KNeighborsClassifier

# 创建一个KNN分类器
model = KNeighborsClassifier()
# 训练模型， 使用特征向量和对应的标签进行训练
model.fit(input_feature, dataset[1].values)

# 准备测试文本
test_sentence = "帮我放一首周杰伦的歌"
# 对测试文本进行分词处理
test_sentence = " ".join(jieba.lcut(test_sentence))
# 将测试文本转换为特征向量
test_feature = vector.transform([test_sentence])
# 使用训练好的模型进行预测
prediction = model.predict(test_feature)
# 输出预测结果
print("机器学习模型预测结果:", prediction[0])  #predict 返回的是数组，因为它支持批量预测。

'''
! 总结 ： 1. 数据读取和预处理： 使用 pandas 读取数据集， 使用 jieba 进行中文分词， 使用 CountVectorizer 提取文本特征。
2. 模型训练： 使用 KNeighborsClassifier 进行文本分类模型的训练。
3. 模型预测： 对新的文本进行分词和特征提取， 使用训练好的模型进行预测分类。
'''


from fastapi import FastAPI
# 创建 FastAPI 应用对象
app = FastAPI()
# 定义接口处理函数
def classify_ml(text: str) -> str:
    """
    机器学习文本分类核心逻辑
    """
    sentence = " ".join(jieba.lcut(text))
    feature = vector.transform([sentence])
    return model.predict(feature)[0]

@app.get("/text-cls/ml")
def text_calssify_using_ml(text: str) -> str:
    """
    文本分类（机器学习），输入文本完成类别划分
    """
    return classify_ml(text)
# fastapi run Week01/homework/文本分类_作业.py --reload
# 或者使用uvicorn uvicorn Week01/homework/文本分类_作业:app --reload  两者的区别在于前者是fastapi自带的命令行工具，后者是使用uvicorn作为ASGI服务器来运行FastAPI应用。
# --reload 参数表示代码修改后自动重启服务，适合开发环境使用。
# http://127.0.0.1:8000/text-cls/ml?text=%E5%B8%AE%E6%88%91%E6%94%BE%E4%B8%80%E9%A6%96%E5%91%A8%E6%9D%B0%E4%BC%A6%E7%9A%84%E6%AD%8C


from openai import OpenAI
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()
# 创建 OpenAI 客户端对象
client = OpenAI(
    # 安全起见，使用环境变量来存储 API Key 和 URL  配置在 .env 文件中
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # 大模型厂商的地址，阿里云
    base_url=os.getenv("DASHSCOPE_API_URL"),
)

# 定义接口处理函数
def calssify_llm(text: str) -> str:
    """
    大语言模型文本分类核心逻辑
    """
    completion = client.chat.completions.create(
        model="qwen-flash",  # 模型的代号

        messages=[
            {"role": "user", "content": f"""帮我进行文本分类：{text}

        输出的类别只能从如下中进行选择， 除了类别之外下列的类别，请给出最合适的类别。
        FilmTele-Play            
        Video-Play               
        Music-Play              
        Radio-Listen           
        Alarm-Update        
        Travel-Query        
        HomeAppliance-Control  
        Weather-Query          
        Calendar-Query      
        TVProgram-Play      
        Audio-Play       
        Other             
        """},  # 用户的提问
        ]
    )
    return completion.choices[0].message.content

@app.get("/text-cls/llm")
def text_calssify_using_llm(text: str) -> str:
    """
    文本分类（大语言模型），输入文本完成类别划分
    """
    return calssify_llm(text)
# http://127.0.0.1:8000/text-cls/llm?text=%E6%88%91%E8%A6%81%E5%9B%9E%E5%AE%B6


def main():
    test_cases = [
        "帮我放一首周杰伦的歌",
        "明天北京天气怎么样",
        "设置一个明早7点的闹钟",
        "我要回家"
    ]

    for text in test_cases:
        ml_result = classify_ml(text)
        llm_result = calssify_llm(text)

        print("=" * 40)
        print("输入文本:", text)
        print("ML  预测结果:", ml_result)
        print("LLM 预测结果:", llm_result)

if __name__ == "__main__":
    main()
