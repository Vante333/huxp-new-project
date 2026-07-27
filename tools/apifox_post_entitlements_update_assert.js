/**
 * =============================================================================
 * Apifox 后置脚本：校验 POST /v2/entitlements/{entitlementPoolId}/update 的响应
 * =============================================================================
 *
 * 【挂载位置】
 *   必须挂在「/v2/entitlements/{{ENTITLEMENT_POOL_ID}}/update」请求的「后置操作」中，
 *   且该请求须在 memberships 后置脚本已成功写入环境变量之后执行（同一场景、同一环境）。
 *
 * 【前置依赖 — 须已由 memberships 后置脚本（或等价步骤）写入】
 *   - ENTITLEMENT_POOL_ID     本次更新的路径参数，用于在响应 crossModuleEntitlements[].pools[] 中定位池子
 *   - MEMBERSHIP_ID           期望响应 data.membershipId 与之完全一致
 *   - ENTITLEMENT_UPDATE_SCENARIO  purchased | normal（决定可选的深度断言分支）
 *   - 当为 normal：USAGE_RESTRICTION（1/2/3）、ENTITLEMENT_UPDATE_QUANTITY（请求中的 quantity），以及
 *     ENTITLEMENT_POOL_SNAPSHOT_CARDHOLDER / _GUEST / _SHARED（memberships 返回中选池当时的三项计数）
 *   - 当为 purchased：ENTITLEMENT_UPDATE_QUANTITY、ENTITLEMENT_POOL_SNAPSHOT_PURCHASED（update 前 purchasedEntitlements）
 *
 * 【U4 语义说明】
 *   接口对 quantity / purchasedQuantity 按「增量」处理：响应中的计数值 ≈ memberships 快照 + 本次请求中的数量。
 *   若仍断言「响应等于本次 quantity 绝对值」会在共享等场景失败（例如原值 2 + 请求 2 → 返回 4）。
 *
 * 【PAPI-2515 结构说明】
 *   entitlementPoolId 与 details 位于 crossModuleEntitlements[].pools[]，不在组级。
 *   各池 details 按裁剪规则只返回本池相关字段（买点池通常仅 purchasedEntitlements；
 *   普通池仅出现 cardholder/guest/shared 中与本池相关的键）。携伴聚合字段在组级 summary。
 *
 * 【断言说明】
 *   - 所有 pm.test 名称：中文 + 编号（U0/U1/U2/U3/U4a/U4b）
 *   - 失败 message：写明期望 vs 实际（含 JSON 片段便于复制排查）
 * =============================================================================
 */

/* 引入 Chai 的 expect，与 memberships 后置脚本保持一致 */
const { expect } = require('chai');

/* -------------------------------------------------------------------------- */
/* 小节：解析 HTTP 响应体为 JSON                                                */
/* -------------------------------------------------------------------------- */

let responseJson = null;
try {
    responseJson = pm.response.json();
} catch (e) {
    responseJson = null;
}

/* -------------------------------------------------------------------------- */
/* 小节：读取环境变量（与 apifox_post_memberships_entitlement_pool.js 一致）   */
/* -------------------------------------------------------------------------- */

const envPoolId = pm.environment.get('ENTITLEMENT_POOL_ID');
const envMembershipId = pm.environment.get('MEMBERSHIP_ID');
const envScenario = (pm.environment.get('ENTITLEMENT_UPDATE_SCENARIO') || '')
    .toString()
    .trim()
    .toLowerCase();
const envUsageRestriction = pm.environment.get('USAGE_RESTRICTION');
const envQtyRaw = pm.environment.get('ENTITLEMENT_UPDATE_QUANTITY');
const envQtyNum =
    envQtyRaw === undefined || envQtyRaw === null || envQtyRaw === ''
        ? NaN
        : Number(envQtyRaw);

/* -------------------------------------------------------------------------- */
/* 小节：工具函数 — 对齐 PAPI-2515 pools[] 嵌套结构                            */
/* -------------------------------------------------------------------------- */

/**
 * 读取 details 中的整型指标；键不存在或无法解析则返回 null。
 * @param {object} details
 * @param {string} key
 * @returns {number|null}
 */
function intDetail(details, key) {
    if (!details || typeof details !== 'object' || !(key in details)) {
        return null;
    }
    const v = details[key];
    if (v === true || v === false) {
        return null;
    }
    if (typeof v === 'number' && Number.isInteger(v)) {
        return v;
    }
    const n = parseInt(v, 10);
    return isNaN(n) ? null : n;
}

