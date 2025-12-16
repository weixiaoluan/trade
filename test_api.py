#!/usr/bin/env python3
"""
简单测试脚本 - 验证 API 连接
"""

import os
from dotenv import load_dotenv
load_dotenv()

def test_siliconflow_api():
    """测试硅基流动 API"""
    print("=" * 50)
    print("测试硅基流动 DeepSeek-R1 API 连接")
    print("=" * 50)
    
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("❌ SILICONFLOW_API_KEY 未设置")
        return False
    
    print(f"✅ API Key 已配置: {api_key[:20]}...")
    
    # 使用 OpenAI 客户端测试
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1"
        )
        
        print("\n发送测试请求...")
        
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1",
            messages=[
                {"role": "user", "content": "你好，请简单介绍一下自己，用一句话回答。"}
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        print(f"\n✅ API 响应成功!")
        print(f"模型回复: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"\n❌ API 调用失败: {e}")
        return False


def test_autogen_basic():
    """测试 AutoGen 基本功能"""
    print("\n" + "=" * 50)
    print("测试 AutoGen 基本功能")
    print("=" * 50)
    
    try:
        import autogen
        from autogen import AssistantAgent, UserProxyAgent
        
        print(f"✅ AutoGen 版本: {autogen.__version__}")
        
        # 配置 LLM
        api_key = os.getenv("SILICONFLOW_API_KEY")
        
        config_list = [{
            "model": "deepseek-ai/DeepSeek-R1",
            "api_key": api_key,
            "base_url": "https://api.siliconflow.cn/v1",
        }]
        
        llm_config = {
            "config_list": config_list,
            "temperature": 0.3,
            "timeout": 120,
        }
        
        # 创建简单的 Agent
        assistant = AssistantAgent(
            name="Assistant",
            system_message="你是一个有帮助的助手。",
            llm_config=llm_config,
        )
        
        user_proxy = UserProxyAgent(
            name="User",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
            code_execution_config=False,
        )
        
        print("✅ Agent 创建成功")
        
        # 简单对话测试
        print("\n发起简单对话...")
        user_proxy.initiate_chat(
            assistant,
            message="你好！请用一句话介绍证券分析。",
        )
        
        print("\n✅ AutoGen 对话测试成功!")
        return True
        
    except Exception as e:
        print(f"\n❌ AutoGen 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧪 开始 API 连接测试\n")
    
    # 测试 API
    api_ok = test_siliconflow_api()
    
    if api_ok:
        # 测试 AutoGen
        test_autogen_basic()
    else:
        print("\n⚠️ 请先修复 API 连接问题")
