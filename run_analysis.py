#!/usr/bin/env python3
"""
============================================
简化版证券分析启动脚本
适用于快速测试和调试
============================================
"""

import os
import sys
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


def quick_analysis(ticker: str):
    """
    快速分析单个标的
    
    使用方法:
        python run_analysis.py AAPL
        python run_analysis.py 600519
    """
    print(f"\n{'='*60}")
    print(f"🔍 开始分析: {ticker}")
    print(f"{'='*60}\n")
    
    # 1. 检查 API Key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ 错误: GOOGLE_API_KEY 未设置")
        print("请在 .env 文件中配置: GOOGLE_API_KEY=your_key")
        return
    
    print("✅ API Key 已配置")
    
    # 2. 导入模块
    try:
        from config import get_llm_config
        from agents import create_all_agents
        from workflow import run_security_analysis
        print("✅ 模块导入成功")
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        print("请确保已安装依赖: pip install -r requirements.txt")
        return
    
    # 3. 初始化 Agent
    print("\n📦 初始化 Agent 系统...")
    try:
        llm_config = get_llm_config()
        agents = create_all_agents(llm_config)
        print("✅ 6个 Agent 已就绪")
    except Exception as e:
        print(f"❌ Agent 初始化失败: {e}")
        return
    
    # 4. 运行分析
    print(f"\n🚀 启动多 Agent 协作分析...")
    print("   (此过程可能需要几分钟，请耐心等待)\n")
    
    try:
        messages = run_security_analysis(
            agents=agents,
            security_input=ticker,
            max_round=20,
        )
        
        print("\n" + "="*60)
        print("📊 分析完成! 结果如下:")
        print("="*60 + "\n")
        
        # 输出对话历史中的关键信息
        for msg in messages:
            if isinstance(msg, dict):
                name = msg.get("name", "")
                content = msg.get("content", "")
                
                # 只显示关键 Agent 的输出
                if name in ["Chief_Investment_Officer", "Technical_Analyst", "Fundamental_Analyst"]:
                    if content and len(content) > 50:
                        print(f"\n{'='*40}")
                        print(f"📝 {name}")
                        print(f"{'='*40}")
                        print(content)
        
    except Exception as e:
        print(f"❌ 分析过程出错: {e}")
        import traceback
        traceback.print_exc()


def test_tools():
    """测试工具函数是否正常工作"""
    print("\n🧪 测试工具函数...")
    
    from tools.data_fetcher import get_stock_data, get_stock_info, search_ticker
    from tools.technical_analysis import calculate_all_indicators
    import json
    
    # 测试 ticker 搜索
    print("\n1. 测试 search_ticker('AAPL')...")
    result = search_ticker("AAPL")
    print(f"   结果: {result[:100]}...")
    
    # 测试行情数据
    print("\n2. 测试 get_stock_data('AAPL', '3mo')...")
    data = get_stock_data("AAPL", "3mo", "1d")
    data_dict = json.loads(data)
    if data_dict.get("status") == "success":
        print(f"   ✅ 获取到 {data_dict.get('data_points')} 条数据")
        print(f"   最新价: ${data_dict.get('summary', {}).get('latest_price')}")
    else:
        print(f"   ❌ 获取失败: {data_dict.get('message')}")
    
    # 测试技术指标
    print("\n3. 测试技术指标计算...")
    indicators = calculate_all_indicators(data)
    ind_dict = json.loads(indicators)
    if ind_dict.get("status") == "success":
        print(f"   ✅ RSI: {ind_dict.get('indicators', {}).get('rsi', {}).get('value')}")
        print(f"   ✅ MACD 趋势: {ind_dict.get('indicators', {}).get('macd', {}).get('trend')}")
    else:
        print(f"   ❌ 计算失败")
    
    print("\n✅ 工具测试完成!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--test":
            test_tools()
        else:
            quick_analysis(arg)
    else:
        print("使用方法:")
        print("  python run_analysis.py AAPL      # 分析苹果公司")
        print("  python run_analysis.py SPY       # 分析 SPY ETF")
        print("  python run_analysis.py 600519    # 分析贵州茅台")
        print("  python run_analysis.py --test    # 测试工具函数")
