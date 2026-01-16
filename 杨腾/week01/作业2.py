import jieba # 中文分词用途
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer # 词频统计
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

dataset = pd.read_csv("dataset.csv", sep="\t", header=None, nrows=200)
print(dataset.head(10))

# 提取 文本的特征 tfidf， dataset[0]
# 构建一个模型 knn， 学习 提取的特征和 标签 dataset[1] 的关系
# 预测，用户输入的一个文本，进行预测结果
input_sententce = dataset[0].apply(lambda x: " ".join(jieba.lcut(x))) # sklearn对中文处理

vector = CountVectorizer() # 对文本进行提取特征 默认是使用标点符号分词， 不是模型
vector.fit(input_sententce.values) # 统计词表
input_feature = vector.transform(input_sententce.values) # 100 * 词表大小

# 朴素贝叶斯模型训练
model1 = MultinomialNB()
model1.fit(input_feature, dataset[1].values)
print(model1)

# 线性SVM模型训练
model2 = LinearSVC()
model2.fit(input_feature, dataset[1].values)
print(model2)

# 模型推理
test_query = "快帮我播放周杰伦的稻香"
test_sentence = " ".join(jieba.lcut(test_query))
test_feature = vector.transform([test_sentence])
print("待预测的文本", test_query)
print("朴素贝叶斯模型预测结果: ", model1.predict(test_feature))
print("线性SVM模型预测结果: ", model1.predict(test_feature))


