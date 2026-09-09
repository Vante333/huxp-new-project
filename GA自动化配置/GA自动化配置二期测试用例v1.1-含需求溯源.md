# GA自动化配置二期 测试用例（v1.1 改良版 · 含需求溯源）

> 需求来源：《二期Generic API自动化配置补充需求-2.pdf》（Jira ECS-373）
> 编号规则：GA2-<模块>-<序号>；优先级：P0=冒烟主流程，P1=全量/异常/边界，P2=低优先
> 默认环境：UAT（品类码禁止串环境，见附录A）

## v1.1 变更说明（相对 v1.0）

1. 每条用例新增【需求出处】列，可按需求逐条过用例
2. 新增第十二章「需求覆盖矩阵」（需求条目 → 用例编号 反向映射）
3. 新增第十三章「待确认需求点」Q1~Q8，这些需求 PDF 未定义，预期结果先按推断写、确认后更新
4. 新增用例：GA2-AGR-012、GA2-AGR-108、GA2-TEN-009、GA2-ESM-024、GA2-ENV-006
5. 修正：GA2-ESM-016 预期结果改为真实报错文案；GA2-P8-001 商品命名口径对齐需求；GA2-SWP-003 补充核销依赖说明
6. 被 B1/B2 阻塞的用例在优先级列标注【阻塞B1】/【阻塞B2】

## 需求出处编号对照

| 编号 | 需求位置 |
|------|----------|
| R0 | PDF「和一期的关系」品类总表（含 Swap 组合规则） |
| R1.1 | 一、BOSS Step3 → 1.1 ESIM |
| R1.2 | 一、BOSS Step3 → 1.2 Fitness |
| R1.3 | 一、BOSS Step3 → 1.3 MPV |
| R2.1 | 二、SAAS → 2.1 创建权益 Step5 |
| R2.2 | 二、SAAS → 2.2 创建会籍 Step6（含 Step7 会籍商品规则） |
| R2.3 | 二、SAAS → 2.3 预约/核销商品 Step8 |
| R2.4 | 二、SAAS → 2.4 接口权限与凭证 Step9 |
| R2.5 | 二、SAAS → 2.5 Agent Portal Step10 |
| R3 | 三、新建/复用协议与租户（含规则1~3） |
| R4 | 四、其它交互（Lounge Pricing Model / Upload File） |
| R5 | 测试时禁止串环境的品类码 + 交易配置对照 |
| Q1~Q8 | 第十三章待确认需求点（PDF 未写，属推断用例） |
| 历史缺陷 | 一期/UAT 实际踩坑转化的回归用例 |

## 通用前置条件

| 编号 | 前置条件 |
|------|----------|
| PRE-01 | 已连接公司 VPN，可访问 BOSS 2.0 与 SAAS 对应环境后台 |
| PRE-02 | Onboarding Form 已完整填写并提交（含品类勾选、Cancellation Rule、Entitlement Order Limit、Settlement Currency、Tax Treatment、Real Name/Verification/Accompany 等） |
| PRE-03 | 已拿到当前环境有效 Customer Code / Contract Code（UAT 示例客户 DPC000168） |
| PRE-04 | 阻塞项确认：B1 标准网络模板编码（产品提供）、B2 标准价格模板（John King 团队提供），未提供则对应用例标记 Blocked |

---

## 一、Step 1 协议配置 Agreement（R3）

### 1.1 新建协议 Create New Agreement

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-AGR-001 | 新建协议-默认内容按Form生成 | R3-新建协议 | Form已提交 | 1.进入Review Detail的Create Agreement步骤 2.选择Create New Agreement | 展示完整编辑区，协议内容按Form信息预填 | P0 |
| GA2-AGR-002 | 新建协议-字段可编辑 | R3-新建协议 | 同上 | 1.编辑协议名称/币种/税率等字段 2.保存 | 编辑生效，审核前内容以编辑后为准 | P1 |
| GA2-AGR-003 | Agreement Company与合同公司一致 | R3+历史缺陷 | 合同为A006开头 | 1.Agreement Company选A006 2.提交审核 | 校验通过，审核通过后可调BOSS创建接口 | P0 |
| GA2-AGR-004 | 审核通过才调BOSS创建协议接口 | R3-新建协议 | 同上 | 1.审核前抓包观察 2.审核通过后抓包观察 | 审核前无创建协议请求；审核通过后发起BOSS创建协议接口 | P0 |
| GA2-AGR-005 | 创建成功BOSS落库对照 | R3-新建协议 | 审核已通过 | 1.执行创建 2.登录BOSS查协议列表 | BOSS可查到新协议，客户/合同/币种/税率与审核通过内容一致 | P0 |
| GA2-AGR-006 | 导入成功后锁定不可编辑 | R3-规则3 | 创建已成功 | 1.返回Review Detail尝试编辑协议 | 协议配置锁定，编辑入口不可用 | P0 |
| GA2-AGR-007 | 未导入或失败可编辑重试 | R3-规则2 | 上次执行失败 | 1.修改协议参数 2.重新执行 | 可编辑，重试后创建成功 | P1 |
| GA2-AGR-008 | 合同编码跨环境（异常） | R3+历史缺陷 | 拿TEST合同配UAT单 | 1.填入TEST环境合同编码 2.提交 | 报"当前合同不存在，请重新选择合同"，不创建协议 | P0 |
| GA2-AGR-009 | 整串粘贴合同显示名（异常） | 历史缺陷 | 显示名"(A006-XS-20230703-10-28)SunnyTestDemo" | 1.整串粘贴到Contract Code 2.提交 | 报"当前合同不存在"，提示取纯编码 | P1 |
| GA2-AGR-010 | Company与合同前缀不一致（异常） | 历史缺陷 | Company=A004+合同A006开头 | 1.提交 | 校验失败，报"当前合同不存在"，不创建协议 | P1 |
| GA2-AGR-011 | 客户与合同归属不一致（异常） | 历史缺陷 | Customer=DPC000168+他客户合同 | 1.提交 | 校验失败提示，不创建协议 | P1 |
| GA2-AGR-012 | 审核驳回后可编辑再提交 | Q7-待确认 | 协议被审核驳回 | 1.修改内容 2.重新提交审核 | 【待确认】预期可编辑再提交；若系统不允许需提需求澄清 | P1 |