/**
 * 在 crossModuleEntitlements[].pools[] 中按 entitlementPoolId 查找池条目。
 * @param {Array} crossList data.entitlements.crossModuleEntitlements
 * @param {string} poolId 环境变量中的池 ID
 * @returns {{ group: object, pool: object } | null}
 */
function findPoolByIdInCross(crossList, poolId) {
    if (!Array.isArray(crossList) || poolId === undefined || poolId === null) {
        return null;
    }
    const idStr = String(poolId);
    for (let i = 0; i < crossList.length; i++) {
        const group = crossList[i];
        if (!group || typeof group !== 'object') {
            continue;
        }
        const pools = group.pools;
        if (!Array.isArray(pools)) {
            continue;
        }
        for (let j = 0; j < pools.length; j++) {
            const pool = pools[j];
            if (pool && String(pool.entitlementPoolId) === idStr) {
                return { group: group, pool: pool };
            }
        }
    }
    return null;
}

/**
 * 收集 crossModuleEntitlements 下所有 pools[].entitlementPoolId，便于失败信息展示。
 * @param {Array} crossList
 * @returns {Array<string|null>}
 */
function collectAllPoolIds(crossList) {
    const ids = [];
    if (!Array.isArray(crossList)) {
        return ids;
    }
    crossList.forEach(function (group) {
        const pools = group && group.pools;
        if (!Array.isArray(pools)) {
            return;
        }
        pools.forEach(function (p) {
            ids.push(p && p.entitlementPoolId);
        });
    });
    return ids;
}

/** 读取环境变量中的数字快照（memberships 后置写入），非法则 NaN */
function envNumOrNaN(key) {
    const v = pm.environment.get(key);
    if (v === undefined || v === null || String(v).trim() === '') {
        return NaN;
    }
    const n = Number(v);
    return Number.isFinite(n) ? n : NaN;
}

/** usageRestriction → details 字段名 */
function usageRestrictionToField(ur) {
    if (ur === 1) {
        return 'cardholderExclusiveEntitlements';
    }
    if (ur === 2) {
        return 'guestsExclusiveEntitlements';
    }
    if (ur === 3) {
        return 'sharedEntitlements';
    }
    return null;
}

/* -------------------------------------------------------------------------- */
/* 小节：pm.test 断言                                                            */
/* -------------------------------------------------------------------------- */

pm.test('【U0】HTTP 状态码为成功区间（2xx）', function () {
    const code = pm.response.code;
    expect(
        code,
        '期望 HTTP 状态码为 2xx，实际 code=' + JSON.stringify(code) + '，请检查网关或服务错误页'
    ).to.be.within(200, 299);
});

pm.test('【U1】响应体为 JSON、业务 code 为 0，且含 data.membershipId / data.entitlements', function () {
    expect(
        responseJson,
        '期望响应体可解析为 JSON，实际解析失败，原始文本前 500 字符：' + String(pm.response.text()).slice(0, 500)
    ).to.be.an('object');
    expect(
        responseJson.code,
        '期望业务 code === 0，实际 code=' +
            JSON.stringify(responseJson.code) +
            '，片段=' +
            JSON.stringify(responseJson).slice(0, 600)
    ).to.equal(0);

    const data = responseJson.data;
    expect(data, '期望存在 data 对象，实际 data=' + JSON.stringify(data)).to.be.an('object');

    expect(
        envMembershipId,
        '环境变量 MEMBERSHIP_ID 未设置或为空，无法校验响应。请在 memberships 后置脚本成功执行后再调 update'
    )
        .to.be.a('string')
        .that.is.not.empty;

    expect(
        data.membershipId,
        '期望 data.membershipId === 环境 MEMBERSHIP_ID。期望=' +
            JSON.stringify(String(envMembershipId)) +
            '，实际=' +
            JSON.stringify(data.membershipId)
    ).to.equal(String(envMembershipId));

    const ent = data.entitlements;
    expect(ent, '期望存在 data.entitlements，实际=' + JSON.stringify(ent)).to.be.an('object');

    expect(
        ent.moduleExclusiveEntitlements,
        '期望 data.entitlements.moduleExclusiveEntitlements 为非空数组，实际=' +
            JSON.stringify(ent.moduleExclusiveEntitlements)
    )
        .to.be.an('array')
        .that.is.not.empty;

    expect(
        ent.crossModuleEntitlements,
        '期望 data.entitlements.crossModuleEntitlements 为非空数组，实际=' +
            JSON.stringify(ent.crossModuleEntitlements)
    )
        .to.be.an('array')
        .that.is.not.empty;

    expect(
        ent.enabledTypes,
        '期望 data.entitlements.enabledTypes 为非空数组，实际=' + JSON.stringify(ent.enabledTypes)
    )
        .to.be.an('array')
        .that.is.not.empty;
});

