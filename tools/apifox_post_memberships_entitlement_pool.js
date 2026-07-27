/**
 * =============================================================================
 * Apifox 后置脚本：从 /v2/memberships 解析 entitlementPoolId，并写入环境变量供
 * /v2/entitlements/{entitlementPoolId}/update 使用。
 * =============================================================================
 *
 * 【挂载位置】
 *   必须挂在「POST/GET /v2/memberships」（注册/查询会员成功后）请求的「后置操作」中。
 *
 * 【前置依赖】
 *
 *   A）须在 Auth（或环境默认值）中配置的变量（与登录/token 一起即可）
 *   1. ENTITLEMENT_MODULE
 *        - 取值：数字字符串或数字，例如 `1`、`3`（与 crossModuleEntitlements[].applicableModules 中枚举一致）
 *   2. PURCHASED_QUANTITY
 *        - 取值：仅「买点」用例需要；写入买点请求体的 purchasedQuantity。
 *
 *   B）不要在 Auth 里写 ENTITLEMENT_UPDATE_CASE
 *   - `purchased` / `normal` 必须由**当前这条 /v2/memberships 请求的前置脚本**在发请求前写入环境：
 *     apifox-pre-memberships-scenario-purchased.js 或 apifox-pre-memberships-scenario-normal.js
 *   - 两条用例各复制一条 memberships，分别挂对应前置即可；无需、也不建议在 Auth 接口里写死该变量。
 *
 * 【本脚本写入的环境变量（在【R2】或【R3】测试全部断言通过之后写入，避免前置失败仍污染环境）】
 *   - ENTITLEMENT_POOL_ID          → 路径参数 {entitlementPoolId}，仅来自 crossModuleEntitlements[].pools[]
 *   - MEMBERSHIP_ID                → 来自本次响应 data.membershipId
 *   - ENTITLEMENT_UPDATE_BODY      → 整段 JSON 字符串，供 update 请求体引用
 *   - ENTITLEMENT_UPDATE_SCENARIO  → purchased | normal（便于排查）
 *   - USAGE_RESTRICTION            → 仅 normal 场景写入 1/2/3；买点场景会 unset
 *   - ENTITLEMENT_UPDATE_QUANTITY  → normal 为 quantity；purchased 时为 PURCHASED_QUANTITY
 *   - ENTITLEMENT_POOL_SNAPSHOT_*  → 更新前快照，供 update 后置断言「增量」校验（普通：三项计数；买点：purchasedEntitlements）
 *
 * 【后续请求配置示例】
 *   URL:  .../v2/entitlements/{{ENTITLEMENT_POOL_ID}}/update
 *   Body: 使用 {{ENTITLEMENT_UPDATE_BODY}}（若 Apifox 支持环境变量替换 JSON）或手动引用各字段拼装。
 *
 * 【配套脚本】
 *   - 用例分流（前置）：apifox-pre-memberships-scenario-purchased.js / apifox-pre-memberships-scenario-normal.js
 *   - update 自动 Body（前置）：apifox-pre-entitlements-update-case-purchased.js / apifox-pre-entitlements-update-case-normal.js
 *   - update 响应断言（后置）：apifox-post-entitlements-update-assert.js
 *
 * 【规则对照（对齐 PAPI-2515 / BuildP2515PoolUpdatePlan）】
 *   (1) entitlementPoolId 只能取自 data.entitlements.crossModuleEntitlements[].pools[].entitlementPoolId
 *   (2) 仅买点池：details 只含 purchasedEntitlements（无持卡人/携伴/共享三键），且值不为 -1
 *   (3) 其余池：details 中 cardholder/guest/shared 任一存在且值不为 -1 → 普通权益体；
 *       usageRestriction: 1=持卡人专属, 2=宾客专属, 3=共享（池内按 1>2>3 优先级取第一条）
 * =============================================================================
 */

/* 引入 Chai 的 expect，便于带清晰 message 的断言（与 Postman/Apifox 沙箱兼容） */
const { expect } = require('chai');

/* -------------------------------------------------------------------------- */
/* 小节：读取响应与环境变量                                                    */
/* -------------------------------------------------------------------------- */