### 1.2 复用协议 Use Existing Agreement

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-AGR-101 | 复用协议-界面只展示编码输入框 | R3-复用协议+规则1 | Form已提交 | 1.选择Use Existing Agreement | 只展示Agreement Code输入框和校验结果，无完整编辑区 | P0 |
| GA2-AGR-102 | 复用协议-编码有效性校验通过 | R3-复用协议 | 已有有效协议 | 1.输入有效Agreement Code 2.继续执行 | 校验通过，进入下一步 | P0 |
| GA2-AGR-103 | 复用协议不调创建接口 | R3-复用协议 | 校验已通过 | 1.抓包执行后续步骤 | 全流程无BOSS创建协议接口请求 | P0 |
| GA2-AGR-104 | 后续步骤沿用该编码 | R3-复用协议 | 复用协议已确认 | 1.完成Step3/Step5 2.BOSS+SAAS对照 | 品类项目、权益均落在该Agreement Code下 | P0 |
| GA2-AGR-105 | 复用成功锁定、失败可改 | R3-规则2/3 | - | 1.成功后尝试修改 2.失败后修改重试 | 成功锁定不可编辑；失败可编辑重试 | P1 |
| GA2-AGR-106 | 编码不存在（异常） | R3-复用协议 | 随机编码 | 1.输入不存在的Agreement Code | 校验失败提示，流程不进入下一步 | P1 |
| GA2-AGR-107 | 编码属其他客户/环境（异常） | 历史缺陷推断 | 他客户/他环境编码 | 1.输入编码 2.提交 | 校验失败提示 | P1 |
| GA2-AGR-108 | 复用协议与Form币种/税率一致性 | Q3-待确认 | 复用USD协议+Form填SGD | 1.执行后续结算配置 | 【待确认】PDF未定义校验规则；预期要么拦截要么以协议为准，需产品确认 | P1 |

---

## 二、Step 3 BOSS品类项目（POST /api/project/batchAdd）

### 2.1 ESIM 品类（R1.1）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-ESM-001 | ESIM项目自动创建 | R1.1-项目名称 | Form勾选ESIM，ProgramName=X | 1.执行Step3 2.BOSS查项目 | 创建项目【Esim】X | P0 |
| GA2-ESM-002 | 品类码-UAT | R1.1-环境表 | 当前UAT | 1.抓包或查BOSS项目详情 | moduleType=ISC，moduleSubType=ISC00001（国际通用卡券eSim） | P0 |
| GA2-ESM-003 | 品类码-Test | R1.1-环境表+R5 | 当前Test | 同上 | moduleSubType=ISC00270（mai-Sim品类） | P1 |
| GA2-ESM-004 | 品类码-生产 | R1.1-环境表+R5 | 当前生产 | 同上 | moduleSubType=ISC00000 | P1 |
| GA2-ESM-005 | businessType/business固定值 | R1.1-JSON要点 | - | 1.抓包看请求体 | businessType=equity，business=agreement | P1 |
| GA2-ESM-006 | 跟随协议续期/状态 | R1.1-JSON要点 | - | 1.BOSS查项目 | renewalFollowAgreementDate=true（跟随协议续期=是），status=1（在用） | P0 |
| GA2-ESM-007 | 订单完成规则 | R1.1-品类规则 | - | 1.BOSS查品类规则 | 固定"确认使用时完成" | P0 |
| GA2-ESM-008 | 订单取消-按时间+按状态 | R1.1-品类规则 | - | 同上 | 取消方式=按时间限制+按状态限制 | P0 |
| GA2-ESM-009 | 取消时间跟Form-1天 | R1.1-品类规则 | Form Cancellation Rule=1天 | 1.BOSS对照 | 取消时间=1天 | P1 |
| GA2-ESM-010 | 取消时间跟Form-3天 | R1.1-品类规则 | Form=3天 | 同上 | 取消时间=3天 | P1 |
| GA2-ESM-011 | 取消时间跟Form-7天 | R1.1-品类规则 | Form=7天 | 同上 | 取消时间=7天 | P1 |
| GA2-ESM-012 | 取消状态固定 | R1.1-品类规则 | - | 同上 | 取消状态=未完成 | P1 |
| GA2-ESM-013 | 下单间隔跟Form-开启 | R1.1-品类规则 | Form Order Limit=N | 1.BOSS对照 | 下单间隔=N | P0 |
| GA2-ESM-014 | 下单间隔-Form未开启 | R1.1+Q1-待确认 | Form关闭Order Limit | 同上 | 【待确认Q1】PDF只写"按文档占位"，传null/0/不传需产品确认后更新预期 | P1 |
| GA2-ESM-015 | 网络模板跟Form选中 | R1.1-品类规则 | B1已解除，Form选模板M | 1.BOSS查网络配置 | Standard Network=模板M | P0【阻塞B1】 |
| GA2-ESM-016 | 网络模板在当前环境不存在（异常） | R1.1+历史缺陷 | 模板未同步到当前环境 | 1.执行Step3 2.看Onboarding执行页 | 报"save-network-range failed: 模板编码找不到对应的模板数据！"，该步失败，修正后可重试 | P0【阻塞B1】 |
| GA2-ESM-017 | 税率-不含税 | R1.1-品类规则 | Form选不含税 | 1.BOSS查结算配置 | 税率=0 | P0【阻塞B2】 |
| GA2-ESM-018 | 税率-含税 | R1.1-品类规则 | Form含税6% | 同上 | 税率=6% | P0【阻塞B2】 |
| GA2-ESM-019 | 定价维度 | R1.1-品类规则 | - | 同上 | 定价维度=ClientCode | P1【阻塞B2】 |
| GA2-ESM-020 | 客户/用户定价含税开关 | R1.1-品类规则 | Form含税 | 同上 | 客户定价含税=是，用户定价含税=是 | P1【阻塞B2】 |
| GA2-ESM-021 | 交易配置三件套 | R1.1-交易配置+R5 | - | 1.BOSS交易配置页 | 超人次方式=PAYG、支付方式=COF、支付网关=Ingenico，下拉均有值（空值=传参失败缺陷） | P0 |
| GA2-ESM-022 | 交易配置不跟Form | R1.1-交易配置 | Form改支付相关选项 | 1.重新执行 2.BOSS对照 | 仍PAYG/COF/Ingenico | P1 |
| GA2-ESM-023 | 备注为空不报错 | R1.1 | - | 1.BOSS查备注 | 备注无需填写，流程正常 | P2 |
| GA2-ESM-024 | 重复执行Step3幂等 | Q4-待确认 | 已成功执行过Step3 | 1.再次执行Step3 | 【待确认Q4】预期不产生重复项目；重复执行策略PDF未定义 | P1 |

