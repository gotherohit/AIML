// ---- Edit these to link the videos. Paste the full YouTube URL or just the video ID. ----
const CHANNEL = "https://www.youtube.com/@go_rohit";
const VIDEOS = {
  "rope-long":  "https://youtu.be/e3wE7pvi7sI",               // Positional encoding and RoPE, from scratch (long video)
  "rope-short": "https://youtube.com/shorts/VvRbbmzuqC4",               // RoPE Short
  "swa-short":  "https://youtube.com/shorts/akXuRjRXxZk",               // Sliding window attention Short
  "vision-long":  "https://youtu.be/15drILbSCVg",               // How LLMs see images (long video)
  "vision-short": "https://youtube.com/shorts/UvJ45e8awmI",       // To an AI, this cat is 1,015 tokens
  "tokenizer-long":  "https://youtu.be/hCq71l2DSHM",            // How a tokenizer works (long video), scheduled
  "tokenizer-short": "https://youtube.com/shorts/0-fl1HIrNxE",   // Tokenizer Short
  "quant-long":  "https://youtu.be/6WNO_kqoZzg",                 // Quantization explained (long video)
  "quant-short": "https://youtube.com/shorts/2BWzZdO9vzQ",       // Quantization in 6 steps
  "kv-long":     "https://youtu.be/9LxIXveSenQ",                 // Why cache reads are 95% cheaper (long video)
  "kv-short":    "https://youtube.com/shorts/qnKMisC82ns",       // Why cached tokens cost 95% less
  "gguf-short":  "https://youtube.com/shorts/mGplRXdsJO4",       // 1 file, 1 whole AI model: how GGUF works
  "chat-short":  "https://youtube.com/shorts/MR_0fXvwU3A",       // What your AI actually sees when you chat
};
// ------------------------------------------------------------------------------------------

function videoId(v) {
  if (!v) return "";
  const m = v.match(/(?:youtu\.be\/|v=|shorts\/|embed\/|live\/)([\w-]{11})/);
  return m ? m[1] : (/^[\w-]{11}$/.test(v) ? v : "");
}

// Scheduled videos: anything marked data-soon is checked with YouTube's public oEmbed lookup on every page load.
// It answers 401/403 while a video is private or scheduled and 200 once it is public, so a scheduled video
// switches from "coming soon" to the player by itself when it goes live. If the lookup cannot be reached at all
// (offline, blocked), the video is treated as live rather than hiding a published video.
const probes = {};
function isLive(key) {
  const id = videoId(VIDEOS[key]);
  if (!id) return Promise.resolve(false);
  if (!probes[key]) probes[key] = fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${id}&format=json`)
    .then((r) => r.ok, () => true);
  return probes[key];
}

// Video blocks: <div class="yt" data-video="key" data-title="..." data-cover="img.jpg" [data-soon]>
function showPlayer(el, id) {
  const label = el.dataset.label || "Video";
  el.classList.remove("pending");
  el.style.backgroundImage = `url("${el.dataset.cover || `https://i.ytimg.com/vi/${id}/hqdefault.jpg`}")`;
  el.innerHTML = "";
  const b = document.createElement("button");
  b.className = "play";
  b.setAttribute("aria-label", "Play: " + el.dataset.title);
  b.innerHTML = `<span class="ic"></span><span class="label">${label}</span>${el.dataset.title}`;
  b.onclick = () => {
    el.innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0" title="${el.dataset.title}" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>`;
  };
  el.appendChild(b);
}
function showSoon(el) {
  const label = el.dataset.label || "Video";
  el.classList.add("pending");
  if (el.dataset.cover) el.style.backgroundImage = `url("${el.dataset.cover}")`;
  el.innerHTML = `<div class="soon"><span class="label">${label} · coming soon</span>${el.dataset.title}</div>`;
}
document.querySelectorAll(".yt[data-video]").forEach((el) => {
  const key = el.dataset.video, id = videoId(VIDEOS[key]);
  if (el.hasAttribute("data-soon")) {          // announced or scheduled: "coming soon" until YouTube says it is public
    showSoon(el);
    isLive(key).then((live) => { if (live) showPlayer(el, id); });
    return;
  }
  if (!id) {                       // no link yet: hide the slot
    const box = el.parentElement;
    el.remove();
    if (box.classList.contains("videos") && !box.querySelector(".yt")) box.remove();
    else box.classList.remove("two");
    return;
  }
  showPlayer(el, id);
});

// Links: <a data-watch="key"> go to the video (with data-soon: only once it is public); hidden until set.
document.querySelectorAll("[data-watch]").forEach((a) => {
  const key = a.dataset.watch, id = videoId(VIDEOS[key]);
  if (!id) { a.remove(); return; }
  if (a.hasAttribute("data-soon")) {
    a.style.display = "none";
    isLive(key).then((live) => { if (live) { a.href = `https://www.youtube.com/watch?v=${id}`; a.style.display = ""; } });
    return;
  }
  a.href = `https://www.youtube.com/watch?v=${id}`;
});
// Text that changes when a scheduled video goes live: <span data-live="key" data-live-text="...">coming soon text</span>
document.querySelectorAll("[data-live]").forEach((e) => {
  isLive(e.dataset.live).then((live) => { if (live) e.textContent = e.dataset.liveText; });
});
document.querySelectorAll("[data-channel]").forEach((a) => {
  if (CHANNEL) a.href = CHANNEL.includes("?") ? CHANNEL : CHANNEL.replace(/\/$/, "") + "?sub_confirmation=1";
  else a.remove();
});
document.querySelectorAll("[data-if-links]").forEach((box) => {
  if (box.querySelector("a")) return;
  if (box.tagName === "DD" && box.previousElementSibling) box.previousElementSibling.remove();
  box.remove();
});

// Table of contents: open on wide screens, highlight the section being read.
const toc = document.querySelector(".toc");
if (toc) {
  if (matchMedia("(min-width: 1061px)").matches) toc.open = true;
  const links = [...toc.querySelectorAll("a")];
  const heads = links.map((a) => document.getElementById(a.hash.slice(1))).filter(Boolean);
  const onScroll = () => {
    let cur = heads[0];
    for (const h of heads) if (h.getBoundingClientRect().top < innerHeight * 0.35) cur = h;
    links.forEach((a) => a.classList.toggle("on", a.hash === "#" + cur.id));
  };
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();
}
