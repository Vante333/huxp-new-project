# Resource接口性能优化技术方案

来源：<https://dragonpass.atlassian.net/wiki/spaces/DGSN/pages/1720418344/Resource>

---

## 1. 方案概述

针对 getResources 接口高并发下因大对象频繁创建导致 GC 压力大、TPS 低的问题，引入 Caffeine 本地缓存 + Redis 分布式缓存 的二级缓存架构。将 program 级网络资源查询拆解为 project 级粒度，每个 project 的资源数据独立缓存，大幅减少序列化开销和 GC 次数。

## 2. 当前问题回顾

- 每次请求需加载 program 下所有 project 的完整网络资源 Map（1MB+），反序列化后提取资源 ID 列表。
- 高并发下大量大对象分配在年轻代 -> 频繁 YGC -> CPU 飙升 -> TPS 仅 102。
- 原有 @DataCacheable 仅有一级 Redis 缓存，未使用本地缓存，每次命中仍需反序列化整个 Map。

## 3. 优化目标指标

| 指标 | 当前现状 | 目标 |
| --- | --- | --- |
| TPS | 102 | >=200 |
| P95 延迟 | 1427ms | <= 500ms |
| YGC频率 | >5次/秒 | <1次/10秒 |
| Full GC | 偶发 | 0 |

## 4. 技术架构

### 4.1 整体设计

### 4.2 缓存层级说明

| 层级 | 实现 | TTL | 作用 |
| --- | --- | --- | --- |
| L1 本地缓存 | Caffeine | 900s | 减少 Redis 反序列化，避免大对象重复 |
| L2 分布式缓存 | Redis | 900s | 跨节点共享，减少后端调用 |
| L3 数据源 | Boss接口 | - | 最终数据来源 |

### 4.3 缓存key设计

本地缓存key：

```text
{tenantCode}:{projectId}:{categoryType}:{moduleType}:{language}
示例: dragonpass:proj_123:IL:1:en_US
```

Redis缓存key：

```text
basedata:tenantResource:v1{tenantCode}:{projectId}:{type}:{language}
```

## 5. 核心实现

### 5.1 本地缓存管理类

```text
    private final Cache>> cache = Caffeine.newBuilder()
            .expireAfterWrite(900, TimeUnit.SECONDS)
            .maximumSize(5000)
            .recordStats()
            .build();
 // get/put/clearAll/stats 方法
```

### 5.2 带二级缓存的 Program 级查询

- 获取 ProgramConfig，提取所有 (projectId, categoryType, moduleType) 组合（去重）。
- 对每个组合构造本地缓存 key，先查 Caffeine。
- 未命中则调用 getNetworkListBySingleProject（该方法已带 @DataCacheable Redis 缓存）。
- 将结果存入本地缓存后合并所有 project 的结果，按 module 去重返回。

