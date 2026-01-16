# pandas 对数据集进行有效的存储、展示、分析
#scikit-learn 简称：sklearn，非常重要
# sklearn 适合单机开发的机器学习
# pytorch 适合深度学习的搭建模型和训练模型
# jieba 分割词，中文分词
# fit()：拟合语料，构建全局词汇表 (1)fit 是 sklearn 通用方法(2)训练模型
# transform()：转换文本，生成词频矩阵
import pandas as pd
import jieba
from openai import OpenAI

from sklearn import linear_model # 线性模型模块
from sklearn import tree # 决策树模块
from sklearn import datasets # 加载数据集
from sklearn.model_selection import train_test_split # 数据集划分
from sklearn import neighbors
from sklearn.neighbors import KNeighborsClassifier #KNN模型
from sklearn.feature_extraction.text import CountVectorizer #词频统计

# ----------------------特征提取---------------------------------------------
datasets = pd.read_csv('dataset.csv', sep="\t", names=['text', 'label'], nrows=100)
input_s = datasets['text'].apply(lambda x: " ".join(jieba.lcut(x))) #定义匿名函数，x 是函数的唯一参数 apply() 收集并组成新的序列
vectorizer = CountVectorizer()
vectorizer.fit(input_s.values) #构建全局词汇表
#  transform 可以接收「数组 / Series / 列表」这类可迭代的文本序列.values 是把 Series 转换成 numpy 数组
feature_data = vectorizer.transform(input_s.values) #生成词频矩阵
# ------模型训练---
model = KNeighborsClassifier()
model.fit(feature_data, datasets['label'].values)
print(f"再次打印{model}")
print(datasets['label'].value_counts())
# ------------------------------------------------------------------------------------------------
client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    # https://bailian.console.aliyun.com/?tab=model#/api-key
    api_key="sk-e78359f2d45xxxxxx059f99575", # 账号绑定，用来计费的

    # 大模型厂商的地址，阿里云
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def classy_using_ml(test_query):
    # 机器学习
    # ------模型推理-------
    test_s = " ".join(jieba.lcut(test_query))
    # 括号 [test_s] 包装成 列表，这样才能符合方法的输入格式要求。
    test_feature = vectorizer.transform([test_s])
    return model.predict(test_feature)[0]
    # ----------------------------------------------------------------
def classy_using_llm(test_query):
    # 大语言学习
    completion = client.chat.completions.create(
        model="qwen-flash",
        messages=[
            {'role':'user',
             'content': f'''
                帮我进行文本分类：{test_query}
                输出的类别只能从下面选
                Video-Play     
                Radio-Listen             
                HomeAppliance-Control   
                Music-Play              
                FilmTele-Play            
                Alarm-Update             
                Calendar-Query         
                Travel-Query            
                Weather-Query'''}]
    )
    return completion.choices[0].message.content

if __name__ == '__main__':
    print(f"机器学习{classy_using_ml("帮我播放音乐")}")
    print(f"大语言学习{classy_using_llm("帮我播放音乐")}")