pm.test('【U2】crossModuleEntitlements[].pools[] 中包含本次更新的 entitlementPoolId（与环境变量一致）', function () {
    expect(
        envPoolId,
        '环境变量 ENTITLEMENT_POOL_ID 未设置，无法定位更新池。请先执行 memberships 选池脚本'
    )
        .to.be.a('string')
        .that.is.not.empty;

    const cross = responseJson.data.entitlements.crossModuleEntitlements;
    const hit = findPoolByIdInCross(cross, envPoolId);
    expect(
        hit,
        '期望在 crossModuleEntitlements[].pools[] 中存在 entitlementPoolId=' +
            JSON.stringify(String(envPoolId)) +
            ' 的项。实际未找到；当前所有池 ID 列表=' +
            JSON.stringify(collectAllPoolIds(cross)) +
            '；cross 结构片段=' +
            JSON.stringify(
                cross.map(function (g) {
                    return {
                        applicableModules: g && g.applicableModules,
                        pools: Array.isArray(g && g.pools)
                            ? g.pools.map(function (p) {
                                  return {
                                      entitlementPoolId: p && p.entitlementPoolId,
                                      details: p && p.details,
                                  };
                              })
                            : g && g.pools,
                    };
                })
            )
    ).to.be.an('object');
});

pm.test('【U3】目标池 details 结构符合 PAPI-2515 裁剪规则（按场景校验本池相关字段）', function () {
    const cross = responseJson.data.entitlements.crossModuleEntitlements;
    const hit = findPoolByIdInCross(cross, envPoolId);
    expect(hit, '内部错误：应已通过【U2】定位到池，实际 hit=' + JSON.stringify(hit)).to.be.an('object');

    const d = hit.pool.details;
    expect(
        d,
        '期望目标池存在 details 对象，实际 details=' + JSON.stringify(d) + '，整池=' + JSON.stringify(hit.pool)
    ).to.be.an('object');

    if (envScenario === 'purchased') {
        const pv = intDetail(d, 'purchasedEntitlements');
        expect(
            pv,
            '买点池期望 details.purchasedEntitlements 存在且为有限数字，实际 details=' + JSON.stringify(d)
        ).to.satisfy(function (v) {
            return v !== null && Number.isFinite(v);
        });
        return;
    }

    const ur = parseInt(String(envUsageRestriction), 10);
    expect(
        ur === 1 || ur === 2 || ur === 3,
        '普通权益场景期望环境 USAGE_RESTRICTION 为 1/2/3，实际=' + JSON.stringify(envUsageRestriction)
    ).to.equal(true);

    const field = usageRestrictionToField(ur);
    const actualVal = intDetail(d, field);
    expect(
        actualVal,
        '普通权益池期望 details.' +
            field +
            '（usageRestriction=' +
            ur +
            '）存在且为有限数字，实际 details=' +
            JSON.stringify(d)
    ).to.satisfy(function (v) {
        return v !== null && Number.isFinite(v);
    });
});

