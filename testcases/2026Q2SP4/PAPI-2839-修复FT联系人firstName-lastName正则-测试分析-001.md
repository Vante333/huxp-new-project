# PAPI-2839修复FT联系人firstName-lastName正则测试分析

## 测试范围说明

- rc: 基于 `requirements/2026Q2SP4/PAPI-2839.md`；覆盖 **FastTrack（FT）** 三个订单创建接口中 `prebookingRequiredInfo.firstName`、`prebookingRequiredInfo.lastName` 以及 `passengers[].firstName`、`passengers[].lastName` 的正则校验修复。
- rc: 涉及接口：`POST /v2/orders/fastTrack/ePasses/prebooking`、`POST /v2/orders/fastTrack/ePasses/bundle`、`POST /v2/orders/fastTrack/memberships/prebooking`；`module` 固定为 `fastTrack`。
- rc: 正则口径为 `^[A-Za-z ]+$`：仅允许英文字母（大小写均可）与空格；不允许数字、连字符、撇号、中文及其他非 ASCII 字母字符；上述四处姓名字段口径一致。
- rc: 本文聚焦 `prebookingRequiredInfo` 与 `passengers[]` 内姓名字段格式校验；不覆盖 `email`、`phoneNumber`、`callingCode`、`transportNumber` 等其他 PII 字段规则（如 PAPI-2387 航班号正则），也不覆盖 Lounge 品类同名接口。
- rc: 需求未明确错误码编号、以及首尾空格/纯空格字符串是否视为合法；执行前需以 Apifox 定义与研发最终实现为准。
- rc: 示例合法样本：`DragonPass`（需求原文示例）；含内部空格的 `John Smith` 亦应符合新正则。

## 需求语义归纳

| 能力 | 需求语义 | 主要风险 |
| --- | --- | --- |
| 正则修复 | `firstName` / `lastName` 统一为 `^[A-Za-z ]+$` | 旧正则过严导致合法英文名（含空格）被拒，或过宽导致非法字符进入下游 |
| 三接口一致 | 上述三个 FT 预订单/Bundle/会籍预订单接口口径一致 | 仅修复其中一个接口，其余仍用旧规则 |
| 字段范围 | 校验对象为 `prebookingRequiredInfo` 与 `passengers[]` 内姓名 | 仅改一处、另一处仍用旧规则，或误改 `extra` 顶层姓名及其他模块字段 |
| 双路径一致 | `prebookingRequiredInfo` 与 `passengers[]` 姓名字段同一正则 | 下单人姓名与同行使用人姓名一处放行一处拒绝 |
| 品类隔离 | 仅 FT 相关接口受影响 | Lounge、Local Offer 等同名字段被误改或 FT 未生效 |
| 非姓名字段 | `email`、`transportNumber` 等保持既有规则 | 修复姓名正则时连带破坏其他 PII 校验 |

## firstName与lastName正则判定表

> 适用于 `prebookingRequiredInfo` 与 `passengers[]` 中的 `firstName` / `lastName`。

| 输入值 | 归类 | 预期校验结果 |
| --- | --- | --- |
| `DragonPass` | 需求示例；纯字母 | 通过 |
| `John Smith` | 含内部空格 | 通过 |
| `JOHN`、`john` | 全大写/全小写 | 通过 |
| `A` | 单字符 | 通过 |
| `John123`、`Mary2` | 含数字 | 拒绝 |
| `Jean-Pierre`、`Mary-Jane` | 含连字符 | 拒绝 |
| `O'Brien`、`D'Angelo` | 含撇号 | 拒绝 |
| `李明`、`José`、`Müller` | 中文/重音/非 ASCII 字母 | 拒绝 |
| `John@mail`、`Test!` | 特殊符号 | 拒绝 |
| `John\tSmith`、`John\nSmith` | 空白符（非空格） | 拒绝 |
| 空字符串 `""` | 空值 | 若字段必填则按缺失处理；不因正则误放行 |
| `"   "`（纯空格，若传入） | 边界 | 技术上匹配 `^[A-Za-z ]+$`；需与研发确认是否额外拒绝纯空格 |
| `" John"` / `"John "` | 首尾空格 | 正则允许；需确认产品是否 trim 或拒绝 |

## FT预订单姓名校验（FtPrebookingRequiredInfoNameValidation）

