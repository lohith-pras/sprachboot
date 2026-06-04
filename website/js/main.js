/* SprachBoot · interactions
 * nav frost on scroll · reveal-on-enter · honest counter tick-up · star-burst
 */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* — Nav frost on scroll (rAF-throttled) — */
  var nav = document.getElementById("nav");
  if (nav) {
    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        nav.classList.toggle("is-scrolled", window.scrollY > 24);
        ticking = false;
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* — Reveal-on-enter (one orchestrated entrance) — */
  var reveals = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
  if (reduceMotion || !("IntersectionObserver" in window)) {
    reveals.forEach(function (el) { el.classList.add("is-in"); });
  } else {
    var revObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("is-in");
          revObs.unobserve(e.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
    reveals.forEach(function (el) { revObs.observe(el); });
  }

  /* — Counter tick-up (honest target number) — */
  var counters = Array.prototype.slice.call(document.querySelectorAll("[data-count-to]"));
  function runCount(el) {
    var target = parseInt(el.getAttribute("data-count-to"), 10) || 0;
    if (reduceMotion) { el.textContent = String(target); return; }
    var start = performance.now();
    var dur = 1200;
    function frame(now) {
      var t = Math.min((now - start) / dur, 1);
      var eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      el.textContent = String(Math.round(eased * target));
      if (t < 1) {
        requestAnimationFrame(frame);
      } else {
        el.textContent = String(target);
        var box = el.closest(".plan__counter");
        if (box) {
          box.animate(
            [{ transform: "scale(1)" }, { transform: "scale(1.06)" }, { transform: "scale(1)" }],
            { duration: 360, easing: "cubic-bezier(0.22,1,0.36,1)" }
          );
        }
      }
    }
    requestAnimationFrame(frame);
  }
  if (counters.length) {
    if (!("IntersectionObserver" in window)) {
      counters.forEach(runCount);
    } else {
      var cntObs = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { runCount(e.target); cntObs.unobserve(e.target); }
        });
      }, { threshold: 0.6 });
      counters.forEach(function (el) { cntObs.observe(el); });
    }
  }

  /* — Star-burst on primary action (fires once per click, at click point) — */
  if (!reduceMotion) {
    document.querySelectorAll("[data-celebrate]").forEach(function (el) {
      el.addEventListener("click", function (ev) {
        var star = document.createElement("span");
        star.className = "star-burst";
        star.setAttribute("aria-hidden", "true");
        star.style.left = ev.clientX + "px";
        star.style.top = ev.clientY + "px";
        document.body.appendChild(star);
        star.addEventListener("animationend", function () { star.remove(); });
      });
    });
  }
})();
