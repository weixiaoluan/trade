#!/usr/bin/env python3
"""
============================================
智能多维度证券分析系统
Smart Multi-Dimensional Securities Analysis System

基于 Microsoft AutoGen 框架的多智能体协同分析系统
使用 Google Gemini Pro API 进行复杂推理

Author: AI-Trade Team
Version: 1.0.0
============================================
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入项目模块
from config import get_llm_config, APIConfig, SystemConfig
from agents import create_all_agents
from workflow import run_security_analysis, create_analysis_group_chat

# Rich Console 用于美化输出
console = Console()


def print_banner():
    """打印启动横幅"""
    # 根据配置显示当前 LLM
    provider = APIConfig.DEFAULT_LLM_PROVIDER
    if provider == "siliconflow":
        llm_name = "SiliconFlow DeepSeek-R1"
    else:
        llm_name = "Google Gemini Pro"
    
    banner = f"""
╔═══════════════════════════════════════════════════════════════╗
║     🤖 智能多维度证券分析系统 v1.0                           ║
║     Smart Multi-Dimensional Securities Analysis System        ║
╠═══════════════════════════════════════════════════════════════╣
║  框架: Microsoft AutoGen                                      ║
║  LLM:  {llm_name:<40}      ║
║  数据: yfinance + 权威财经新闻                                ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def validate_environment():
    """验证运行环境"""
    console.print("\n[yellow]▶ 验证运行环境...[/yellow]")
    
    try:
        # 检查 API Key
        APIConfig.validate()
        provider = APIConfig.DEFAULT_LLM_PROVIDER
        if provider == "siliconflow":
            console.print("  ✅ 硅基流动 API Key 已配置 (DeepSeek-R1)")
        else:
            console.print("  ✅ Google Gemini API Key 已配置")
    except ValueError as e:
        console.print(f"  ❌ {e}", style="red")
        return False
    
    # 检查必要的依赖
    required_packages = ["autogen", "yfinance", "pandas", "requests", "bs4"]
    missing = []
    
    for pkg in required_packages:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    
    if missing:
        console.print(f"  ❌ 缺少依赖包: {', '.join(missing)}", style="red")
        console.print("  请运行: pip install -r requirements.txt")
        return False
    
    console.print("  ✅ 所有依赖已安装")
    console.print("  ✅ 环境验证通过\n")
    return True


def run_interactive_mode():
    """交互模式 - 持续接收用户输入"""
    print_banner()
    
    if not validate_environment():
        return
    
    console.print("[green]▶ 初始化 Agent 系统...[/green]")
    
    try:
        # 获取 LLM 配置
        llm_config = get_llm_config()
        
        # 创建所有 Agent
        agents = create_all_agents(llm_config)
        console.print("  ✅ 6个 Agent 已创建:")
        console.print("     • User_Proxy (用户代理)")
        console.print("     • Data_Engineer (数据工程师)")
        console.print("     • Data_Verifier (数据审计员)")
        console.print("     • Technical_Analyst (技术分析师)")
        console.print("     • Fundamental_Analyst (基本面分析师)")
        console.print("     • Chief_Investment_Officer (首席投资官)")
        
    except Exception as e:
        console.print(f"  ❌ Agent 初始化失败: {e}", style="red")
        return
    
    console.print("\n" + "="*60)
    console.print("[bold cyan]系统就绪! 请输入要分析的股票/ETF/基金代码或名称[/bold cyan]")
    console.print("示例: AAPL, 苹果, SPY, 600519, 贵州茅台")
    console.print("输入 'quit' 或 'exit' 退出系统")
    console.print("="*60 + "\n")
    
    while True:
        try:
            # 获取用户输入
            user_input = console.input("[bold yellow]请输入分析标的 > [/bold yellow]").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["quit", "exit", "q"]:
                console.print("\n[cyan]感谢使用，再见! 👋[/cyan]")
                break
            
            # 开始分析
            console.print(f"\n[green]▶ 开始分析: {user_input}[/green]\n")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Agent 协作分析中...", total=None)
                
                # 运行分析
                messages = run_security_analysis(
                    agents=agents,
                    security_input=user_input,
                    max_round=SystemConfig.MAX_ROUNDS,
                )
                
                progress.update(task, description="分析完成!")
            
            # 提取并显示报告
            console.print("\n" + "="*60)
            console.print("[bold green]📊 分析报告[/bold green]")
            console.print("="*60 + "\n")
            
            # 查找 CIO 的最终报告
            final_report = None
            for msg in reversed(messages):
                if isinstance(msg, dict):
                    name = msg.get("name", "")
                    content = msg.get("content", "")
                    if name == "Chief_Investment_Officer" and content and "投资" in content:
                        final_report = content
                        break
            
            if final_report:
                # 使用 Rich 渲染 Markdown
                md = Markdown(final_report)
                console.print(md)
                
                # 保存报告
                from workflow.group_chat import save_report
                report_path = save_report(final_report, user_input)
                console.print(f"\n[dim]报告已保存至: {report_path}[/dim]")
            else:
                # 显示对话历史
                console.print("[yellow]未能生成完整报告，显示分析过程:[/yellow]\n")
                for msg in messages[-10:]:
                    if isinstance(msg, dict):
                        name = msg.get("name", "Unknown")
                        content = msg.get("content", "")
                        if content:
                            console.print(f"[bold]{name}:[/bold]")
                            console.print(content[:1000] + ("..." if len(content) > 1000 else ""))
                            console.print()
            
            console.print("\n" + "="*60 + "\n")
            
        except KeyboardInterrupt:
            console.print("\n\n[cyan]分析已中断，输入新标的或 'quit' 退出[/cyan]")
            continue
        except Exception as e:
            console.print(f"\n[red]❌ 分析过程出错: {e}[/red]")
            console.print("[dim]请检查网络连接和 API Key 配置[/dim]\n")
            continue


def run_single_analysis(security: str):
    """单次分析模式"""
    print_banner()
    
    if not validate_environment():
        return
    
    console.print(f"[green]▶ 分析标的: {security}[/green]\n")
    
    try:
        llm_config = get_llm_config()
        agents = create_all_agents(llm_config)
        
        messages = run_security_analysis(
            agents=agents,
            security_input=security,
            max_round=SystemConfig.MAX_ROUNDS,
        )
        
        # 输出结果
        for msg in messages:
            if isinstance(msg, dict):
                name = msg.get("name", "")
                content = msg.get("content", "")
                if name == "Chief_Investment_Officer" and content:
                    print(content)
                    break
        
    except Exception as e:
        console.print(f"[red]分析失败: {e}[/red]")
        sys.exit(1)


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="智能多维度证券分析系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                    # 交互模式
  python main.py --analyze AAPL     # 分析苹果公司
  python main.py --analyze SPY      # 分析 SPY ETF
  python main.py --analyze 600519   # 分析贵州茅台
        """
    )
    
    parser.add_argument(
        "--analyze", "-a",
        type=str,
        help="要分析的股票/ETF/基金代码或名称"
    )
    
    parser.add_argument(
        "--max-rounds", "-r",
        type=int,
        default=20,
        help="最大对话轮次 (默认: 20)"
    )
    
    args = parser.parse_args()
    
    # 更新配置
    if args.max_rounds:
        SystemConfig.MAX_ROUNDS = args.max_rounds
    
    if args.analyze:
        # 单次分析模式
        run_single_analysis(args.analyze)
    else:
        # 交互模式
        run_interactive_mode()


if __name__ == "__main__":
    main()
