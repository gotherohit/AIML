// ---- Edit these to link the videos. Paste the full YouTube URL or just the video ID. ----
const CHANNEL = "https://www.youtube.com/@go_rohit";
const VIDEOS = {
  "rope-long":  "https://youtu.be/e3wE7pvi7sI",               // Positional encoding and RoPE, from scratch (long video)
  "rope-short": "https://youtube.com/shorts/VvRbbmzuqC4",               // RoPE Short
  "swa-short":  "https://youtube.com/shorts/akXuRjRXxZk",               // Sliding window attention Short
  "vision-long":  "https://youtu.be/15drILbSCVg",               // How LLMs see images (long video)
  "vision-short": "https://youtube.com/shorts/UvJ45e8awmI",       // To an AI, this cat is 1,015 tokens
};
// ------------------------------------------------------------------------------------------

function videoId(v) {
  if (!v) return "";
  const m = v.match(/(?:youtu\.be\/|v=|shorts\/|embed\/|live\/)([\w-]{11})/);
  return m ? m[1] : (/^[\w-]{11}$/.test(v) ? v : "");
}

// Video blocks: <div class="yt" data-video="key" data-title="..." data-cover="img.jpg">
document.querySelectorAll(".yt[data-video]").forEach((el) => {
  const id = videoId(VIDEOS[el.dataset.video]);
  const label = el.dataset.label || "Video";
  const cover = el.dataset.cover || (id ? `https://i.ytimg.com/vi/${id}/hqdefault.jpg` : "");
  if (cover) el.style.backgroundImage = `url("${cover}")`;
  if (!id) {                       // no link yet: hide the slot
    const box = el.parentElement;
    el.remove();
    if (box.classList.contains("videos") && !box.querySelector(".yt")) box.remove();
    else box.classList.remove("two");
    return;
  }
  const b = document.createElement("button");
  b.className = "play";
  b.setAttribute("aria-label", "Play: " + el.dataset.title);
  b.innerHTML = `<span class="ic"></span><span class="label">${label}</span>${el.dataset.title}`;
  b.onclick = () => {
    el.innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0" title="${el.dataset.title}" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>`;
  };
  el.appendChild(b);
});

// Links: <a data-watch="key"> go to the video; <a data-channel> go to the channel. Hidden until set.
document.querySelectorAll("[data-watch]").forEach((a) => {
  const id = videoId(VIDEOS[a.dataset.watch]);
  if (id) a.href = `https://www.youtube.com/watch?v=${id}`; else a.remove();
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
