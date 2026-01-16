# Implementation Plan: Strategy Pool

## Overview

实现模拟交易系统的策略池功能，包括策略注册表、6种预设策略、用户配置管理、多策略并行执行和性能统计对比。采用渐进式开发，先完成核心框架，再逐步添加各策略实现。

## Tasks

- [x] 1. 数据库迁移和基础架构
  - [x] 1.1 添加策略相关数据库表
    - 在 web/database.py 的 migrate_database() 函数中添加迁移逻辑
    - 创建 strategy_configs 表存储用户策略配置
    - 创建 strategy_performance 表存储策略表现
    - 修改 sim_trade_positions 表添加 strategy_id 字段
    - 修改 sim_trade_records 表添加 strategy_id 字段
    - _Requirements: 3.3, 11.1_

  - [x] 1.2 创建策略模块目录结构
    - 创建 web/strategies/ 目录
    - 创建 __init__.py, registry.py, base.py
    - _Requirements: 1.1_

- [x] 2. 策略注册表和基类实现
  - [x] 2.1 实现策略定义数据类
    - 在 web/strategies/registry.py 中创建 StrategyCategory 枚举
    - 创建 RiskLevel 枚举
    - 创建 StrategyDefinition 数据类
    - _Requirements: 1.1, 1.3_

  - [x] 2.2 实现策略注册表
    - 实现 StrategyRegistry 类
    - 实现 register, get_all, get_by_id, get_by_category 方法
    - _Requirements: 1.1, 1.2_

  - [x] 2.3 实现策略基类
    - 在 web/strategies/base.py 中创建 Signal 数据类
    - 创建 BaseStrategy 抽象基类
    - 定义 generate_signals, calculate_position_size, check_exit_conditions 抽象方法
    - _Requirements: 5.1, 6.1, 7.1, 8.1, 9.1, 10.1_

  - [x] 2.4 编写策略基类单元测试

    - 测试 Signal 数据类
    - 测试 StrategyRegistry 注册和查询
    - _Requirements: 1.1_

- [-] 3. 短线策略实现
  - [x] 3.1 实现RSI极限反转策略
    - 创建 web/strategies/rsi_reversal.py
    - 实现 2日RSI 和 200日均线计算
    - 实现买入信号生成（RSI<10 且 价格>MA200）
    - 实现卖出信号生成（价格>MA5）
    - 实现止损逻辑（-3%）
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 3.2 编写RSI策略属性测试

    - **Property 7: RSI Strategy Signal Generation**
    - **Validates: Requirements 5.1, 5.2, 5.3**

  - [x] 3.3 实现隔夜效应策略
    - 创建 web/strategies/overnight.py
    - 实现买入时段判断（14:50-14:57）
    - 实现卖出时段判断（9:30-9:35）
    - 实现周五跳过逻辑
    - 实现历史隔夜收益率筛选
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 3.4 编写隔夜策略单元测试

    - 测试时段判断逻辑
    - 测试周五跳过逻辑
    - _Requirements: 6.1, 6.4_

- [x] 4. 波段策略实现
  - [x] 4.1 实现动量轮动策略
    - 创建 web/strategies/momentum_rotation.py
    - 实现动量得分计算 (P_t - P_{t-20}) / P_{t-20}
    - 实现ETF排名和选择逻辑
    - 实现轮动信号生成
    - 配置10-15只行业ETF池
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 4.2 编写动量策略属性测试
    - **Property 8: Momentum Score Calculation**
    - **Validates: Requirements 7.2, 7.3**

  - [x] 4.3 实现乖离率回归策略
    - 创建 web/strategies/bias_reversion.py
    - 实现BIAS计算 (Close - MA20) / MA20
    - 实现布林带计算（20日，2倍标准差）
    - 实现买入信号（触及下轨+缩量）
    - 实现卖出信号（中轨或上轨）
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 4.4 编写乖离率策略单元测试

    - 测试BIAS计算
    - 测试布林带计算
    - _Requirements: 8.1, 8.2_