### 2.2 Fitness 品类（R1.2）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-FIT-001 | Fitness项目自动创建 | R1.2-项目名称 | Form勾选Fitness，ProgramName=X | 1.执行Step3 2.BOSS查项目 | 创建项目【Fitness】X | P0 |
| GA2-FIT-002 | 品类码-UAT | R1.2-环境表 | 当前UAT | 1.查项目详情 | moduleType=IGC，moduleSubType=IGC00005（BODDY Gym） | P0 |
| GA2-FIT-003 | 品类码-Test/生产 | R1.2-环境表+R5 | Test/PROD | 同上 | IGC00013 / IGC00003 | P1 |
| GA2-FIT-004 | PDF示例IGC00002不适用（对照） | R1.2-环境表注 | - | 1.以环境表为准核对落库值 | 实际落库≠IGC00002，与环境表一致 | P1 |
| GA2-FIT-005 | 退订规则=允许 | R1.2-品类规则 | - | 1.BOSS查品类规则 | 退订=允许 | P0 |
| GA2-FIT-006 | 取消时间-24 hours before Service Time | R1.2-品类规则 | Form选该项 | 同上 | 与Form一致 | P0 |
| GA2-FIT-007 | 取消时间-One day before Service Date | R1.2-品类规则 | Form选该项 | 同上 | 与Form一致 | P1 |
| GA2-FIT-008 | 取消状态 | R1.2-品类规则 | - | 同上 | 待确认/待使用 | P1 |
| GA2-FIT-009 | 下单间隔跟Form | R1.2-品类规则 | Form Order Limit=N | 同上 | 下单间隔=N | P1 |
| GA2-FIT-010 | 默认网络模板 | R1.2-品类规则 | - | 1.BOSS查网络配置 | 模板=BOSS_T000727 | P0 |
| GA2-FIT-011 | 税率固定0 | R1.2-品类规则 | Form含税/不含税各测一组 | 1.BOSS查结算配置 | 两种Tax Treatment下税率均为0 | P0 |
| GA2-FIT-012 | 结算币种跟Form | R1.2-品类规则 | Form Settlement Currency=USD | 同上 | 客户/用户结算币种=USD | P0 |
| GA2-FIT-013 | 结算类型/结算时间 | R1.2-品类规则 | - | 同上 | 使用即结算/服务时间 | P1 |
| GA2-FIT-014 | 定价模式/维度/模板 | R1.2-品类规则 | - | 同上 | 标准模式/选择客户/使用模板=是（Standard Price） | P1【阻塞B2】 |
| GA2-FIT-015 | 交易配置 | R1.2-品类规则+R5 | - | 1.BOSS交易配置页 | PAYG/COF/Ingenico；超人次=否；信用卡核销=否 | P0 |
| GA2-FIT-016 | 跟随协议续期确认 | R1.2-品类规则+Q2 | 已向AM确认结论 | 1.核对BOSS配置 | 【待确认Q2】与AM结论一致；未确认前默认"是"仅作冒烟 | P2 |

### 2.3 MPV 品类（R1.3）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-MPV-001 | MPV项目自动创建 | R1.3-项目名称 | Form勾选MPV，ProgramName=X | 1.执行Step3 2.BOSS查项目 | 创建项目【MPV】X | P0 |
| GA2-MPV-002 | 品类码-UAT | R1.3-环境表 | 当前UAT | 1.查项目详情 | moduleType=NPMPV，moduleSubType=NPMPV00028（新平台MVPPCS） | P0 |
| GA2-MPV-003 | 品类码-Test/生产 | R1.3-环境表+R5 | Test/PROD | 同上 | NPMPV00031 / NPMPV00029 | P1 |
| GA2-MPV-004 | 实名规则-实名 | R1.3-品类规则 | Form Real Name=实名 | 1.BOSS查Advanced Rules | 实名规则=实名 | P0 |
| GA2-MPV-005 | 实名规则-校验凭证姓名 | R1.3-品类规则 | Form=校验凭证姓名 | 同上 | 与Form一致 | P1 |
| GA2-MPV-006 | 实名规则-非实名 | R1.3-品类规则 | Form=非实名 | 同上 | 与Form一致 | P1 |
| GA2-MPV-007 | 核销间隔跟Form | R1.3-品类规则 | Form Verification=30分钟 | 同上 | 核销间隔=30分钟 | P0 |
| GA2-MPV-008 | 携伴-不限制 | R1.3-品类规则 | Form Accompany=不限制 | 同上 | 与Form一致 | P1 |
| GA2-MPV-009 | 携伴-不可携伴 | R1.3-品类规则 | Form=不可携伴 | 同上 | 与Form一致 | P1 |
| GA2-MPV-010 | 携伴-可携伴X人 | R1.3-品类规则 | Form=可携伴2人 | 同上 | 携伴规则=可携伴2人 | P0 |
| GA2-MPV-011 | 扣点规则固定1点 | R1.3-品类规则+Q6 | - | 1.BOSS查扣点规则 | 统一扣点，扣减点数=1；【待确认Q6】携伴核销时扣1点还是按人数扣，需产品确认 | P0 |
| GA2-MPV-012 | 网络模板同Lounge | R1.3-品类规则 | B1已解除 | 1.BOSS查网络配置 | 与Lounge标准网络模板一致 | P1【阻塞B1】 |
| GA2-MPV-013 | 结算配置同ESIM规则 | R1.3-品类规则 | Form含税6% | 1.BOSS查结算配置 | 税率/定价维度ClientCode/含税开关与ESIM规则一致 | P1【阻塞B2】 |
| GA2-MPV-014 | 交易配置 | R1.3-品类规则+R5 | - | 1.BOSS交易配置页 | 支持超人次=否；支持信用卡核销=不支持；备注空 | P0 |

