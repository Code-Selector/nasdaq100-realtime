/**
 * 纳斯达克100 实时行情 - 前端逻辑
 */

const API_BASE = "";  // 同源，留空即可
const REFRESH_INTERVAL = 60; // 秒

let allStocks = [];
let prevPrices = {};   // ticker -> 上一次的 price，用于闪烁
let countdownTimer = null;
let countdown = REFRESH_INTERVAL;

// ── DOM refs ──
const $body       = document.getElementById("stockBody");
const $sessionBadge = document.getElementById("sessionBadge");
const $timeCN     = document.getElementById("timeCN");
const $timeET     = document.getElementById("timeET");
const $statUp     = document.getElementById("statUp");
const $statDown   = document.getElementById("statDown");
const $statFlat   = document.getElementById("statFlat");
const $statAvg    = document.getElementById("statAvg");
const $statTotal  = document.getElementById("statTotal");
const $statRefresh= document.getElementById("statRefresh");
const $search     = document.getElementById("searchInput");
const $sort       = document.getElementById("sortSelect");
const $autoCheck  = document.getElementById("autoRefreshCheck");
const $countdown  = document.getElementById("countdown");
const $heatbar    = document.getElementById("heatbar");
const $updateInfo = document.getElementById("updateInfo");

// ═══════════════════════════════════════════════════════════════
//  数据获取
// ═══════════════════════════════════════════════════════════════
async function fetchData() {
    try {
        const resp = await fetch(`${API_BASE}/api/nasdaq100`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        allStocks = data.stocks || [];
        updateHeader(data);
        updateStats(data.stats);
        updateHeatbar(data.stats);
        renderTable();
        $updateInfo.textContent = `上次更新: ${data.updatedAt || "--"} | 第 ${data.fetchCount || 0} 次`;
    } catch (e) {
        console.error("Fetch failed:", e);
        $updateInfo.textContent = `获取失败: ${e.message}`;
    }
}

// ═══════════════════════════════════════════════════════════════
//  Header
// ═══════════════════════════════════════════════════════════════
function updateHeader(data) {
    const session = data.session || {};
    $sessionBadge.textContent = session.label || "--";
    $sessionBadge.style.borderColor = session.color || "#666";
    $sessionBadge.style.color = session.color || "#fff";
    $timeCN.textContent = `🇨🇳 ${data.updatedAt || "--"}`;
    $timeET.textContent = `🇺🇸 ${data.updatedEt || "--"}`;
}

// ═══════════════════════════════════════════════════════════════
//  Stats
// ═══════════════════════════════════════════════════════════════
function updateStats(stats) {
    if (!stats) return;
    $statUp.textContent = stats.up ?? "--";
    $statDown.textContent = stats.down ?? "--";
    $statFlat.textContent = stats.flat ?? "--";
    $statTotal.textContent = stats.total ?? "--";
    $statRefresh.textContent = stats.total ?? "--";
    const avgEl = $statAvg;
    const avg = stats.avgChange ?? 0;
    avgEl.textContent = `${avg >= 0 ? "+" : ""}${avg.toFixed(2)}%`;
    avgEl.className = "stat-value" + (avg > 0 ? " td-up" : avg < 0 ? " td-down" : "");
}

function updateHeatbar(stats) {
    if (!stats || !stats.total) return;
    const total = stats.total;
    const upPct = ((stats.up / total) * 100).toFixed(1);
    const flatPct = ((stats.flat / total) * 100).toFixed(1);
    const downPct = ((stats.down / total) * 100).toFixed(1);
    $heatbar.innerHTML = `
        <div class="bar-up" style="width:${upPct}%" title="上涨 ${stats.up}"></div>
        <div class="bar-flat" style="width:${flatPct}%" title="平盘 ${stats.flat}"></div>
        <div class="bar-down" style="width:${downPct}%" title="下跌 ${stats.down}"></div>
    `;
}

// ═══════════════════════════════════════════════════════════════
//  Table 渲染
// ═══════════════════════════════════════════════════════════════
function renderTable() {
    const keyword = ($search.value || "").trim().toUpperCase();
    let stocks = [...allStocks];

    // 过滤
    if (keyword) {
        stocks = stocks.filter(s =>
            s.ticker.includes(keyword) || (s.name || "").toUpperCase().includes(keyword)
        );
    }

    // 排序
    const sortVal = $sort.value;
    stocks = sortStocks(stocks, sortVal);

    // 构建 HTML
    if (stocks.length === 0) {
        $body.innerHTML = `<tr><td colspan="16" class="loading">无匹配数据</td></tr>`;
        return;
    }

    const rows = stocks.map((s, i) => {
        const pct = s.changePercent ?? 0;
        const cls = pct > 0 ? "td-up" : pct < 0 ? "td-down" : "td-flat";

        // flash
        const prev = prevPrices[s.ticker];
        let flashClass = "";
        if (prev !== undefined && s.price !== prev) {
            flashClass = s.price > prev ? "flash-up" : "flash-down";
        }

        // mini bar: max bar width = 50% cell, max pct clamp ±15%
        const clampPct = Math.max(-15, Math.min(15, pct));
        const barWidth = Math.abs(clampPct) / 15 * 50;
        const barDir = pct >= 0 ? "up" : "down";

        // after-hours coloring
        const ahPct = s.afterHoursChangePct ?? 0;
        const ahCls = ahPct > 0 ? "td-up" : ahPct < 0 ? "td-down" : "td-flat";

        return `<tr class="${flashClass}">
            <td class="td-rank">${i + 1}</td>
            <td class="td-ticker">${esc(s.ticker)}</td>
            <td class="td-name" title="${esc(s.name)}">${esc(s.name)}</td>
            <td class="td-price ${cls}">$${fmtNum(s.price, 2)}</td>
            <td class="${cls}">${fmtChange(s.change)}</td>
            <td class="${cls}" style="font-weight:700">${fmtPct(pct)}</td>
            <td class="mini-bar-cell">
                <div class="mini-bar-wrap">
                    <div class="mini-bar-center"></div>
                    <div class="mini-bar-fill ${barDir}" style="width:${barWidth}%"></div>
                </div>
            </td>
            <td class="${ahCls}">${s.afterHoursPrice != null ? '$' + fmtNum(s.afterHoursPrice, 2) : '--'}</td>
            <td class="${ahCls}" style="font-weight:600">${fmtPct(s.afterHoursChangePct)}</td>
            <td>$${fmtNum(s.prevClose, 2)}</td>
            <td>$${fmtNum(s.open, 2)}</td>
            <td>$${fmtNum(s.high, 2)}</td>
            <td>$${fmtNum(s.low, 2)}</td>
            <td>${fmtVolume(s.volume)}</td>
            <td>${fmtMarketCap(s.marketCap)}</td>
            <td>${s.pe != null ? s.pe.toFixed(1) : "--"}</td>
        </tr>`;
    });

    $body.innerHTML = rows.join("");

    // 更新 prevPrices
    allStocks.forEach(s => { prevPrices[s.ticker] = s.price; });
}

// ═══ 排序 ═══
function sortStocks(stocks, key) {
    const [field, dir] = key.split("_");
    const asc = dir === "asc" ? 1 : -1;
    return stocks.sort((a, b) => {
        let va = a[field], vb = b[field];
        if (va == null) va = -Infinity;
        if (vb == null) vb = -Infinity;
        if (typeof va === "string") return va.localeCompare(vb) * asc;
        return (va - vb) * asc;
    });
}

// ═══ 格式化 ═══
function fmtNum(n, d) {
    return n != null ? n.toFixed(d) : "--";
}

function fmtChange(n) {
    if (n == null) return "--";
    return (n >= 0 ? "+" : "") + n.toFixed(2);
}

function fmtPct(n) {
    if (n == null) return "--";
    return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}

function fmtVolume(n) {
    if (n == null) return "--";
    if (n >= 1e8) return (n / 1e8).toFixed(1) + "亿";
    if (n >= 1e4) return (n / 1e4).toFixed(0) + "万";
    return n.toLocaleString();
}

function fmtMarketCap(n) {
    if (n == null) return "--";
    if (n >= 1e12) return "$" + (n / 1e12).toFixed(1) + "T";
    if (n >= 1e9) return "$" + (n / 1e9).toFixed(0) + "B";
    if (n >= 1e6) return "$" + (n / 1e6).toFixed(0) + "M";
    return "$" + n.toLocaleString();
}

function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

// ═══════════════════════════════════════════════════════════════
//  倒计时 & 自动刷新
// ═══════════════════════════════════════════════════════════════
function startCountdown() {
    clearInterval(countdownTimer);
    countdown = REFRESH_INTERVAL;
    $countdown.textContent = countdown;

    countdownTimer = setInterval(() => {
        countdown--;
        $countdown.textContent = Math.max(0, countdown);
        if (countdown <= 0) {
            if ($autoCheck.checked) {
                fetchData();
            }
            countdown = REFRESH_INTERVAL;
        }
    }, 1000);
}

// ═══════════════════════════════════════════════════════════════
//  事件绑定
// ═══════════════════════════════════════════════════════════════
$search.addEventListener("input", () => renderTable());
$sort.addEventListener("change", () => renderTable());
$autoCheck.addEventListener("change", () => {
    if ($autoCheck.checked) {
        startCountdown();
    } else {
        clearInterval(countdownTimer);
        $countdown.textContent = "--";
    }
});

// ═══ 初始化 ═══
(async function init() {
    await fetchData();
    startCountdown();
})();