- [ ] 5. 长线策略实现
  - [ ] 5.1 实现风险平价策略
    - 创建 web/strategies/risk_parity.py
    - 实现60日滚动波动率计算
    - 实现权重计算 Weight_i = (1/σ_i) / Σ(1/σ_j)
    - 实现最小配置约束（10%）
    - 实现再平衡触发逻辑（偏离>5%）
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 5.2 编写风险平价策略属性测试
    - **Property 9: Risk Parity Weight Calculation**
    - **Validates: Requirements 9.3, 9.5**

  - [ ] 5.3 实现自适应均线择时策略
    - 创建 web/strategies/adaptive_ma.py
    - 实现基准指数均线监控
    - 实现缓冲区逻辑（1%）
    - 实现牛市/熊市信号生成
    - 支持可配置均线周期（20/60/120日）
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 5.4 编写自适应均线策略属性测试
    - **Property 10: Adaptive MA Signal Generation**
    - **Validates: Requirements 10.2, 10.3, 10.5**

- [ ] 6. Checkpoint - 策略实现完成
  - 确保所有6个策略实现完成
  - 确保所有策略测试通过
  - 询问用户是否有问题

- [ ] 7. 策略执行器实现
  - [ ] 7.1 实现策略执行器核心
    - 创建 web/strategies/executor.py
    - 实现 StrategyExecutor 类
    - 实现 load_user_strategies 方法
    - 实现 execute_all 方法
    - _Requirements: 3.1, 3.2_

  - [ ] 7.2 实现信号冲突解决
    - 实现 _resolve_conflicts 方法
    - 优先级：卖出 > 买入，强度高 > 强度低
    - _Requirements: 3.2_

  - [ ]* 7.3 编写信号冲突解决属性测试
    - **Property 5: Signal Conflict Resolution**
    - **Validates: Requirements 3.2**

  - [ ] 7.4 实现策略资金隔离
    - 每个策略使用独立分配的资金
    - 交易金额不超过策略分配资金
    - _Requirements: 3.4, 3.5_

  - [ ]* 7.5 编写资金隔离属性测试
    - **Property 4: Strategy Position Isolation**
    - **Validates: Requirements 3.3, 3.4, 3.5**

- [ ] 8. 用户配置管理
  - [ ] 8.1 实现策略配置数据库操作
    - 在 web/database.py 中添加策略配置相关函数
    - 创建 db_get_user_strategy_configs 函数
    - 创建 db_save_user_strategy_config 函数
    - 创建 db_update_strategy_config 函数
    - 创建 db_delete_strategy_config 函数
    - _Requirements: 2.1, 2.2, 2.4_

  - [ ]* 8.2 编写配置持久化属性测试
    - **Property 2: Strategy Configuration Persistence**
    - **Validates: Requirements 2.1, 2.2, 2.4**

  - [ ] 8.3 实现资金分配验证
    - 验证总分配不超过可用资金
    - 验证单策略最小资金要求
    - _Requirements: 2.3_

  - [ ]* 8.4 编写资金分配验证属性测试
    - **Property 3: Capital Allocation Validation**
    - **Validates: Requirements 2.3**

- [ ] 9. 性能统计实现
  - [ ] 9.1 实现策略性能计算
    - 在 web/strategies/ 中创建 performance.py
    - 计算总收益率
    - 计算胜率
    - 计算最大回撤
    - 计算夏普比率
    - _Requirements: 4.1_

  - [ ] 9.2 实现性能数据持久化
    - 在 web/database.py 中添加性能数据相关函数
    - 每日更新策略性能
    - 支持按日/周/月聚合
    - _Requirements: 4.4, 4.5_

  - [ ]* 9.3 编写性能指标属性测试
    - **Property 6: Performance Metrics Completeness**
    - **Validates: Requirements 4.1, 4.2, 4.3**

- [ ] 10. Checkpoint - 后端核心完成
  - 确保所有后端功能实现完成
  - 确保所有测试通过
  - 询问用户是否有问题