### tc-p1: 三接口合法纯字母firstName与lastName均可通过校验

- pc: FT 沙箱可用；准备有效 `prebookingToken`、资源/会籍等其余必填字段；三个接口除路径外请求体结构符合 Apifox。
- 分别调用 `POST /v2/orders/fastTrack/ePasses/prebooking`、`POST /v2/orders/fastTrack/ePasses/bundle`、`POST /v2/orders/fastTrack/memberships/prebooking`，`prebookingRequiredInfo.firstName` 与 `lastName` 均为 `DragonPass`（或 `Auto` / `Test`）。
  - 三个接口均不因姓名格式触发参数校验错误；进入正常业务处理或返回与样本一致的成功/业务错误（非姓名正则类错误）。
- 对比需求示例报文。
  - 姓名取值与入参一致，不被截断或改写。

### tc-p1: 三接口含内部空格的合法姓名均可通过校验

- pc: 同上；其余必填字段合法。
- 分别对上述三个接口发起请求，`prebookingRequiredInfo.firstName` 为 `John Smith`，`lastName` 为 `Mary Jane`。
  - 请求通过姓名正则校验，不因内部空格被拒绝。
- 校验响应或下游持久化（若可查询）。
  - 姓名字段保留空格，符合 `^[A-Za-z ]+$` 语义。

### tc-p1: firstName含数字时三接口均被拒绝

- pc: 基础预订单请求合法，仅篡改 `prebookingRequiredInfo.firstName` 为 `John123`；`lastName` 保持合法值如 `Smith`。
- 分别调用三个 FT 接口。
  - 均返回约定参数校验错误，错误信息可定位 `firstName` 格式非法。
- 校验错误响应。
  - 不因 `lastName` 合法而误放行；错误码/错误类型在三接口间一致。

### tc-p1: lastName含连字符或撇号时三接口均被拒绝

- pc: 基础预订单请求合法；分别准备 `lastName` 为 `Jean-Pierre`、`O'Brien` 两组样本，`firstName` 保持 `John`。
- 分别对三个 FT 接口各发起上述样本请求。
  - 均返回约定参数校验错误，说明姓名不符合 `^[A-Za-z ]+$`。
- 重复同一非法样本。
  - 拒绝结果稳定，不出现偶发通过或 500。

### tc-p2: firstName含中文或非ASCII字母时被拒绝

- pc: 基础预订单请求合法。
- 分别传入 `firstName` 为 `李明`、`José`，`lastName` 为合法英文 `Smith`；对三个 FT 接口各测一组。
  - 返回参数校验错误，非法字符不被静默转写为 ASCII 后放行。
- 校验错误信息。
  - 能区分姓名字段校验失败，而非其他 PII 字段误报。

### tc-p2: lastName非法而firstName合法时仅拒绝lastName相关校验

- pc: `firstName` 为 `John`，`lastName` 分别为 `Test@`、`Smith!`。
- 分别调用三个 FT 接口。
  - 返回参数校验错误，指向 `lastName` 格式问题。
- 将 `lastName` 改回 `Smith` 后重试。
  - 不因先前非法值导致后续合法请求异常。

### tc-p2: firstName与lastName同时非法时返回明确校验错误

- pc: `firstName` 为 `123`，`lastName` 为 `456`。
- 分别调用三个 FT 接口。
  - 返回参数校验错误；至少能识别姓名格式非法（若错误信息合并需覆盖两字段）。
- 校验 HTTP 状态与业务码。
  - 不为 500；错误类型与单字段非法场景一致。

### tc-p2: 姓名字段缺失时按必填规则处理且优先于正则

- pc: 确认资源详情或 BOSS 配置要求收集姓名（`prebookingRequiredInfo` 枚举含 1、2）；基础请求除姓名外合法。
- 分别测试：`firstName` 缺失、`lastName` 缺失、两者均缺失；对三个 FT 接口各测。
  - 返回必填缺失或格式错误，不允许下单成功。
- 与 Apifox 必填定义对比。
  - 缺失场景错误语义稳定，不与「格式非法」混淆导致排查困难。

## FT乘客姓名校验（FtPassengersNameValidation）

### tc-p1: 三接口passengers合法纯字母firstName与lastName均可通过校验

