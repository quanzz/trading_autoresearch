# Trading Autoresearch

请仔细阅读karpathy_autoresearch目录里的文件，基于这个思路，帮我做一个类似的项目Trading Autoresearch，所有文件放在trading_autoresearch中。

## 任务

Trading Autoresearch不是用来测试验证损失、迭代机器学习模型，而是把karpathy的autoresearch方法用在量化交易策略的优化上。
你需要：
- 用python撰写一个回测框架，包含回测模块、策略模板、账户等；
- 所处理的交易数据格式如（## 数据格式）所示；
- 你会自己撰写分钟级的策略，然后利用该回测框架回测，根据（## 优化指标）来评估当前策略；
- 你会自动化地（比如每小时一次）进行回测，通过调整策略来改进指标表现；
- 你会撰写日志，将每一次的发现、改进以及总结撰写到相应日志中；
- 整个项目是无人值守的，用户可能需要的参与的是在你提供的配置文件中给出交易手续费、滑点、乘数等信息。

## 优化指标

- 最大回撤（Max Drawdown, MDD）: 优先级最高
- 夏普比率（Sharpe Ratio）: 优先级其次
你可以设计一个两个指标的加权指标。

## 数据格式
我所提供的数据是csv文件，单个品种放在一个csv文件中，比如 "au2607.csv"，csv文件包含以下字段（逗号`,`分隔）：
- date: 日期（分钟级，比如 2026-06-06 09:31:28）
- open: 开盘价
- high: 最高价
- low: 最低价
- close: 收盘价 
- volume: 成交量
- amt: 成交额
- oi: 持仓量
若某些字段不存在对应数值，则该列为空字符串。


---

@trading_autoresearch/  修改这个项目，增加如下过程：1、每次回测完，都将策略脚本复制一份到trading_autoresearch/results下（脚本名称包含日期）；2、每次回测完都将回测结果做成净值曲线图，将图片保存在trading_autoresearch/results下，图片名称包含日期以及策略名；3、每次回测完，你需要针对当前所回测的策略写总结，将总结报告也保存在trading_autoresearch/results下，名称包含日期以及策略名。按照上述增加项目，修改以及增加相应的文件、代码、说明。