### 2.4 Swap 组合（R0）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-SWP-001 | Swap组合-Lounge+SetMeal+MPV各品类项目分别创建 | R0-Swap | Form勾选三品类组合 | 1.执行Step3 2.BOSS查项目 | Lounge/SetMeal/MPV各有独立品类项目 | P0 |
| GA2-SWP-002 | Swap组合-Lounge+MPV各品类项目分别创建 | R0-Swap | Form勾选Lounge+MPV | 同上 | 两个品类项目均创建 | P0 |
| GA2-SWP-003 | 组合共用点数 | R0-Swap | 品类项目已建+权益已配+可核销资源 | 1.通过开发者平台/BOSS构造组合内核销 2.查权益扣减 | 组合内核销统一从Swap权益扣减。注意：依赖核销链路可用，无核销环境时降级为配置对照 | P1 |
| GA2-SWP-004 | 只建部分品类项目（异常） | R0-Swap推断 | 模拟SetMeal项目缺失 | 1.执行Step5权益绑定 | 权益绑定失败或告警，不静默通过 | P1 |

---

## 三、Step 4 租户配置 Tenant（R3）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-TEN-001 | 新建租户-按Form生成 | R3-新建租户 | Form已提交 | 1.Step4选择Create New Tenant | 租户名称/所属区域按Form预填 | P0 |
| GA2-TEN-002 | 新建租户-名称/区域可自定义 | R3-新建租户 | 同上 | 1.编辑租户名称和所属区域 | 编辑生效 | P1 |
| GA2-TEN-003 | 审核通过才调SAAS创建接口 | R3-新建租户 | 同上 | 1.审核前后抓包 | 审核前无请求，审核通过后调SAAS创建租户接口 | P0 |
| GA2-TEN-004 | 创建成功SAAS可查 | R3-新建租户 | 审核已通过 | 1.执行创建 2.SAAS后台查 | 返回Tenant Code，SAAS可查到该租户 | P0 |
| GA2-TEN-005 | 复用租户-只填编码 | R3-复用租户+规则1 | 已有有效租户 | 1.选择Use Existing Tenant | 只展示编码输入框，无完整编辑区 | P0 |
| GA2-TEN-006 | 复用租户不调创建接口 | R3-复用租户 | 校验已通过 | 1.抓包 | 无SAAS创建租户请求 | P0 |
| GA2-TEN-007 | 后续步骤归属该Tenant | R3-复用租户 | 复用已确认 | 1.完成Step5-9 2.SAAS对照 | 权益/会籍/商品均归属该Tenant | P0 |
| GA2-TEN-008 | 失败可编辑重试/成功锁定 | R3-规则2/3 | - | 1.失败后修改重试 2.成功后尝试编辑 | 失败可编辑重试；成功锁定不可编辑 | P1 |
| GA2-TEN-009 | 复用租户编码跨环境（异常） | Q3-待确认 | 拿TEST租户码到UAT用 | 1.输入编码 2.提交 | 【待确认】校验规则PDF未写；预期按环境隔离拦截 | P1 |

---

