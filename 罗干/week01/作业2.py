import pandas as pd
import jieba
from sklearn.feature_extraction.text import CountVectorizer # 词频统计
from sklearn.neighbors import KNeighborsClassifier # KNN
from openai import OpenAI

dataset = pd.read_csv("dataset.csv", sep="\t", header=None, nrows=10000)
# print(dataset[1].value_counts())
input_sententce = dataset[0].apply(lambda x: " ".join(jieba.lcut(x)))  # sklearn对中文处理
print("input_sententce: ", input_sententce)
print("dataset[0]: ", dataset[0])
vector = CountVectorizer()  # 对文本进行提取特征 默认是使用标点符号分词
vector.fit(input_sententce.values)  # 统计词表
input_feature = vector.transform(input_sententce.values)  # 进行转换 100 * 词表大小

model = KNeighborsClassifier()
model.fit(input_feature, dataset[1].values)


client = OpenAI(
    api_key="sk-b8d6efe8169b4351a91a13b8fe8fd99a", # 账号绑定，用来计费的
    # 大模型阿里云
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def text_calssify_using_ml(text: str) -> str:
    """
    文本分类（机器学习），输入文本完成类别划分
    """
    test_sentence = " ".join(jieba.lcut(text))
    test_feature = vector.transform([test_sentence])
    print(test_feature, '++++', test_sentence, " ".join(jieba.lcut(text)))
    return model.predict(test_feature)[0]


def text_calssify_using_llm(text: str) -> str:
    """
    文本分类（大语言模型），输入文本完成类别划分
    """
    completion = client.chat.completions.create(
        model="qwen-flash",  # 模型的代号
        messages=[
            {"role": "user", "content": f"""帮我进行文本分类：{text}
                输出的类别只能从如下中进行选择，请给出最合适的类别;注意:只输出下面选项的值,不需要加工输出多余的字符。
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
                """},
        ]
    )
    return completion.choices[0].message.content


if __name__ == "__main__":
    print("机器学习: ", text_calssify_using_ml("播放刘德华的歌曲"))
    print("大语言模型: ", text_calssify_using_llm("播放刘德华的歌曲"))