/** 将 HTTP 响应体解析为对象；解析失败时 json 为 null，后续断言会给出明确失败信息 */
let responseJson = null;
try {
    responseJson = pm.response.json();
} catch (e) {
    responseJson = null;
}

/** 当前用例类型：purchased = 买点更新；normal = 普通权益更新（由前置脚本写入 ENTITLEMENT_UPDATE_CASE） */
const entitlementUpdateCase = (pm.environment.get('ENTITLEMENT_UPDATE_CASE') || '')
    .toString()
    .trim()
    .toLowerCase();

/** 要匹配的模块号（与 applicableModules 数组中的数字一致） */
const moduleRaw = pm.environment.get('ENTITLEMENT_MODULE');
const moduleNum = moduleRaw === undefined || moduleRaw === null || moduleRaw === ''
    ? NaN
    : parseInt(String(moduleRaw), 10);

/** 买点场景下请求体中的 purchasedQuantity（环境变量 PURCHASED_QUANTITY，通常与 token 一并放在 Auth） */
const purchasedQtyRaw = pm.environment.get('PURCHASED_QUANTITY');
const purchasedQuantity = purchasedQtyRaw === undefined || purchasedQtyRaw === null || purchasedQtyRaw === ''
    ? NaN
    : Number(purchasedQtyRaw);

/* -------------------------------------------------------------------------- */
/* 小节：工具函数 — 对齐 papi2515_cross_module_impl / Postman p2515* 辅助函数   */
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
 * 判定是否为「仅买点池」：含 purchasedEntitlements，且不含持卡人/携伴/共享三键。
 * 对齐 DetailsOnlyPurchasedEntitlements。
 * @param {object} details
 */
function detailsOnlyPurchasedEntitlements(details) {
    if (!details || typeof details !== 'object') {
        return false;
    }
    const keys = Object.keys(details);
    if (keys.indexOf('purchasedEntitlements') < 0) {
        return false;
    }
    const other = {
        cardholderExclusiveEntitlements: 1,
        guestsExclusiveEntitlements: 1,
        sharedEntitlements: 1,
    };
    for (let i = 0; i < keys.length; i++) {
        if (other[keys[i]]) {
            return false;
        }
    }
    return true;
}

/**
 * 买点池（规则 2）：仅含 purchasedEntitlements，且值不为 -1。
 * @param {object} details pools[].details
 */
function isPurchasedPoolDetails(details) {
    if (!detailsOnlyPurchasedEntitlements(details)) {
        return false;
    }
    const pv = intDetail(details, 'purchasedEntitlements');
    return pv !== null && pv !== -1;
}

/**
 * 根据规则(3)从 details 中解析普通权益动态入参：按优先级 持卡人(1) > 宾客(2) > 共享(3)。
 * 值为 null 或 -1 的字段跳过。
 * @returns {{ usageRestriction: number, quantity: number } | null}
 */
function resolveNormalUpdateFromDetails(details) {
    if (!details || typeof details !== 'object') {
        return null;
    }
    const pairs = [
        ['cardholderExclusiveEntitlements', 1],
        ['guestsExclusiveEntitlements', 2],
        ['sharedEntitlements', 3],
    ];
    for (let i = 0; i < pairs.length; i++) {
        const v = intDetail(details, pairs[i][0]);
        if (v !== null && v !== -1) {
            return { usageRestriction: pairs[i][1], quantity: v };
        }
    }
    return null;
}

/**
 * 从 crossModuleEntitlements 中筛出 applicableModules 含指定模块的组，并扁平化为 pools 条目。
 * @param {Array} crossAll data.entitlements.crossModuleEntitlements
 * @param {number} mod 模块号
 * @returns {Array<{ group: object, pool: object }>}
 */
function flattenPoolsByModule(crossAll, mod) {
    const result = [];
    if (!Array.isArray(crossAll) || !Number.isFinite(mod)) {
        return result;
    }
    crossAll.forEach(function (group) {
        if (!group || typeof group !== 'object') {
            return;
        }
        if (!Array.isArray(group.applicableModules) || group.applicableModules.indexOf(mod) === -1) {
            return;
        }
        const pools = group.pools;
        if (!Array.isArray(pools)) {
            return;
        }
        pools.forEach(function (pool) {
            if (pool && typeof pool === 'object') {
                result.push({ group: group, pool: pool });
            }
        });
    });
    return result;
}