## 四、Step 5 SAAS创建权益（R2.1，POST /api/tenant/global/equity/equity/add）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-EQ-001 | Single品类各建大客户权益 | R2.1-补充规则1 | Form含Esim+Fitness+MPV | 1.执行Step5 2.SAAS查权益模板 | Esim/Fitness/MPV各1条大客户权益模板 | P0 |
| GA2-EQ-002 | Topup开启加建充值权益 | R2.1-补充规则1 | Esim开启Topup | 同上 | Esim额外多1条充值权益模板 | P0 |
| GA2-EQ-003 | Swap只建1条且isCombine=true | R2.1-补充规则2 | Form为Swap组合 | 1.执行Step5 2.查权益模板 | 仅1条Swap权益模板，isCombine=true | P0 |
| GA2-EQ-004 | equityExpirationType=6 | R2.1-关键字段 | - | 1.查权益详情 | 有效期类型=6（随会籍过期） | P0 |
| GA2-EQ-005 | Epass的isShare固定true | R2.1-关键字段 | ePASS单 | 同上 | isShare=true | P0 |
| GA2-EQ-006 | Membership的isShare跟Form-开 | R2.1-关键字段 | Form Share=开 | 同上 | isShare=true | P1 |
| GA2-EQ-007 | Membership的isShare跟Form-关 | R2.1-关键字段 | Form Share=关 | 同上 | isShare=false | P1 |
| GA2-EQ-008 | isInfinite/equityNum仅共享时传 | R2.1-关键字段 | 共享/非共享各一组 | 1.抓包看请求体 | 共享时传isInfinite/equityNum；非共享不传；epass不传isInfinite | P1 |
| GA2-EQ-009 | Single命名-Epass | R2.1-权益命名 | ePASS+Esim，Cardhold2-Guest1 | 1.查权益名称 | 【Esim】ProgramName-Epass-Cardhold2-Guest1 | P0 |
| GA2-EQ-010 | Single命名-Membership共享 | R2.1-权益命名 | Membership+MPV，Share5 | 同上 | 【MPV】ProgramName-Membership-Share5 | P1 |
| GA2-EQ-011 | Swap命名 | R2.1-权益命名 | Swap=Lounge+MPV | 同上 | 【Swap-Lounge&MPV】ProgramName-... | P0 |
| GA2-EQ-012 | Topup命名 | R2.1-权益命名 | Esim Topup | 同上 | 【Esim Topup】ProgramName-membership | P1 |
| GA2-EQ-013 | Swap绑品类-Lounge+SetMeal只绑Lounge | R2.1-Swap选品类项目 | 组合=L+S | 1.查categoryProjectInfos | 只绑Lounge一个品类项目 | P0 |
| GA2-EQ-014 | Swap绑品类-L+S+M绑Lounge+MPV | R2.1-Swap选品类项目 | 组合=L+S+M | 同上 | 绑Lounge+MPV两个品类项目 | P0 |
| GA2-EQ-015 | Swap绑品类-L+M绑Lounge+MPV | R2.1-Swap选品类项目 | 组合=L+M | 同上 | 绑Lounge+MPV两个品类项目 | P0 |
| GA2-EQ-016 | 标签-含SetMeal勾SetMeal | R2.1-标签 | 组合含SetMeal | 1.查权益标签 | 勾选SetMeal标签 | P1 |
| GA2-EQ-017 | 标签-Swap组合勾Swap | R2.1-标签 | L+S或含MPV的Swap | 同上 | 勾选Swap标签 | P1 |
| GA2-EQ-018 | 标签-Topup勾充值 | R2.1-标签 | 有Topup权益 | 同上 | 勾选充值标签 | P1 |
| GA2-EQ-019 | 优先级-大客户1/充值2 | R2.1 | 有Topup | 1.查权益priority | 大客户priority=1，充值priority=2 | P0 |
| GA2-EQ-020 | 权益类型 | R2.1 | - | 同上 | 大客户权益=大客户；充值权益=充值 | P1 |
| GA2-EQ-021 | 创建后自动上架 | R2.1-上架 | 权益已建 | 1.查权益状态 2.抓包 | 调/api/tenant/equity/equity/updateStatus，equityStatus=2，SAAS=已上架 | P0 |
| GA2-EQ-022 | 品类项目编码不存在（异常） | R2.1推断 | 构造错误项目编码 | 1.执行Step5 | 创建失败并给出明确提示 | P1 |
| GA2-EQ-023 | 重复执行Step5幂等 | Q4-待确认 | 已成功执行过 | 1.再次执行Step5 | 【待确认Q4】预期不产生重复权益模板 | P1 |

---

## 五、Step 6 SAAS创建会籍（R2.2，/api/tenant/member/memberShipTemplate/saveOrUpdate）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-MBR-001 | ePASS每品类1个会籍模板 | R2.2-对照表 | ePASS单含Esim+MPV | 1.执行Step6 2.SAAS查会籍模板 | 2个会籍模板，每品类1个 | P0 |
| GA2-MBR-002 | ePASS模板只绑本品类权益 | R2.2-对照表 | 同上 | 1.查模板绑定关系 | 每个模板仅绑该品类1个权益模板 | P0 |
| GA2-MBR-003 | ePASS命名 | R2.2-对照表 | Esim | 1.查模板名称 | DP API-Epass-Esim-ProgramName | P0 |
| GA2-MBR-004 | ePASS标签=E-pass | R2.2-对照表 | - | 1.查模板标签 | 勾选E-pass标签 | P1 |
| GA2-MBR-005 | Membership全单仅1个模板 | R2.2-对照表 | Membership单含三品类+Topup | 1.执行Step6 | 仅1个会籍模板 | P0 |
| GA2-MBR-006 | Membership绑全部权益 | R2.2-对照表 | 同上 | 1.查绑定关系 | 绑全部品类大客户权益+Topup权益 | P0 |
| GA2-MBR-007 | Membership命名/标签 | R2.2-对照表 | - | 1.查名称和标签 | DP API-Membership-ProgramName，不选标签 | P1 |
| GA2-MBR-008 | 会籍码规则=DAMM | R2.2-其它固定 | - | 1.查模板配置 | 国际会籍码DAMM | P1 |
| GA2-MBR-009 | 有效期=固定12个月 | R2.2-其它固定 | - | 同上 | 固定时长12个月 | P0 |
| GA2-MBR-010 | 自动启用开/状态启用 | R2.2-其它固定 | - | 同上 | 自动启用=开，状态=启用 | P1 |
| GA2-MBR-011 | 预制会籍模式关 | R2.2-其它固定 | - | 同上 | 预制会籍模式=关 | P2 |
| GA2-MBR-012 | 删除后再注册=重发初始权益 | R2.2-其它固定 | - | 同上 | 配置为重发初始权益（注意：存在权益重置被滥用风险，需与业务确认是否预期） | P1 |
| GA2-MBR-013 | 绑未上架权益（异常） | R2.2推断 | 权益未上架 | 1.执行Step6 | 按预期提示或绑定失败，不静默成功 | P1 |

---

## 六、Step 7 会籍商品（R2.2，仅ePASS）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-P7-001 | ePASS每品类1个会籍商品 | R2.2-对照表 | ePASS单两品类 | 1.执行Step7 2.SAAS查商品 | 2个会籍商品，与会籍模板一一对应 | P0 |
| GA2-P7-002 | 会籍商品已上架 | R2.2-对照表 | 同上 | 1.查商品状态 | 状态=已上架 | P0 |
| GA2-P7-003 | Membership不配会籍商品 | R2.2-对照表 | Membership单 | 1.执行Step7 2.SAAS查商品 | 商品列表无新增会籍商品 | P0 |

---

