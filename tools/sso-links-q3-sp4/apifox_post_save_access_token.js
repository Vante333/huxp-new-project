/**
 * Generate Access Token 后置脚本
 * 作用：把返回的 accessToken 写入环境变量 access_token
 *
 * 粘贴位置：
 *   Apifox → POST /v2/auth/token（Generate Access Token）
 *   →「后置操作」→「自定义脚本」
 */
const json = pm.response.json();

pm.test("换 Token 成功 code=0", function () {
  pm.expect(json.code).to.eql(0);
});

const token =
  (json.data && (json.data.accessToken || json.data.access_token)) ||
  json.accessToken ||
  json.access_token ||
  "";

if (!token) {
  console.log("[auth] 未找到 accessToken，完整响应:", JSON.stringify(json));
  pm.test("响应含 accessToken", function () {
    pm.expect.fail("未找到 data.accessToken，请检查 Body 的 clientId/secret");
  });
} else {
  pm.environment.set("access_token", token);
  // 兼容旧集合里写 {{accessToken}} 的 Header
  pm.environment.set("accessToken", token);

  if (json.data && json.data.validUntil != null) {
    pm.environment.set("token_validUntil", String(json.data.validUntil));
  }

  console.log("[auth] 已写入 access_token，长度=", token.length);
  console.log("[auth] 前缀=", token.substring(0, 20) + "...");
}