/* -------------------------------------------------------------------------- */
/* 小节：pm.test 断言 — 名称使用「中文 + 规则编号」，失败信息带期望与实际值    */
/* -------------------------------------------------------------------------- */

pm.test('【R0】HTTP 状态码为成功区间（2xx）', function () {
    const code = pm.response.code;
    expect(
        code,
        '期望 HTTP 状态码为 2xx，实际 code=' + JSON.stringify(code) + '，请检查上游网关或服务是否报错'
    ).to.be.within(200, 299);
});

pm.test('【R1】响应体为 JSON 且业务 code 为 0', function () {
    expect(
        responseJson,
        '期望响应体可解析为 JSON，实际解析失败（可能为空或非 JSON），原始文本前 500 字符：' +
            String(pm.response.text()).slice(0, 500)
    ).to.be.an('object');
    const bizCode = responseJson.code;
    expect(
        bizCode,
        '期望业务字段 code === 0，实际 code=' + JSON.stringify(bizCode) + '，完整响应片段：' +
            JSON.stringify(responseJson).slice(0, 800)
    ).to.equal(0);
});

pm.test('【R1】存在 crossModuleEntitlements 且 entitlementPoolId 仅从此数组 pools 选取（结构校验）', function () {
    const data = responseJson && responseJson.data;
    expect(data, '期望存在 data，实际 data=' + JSON.stringify(data)).to.be.an('object');
    const ent = data.entitlements;
    expect(ent, '期望存在 data.entitlements，实际=' + JSON.stringify(ent)).to.be.an('object');
    const cross = ent.crossModuleEntitlements;
    expect(
        cross,
        '期望 data.entitlements.crossModuleEntitlements 为非空数组；实际类型=' +
            Object.prototype.toString.call(cross) +
            '，值=' +
            JSON.stringify(cross)
    ).to.be.an('array').that.is.not.empty;

    let foundPoolId = false;
    for (let i = 0; i < cross.length; i++) {
        const pools = cross[i] && cross[i].pools;
        if (!Array.isArray(pools) || pools.length === 0) {
            continue;
        }
        for (let j = 0; j < pools.length; j++) {
            const pid = pools[j] && pools[j].entitlementPoolId;
            if (typeof pid === 'string' && pid.length > 0) {
                foundPoolId = true;
                break;
            }
        }
        if (foundPoolId) {
            break;
        }
    }
    expect(
        foundPoolId,
        '期望 crossModuleEntitlements[].pools[].entitlementPoolId 至少存在一个非空字符串；' +
            '当前 cross 结构片段=' +
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
    ).to.equal(true);
});

pm.test('【前置】ENTITLEMENT_UPDATE_CASE（由本请求前置脚本注入）与 ENTITLEMENT_MODULE 已就绪', function () {
    expect(
        entitlementUpdateCase === 'purchased' || entitlementUpdateCase === 'normal',
        '期望 ENTITLEMENT_UPDATE_CASE 为 purchased 或 normal。实际环境值=' +
            JSON.stringify(pm.environment.get('ENTITLEMENT_UPDATE_CASE')) +
            '。请勿在 Auth 中写死该变量；请在**本 memberships 请求的前置操作**中挂载 apifox-pre-memberships-scenario-purchased.js 或 apifox-pre-memberships-scenario-normal.js，先发请求再执行本后置。'
    ).to.equal(true);
    expect(
        Number.isFinite(moduleNum),
        '期望 ENTITLEMENT_MODULE 为可解析整数，实际 ENTITLEMENT_MODULE=' + JSON.stringify(moduleRaw)
    ).to.equal(true);
});

