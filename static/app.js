let allChannels = [];
let favorites = JSON.parse(localStorage.getItem("fav") || "[]");

// شعارات حقيقية بناءً على اسم القناة
function getLogoUrl(channelName) {
    const name = channelName.toLowerCase();
    if (name.includes("bein")) return "https://upload.wikimedia.org/wikipedia/commons/9/9b/BeIN_Sports_logo.png";
    if (name.includes("mbc")) return "https://upload.wikimedia.org/wikipedia/commons/5/59/MBC_Logo.png";
    if (name.includes("bbc")) return "https://upload.wikimedia.org/wikipedia/commons/b/bc/BBC_logo.svg";
    if (name.includes("cnn")) return "https://upload.wikimedia.org/wikipedia/commons/b/b1/CNN.svg";
    if (name.includes("pluto")) return "https://pluto.tv/favicon.ico";
    if (name.includes("samsung")) return "https://www.samsung.com/etc/designs/samsung/static/favicon.ico";
    return "https://via.placeholder.com/300x180?text=TV";
}

function groupByCategory(channels) {
    const groups = {};
    channels.forEach(ch => {
        const cat = ch.category || "General";
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push(ch);
    });
    return groups;
}

function renderRows(channels) {
    const rowsDiv = document.getElementById("rows");
    const groups = groupByCategory(channels);
    let html = "";

    // صف المفضلات
    if (favorites.length > 0) {
        const favChannels = channels.filter(c => favorites.includes(c.name));
        if (favChannels.length) {
            html += `<div class="row"><h2>⭐ Favorites</h2><div class="row-items">`;
            favChannels.slice(0, 25).forEach(ch => {
                html += `
                    <div class="card" data-url="${ch.streams?.[0] || ''}" data-name="${ch.name}">
                        <img src="${getLogoUrl(ch.name)}" onerror="this.src='https://via.placeholder.com/300x180'">
                        <div class="title">${ch.name}</div>
                        <button class="fav-btn" onclick="toggleFav('${ch.name.replace(/'/g, "\\'")}', event)">⭐</button>
                    </div>
                `;
            });
            html += `</div></div>`;
        }
    }

    // باقي التصنيفات
    for (const [cat, chs] of Object.entries(groups)) {
        if (chs.length === 0) continue;
        html += `<div class="row"><h2>${cat}</h2><div class="row-items">`;
        chs.slice(0, 25).forEach(ch => {
            html += `
                <div class="card" data-url="${ch.streams?.[0] || ''}" data-name="${ch.name}">
                    <img src="${getLogoUrl(ch.name)}" onerror="this.src='https://via.placeholder.com/300x180'">
                    <div class="title">${ch.name}</div>
                    <button class="fav-btn" onclick="toggleFav('${ch.name.replace(/'/g, "\\'")}', event)">⭐</button>
                </div>
            `;
        });
        html += `</div></div>`;
    }
    rowsDiv.innerHTML = html;

    // ربط أحداث النقر على البطاقات
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (e.target.classList.contains('fav-btn')) return;
            const url = card.dataset.url;
            if (url) playChannel(url);
        });
    });
}

// نظام Fallback: إذا فشل التدفق يحاول التي تليه
let currentFallbackList = [];
let fallbackIndex = 0;

function playChannel(url) {
    const video = document.getElementById("player");
    if (!url) return alert("No stream URL");
    
    // محاولة جلب قائمة احتياطية من الخادم (اختياري)
    fetch(`/watch/${getChannelIdFromUrl(url)}`) // يجب تعديل حسب منطق التطبيق
        .then(res => res.json())
        .then(data => {
            currentFallbackList = [data.stream_url, ...(data.backups || [])];
            fallbackIndex = 0;
            tryPlayStream(currentFallbackList[0]);
        })
        .catch(() => {
            currentFallbackList = [url];
            fallbackIndex = 0;
            tryPlayStream(url);
        });
}

function tryPlayStream(streamUrl) {
    const video = document.getElementById("player");
    if (!streamUrl) {
        alert("All streams failed");
        return;
    }
    if (streamUrl.includes(".m3u8") && Hls.isSupported()) {
        if (window.hls) window.hls.destroy();
        const hls = new Hls();
        hls.loadSource(streamUrl);
        hls.attachMedia(video);
        window.hls = hls;
        hls.on(Hls.Events.ERROR, (_, data) => {
            if (data.fatal) {
                fallbackIndex++;
                tryPlayStream(currentFallbackList[fallbackIndex]);
            }
        });
    } else {
        video.src = streamUrl;
        video.play().catch(() => {
            fallbackIndex++;
            tryPlayStream(currentFallbackList[fallbackIndex]);
        });
    }
    video.onerror = () => {
        fallbackIndex++;
        tryPlayStream(currentFallbackList[fallbackIndex]);
    };
}

function getChannelIdFromUrl(url) {
    // بسيط: نحتاج إلى استخراج channel_id من التخزين المحلي
    // يمكن تحسينه لاحقاً، حالياً نستخدم أول قناة تحمل نفس الرابط
    const ch = allChannels.find(c => c.streams && c.streams[0] === url);
    return ch ? ch.id : 1;
}

function toggleFav(name, event) {
    event.stopPropagation();
    if (favorites.includes(name)) {
        favorites = favorites.filter(f => f !== name);
    } else {
        favorites.push(name);
    }
    localStorage.setItem("fav", JSON.stringify(favorites));
    renderRows(allChannels); // إعادة رسم
}

function filterChannels(searchTerm) {
    if (!searchTerm) return renderRows(allChannels);
    const filtered = allChannels.filter(ch => ch.name.toLowerCase().includes(searchTerm.toLowerCase()));
    renderRows(filtered);
}

async function loadChannels() {
    try {
        const res = await fetch("/channels?alive_only=false&limit=5000");
        const data = await res.json();
        allChannels = data.channels;
        renderRows(allChannels);
    } catch (err) {
        console.error(err);
        document.getElementById("rows").innerHTML = "<p>Failed to load channels</p>";
    }
}

document.getElementById("search").addEventListener("input", (e) => filterChannels(e.target.value));
loadChannels();