## 七、Step 8 预约商品Fitness / 核销商品eSIM（R2.3）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-P8-001 | Fitness预约商品创建 | R2.3 | Form含Fitness，ProgramName=X | 1.执行Step8 2.SAAS查商品 | 商品创建成功，名称=【Fitness】X（【品类项目】ProgramName格式） | P0 |
| GA2-P8-002 | 预约商品类目/权益兑换 | R2.3 | 同上 | 1.查商品详情 | 类目=机场服务，支持权益兑换=开 | P0 |
| GA2-P8-003 | 预约商品价格由项目配置带出 | R2.3 | 项目结算已配 | 同上 | 价格与Fitness品类项目配置一致 | P1【阻塞B2】 |
| GA2-P8-004 | eSIM核销商品创建 | R2.3 | Form含ESIM | 1.执行Step8（POST /api/tenant/qr/v2/product/add） | 核销商品创建成功 | P0 |
| GA2-P8-005 | 核销商品类目=卡券 | R2.3 | 同上 | 1.查商品详情 | 类目=卡券 | P0 |
| GA2-P8-006 | 核销商品有效期 | R2.3 | 同上 | 同上 | 自购买后0天生效，有效期9999999年 | P1 |
| GA2-P8-007 | 核销商品支持权益兑换/不限库存 | R2.3 | 同上 | 同上 | 权益兑换=开，库存=不限制 | P1 |
| GA2-P8-008 | 核销商品创建后上架 | R2.3 | 同上 | 1.查状态 2.抓包 | 调batchUpdateStatus，状态=已上架 | P0 |
| GA2-P8-009 | 商品编码productCode为0（异常） | 历史缺陷 | 对照一期已知问题 | 1.查创建返回 | productCode不为0；为0则提缺陷 | P0 |
| GA2-P8-010 | 预约商品接口路径（对照） | R2.3-注 | PDF路径笔误 | 1.抓包确认实际接口 | 实际调商品接口，非会籍saveOrUpdate | P2 |

---

## 八、Step 9 接口权限与安全凭证（R2.4）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-SEC-001 | ePASS-esimsProCode写入 | R2.4 | ePASS+Esim | 1.执行Step9 2.查program配置 | programConfigObj.esimsProCode=Esim会籍模板编码 | P0 |
| GA2-SEC-002 | ePASS-fitnessProCode写入 | R2.4 | ePASS+Fitness | 同上 | fitnessProCode=Fitness会籍模板编码 | P0 |
| GA2-SEC-003 | ePASS-diningCouponProCode写入 | R2.4 | ePASS+MPV | 同上 | diningCouponProCode=MPV会籍模板编码 | P0 |
| GA2-SEC-004 | Membership-saveOrUpdateBatch | R2.4 | Membership单 | 1.抓包/查配置 | membershipTemplateCodeList包含本次会籍模板编码 | P0 |
| GA2-SEC-005 | publicKey=1 | R2.4 | - | 1.查权限配置 | publicKey=1 | P1 |
| GA2-SEC-006 | QPS=200 | R2.4 | - | 同上 | QPS=200 | P1 |
| GA2-SEC-007 | ePASS勾选对应品类产品包 | R2.4 | ePASS三品类 | 同上 | Esim/Fitness/MPV产品包均勾选 | P0 |
| GA2-SEC-008 | Membership勾Membership基准 | R2.4 | Membership单 | 同上 | 勾选Membership基准 | P0 |
| GA2-SEC-009 | 新凭证端到端验证 | R2.4推断 | Step9完成 | 1.用新clientId/secret取token 2.调开发者平台对应品类接口 | 鉴权通过，返回对应品类数据（如esims options） | P0 |
| GA2-SEC-010 | 越权访问未勾品类（异常） | R2.4推断 | 只勾Esim | 1.用凭证调Fitness接口 | 返回无权限类错误，不放行 | P1 |

---

## 九、Step 10 Agent Portal 权限（R2.5）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-AP-001 | Enable Agent Portal Permission执行成功 | R2.5 | Step1-9完成 | 1.执行Step10 | 步骤执行成功无报错（对照PRD SSAP20-123） | P0 |
| GA2-AP-002 | Agent Portal可见该Program | R2.5推断 | 步骤成功 | 1.登录Agent Portal | 可查到该Program及对应权益；Portal侧未就绪时需拉齐验收口径 | P1 |
| GA2-AP-003 | 重复开启（异常） | R2.5推断 | 已开启过 | 1.再次执行Step10 | 不报错、不重复授权 | P1 |

---

## 十、其他交互（R4）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-OTH-001 | Lounge Pricing Model配置 | R4+Q5 | Form含Lounge | 1.选择价格模型 2.BOSS/SAAS对照 | 【待确认Q5】PDF仅一句"要支持"，模型枚举与联动规则需产品补PRD | P1 |
| GA2-OTH-002 | Others展示Upload File入口 | R4 | - | 1.打开Others区块 | Others后展示Upload File，交互对齐DP APP | P1 |
| GA2-OTH-003 | 上传合法文件 | R4 | pdf/png | 1.上传文件 | 上传成功，可回查下载 | P1 |
| GA2-OTH-004 | 非法格式或超大文件（异常） | R4推断 | exe/超限文件 | 1.上传 | 合理提示，不上传 | P2 |

---

## 十一、通用-环境与回归（R5）

| 用例编号 | 用例标题 | 需求出处 | 前置条件/测试数据 | 操作步骤 | 预期结果 | 优先级 |
|----------|----------|----------|------------------|----------|----------|--------|
| GA2-ENV-001 | 品类码环境对照表核对 | R5 | 三环境均可访问 | 1.逐环境核对Step3落库 | eSIM=ISC00270/ISC00001/ISC00000；Fitness=IGC00013/IGC00005/IGC00003；MPV=NPMPV00031/NPMPV00028/NPMPV00029 | P0 |
| GA2-ENV-002 | 一期Lounge/FastTrack/SetMeal回归 | R0 | 二期已上线UAT | 1.跑一期主流程用例 | 一期自动化配置全流程不受影响 | P0 |
| GA2-ENV-003 | 交易配置三件套回归（全品类） | R5 | - | 1.各品类BOSS交易页核对 | PAYG/COF/Ingenico均有值（空下拉=传参失败缺陷） | P0 |
| GA2-ENV-004 | 网络模板阻塞B1补测 | R1.1/R1.3 | 产品已提供编码 | 1.补测ESIM/MPV网络落库 | Standard Network与Form选中一致；注意模板编码按环境隔离，需确认给的是哪个环境的码 | P1【阻塞B1】 |
| GA2-ENV-005 | 价格模板阻塞B2补测 | R1.1/R1.2 | John King团队已提供 | 1.补测结算配置 | 客户/用户定价模板正确 | P1【阻塞B2】 |
| GA2-ENV-006 | 全步骤重复执行幂等性 | Q4-待确认 | 单已成功跑完一遍 | 1.Form改字段（如Cancellation Rule 1天改7天）后整体重跑 | 【待确认Q4】预期已建配置被更新而非重复创建；更新策略PDF未定义，需开发确认后固化预期 | P1 |