/* 提取 membershipId 与 cross 列表（前面测试已通过，此处仍做防御性读取） */
const dataLayer = responseJson && responseJson.data;
const membershipId = dataLayer && dataLayer.membershipId;
const crossAll = dataLayer && dataLayer.entitlements && dataLayer.entitlements.crossModuleEntitlements;
const poolsFiltered = flattenPoolsByModule(crossAll, moduleNum);

pm.test('【R1】在 applicableModules 包含 ENTITLEMENT_MODULE 的条件下存在可用权益池', function () {
    expect(
        poolsFiltered.length,
        '期望过滤后权益池数量 >= 1。ENTITLEMENT_MODULE=' +
            JSON.stringify(moduleNum) +
            '，实际过滤后数量=' +
            poolsFiltered.length +
            '；crossModuleEntitlements 条目数=' +
            (Array.isArray(crossAll) ? crossAll.length : 'N/A') +
            '；扁平化池列表=' +
            JSON.stringify(
                poolsFiltered.map(function (x) {
                    return {
                        entitlementPoolId: x.pool && x.pool.entitlementPoolId,
                        details: x.pool && x.pool.details,
                    };
                })
            )
    ).to.be.at.least(1);
});

pm.test('【R1】data.membershipId 存在，供 update 请求体使用', function () {
    expect(
        membershipId,
        '期望 data.membershipId 为非空字符串，实际 membershipId=' + JSON.stringify(membershipId)
    )
        .to.be.a('string')
        .that.is.not.empty;
});

/* -------------------------------------------------------------------------- */
/* 小节：按场景选池、断言、并写入环境变量（写在同一 pm.test 内，避免前置断言失败仍误写环境） */
/* -------------------------------------------------------------------------- */

