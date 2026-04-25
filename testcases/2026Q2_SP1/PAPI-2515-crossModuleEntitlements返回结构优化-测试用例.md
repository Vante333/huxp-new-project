# PAPI-2515_crossModuleEntitlements返回结构优化测试用例

## v2_entitlements_search（SearchEntitlements）

### summary与pools结构契约

> **与自动化断言对齐（pytest / Postman）**：同组 `applicableModules` 下，四类指标 `cardholderExclusiveEntitlements`、`guestsExclusiveEntitlements`、`sharedEntitlements`、`purchasedEntitlements` 须满足——各池 `pools[].details` **缺键按 0**；**任池该指标为 `-1` 则组级 `summary` 该指标为 `-1`**（不再与其它池数值做代数和）。四类指标彼此独立计算。

#### 正向场景验证

##### tc-P1-GEN-001：Search成功返回crossModuleEntitlements含applicableModules与summary与pools

- tc-P1: pc: 测试用户已配置跨模块权益且存在至少一组跨品类数据及多个entitlementPoolId
- tc-P1: 调用GET或POST等环境契约约定的v2_entitlements_search接口查询权益
- tc-P1: HTTP状态码为业务成功，响应体中crossModuleEntitlements为数组且非空时每项包含applicableModules、summary、pools三个键
- tc-P1: tag: PAPI-2515,Search,结构

##### tc-P1-GEN-002：Search返回每组crossModule中summary含合并后携伴与权益聚合字段

- tc-P1: pc: 同组applicableModules下存在多池权益且含可触发allowedGuestsPerUsage与maxGuestsNextUse计算的数据
- tc-P1: 调用v2_entitlements_search接口
- tc-P1: summary对象存在且包含需求约定的聚合字段（含allowedGuestsPerUsage与maxGuestsNextUse或契约等价命名），取值类型与业务含义正确
- tc-P1: tag: PAPI-2515,Search,summary

##### tc-P1-GEN-003：Search返回pools每项含entitlementPoolId与details对象

- tc-P1: pc: crossModuleEntitlements非空
- tc-P1: 调用v2_entitlements_search接口
- tc-P1: pools为数组且每项包含entitlementPoolId与details，details为对象
- tc-P1: tag: PAPI-2515,Search,pools

### pools明细字段规则

#### 规则验证

##### tc-P1-GEN-004：Search中pools各条details不含allowedGuestsPerUsage与maxGuestsNextUse

- tc-P1: pc: crossModuleEntitlements非空
- tc-P1: 调用v2_entitlements_search接口
- tc-P1: 遍历全部pools[].details的键名，均不得出现allowedGuestsPerUsage与maxGuestsNextUse
- tc-P1: tag: PAPI-2515,Search,字段移除

##### tc-P2-GEN-001：Search中大客户nonShare池details仅含持卡人与携伴专属字段

- tc-P2: pc: 用户同组内存在大客户nonShare池且另有shared池与买点池
- tc-P2: 调用v2_entitlements_search接口
- tc-P2: nonShare池的details仅包含cardholderExclusiveEntitlements与guestsExclusiveEntitlements等本池类型字段，不包含sharedEntitlements与purchasedEntitlements
- tc-P2: tag: PAPI-2515,Search,明细裁剪

##### tc-P2-GEN-002：Search中shared池details仅含sharedEntitlements

- tc-P2: pc: 用户同组内存在大客户shared池且另有nonShare或买点池
- tc-P2: 调用v2_entitlements_search接口
- tc-P2: shared池的details以sharedEntitlements为主，不包含nonShare与买点专属字段
- tc-P2: tag: PAPI-2515,Search,明细裁剪

##### tc-P2-GEN-003：Search中买点池details仅含purchasedEntitlements

- tc-P2: pc: 用户存在买点池且买点余额大于0
- tc-P2: 调用v2_entitlements_search接口
- tc-P2: 买点池details仅展示purchasedEntitlements（及契约允许的同池字段），不包含大客户nonShare与shared的冗余权益字段
- tc-P2: tag: PAPI-2515,Search,买点

### 合并分组与买点虚构

#### 规则验证

##### tc-P1-GEN-005：Search中相同applicableModules仅对应一条crossModule元素且summary为整组合并结果

- tc-P1: pc: 多个entitlementPoolId属于同一applicableModules集合例如模块134
- tc-P1: 调用v2_entitlements_search接口
- tc-P1: crossModuleEntitlements中仅一条元素的applicableModules与该集合一致，summary中携伴与权益聚合为整组规则合并后的结果而非按旧版逐条明细独立计算
- tc-P1: rc: 期望数值以技术方案或造数脚本为准，自动化可与变更前备份或黄金JSON对比
- tc-P1: tag: PAPI-2515,Search,合并

##### tc-P2-GEN-004：Search中不同applicableModules分为多条crossModule元素且summary各自独立

- tc-P2: pc: 用户同时存在两组不同applicableModules例如134与12
- tc-P2: 调用v2_entitlements_search接口
- tc-P2: crossModuleEntitlements包含两条及以上元素时各组applicableModules不混淆且各组summary独立计算
- tc-P2: tag: PAPI-2515,Search,分组

