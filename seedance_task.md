# 任务指令：使用火山引擎 Ark SDK 调用 Seedance 1.5 Pro 生成视频

## 1. 任务背景与目标

你需要配置环境并运行一段 Python 脚本，通过火山引擎的 Ark SDK 调用豆包·Seedance 1.5 Pro (`doubao-seedance-1-5-pro-251215`) 模型，完成“图文生视频”的异步任务，并轮询获取最终的视频结果。

## 2. 环境与前置准备

在运行代码之前，请务必完成以下检查：

1. **安装依赖**：检查当前 Python 环境是否已安装 Ark SDK。如果未安装，请在终端执行以下命令：
   `pip install 'volcengine-python-sdk[ark]'`

2. **配置环境变量**：调用该 API 需要火山引擎的 API Key。

   - 请检查环境变量 `ARK_API_KEY` 是否存在。

   - 如果不存在，请**主动询问我**提供 API Key，并在当前终端会话中设置它（或指导我写入 `.env` 文件并使用 `python-dotenv` 加载）。请不要在代码中硬编码任何伪造的 API Key。

## 3. 核心参考代码

请将以下代码保存为 `generate_video.py`。这是官方提供的标准调用与轮询逻辑：

```python
import os
import time  
from volcenginesdkarkruntime import Ark

# 初始化Ark客户端，从环境变量中读取 API Key
client = Ark(
    base_url="[https://ark.cn-beijing.volces.com/api/v3](https://ark.cn-beijing.volces.com/api/v3)",
    api_key=os.environ.get("ARK_API_KEY"),
)

if __name__ == "__main__":
    print("----- create request -----")
    create_result = client.content_generation.tasks.create(
        model="doubao-seedance-1-5-pro-251215", 
        content=[
            {
                "type": "text",
                "text": "无人机以极快速度穿越复杂障碍或自然奇观，带来沉浸式飞行体验  --duration 5 --camerafixed false --watermark true"
            },
            { 
                "type": "image_url",
                "image_url": {
                    "url": "[https://ark-project.tos-cn-beijing.volces.com/doc_image/seepro_i2v.png](https://ark-project.tos-cn-beijing.volces.com/doc_image/seepro_i2v.png)" 
                }
            }
        ]
    )
    print(create_result)

    # 轮询查询部分
    print("----- polling task status -----")
    task_id = create_result.id
    while True:
        get_result = client.content_generation.tasks.get(task_id=task_id)
        status = get_result.status
        if status == "succeeded":
            print("----- task succeeded -----")
            print(get_result)
            break
        elif status == "failed":
            print("----- task failed -----")
            print(f"Error: {get_result.error}")
            break
        else:
            print(f"Current status: {status}, Retrying after 3 seconds...")
            time.sleep(3)
```

## 4. 执行步骤与期望输出

请严格按照以下步骤执行：

1. **审查并保存**：读取上述代码并将其保存到工作目录中。

2. **执行脚本**：运行 `python generate_video.py`。

3. **耐心等待轮询**：视频生成模型耗时较长（可能需要几分钟）。在控制台打印 `Retrying after 3 seconds...` 时，**请保持进程运行，不要中断**，直到状态变为 `succeeded` 或 `failed`。

4. **解析并展示结果**：

   - 如果任务成功，请从返回的 JSON/对象中解析出**视频的直接下载 URL**，并用 Markdown 格式清楚地打印出来。

   - 如果任务失败，请提取具体的报错信息进行分析，并告诉我需要如何修改。