pm.test('【U4a】普通权益：usageRestriction 对应字段应等于「memberships 快照 + 本次 quantity」（增量语义）', function () {
    if (envScenario !== 'normal') {
        return;
    }
    if (!responseJson || !responseJson.data || !responseJson.data.entitlements) {
        throw new Error('【U4a】跳过失败：缺少 data.entitlements，请先修复【U1】');
    }

    expect(
        Number.isFinite(envQtyNum),
        '期望环境 ENTITLEMENT_UPDATE_QUANTITY 为数字，实际=' + JSON.stringify(envQtyRaw)
    ).to.equal(true);
    const ur = parseInt(String(envUsageRestriction), 10);
    expect(
        ur === 1 || ur === 2 || ur === 3,
        '期望环境 USAGE_RESTRICTION 为 1/2/3，实际=' + JSON.stringify(envUsageRestriction)
    ).to.equal(true);

    const cross = responseJson.data.entitlements.crossModuleEntitlements;
    const hit = findPoolByIdInCross(cross, envPoolId);
    if (!hit) {
        throw new Error('【U4a】未找到目标池，请先修复【U2】');
    }
    const d = hit.pool.details;

    let beforeVal = NaN;
    let fieldLabel = '';
    let actualVal = NaN;
    if (ur === 1) {
        beforeVal = envNumOrNaN('ENTITLEMENT_POOL_SNAPSHOT_CARDHOLDER');
        fieldLabel = 'cardholderExclusiveEntitlements(usageRestriction=1)';
        actualVal = intDetail(d, 'cardholderExclusiveEntitlements');
    } else if (ur === 2) {
        beforeVal = envNumOrNaN('ENTITLEMENT_POOL_SNAPSHOT_GUEST');
        fieldLabel = 'guestsExclusiveEntitlements(usageRestriction=2)';
        actualVal = intDetail(d, 'guestsExclusiveEntitlements');
    } else {
        beforeVal = envNumOrNaN('ENTITLEMENT_POOL_SNAPSHOT_SHARED');
        fieldLabel = 'sharedEntitlements(usageRestriction=3)';
        actualVal = intDetail(d, 'sharedEntitlements');
    }

    expect(
        Number.isFinite(beforeVal),
        '【U4a】缺少 memberships 写入的快照变量（请使用最新版 apifox_post_memberships_entitlement_pool.js 并重跑 memberships）。' +
            ' 期望可读 ENTITLEMENT_POOL_SNAPSHOT_' +
            (ur === 1 ? 'CARDHOLDER' : ur === 2 ? 'GUEST' : 'SHARED') +
            '，实际 raw=' +
            JSON.stringify(
                pm.environment.get(
                    ur === 1
                        ? 'ENTITLEMENT_POOL_SNAPSHOT_CARDHOLDER'
                        : ur === 2
                          ? 'ENTITLEMENT_POOL_SNAPSHOT_GUEST'
                          : 'ENTITLEMENT_POOL_SNAPSHOT_SHARED'
                )
            )
    ).to.equal(true);

    expect(
        actualVal,
        '【U4a】目标池 details.' + fieldLabel + ' 无法解析为有限数字，实际 details=' + JSON.stringify(d)
    ).to.satisfy(function (v) {
        return v !== null && Number.isFinite(v);
    });

    const expectedAfter = beforeVal + envQtyNum;
    expect(
        actualVal,
        '普通权益-' +
            fieldLabel +
            '：期望 更新后 === memberships 快照(' +
            beforeVal +
            ') + 本次请求 quantity(' +
            envQtyNum +
            ') = ' +
            expectedAfter +
            '，实际=' +
            actualVal +
            '；完整 details=' +
            JSON.stringify(d)
    ).to.equal(expectedAfter);
});

pm.test('【U4b】买点：若响应含 purchasedEntitlements 则等于「快照 + purchasedQuantity」（增量语义）', function () {
    if (envScenario !== 'purchased') {
        return;
    }
    if (!responseJson || !responseJson.data || !responseJson.data.entitlements) {
        throw new Error('【U4b】跳过失败：缺少 data.entitlements，请先修复【U1】');
    }
    expect(
        Number.isFinite(envQtyNum),
        '买点：期望 ENTITLEMENT_UPDATE_QUANTITY（即 purchasedQuantity）为数字，实际=' + JSON.stringify(envQtyRaw)
    ).to.equal(true);

    const cross = responseJson.data.entitlements.crossModuleEntitlements;
    const hit = findPoolByIdInCross(cross, envPoolId);
    if (!hit) {
        throw new Error('【U4b】未找到目标池，请先修复【U2】');
    }
    const d = hit.pool.details;

    if (!Object.prototype.hasOwnProperty.call(d, 'purchasedEntitlements')) {
        console.warn(
            '【U4b 提示】当前响应 details 无 purchasedEntitlements，已跳过与 purchasedQuantity 的数值对齐；' +
                '若接口文档要求返回该字段，请提缺陷。details=' +
                JSON.stringify(d)
        );
        return;
    }
    const beforeP = envNumOrNaN('ENTITLEMENT_POOL_SNAPSHOT_PURCHASED');
    const actualP = intDetail(d, 'purchasedEntitlements');
    expect(
        actualP,
        '买点：details.purchasedEntitlements 无法解析为有限数字，实际 details=' + JSON.stringify(d)
    ).to.satisfy(function (v) {
        return v !== null && Number.isFinite(v);
    });

    if (!Number.isFinite(beforeP)) {
        expect(
            actualP,
            '买点：未读到 ENTITLEMENT_POOL_SNAPSHOT_PURCHASED（请更新 memberships 后置并重跑）。退化为期望 purchasedEntitlements === 请求值(' +
                envQtyNum +
                ')，实际=' +
                actualP +
                '；details=' +
                JSON.stringify(d)
        ).to.equal(envQtyNum);
        return;
    }
    const expectedPurchased = beforeP + envQtyNum;
    expect(
        actualP,
        '买点：期望 details.purchasedEntitlements === 快照(' +
            beforeP +
            ') + purchasedQuantity(' +
            envQtyNum +
            ') = ' +
            expectedPurchased +
            '，实际=' +
            actualP +
            '；完整 details=' +
            JSON.stringify(d)
    ).to.equal(expectedPurchased);
});