##### tc-P2-GEN-005：Search在无买点明细但存在买点配置时pools含purchasedEntitlements为0的买点池

- tc-P2: pc: 项目或用户已配置买点能力但当前无真实买点余额明细或余额为0且需触发虚构规则
- tc-P2: 调用v2_entitlements_search接口
- tc-P2: pools中存在买点对应池且其details中purchasedEntitlements为0，summary中买点相关聚合与配置存在且余额为零语义一致
- tc-P2: tag: PAPI-2515,Search,虚构买点

#### 边界值验证

##### tc-P3-GEN-001：Search中crossModuleEntitlements为空数组时接口仍成功且其余权益字段正常

- tc-P3: pc: 测试用户无任何跨模块权益组合
- tc-P3: 调用v2_entitlements_search接口
- tc-P3: HTTP业务成功，crossModuleEntitlements为空数组或符合契约的缺省形态，响应中其他权益相关字段完整且类型正确
- tc-P3: tag: PAPI-2515,Search,边界

##### tc-P3-GEN-002：Search中仅单池单明细时仍返回完整summary与单项pools

- tc-P3: pc: 某applicableModules组内仅一个entitlementPoolId与一条明细
- tc-P3: 调用v2_entitlements_search接口
- tc-P3: 该组仍包含summary与仅含一项的pools，summary与唯一池details权益语义一致且details无携伴两字段
- tc-P3: tag: PAPI-2515,Search,边界

##### tc-P2-GEN-006：Search中sharedEntitlements为负一无限时summary与shared池details一致

- tc-P2: pc: 用户共享权益为无限负一可造数场景
- tc-P2: 调用v2_entitlements_search接口
- tc-P2: summary.sharedEntitlements与shared池details.sharedEntitlements均为负一或契约等价表示且合并逻辑未错误累加
- tc-P2: tag: PAPI-2515,Search,无限共享

## v2_memberships（Memberships）

### 会籍返回crossModule结构

#### 正向场景验证

##### tc-P1-MBR-001：Memberships成功返回crossModuleEntitlements结构与Search新契约一致

- tc-P1: pc: 测试用户与Search用例同构且具备会籍查询权限
- tc-P1: 调用环境契约约定的v2_memberships接口
- tc-P1: 成功响应中若包含crossModuleEntitlements则每组含summary与pools且pools[].details不含allowedGuestsPerUsage与maxGuestsNextUse
- tc-P1: tag: PAPI-2515,Memberships,结构

##### tc-P2-MBR-001：Memberships与Search在同一用户下crossModule分组与summary核心数值一致

- tc-P2: pc: 用户存在非空crossModuleEntitlements
- tc-P2: 先调用v2_entitlements_search再调用v2_memberships（或相反，时间窗口内无并发变更）
- tc-P2: 两次响应中crossModuleEntitlements组数与各组applicableModules集合及summary关键数值一致，若产品允许短暂不一致则在rc中写明可接受条件
- tc-P2: tag: PAPI-2515,Memberships,一致性

#### 规则验证

##### tc-P2-MBR-002：新注册或注册完成返回体中crossModule为新结构不含明细携伴字段

- tc-P2: pc: 新用户走会籍注册流程且模板含跨模块权益
- tc-P2: 在注册成功响应或紧随其后的memberships查询中获取crossModuleEntitlements
- tc-P2: 若存在该字段则符合summary与pools结构且pools[].details无allowedGuestsPerUsage与maxGuestsNextUse
- tc-P2: tag: PAPI-2515,Memberships,注册

## v2_entitlements_update（UpdateEntitlements）

### 全量或批量更新响应

#### 正向场景验证

##### tc-P1-GEN-001：Update成功响应中crossModuleEntitlements符合summary与pools新结构

- tc-P1: pc: 用户存在跨模块权益且准备合法更新请求体
- tc-P1: 调用环境契约约定的v2_entitlements_update接口
- tc-P1: 业务成功且响应体若返回crossModuleEntitlements则每组含summary与pools且明细无allowedGuestsPerUsage与maxGuestsNextUse
- tc-P1: tag: PAPI-2515,Update,结构

##### tc-P2-GEN-001：Update后summary随合并规则重算且pools明细仍裁剪

- tc-P2: pc: 更新将改变影响组级合并的权益数值
- tc-P2: 调用v2_entitlements_update接口提交变更
- tc-P2: 成功响应中对应组summary已重算且各pools[].details仅含本池相关字段且无携伴两字段
- tc-P2: tag: PAPI-2515,Update,重算

##### tc-P2-GEN-002：Update后买点余额为零但配置仍存在时仍保留买点池且purchasedEntitlements为零

- tc-P2: pc: 更新使用户买点余额变为零且买点配置仍存在
- tc-P2: 调用v2_entitlements_update接口后检查响应或紧接着调用v2_entitlements_search
- tc-P2: crossModuleEntitlements中仍存在买点池且details.purchasedEntitlements为零
- tc-P2: tag: PAPI-2515,Update,虚构买点

