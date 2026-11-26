(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(pointer: fine)").matches;

  // Reveal sections only as they enter the viewport.
  const revealItems = document.querySelectorAll(".motion-reveal");
  if ("IntersectionObserver" in window && !reduceMotion) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.14, rootMargin: "0px 0px -35px 0px" });
    revealItems.forEach((item) => revealObserver.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  // Lightweight pointer-reactive depth; no WebGL dependency.
  const orbStage = document.getElementById("orbStage");
  if (orbStage && finePointer && !reduceMotion) {
    let frame = 0;
    orbStage.addEventListener("pointermove", (event) => {
      const rect = orbStage.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        orbStage.style.transform = `rotateY(${x * 9}deg) rotateX(${-y * 8}deg)`;
      });
    });
    orbStage.addEventListener("pointerleave", () => {
      cancelAnimationFrame(frame);
      orbStage.style.transform = "rotateY(0deg) rotateX(0deg)";
    });
  }

  // Soft magnetic response for the two primary actions.
  if (finePointer && !reduceMotion) {
    document.querySelectorAll(".magnetic").forEach((button) => {
      button.addEventListener("pointermove", (event) => {
        const rect = button.getBoundingClientRect();
        const dx = event.clientX - rect.left - rect.width / 2;
        const dy = event.clientY - rect.top - rect.height / 2;
        button.style.transform = `translate(${dx * 0.055}px, ${dy * 0.08}px)`;
      });
      button.addEventListener("pointerleave", () => {
        button.style.transform = "";
      });
    });
  }

  // Ripple feedback on pointer and keyboard activation.
  document.querySelectorAll(".motion-cta").forEach((button) => {
    button.addEventListener("pointerdown", (event) => {
      const rect = button.getBoundingClientRect();
      const ripple = document.createElement("span");
      const diameter = Math.max(rect.width, rect.height) * 0.7;
      ripple.className = "ripple-ink";
      ripple.style.width = ripple.style.height = `${diameter}px`;
      ripple.style.left = `${event.clientX - rect.left - diameter / 2}px`;
      ripple.style.top = `${event.clientY - rect.top - diameter / 2}px`;
      button.appendChild(ripple);
      ripple.addEventListener("animationend", () => ripple.remove(), { once: true });
    });
  });

  // Ambient particle field in the hero. Pauses when the tab is hidden.
  const canvas = document.getElementById("ambientCanvas");
  if (!canvas || reduceMotion) return;
  const context = canvas.getContext("2d", { alpha: true });
  if (!context) return;
  let width = 0, height = 0, particles = [], raf = 0;
  const pointer = { x: -1000, y: -1000 };
  const particleCount = window.innerWidth < 640 ? 28 : 58;

  function resize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 1.6);
    width = rect.width;
    height = rect.height;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    particles = Array.from({ length: particleCount }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.28,
      vy: (Math.random() - 0.5) * 0.28,
      radius: Math.random() * 1.7 + 0.5
    }));
  }

  function draw() {
    context.clearRect(0, 0, width, height);
    particles.forEach((p, i) => {
      const dx = pointer.x - p.x, dy = pointer.y - p.y;
      const distanceToPointer = Math.hypot(dx, dy);
      if (distanceToPointer < 130 && distanceToPointer > 0) {
        p.vx -= (dx / distanceToPointer) * 0.006;
        p.vy -= (dy / distanceToPointer) * 0.006;
      }
      p.x += p.vx; p.y += p.vy;
      p.vx *= 0.995; p.vy *= 0.995;
      if (p.x < 0 || p.x > width) p.vx *= -1;
      if (p.y < 0 || p.y > height) p.vy *= -1;
      p.x = Math.max(0, Math.min(width, p.x));
      p.y = Math.max(0, Math.min(height, p.y));

      context.beginPath();
      context.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      context.fillStyle = "rgba(190,255,220,.62)";
      context.fill();

      for (let j = i + 1; j < particles.length; j++) {
        const other = particles[j];
        const distance = Math.hypot(p.x - other.x, p.y - other.y);
        if (distance < 112) {
          context.beginPath();
          context.moveTo(p.x, p.y);
          context.lineTo(other.x, other.y);
          context.strokeStyle = `rgba(101,230,224,${(1 - distance / 112) * 0.16})`;
          context.lineWidth = 0.7;
          context.stroke();
        }
      }
    });
    raf = requestAnimationFrame(draw);
  }

  canvas.parentElement.addEventListener("pointermove", (event) => {
    const rect = canvas.getBoundingClientRect();
    pointer.x = event.clientX - rect.left;
    pointer.y = event.clientY - rect.top;
  }, { passive: true });
  canvas.parentElement.addEventListener("pointerleave", () => {
    pointer.x = -1000; pointer.y = -1000;
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) cancelAnimationFrame(raf);
    else if (!raf || document.visibilityState === "visible") draw();
  });
  window.addEventListener("resize", resize, { passive: true });
  resize();
  draw();
})();