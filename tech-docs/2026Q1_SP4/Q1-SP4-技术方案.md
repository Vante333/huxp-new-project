# Q1-SP4 技术方案

> 来源：[Confluence - Q1-SP4 技术方案](https://dragonpass.atlassian.net/wiki/spaces/DGSN/pages/1492779221/Q1-SP4)

---

## 一、需求文档

- [PAPI-2214](https://dragonpass.atlassian.net/browse/PAPI-2214)
- [PAPI-2352](https://dragonpass.atlassian.net/browse/PAPI-2352)

---

## 二、技术方案

### 2.1 会籍注册和权益查询接口的权益查询（通用代码逻辑）

> **查询所有权益模板下面是否设置了等级权益，有则置空 `maxGuestsNextUse` 和 `allowedGuestsPerUsage` 字段，没有则按旧逻辑计算**

![权益查询逻辑](images/image-20260302-031359.png)

#### 2.1.1 时序图

![权益查询时序图](images/queryEq-shixutu-handlerExclusiveEntitlement-20260206-101645.png)

#### 2.1.2 整体流程图

![权益查询整体流程图](images/queryEq-handlerExclusiveEntitlement_-20260206-055033.png)

---

### 2.2 权益明细接口

接口路径：`/v2/entitlements/update`

#### 2.2.1 时序图

> **分级权益一句话概括：就是过滤出指定等级的权益，然后进行 update**

![权益更新时序图](images/entitlementsupdateV2-_v2_entitlements_update__-20260302-024652.png)

**整个接口时序图：**

![权益更新整体时序图](images/queryEqupdate-shixutu-Tier-20260206-101035.png)

#### 2.2.2 整体业务图

![权益更新整体业务图](images/queryEqupdate-Tier-20260206-093851.png)

---

### 2.3 权益明细接口

#### 2.3.1 时序图

![权益明细时序图](images/entitlements-details-ds-_v2_entitlements_details__-20260302-075716.png)

---

### 2.4 放开语种限制

#### 2.4.1 全局拦截器时序图

会在全局拦截器中去除权限语种的限制。

![全局拦截器时序图](images/diagram-7580946029805101431-20260227-075745.png)

#### 2.4.2 影响范围

在全局拦截器中修改，所以调个别场景回归即可。