---

## 十二、需求覆盖矩阵（按需求过用例用）

> 用法：逐行核对「需求条目 → 用例」，覆盖状态为「待确认/阻塞」的先解决再执行。

### R1.1 ESIM

| 需求条目 | 对应用例 | 覆盖状态 |
|----------|----------|----------|
| 项目名称【Esim】{ProgramName} | GA2-ESM-001 | ✅ |
| 环境品类码 ISC00000/ISC00001/ISC00270 | GA2-ESM-002/003/004 | ✅ |
| JSON要点 businessType/business/续期/状态 | GA2-ESM-005/006 | ✅ |
| 订单完成=确认使用时完成 | GA2-ESM-007 | ✅ |
| 订单取消=按时间+按状态 | GA2-ESM-008 | ✅ |
| 取消时间=Cancellation Rule 1/3/7天 | GA2-ESM-009/010/011 | ✅ |
| 取消状态=未完成 | GA2-ESM-012 | ✅ |
| 下单间隔=Entitlement Order Limit | GA2-ESM-013/014 | ⚠️ 014待确认Q1 |
| 网络模板=Standard Network取Form | GA2-ESM-015/016 | ⛔ 阻塞B1 |
| 税率=Tax Treatment | GA2-ESM-017/018 | ⛔ 阻塞B2 |
| 定价维度=ClientCode | GA2-ESM-019 | ⛔ 阻塞B2 |
| 客户/用户定价含税跟Tax Treatment | GA2-ESM-020 | ⛔ 阻塞B2 |
| 交易配置 PAYG/COF/Ingenico | GA2-ESM-021/022 | ✅ |
| 备注无需填写 | GA2-ESM-023 | ✅ |

### R1.2 Fitness

| 需求条目 | 对应用例 | 覆盖状态 |
|----------|----------|----------|
| 项目名称【Fitness】{ProgramName} | GA2-FIT-001 | ✅ |
| 环境品类码 IGC00003/00005/00013 | GA2-FIT-002/003 | ✅ |
| PDF示例IGC00002以环境表为准 | GA2-FIT-004 | ✅ |
| 退订=允许 | GA2-FIT-005 | ✅ |
| 取消时间两种取值 | GA2-FIT-006/007 | ✅ |
| 取消状态=待确认/待使用 | GA2-FIT-008 | ✅ |
| 下单间隔=Entitlement Order Limit | GA2-FIT-009 | ✅ |
| 网络模板=BOSS_T000727 | GA2-FIT-010 | ✅ |
| 税率固定0 | GA2-FIT-011 | ✅ |
| 币种=Settlement Currency | GA2-FIT-012 | ✅ |
| 结算类型/时间/定价模式/维度/模板 | GA2-FIT-013/014 | ⛔ 014阻塞B2 |
| 交易配置+超人次否+信用卡核销否 | GA2-FIT-015 | ✅ |
| 跟随协议续期需问AM | GA2-FIT-016 | ⚠️ 待确认Q2 |

### R1.3 MPV

| 需求条目 | 对应用例 | 覆盖状态 |
|----------|----------|----------|
| 项目名称【MPV】{ProgramName} | GA2-MPV-001 | ✅ |
| 环境品类码 NPMPV00029/00028/00031 | GA2-MPV-002/003 | ✅ |
| 实名规则三态 | GA2-MPV-004/005/006 | ✅ |
| 核销间隔=Verification | GA2-MPV-007 | ✅ |
| 携伴规则三态 | GA2-MPV-008/009/010 | ✅ |
| 扣点固定1点 | GA2-MPV-011 | ⚠️ 携伴扣点待确认Q6 |
| 网络=同Lounge标准模板 | GA2-MPV-012 | ⛔ 阻塞B1 |
| 结算同ESIM | GA2-MPV-013 | ⛔ 阻塞B2 |
| 交易配置 | GA2-MPV-014 | ✅ |

### R0 Swap

| 需求条目 | 对应用例 | 覆盖状态 |
|----------|----------|----------|
| 组合内各品类项目分别创建 | GA2-SWP-001/002 | ✅ |
| 共用点数 | GA2-SWP-003 | ✅（依赖核销链路） |
| 权益模板只建1份isCombine=true | GA2-EQ-003 | ✅ |

### R2.1 创建权益

| 需求条目 | 对应用例 | 覆盖状态 |
|----------|----------|----------|
| Single品类建大客户权益 | GA2-EQ-001 | ✅ |
| Topup开启加建充值权益 | GA2-EQ-002 | ✅ |
| Swap只建1条isCombine=true | GA2-EQ-003 | ✅ |
| equityExpirationType=6 | GA2-EQ-004 | ✅ |
| Epass isShare=true | GA2-EQ-005 | ✅ |
| Membership isShare跟Form | GA2-EQ-006/007 | ✅ |
| isInfinite/equityNum仅共享时传 | GA2-EQ-008 | ✅ |
| 命名规则 Single/Swap/Topup | GA2-EQ-009/010/011/012 | ✅ |
| Swap绑品类项目三种组合 | GA2-EQ-013/014/015 | ✅ |
| 标签 SetMeal/Swap/充值 | GA2-EQ-016/017/018 | ✅ |
| 优先级1/2、权益类型 | GA2-EQ-019/020 | ✅ |
| 创建后上架equityStatus=2 | GA2-EQ-021 | ✅ |