```text
/**
     * 通过二级缓存（Caffeine + Redis）获取 program 下所有项目的网络资源（按模块分组）
     * @param programId  项目ID
     * @param tenantCode 租户编码
     * @return Map>
     * @author maoqichuan
     */
    public Map> getNetworkListByProgram(String programId, String tenantCode, String language) {
        log.info("查询项目网络资源清单:tenantCode={}, programId={}", tenantCode, programId);
        long startTime = System.currentTimeMillis();
        // 1. 获取 ProgramConfig
        ProgramConfig programConfig = apiProgramFacade.init(programId);
        if (Objects.isNull(programConfig)) {
            log.warn("ProgramConfig not found for programId: {}", programId);
            return Collections.emptyMap();
        }

        // 2. 收集所有需要查询的 projectId 及其对应的 categoryType + moduleType,使用 Set 去重，避免重复查询同一个 projectId
        Set queryKeys = new HashSet<>();
        List processors = Arrays.asList(
                new NetworkResourceService.ProjectConfigProcessor(programConfig.getLoungeProjectIds(),
                        GlobalCategoryType.IL, ModuleTypeEnum.LOUNGE),
                new NetworkResourceService.ProjectConfigProcessor(programConfig.getFastTrackProjectIds(),
                        GlobalCategoryType.QT, ModuleTypeEnum.CIP),
                new NetworkResourceService.ProjectConfigProcessor(programConfig.getDiningSetMealProjectIds(),
                        GlobalCategoryType.IL, ModuleTypeEnum.DINING_SET_MEAL),
                new NetworkResourceService.ProjectConfigProcessor(programConfig.getDiningCouponProjectIds(),
                        GlobalCategoryType.NPMPV, ModuleTypeEnum.DINING_COUPON),
                new NetworkResourceService.ProjectConfigProcessor(programConfig.getFitnessProjectIds(),
                        GlobalCategoryType.IGC, ModuleTypeEnum.FITNESS),
                new NetworkResourceService.ProjectConfigProcessor(programConfig.getESimsProjectIds(),
                        GlobalCategoryType.ISC, ModuleTypeEnum.ESIMS)
        );
        for (NetworkResourceService.ProjectConfigProcessor processor : processors) {
            List projectIds = processor.getProjectIds();
            if (CollUtil.isEmpty(projectIds)) {
                continue;
            }
            for (String projectId : projectIds) {
                queryKeys.add(new NetworkResourceWithCacheService.ProjectQueryKey(projectId, processor.getCategoryType(), processor.getModuleType()));
            }
        }

        // 3. 遍历每个 queryKey，从二级缓存获取数据
        Map> result = new HashMap<>();
        for (NetworkResourceWithCacheService.ProjectQueryKey key : queryKeys) {
            String cacheKey = buildLocalCacheKey(tenantCode, key.projectId, key.categoryType.getType(), key.moduleType.getType(),language );
            // 先查本地 Caffeine 缓存
            Map> projectNetwork = localCache.get(cacheKey);
            if (projectNetwork == null || projectNetwork.isEmpty()) {
                // 本地未命中，调用 Redis 一级缓存方法
                projectNetwork = SpringContextHolder.getBean(NetworkResourceWithCacheService.class).getNetworkListBySingleProject(key.projectId, key.categoryType, key.moduleType, tenantCode, language,key.moduleType.getType());
                if (CollUtil.isNotEmpty(projectNetwork)) {
                    localCache.put(cacheKey, projectNetwork);
                    log.info("Loaded project network from Redis and cached locally: projectId={}, moduleType={}",
                            key.projectId, key.moduleType.getType());
                }

                // 预警分组
                SpringUtil.getBean(NetworkResourceWarnBizService.class).warnNetworkGroup(programId, tenantCode, result);

                // 异步检测资源变更
                detectResourceChanges(programId, tenantCode, result);
            } else {
                log.info("Local cache hit for projectId={}, moduleType={}", key.projectId, key.moduleType.getType());
            }

            // 合并结果
            if (CollUtil.isNotEmpty(projectNetwork)) {
                for (Map.Entry> entry : projectNetwork.entrySet()) {
                    String module = entry.getKey();
                    List resources = entry.getValue();
                    result.computeIfAbsent(module, k -> new ArrayList<>()).addAll(resources);
                }
            }
        }

        // 4. 去重每个模块的资源id
        result.replaceAll((module, list) -> list.stream()
                .distinct()
                .collect(Collectors.toList()));
        log.info("查询项目网络资源清单完成:tenantCode={}, programId={}, cost={} ms",
                tenantCode, programId, System.currentTimeMillis() - startTime);
        return result;
    }
```

### 5.3 单项目查询 getNetworkListBySingleProject

