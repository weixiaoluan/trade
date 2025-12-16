"""
============================================
GroupChat 工作流编排模块
管理多 Agent 协作的证券分析流程
============================================

工作流设计:
1. User_Proxy 发起分析任务
2. Data_Engineer 收集数据 (行情 + 基本面 + 新闻)
3. Data_Verifier 验证数据权威性和时效性
4. 如果验证不通过 → 返回步骤2重新收集
5. Technical_Analyst 进行技术分析
6. Fundamental_Analyst 进行基本面分析
7. Chief_Investment_Officer 汇总生成最终报告
8. User_Proxy 输出报告给用户
"""

import autogen
from autogen import GroupChat, GroupChatManager
from typing import Dict, List, Optional, Callable
import json
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config import SystemConfig


def custom_speaker_selection(
    last_speaker: autogen.Agent,
    groupchat: GroupChat,
) -> Optional[autogen.Agent]:
    """
    自定义发言者选择逻辑
    
    实现分析工作流:
    User_Proxy → Data_Engineer → Data_Verifier → (如验证失败返回 Data_Engineer)
                                               → Technical_Analyst → Fundamental_Analyst
                                               → Chief_Investment_Officer → User_Proxy (结束)
    """
    messages = groupchat.messages
    agents = {agent.name: agent for agent in groupchat.agents}
    
    if not messages:
        return agents.get("Data_Engineer")
    
    last_message = messages[-1]
    last_content = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
    last_name = last_speaker.name
    
    # 检查是否有工具调用需要执行
    if "tool_calls" in last_message or "function_call" in last_message:
        return agents.get("User_Proxy")  # User_Proxy 执行工具
    
    # 根据上一个发言者决定下一个
    if last_name == "User_Proxy":
        # 检查是否是工具执行结果
        if "tool_responses" in str(last_message) or last_content.startswith("{"):
            # 工具执行完成，返回给调用工具的 Agent
            for i in range(len(messages) - 2, -1, -1):
                prev_msg = messages[i]
                if "tool_calls" in prev_msg or "function_call" in prev_msg:
                    prev_name = prev_msg.get("name", "")
                    if prev_name in agents:
                        return agents[prev_name]
            return agents.get("Data_Engineer")
        else:
            # 用户输入，开始数据收集
            return agents.get("Data_Engineer")
    
    elif last_name == "Data_Engineer":
        # 数据收集完成，交给验证员
        return agents.get("Data_Verifier")
    
    elif last_name == "Data_Verifier":
        # 检查验证结果
        if "REJECTED" in last_content or "打回" in last_content or "重新获取" in last_content:
            # 验证失败，返回 Data_Engineer 重新收集
            return agents.get("Data_Engineer")
        elif "APPROVED" in last_content or "通过" in last_content:
            # 验证通过，进入技术分析
            return agents.get("Technical_Analyst")
        else:
            # 默认进入技术分析
            return agents.get("Technical_Analyst")
    
    elif last_name == "Technical_Analyst":
        # 技术分析完成，进入基本面分析
        return agents.get("Fundamental_Analyst")
    
    elif last_name == "Fundamental_Analyst":
        # 基本面分析完成，CIO 汇总
        return agents.get("Chief_Investment_Officer")
    
    elif last_name == "Chief_Investment_Officer":
        # 报告生成完成
        return agents.get("User_Proxy")  # 结束
    
    # 默认返回 None 让 GroupChat 自动选择
    return None


def create_analysis_group_chat(
    agents: Dict[str, autogen.Agent],
    max_round: int = 20,
) -> tuple:
    """
    创建证券分析 GroupChat
    
    Args:
        agents: Agent 字典
        max_round: 最大对话轮次
    
    Returns:
        (GroupChat, GroupChatManager)
    """
    # 获取 Agent 列表 (按工作流顺序)
    agent_list = [
        agents["user_proxy"],
        agents["data_engineer"],
        agents["data_verifier"],
        agents["technical_analyst"],
        agents["fundamental_analyst"],
        agents["chief_investment_officer"],
    ]
    
    # 创建 GroupChat
    groupchat = GroupChat(
        agents=agent_list,
        messages=[],
        max_round=max_round,
        speaker_selection_method=custom_speaker_selection,
        allow_repeat_speaker=True,  # 允许同一 Agent 连续发言 (用于工具调用)
    )
    
    # 创建 GroupChatManager
    # 注意: Manager 使用与其他 Agent 相同的 LLM 配置
    manager_llm_config = agents["data_engineer"].llm_config
    
    manager = GroupChatManager(
        groupchat=groupchat,
        llm_config=manager_llm_config,
        system_message="""你是证券分析工作流管理器。
你的职责是协调各 Agent 按正确顺序完成分析任务。

工作流顺序:
1. Data_Engineer: 收集数据
2. Data_Verifier: 验证数据 (如不通过，返回步骤1)
3. Technical_Analyst: 技术分析
4. Fundamental_Analyst: 基本面分析
5. Chief_Investment_Officer: 生成最终报告

确保每个步骤完成后才进入下一步。
""",
    )
    
    return groupchat, manager