- [ ] 11. 后端API实现
  - [ ] 11.1 实现策略列表API
    - 在 web/api.py 中添加策略相关API端点
    - GET /api/strategies - 获取所有预设策略
    - GET /api/strategies/{id} - 获取策略详情
    - _Requirements: 1.1, 1.2, 1.4_

  - [ ] 11.2 实现用户策略配置API
    - GET /api/sim-trade/strategies - 获取用户策略配置
    - POST /api/sim-trade/strategies - 添加策略配置
    - PUT /api/sim-trade/strategies/{id} - 更新策略配置
    - DELETE /api/sim-trade/strategies/{id} - 删除策略配置
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 11.3 实现策略性能API
    - GET /api/sim-trade/strategies/performance - 获取所有策略性能对比
    - GET /api/sim-trade/strategies/{id}/performance - 获取单策略性能详情
    - _Requirements: 4.1, 4.2, 4.3, 4.5_

  - [ ] 11.4 实现策略交易记录API
    - GET /api/sim-trade/records?strategy_id={id} - 按策略筛选交易记录
    - GET /api/sim-trade/records/export?strategy_id={id} - 导出CSV
    - _Requirements: 11.3, 11.4_

- [ ] 12. 风控模块实现
  - [ ] 12.1 实现策略风控检查
    - 在 web/strategies/ 中创建 risk_control.py
    - 实现单策略仓位限制
    - 实现策略回撤监控
    - 实现日亏损限制
    - _Requirements: 12.1, 12.2, 12.3_

  - [ ] 12.2 实现策略暂停机制
    - 回撤超阈值自动暂停
    - 日亏损超限自动暂停
    - 记录暂停原因和时间
    - _Requirements: 12.2, 12.4_

  - [ ]* 12.3 编写风控属性测试
    - **Property 12: Risk Control Enforcement**
    - **Validates: Requirements 12.1, 12.2, 12.4**

- [ ] 13. 调度器集成
  - [ ] 13.1 修改自动交易调度器
    - 修改 web/scheduler.py 集成策略执行器
    - 支持多策略并行执行
    - 记录策略执行日志
    - _Requirements: 2.5, 3.1_

  - [ ] 13.2 实现策略定时任务
    - 动量轮动策略每周五执行
    - 风险平价策略每月执行
    - 隔夜策略每日执行
    - _Requirements: 7.4, 9.4_

- [ ] 14. 前端策略池页面
  - [ ] 14.1 创建策略池页面组件
    - 创建 frontend/app/sim-trade/strategies/page.tsx
    - 显示所有预设策略列表
    - 显示策略分类（短线/波段/长线）
    - 显示策略风险等级
    - _Requirements: 1.1, 1.3_

  - [ ] 14.2 实现策略详情弹窗
    - 显示策略入场/出场逻辑
    - 显示适用ETF类型
    - 显示历史回测表现
    - _Requirements: 1.2, 1.4_

  - [ ] 14.3 实现策略配置面板
    - 策略启用/禁用开关
    - 资金分配输入框
    - 参数配置（可选）
    - 保存配置按钮
    - _Requirements: 2.1, 2.2_

  - [ ] 14.4 实现资金分配验证UI
    - 显示总分配金额
    - 显示剩余可分配金额
    - 超额时显示警告
    - _Requirements: 2.3_

- [ ] 15. 前端性能对比页面
  - [ ] 15.1 实现策略性能对比表格
    - 显示所有启用策略的性能指标
    - 支持按指标排序
    - 高亮最佳/最差策略
    - _Requirements: 4.1, 4.2_

  - [ ] 15.2 实现收益曲线图表
    - 使用 recharts 绑制累计收益曲线
    - 支持多策略叠加显示
    - 支持时间范围选择
    - _Requirements: 4.3_

  - [ ] 15.3 实现策略交易记录筛选
    - 按策略筛选交易记录
    - 显示策略归属标签
    - 支持导出CSV
    - _Requirements: 11.3, 11.4, 11.5_

- [ ] 16. 前端模拟交易页面集成
  - [ ] 16.1 修改持仓显示
    - 修改 frontend/app/sim-trade/page.tsx
    - 显示持仓的策略归属
    - 按策略分组显示
    - _Requirements: 11.5_

  - [ ] 16.2 添加策略池入口
    - 在模拟交易页面添加"策略池"按钮
    - 显示已启用策略数量
    - _Requirements: 1.1_

- [ ] 17. Final Checkpoint - 功能完成
  - 确保所有功能实现完成
  - 确保所有测试通过
  - 确保前后端集成正常
  - 询问用户是否有问题

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
