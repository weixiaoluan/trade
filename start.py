#!/usr/bin/env python3
"""
============================================
智能证券分析系统 - 简化启动脚本
============================================
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from config import get_llm_config, APIConfig

console = Console()


def print_banner():
    """打印启动横幅"""
    provider = APIConfig.DEFAULT_LLM_PROVIDER
    llm_name = "SiliconFlow DeepSeek-R1" if provider == "siliconflow" else "Google Gemini Pro"
    
    console.print(f"""
[bold cyan]╔═══════════════════════════════════════════════════════════════╗
║     🤖 智能多维度证券分析系统 v1.0                           ║
╠═══════════════════════════════════════════════════════════════╣
║  框架: Microsoft AutoGen                                      ║
║  LLM:  {llm_name:<46}║
║  数据: yfinance + 权威财经新闻                                ║
╚═══════════════════════════════════════════════════════════════╝[/bold cyan]
    """)


def run_analysis(ticker: str):
    """运行证券分析"""
    from agents.agents_simple import create_simple_agents
    
    console.print(f"\n[green]▶ 分析标的: {ticker}[/green]\n")
    
    # 获取 LLM 配置
    llm_config = get_llm_config()
    
    # 创建 Agent
    console.print("[yellow]初始化 Agent...[/yellow]")
    agents = create_simple_agents(llm_config)
    console.print("[green]✅ Agent 就绪[/green]\n")
    
    # 构建分析任务
    task = f"""
请对以下标的进行全面的证券分析：

**标的**: {ticker}

请按照以下步骤进行分析，并在每一步调用相应的工具函数：

**步骤 1**: 获取行情数据
- 调用 get_stock_data("{ticker}", "1y", "1d") 获取1年的日线数据

**步骤 2**: 获取基本面信息  
- 调用 get_stock_info("{ticker}") 获取公司基本信息

**步骤 3**: 技术分析
- 将步骤1获取的数据传入 calculate_all_indicators() 计算技术指标
- 调用 analyze_trend() 分析趋势
- 调用 get_support_resistance_levels() 获取支撑阻力位

**步骤 4**: 生成报告
- 综合以上分析，生成包含8个时间周期预测的完整投资报告

开始分析。
"""
    
    console.print("[bold]🚀 开始多维度证券分析...[/bold]\n")
    console.print("-" * 60)
    
    # 启动分析
    agents["user_proxy"].initiate_chat(
        agents["assistant"],
        message=task,
    )
    
    console.print("\n" + "=" * 60)
    console.print("[bold green]✅ 分析完成![/bold green]")


def main():
    print_banner()
    
    # 验证 API
    try:
        APIConfig.validate()
        provider = APIConfig.DEFAULT_LLM_PROVIDER
        if provider == "siliconflow":
            console.print("[green]✅ 硅基流动 API Key 已配置[/green]")
        else:
            console.print("[green]✅ Google Gemini API Key 已配置[/green]")
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return
    
    console.print()
    console.print("=" * 60)
    console.print("[bold cyan]输入要分析的股票代码 (如 AAPL, TSLA, SPY, 600519)[/bold cyan]")
    console.print("输入 'quit' 退出")
    console.print("=" * 60)
    
    while True:
        try:
            ticker = console.input("\n[yellow]请输入股票代码 > [/yellow]").strip()
            
            if not ticker:
                continue
            
            if ticker.lower() in ["quit", "exit", "q"]:
                console.print("\n[cyan]再见! 👋[/cyan]")
                break
            
            run_analysis(ticker.upper())
            
        except KeyboardInterrupt:
            console.print("\n\n[cyan]已中断，输入新代码或 quit 退出[/cyan]")
        except Exception as e:
            console.print(f"\n[red]❌ 错误: {e}[/red]")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