def format_initial_task(
    security_input: str,
    additional_context: str = ""
) -> str:
    """
    格式化初始分析任务消息
    
    Args:
        security_input: 用户输入的证券代码或名称
        additional_context: 额外上下文信息
    
    Returns:
        格式化的任务消息
    """
    task_message = f"""
# 证券分析任务

## 分析标的
用户输入: **{security_input}**

## 任务要求
请对上述标的进行全面的多维度分析，包括:

1. **数据收集** (Data_Engineer):
   - 获取最新行情数据 (至少1年历史)
   - 获取公司/ETF 基本信息
   - 获取财务报表数据
   - 搜索权威财经新闻

2. **数据验证** (Data_Verifier):
   - 验证所有数据来源的权威性
   - 检查数据时效性
   - 确保数据完整性

3. **技术分析** (Technical_Analyst):
   - 计算 MACD, KDJ, RSI, 布林带等指标
   - 分析短线、中线、长线趋势
   - 标注支撑位和阻力位

4. **基本面分析** (Fundamental_Analyst):
   - 评估估值水平
   - 分析财务健康度
   - 考虑宏观经济影响

5. **综合报告** (Chief_Investment_Officer):
   - 汇总所有分析结论
   - 生成8个时间周期的预测
   - 给出具体操作建议
   - 列出风险提示

{f"## 额外信息{chr(10)}{additional_context}" if additional_context else ""}

## 开始分析
请 Data_Engineer 首先确认股票代码并开始数据收集。
"""
    return task_message


async def run_security_analysis_async(
    agents: Dict[str, autogen.Agent],
    security_input: str,
    additional_context: str = "",
    max_round: int = 20,
) -> List[Dict]:
    """
    异步运行证券分析流程
    
    Args:
        agents: Agent 字典
        security_input: 证券代码或名称
        additional_context: 额外上下文
        max_round: 最大轮次
    
    Returns:
        对话历史列表
    """
    # 创建 GroupChat
    groupchat, manager = create_analysis_group_chat(agents, max_round)
    
    # 格式化任务
    task = format_initial_task(security_input, additional_context)
    
    # 启动分析
    await agents["user_proxy"].a_initiate_chat(
        manager,
        message=task,
    )
    
    return groupchat.messages


def run_security_analysis(
    agents: Dict[str, autogen.Agent],
    security_input: str,
    additional_context: str = "",
    max_round: int = 20,
) -> List[Dict]:
    """
    同步运行证券分析流程
    
    Args:
        agents: Agent 字典
        security_input: 证券代码或名称
        additional_context: 额外上下文
        max_round: 最大轮次
    
    Returns:
        对话历史列表
    """
    # 创建 GroupChat
    groupchat, manager = create_analysis_group_chat(agents, max_round)
    
    # 格式化任务
    task = format_initial_task(security_input, additional_context)
    
    # 启动分析
    agents["user_proxy"].initiate_chat(
        manager,
        message=task,
    )
    
    return groupchat.messages


def extract_final_report(messages: List[Dict]) -> Optional[str]:
    """
    从对话历史中提取最终报告
    
    Args:
        messages: 对话历史
    
    Returns:
        最终报告 Markdown 文本，如果未找到返回 None
    """
    # 从后往前搜索 CIO 的报告
    for msg in reversed(messages):
        if isinstance(msg, dict):
            name = msg.get("name", "")
            content = msg.get("content", "")
            
            if name == "Chief_Investment_Officer" and content:
                # 检查是否包含报告特征
                if "投资分析报告" in content or "# " in content:
                    return content
    
    return None


def save_report(
    report: str,
    security_name: str,
    output_dir: Path = None,
) -> Path:
    """
    保存分析报告到文件
    
    Args:
        report: 报告内容
        security_name: 证券名称
        output_dir: 输出目录
    
    Returns:
        保存的文件路径
    """
    if output_dir is None:
        output_dir = SystemConfig.REPORT_DIR
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in security_name)
    filename = f"{safe_name}_{timestamp}.md"
    
    filepath = output_dir / filename
    filepath.write_text(report, encoding="utf-8")
    
    return filepath
