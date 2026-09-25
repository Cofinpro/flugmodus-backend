/*
 * Flugmodus-Nachthimmel: Sterne (leuchten bei Mausnähe), Flugroute mit Flugzeug,
 * Sternschnuppen und Pixel-Funkeln. Einbinden mit
 *   <script src="design/sky.js" defer></script>
 * auf einer Seite mit <body class="fm-page">. Abschalten einzelner Teile:
 *   <body class="fm-page" data-fm-meteors="off" data-fm-route="off">
 * API für eigene Momente: window.FlugmodusSky.sparkle(x, y), .sparkleAround(element), .shoot()
 */
(() => {
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const svgNs = "http://www.w3.org/2000/svg";

  // Feste Positionen im 1440×900-Raster, damit der Himmel überall gleich aussieht
  const STARS = [
    [120, 90, 1.2], [340, 210, 0.8], [610, 70, 1], [930, 150, 1.3], [1210, 60, 0.9], [1350, 260, 1.1],
    [1080, 820, 0.8], [230, 760, 1], [60, 480, 0.7], [1400, 600, 0.8], [40, 160, 0.8], [210, 40, 1],
    [470, 130, 0.7], [760, 40, 0.9], [820, 250, 0.7], [1030, 90, 1], [1300, 150, 0.8], [1420, 30, 0.7],
    [150, 300, 0.9], [1250, 340, 0.8], [90, 640, 1], [180, 860, 0.8], [420, 820, 0.9], [700, 870, 0.7],
    [880, 800, 1], [1180, 720, 0.9], [1330, 860, 1], [1260, 480, 0.7], [30, 860, 0.7], [560, 760, 0.8],
  ];
  const PLANE_PATH =
    "M12 0 L15 9 L26 13 L26 16 L15 14 L14 22 L17 25 L17 27 L12 25.5 L7 27 L7 25 L10 22 L9 14 L-2 16 L-2 13 L9 9 Z";
  const SPARKLE_COLORS = ["#fff", "#fff", "#fff", "#ffe8a3", "#ffb3e6", "#a8e4ff"];

  function buildSky(withRoute) {
    const sky = document.createElementNS(svgNs, "svg");
    sky.setAttribute("class", "fm-sky");
    sky.setAttribute("viewBox", "0 0 1440 900");
    sky.setAttribute("preserveAspectRatio", "xMidYMid slice");
    sky.setAttribute("aria-hidden", "true");
    const stars = STARS.map(([cx, cy, r]) => `<circle class="fm-star" cx="${cx}" cy="${cy}" r="${r}"/>`).join("");
    const route = withRoute
      ? `<path id="fm-flight" class="fm-sky-route" d="M -40 780 C 320 520, 520 140, 900 170 S 1380 420, 1500 120"/>
         <g class="fm-sky-plane">
           <path d="${PLANE_PATH}" transform="translate(-12 -13.5) rotate(90 12 13.5)"/>
           <animateMotion dur="22s" repeatCount="indefinite" rotate="auto"><mpath href="#fm-flight"/></animateMotion>
         </g>`
      : "";
    sky.innerHTML = `<g>${stars}</g>${route}`;
    return sky;
  }

  // Sterne leuchten auf, wenn die Maus in der Nähe ist
  function enableStarGlow() {
    const stars = [...document.querySelectorAll(".fm-star")];
    const reach = 300;
    let pointer = null;
    let frame = 0;
    function glow() {
      frame = 0;
      for (const star of stars) {
        let t = 0;
        if (pointer) {
          const box = star.getBoundingClientRect();
          const distance = Math.hypot(box.x + box.width / 2 - pointer.x, box.y + box.height / 2 - pointer.y);
          t = Math.max(0, 1 - distance / reach) ** 1.5;
        }
        star.style.setProperty("--t", t.toFixed(3));
      }
    }
    const schedule = () => { frame ||= requestAnimationFrame(glow); };
    addEventListener("pointermove", (event) => { pointer = { x: event.clientX, y: event.clientY }; schedule(); });
    document.documentElement.addEventListener("pointerleave", () => { pointer = null; schedule(); });
  }

  let meteorLayer = null;
  function shoot() {
    if (!meteorLayer || reducedMotion) return;
    const meteor = document.createElement("span");
    meteor.className = "fm-meteor";
    const angle = 18 + Math.random() * 22;
    const distance = 380 + Math.random() * 420;
    const radians = (angle * Math.PI) / 180;
    meteor.style.left = `${Math.random() * innerWidth * 0.75 - 80}px`;
    meteor.style.top = `${Math.random() * innerHeight * 0.45}px`;
    meteorLayer.append(meteor);
    meteor.animate(
      [
        { transform: `translate(0, 0) rotate(${angle}deg) scaleX(.3)`, opacity: 0 },
        { opacity: 1, offset: 0.2 },
        { transform: `translate(${Math.cos(radians) * distance}px, ${Math.sin(radians) * distance}px) rotate(${angle}deg) scaleX(1)`, opacity: 0 },
      ],
      { duration: 900 + Math.random() * 700, easing: "cubic-bezier(.3, 0, .7, 1)" },
    ).onfinish = () => meteor.remove();
  }
  function scheduleMeteors() {
    setTimeout(() => {
      if (!document.hidden) {
        shoot();
        if (Math.random() < 0.2) setTimeout(shoot, 250 + Math.random() * 400);
      }
      scheduleMeteors();
    }, 2500 + Math.random() * 4500);
  }

  function sparkle(x, y, color) {
    if (reducedMotion) return;
    const dot = document.createElement("span");
    dot.className = "fm-sparkle";
    dot.style.setProperty("--c", color || SPARKLE_COLORS[Math.floor(Math.random() * SPARKLE_COLORS.length)]);
    dot.style.left = `${x}px`;
    dot.style.top = `${y}px`;
    document.body.append(dot);
    dot.addEventListener("animationend", () => dot.remove());
  }
  // Ein Funken irgendwo auf Höhe des Elements, gestreut um ±spread px
  function sparkleAround(element, spread = 55) {
    const box = element.getBoundingClientRect();
    sparkle(box.left + Math.random() * box.width, box.top + box.height / 2 + (Math.random() - 0.5) * 2 * spread);
  }

  function init() {
    const body = document.body;
    body.prepend(buildSky(body.dataset.fmRoute !== "off"));
    enableStarGlow();
    if (body.dataset.fmMeteors !== "off") {
      meteorLayer = document.createElement("div");
      meteorLayer.className = "fm-meteors";
      meteorLayer.setAttribute("aria-hidden", "true");
      body.querySelector(".fm-sky").after(meteorLayer);
      if (!reducedMotion) scheduleMeteors();
    }
  }

  window.FlugmodusSky = { sparkle, sparkleAround, shoot, reducedMotion };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