- pc: FT 沙箱可用；BOSS 配置要求收集乘客信息（`passengers[]` 必填）；准备含下单人与至少一名同行使用人的合法预订单上下文；`prebookingRequiredInfo` 姓名合法。
- 分别调用三个 FT 接口，每位 `passengers[]` 元素的 `firstName` 与 `lastName` 均为 `DragonPass`（或 `Auto` / `Test`）。
  - 三个接口均不因乘客姓名格式触发参数校验错误；进入正常业务处理或返回与样本一致的成功/业务错误（非姓名正则类错误）。
- 校验响应或下游持久化（若可查询）。
  - 各乘客姓名字段与入参一致，不被截断或改写。

### tc-p1: 三接口passengers含内部空格的合法姓名均可通过校验

- pc: 同上；`prebookingRequiredInfo` 姓名合法；其余必填字段合法。
- 分别对上述三个接口发起请求，`passengers[0].firstName` 为 `John Smith`，`passengers[0].lastName` 为 `Mary Jane`；同行乘客使用另一组合法英文姓名。
  - 请求通过乘客姓名正则校验，不因内部空格被拒绝。
- 校验响应或下游持久化（若可查询）。
  - 乘客姓名字段保留空格，符合 `^[A-Za-z ]+$` 语义。

### tc-p1: passengers中firstName含数字时三接口均被拒绝

- pc: 基础预订单请求合法；`prebookingRequiredInfo` 姓名合法；仅将 `passengers[0].firstName` 设为 `John123`，`passengers[0].lastName` 保持 `Smith`。
- 分别调用三个 FT 接口。
  - 均返回约定参数校验错误，错误信息可定位 `passengers` 内 `firstName` 格式非法。
- 校验错误响应。
  - 不因 `prebookingRequiredInfo` 或同乘客 `lastName` 合法而误放行；错误码/错误类型在三接口间一致。

### tc-p1: passengers中lastName含连字符或撇号时三接口均被拒绝

- pc: 基础预订单请求合法；`prebookingRequiredInfo` 姓名合法；分别准备 `passengers[0].lastName` 为 `Jean-Pierre`、`O'Brien` 两组样本，`passengers[0].firstName` 保持 `John`。
- 分别对三个 FT 接口各发起上述样本请求。
  - 均返回约定参数校验错误，说明乘客姓名不符合 `^[A-Za-z ]+$`。
- 重复同一非法样本。
  - 拒绝结果稳定，不出现偶发通过或 500。

### tc-p2: passengers中firstName含中文或非ASCII字母时被拒绝

- pc: 基础预订单请求合法；`prebookingRequiredInfo` 姓名合法。
- 分别传入 `passengers[0].firstName` 为 `李明`、`José`，`passengers[0].lastName` 为合法英文 `Smith`；对三个 FT 接口各测一组。
  - 返回参数校验错误，非法字符不被静默转写为 ASCII 后放行。
- 校验错误信息。
  - 能区分 `passengers` 姓名字段校验失败，而非 `prebookingRequiredInfo` 或其他 PII 字段误报。

### tc-p2: passengers中lastName非法而firstName合法时仅拒绝lastName相关校验

- pc: `prebookingRequiredInfo` 姓名合法；`passengers[0].firstName` 为 `John`，`passengers[0].lastName` 分别为 `Test@`、`Smith!`。
- 分别调用三个 FT 接口。
  - 返回参数校验错误，指向 `passengers` 内 `lastName` 格式问题。
- 将 `passengers[0].lastName` 改回 `Smith` 后重试。
  - 不因先前非法值导致后续合法请求异常。

### tc-p2: passengers多元素时任一乘客姓名非法均被拒绝

- pc: 请求含 `passengers[0]`（下单人）与 `passengers[1]`（同行使用人）；`prebookingRequiredInfo` 与 `passengers[0]` 姓名均合法。
- 将 `passengers[1].firstName` 设为 `Bad123` 或 `passengers[1].lastName` 设为 `Jean-Pierre`；分别调用三个 FT 接口。
  - 均返回约定参数校验错误，可定位至非法乘客条目及其姓名字段。
- 修正 `passengers[1]` 姓名为合法英文后重试。
  - 不因先前非法值导致后续合法请求异常。

### tc-p2: passengers姓名字段缺失时按必填规则处理且优先于正则

