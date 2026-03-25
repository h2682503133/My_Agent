import openviking as ov

# 【全局初始化】整个程序生命周期只运行一次
ov.initialize(
    storage_path="./ov_data",  # 所有数据存在这
    embedding_model="auto"     # 自动下载向量模型
)