# PAPI-3218 routeTypes美国跨境区

## 休息室

BOSS对照｜机场贵宾供应链 → 该网点 → 出发类型

操作：BOSS 把休息室网点的出发类型配成美国跨境区，记下 resourceId 和机场三字码。只有配了这个类型的网点，routeTypes 才包含 7。

### RetrieveResources查询资源列表 GET /v2/resources

#### 返回校验

##### tc-p0: 美国跨境区休息室列表含7 (PAPI-3218)

- module 传休息室
- 目标网点 extra.loungeInfo.routeTypes 包含 7
- 7 表示美国跨境区
- 同一列表里未配美国跨境区的网点不出现 7

##### tc-p1: 旧出发类型休息室列表不含7 (PAPI-3218)

- 出发类型仍是国际或国内的出港、到港、中转
- extra.loungeInfo.routeTypes 只含 1 到 6
- 不包含 7

#### 业务逻辑

##### tc-p1: 休息室同时配旧类型和美国跨境区 (PAPI-3218)

- BOSS 出发类型同时包含原有类型和美国跨境区
- extra.loungeInfo.routeTypes 同时含原数字和 7
- 数字按从小到大排列

### RetrieveResourceDetails查询资源详情 GET /v2/resources/{resourceId}

#### 返回校验

##### tc-p0: 美国跨境区休息室详情含7 (PAPI-3218)

- 打开已配美国跨境区的休息室 resourceId
- extra.loungeInfo.routeTypes 包含 7
- 与列表里同一网点的 routeTypes 一致

##### tc-p1: 未配美国跨境区的休息室详情不含7 (PAPI-3218)

- extra.loungeInfo.routeTypes 只含 1 到 6
- 不包含 7

### RetrieveTransportHubResources按IATA查枢纽下资源 GET /v2/transportHubs/iata/{iata}/resources

操作：这个接口只返回休息室。快速安检、餐厅、eSIM、健身、Local Offer 不会出现在 resourcesList 里。

#### 返回校验

##### tc-p0: 美国跨境区休息室在机场网点里含7 (PAPI-3218)

- 用该休息室所在机场的三字码查询
- resourcesList 里该 resourceId 的 routeTypes 包含 7
- 与详情 extra.loungeInfo.routeTypes 一致

##### tc-p1: 该接口不返回其他品类 (PAPI-3218)

- resourcesList 里只有休息室
- 不要求快速安检、餐厅在这个接口里出现 routeTypes

## 快速安检

BOSS对照｜机场贵宾供应链 → 该网点 → 出发类型

操作：另找一个出发类型为美国跨境区的快速安检网点。不要用按机场三字码查资源的接口验这个品类。

### RetrieveResources查询资源列表 GET /v2/resources

#### 返回校验

##### tc-p1: 美国跨境区快速安检列表含7 (PAPI-3218)

- module 传快速安检
- 目标网点 extra.fastTrackInfo.routeTypes 包含 7

### RetrieveResourceDetails查询资源详情 GET /v2/resources/{resourceId}

#### 返回校验

##### tc-p1: 美国跨境区快速安检详情含7 (PAPI-3218)

- extra.fastTrackInfo.routeTypes 包含 7
- 与列表一致

## 餐厅

BOSS对照｜机场贵宾供应链 → 该网点 → 出发类型

操作：套餐、券、折扣里任选一个已配美国跨境区的网点。三者共用同一套出发类型转换，测一个即可。不要用按机场三字码查资源的接口验餐厅。

### RetrieveResources查询资源列表 GET /v2/resources

#### 返回校验

##### tc-p1: 美国跨境区餐厅列表含7 (PAPI-3218)

- 目标网点 extra.diningInfo.routeTypes 包含 7

### RetrieveResourceDetails查询资源详情 GET /v2/resources/{resourceId}

#### 返回校验

##### tc-p1: 美国跨境区餐厅详情含7 (PAPI-3218)

- extra.diningInfo.routeTypes 包含 7
- 与列表一致

## 无出发类型的品类

### RetrieveResourceDetails查询资源详情 GET /v2/resources/{resourceId}

#### 返回校验

##### tc-p1: eSIM健身LocalOffer没有routeTypes (PAPI-3218)

- 分别打开 eSIM、健身、Local Offer 各一个网点详情
- 返回里没有 routeTypes
- 不出现 7