- pc: BOSS 配置要求收集乘客姓名；基础请求除 `passengers` 姓名外合法；`prebookingRequiredInfo` 姓名合法。
- 分别测试：`passengers[0].firstName` 缺失、`passengers[0].lastName` 缺失、两者均缺失；对三个 FT 接口各测。
  - 返回必填缺失或格式错误，不允许下单成功。
- 与 Apifox 必填定义对比。
  - 缺失场景错误语义稳定，不与「格式非法」混淆导致排查困难。

## 品类隔离与字段回归（FtNameRegexRegression）

### tc-p2: Lounge同路径接口不受FT姓名正则修复影响

- pc: Lounge 预订单接口 `POST /v2/orders/lounge/ePasses/prebooking`（及同结构 bundle/memberships 若存在）可访问；准备 Lounge 合法预订单上下文。
- 使用 Lounge 合法姓名样本（若 Lounge 允许非 `^[A-Za-z ]+$` 格式，如含连字符或中文）调用 Lounge 接口。
  - Lounge 行为与 FT 修复前基线一致，不因 FT 正则调整被误伤。
- 使用 FT 非法、Lounge 可能合法的样本对比 FT 接口。
  - FT 仍按 `^[A-Za-z ]+$` 拒绝，品类隔离正确。

### tc-p2: prebookingRequiredInfo其他字段校验不受姓名正则修复影响

- pc: 姓名使用合法值 `DragonPass`；分别构造 `email` 非法、`transportNumber` 非法（参考 PAPI-2387）、`phoneNumber` 非法等样本。
- 对三个 FT 接口分别发起请求。
  - 仍按各字段既有规则拒绝，不因姓名正则修复导致其他字段校验失效或误放行。
- 全部 PII 合法时重试。
  - 正常进入业务处理，姓名与其他字段校验互不干扰。

### tc-p2: prebookingRequiredInfo与passengers姓名字段正则口径一致

- pc: FT 请求体同时含 `prebookingRequiredInfo` 与 `passengers[]` 姓名字段；其余必填字段合法。
- 将 `prebookingRequiredInfo.firstName` 设为 `Bad123`，`passengers[]` 姓名均合法；调用三个 FT 接口。
  - 返回参数校验错误，拒绝 `prebookingRequiredInfo` 非法姓名。
- 将 `prebookingRequiredInfo` 姓名改回合法，将 `passengers[0].firstName` 设为 `Bad123` 后重试。
  - 同样返回参数校验错误，拒绝 `passengers` 非法姓名；两处校验规则均为 `^[A-Za-z ]+$`，无口径分裂。

### tc-p3: 超长纯字母姓名边界行为符合产品约定

- pc: 准备长度接近或达到字段上限的纯字母字符串（如 64/128 字符，以 Apifox maxLength 为准）。
- 对三个 FT 接口分别传入：`prebookingRequiredInfo.firstName` 为该超长串；`passengers[0].firstName` 为另一组未超长纯字母合法值。
  - 若未超 maxLength 则通过正则；若超长则返回长度校验错误而非 500。
- 将超长串改用于 `passengers[0].firstName` 后重试。
  - `passengers` 与 `prebookingRequiredInfo` 长度校验行为一致，错误可区分于正则类错误。

### tc-p3: 单字符与大小写混合姓名稳定通过

- pc: 样本：`firstName`=`A`，`lastName`=`b`；`firstName`=`McDonald`（无空格混合大小写）；分别在 `prebookingRequiredInfo` 与 `passengers[0]` 各测一组。
- 对三个 FT 接口参数化调用。
  - 均通过 `^[A-Za-z ]+$` 校验。
- 校验持久化或响应回显。
  - 大小写原样保留，不被强制转换。

### tc-p3: 网关层与业务层对姓名正则口径一致

- pc: 若存在 API 网关 schema 校验与业务层二次校验，可观察错误来源或日志。
- 通过正式入口对三个 FT 接口分别传入：`prebookingRequiredInfo` 非法姓名 `Test1`；`passengers[0]` 非法姓名 `Test1`；合法对照组 `Test`。
  - 非法样本在网关或业务任一层均被一致拒绝；合法样本不被任一层误拦。
- 检查访问日志。
  - 合法 `John Smith` 流量不误记为参数异常。