### R2.2 创建会籍 + Step7

| 需求条目 | 对应用例 | 覆盖状态 |
|----------|----------|----------|
| ePASS每品类1个/只绑本品类权益/命名/标签 | GA2-MBR-001~004 | ✅ |
| Membership全单1个/绑全部权益/命名/不选标签 | GA2-MBR-005/006/007 | ✅ |
| 固定配置 DAMM/12个月/自动启用/预制关/重发权益 | GA2-MBR-008~012 | ✅ |
| ePASS每品类1个会籍商品 | GA2-P7-001/002 | ✅ |
| Membership不配会籍商品 | GA2-P7-003 | ✅ |

### R2.3 预约/核销商品

| 需求条目 | 对应用例 | 覆盖状态 |
|----------|----------|----------|
| Fitness预约商品 名称/类目/权益兑换/价格 | GA2-P8-001/002/003 | ✅（003阻塞B2） |
| eSIM核销商品 创建/类目/有效期/兑换/库存/上架 | GA2-P8-004~008 | ✅ |
| PDF接口路径笔误以实际为准 | GA2-P8-010 | ✅ |

### R2.4 接口权限与凭证

| 需求条目 | 对应用例 | 覆盖状态 |
|----------|----------|----------|
| ePASS三个ProCode写入 | GA2-SEC-001/002/003 | ✅ |
| Membership membershipTemplateCodeList | GA2-SEC-004 | ✅ |
| publicKey=1/QPS=200 | GA2-SEC-005/006 | ✅ |
| 产品包勾选 | GA2-SEC-007/008 | ✅ |

### R2.5 / R3 / R4 / R5

| 需求条目 | 对应用例 | 覆盖状态 |
|----------|----------|----------|
| R2.5 Agent Portal | GA2-AP-001/002/003 | ✅（002依赖外部PRD） |
| R3 新建协议 | GA2-AGR-001~007 | ✅ |
| R3 复用协议 | GA2-AGR-101~105 | ✅ |
| R3 规则1/2/3 | GA2-AGR-001/006/007/101/105、GA2-TEN-005/008 | ✅ |
| R3 新建/复用租户 | GA2-TEN-001~007 | ✅ |
| R4 Lounge Pricing Model | GA2-OTH-001 | ⚠️ 待确认Q5 |
| R4 Upload File | GA2-OTH-002/003/004 | ✅ |
| R5 品类码不串环境 | GA2-ENV-001 | ✅ |
| R5 交易配置对照 | GA2-ENV-003 | ✅ |

---

## 十三、待确认需求点（执行前找产品/开发确认）

| 编号 | 待确认问题 | 影响用例 | 建议确认人 |
|------|-----------|----------|-----------|
| Q1 | ESIM下单间隔：Form未开启Entitlement Order Limit时传什么值（null/0/不传字段）？PDF只写"按文档占位" | GA2-ESM-014 | 产品 |
| Q2 | Fitness"跟随协议续期"默认值：不确定先选"是"是否可接受 | GA2-FIT-016 | AM/产品 |
| Q3 | 复用协议/租户时，协议币种、税率、客户归属与Form的一致性校验规则 | GA2-AGR-108、GA2-TEN-009 | 产品/开发 |
| Q4 | 重复执行/Form改字段重跑时，已建BOSS/SAAS配置的更新策略（新建/覆盖/报错） | GA2-ESM-024、GA2-EQ-023、GA2-ENV-006 | 开发 |
| Q5 | Lounge Pricing Model 有哪些模型、与结算配置如何联动（PDF仅一句话） | GA2-OTH-001 | 产品 |
| Q6 | MPV携伴核销时扣点：统一扣1点还是按人数扣 | GA2-MPV-011 | 产品 |
| Q7 | 协议/租户审核驳回后的流转：能否编辑再提交 | GA2-AGR-012 | 产品/开发 |
| Q8 | B1/B2模板编码按环境隔离：提供编码时需注明适用环境（Test/UAT/PROD） | GA2-ENV-004/005 | 产品/John King团队 |

---

## 附录A：品类码环境对照（禁止串环境）

| 品类 | Test | UAT | 生产 |
|------|------|-----|------|
| eSIM | ISC00270（mai-Sim品类） | ISC00001（国际通用卡券eSim） | ISC00000（国际通用卡券eSim） |
| Fitness | IGC00013 | IGC00005（BODDY Gym） | IGC00003 |
| MPV | NPMPV00031 | NPMPV00028（新平台MVPPCS） | NPMPV00029 |

## 附录B：关键接口清单

| 步骤 | 接口 |
|------|------|
| Step3 品类项目 | POST /api/project/batchAdd |
| Step5 创建权益 | POST /api/tenant/global/equity/equity/add |
| Step5 权益上架 | /api/tenant/equity/equity/updateStatus（equityStatus=2） |
| Step6 会籍模板 | /api/tenant/member/memberShipTemplate/saveOrUpdate |
| Step8 eSIM核销商品 | POST /api/tenant/qr/v2/product/add + batchUpdateStatus |
| Step9 ePASS凭证 | /api/tenant/sys/program/saveOrUpdate |
| Step9 Membership凭证 | /api/tenant/sys/program/saveOrUpdateBatch |
| Step9 权限 | updateGroupConfigInfo |

## 附录C：当前阻塞项

| 编号 | 阻塞项 | 等待方 | 影响用例 |
|------|--------|--------|----------|
| B1 | 标准网络模板编码（ESIM/MPV） | 产品 | GA2-ESM-015/016、GA2-MPV-012、GA2-ENV-004 |
| B2 | 标准价格模板 | John King 团队 | GA2-ESM-017~020、GA2-FIT-014、GA2-MPV-013、GA2-P8-003、GA2-ENV-005 |