```text
    /**
     * 根据单个项目ID、品类类型、模块类型查询网络资源列表（带缓存）
     *
     * @param projectId    项目ID
     * @param categoryType 品类类型
     * @param moduleType   模块类型
     * @param tenantCode   租户编码
     * @param language     语种
     * @param type
     * @return 模块编码 -> 资源列表的映射（通常只包含一个模块，但为保持结构一致返回Map）
     */
    @DataCacheable(key = "'basedata:tenantResource:v1' + #tenantCode+ ':' + #projectId+ ':'+ #type + ':' + #language ",
            expireAfter = 900L,
            condition = "#result != null && !#result.isEmpty()")
    public Map> getNetworkListBySingleProject(String projectId,
                                                                                   GlobalCategoryType categoryType,
                                                                                   ModuleTypeEnum moduleType,
                                                                                   String tenantCode,
                                                                                   String language, Integer type) {
        log.info("查询单个项目网络资源: projectId={}, moduleType={}, language={}", projectId, moduleType.getType(), language);
        long startTime = System.currentTimeMillis();
        // 1. 构建请求参数
        List buildNetWorkReqDtos = new ArrayList<>();
        List moduleTypes = new ArrayList<>();
        processNetWorkModuleRequest(categoryType, moduleType, projectId, buildNetWorkReqDtos, moduleTypes);

        List>>> futures = buildNetWorkReqDtos.stream()
                .map(item -> CompletableFuture.supplyAsync(() -> {
                    try {
                        NetworkResourceReqDto request = buildNetworkRequest(item.getProjectId(), item.getCategoryType(), item.getScenes(), language, null);
                        DataResponse productListBatch = salesCenterFeignClientService.findNetworksByPage(request);
                        if (CollUtil.isNotEmpty(productListBatch.getResult().getList())) {
                            List result = productListBatch.getResult().getList();
                            if (CollUtil.isNotEmpty(result)) {
                                result.forEach(x -> x.setProjectId(item.getProjectId()));
                            }
                            List finalResult = filterNetWork(result, item.getCategoryType(), item.getScenes(), tenantCode, true);
                            processNetworkCodes(finalResult, moduleType);

                            // 处理 tier
                            this.doHandleNetworkGroupTier(item.getProjectId(), finalResult);

                            // 返回按模块分类的结果
                            Map> moduleNetworks = new HashMap<>();
                            for (String module : moduleTypes) {
                                moduleNetworks.put(module, new ArrayList<>(finalResult));
                            }
                            return moduleNetworks;
                        }
                    } catch (Exception e) {
                        log.error("获取网络清单异常, 权益项: {}, 异常: {}", item.getCategoryProjectCode(), e.getMessage(), e);
                    }
                    return Collections.emptyMap();
                }, mqTaskExecutor))
                .collect(Collectors.toList());

        // 等待所有任务完成，并合并结果
        Map> resultMap = new HashMap<>();
        futures.forEach(future -> {
            try {
                Map> moduleNetworks = future.get();
                moduleNetworks.forEach((module, networks) -> {
                    resultMap.computeIfAbsent(module, k -> new ArrayList<>()).addAll(networks);
                });
            } catch (InterruptedException | ExecutionException e) {
                log.error("合并网络清单结果异常", e);
                Thread.currentThread().interrupt();
            }
        });

        // 去重每个模块的网络清单
        resultMap.replaceAll((module, networks) ->
                networks.stream().distinct().collect(Collectors.toList())
        );
        log.info("查询项目网络资源清单完成:tenantCode={}, projectId={},result={}, cost={} ms",tenantCode, projectId, JSONObject.toJSONString(resultMap), System.currentTimeMillis() - startTime);
        return resultMap;
    }
```

## 6. 缓存一致性保证

### 6.1 变更触发MQ

当 Program 配置变更（项目绑定关系、权益等）时，业务系统发送 RocketMQ 消息。

### 6.2 消费者处理

- 收到消息后，调用 apiProgramFacade.resetInit(programId) 刷新 Redis 中的 ProgramConfig。
- 调用 networkResourceWithCacheService.getNetworkListByProgram(...) 重新加载该 program 的所有 project 数据。

### 6.3 TTL兜底

本地缓存与 Redis 缓存均设置 900 秒过期。即使消息丢失，缓存也会自动失效，保证最终一致性。

### 6.4 预热机制

CacheWarmUpJob 定时任务（或手动触发）调用 getNetworkListByProgram 提前加载热点 program 数据到本地和 Redis 缓存，避免冷启动时缓存穿透。

## 7. 多节点一致性分析

- 问题：多个服务节点各自维护本地 Caffeine 缓存，变更消息需要通知所有节点。
- 现状：当前使用 RocketMQ 广播消费（PROGRAM_PROJECT_TOPIC 被所有节点监听），每个节点独立消费消息并执行 getNetworkListByProgram，从而刷新自己的本地缓存。

## 8. 影响范围

| 序号 | 接口 | 备注 |
| --- | --- | --- |
| 1 | /v2/resources | 资源查询 |
| 2 | /v2/transportHubs | 机场列表查询 |
| 3 | /v2/search | 聚合搜索接口 |
| 4 | /v2/search/modules | 查询接口 |