## v2_entitlements_entitlementPoolId_update（UpdateEntitlementByPool）

### 单池路径更新

#### 正向场景验证

##### tc-P1-GEN-001：entitlementPoolId路径Update成功返回crossModule新结构

- tc-P1: pc: 目标entitlementPoolId属于某applicableModules组内一池
- tc-P1: 调用PUT或PATCH等契约约定的v2_entitlements_entitlementPoolId_update接口做合法更新
- tc-P1: 业务成功，响应中crossModuleEntitlements含summary与pools，被更新池details反映新值且全部details无allowedGuestsPerUsage与maxGuestsNextUse
- tc-P1: tag: PAPI-2515,PoolUpdate,结构

#### 规则验证

##### tc-P2-GEN-001：单池更新后该组summary为整组合并非仅等于被更新池明细

- tc-P2: pc: 组内至少两个池，仅更新其中一个池的权益数值
- tc-P2: 调用v2_entitlements_entitlementPoolId_update接口
- tc-P2: 该组summary为同组多池合并规则下的结果，不等于单池details的简单拷贝（除非业务上仅一池有值）
- tc-P2: tag: PAPI-2515,PoolUpdate,合并

##### tc-P3-GEN-001：单池更新未波及其他applicableModules组的crossModule数据

- tc-P3: pc: 用户存在至少两组不同applicableModules，仅更新其中一组内某池
- tc-P3: 记录更新前其他组的applicableModules与summary与pools摘要后调用v2_entitlements_entitlementPoolId_update接口
- tc-P3: 其他组crossModuleEntitlements与更新前一致（除契约允许的时间戳类字段外）
- tc-P3: tag: PAPI-2515,PoolUpdate,隔离

## 跨接口一致性（CrossModuleConsistency）

### Search与Update对齐

#### 正向场景验证

##### tc-P1-GEN-001：Update成功后Search与Update响应中crossModule结构语义一致

- tc-P1: pc: 用户存在跨模块权益
- tc-P1: 调用v2_entitlements_update接口成功完成权益更新
- tc-P1: 响应中crossModuleEntitlements与随后调用v2_entitlements_search得到的结果在组级summary与各池details上语义一致，或以产品说明的允许差异为准
- tc-P1: rc: 若Update接口不返回完整crossModule则以Search为权威校验更新结果
- tc-P1: tag: PAPI-2515,一致性,Update,Search

##### tc-P1-GEN-002：entitlementPoolId路径Update成功后Search与本次响应crossModule一致

- tc-P1: pc: 用户跨模块组内某池可更新
- tc-P1: 调用v2_entitlements_entitlementPoolId_update接口成功更新
- tc-P1: 随后调用v2_entitlements_search得到的crossModuleEntitlements与该组summary及各池details与更新操作预期一致
- tc-P1: tag: PAPI-2515,一致性,PoolUpdate,Search

### 四接口结构契约参数化

#### 规则验证

##### tc-P2-GEN-PARAM-001：同一用户下四接口返回crossModule时均满足新结构契约

| 序号 | 接口标识 | 调用说明 |
| --- | --- | --- |
| 1 | v2_entitlements_search | 按OpenAPI方法路径与鉴权头调用 |
| 2 | v2_memberships | 按OpenAPI方法路径与鉴权头调用 |
| 3 | v2_entitlements_update | 使用合法请求体，避免破坏后续断言或于独立环境执行 |
| 4 | v2_entitlements_entitlementPoolId_update | 路径参数替换为真实entitlementPoolId |

- tc-P2: pc: 固定测试用户且数据满足crossModuleEntitlements非空
- tc-P2: 按上表序号依次调用各接口（更新类仅做合法小改或幂等请求）
- tc-P2: 每次成功响应中若存在crossModuleEntitlements则每组均有summary与pools且所有pools[].details均不含allowedGuestsPerUsage与maxGuestsNextUse
- tc-P2: rc: 某接口成功体不包含crossModule时改为成功后仅调用Search校验持久结果
- tc-P2: tag: PAPI-2515,参数化,四接口

## 其他权益字段回归（Regression）

### 响应其他字段

#### 回归验证

##### tc-P2-GEN-001：Search除crossModuleEntitlements外其他已文档化字段未被破坏

- tc-P2: pc: 用户数据同时包含crossModule与其他权益块字段
- tc-P2: 调用v2_entitlements_search接口
- tc-P2: 除crossModuleEntitlements结构按新需求变化外其余字段路径与类型符合OpenAPI或变更前基线
- tc-P2: tag: PAPI-2515,回归

##### tc-P3-GEN-001：鉴权失败或参数非法时错误响应形态与变更前一致

- tc-P3: pc: 准备无效Token或非法请求体等
- tc-P3: 调用v2_entitlements_search或v2_entitlements_update等接口触发失败分支
- tc-P3: HTTP与业务错误码及错误体结构符合既有规范且不额外泄露内部实现细节
- tc-P3: tag: PAPI-2515,异常
