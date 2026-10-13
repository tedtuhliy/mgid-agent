/* Arcadia Blog · советы — версия для трафика MGID (Казахстан). Собирается build.py, __CFG__ подставляется при сборке.
 *
 * Что делает страница (и чего не делает):
 *  - читает из ссылки тизера click_id и source (mgid_<кампания>_<площадка>), хранит их на время визита и
 *    переносит на другие страницы сайта;
 *  - на каждый настоящий клик посетителя по рекламному блоку Geozo шлёт на свой же адрес /dom/lead сигнал с
 *    click_id: nginx передаёт его в MGID как конверсию цели geozoclick (по одной на клик, не чаще раза в
 *    cooldownMs и не больше maxPerVisit за визит);
 *  - показывает метку «Реклама» и отступы только у заполненного блока;
 *  - показывает уведомление о cookies.
 * Нет пикселей TikTok, нет переходов, всплывающих окон и подмены кнопки «назад»: страница одинакова для всех.
 */
(function () {
  "use strict";
  var CFG = __CFG__;
  var qs = new URLSearchParams(location.search);
  var SAFE = /^[A-Za-z0-9_.-]{6,128}$/;

  function enc(s) { return encodeURIComponent(s); }
  function ssGet(k) { try { return sessionStorage.getItem("dom_" + k) || ""; } catch (e) { return ""; } }
  function ssSet(k, v) { try { sessionStorage.setItem("dom_" + k, v); } catch (e) {} }
  function lsGet(k) { try { return localStorage.getItem("dom_" + k) || ""; } catch (e) { return ""; } }
  function lsSet(k, v) { try { localStorage.setItem("dom_" + k, v); } catch (e) {} }

  // ---- атрибуция MGID -------------------------------------------------------------------------------------
  var clickId = qs.get("click_id") || ssGet("click_id");
  if (!SAFE.test(clickId)) clickId = "";
  var source = (qs.get("source") || ssGet("source") || "").replace(/[^A-Za-z0-9_.-]/g, "").slice(0, 80);
  if (clickId) { ssSet("click_id", clickId); ssSet("source", source); }

  function decorate() {
    if (!clickId) return;
    var els = document.querySelectorAll("a.js-int");
    for (var i = 0; i < els.length; i++) {
      var h = els[i].getAttribute("href");
      if (!h || /[?&]click_id=/.test(h)) continue;
      els[i].setAttribute("href", h + (h.indexOf("?") < 0 ? "?" : "&") + "click_id=" + enc(clickId) +
        (source ? "&source=" + enc(source) : ""));
    }
  }

  // ---- клик по рекламному блоку Geozo = конверсия ---------------------------------------------------------
  // Блоки Geozo рисуются в саму страницу (без iframe) внутри наших .ad-slot, лоадер при этом убирает с div
  // атрибут data-gz-block, поэтому ловим клик по ссылке внутри слота, а не по атрибуту.
  var t0 = Date.now(), last = 0, sent = 0;
  function sendLead() {
    var n = ++sent;
    var u = CFG.lead + "?c=" + enc(clickId) + "&n=" + n + "&t=" + Date.now();
    try {
      fetch(u, { method: "GET", keepalive: true, credentials: "omit", cache: "no-store" }).catch(function () {});
    } catch (e) {
      try { new Image().src = u; } catch (e2) {}
    }
  }
  function onClick(e) {
    if (!clickId || !e.isTrusted) return;                       // только настоящий клик человека и только с click_id MGID
    var el = e.target && e.target.closest ? e.target.closest(".ad-slot a[href]") : null;
    if (!el) return;
    var now = Date.now();
    if (now - t0 < CFG.minDwellMs) return;                     // клик в первые доли секунды — не человек
    if (now - last < CFG.cooldownMs) return;                   // один клик = один сигнал
    if (sent >= CFG.maxPerVisit) return;
    last = now;
    sendLead();
  }
  document.addEventListener("click", onClick, true);

  // ---- слоты: метка и отступы только у заполненного блока --------------------------------------------------
  // Лоадер Geozo подменяет контейнер блока новым элементом (атрибут data-gz-block получает случайное имя), поэтому
  // контейнер ищем заново при каждой проверке, а не держим ссылку.
  function watchSlots() {
    var slots = document.querySelectorAll(".ad-slot");
    Array.prototype.forEach.call(slots, function (slot) {
      function filled() {
        var inner = slot.querySelector("div");
        if (!inner) return false;
        if (inner.children.length > 0) return true;
        if (inner.textContent.replace(/\s+/g, "").length > 0) return true;
        return inner.offsetHeight > 24;
      }
      function check() {
        if (filled()) { slot.classList.add("filled"); return true; }
        return false;
      }
      if (slot.classList.contains("filled") || check()) return;
      if (window.MutationObserver) {
        var mo = new MutationObserver(function () { if (check()) mo.disconnect(); });
        mo.observe(slot, { childList: true, subtree: true, characterData: true, attributes: true });
      }
    });
  }

  // ---- уведомление о cookies -------------------------------------------------------------------------------
  function initBanner() {
    var box = document.getElementById("cookie");
    var ok = document.getElementById("cookie-ok");
    if (!box || lsGet("cookie")) return;
    box.hidden = false;
    if (ok) ok.addEventListener("click", function () { box.hidden = true; lsSet("cookie", "1"); });
  }

  function init() { decorate(); watchSlots(); initBanner(); }
  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();
