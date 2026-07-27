/**
 * usedEntitlementDetails vs breakdown 加总 + cashPaymentApplied/cashier 入参回显（紧凑版，供内联）
 * ePass 响应常无 usedEntitlement* / 不回显 cashPaymentApplied：缺省时软跳过，勿硬失败。
 */
var ENT_KEYS = [
  "cardholderExclusiveEntitlements",
  "guestsExclusiveEntitlements",
  "sharedEntitlements",
  "purchasedEntitlements"
];
function _Ex(j) {
  if (!j) return null;
  if (j.data && j.data.extra) return j.data.extra;
  if (j.extra) return j.extra;
  return null;
}
function _N(v) {
  if (v === null || v === undefined) return NaN;
  return Number(v);
}
function _F(v) {
  try {
    return JSON.stringify(v);
  } catch (e) {
    return String(v);
  }
}
function _Own(o, k) {
  return !!(o && Object.prototype.hasOwnProperty.call(o, k));
}
function _BizOk(j) {
  if (!j || typeof j !== "object") return false;
  if (!Object.prototype.hasOwnProperty.call(j, "code")) return true;
  var c = j.code;
  return c === 0 || c === 1 || c === "0" || c === "1";
}
function _Req() {
  try {
    var r = pm.request && pm.request.body ? pm.request.body.raw : null;
    if (!r || !String(r).trim()) return null;
    return JSON.parse(String(r));
  } catch (e) {
    return null;
  }
}
var _json = pm.response.json();
if (!_BizOk(_json)) {
  pm.test(
    "一致性断言 skip (business not ok) | code=" +
      (_json && _json.code) +
      " err=" +
      (_json && _json.errCode),
    function () {
      console.warn("[extra-consistency] skip", _json && _json.code, _json && _json.errCode);
    }
  );
} else {
  var _extra = _Ex(_json);
  var _det = _extra ? _extra.usedEntitlementDetails : null;
  var _bd = _extra ? _extra.usedEntitlementBreakdown : null;
  if (_det == null && _bd == null) {
    pm.test("usedEntitlementDetails/Breakdown 缺省可跳过 | 期望=ePass可无 | 实际=null", function () {
      console.warn("[extra-consistency] usedEntitlement* absent; soft skip");
    });
  } else {
    pm.test("usedEntitlementDetails 存在 | 期望=object | 实际=type", function () {
      pm.expect(_det, "usedEntitlementDetails").to.be.an("object");
    });
    pm.test("usedEntitlementBreakdown 为数组 | 期望=array | 实际=type", function () {
      pm.expect(_bd, "usedEntitlementBreakdown").to.be.an("array");
    });
    if (_det && Array.isArray(_bd)) {
      pm.test("usedEntitlementDetails 含4权益key | 期望=4keys | 实际=keys", function () {
        for (var i = 0; i < ENT_KEYS.length; i++) {
          var k = ENT_KEYS[i];
          pm.expect(_det, "missing " + k).to.have.property(k);
          pm.expect(isNaN(_N(_det[k])), "details." + k + " not number").to.be.false;
        }
      });
      if (_bd.length === 0) {
        pm.test("breakdown=[] 则 details 全0 | 期望=0 | 实际=details", function () {
          for (var i = 0; i < ENT_KEYS.length; i++) {
            var k = ENT_KEYS[i];
            pm.expect(_N(_det[k]), "details." + k).to.eql(0);
          }
        });
      } else {
        pm.test("breakdown[].entitlements 含相同4key | 期望=4keys | 实际=item", function () {
          for (var bi = 0; bi < _bd.length; bi++) {
            var en = _bd[bi] && _bd[bi].entitlements;
            pm.expect(en, "breakdown[" + bi + "].entitlements").to.be.an("object");
            for (var ki = 0; ki < ENT_KEYS.length; ki++) {
              var k = ENT_KEYS[ki];
              pm.expect(en, "bd[" + bi + "] missing " + k).to.have.property(k);
              pm.expect(isNaN(_N(en[k])), "bd[" + bi + "]." + k + " not number").to.be.false;
            }
          }
        });
        for (var ki2 = 0; ki2 < ENT_KEYS.length; ki2++) {
          (function (key) {
            var dv = _N(_det[key]),
              sum = 0;
            for (var bi2 = 0; bi2 < _bd.length; bi2++) {
              var en2 = _bd[bi2] && _bd[bi2].entitlements;
              var p = en2 ? _N(en2[key]) : NaN;
              if (!isNaN(p)) sum += p;
            }
            pm.test(key + " details=sum(breakdown) | 期望=" + dv + " | 实际=" + sum, function () {
              pm.expect(isNaN(dv), "details." + key + " invalid").to.be.false;
              pm.expect(sum, key + " mismatch").to.eql(dv);
            });
          })(ENT_KEYS[ki2]);
        }
      }
    }
  }
  var _body = _Req();
  if (_body) {
    var _re = _body.extra && typeof _body.extra === "object" ? _body.extra : null;
    var _hasA = _Own(_body, "cashPaymentApplied") || (_re && _Own(_re, "cashPaymentApplied"));
    var _hasC = _Own(_body, "cashier") || (_re && _Own(_re, "cashier"));
    var _reqA = _Own(_body, "cashPaymentApplied")
      ? _body.cashPaymentApplied
      : _re
        ? _re.cashPaymentApplied
        : undefined;
    var _reqC = _Own(_body, "cashier") ? _body.cashier : _re ? _re.cashier : undefined;
    if (_hasA || _hasC) {
      if (!_extra || typeof _extra !== "object") {
        pm.test("extra 存在(入参回显) | 期望=object|可跳过 | 实际=missing", function () {
          console.warn("[extra-consistency] extra missing for echo; soft skip");
        });
      } else {
        if (_hasA) {
          if (!_Own(_extra, "cashPaymentApplied")) {
            pm.test("cashPaymentApplied 回显缺省可跳过 | 期望=ePass可无 | 实际=undefined", function () {
              console.warn("[extra-consistency] cashPaymentApplied not echoed; soft skip");
            });
          } else {
            pm.test(
              "cashPaymentApplied 与入参一致 | 期望=" + _F(_reqA) + " | 实际=" + _F(_extra.cashPaymentApplied),
              function () {
                pm.expect(_extra.cashPaymentApplied, "cashPaymentApplied").to.eql(_reqA);
              }
            );
          }
        }
        if (_hasC) {
          if (!_Own(_extra, "cashier") || _extra.cashier == null) {
            pm.test("cashier 回显缺省可跳过 | 期望=可无/null | 实际=missingOrNull", function () {
              console.warn("[extra-consistency] cashier not echoed; soft skip");
            });
          } else {
            pm.test("cashier 与入参一致 | 期望=" + _F(_reqC) + " | 实际=" + _F(_extra.cashier), function () {
              if (_reqC === null) {
                pm.expect(
                  _extra.cashier === null || _extra.cashier === undefined,
                  "cashier should be null"
                ).to.be.true;
                return;
              }
              if (_reqC && typeof _reqC === "object" && _Own(_reqC, "paymentMode")) {
                pm.expect(_extra.cashier, "extra.cashier").to.be.an("object");
                pm.expect(_extra.cashier.paymentMode, "cashier.paymentMode").to.eql(_reqC.paymentMode);
                return;
              }
              pm.expect(_extra.cashier, "extra.cashier").to.eql(_reqC);
            });
          }
        }
      }
    }
  }
}