if (entitlementUpdateCase === 'purchased') {
    pm.test('【R2】买点场景：解析 entitlementPoolId 并写入环境（规则2）', function () {
        expect(
            Number.isFinite(purchasedQuantity) && purchasedQuantity >= 0,
            '期望 PURCHASED_QUANTITY 为非负数字，实际 PURCHASED_QUANTITY=' + JSON.stringify(purchasedQtyRaw)
        ).to.equal(true);

        const entry = poolsFiltered.find(function (x) {
            return x && x.pool && isPurchasedPoolDetails(x.pool.details);
        });
        expect(
            entry,
            '期望在 applicableModules 包含模块 ' +
                moduleNum +
                ' 的池子中，至少存在一个「仅含 purchasedEntitlements」的买点池（规则2）。实际未找到；当前池子列表：' +
                JSON.stringify(
                    poolsFiltered.map(function (x) {
                        return {
                            entitlementPoolId: x.pool && x.pool.entitlementPoolId,
                            details: x.pool && x.pool.details,
                        };
                    })
                )
        ).to.be.an('object');

        const pool = entry.pool;
        const poolId = pool.entitlementPoolId;
        expect(
            poolId,
            '期望选中池的 entitlementPoolId 为非空字符串，实际=' + JSON.stringify(poolId)
        )
            .to.be.a('string')
            .that.is.not.empty;

        const bodyObj = {
            membershipId: String(membershipId),
            purchasedQuantity: purchasedQuantity,
        };

        const detPurch = pool.details || {};
        const snapPurch = intDetail(detPurch, 'purchasedEntitlements');
        pm.environment.set('ENTITLEMENT_POOL_SNAPSHOT_PURCHASED', String(snapPurch !== null ? snapPurch : 0));
        pm.environment.unset('ENTITLEMENT_POOL_SNAPSHOT_CARDHOLDER');
        pm.environment.unset('ENTITLEMENT_POOL_SNAPSHOT_GUEST');
        pm.environment.unset('ENTITLEMENT_POOL_SNAPSHOT_SHARED');

        pm.environment.set('ENTITLEMENT_POOL_ID', String(poolId));
        pm.environment.set('MEMBERSHIP_ID', String(membershipId));
        pm.environment.set('ENTITLEMENT_UPDATE_BODY', JSON.stringify(bodyObj));
        pm.environment.set('ENTITLEMENT_UPDATE_SCENARIO', entitlementUpdateCase);
        pm.environment.unset('USAGE_RESTRICTION');
        pm.environment.set('ENTITLEMENT_UPDATE_QUANTITY', String(purchasedQuantity));

        expect(pm.environment.get('ENTITLEMENT_POOL_ID'), '期望环境变量 ENTITLEMENT_POOL_ID 已写入且等于选中池').to.equal(
            String(poolId)
        );
        const savedBody = pm.environment.get('ENTITLEMENT_UPDATE_BODY');
        expect(
            savedBody,
            '期望 ENTITLEMENT_UPDATE_BODY 已写入；实际=' + JSON.stringify(savedBody)
        ).to.be.a('string').that.is.not.empty;
    });
} else {
    pm.test('【R3】普通权益场景：解析 entitlementPoolId、usageRestriction、quantity 并写入环境（规则3）', function () {
        let picked = null;
        for (let i = 0; i < poolsFiltered.length; i++) {
            const p = poolsFiltered[i].pool;
            const resolved = resolveNormalUpdateFromDetails(p && p.details);
            if (resolved) {
                picked = { pool: p, resolved: resolved };
                break;
            }
        }
        expect(
            picked,
            '期望在 applicableModules 包含模块 ' +
                moduleNum +
                ' 的池子中，至少存在一个池满足 cardholder/guest/shared 任一非 -1（规则3）。实际未找到；当前池子 details：' +
                JSON.stringify(
                    poolsFiltered.map(function (x) {
                        return {
                            entitlementPoolId: x.pool && x.pool.entitlementPoolId,
                            details: x.pool && x.pool.details,
                        };
                    })
                )
        ).to.be.an('object');

        const pool = picked.pool;
        const r = picked.resolved;
        const poolId = pool.entitlementPoolId;
        expect(
            poolId,
            '期望选中池的 entitlementPoolId 为非空字符串，实际=' + JSON.stringify(poolId)
        )
            .to.be.a('string')
            .that.is.not.empty;

        const bodyObj = {
            membershipId: String(membershipId),
            quantity: r.quantity,
            usageRestriction: r.usageRestriction,
        };

        expect(
            bodyObj.usageRestriction,
            '期望 usageRestriction 为 1、2 或 3，实际=' + JSON.stringify(bodyObj.usageRestriction)
        ).to.be.oneOf([1, 2, 3]);

        const detN = pool.details || {};
        const snapC = intDetail(detN, 'cardholderExclusiveEntitlements');
        const snapG = intDetail(detN, 'guestsExclusiveEntitlements');
        const snapS = intDetail(detN, 'sharedEntitlements');
        pm.environment.set('ENTITLEMENT_POOL_SNAPSHOT_CARDHOLDER', String(snapC !== null ? snapC : 0));
        pm.environment.set('ENTITLEMENT_POOL_SNAPSHOT_GUEST', String(snapG !== null ? snapG : 0));
        pm.environment.set('ENTITLEMENT_POOL_SNAPSHOT_SHARED', String(snapS !== null ? snapS : 0));
        pm.environment.unset('ENTITLEMENT_POOL_SNAPSHOT_PURCHASED');

        pm.environment.set('ENTITLEMENT_POOL_ID', String(poolId));
        pm.environment.set('MEMBERSHIP_ID', String(membershipId));
        pm.environment.set('ENTITLEMENT_UPDATE_BODY', JSON.stringify(bodyObj));
        pm.environment.set('ENTITLEMENT_UPDATE_SCENARIO', entitlementUpdateCase);
        pm.environment.set('USAGE_RESTRICTION', String(bodyObj.usageRestriction));
        pm.environment.set('ENTITLEMENT_UPDATE_QUANTITY', String(bodyObj.quantity));

        expect(pm.environment.get('ENTITLEMENT_POOL_ID'), '期望环境变量 ENTITLEMENT_POOL_ID 已写入且等于选中池').to.equal(
            String(poolId)
        );
        const savedBody = pm.environment.get('ENTITLEMENT_UPDATE_BODY');
        expect(
            savedBody,
            '期望 ENTITLEMENT_UPDATE_BODY 已写入；实际=' + JSON.stringify(savedBody)
        ).to.be.a('string').that.is.not.empty;
    });
}
